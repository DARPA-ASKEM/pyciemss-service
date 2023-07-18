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

def parse_samples_into_file(samples):
    # samples_str = json.dumps(samples)
    # samples_dict = json.loads(samples)

    pyciemss_results = {"states": {}, "params": {}}
    for key, value in samples.items():
        key_components = key.split("_")
        if len(key_components) > 1:
            if key_components[1] == "sol":
                pyciemss_results["states"][key] = value
        else:
            pyciemss_results["params"][key] = value

    print(pyciemss_results)

    file_output_json = {
        "0": {
            "description": "PyCIEMSS integration demo",
            "initials": {
                str(i): {"name": k, "identifiers": {}, "value": v.tolist()[0][0]}
                for i, (k, v) in enumerate(pyciemss_results["states"].items())
            },
            "parameters": {
                str(i): {"name": k, "identifiers": {}, "value": v.tolist()}
                for i, (k, v) in enumerate(pyciemss_results["params"].items())
            },
            "output": {
                str(i): {"name": k, "identifiers": {}, "value": v.tolist()}
                for i, (k, v) in enumerate(pyciemss_results["states"].items())
            },
        }
    }

    with open("sim_output.json", "w") as f:
        f.write(json.dumps(file_output_json))


def parse_samples_into_csv(samples):
    # Alternate: flat dataframe CSV

    pyciemss_results = {"states": {}, "params": {}}
    for key, value in samples.items():
        key_components = key.split("_")
        if len(key_components) > 1:
            if key_components[1] == "sol":
                pyciemss_results["states"][key] = value
        else:
            pyciemss_results["params"][key] = value

    # Time points and sample points
    num_samples, num_timepoints = next(iter(pyciemss_results["states"].values())).shape
    d = {
        "timepoint_id": np.tile(np.array(range(num_timepoints)), num_samples),
        "sample_id": np.repeat(np.array(range(num_samples)), num_timepoints),
    }

    # Parameters
    d = {
        **d,
        **{
            f"{k}_param": np.repeat(v, num_timepoints)
            for k, v in pyciemss_results["params"].items()
        },
    }

    # Solution (state variables)
    d = {
        **d,
        **{
            f"{k}_sol": np.squeeze(v.reshape((num_timepoints * num_samples, 1)))
            for k, v in pyciemss_results["states"].items()
        },
    }

    df = pandas.DataFrame(d)

    # Write to CSV
    df.to_csv("pyciemss_results.csv", index=False)


def update_tds_status(url, status, result_files=[], start=False, finish=False):
    logging.info(f"Updating simulation `{url}` -- {status} start: {start}; finish: {finish}; result_files: {result_files}")
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

def fetch_model(model_config_id, tds_api, config_endpoint):
    logging.info(f"Fetching model {model_config_id}")
    url_components = [tds_api, config_endpoint, model_config_id]
    model_url = ""
    for component in url_components:
        model_url = urllib.parse.urljoin(model_url, component)
    model_response = requests.get(model_url)
    amr_path = os.path.abspath(f"./{model_config_id}.json")
    with open(amr_path, "w") as file:
        json.dump(model_response.json()["configuration"], file)
    return amr_path


def fetch_dataset(dataset: dict, tds_api):
    logging.info(f"Fetching dataset {dataset['id']}")
    dataset_url = f"{tds_api}/datasets/{dataset['id']}/download-url?filename={dataset['filename']}"
    response = requests.get(dataset_url)
    df = pandas.read_csv(response.json()["url"])
    df = df.rename(columns=dataset["mappings"])
    dataset_path = os.path.abspath("./temp.json")
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
        logging.info(f"{job_id} ran into error")

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
                f"Elapsed time for {function.__name__} for {kwargs['username']}:",
                end_time - start_time
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