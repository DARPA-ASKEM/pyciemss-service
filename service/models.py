from __future__ import annotations
import socket  # noqa: F401
import logging  # noqa: F401

from enum import Enum
from typing import ClassVar, Dict, List, Optional
from pydantic import BaseModel, Field, Extra

from pika.exceptions import AMQPConnectionError

# TODO: Do not use Torch in PyCIEMSS Library interface
import torch


from utils.convert import convert_to_static_interventions, convert_to_solution_mapping
from utils.rabbitmq import gen_rabbitmq_hook  # noqa: F401
from utils.tds import fetch_dataset, fetch_model, fetch_inferred_parameters
from settings import settings

TDS_CONFIGURATIONS = "/model-configurations/"
TDS_SIMULATIONS = "/simulations/"
TDS_URL = settings.TDS_URL


class Timespan(BaseModel):
    start: float = Field(..., example=0)
    end: float = Field(..., example=90)


class Status(Enum):
    cancelled = "cancelled"
    complete = "complete"
    error = "error"
    queued = "queued"
    running = "running"
    failed = "failed"
    started = "started"
    finished = "finished"

    @staticmethod
    def from_rq(rq_status):
        rq_status_to_tds_status = {
            "canceled": "cancelled",
            "complete": "complete",
            "error": "error",
            "queued": "queued",
            "running": "running",
            "failed": "failed",
            "started": "running",
            "finished": "complete",
        }
        return Status(rq_status_to_tds_status[rq_status])


class ModelConfig(BaseModel):
    id: str = Field(..., example="cd339570-047d-11ee-be55")
    solution_mappings: dict[str, str] = Field(
        ...,
        example={"Infected": "Cases", "Hospitalizations": "hospitalized_population"},
    )
    weight: float = Field(..., example="cd339570-047d-11ee-be55")


class Dataset(BaseModel):
    id: str = Field(None, example="cd339570-047d-11ee-be55")
    filename: str = Field(None, example="dataset.csv")
    mappings: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Mappings from the dataset column names to "
            "the model names they should be replaced with."
        ),
        example={"postive_tests": "infected"},
    )


class InterventionObject(BaseModel):
    timestep: float
    name: str
    value: float


class InterventionSelection(BaseModel):
    timestep: float
    name: str


class QuantityOfInterest(BaseModel):
    function: str
    state: str
    arg: int  # TODO: Make this a list of args?


######################### Base operation request ############
class OperationRequest(BaseModel):
    pyciemss_lib_function: ClassVar[str] = ""
    engine: str = Field("ciemss", example="ciemss")
    username: str = Field("not_provided", example="not_provided")

    def gen_pyciemss_args(self, job_id):
        raise NotImplementedError("PyCIEMSS cannot handle this operation")

    def run_sciml_operation(self, job_id, julia_context):
        raise NotImplementedError("SciML cannot handle this operation")

    # @field_validator("engine")
    # def must_be_ciemss(cls, engine_choice):
    #     if engine_choice != "ciemss":
    #         raise ValueError("The chosen engine is NOT 'ciemss'")
    #     return engine_choice


######################### `simulate` Operation ############
class SimulateExtra(BaseModel):
    num_samples: int = Field(
        100, description="number of samples for a CIEMSS simulation", example=100
    )
    inferred_parameters: Optional[str] = Field(
        None,
        description="id from a previous calibration",
        example=None,
    )


