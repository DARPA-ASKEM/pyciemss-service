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

TDS_CONFIGURATIONS = "/model_configurations/"
TDS_SIMULATIONS = "/simulations/"
OUTPUT_FILENAME = os.getenv("PYCIEMSS_OUTPUT_FILEPATH")
TDS_API = os.getenv("TDS_URL")


def simulate(*args, **kwargs):
    model_config_id = kwargs.pop("model_config_id")
    num_samples = kwargs.pop("num_samples")
    start = kwargs.pop("start")
    end = kwargs.pop("end")
    job_id = kwargs.pop("job_id")

    sim_results_url = TDS_API + TDS_SIMULATIONS + job_id

    update_tds_status(sim_results_url, status="running", start=True)

    # Get model from TDS
    url_components = [TDS_API, TDS_CONFIGURATIONS, model_config_id]
    model_url = ""
    for component in url_components:
        model_url = urllib.parse.urljoin(model_url, component)
    model_response = requests.get(model_url)
    # TODO when pyciemss can handle full model configuration payload remove ["model"]
    model_json = json.loads(model_response.content)["configuration"]["model"]

    # Generate timepoints
    time_count = end - start
    timepoints = map(float, range(1, time_count + 1))

    samples = load_and_sample_petri_model(model_json, num_samples, timepoints=timepoints, **kwargs)

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


def calibrate_then_simulate(*args, **kwargs):
    model_config_id = kwargs.pop("model_config_id")
    start = kwargs.pop("start")
    end = kwargs.pop("end")
    mappings = kwargs.pop("mappings")
    job_id = kwargs.pop("job_id")

    sim_results_url = TDS_API + TDS_SIMULATIONS + job_id

    update_tds_status(sim_results_url, status="running", start=True)

    # Get model from TDS
    tds_api = os.getenv("TDS_URL")
    url_components = [tds_api, TDS_CONFIGURATIONS, model_config_id]
    model_url = ""
    for component in url_components:
        model_url = urllib.parse.urljoin(model_url, component)
    model_response = requests.get(model_url)
    model_json = json.loads(model_response.content)

    # Generate timepoints
    time_count = end - start
    timepoints = map(float, range(1, time_count + 1))

    # Get dataset from TDS
    dataset = kwargs.get("dataset")
    dataset_url = (
        TDS_API + f"/datasets/{dataset.id}/download-url?filename={dataset.filename}"
    )
    dataset_df = fetch_dataset(dataset_url=dataset_url, mappings=mappings)
    dataset_buffer = io.StringIO()
    dataset_df.to_csv(dataset_buffer)

    # TODO parse arguments out for calibration
    samples = load_and_calibrate_and_sample_petri_model(
        model_json,
        data=dataset_buffer,
        timepoints=timepoints,
        **kwargs
    )

    update_tds_status(
        sim_results_url, status="complete", result_files=[OUTPUT_FILENAME], finish=True
    )

    return str(samples)
