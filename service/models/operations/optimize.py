from __future__ import annotations

from enum import Enum
from typing import ClassVar, Dict, List, Optional

import numpy as np
import torch
from pydantic import BaseModel, Field, Extra


from models.base import OperationRequest, Timespan, InterventionObject
from models.converters import convert_to_static_interventions
from utils.tds import fetch_model, fetch_inferred_parameters


class QOIMethod(Enum):
    obs_nday_average = "obs_nday_average"


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
    dataQoI = samples[contexts[0]].detach().numpy()

    return np.mean(dataQoI[:, -ndays:], axis=1)


qoi_implementations = {QOIMethod.obs_nday_average: obs_nday_average_qoi}


class OptimizeExtra(BaseModel):
    num_samples: int = Field(
        100, description="number of samples for a CIEMSS simulation", example=100
    )
    inferred_parameters: Optional[str] = Field(
        None,
        description="id from a previous calibration",
        example=None,
    )


class Optimize(OperationRequest):
    pyciemss_lib_function: ClassVar[str] = "optimize"
    model_config_id: str = Field(..., example="ba8da8d4-047d-11ee-be56")
    timespan: Timespan = Timespan(start=0, end=90)
    interventions: List[InterventionObject] = Field(
        default_factory=list, example=[{"timestep": 1, "name": "beta", "value": 0.4}]
    )
    step_size: float = 1.0
    qoi: QOIMethod
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

        interventions = convert_to_static_interventions(self.interventions)

        extra_options = self.extra.dict()
        inferred_parameters = fetch_inferred_parameters(
            extra_options.pop("inferred_parameters"), job_id
        )

        return {
            "model_path_or_json": amr_path,
            "logging_step_size": self.step_size,
            "start_time": self.timespan.start,
            "end_time": self.timespan.end,
            "qoi": qoi_implementations[self.qoi],
            "risk_bound": self.risk_bound,
            "initial_guess_interventions": self.initial_guess_interventions,
            "bounds_interventions": self.bounds_interventions,
            "static_parameter_interventions": interventions,
            "inferred_parameters": inferred_parameters,
            **extra_options,
        }

    class Config:
        extra = Extra.forbid
