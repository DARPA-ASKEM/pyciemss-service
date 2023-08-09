from __future__ import annotations

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from service.models import (
    Status,
    JobResponse,
    Calibrate,
    Simulate,
    EnsembleSimulate,
    EnsembleCalibrate,
    StatusSimulationIdGetResponse,
)

from utils.rq_helpers import create_job, fetch_job_status, kill_job

Operation = Simulate | Calibrate | EnsembleSimulate | EnsembleCalibrate

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


@app.get("/ping")  # NOT IN SPEC
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
    status = fetch_job_status(simulation_id)
    logging.info(status)
    if not isinstance(status, str):
        return status

    return {"status": Status.from_rq(status)}


@app.get(
    "/cancel/{simulation_id}", response_model=StatusSimulationIdGetResponse
)  # NOT IN SPEC
def cancel_job(simulation_id: str) -> StatusSimulationIdGetResponse:
    """
    Cancel a simulation
    """
    status = kill_job(simulation_id)
    logging.info(status)
    if not isinstance(status, str):
        return status

    return {"status": Status.from_rq(status)}


@app.post("/{operation}", response_model=JobResponse)
def operate(operation: str, body: Operation) -> JobResponse:
    def check(otype):
        if isinstance(body, otype):
            return None
        else:
            raise HTTPException(
                status_code=400, detail="Payload does not match operation"
            )

    match operation:
        case "simulate":
            check(Simulate)
        case "calibrate":
            check(Calibrate)
        case "ensemble-simulate":
            check(EnsembleSimulate)
        case "ensemble-calibrate":
            check(EnsembleCalibrate)
        case _:
            raise HTTPException(status_code=404, detail="Operation not found")
    return create_job(body, operation)
