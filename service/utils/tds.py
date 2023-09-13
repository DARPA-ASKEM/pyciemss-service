"""
Module used to interact with the Terarium Data Service (TDS)    
"""
from __future__ import annotations

import logging
import urllib
import os
import shutil
import json
import requests
import dill
from datetime import datetime

from fastapi import HTTPException


from settings import settings

TDS_SIMULATIONS = "/simulations/"
TDS_URL = settings.TDS_URL


def update_tds_status(url, status, result_files=[], start=False, finish=False):
    logging.debug(
        "Updating simulation `%s` -- %s start: %s; finish: %s; result_files: %s",
        url,
        status,
        start,
        finish,
        result_files,
    )
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


def get_job_dir(job_id):
    path = os.path.join("/tmp", str(job_id))
    os.makedirs(path, exist_ok=True)
    return path


def cleanup_job_dir(job_id):
    path = get_job_dir(job_id)
    shutil.rmtree(path)


def fetch_model(model_config_id, tds_api, config_endpoint, job_id):
    job_dir = get_job_dir(job_id)
    logging.debug(f"Fetching model {model_config_id}")
    url_components = [tds_api, config_endpoint, model_config_id]
    model_url = ""
    for component in url_components:
        model_url = urllib.parse.urljoin(model_url, component)
    model_response = requests.get(model_url)
    if model_response.status_code == 404:
        raise HTTPException(status_code=404, detail="Model not found")
    amr_path = os.path.join(job_dir, f"./{model_config_id}.json")
    with open(amr_path, "w") as file:
        json.dump(model_response.json()["configuration"], file)
    return amr_path


def fetch_dataset(dataset: dict, tds_api, job_id):
    import pandas as pd

    job_dir = get_job_dir(job_id)
    logging.debug(f"Fetching dataset {dataset['id']}")
    dataset_url = (
        f"{tds_api}/datasets/{dataset['id']}/"
        f"download-url?filename={dataset['filename']}"
    )
    response = requests.get(dataset_url)
    if response.status_code >= 300:
        raise HTTPException(status_code=400, detail="Unable to retrieve dataset")
    df = pd.read_csv(response.json()["url"])
    df = df.rename(columns=dataset["mappings"])
    # drop columns that aren't being mapped
    if len(df.columns) > len(dataset["mappings"]) and len(dataset["mappings"]) > 0:
        extra_columns = set(df.columns) - set(dataset["mappings"].values())
        df.drop(columns=list(extra_columns), inplace=True)
    dataset_path = os.path.join(job_dir, "./temp.json")
    with open(dataset_path, "w") as file:
        df.to_csv(file, index=False)
    return dataset_path


def attach_files(output: dict, tds_api, simulation_endpoint, job_id, status="complete"):
    sim_results_url = tds_api + simulation_endpoint + job_id
    job_dir = get_job_dir(job_id)
    files = {}

    output_filename = os.path.join(job_dir, "./result.csv")
    data_result = output.get("data", None)
    if data_result is not None:
        data_result.to_csv(output_filename, index=False)
        files[output_filename] = "result.csv"

    eval_output_filename = os.path.join(job_dir, "./eval.csv")
    eval_result = output.get("quantiles", None)
    if eval_result is not None:
        eval_result.to_csv(eval_output_filename, index=False)
        files[eval_output_filename] = "eval.csv"

    params_filename = os.path.join(job_dir, "./parameters.dill")
    params_result = output.get("inferred_parameters", None)
    if params_result:
        with open(params_filename, "wb") as file:
            dill.dump(params_result, file)
        files[params_filename] = "parameters.dill"

    visualization_filename = os.path.join(job_dir, "./visualization.json")
    viz_result = output.get("visual", None)
    if viz_result is not None:
        with open(visualization_filename, "w") as f:
            json.dump(viz_result, f, indent=2)
        files[visualization_filename] = "visualization.json"

    if status != "error":
        for location, handle in files.items():
            upload_url = f"{sim_results_url}/upload-url?filename={handle}"
            upload_response = requests.get(upload_url)
            presigned_upload_url = upload_response.json()["url"]
            with open(location, "rb") as f:
                upload_response = requests.put(presigned_upload_url, f)
                if upload_response.status_code >= 300:
                    raise Exception(
                        (
                            "Failed to upload file to TDS "
                            f"(status: {upload_response.status_code}): {handle}"
                        )
                    )
    else:
        logging.error(f"{job_id} ran into error")

    # Update simulation object with status and filepaths.
    update_tds_status(
        sim_results_url, status=status, result_files=list(files.values()), finish=True
    )
    logging.info("uploaded files to %s", job_id)
