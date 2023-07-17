import io
import json
import os
import urllib
import sys
import logging
import numpy as np
import requests
from utils import update_tds_status,\
                parse_samples_into_csv,\
                fetch_dataset,\
                fetch_model,\
                attach_files,\
                catch_job_status

from pyciemss.PetriNetODE.interfaces import (
    load_and_calibrate_and_sample_petri_model,
    load_and_sample_petri_model,
)

TDS_CONFIGURATIONS = "/model_configurations/"
TDS_SIMULATIONS = "/simulations/"
OUTPUT_FILENAME = os.getenv("PYCIEMSS_OUTPUT_FILEPATH")
TDS_API = os.getenv("TDS_URL")

@catch_job_status
def simulate(*args, **kwargs):
    model_config_id = kwargs.pop("model_config_id")
    num_samples = kwargs.pop("num_samples")
    start = kwargs.pop("start")
    end = kwargs.pop("end")
    username = kwargs.pop("username")
    job_id = kwargs.pop("job_id")

    sim_results_url = TDS_API + TDS_SIMULATIONS + job_id

    update_tds_status(sim_results_url, status="running", start=True)

    # Get model from TDS
    amr_path = fetch_model(model_config_id, TDS_API, TDS_CONFIGURATIONS)

    # Generate timepoints
    time_count = end - start
    timepoints=[x for x in range(1,time_count+1)]

    output = load_and_sample_petri_model(amr_path, num_samples, timepoints=timepoints, **kwargs)
    samples = output.get('data')
    schema = output.get('visual')
    with open("visualization.json", "w") as f:
        json.dump(schema, f, indent=2)
    samples.to_csv(OUTPUT_FILENAME, index=False)
    attach_files({OUTPUT_FILENAME: "result.csv", "visualization.json": "visualization.json"}, TDS_API, TDS_SIMULATIONS, job_id)

    return

@catch_job_status
def calibrate_then_simulate(*args, **kwargs):
    model_config_id = kwargs.pop("model_config_id")
    start = kwargs.pop("start")
    end = kwargs.pop("end")
    username = kwargs.pop("username")
    mappings = kwargs.pop("mappings", {})
    job_id = kwargs.pop("job_id")

    sim_results_url = TDS_API + TDS_SIMULATIONS + job_id

    update_tds_status(sim_results_url, status="running", start=True)

    amr_path = fetch_model(model_config_id, TDS_API, TDS_CONFIGURATIONS)

    # Generate timepoints
    time_count = end - start
    timepoints=[x for x in range(1,time_count+1)]

    dataset_path = fetch_dataset(kwargs.pop("dataset"), TDS_API)

    output = load_and_calibrate_and_sample_petri_model(
        amr_path,
        dataset_path,
        timepoints=timepoints,
        **kwargs
    )
    samples = output.get('data')
    schema = output.get('visual')
    with open("visualization.json", "w") as f:
        json.dump(schema, f, indent=2)
    samples.to_csv(OUTPUT_FILENAME, index=False)
    attach_files({OUTPUT_FILENAME: "simulation.csv", "visualization.json": "visualization.json"}, TDS_API, TDS_SIMULATIONS, job_id)
    

    return True


@catch_job_status
def ensemble_simulate(*args, **kwargs):
    return True


@catch_job_status
def ensemble_calibrate(*args, **kwargs):
    return True
