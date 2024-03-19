from __future__ import annotations

from typing import ClassVar, List, Optional

from pydantic import BaseModel, Field, Extra
import torch  # TODO: Do not use Torch in PyCIEMSS Library interface

from models.base import OperationRequest, Timespan, ModelConfig
from models.converters import convert_to_solution_mapping
from utils.tds import fetch_model, fetch_inferred_parameters


class EnsembleSimulateExtra(BaseModel):
    num_samples: int = Field(
        100, description="number of samples for a CIEMSS simulation", example=100
    )
    inferred_parameters: Optional[str] = Field(
        None,
        description="id from a previous calibration",
        example=None,
    )


class EnsembleSimulate(OperationRequest):
    pyciemss_lib_function: ClassVar[str] = "ensemble_sample"
    model_configs: List[ModelConfig] = Field(
        [],
        example=[],
    )
    timespan: Timespan

    step_size: float = 1.0

    extra: EnsembleSimulateExtra = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )

    def gen_pyciemss_args(self, job_id):
        weights = torch.tensor([config.weight for config in self.model_configs])
        solution_mappings = [
            convert_to_solution_mapping(config) for config in self.model_configs
        ]
        amr_paths = [fetch_model(config.id, job_id) for config in self.model_configs]

        extra_options = self.extra.dict()
        inferred_parameters = fetch_inferred_parameters(
            extra_options.pop("inferred_parameters"), job_id
        )

        return {
            "model_paths_or_jsons": amr_paths,
            "solution_mappings": solution_mappings,
            "start_time": self.timespan.start,
            "end_time": self.timespan.end,
            "logging_step_size": self.step_size,
            "dirichlet_alpha": weights,
            "inferred_parameters": inferred_parameters,
            # "visual_options": True,
            **extra_options,
        }

    class Config:
        extra = Extra.forbid
