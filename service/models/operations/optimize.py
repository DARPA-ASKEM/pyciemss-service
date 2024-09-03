from __future__ import annotations

from typing import ClassVar, List, Optional
from enum import Enum

import numpy as np
import torch
from pydantic import BaseModel, Field, Extra
from models.base import OperationRequest, Timespan, HMIIntervention
from pyciemss.integration_utils.intervention_builder import (
    param_value_objective,
    start_time_objective,
    start_time_param_value_objective,
)

from pyciemss.ouu.qoi import obs_nday_average_qoi, obs_max_qoi
from models.converters import convert_static_interventions
from utils.tds import fetch_model, fetch_inferred_parameters


class QOIMethod(str, Enum):
    day_average = "day_average"
    max = "max"


class QOI(BaseModel):
    method: QOIMethod = QOIMethod.day_average
    contexts: List[str] = []

    def gen_call(self):
        contexts = self.contexts
        qoi_map = {
            QOIMethod.day_average: lambda samples: obs_nday_average_qoi(
                samples, contexts, 1
            ),
            QOIMethod.max: lambda samples: obs_max_qoi(samples, contexts),
        }
        return qoi_map[self.method]


def objfun(x, initial_guess, objective_function_option):
    if objective_function_option == "lower_bound":
        return np.sum(np.abs(x))
    if objective_function_option == "upper_bound":
        return -np.sum(np.abs(x))
    if objective_function_option == "initial_guess":
        return np.sum(np.abs(x - initial_guess))


class InterventionObjective(BaseModel):
    intervention_type: str = Field(
        "param_value",
        description="The intervention objective to use",
        example="param_value",
    )
    param_names: list[str]
    param_values: Optional[list[Optional[float]]] = None
    start_time: Optional[list[float]] = None
    objective_function_option: Optional[list[str]] = None
    initial_guess: Optional[list[float]] = None


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
    alpha: float = 0.95
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
    optimize_interventions: InterventionObjective  # These are the interventions to be optimized.
    fixed_interventions: list[HMIIntervention] = Field(
        None
    )  # Theses are interventions provided that will not be optimized
    logging_step_size: float = 1.0
    qoi: QOI
    risk_bound: float
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

        intervention_type = self.optimize_interventions.intervention_type
        if intervention_type == "param_value":
            assert self.optimize_interventions.start_time is not None
            start_time = [
                torch.tensor(time) for time in self.optimize_interventions.start_time
            ]
            param_value = [None] * len(self.optimize_interventions.param_names)

            optimize_interventions = param_value_objective(
                start_time=start_time,
                param_name=self.optimize_interventions.param_names,
                param_value=param_value,
            )
        if intervention_type == "start_time":
            assert self.optimize_interventions.param_values is not None
            param_value = [
                torch.tensor(value)
                for value in self.optimize_interventions.param_values
            ]
            optimize_interventions = start_time_objective(
                param_name=self.optimize_interventions.param_names,
                param_value=param_value,
            )
        if intervention_type == "start_time_param_value":
            optimize_interventions = start_time_param_value_objective(
                param_name=self.optimize_interventions.param_names
            )

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

        return {
            "model_path_or_json": amr_path,
            "logging_step_size": self.logging_step_size,
            "start_time": self.timespan.start,
            "end_time": self.timespan.end,
            "objfun": lambda x: objfun(
                x,
                self.optimize_interventions.initial_guess[0],
                self.optimize_interventions.objective_function_option[0],
            ),
            "qoi": self.qoi.gen_call(),
            "risk_bound": self.risk_bound,
            "initial_guess_interventions": self.optimize_interventions.initial_guess,
            "bounds_interventions": self.bounds_interventions,
            "static_parameter_interventions": optimize_interventions,
            "fixed_static_parameter_interventions": fixed_static_parameter_interventions,
            # https://github.com/DARPA-ASKEM/terarium/issues/4612
            # "fixed_static_state_interventions": fixed_static_state_interventions,
            "inferred_parameters": inferred_parameters,
            "n_samples_ouu": n_samples_ouu,
            "solver_method": solver_method,
            "solver_options": solver_options,
            **extra_options,
        }

    class Config:
        extra = Extra.forbid
        # use_enum_values = True
