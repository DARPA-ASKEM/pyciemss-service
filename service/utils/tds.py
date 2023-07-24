"""
Module used to interact with the Terarium Data Service (TDS)    
"""
from __future__ import annotations

import logging
import csv
import urllib
import os
import time
import uuid
import json
import sys
import requests
from ast import Dict
from typing import Any, Optional
from copy import deepcopy
from datetime import datetime

import pandas
import numpy as np
from fastapi import Response, status


from settings import settings

OUTPUT_FILENAME = settings.PYCIEMSS_OUTPUT_FILEPATH
TDS_SIMULATIONS = "/simulations/"
TDS_URL = settings.TDS_URL


def update_tds_status(url, status, result_files=[], start=False, finish=False):
    logging.debug(f"Updating simulation `{url}` -- {status} start: {start}; finish: {finish}; result_files: {result_files}")
    tds_payload = requests.get(url)
    tds_payload = tds_payload.json()

    if start:
        tds_payload["start_time"] = datetime.now()
    if finish:
        tds_payload["completed_time"] = datetime.now()

    tds_payload["status"] = status
    if result_files:
        tds_payload["result_files"] = result_files

    update_response = requests.put(
        url, json=json.loads(json.dumps(tds_payload, default=str))
    )

    return update_response


def fetch_model(model_config_id, tds_api, config_endpoint, job_dir):
    logging.debug(f"Fetching model {model_config_id}")
    url_components = [tds_api, config_endpoint, model_config_id]
    model_url = ""
    for component in url_components:
        model_url = urllib.parse.urljoin(model_url, component)
    model_response = requests.get(model_url)
    amr_path = os.path.join(job_dir, f"./{model_config_id}.json")
    with open(amr_path, "w") as file:
        json.dump(model_response.json()["configuration"], file)
    return amr_path


def fetch_dataset(dataset: dict, tds_api, job_dir):
    logging.debug(f"Fetching dataset {dataset['id']}")
    dataset_url = f"{tds_api}/datasets/{dataset['id']}/download-url?filename={dataset['filename']}"
    response = requests.get(dataset_url)
    df = pandas.read_csv(response.json()["url"])
    df = df.rename(columns=dataset["mappings"])
    dataset_path = os.path.join(job_dir, "./temp.json")
    with open(dataset_path, "w") as file:
        df.to_csv(file, index=False)
    return dataset_path


def attach_files(files: dict, tds_api, simulation_endpoint, job_id, status='complete'):
    sim_results_url = tds_api + simulation_endpoint + job_id

    if status!="error":
        for (location, handle) in files.items():   
            upload_url = f"{sim_results_url}/upload-url?filename={handle}"
            upload_response = requests.get(upload_url)
            presigned_upload_url = upload_response.json()["url"]
            with open(location, "rb") as f:
                upload_response = requests.put(presigned_upload_url, f)
    else:
        logging.error(f"{job_id} ran into error")

    # Update simulation object with status and filepaths.
    update_tds_status(
        sim_results_url, status=status, result_files=list(files.values()), finish=True
    )



