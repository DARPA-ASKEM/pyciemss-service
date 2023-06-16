import io
import json
import os
import urllib
import sys

import numpy as np
import requests
from utils import update_tds_status, parse_samples_into_csv, fetch_dataset

from pyciemss.PetriNetODE.interfaces import (
    load_and_calibrate_and_sample_petri_model,
    load_and_sample_petri_model,
)

TDS_MODELS = "/model_configurations/"
TDS_SIMULATIONS = "/simulations/"
OUTPUT_FILENAME = os.getenv("PYCIEMSS_OUTPUT_FILEPATH")
TDS_API = os.getenv("TDS_URL")


def simulate_model(*args, **kwargs):
    model_id = kwargs.get("model_id")
    num_samples = kwargs.get("num_samples")
    start_epoch = kwargs.get("start")
    end_epoch = kwargs.get("end")
    add_uncertainty = kwargs.get("add_uncertainty", True)
    job_id = kwargs.get("job_id")

    sim_results_url = TDS_API + TDS_SIMULATIONS + job_id

    update_tds_status(sim_results_url, status="running", start=True)

    # Get model from TDS
    url_components = [TDS_API, TDS_MODELS, model_id]
    model_url = ""
    for component in url_components:
        model_url = urllib.parse.urljoin(model_url, component)
    model_response = requests.get(model_url)
    # TODO when pyciemss can handle full model configuration payload remove ["model"]
    model_json = json.loads(model_response.content)["configuration"]["model"]

    # Generate timepoints
    time_count = end_epoch - start_epoch
    timepoints = map(float, range(1, time_count + 1))

    samples = load_and_sample_petri_model(
        model_json, num_samples, timepoints=timepoints, add_uncertainty=add_uncertainty
    )

    # Upload results file
    # TODO remove when pyciemss implements a file output
    parse_samples_into_csv(samples)

    upload_url = (
        TDS_API + f"{TDS_SIMULATIONS}{job_id}/upload-url?filename={OUTPUT_FILENAME}"
    )
    print(upload_url)
    upload_response = requests.get(upload_url)
    presigned_upload_url = upload_response.json()["url"]
    print(presigned_upload_url)
    with open(OUTPUT_FILENAME, "rb") as f:
        upload_response = requests.put(presigned_upload_url, f)

    print(upload_response.status_code)

    # Update simulation object with status and filepaths.
    update_tds_status(
        sim_results_url, status="complete", result_files=[OUTPUT_FILENAME], finish=True
    )

    return upload_response


def calibrate_and_simulate_model(*args, **kwargs):
    model_id = kwargs.get("model_id")
    num_samples = kwargs.get("num_samples")
    start_epoch = kwargs.get("start")
    end_epoch = kwargs.get("end")
    mappings = kwargs.get("mappings")
    job_id = kwargs.get("job_id")

    sim_results_url = TDS_API + TDS_SIMULATIONS + job_id

    update_tds_status(sim_results_url, status="running", start=True)

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

    # Get dataset from TDS
    dataset = kwargs.get("dataset")
    dataset_url = (
        TDS_API + f"/datasets/{dataset.id}/download-url?filename={dataset.filename}"
    )
    dataset_df = fetch_dataset(dataset_url=dataset_url, mappings=mappings)
    dataset_buffer = io.StringIO
    dataset_df.to_csv(dataset_buffer)

    # TODO parse arguments out for calibration
    samples = load_and_calibrate_and_sample_petri_model(
        model_json,
        data=dataset_buffer,
        num_samples=num_samples,
        timepoints=timepoints,
        # start_state: Optional[dict[str, float]] = None,
        add_uncertainty=kwargs.get("add_uncertainty", True),
        pseudocount=kwargs.get("pseudocount", 1.0),
        start_time=kwargs.get("start_time", -1e-10),
        num_iterations=kwargs.get("num_iterations", 1000),
        lr=kwargs.get("lr", 0.03),
        verbose=kwargs.get("verbose", False),
        num_particles=kwargs.get("num_particles", 1),
        # autoguide=pyro.infer.autoguide.AutoLowRankMultivariateNormal,
        method=kwargs.get("method", "dopri5"),
    )

    update_tds_status(
        sim_results_url, status="complete", result_files=[OUTPUT_FILENAME], finish=True
    )

    return str(samples)
