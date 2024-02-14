from __future__ import annotations

from typing import ClassVar, List, Optional
from pydantic import BaseModel, Field, Extra


from models.base import OperationRequest, Timespan, InterventionObject
from models.converters import convert_to_static_interventions
from utils.tds import fetch_model, fetch_inferred_parameters


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
            "static_parameter_interventions": interventions,
            "inferred_parameters": inferred_parameters,
            **extra_options,
        }

    class Config:
        extra = Extra.forbid
