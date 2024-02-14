from __future__ import annotations

import logging
import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from service.models import (
    Status,
    JobResponse,
    Calibrate,
    Simulate,
    EnsembleSimulate,
    StatusSimulationIdGetResponse,
)

from utils.rq_helpers import get_redis, create_job, fetch_job_status, kill_job

operations = {
    "simulate": Simulate,
    "calibrate": Calibrate,
    "ensemble-simulate": EnsembleSimulate,
}

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


@app.get("/health")
def get_health():
    """
    Get health and version
    """
    version_file = "../.version"
    if os.path.exists(version_file):
        version = open(version_file).read().strip("\n")
    else:
        version = "unknown"
    return {"status": "ok", "git_sha": version}


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


for operation_name, schema in operations.items():
    registrar = app.post(f"/{operation_name}", response_model=JobResponse)

    def operate(
        body: schema,
        redis_conn=Depends(get_redis),
    ) -> JobResponse:
        return create_job(body, operation_name, redis_conn)

    registrar(operate)


@app.get("/ensemble-calibrate", response_model=StatusSimulationIdGetResponse)
def ensemble_calibrate_not_yet_implemented():
    """
    DO NOT USE. Placeholder for `ensemble-calibrate` endpoint.
    This will be reimplemented in the future.
    """
    raise HTTPException(status=501, detail="Not yet reimplemented")


@app.get("/optimize", response_model=StatusSimulationIdGetResponse)  # NOT YET IN SPEC
def optimize_not_yet_implemented():  # NOT YET IN SPEC
    """
    DO NOT USE. Placeholder for `optimize` endpoint.
    This will be implemented in the future.
    """
    raise HTTPException(status=501, detail="Not yet implemented")
