import csv
import json
import requests
import sys
import urllib
import os
from datetime import datetime
import pandas
import numpy as np
import time
import logging

TDS_SIMULATIONS = "/simulations/"
OUTPUT_FILENAME = os.getenv("PYCIEMSS_OUTPUT_FILEPATH")
TDS_API = os.getenv("TDS_URL")

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


def make_job_dir(job_id):
    path = os.path.join("/tmp", str(job_id))    
    os.makedirs(path)
    return path


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
    if len(dataset["mappings"]) > 0:
        dropped_columns = set(df.columns) - set(datset["mappings"].values())
        df = df.drop(columns=list(dropped_columns))
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


def catch_job_status(function):
    """
    decorator that catches failed wrapped rq jobs and make sure the simulation status is set in tds.
    """
    def wrapped(*args, **kwargs):
        try:
            start_time = time.perf_counter()
            result = function(*args, **kwargs)
            end_time = time.perf_counter()
            logging.info(
                "Elapsed time for %s for %s: %f",
                function.__name__, kwargs['username'], end_time - start_time
                )
            return result
        except Exception as e:

            log_message = f"""
                ###############################

                There was an exception in CIEMSS Service
                
                Error occured in function: {function.__name__}

                Username: {kwargs['username']}

                ################################
            """
            logging.exception(log_message)
            raise e
    return wrapped