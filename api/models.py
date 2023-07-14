from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, Extra as ExtraEnum


class Engine(Enum):
    sciml = "sciml"
    ciemss = "ciemss"


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
            "cancelled": "cancelled",
            "complete": "complete",
            "error": "error",
            "queued": "queued",
            "running": "running",
            "failed": "failed",
            "started": "running",
            "finished": "complete"
        }
        return Status(rq_status_to_tds_status[rq_status])


class SimulateExtra(BaseModel):
    class Config:
        extra = ExtraEnum.allow

    num_samples: int = Field(
        100, description="number of samples for a CIEMSS simulation", example=100
    )


class CalibrateExtra(BaseModel):
    class Config:
        extra = ExtraEnum.allow

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


class Dataset(BaseModel):
    id: str = Field(None, example="cd339570-047d-11ee-be55")
    filename: str = Field(None, example="dataset.csv")
    mappings: Optional[Dict[str, str]] = Field(
        None,
        description="Mappings from the dataset column names to the model names they should be replaced with.",
        example={'postive_tests': 'infected'},
    )

class InterventionObject(BaseModel):
    timestep: float
    name: str
    value: float

class SimulatePostRequest(BaseModel):
    engine: Engine = Field(..., example="ciemss")
    model_config_id: str = Field(..., example="ba8da8d4-047d-11ee-be56")
    timespan: Timespan
    interventions: Optional[List[InterventionObject]] = Field(None, example=[{"timestep":1,"name":"beta","value":.4}])
    extra: SimulateExtra = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )


class CalibratePostRequest(BaseModel):
    engine: Engine = Field(..., example="ciemss")
    model_config_id: str = Field(..., example="c1cd941a-047d-11ee-be56")
    dataset: Dataset = None
    timespan: Optional[Timespan] = None
    extra: CalibrateExtra = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )


class EnsemblePostRequest(BaseModel):
    engine: Engine = Field(..., example="ciemss")
    model_configuration_ids: Optional[List[str]] = Field(
        None,
        example=[
            "ba8da8d4-047d-11ee-be56",
            "c1cd941a-047d-11ee-be56",
            "c4b9f88a-047d-11ee-be56",
        ],
    )
    timespan: Timespan
    extra: Optional[Dict[str, Any]] = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )

class JobResponse(BaseModel):
    simulation_id: Optional[str] = Field(
        None,
        description="Simulation created successfully",
        example="fc5d80e4-0483-11ee-be56",
    )


class StatusSimulationIdGetResponse(BaseModel):
    status: Optional[Status] = None
