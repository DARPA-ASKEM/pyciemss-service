import io
import json
import os
import urllib
import sys
import logging
import pandas as pd
import numpy as np
from juliacall import newmodule
import requests
from settings import settings
from utils.rq_helpers import update_status_on_job_fail
from utils.tds import update_tds_status, cleanup_job_dir, fetch_dataset, fetch_model, attach_files
from utils.rabbitmq import gen_rabbitmq_hook

TDS_CONFIGURATIONS = "/model_configurations/"
TDS_SIMULATIONS = "/simulations/"
TDS_URL = settings.TDS_URL

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

jl = newmodule("SciMLIntegration")
jl.seval("using SciMLIntegration, PythonCall")

@update_status_on_job_fail
def simulate(request, *, job_id):
    logging.debug(f"{job_id} (username - {request.username}): start simulate")

    sim_results_url = TDS_URL + TDS_SIMULATIONS + job_id

    update_tds_status(sim_results_url, status="running", start=True)

    # Get model from TDS
    amr_path = fetch_model(request.model_config_id, TDS_URL, TDS_CONFIGURATIONS, job_id)
    with open(amr_path, "r") as file:
        amr = file.read()
    
    result = jl.pytable(jl.simulate(amr, request.timespan.start, request.timespan.end))

    attach_files({"data": result}, TDS_URL, TDS_SIMULATIONS, job_id)
    cleanup_job_dir(job_id)
    logging.debug(f"{job_id} (username - {request.username}): finish simulate")
