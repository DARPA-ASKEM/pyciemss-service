from __future__ import annotations
import json
import socket
import logging

from typing import ClassVar, Optional
from pydantic import BaseModel, Field, Extra

from pika.exceptions import AMQPConnectionError


from models.base import Dataset, OperationRequest, Timespan
from models.converters import (
    fetch_and_convert_static_interventions,
    fetch_and_convert_dynamic_interventions,
)
from utils.rabbitmq import gen_calibrate_rabbitmq_hook
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
    # https://github.com/ciemss/pyciemss/blob/main/pyciemss/integration_utils/interface_checks.py
    solver_step_size: float = Field(
        None,
        description="Step size required if solver method is euler.",
        example=1.0,
    )


class Calibrate(OperationRequest):
    pyciemss_lib_function: ClassVar[str] = "calibrate"
    model_config_id: str = Field(..., example="c1cd941a-047d-11ee-be56")
    dataset: Dataset = None
    timespan: Optional[Timespan] = None
    policy_intervention_id: str = Field(None, example="ba8da8d4-047d-11ee-be56")
    extra: CalibrateExtra = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )

    def gen_pyciemss_args(self, job_id):
        amr_path = fetch_model(self.model_config_id, job_id)

        with open(amr_path, "r") as f:
            model_config_json = json.load(f)

        dataset_path = fetch_dataset(self.dataset.dict(), job_id)

        (
            static_param_interventions,
            static_state_interventions,
        ) = fetch_and_convert_static_interventions(self.policy_intervention_id, model_config_json, job_id)

        (
            dynamic_param_interventions,
            dynamic_state_interventions,
        ) = fetch_and_convert_dynamic_interventions(self.policy_intervention_id, job_id)

        # TODO: Test RabbitMQ
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

        extra_options = self.extra.dict()
        solver_options = {}
        step_size = extra_options.pop(
            "solver_step_size"
        )  # Need to pop this out of extra.
        solver_method = extra_options.pop("solver_method")
        if step_size is not None and solver_method == "euler":
            solver_options["step_size"] = step_size

        return {
            "model_path_or_json": amr_path,
            "start_time": self.timespan.start,
            # TODO: Is this intentionally missing from `calibrate`?
            # "end_time": self.timespan.end,
            "data_path": dataset_path,
            "static_parameter_interventions": static_param_interventions,
            "static_state_interventions": static_state_interventions,
            "dynamic_parameter_interventions": dynamic_param_interventions,
            "dynamic_state_interventions": dynamic_state_interventions,
            "progress_hook": hook,
            "solver_method": solver_method,
            "solver_options": solver_options,
            # "visual_options": True,
            **extra_options,
        }

    class Config:
        extra = Extra.forbid
