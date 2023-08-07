import io
import json
import os
import urllib
import sys
import logging
import numpy as np
import requests
from juliacall import newmodule
from settings import settings
from utils.rq_helpers import update_status_on_job_fail
from utils.tds import update_tds_status, cleanup_job_dir, fetch_dataset, fetch_model, attach_files
from utils.rabbitmq import gen_rabbitmq_hook

from pyciemss.PetriNetODE.interfaces import (
    load_and_calibrate_and_sample_petri_model,
    load_and_sample_petri_model,
)

from pyciemss.Ensemble.interfaces import (
    load_and_sample_petri_ensemble, load_and_calibrate_and_sample_ensemble_model
)


TDS_CONFIGURATIONS = "/model_configurations/"
TDS_SIMULATIONS = "/simulations/"
TDS_URL = settings.TDS_URL

jl = newmodule("SciMLIntegration")
#jl.seval("using SciMLIntegration, PythonCall")

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

def execute(request, *, job_id):
    logging.debug(f"STARTED {job_id} (username: {request.username})")
    sim_results_url = TDS_URL + TDS_SIMULATIONS + job_id
    update_tds_status(sim_results_url, status="running", start=True)

    if request.engine == "ciemss":
        operation_name = request.__class__.pyciemss_lib_function
        kwargs = request.gen_pyciemss_args(job_id)
        if len(operation_name) == 0: 
            raise Exception("No operation provided in request")
        else:
            output = eval(operation_name)(**kwargs) 
    else:
        operation = request.__class__.sciml_lib_function
        output = operation(job_id, jl)

    output = operation(**kwargs)

    attach_files(output, TDS_URL, TDS_SIMULATIONS, job_id)
    cleanup_job_dir(job_id)
    logging.debug(f"FINISHED {job_id} (username: {request.username})")


@update_status_on_job_fail
def calibrate_then_simulate(request, *, job_id):
    logging.debug(f"{job_id} (username - {request.username}): start calibrate")
    sim_results_url = TDS_URL + TDS_SIMULATIONS + job_id

    update_tds_status(sim_results_url, status="running", start=True)

    amr_path = fetch_model(request.model_config_id, TDS_URL, TDS_CONFIGURATIONS, job_id)
    
    # Generate timepoints
    time_count = request.timespan.end - request.timespan.start
    timepoints=[step for step in range(1,time_count+1)]

    dataset_path = fetch_dataset(request.dataset.dict(), TDS_URL, job_id)

    output = load_and_calibrate_and_sample_petri_model(
        petri_model_or_path=amr_path,
        timepoints=timepoints,
        data_path=dataset_path,
        progress_hook=gen_rabbitmq_hook(job_id),
        visual_options=True,
        **request.extra.dict()
    )
    attach_files(output, TDS_URL, TDS_SIMULATIONS, job_id)
    cleanup_job_dir(job_id)

    logging.debug(f"{job_id} (username - {request.username}): finish calibrate")
    


@update_status_on_job_fail
def ensemble_simulate(request, *, job_id):
    logging.debug(f"{job_id} (username - {request.username}): start ensemble simulate")

    sim_results_url = TDS_URL + TDS_SIMULATIONS + job_id

    update_tds_status(sim_results_url, status="running", start=True)

    weights = [config.weight for config in request.model_configs]
    solution_mappings = [config.solution_mappings for config in request.model_configs]
    amr_paths = [fetch_model(config.id, TDS_URL, TDS_CONFIGURATIONS, job_id) for config in request.model_configs]
    
    # Generate timepoints
    time_count = request.timespan.end - request.timespan.start
    timepoints=[step for step in range(1,time_count+1)]

    output = load_and_sample_petri_ensemble(
        petri_model_or_paths=amr_paths,
        weights=weights,
        solution_mappings=solution_mappings,
        timepoints=timepoints,
        visual_options=True,
        **request.extra.dict()
    )
    attach_files(output, TDS_URL, TDS_SIMULATIONS, job_id)
    cleanup_job_dir(job_id)
    logging.debug(f"{job_id} (username - {request.username}): finish ensemble simulate")


@update_status_on_job_fail
def ensemble_calibrate(request, *, job_id):
    extra = request.extra.dict()
    num_samples = extra.pop("num_samples")
    logging.debug(f"{job_id} (username - {request.username}): start ensemble calibrate")

    sim_results_url = TDS_URL + TDS_SIMULATIONS + job_id

    update_tds_status(sim_results_url, status="running", start=True)

    weights = [config.weight for config in request.model_configs]
    solution_mappings = [config.solution_mappings for config in request.model_configs]
    amr_paths = [fetch_model(config.id, TDS_URL, TDS_CONFIGURATIONS, job_id) for config in request.model_configs]

    dataset_path = fetch_dataset(request.dataset.dict(), TDS_URL, job_id)

    # Generate timepoints
    time_count = request.timespan.end - request.timespan.start
    timepoints=[step for step in range(1,time_count+1)]

    output = load_and_calibrate_and_sample_ensemble_model(
        petri_model_or_paths=amr_paths,
        weights=weights,
        solution_mappings=solution_mappings,
        timepoints=timepoints,
        data_path=dataset_path,
        visual_options=True,
        **request.extra.dict()
    )
    attach_files(output, TDS_URL, TDS_SIMULATIONS, job_id)
    cleanup_job_dir(job_id)
    logging.debug(f"{job_id} (username - {request.username}): finish ensemble calibrate")
