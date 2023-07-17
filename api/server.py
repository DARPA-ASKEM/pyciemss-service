from __future__ import annotations

from fastapi import FastAPI, Response, status
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
    print(status)
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
    start = body.timespan.start
    end = body.timespan.end
    interventions = [
        (intervention.timestep, intervention.name, intervention.value) for intervention in body.interventions 
    ]
        

    operation_name = "operations.simulate"
    options = {
        "engine": engine,
        "model_config_id": model_config_id,
        "start": start,
        "end": end,
        "extra": body.extra.dict(),
        "visual_options": True,
        "interventions": interventions
    }

    resp = create_job(operation_name=operation_name, options=options)

    response = {"simulation_id": resp["id"]}

    return response


@app.post("/calibrate", response_model=JobResponse)
def calibrate_model(body: CalibratePostRequest) -> JobResponse:
    """
    Calibrate a model
    """
    from utils import create_job

    # Parse request body
    print(body)
    engine = str(body.engine).lower()
    model_config_id = body.model_config_id
    dataset = body.dataset
    start = body.timespan.start
    end = body.timespan.end
    extra = body.extra.dict()
    intervention_tuples=None
    interventions_array =  body.interventions

    if interventions_array is not None:
        intervention_tuples= [(intervention.timestep +.001, intervention.name, intervention.value) for intervention in interventions_array ]
        


    operation_name = "operations.calibrate_then_simulate"
    options = {
        "engine": engine,
        "model_config_id": model_config_id,
        "start": start,
        "end": end,
        "dataset": dataset.dict(),
        "extra": extra,
        "visual_options": True,
        "interventions":intervention_tuples
    }

    resp = create_job(operation_name=operation_name, options=options)

    response = {"simulation_id": resp["id"]}

    return response


@app.post("/ensemble", response_model=JobResponse)
def create_ensemble(body: EnsemblePostRequest) -> JobResponse:
    """
    Perform an ensemble simulation
    """
    return Response(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content="Ensemble is not yet implemented",
    )


