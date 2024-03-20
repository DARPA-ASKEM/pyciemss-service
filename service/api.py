from __future__ import annotations

import logging
import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from service.models import (
    Status,
    JobResponse,
    Calibrate,
    Simulate,
    EnsembleSimulate,
    EnsembleCalibrate,
    Optimize,
    StatusSimulationIdGetResponse,
)

from utils.rq_helpers import get_redis, create_job, fetch_job_status, kill_job

operations = {
    "simulate": Simulate,
    "calibrate": Calibrate,
    "ensemble-simulate": EnsembleSimulate,
    "ensemble-calibrate": EnsembleCalibrate,
    "optimize": Optimize,
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
    status, error_msg = fetch_job_status(simulation_id, redis_conn)
    logging.info(status)
    if not isinstance(status, str):
        return status

    return {
        "status": Status.from_rq(status),
        "error_msg": error_msg,
    }


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

    def make_operate(operation):
        def operate(
            body: schema,
            redis_conn=Depends(get_redis),
        ) -> JobResponse:
            return create_job(body, operation, redis_conn)

        return operate

    operate = make_operate(operation_name)
    registrar(operate)
