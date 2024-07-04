from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional
from enum import Enum

import numpy as np
import torch
from pydantic import BaseModel, Field, Extra
from models.base import OperationRequest, Timespan
from pyciemss.integration_utils.intervention_builder import (
    param_value_objective,
    start_time_objective,
)

from pyciemss.ouu.qoi import obs_nday_average_qoi, obs_max_qoi
from models.converters import fetch_and_convert_static_interventions
from utils.tds import fetch_model, fetch_inferred_parameters


class QOIMethod(str, Enum):
    day_average = "day_average"
    max = "max"


class QOI(BaseModel):
    method: QOIMethod = QOIMethod.day_average
    contexts: List[str] = []

    def gen_call(self):
        contexts = [context + "_state" for context in self.contexts]
        qoi_map = {
            QOIMethod.day_average: lambda samples: obs_nday_average_qoi(
                samples, contexts, 1
            ),
            QOIMethod.max: lambda samples: obs_max_qoi(samples, contexts),
        }
        return qoi_map[self.method]


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
    maxfeval: int = 25
    is_minimized: bool = True
    alpha: float = 0.95
    solver_method: str = "dopri5"
    solver_options: Dict[str, Any] = {}


class Optimize(OperationRequest):
    pyciemss_lib_function: ClassVar[str] = "optimize"
    model_config_id: str = Field(..., example="ba8da8d4-047d-11ee-be56")
    timespan: Timespan = Timespan(start=0, end=90)
    policy_interventions: InterventionObjective
    step_size: float = 1.0
    qoi: QOI
    risk_bound: float
    initial_guess_interventions: List[float]
    bounds_interventions: List[List[float]]
    extra: OptimizeExtra = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )
    policy_intervention_id: str = Field(None, example="ba8da8d4-047d-11ee-be56")

    def gen_pyciemss_args(self, job_id):
        # Get model from TDS
        amr_path = fetch_model(self.model_config_id, job_id)
        static_interventions = fetch_and_convert_static_interventions(
            self.policy_intervention_id
        )

        intervention_type = self.policy_interventions.selection
        if intervention_type == "param_value":
            assert self.policy_interventions.start_time is not None
            start_time = [
                torch.tensor(time) for time in self.policy_interventions.start_time
            ]
            param_value = [None] * len(self.policy_interventions.param_names)

            policy_interventions = param_value_objective(
                start_time=start_time,
                param_name=self.policy_interventions.param_names,
                param_value=param_value,
            )
        else:
            assert self.policy_interventions.param_values is not None
            param_value = [
                torch.tensor(value) for value in self.policy_interventions.param_values
            ]
            policy_interventions = start_time_objective(
                param_name=self.policy_interventions.param_names,
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
            "qoi": self.qoi.gen_call(),
            "risk_bound": self.risk_bound,
            "initial_guess_interventions": self.initial_guess_interventions,
            "bounds_interventions": self.bounds_interventions,
            "static_parameter_interventions": policy_interventions,
            "fixed_static_parameter_interventions": static_interventions,
            "inferred_parameters": inferred_parameters,
            "n_samples_ouu": n_samples_ouu,
            **extra_options,
        }

    class Config:
        extra = Extra.forbid
        # use_enum_values = True
