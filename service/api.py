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
import os
import redis
import sys
from threading import Thread
import time

from utils.rq_helpers import create_job, fetch_job_status, kill_job
from utils.rabbitmq import mock_rabbitmq_consumer


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


@app.get("/ping") # NOT IN SPEC
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


@app.get("/cancel/{simulation_id}", response_model=StatusSimulationIdGetResponse) # NOT IN SPEC
def cancel_job(simulation_id: str) -> StatusSimulationIdGetResponse:
    """
    Cancel a simulation
    """
    status = kill_job(simulation_id)
    logging.info(status)
    if not isinstance(status, str):
        return status

    return {"status": Status.from_rq(status)}


@app.post("/simulate", response_model=JobResponse)
def simulate_model(body: SimulatePostRequest) -> JobResponse:
    """
    Perform a simulation
    """
    return create_job(body, "simulate")


@app.post("/calibrate", response_model=JobResponse)
def calibrate_model(body: CalibratePostRequest) -> JobResponse:
    """
    Calibrate a model
    """
    return create_job(body, "calibrate")


@app.post("/ensemble-simulate", response_model=JobResponse)
def create_simulate_ensemble(body: EnsembleSimulatePostRequest) -> JobResponse:
    """
    Perform ensemble simulate
    """
    return create_job(body, "ensemble-simulate")


@app.post("/ensemble-calibrate", response_model=JobResponse)
def create_calibrate_ensemble(body: EnsembleCalibratePostRequest) -> JobResponse:
    """
    Perform ensemble simulate
    """
    return create_job(body, "ensemble-calibrate")