from __future__ import annotations

from typing import ClassVar, Dict, List, Optional

import numpy as np
import torch
from pydantic import BaseModel, Field, Extra
from models.base import OperationRequest, Timespan
from pyciemss.integration_utils.intervention_builder import (
    param_value_objective,
    start_time_objective,
)
from utils.tds import fetch_model, fetch_inferred_parameters


# TODO: Add more methods later if needed
# class QOIMethod(Enum):
#     obs_nday_average = "obs_nday_average"


def obs_nday_average_qoi(
    samples: Dict[str, torch.Tensor], contexts: List, ndays: int = 7
) -> np.ndarray:
    """
    Return estimate of last n-day average of each sample.
    samples is is the output from a Pyro Predictive object.
    samples[VARIABLE] is expected to have dimension (nreplicates, ntimepoints)
    Note: last ndays timepoints is assumed to represent last n-days of simulation.

    Taken from:
    https://github.com/ciemss/pyciemss/blob/main/docs/source/interfaces.ipynb
    """
    dataQoI = samples[contexts[0] + "_state"].detach().numpy()

    return np.mean(dataQoI[:, -ndays:], axis=1)


def objfun(x, is_minimized):
    if is_minimized:
        return np.sum(np.abs(x))
    else:
        return -np.sum(np.abs(x))


class InterventionObjective(BaseModel):
    selection: str = Field(
        "param_value",
        description="The intervention objective to use",
        example="param_value",
    )
    param_names: list[str]
    param_values: Optional[list[Optional[float]]] = None
    start_time: Optional[list[float]] = None


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
    maxfeval: int = 5
    is_minimized: bool = True
    alpha: float = 0.95


class Optimize(OperationRequest):
    pyciemss_lib_function: ClassVar[str] = "optimize"
    model_config_id: str = Field(..., example="ba8da8d4-047d-11ee-be56")
    timespan: Timespan = Timespan(start=0, end=90)
    interventions: InterventionObjective
    step_size: float = 1.0
    qoi: List[str]  # QOIMethod
    risk_bound: float
    initial_guess_interventions: List[float]
    bounds_interventions: List[List[float]]
    extra: OptimizeExtra = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )

    def gen_pyciemss_args(self, job_id):
        # Get model from TDS
        amr_path = fetch_model(self.model_config_id, job_id)

        intervention_type = self.interventions.selection
        if intervention_type == "param_value":
            assert self.interventions.start_time is not None
            start_time = [torch.tensor(time) for time in self.interventions.start_time]
            param_value = [None] * len(self.interventions.param_names)

            interventions = param_value_objective(
                start_time=start_time,
                param_name=self.interventions.param_names,
                param_value=param_value,
            )
        else:
            assert self.interventions.param_values is not None
            param_value = [
                torch.tensor(value) for value in self.interventions.param_values
            ]
            interventions = start_time_objective(
                param_name=self.interventions.param_names,
                param_value=param_value,
            )

        extra_options = self.extra.dict()
        inferred_parameters = fetch_inferred_parameters(
            extra_options.pop("inferred_parameters"), job_id
        )
        n_samples_ouu = extra_options.pop("num_samples")
        is_minimized = extra_options.pop("is_minimized")

        return {
            "model_path_or_json": amr_path,
            "logging_step_size": self.step_size,
            "start_time": self.timespan.start,
            "end_time": self.timespan.end,
            "objfun": lambda x: objfun(x, is_minimized),
            "qoi": lambda samples: obs_nday_average_qoi(samples, self.qoi, 1),
            "risk_bound": self.risk_bound,
            "initial_guess_interventions": self.initial_guess_interventions,
            "bounds_interventions": self.bounds_interventions,
            "static_parameter_interventions": interventions,
            "inferred_parameters": inferred_parameters,
            "n_samples_ouu": n_samples_ouu,
            **extra_options,
        }

    class Config:
        extra = Extra.forbid
        # use_enum_values = True
