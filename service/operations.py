import io
import json
import os
import urllib
import sys
import logging
import numpy as np
import requests
from settings import settings
from utils.rq_helpers import make_job_dir, catch_job_status
from utils.tds import update_tds_status, fetch_datset, fetch_model, attach_files

from pyciemss.PetriNetODE.interfaces import (
    load_and_calibrate_and_sample_petri_model,
    load_and_sample_petri_model,
)

from pyciemss.Ensemble.interfaces import (
    load_and_sample_petri_ensemble, load_and_calibrate_and_sample_ensemble_model
)


TDS_CONFIGURATIONS = "/model_configurations/"
TDS_SIMULATIONS = "/simulations/"
OUTPUT_FILENAME = settings.PYCIEMSS_OUTPUT_FILEPATH
EVAL_OUTPUT_FILENAME = settings.EVAL_OUTPUT_FILENAME
TDS_URL = settings.TDS_URL

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

    sim_results_url = TDS_URL + TDS_SIMULATIONS + job_id
    job_dir = make_job_dir(job_id)
    output_filename = os.path.join(job_dir, OUTPUT_FILENAME)
    eval_output_filename = os.path.join(job_dir, EVAL_OUTPUT_FILENAME)
    visualization_filename = os.path.join(job_dir, "./visualization.json")

    update_tds_status(sim_results_url, status="running", start=True)

    # Get model from TDS
    amr_path = fetch_model(model_config_id, TDS_URL, TDS_CONFIGURATIONS, job_dir)

    # Generate timepoints
    time_count = end - start
    timepoints=[x for x in range(1,time_count+1)]

    output = load_and_sample_petri_model(amr_path, num_samples, timepoints=timepoints, **kwargs)
    samples = output.get('data')
    schema = output.get('visual')
    with open(visualization_filename, "w") as f:
        json.dump(schema, f, indent=2)
    samples.to_csv(output_filename, index=False)
    eval = output.get('quantiles')
    eval.to_csv(eval_output_filename, index=False)
    attach_files({output_filename: "result.csv", visualization_filename: "visualization.json", eval_output_filename: "eval.csv"}, TDS_URL, TDS_SIMULATIONS, job_id)
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

    sim_results_url = TDS_URL + TDS_SIMULATIONS + job_id
    job_dir = make_job_dir(job_id)
    output_filename = os.path.join(job_dir, OUTPUT_FILENAME)
    eval_output_filename = os.path.join(job_dir, EVAL_OUTPUT_FILENAME)
    visualization_filename = os.path.join(job_dir, "./visualization.json")

    update_tds_status(sim_results_url, status="running", start=True)

    amr_path = fetch_model(model_config_id, TDS_URL, TDS_CONFIGURATIONS, job_dir)

    # Generate timepoints
    time_count = end - start
    timepoints=[x for x in range(1,time_count+1)]

    dataset_path = fetch_dataset(kwargs.pop("dataset"), TDS_URL, job_dir)

    output = load_and_calibrate_and_sample_petri_model(
        amr_path,
        dataset_path,
        timepoints=timepoints,
        **kwargs
    )
    samples = output.get('data')
    schema = output.get('visual')
    with open(visualization_filename, "w") as f:
        json.dump(schema, f, indent=2)
    samples.to_csv(output_filename, index=False)
    eval = output.get('quantiles')
    eval.to_csv(eval_output_filename, index=False)
    attach_files({output_filename: "simulation.csv", visualization_filename: "visualization.json", eval_output_filename: "eval.csv"}, TDS_URL, TDS_SIMULATIONS, job_id)

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

    sim_results_url = TDS_URL + TDS_SIMULATIONS + job_id
    job_dir = make_job_dir(job_id)
    output_filename = os.path.join(job_dir, OUTPUT_FILENAME)
    eval_output_filename = os.path.join(job_dir, EVAL_OUTPUT_FILENAME)
    visualization_filename = os.path.join(job_dir, "./visualization.json")

    update_tds_status(sim_results_url, status="running", start=True)

    weights = [config["weight"] for config in model_configs]
    solution_mappings = [config["solution_mappings"] for config in model_configs]
    amr_paths = [fetch_model(config["id"], TDS_URL, TDS_CONFIGURATIONS, job_dir) for config in model_configs]

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
    with open(visualization_filename, "w") as f:
        json.dump(schema, f, indent=2)
    samples.to_csv(output_filename, index=False)
    eval = output.get('quantiles')
    eval.to_csv(eval_output_filename, index=False)
    attach_files({output_filename: "simulation.csv", visualization_filename: "visualization.json", eval_output_filename: "eval.csv"}, TDS_URL, TDS_SIMULATIONS, job_id)
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

    sim_results_url = TDS_URL + TDS_SIMULATIONS + job_id
    job_dir = make_job_dir(job_id)
    output_filename = os.path.join(job_dir, OUTPUT_FILENAME)
    eval_output_filename = os.path.join(job_dir, EVAL_OUTPUT_FILENAME)
    visualization_filename = os.path.join(job_dir, "./visualization.json")

    update_tds_status(sim_results_url, status="running", start=True)

    weights = [config["weight"] for config in model_configs]
    solution_mappings = [config["solution_mappings"] for config in model_configs]
    amr_paths = [fetch_model(config["id"], TDS_URL, TDS_CONFIGURATIONS, job_dir) for config in model_configs]

    dataset_path = fetch_dataset(dataset, TDS_URL, job_dir)

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
    with open(visualization_filename, "w") as f:
        json.dump(schema, f, indent=2)
    samples.to_csv(output_filename, index=False)
    eval = output.get('quantiles')
    eval.to_csv(eval_output_filename, index=False)
    attach_files({output_filename: "simulation.csv", visualization_filename: "visualization.json", eval_output_filename: "eval.csv"}, TDS_URL, TDS_SIMULATIONS, job_id)
    logging.debug(f"{job_id} (username - {username}): finish ensemble calibrate")
    return True