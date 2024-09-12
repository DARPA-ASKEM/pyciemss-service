from __future__ import annotations

from typing import ClassVar, List, Dict, Any

import socket
import logging
from pydantic import BaseModel, Field, Extra
import torch  # TODO: Do not use Torch in PyCIEMSS Library interface

from pika.exceptions import AMQPConnectionError

from models.base import Dataset, OperationRequest, Timespan, ModelConfig
from models.converters import convert_to_solution_mapping
from utils.rabbitmq import gen_calibrate_rabbitmq_hook
from utils.tds import fetch_dataset, fetch_model


class EnsembleCalibrateExtra(BaseModel):
    noise_model: str = "normal"
    noise_model_kwargs: Dict[str, Any] = {"scale": 0.1}
    solver_method: str = "dopri5"
    solver_options: Dict[str, Any] = {}
    num_iterations: int = 1000
    lr: float = 0.03
    verbose: bool = False
    num_particles: int = 1
    deterministic_learnable_parameters: List[str] = []


class EnsembleCalibrate(OperationRequest):
    pyciemss_lib_function: ClassVar[str] = "ensemble_calibrate"
    model_configs: List[ModelConfig] = Field(
        [],
        example=[],
    )
    timespan: Timespan
    dataset: Dataset = None

    step_size: float = 1.0

    extra: EnsembleCalibrateExtra = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )

    def gen_pyciemss_args(self, job_id):
        weights = torch.tensor([config.weight for config in self.model_configs])
        solution_mappings = [
            convert_to_solution_mapping(config) for config in self.model_configs
        ]
        amr_paths = [fetch_model(config.id, job_id) for config in self.model_configs]
        dataset_path = fetch_dataset(self.dataset.dict(), job_id)

        try:
            hook = gen_calibrate_rabbitmq_hook(job_id)
        except (socket.gaierror, AMQPConnectionError):
            logging.warning(
                "%s: Failed to connect to RabbitMQ. Unable to log progress", job_id
            )

            def hook(progress, _loss):
                progress = progress / 10  # TODO: Fix magnitude of progress upstream
                if progress == int(progress):
                    logging.info(f"Calibration is {progress}% complete")
                return None

        return {
            "model_paths_or_jsons": amr_paths,
            "solution_mappings": solution_mappings,
            "data_path": dataset_path,
            "start_time": self.timespan.start,
            # "end_time": self.timespan.end,
            "dirichlet_alpha": weights,
            "progress_hook": hook,
            # "visual_options": True,
            **self.extra.dict(),
        }

    class Config:
        extra = Extra.forbid
