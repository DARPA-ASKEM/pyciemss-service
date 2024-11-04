from __future__ import annotations

from typing import ClassVar, List, Optional, Union, Callable, Dict
from chirho.interventional.ops import Intervention
from enum import Enum
from utils.rabbitmq import OptimizeHook
from pika.exceptions import AMQPConnectionError
import socket
import logging


import numpy as np
import torch
from pydantic import BaseModel, Field, Extra
from models.base import OperationRequest, Timespan, HMIIntervention
from pyciemss.integration_utils.intervention_builder import (
    intervention_func_combinator,
    param_value_objective,
    start_time_objective,
    start_time_param_value_objective,
)

from pyciemss.ouu.qoi import obs_nday_average_qoi, obs_max_qoi
from models.converters import convert_static_interventions
from utils.tds import fetch_model, fetch_inferred_parameters


class InterventionType(str, Enum):
    param_value = "param_value"
    start_time = "start_time"
    start_time_param_value = "start_time_param_value"


class InterventionObjectiveFunction(str, Enum):
    lower_bound = ("lower_bound",)
    upper_bound = ("upper_bound",)
    initial_guess = "initial_guess"


class QOIMethod(str, Enum):
    day_average = "day_average"
    max = "max"


class QOI(BaseModel):
    method: QOIMethod = QOIMethod.day_average
    contexts: List[str] = []
    risk_bound: float = 0
    is_minimized: bool = True

    def gen_call(self):
        contexts = self.contexts
        if self.is_minimized is True:
            qoi_map = {
                QOIMethod.day_average: lambda samples: obs_nday_average_qoi(
                    samples, contexts, 1
                ),
                QOIMethod.max: lambda samples: obs_max_qoi(samples, contexts),
            }
        else:
            qoi_map = {
                QOIMethod.day_average: lambda samples: -obs_nday_average_qoi(
                    samples, contexts, 1
                ),
                QOIMethod.max: lambda samples: -obs_max_qoi(samples, contexts),
            }
        return qoi_map[self.method]

    def gen_risk_bound(self):
        if self.is_minimized is True:
            return self.risk_bound
        else:
            return -self.risk_bound


def objfun(x, optimize_interventions: list[InterventionObjective]):
    """
    Calculate the weighted sum of objective functions based on the given parameters.

    Parameters:
    x (list): The current values of the variables.
    optimize_interventions: The interventions which are being optimized over

    Returns:
    float: The weighted sum of the objective functions.
    """

    # Initialize the total sum to zero
    total_sum = 0
    # TODO: Will be cleaning this up in the next PR. I want minimal changes per PR for readability.
    relative_importance = [i.relative_importance for i in optimize_interventions]
    initial_guess = [i.initial_guess for i in optimize_interventions]
    objective_function_option = [
        i.objective_function_option for i in optimize_interventions
    ]
    # Calculate the sum of all weights, fallback to 1 if the sum is 0
    sum_of_all_weights = np.sum(relative_importance) or 1

    # Check if any of the required parameters is None and raise an error if so
    if (
        x is None
        or initial_guess is None
        or objective_function_option is None
        or relative_importance is None
    ):
        raise ValueError(
            "There was an issue creating the objective function. None of the parameters x, initial_guess, objective_function_option, or relative_importance can be None"
        )

    # Iterate over each variable
    for i in range(len(x)):
        # Calculate the weight for the current variable
        weight = relative_importance[i] / sum_of_all_weights

        # Apply the corresponding objective function based on the option provided
        if objective_function_option[i] == InterventionObjectiveFunction.lower_bound:
            total_sum += weight * np.abs(x[i])
        elif objective_function_option[i] == InterventionObjectiveFunction.upper_bound:
            total_sum += weight * -np.abs(x[i])
        elif (
            objective_function_option[i] == InterventionObjectiveFunction.initial_guess
        ):
            total_sum += weight * np.abs(x[i] - initial_guess[i])

    # Return the total weighted sum of the objective functions
    return total_sum


class InterventionObjective(BaseModel):
    intervention_type: InterventionType = Field(
        InterventionType.param_value,
        description="The intervention objective to use",
        example="param_value",
    )
    param_names: list[str]
    param_values: Optional[list[Optional[float]]] = None
    start_time: Optional[list[float]] = None
    objective_function_option: Optional[InterventionObjectiveFunction] = None
    initial_guess: Optional[list[float]] = None
    relative_importance: Optional[float] = None


class OptimizeExtra(BaseModel):
    num_samples: int = Field(
        100,
        description="""
            The number of samples to draw from the model to estimate risk for each optimization iteration.
        """,
        example=100,
    )
    inferred_parameters: Optional[str] = Field(
        None,
        description="ID from a previous calibration",
        example=None,
    )
    maxiter: int = 5
    maxfeval: int = 25
    alpha: Union[List[float], float] = 0.95
    solver_method: str = "dopri5"
    # https://github.com/ciemss/pyciemss/blob/main/pyciemss/integration_utils/interface_checks.py
    solver_step_size: float = Field(
        None,
        description="Step size required if solver method is euler.",
        example=1.0,
    )


