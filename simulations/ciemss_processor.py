import json
import os
import urllib
import sys

import numpy as np
import requests
from utils import parse_samples_into_file

from pyciemss.PetriNetODE.interfaces import (
    load_and_calibrate_and_sample_petri_model,
    load_and_sample_petri_model,
)

TDS_MODELS = "/model_configurations/"


def simulate_model(*args, **kwargs):
    model_id = kwargs.get("model_id")
    num_samples = kwargs.get("num_samples")
    start_epoch = kwargs.get("start_epoch")
    end_epoch = kwargs.get("end_epoch")
    add_uncertainty = kwargs.get("add_uncertainty", True)
    job_id = kwargs.get("job_id")

    # Get model from TDS
    tds_api = os.getenv("TDS_URL")
    url_components = [tds_api, TDS_MODELS, model_id]
    model_url = ""
    for component in url_components:
        model_url = urllib.parse.urljoin(model_url, component)
    model_response = requests.get(model_url)
    # TODO when pyciemss can handle full model payload remove ["model"]
    model_json = json.loads(model_response.content)["configuration"]["model"]

    # TODO Remove when PyCIEMSS can handle correct models
    # if os.getenv("MODEL_DEBUG_HARDCODE_FILE"):
    #     model_json = json.load(open("/simulations/BIOMD0000000955_template_model.json"))

    # Generate timepoints
    time_count = end_epoch - start_epoch
    timepoints = map(float, range(1, time_count + 1))

    samples = load_and_sample_petri_model(
        model_json, num_samples, timepoints=timepoints, add_uncertainty=add_uncertainty
    )

    # TODO Put results (and files) to TDS
    parse_samples_into_file(samples)

    upload_url = tds_api + f"/simulations/{job_id}/upload-url?filename=sim_output.json"
    print(upload_url)
    upload_response = requests.get(upload_url)
    presigned_upload_url = upload_response.content
    print(presigned_upload_url)
    sys.stdout.flush()
    with open("sim_output.json", "rb") as f:
        upload_response = requests.put(presigned_upload_url, f)

    print(upload_response.content)
    return upload_response.content


def calibrate_and_simulate_model(*args, **kwargs):
    model_id = kwargs.get("model_id")
    num_samples = kwargs.get("num_samples")
    start_epoch = kwargs.get("start_epoch")
    end_epoch = kwargs.get("end_epoch")
    add_uncertainty = kwargs.get("add_uncertainty", True)

    # Get model from TDS
    tds_api = os.getenv("TDS_URL")
    url_components = [tds_api, TDS_MODELS, model_id]
    model_url = ""
    for component in url_components:
        model_url = urllib.parse.urljoin(model_url, component)
    model_response = requests.get(model_url)
    model_json = json.loads(model_response.content)

    # Generate timepoints
    time_count = end_epoch - start_epoch
    timepoints = map(float, range(1, time_count + 1))

    # TODO parse arguments out for calibration
    samples = load_and_calibrate_and_sample_petri_model(
        model_json,
        # data: Iterable[Tuple[float, dict[str, float]]],
        num_samples=num_samples,
        timepoints=timepoints,
        # start_state: Optional[dict[str, float]] = None,
        add_uncertainty=add_uncertainty,
        # pseudocount: float = 1.0,
        # start_time: float = -1e-10,
        # num_iterations: int = 1000,
        # lr: float = 0.03,
        # verbose: bool = False,
        # num_particles: int = 1,
        # autoguide=pyro.infer.autoguide.AutoLowRankMultivariateNormal,
        # method="dopri5",
    )

    return str(samples)
