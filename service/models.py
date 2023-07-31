from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Timespan(BaseModel):
    start: int = Field(..., example=0)
    end: int = Field(..., example=90)


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
            "finished": "complete"
        }
        return Status(rq_status_to_tds_status[rq_status])


class ModelConfig(BaseModel):
    id: str = Field(..., example="cd339570-047d-11ee-be55")
    solution_mappings: dict[str, str] = Field(..., example={"Infected": "Cases", "Hospitalizations": "hospitalized_population"})
    weight: float = Field(..., example="cd339570-047d-11ee-be55") 


class Dataset(BaseModel):
    id: str = Field(None, example="cd339570-047d-11ee-be55")
    filename: str = Field(None, example="dataset.csv")
    mappings: Dict[str, str] = Field(
        default_factory=dict,
        description="Mappings from the dataset column names to the model names they should be replaced with.",
        example={'postive_tests': 'infected'},
    )

class InterventionObject(BaseModel):
    timestep: float
    name: str
    value: float

######################### Base operation request ############
class OperationRequest(BaseModel):
    engine: str = Field("ciemss", example="ciemss")
    username: str = Field("not_provided", example="not_provided")

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


class SimulatePostRequest(OperationRequest):
    model_config_id: str = Field(..., example="ba8da8d4-047d-11ee-be56")
    timespan: Timespan
    interventions: List[InterventionObject] = Field(default_factory=list, example=[{"timestep":1,"name":"beta","value":.4}])
    extra: SimulateExtra = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )


######################### `calibrate` Operation ############
class CalibrateExtra(BaseModel):
    num_samples: int = Field(
        100,  description="number of samples for a CIEMSS simulation", example=100
    )
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
    method: str = Field(
        "dopri5", description="Optional field for CIEMSS calibration", example="dopri5"
    )


class CalibratePostRequest(OperationRequest):
    model_config_id: str = Field(..., example="c1cd941a-047d-11ee-be56")
    dataset: Dataset = None
    timespan: Optional[Timespan] = None
    extra: CalibrateExtra = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )


######################### `ensemble-simulate` Operation ############
class EnsembleSimulateExtra(BaseModel):
    num_samples: int = Field(
        100, description="number of samples for a CIEMSS simulation", example=100
    )


class EnsembleSimulatePostRequest(OperationRequest):
    model_configs: List[ModelConfig] = Field(
        [],
        example=[],
    )
    timespan: Timespan

    extra: EnsembleSimulateExtra = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )

######################### `ensemble-calibrate` Operation ############
class EnsembleCalibrateExtra(BaseModel):
    num_samples: int = Field(
        100, description="number of samples for a CIEMSS simulation", example=100
    )

    total_population: int = Field(
        1000, description="total population", example=1000
    )

    num_iterations: int = Field(
        350, description="number of iterations", example=1000
    )

    time_unit: int = Field(
        "days", description="units in numbers of days", example="days"
    )

class EnsembleCalibratePostRequest(OperationRequest):
    username: str = Field("not_provided", example="not_provided")
    model_configs: List[ModelConfig] = Field(
        [],
        example=[],
    )
    timespan: Timespan
    dataset: Dataset
    extra: EnsembleCalibrateExtra = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )

######################### API Response ############
class JobResponse(BaseModel):
    simulation_id: Optional[str] = Field(
        None,
        description="Simulation created successfully",
        example="fc5d80e4-0483-11ee-be56",
    )


class StatusSimulationIdGetResponse(BaseModel):
    status: Optional[Status] = None
