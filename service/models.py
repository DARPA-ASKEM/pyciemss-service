from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field



from utils.tds import fetch_dataset, fetch_model
from utils.rabbitmq import gen_rabbitmq_hook
from settings import settings

TDS_CONFIGURATIONS = "/model_configurations/"
TDS_SIMULATIONS = "/simulations/"
TDS_URL = settings.TDS_URL

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


class SimulatePostRequest(OperationRequest):
    pyciemss_lib_function: ClassVar[str] = "load_and_sample_petri_model"
    model_config_id: str = Field(..., example="ba8da8d4-047d-11ee-be56")
    timespan: Timespan
    interventions: List[InterventionObject] = Field(default_factory=list, example=[{"timestep":1,"name":"beta","value":.4}])
    extra: SimulateExtra = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )


    def gen_pyciemss_args(self, job_id):
        # Get model from TDS
        amr_path = fetch_model(self.model_config_id, TDS_URL, TDS_CONFIGURATIONS, job_id)
    
        interventions = []
        if len(self.interventions) > 0:
            interventions = [
                (intervention.timestep, intervention.name, intervention.value) 
                for intervention in self.interventions 
            ]

        # Generate timepoints
        time_count = self.timespan.end - self.timespan.start
        timepoints=[step for step in range(1,time_count+1)]

        return {
            "petri_model_or_path": amr_path, 
            "timepoints": timepoints, 
            "interventions": interventions,
            "visual_options": True, 
            **self.extra.dict()
        }
        

    def run_sciml_operation(self, job_id, julia_context):
        amr_path = fetch_model(self.model_config_id, TDS_URL, TDS_CONFIGURATIONS, job_id)
        with open(amr_path, "r") as file:
            amr = file.read()
        result = jl.pytable(jl.simulate(amr, self.timespan.start, self.timespan.end))
        return {"data": result}


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
    pyciemss_lib_function: ClassVar[str] = "load_and_calibrate_and_sample_petri_model"
    model_config_id: str = Field(..., example="c1cd941a-047d-11ee-be56")
    dataset: Dataset = None
    timespan: Optional[Timespan] = None
    extra: CalibrateExtra = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )
    

    def gen_pyciemss_args(self, job_id):
        amr_path = fetch_model(self.model_config_id, TDS_URL, TDS_CONFIGURATIONS, job_id)
    
        # Generate timepoints
        time_count = self.timespan.end - self.timespan.start
        timepoints=[step for step in range(1, time_count+1)]

        dataset_path = fetch_dataset(self.dataset.dict(), TDS_URL, job_id)

        return {
            "petri_model_or_path": amr_path,
            "timepoints": timepoints,
            "data_path": dataset_path,
            "progress_hook": gen_rabbitmq_hook(job_id),
            "visual_options": True,
            **self.extra.dict()
        }


######################### `ensemble-simulate` Operation ############
class EnsembleSimulateExtra(BaseModel):
    num_samples: int = Field(
        100, description="number of samples for a CIEMSS simulation", example=100
    )


class EnsembleSimulatePostRequest(OperationRequest):
    pyciemss_lib_function: ClassVar[str] = "load_and_sample_petri_ensemble"
    model_configs: List[ModelConfig] = Field(
        [],
        example=[],
    )
    timespan: Timespan

    extra: EnsembleSimulateExtra = Field(
        None,
        description="optional extra system specific arguments for advanced use cases",
    )

    
    def gen_pyciemss_args(self, job_id):
        weights = [config.weight for config in self.model_configs]
        solution_mappings = [config.solution_mappings for config in self.model_configs]
        amr_paths = [fetch_model(config.id, TDS_URL, TDS_CONFIGURATIONS, job_id) for config in self.model_configs]
    
        # Generate timepoints
        time_count = self.timespan.end - self.timespan.start
        timepoints=[step for step in range(1,time_count+1)]

        
        return {
            "petri_model_or_paths": amr_paths,
            "weights": weights,
            "solution_mappings": solution_mappings,
            "timepoints": timepoints,
            "visual_options": True,
            **self.extra.dict()
        }

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
    pyciemss_lib_function: ClassVar[str] = "load_and_calibrate_and_sample_ensemble_model"
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

    
    def gen_pyciemss_args(self, job_id):
        weights = [config.weight for config in self.model_configs]
        solution_mappings = [config.solution_mappings for config in self.model_configs]
        amr_paths = [fetch_model(config.id, TDS_URL, TDS_CONFIGURATIONS, job_id) for config in self.model_configs]

        dataset_path = fetch_dataset(self.dataset.dict(), TDS_URL, job_id)

        # Generate timepoints
        time_count = self.timespan.end - self.timespan.start
        timepoints=[step for step in range(1, time_count+1)]

        output = load_and_calibrate_and_sample_ensemble_model(
            petri_model_or_paths=amr_paths,
            weights=weights,
            solution_mappings=solution_mappings,
            timepoints=timepoints,
            data_path=dataset_path,
            visual_options=True,
            **self.extra.dict()
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
