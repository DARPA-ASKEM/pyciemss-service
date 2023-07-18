import io
import json
import os
import urllib
import sys
import logging
import numpy as np
import requests
from utils import (
    update_tds_status,
    fetch_dataset,
    fetch_model,
    attach_files,
    catch_job_status
)

from pyciemss.PetriNetODE.interfaces import (
    load_and_calibrate_and_sample_petri_model,
    load_and_sample_petri_model,
)

from pyciemss.Ensemble.interfaces import (
    load_and_sample_petri_ensemble, load_and_calibrate_and_sample_ensemble_model
)


TDS_CONFIGURATIONS = "/model_configurations/"
TDS_SIMULATIONS = "/simulations/"
OUTPUT_FILENAME = os.getenv("PYCIEMSS_OUTPUT_FILEPATH")
EVAL_OUTPUT_FILENAME = "eval.csv"
TDS_API = os.getenv("TDS_URL")

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

@catch_job_status
def simulate(*args, **kwargs):
    username = kwargs.pop("username")
    model_config_id = kwargs.pop("model_config_id")
    num_samples = kwargs.pop("num_samples")
    start = kwargs.pop("start")
    end = kwargs.pop("end")
    job_id = kwargs.pop("job_id")
    logging.debug(f"{job_id} (username - {username}): start simulate")

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
    eval = output.get('quantiles')
    eval.to_csv(EVAL_OUTPUT_FILENAME, index=False)
    attach_files({OUTPUT_FILENAME: "result.csv", "visualization.json": "visualization.json", EVAL_OUTPUT_FILENAME: EVAL_OUTPUT_FILENAME}, TDS_API, TDS_SIMULATIONS, job_id)
    logging.debug(f"{job_id} (username - {username}): finish simulate")

    return

@catch_job_status
def calibrate_then_simulate(*args, **kwargs):
    username = kwargs.pop("username")
    model_config_id = kwargs.pop("model_config_id")
    start = kwargs.pop("start")
    end = kwargs.pop("end")
    mappings = kwargs.pop("mappings", {})
    job_id = kwargs.pop("job_id")
    logging.debug(f"{job_id} (username - {username}): start calibrate")

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
    eval = output.get('quantiles')
    eval.to_csv(EVAL_OUTPUT_FILENAME, index=False)
    attach_files({OUTPUT_FILENAME: "simulation.csv", "visualization.json": "visualization.json", EVAL_OUTPUT_FILENAME: EVAL_OUTPUT_FILENAME}, TDS_API, TDS_SIMULATIONS, job_id)

    logging.debug(f"{job_id} (username - {username}): finish calibrate")
    
    return True


@catch_job_status
def ensemble_simulate(*args, **kwargs):
    username = kwargs.pop("username")
    model_configs = kwargs.pop("model_configs")
    start = kwargs.pop("start")
    end = kwargs.pop("end")
    num_samples = kwargs.pop("num_samples")
    job_id = kwargs.pop("job_id")
    logging.debug(f"{job_id} (username - {username}): start ensemble simulate")

    sim_results_url = TDS_API + TDS_SIMULATIONS + job_id

    update_tds_status(sim_results_url, status="running", start=True)

    weights = [config["weight"] for config in model_configs]
    solution_mappings = [config["solution_mappings"] for config in model_configs]
    amr_paths = [fetch_model(config["id"], TDS_API, TDS_CONFIGURATIONS) for config in model_configs]

    # Generate timepoints
    time_count = end - start
    timepoints=[x for x in range(1,time_count+1)]

    output = load_and_sample_petri_ensemble(
        amr_paths,
        weights,
        solution_mappings,
        num_samples,
        timepoints,
        **kwargs
    )
    samples = output.get('data')
    schema = output.get('visual')
    with open("visualization.json", "w") as f:
        json.dump(schema, f, indent=2)
    samples.to_csv(OUTPUT_FILENAME, index=False)
    eval = output.get('quantiles')
    eval.to_csv(EVAL_OUTPUT_FILENAME, index=False)
    attach_files({OUTPUT_FILENAME: "simulation.csv", "visualization.json": "visualization.json", EVAL_OUTPUT_FILENAME: EVAL_OUTPUT_FILENAME}, TDS_API, TDS_SIMULATIONS, job_id)
    logging.debug(f"{job_id} (username - {username}): finish ensemble simulate")
    return True


@catch_job_status
def ensemble_calibrate(*args, **kwargs):
    username = kwargs.pop("username")
    model_configs = kwargs.pop("model_configs")
    start = kwargs.pop("start")
    end = kwargs.pop("end")
    num_samples = kwargs.pop("num_samples")
    dataset = kwargs.pop("dataset")
    job_id = kwargs.pop("job_id")
    logging.debug(f"{job_id} (username - {username}): start ensemble calibrate")

    sim_results_url = TDS_API + TDS_SIMULATIONS + job_id

    update_tds_status(sim_results_url, status="running", start=True)

    weights = [config["weight"] for config in model_configs]
    solution_mappings = [config["solution_mappings"] for config in model_configs]
    amr_paths = [fetch_model(config["id"], TDS_API, TDS_CONFIGURATIONS) for config in model_configs]

    dataset_path = fetch_dataset(dataset, TDS_API)

    # Generate timepoints
    time_count = end - start
    timepoints=[x for x in range(1,time_count+1)]

    output = load_and_calibrate_and_sample_ensemble_model(
        amr_paths,
        dataset_path,
        weights,
        solution_mappings,
        num_samples,
        timepoints,
        **kwargs
    )
    samples = output.get('data')
    schema = output.get('visual')
    with open("visualization.json", "w") as f:
        json.dump(schema, f, indent=2)
    samples.to_csv(OUTPUT_FILENAME, index=False)
    eval = output.get('quantiles')
    eval.to_csv(EVAL_OUTPUT_FILENAME, index=False)
    attach_files({OUTPUT_FILENAME: "simulation.csv", "visualization.json": "visualization.json", EVAL_OUTPUT_FILENAME: EVAL_OUTPUT_FILENAME}, TDS_API, TDS_SIMULATIONS, job_id)
    logging.debug(f"{job_id} (username - {username}): finish ensemble calibrate")
    return True
