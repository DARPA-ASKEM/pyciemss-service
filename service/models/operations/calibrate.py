from __future__ import annotations
import socket
import logging

from typing import ClassVar, Optional, List
from pydantic import BaseModel, Field, Extra

from pika.exceptions import AMQPConnectionError


from models.base import Dataset, OperationRequest, Timespan, InterventionObject
from models.converters import convert_to_static_interventions
from utils.rabbitmq import gen_rabbitmq_hook
from utils.tds import fetch_dataset, fetch_model


class CalibrateExtra(BaseModel):
    # start_state: Optional[dict[str,float]]
    # pseudocount: float = Field(
    #     1.0, description="Optional field for CIEMSS calibration", example=1.0
    # )
    start_time: float = Field(
        0, description="Optional field for CIEMSS calibration", example=0
    )
    num_iterations: int = Field(
        1000, description="Optional field for CIEMSS calibration", example=1000
    )
    lr: float = Field(
        0.03, description="Optional field for CIEMSS calibration", example=0.03
    )
    verbose: bool = Field(
        False, description="Optional field for CIEMSS calibration", example=False
    )
    num_particles: int = Field(
        1, description="Optional field for CIEMSS calibration", example=1
    )
    # autoguide: pyro.infer.autoguide.AutoLowRankMultivariateNormal
    solver_method: str = Field(
        "dopri5", description="Optional field for CIEMSS calibration", example="dopri5"
    )


class Calibrate(OperationRequest):
    pyciemss_lib_function: ClassVar[str] = "calibrate"
    model_config_id: str = Field(..., example="c1cd941a-047d-11ee-be56")
    dataset: Dataset = None
    timespan: Optional[Timespan] = None
    interventions: List[InterventionObject] = Field(
        default_factory=list, example=[{"timestep": 1, "name": "beta", "value": 0.4}]
    )

    extra: CalibrateExtra = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )

    def gen_pyciemss_args(self, job_id):
        amr_path = fetch_model(self.model_config_id, job_id)

        dataset_path = fetch_dataset(self.dataset.dict(), job_id)

        interventions = convert_to_static_interventions(self.interventions)

        # TODO: Test RabbitMQ
        try:
            hook = gen_rabbitmq_hook(job_id)
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
            "model_path_or_json": amr_path,
            "start_time": self.timespan.start,
            # TODO: Is this intentionally missing from `calibrate`?
            # "end_time": self.timespan.end,
            "data_path": dataset_path,
            "static_parameter_interventions": interventions,
            "progress_hook": hook,
            # "visual_options": True,
            **self.extra.dict(),
        }

    class Config:
        extra = Extra.forbid
