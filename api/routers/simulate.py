from __future__ import annotations

import json
import os
import requests
import sys

from fastapi import APIRouter
import urllib

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

TDS_MODELS = '/models/'


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

    # Parse request body
    print(body)
    model_id = body.model_config_id
    num_samples = body.num_samples
    start_timestamp = body.timespan.start_epoch
    end_timestamp = body.timespan.end_epoch

    print(model_id)

    # Get model from TDS
    tds_api = os.getenv("TDS_URL")
    url_components = [tds_api, TDS_MODELS, model_id]
    model_url = ''
    for component in url_components:
        model_url = urllib.parse.urljoin(model_url, component)
    print(model_url)
    sys.stdout.flush()
    model_response = requests.get(model_url)
    model_json = json.loads(model_response.content)

    if os.getenv("MODEL_DEBUG_HARDCODE_FILE"):
        model_json = json.load(open("/api/BIOMD0000000955_template_model.json"))


    job_string = "ciemss_processor.simulate_model"
    options = {
        "model": model_json,
        "start_epoch": start_timestamp,
        "end_epoch": end_timestamp,
        "num_samples": num_samples
    }

    resp = job(uuid=model_id, job_string=job_string, options=options)

    return resp



@router.get('/status/{simulation_id}', response_model=StatusSimulationIdGetResponse)
def get_status(simulation_id: str) -> StatusSimulationIdGetResponse:
    """
    Retrieve the status of a simulation
    """
    from utils import fetch_job_status
    
    return fetch_job_status(simulation_id)
