from __future__ import annotations

from fastapi import APIRouter

from validation.models import (
    CalibratePostRequest,
    CalibratePostResponse,
    EnsemblePostRequest,
    EnsemblePostResponse,
    SimulatePostRequest,
    SimulatePostResponse,
    StatusSimulationIdGetResponse,
)

router = APIRouter()


@router.post('/calibrate', response_model=CalibratePostResponse)
def calibrate_model(body: CalibratePostRequest) -> CalibratePostResponse:
    """
    Calibrate a model (SciML only)
    """
    pass


@router.post('/ensemble', response_model=EnsemblePostResponse)
def create_ensemble(body: EnsemblePostRequest) -> EnsemblePostResponse:
    """
    Perform an ensemble simulation
    """
    pass


@router.post('/simulate', response_model=SimulatePostResponse)
def simulate_model(body: SimulatePostRequest) -> SimulatePostResponse:
    """
    Perform a simulation
    """
    from utils import job

    model_id = body.get("model_config_id")
    num_samples = body.get("num_samples")
    start_timestamp = body.get("timespan").get("start_epoch")
    end_timestamp = body.get("timespan").get("end_epoch")

    job_string = "ciemss_processor.simulate_model"
    options = {"start_timestamp": start_timestamp,
               "end_timestamp": end_timestamp,
               "num_samples": num_samples}

    resp = job(uuid=model_id, job_string=job_string, options=options)

    return resp



@router.get('/status/{simulation_id}', response_model=StatusSimulationIdGetResponse)
def get_status(simulation_id: str) -> StatusSimulationIdGetResponse:
    """
    Retrieve the status of a simulation
    """
    from utils import fetch_job_status
    
    return fetch_job_status(simulation_id)
