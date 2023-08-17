from __future__ import annotations

import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import (
    Status,
    JobResponse,
    Calibrate,
    Simulate,
    EnsembleSimulate,
    EnsembleCalibrate,
    StatusSimulationIdGetResponse,
)

from utils.rq_helpers import get_redis, create_job, fetch_job_status, kill_job

Operation = Simulate | Calibrate | EnsembleSimulate | EnsembleCalibrate

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


def enable_progress():
    return True


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
def get_status(
    simulation_id: str, redis_conn=Depends(get_redis)
) -> StatusSimulationIdGetResponse:
    """
    Retrieve the status of a simulation
    """
    status = fetch_job_status(simulation_id, redis_conn)
    logging.info(status)
    if not isinstance(status, str):
        return status

    return {"status": Status.from_rq(status)}


@app.get(
    "/cancel/{simulation_id}", response_model=StatusSimulationIdGetResponse
)  # NOT IN SPEC
def cancel_job(
    simulation_id: str, redis_conn=Depends(get_redis)
) -> StatusSimulationIdGetResponse:
    """
    Cancel a simulation
    """
    status = kill_job(simulation_id, redis_conn)
    logging.info(status)
    if not isinstance(status, str):
        return status

    return {"status": Status.from_rq(status)}


@app.post("/{operation}", response_model=JobResponse)
def operate(
    operation: str,
    body: Operation,
    redis_conn=Depends(get_redis),
    progress_enabled=Depends(enable_progress),
) -> JobResponse:
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
    return create_job(body, operation, redis_conn, progress_enabled)