class Simulate(OperationRequest):
    pyciemss_lib_function: ClassVar[str] = "sample"
    model_config_id: str = Field(..., example="ba8da8d4-047d-11ee-be56")
    timespan: Timespan = Timespan(start=0, end=90)
    interventions: List[InterventionObject] = Field(
        default_factory=list, example=[{"timestep": 1, "name": "beta", "value": 0.4}]
    )
    step_size: float = 1.0
    extra: SimulateExtra = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )

    def gen_pyciemss_args(self, job_id):
        # Get model from TDS
        amr_path = fetch_model(
            self.model_config_id, TDS_URL, TDS_CONFIGURATIONS, job_id
        )

        interventions = convert_to_static_interventions(self.interventions)

        extra_options = self.extra.dict()
        inferred_parameters = fetch_inferred_parameters(
            extra_options.pop("inferred_parameters"), TDS_URL, job_id
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

    def run_sciml_operation(self, job_id, julia_context):
        amr_path = fetch_model(
            self.model_config_id, TDS_URL, TDS_CONFIGURATIONS, job_id
        )
        with open(amr_path, "r") as file:
            amr = file.read()
        result = julia_context.simulate(amr, self.timespan.start, self.timespan.end)
        return {"data": julia_context.pytable(result)}

    class Config:
        extra = Extra.forbid


######################### `calibrate` Operation ############
class CalibrateExtra(BaseModel):
    # start_state: Optional[dict[str,float]]
    # pseudocount: float = Field(
    #     1.0, description="Optional field for CIEMSS calibration", example=1.0
    # )
    start_time: float = Field(
        -1e-10, description="Optional field for CIEMSS calibration", example=-1e-10
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
    extra: CalibrateExtra = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )

    def gen_pyciemss_args(self, job_id):
        amr_path = fetch_model(
            self.model_config_id, TDS_URL, TDS_CONFIGURATIONS, job_id
        )

        dataset_path = fetch_dataset(self.dataset.dict(), TDS_URL, job_id)

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
            "progress_hook": hook,
            # "visual_options": True,
            **self.extra.dict(),
        }

    class Config:
        extra = Extra.forbid


######################### `ensemble-simulate` Operation ############
class EnsembleSimulateExtra(BaseModel):
    num_samples: int = Field(
        100, description="number of samples for a CIEMSS simulation", example=100
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
        amr_paths = [
            fetch_model(config.id, TDS_URL, TDS_CONFIGURATIONS, job_id)
            for config in self.model_configs
        ]

        return {
            "model_paths_or_jsons": amr_paths,
            "solution_mappings": solution_mappings,
            "start_time": self.timespan.start,
            "end_time": self.timespan.end,
            "logging_step_size": self.step_size,
            "dirichlet_alpha": weights,
            # "visual_options": True,
            **self.extra.dict(),
        }

    class Config:
        extra = Extra.forbid


######################### `ensemble-calibrate` Operation ############
# class EnsembleCalibrateExtra(BaseModel):
#     num_samples: int = Field(
#         100, description="number of samples for a CIEMSS simulation", example=100
#     )

#     total_population: int = Field(1000, description="total population", example=1000)

#     num_iterations: int = Field(350, description="number of iterations", example=1000)

#     time_unit: int = Field(
#         "days", description="units in numbers of days", example="days"
#     )


# class EnsembleCalibrate(OperationRequest):
#     pyciemss_lib_function: ClassVar[
#         str
#     ] = "load_and_calibrate_and_sample_ensemble_model"
#     username: str = Field("not_provided", example="not_provided")
#     model_configs: List[ModelConfig] = Field(
#         [],
#         example=[],
#     )
#     timespan: Timespan = Timespan(start=0, end=90)
#     dataset: Dataset
#     extra: EnsembleCalibrateExtra = Field(
#         None,
#         description="optional extra system specific arguments for advanced use cases",
#     )

#     def gen_pyciemss_args(self, job_id):
#         weights = [config.weight for config in self.model_configs]
#         solution_mappings = [config.solution_mappings for config
#               in self.model_configs]
#         amr_paths = [
#             fetch_model(config.id, TDS_URL, TDS_CONFIGURATIONS, job_id)
#             for config in self.model_configs
#         ]

#         dataset_path = fetch_dataset(self.dataset.dict(), TDS_URL, job_id)

#         # Generate timepoints
#         time_count = self.timespan.end - self.timespan.start
#         timepoints = [step for step in range(1, time_count + 1)]

#         return {
#             "petri_model_or_paths": amr_paths,
#             "weights": weights,
#             "solution_mappings": solution_mappings,
#             "timepoints": timepoints,
#             "data_path": dataset_path,
#             "visual_options": True,
#             **self.extra.dict(),
#         }

#     class Config:
#         extra = Extra.forbid


######################### API Response ############
class JobResponse(BaseModel):
    simulation_id: Optional[str] = Field(
        None,
        description="Simulation created successfully",
        example="fc5d80e4-0483-11ee-be56",
    )


class StatusSimulationIdGetResponse(BaseModel):
    status: Optional[Status] = None
