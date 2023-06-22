from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models import (
    Status,
    JobResponse,
    CalibratePostRequest,
    EnsemblePostRequest,
    SimulatePostRequest,
    StatusSimulationIdGetResponse,
)


def build_api(*args) -> FastAPI:

    api = FastAPI(
        title="CIEMSS Service",
        description="Service for running CIEMSS simulations",
        docs_url="/",
    )
    origins = [
        "http://localhost",
        "http://localhost:8080",
    ]
    api.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return api


app = build_api()


@app.get("/status/{simulation_id}", response_model=StatusSimulationIdGetResponse)
def get_status(simulation_id: str) -> StatusSimulationIdGetResponse:
    """
    Retrieve the status of a simulation
    """
    from utils import fetch_job_status

    return {"status": Status(fetch_job_status(simulation_id))}


@app.post("/simulate", response_model=JobResponse)
def simulate_model(body: SimulatePostRequest) -> SimulatePostResponse:
    """
    Perform a simulation
    """
    from utils import job

    # Parse request body
    engine = str(body.engine.value).lower()
    model_id = body.model_config_id
    num_samples = body.extra.num_samples
    start = body.timespan.start
    end = body.timespan.end

    job_string = "operations.simulate"
    options = {
        "engine": engine,
        "model_id": model_id,
        "start": start,
        "end": end,
        "num_samples": num_samples,
    }

    resp = job(model_id=model_id, job_string=job_string, options=options)

    response = {"simulation_id": resp["id"]}

    return response


@app.post("/calibrate", response_model=JobResponse)
def calibrate_model(body: CalibratePostRequest) -> CalibratePostResponse:
    """
    Calibrate a model (SciML only)
    """
    from utils import job

    # Parse request body
    print(body)
    engine = str(body.engine).lower()
    model_id = body.model_config_id
    dataset = body.dataset
    start = body.timespan.start
    end = body.timespan.end
    extra = body.extra

    print(model_id)

    job_string = "operations.calibrate_then_simulate"
    options = {
        "engine": engine,
        "model_id": model_id,
        "start": start,
        "end": end,
        "num_samples": extra.num_samples,
        "dataset": dataset,
        "extra": extra,
    }

    resp = job(model_id=model_id, job_string=job_string, options=options)

    response = {"simulation_id": resp["id"]}

    return response


@app.post("/ensemble", response_model=JobResponse)
def create_ensemble(body: EnsemblePostRequest) -> EnsemblePostResponse:
    """
    Perform an ensemble simulation
    """
    pass


