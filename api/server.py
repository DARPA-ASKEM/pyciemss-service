from __future__ import annotations

import logging
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

from models import (
    Status,
    JobResponse,
    CalibratePostRequest,
    SimulatePostRequest,
    EnsembleSimulatePostRequest,
    EnsembleCalibratePostRequest,
    StatusSimulationIdGetResponse,
)


logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

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


@app.get("/ping")
def get_ping():
    """
    Retrieve the status of a simulation
    """
    return {"status": "ok"}

@app.get("/status/{simulation_id}", response_model=StatusSimulationIdGetResponse)
def get_status(simulation_id: str) -> StatusSimulationIdGetResponse:
    """
    Retrieve the status of a simulation
    """
    from utils import fetch_job_status

    status = fetch_job_status(simulation_id)
    logging.info(status)
    if not isinstance(status, str):
        return status

    return {"status": Status.from_rq(status)}

import logging
@app.post("/simulate", response_model=JobResponse)
def simulate_model(body: SimulatePostRequest) -> JobResponse:
    """
    Perform a simulation
    """
    from utils import create_job
    # Parse request body
    engine = str(body.engine.value).lower()
    model_config_id = body.model_config_id
    username = body.username
    start = body.timespan.start
    end = body.timespan.end
    interventions = [
        (intervention.timestep, intervention.name, intervention.value) for intervention in body.interventions 
    ]
        

    operation_name = "operations.simulate"
    options = {
        "engine": engine,
        "username": username,
        "model_config_id": model_config_id,
        "start": start,
        "end": end,
        "extra": body.extra.dict(),
        "visual_options": True,
        "interventions": interventions
    }

    resp = create_job(operation_name=operation_name, options=options)

    if len(interventions) > 0:
        logging.info(f"{resp['id']} used interventions: {interventions}")
    response = {"simulation_id": resp["id"]}

    return response


@app.post("/calibrate", response_model=JobResponse)
def calibrate_model(body: CalibratePostRequest) -> JobResponse:
    """
    Calibrate a model
    """
    from utils import create_job

    # Parse request body
    logging.info(body)
    engine = str(body.engine).lower()
    username = body.username
    model_config_id = body.model_config_id
    dataset = body.dataset
    start = body.timespan.start
    end = body.timespan.end
    extra = body.extra.dict()

    operation_name = "operations.calibrate_then_simulate"
    options = {
        "engine": engine,
        "username": username,
        "model_config_id": model_config_id,
        "start": start,
        "end": end,
        "dataset": dataset.dict(),
        "extra": extra,
        "visual_options": True,
    }

    resp = create_job(operation_name=operation_name, options=options)

    response = {"simulation_id": resp["id"]}

    return response


@app.post("/ensemble-simulate", response_model=JobResponse)
def create_simulate_ensemble(body: EnsembleSimulatePostRequest) -> JobResponse:
    """
    Perform ensemble simulate
    """
    from utils import create_job

    # Parse request body
    engine = str(body.engine).lower()
    model_configs = [config.dict() for config in body.model_configs]
    start = body.timespan.start
    end = body.timespan.end
    username = body.username
    extra = body.extra.dict()


    operation_name = "operations.ensemble_simulate"
    options = {
        "engine": engine,
        "model_configs": model_configs,
        "start": start,
        "end": end,
        "username": username,
        "extra": extra,
        "visual_options": True
    }

    resp = create_job(operation_name=operation_name, options=options)

    response = {"simulation_id": resp["id"]}

    return response


@app.post("/ensemble-calibrate", response_model=JobResponse)
def create_calibrate_ensemble(body: EnsembleCalibratePostRequest) -> JobResponse:
    """
    Perform ensemble simulate
    """
    from utils import create_job

    # Parse request body
    engine = str(body.engine).lower()
    username = body.username
    dataset = body.dataset.dict()
    model_configs = [config.dict() for config in body.model_configs]
    start = body.timespan.start
    end = body.timespan.end
    extra = body.extra.dict()


    operation_name = "operations.ensemble_calibrate"
    options = {
        "engine": engine,
        "model_configs": model_configs,
        "dataset": dataset, 
        "start": start,
        "end": end,
        "username": username,
        "extra": extra,
        "visual_options": True
    }

    resp = create_job(operation_name=operation_name, options=options)

    response = {"simulation_id": resp["id"]}

    return response


