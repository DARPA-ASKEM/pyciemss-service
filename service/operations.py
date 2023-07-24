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
def simulate(request, *, job_id):
    extra = request.dict()
    num_samples = extra.pop("num_samples")
    if len(request.interventions) > 0:
        interventions = [
            (intervention.timestep, intervention.name, intervention.value) for intervention in body.interventions 
        ]
    else:
        intervention = []

    logging.debug(f"{job_id} (username - {request.username}): start simulate")

    sim_results_url = TDS_URL + TDS_SIMULATIONS + job_id
    job_dir = make_job_dir(job_id)
    output_filename = os.path.join(job_dir, OUTPUT_FILENAME)
    eval_output_filename = os.path.join(job_dir, EVAL_OUTPUT_FILENAME)
    visualization_filename = os.path.join(job_dir, "./visualization.json")

    update_tds_status(sim_results_url, status="running", start=True)

    # Get model from TDS
    amr_path = fetch_model(request.model_config_id, TDS_URL, TDS_CONFIGURATIONS, job_dir)

    # Generate timepoints
    time_count = request.end - request.start
    timepoints=[x for x in range(1,time_count+1)]

    output = load_and_sample_petri_model(
        amr_path, 
        num_samples, 
        timepoints=timepoints, 
        interventions=interventions,
        visual_options=True, 
        **extra
    )
    samples = output.get('data')
    schema = output.get('visual')
    with open(visualization_filename, "w") as f:
        json.dump(schema, f, indent=2)
    samples.to_csv(output_filename, index=False)
    eval = output.get('quantiles')
    eval.to_csv(eval_output_filename, index=False)
    attach_files({output_filename: "result.csv", visualization_filename: "visualization.json", eval_output_filename: "eval.csv"}, TDS_URL, TDS_SIMULATIONS, job_id)
    logging.debug(f"{job_id} (username - {request.username}): finish simulate")

    return True

@catch_job_status
def calibrate_then_simulate(request, *, job_id):
    extra = request.extra.dict()
    logging.debug(f"{job_id} (username - {request.username}): start calibrate")
    sim_results_url = TDS_URL + TDS_SIMULATIONS + job_id
    job_dir = make_job_dir(job_id)
    output_filename = os.path.join(job_dir, OUTPUT_FILENAME)
    eval_output_filename = os.path.join(job_dir, EVAL_OUTPUT_FILENAME)
    visualization_filename = os.path.join(job_dir, "./visualization.json")

    update_tds_status(sim_results_url, status="running", start=True)

    amr_path = fetch_model(request.model_config_id, TDS_URL, TDS_CONFIGURATIONS, job_dir)

    # Generate timepoints
    time_count = request.end - request.start
    timepoints=[x for x in range(1,time_count+1)]

    dataset_path = fetch_dataset(request.dataset.dict(), TDS_URL, job_dir)

    output = load_and_calibrate_and_sample_petri_model(
        amr_path,
        dataset_path,
        timepoints=timepoints,
        visual_options=True,
        **extra
    )
    samples = output.get('data')
    schema = output.get('visual')
    with open(visualization_filename, "w") as f:
        json.dump(schema, f, indent=2)
    samples.to_csv(output_filename, index=False)
    eval = output.get('quantiles')
    eval.to_csv(eval_output_filename, index=False)
    attach_files({output_filename: "simulation.csv", visualization_filename: "visualization.json", eval_output_filename: "eval.csv"}, TDS_URL, TDS_SIMULATIONS, job_id)

    logging.debug(f"{job_id} (username - {request.username}): finish calibrate")
    
    return True


@catch_job_status
def ensemble_simulate(request, *, job_id):
    extra = request.dict()
    num_samples = extra.pop("num_samples")
    logging.debug(f"{job_id} (username - {request.username}): start ensemble simulate")

    sim_results_url = TDS_URL + TDS_SIMULATIONS + job_id
    job_dir = make_job_dir(job_id)
    output_filename = os.path.join(job_dir, OUTPUT_FILENAME)
    eval_output_filename = os.path.join(job_dir, EVAL_OUTPUT_FILENAME)
    visualization_filename = os.path.join(job_dir, "./visualization.json")

    update_tds_status(sim_results_url, status="running", start=True)

    weights = [config.weight for config in request.model_configs]
    solution_mappings = [config.solution_mappings for config in request.model_configs]
    amr_paths = [fetch_model(config.id, TDS_URL, TDS_CONFIGURATIONS, job_dir) for config in request.model_configs]

    # Generate timepoints
    time_count = request.end - request.start
    timepoints=[x for x in range(1,time_count+1)]

    output = load_and_sample_petri_ensemble(
        amr_paths,
        weights,
        solution_mappings,
        num_samples,
        timepoints,
        visual_options=True,
        **extra
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
def ensemble_calibrate(request, *, job_id):
    extra = request.extra.dict()
    num_samples = extra.pop("num_samples")
    logging.debug(f"{job_id} (username - {username}): start ensemble calibrate")

    sim_results_url = TDS_URL + TDS_SIMULATIONS + job_id
    job_dir = make_job_dir(job_id)
    output_filename = os.path.join(job_dir, OUTPUT_FILENAME)
    eval_output_filename = os.path.join(job_dir, EVAL_OUTPUT_FILENAME)
    visualization_filename = os.path.join(job_dir, "./visualization.json")

    update_tds_status(sim_results_url, status="running", start=True)

    weights = [config.weight for config in request.model_configs]
    solution_mappings = [config.solution_mappings for config in request.model_configs]
    amr_paths = [fetch_model(config.id, TDS_URL, TDS_CONFIGURATIONS, job_dir) for config in request.model_configs]

    dataset_path = fetch_dataset(request.dataset.dict(), TDS_URL, job_dir)

    # Generate timepoints
    time_count = request.end - request.start
    timepoints=[x for x in range(1,time_count+1)]

    output = load_and_calibrate_and_sample_ensemble_model(
        amr_paths,
        dataset_path,
        weights,
        solution_mappings,
        num_samples,
        timepoints,
        visual_options=True,
        **request.extra
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
