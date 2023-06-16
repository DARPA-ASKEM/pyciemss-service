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


@router.post("/calibrate", response_model=CalibratePostResponse)
def calibrate_model(body: CalibratePostRequest) -> CalibratePostResponse:
    """
    Calibrate a model (SciML only)
    """
    from utils import job

    # Parse request body
    print(body)
    engine = str(body.engine).lower()
    model_id = body.model_config_id
    num_samples = body.extra.num_samples
    dataset = body.dataset
    start_timestamp = body.timespan.start_epoch
    end_timestamp = body.timespan.end_epoch
    mappings = body.mappings
    extra = body.extra

    print(model_id)

    job_string = "ciemss_processor.calibrate_and_simulate_model"
    options = {
        "engine": engine,
        "model_id": model_id,
        "start_epoch": start_timestamp,
        "end_epoch": end_timestamp,
        "num_samples": num_samples,
        "dataset": dataset,
        "mappings": mappings,
        "extra": extra,
    }

    resp = job(model_id=model_id, job_string=job_string, options=options)

    response = {"simulation_id": resp["id"]}

    return response


@router.post("/ensemble", response_model=EnsemblePostResponse)
def create_ensemble(body: EnsemblePostRequest) -> EnsemblePostResponse:
    """
    Perform an ensemble simulation
    """
    pass


@router.post("/simulate", response_model=SimulatePostResponse)
def simulate_model(body: SimulatePostRequest) -> SimulatePostResponse:
    """
    Perform a simulation
    """
    from utils import job

    # Parse request body
    engine = str(body.engine.value).lower()
    model_id = body.model_config_id
    num_samples = body.extra.num_samples
    start_timestamp = body.timespan.start
    end_timestamp = body.timespan.end

    job_string = "ciemss_processor.simulate_model"
    options = {
        "engine": engine,
        "model_id": model_id,
        "start": start_timestamp,
        "end": end_timestamp,
        "num_samples": num_samples,
    }

    resp = job(model_id=model_id, job_string=job_string, options=options)

    response = {"simulation_id": resp["id"]}

    return response


@router.get("/status/{simulation_id}", response_model=StatusSimulationIdGetResponse)
def get_status(simulation_id: str) -> StatusSimulationIdGetResponse:
    """
    Retrieve the status of a simulation
    """
    from utils import fetch_job_status

    return {"status": fetch_job_status(simulation_id)}