class Optimize(OperationRequest):
    pyciemss_lib_function: ClassVar[str] = "optimize"
    model_config_id: str = Field(..., example="ba8da8d4-047d-11ee-be56")
    timespan: Timespan = Timespan(start=0, end=90)
    optimize_interventions: list[
        InterventionObjective
    ]  # These are the interventions to be optimized.
    fixed_interventions: list[HMIIntervention] = Field(
        None
    )  # Theses are interventions provided that will not be optimized
    logging_step_size: float = 1.0
    qoi: list[QOI]
    bounds_interventions: List[List[float]]
    extra: OptimizeExtra = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )

    def gen_pyciemss_args(self, job_id):
        # Get model from TDS
        amr_path = fetch_model(self.model_config_id, job_id)
        (
            fixed_static_parameter_interventions,
            fixed_static_state_interventions,
        ) = convert_static_interventions(self.fixed_interventions)

        transformed_optimize_interventions: list[
            Callable[[torch.Tensor], Dict[float, Dict[str, Intervention]]]
        ] = []
        intervention_func_lengths: list[int] = []
        for i in range(len(self.optimize_interventions)):
            currentIntervention = self.optimize_interventions[i]
            intervention_type = currentIntervention.intervention_type
            if intervention_type == InterventionType.param_value:
                assert currentIntervention.start_time is not None
                start_time = [
                    torch.tensor(time) for time in currentIntervention.start_time
                ]
                param_value = [None] * len(currentIntervention.param_names)

                transformed_optimize_interventions.append(
                    param_value_objective(
                        start_time=start_time,
                        param_name=currentIntervention.param_names,
                        param_value=param_value,
                    )
                )
                intervention_func_lengths.append(1)
            if intervention_type == InterventionType.start_time:
                assert currentIntervention.param_values is not None
                param_value = [
                    torch.tensor(value) for value in currentIntervention.param_values
                ]
                transformed_optimize_interventions.append(
                    start_time_objective(
                        param_name=currentIntervention.param_names,
                        param_value=param_value,
                    )
                )
                intervention_func_lengths.append(1)
            if intervention_type == InterventionType.start_time_param_value:
                transformed_optimize_interventions.append(
                    start_time_param_value_objective(
                        param_name=currentIntervention.param_names
                    )
                )
                intervention_func_lengths.append(2)

        extra_options = self.extra.dict()
        inferred_parameters = fetch_inferred_parameters(
            extra_options.pop("inferred_parameters"), job_id
        )
        n_samples_ouu = extra_options.pop("num_samples")
        solver_options = {}
        step_size = extra_options.pop(
            "solver_step_size"
        )  # Need to pop this out of extra.
        solver_method = extra_options.pop("solver_method")
        if step_size is not None and solver_method == "euler":
            solver_options["step_size"] = step_size

        total_possible_iterations = (
            extra_options.get("maxiter") + 1
        ) * extra_options.get("maxfeval")
        try:
            progress_hook = OptimizeHook(job_id, total_possible_iterations)
        except (socket.gaierror, AMQPConnectionError):
            logging.warning(
                "%s: Failed to connect to RabbitMQ. Unable to log progress", job_id
            )

            # Log progress hook when unable to connect - for testing purposes.
            def progress_hook(current_results):
                logging.info(f"Optimize current results: {current_results.tolist()}")

        qoi_methods = []
        risk_bounds = []
        for qoi in self.qoi:
            qoi_methods.append(qoi.gen_call())
            risk_bounds.append(qoi.gen_risk_bound())

        return {
            "model_path_or_json": amr_path,
            "logging_step_size": self.logging_step_size,
            "start_time": self.timespan.start,
            "end_time": self.timespan.end,
            "objfun": lambda x: objfun(x, self.optimize_interventions),
            "qoi": qoi_methods,
            "risk_bound": risk_bounds,
            "initial_guess_interventions": [
                i.initial_guess for i in self.optimize_interventions
            ],
            "bounds_interventions": self.bounds_interventions,
            "static_parameter_interventions": intervention_func_combinator(
                transformed_optimize_interventions, intervention_func_lengths
            ),
            "fixed_static_parameter_interventions": fixed_static_parameter_interventions,
            # https://github.com/DARPA-ASKEM/terarium/issues/4612
            # "fixed_static_state_interventions": fixed_static_state_interventions,
            "inferred_parameters": inferred_parameters,
            "n_samples_ouu": n_samples_ouu,
            "solver_method": solver_method,
            "solver_options": solver_options,
            "progress_hook": progress_hook,
            **extra_options,
        }

    class Config:
        extra = Extra.forbid
        # use_enum_values = True
