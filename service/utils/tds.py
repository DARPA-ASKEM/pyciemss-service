"""
Module used to interact with the Terarium Data Service (TDS)
"""
from __future__ import annotations

import logging

import os
import shutil
import json
import requests
import dill
import numbers
from datetime import datetime
from typing import Optional
import pandas as pd

from fastapi import HTTPException

from settings import settings

TDS_URL = settings.TDS_URL
TDS_USER = settings.TDS_USER
TDS_PASSWORD = settings.TDS_PASSWORD
TDS_SIMULATIONS = "/simulations"
TDS_DATASETS = "/datasets"
TDS_CONFIGURATIONS = "/model-configurations/as-configured-model"
TDS_INTERVENTIONS = "/interventions"


#
# FIXME: remove when pyciemss resolve https://github.com/ciemss/pyciemss/issues/567
#
# Recursively force every numeric looking value in a dict to be float to make it more likely to
# be compatible with tensor datatypes downstream
def shim_float(obj):
    if type(obj) == dict:
        for k, v in obj.items():
            obj[k] = shim_float(v)
    elif type(obj) == list:
        for idx, v in enumerate(obj):
            obj[idx] = shim_float(v)

    if isinstance(obj, numbers.Number):
        return float(obj)
    else:
        return obj


def tds_session():
    session = requests.Session()
    session.auth = (TDS_USER, TDS_PASSWORD)
    session.headers.update(
        {"Content-Type": "application/json", "X-Enable-Snake-Case": ""}
    )
    return session


def create_tds_job(payload):
    post_url = TDS_URL + TDS_SIMULATIONS
    response = tds_session().post(post_url, json=payload)
    if response.status_code >= 300:
        raise Exception(
            (
                "Failed to create simulation on TDS "
                f"(status: {response.status_code}): {json.dumps(payload)}"
            )
        )
    return response.json()


def cancel_tds_job(job_id):
    url = TDS_URL + TDS_SIMULATIONS + "/" + str(job_id)
    tds_payload = tds_session().get(url).json()
    tds_payload["status"] = "cancelled"
    return tds_session().put(url, json=json.loads(json.dumps(tds_payload, default=str)))


def update_tds_status(job_id, status, result_files=[], start=False, finish=False):
    url = TDS_URL + TDS_SIMULATIONS + "/" + str(job_id)
    logging.debug(
        "Updating simulation `%s` -- %s start: %s; finish: %s; result_files: %s",
        url,
        status,
        start,
        finish,
        result_files,
    )
    tds_payload = tds_session().get(url)
    tds_payload = tds_payload.json()

    if start:
        tds_payload["start_time"] = datetime.now().isoformat()
    if finish:
        tds_payload["completed_time"] = datetime.now().isoformat()

    tds_payload["status"] = status
    if result_files:
        tds_payload["result_files"] = result_files

    update_response = tds_session().put(
        url, json=json.loads(json.dumps(tds_payload, default=str))
    )
    if update_response.status_code >= 300:
        logging.debug("error", update_response.reason)
        raise Exception(
            (
                "Failed to update simulation on TDS "
                f"(status: {update_response.status_code}): {json.dumps(tds_payload, default=str)}"
            )
        )

    return update_response


def get_job_dir(job_id):
    path = os.path.join("/tmp", str(job_id))
    os.makedirs(path, exist_ok=True)
    return path


def cleanup_job_dir(job_id):
    path = get_job_dir(job_id)
    shutil.rmtree(path)


def fetch_model(model_config_id, job_id):
    job_dir = get_job_dir(job_id)
    logging.debug(f"Fetching model {model_config_id}")

    model_url = TDS_URL + TDS_CONFIGURATIONS + "/" + model_config_id

    model_response = tds_session().get(model_url)
    if model_response.status_code == 404:
        raise HTTPException(status_code=404, detail="Model not found")

    amr_path = os.path.join(job_dir, f"./{model_config_id}.json")
    with open(amr_path, "w") as file:
        # Ensure we don't have null observables which can be problematic downstream, if so convert
        # to empty list
        model_json = model_response.json()
        if "semantics" in model_json and "ode" in model_json["semantics"]:
            ode = model_json["semantics"]["ode"]
            if "observables" in ode and ode["observables"] is None:
                ode["observables"] = []

        shimmed_model = shim_float(model_json)
        json.dump(shimmed_model, file)
    return amr_path


def fetch_dataset(dataset: dict, job_id):
    job_dir = get_job_dir(job_id)
    logging.debug(f"Fetching dataset {dataset['id']}")
    dataset_url = (
        f"{TDS_URL}{TDS_DATASETS}/{dataset['id']}/"
        f"download-url?filename={dataset['filename']}"
    )
    response = tds_session().get(dataset_url)

    # Small hack to rename mapping, namely timestamp => Timestamp if timestamp exist as a value
    key_to_rename = None
    for item in dataset["mappings"].items():
        if item[1] == "timestamp":
            key_to_rename = item[0]
    if key_to_rename is not None:
        logging.debug(f"Overwriting {key_to_rename}")
        logging.debug("")
        dataset["mappings"][key_to_rename] = "Timestamp"

    if response.status_code >= 300:
        raise HTTPException(status_code=400, detail="Unable to retrieve dataset")

    df = pd.read_csv(response.json()["url"])
    df = df.rename(columns=dataset["mappings"])

    # Shift Timestamp to first position
    col = df.pop("Timestamp")
    df.insert(0, "Timestamp", col)

    # drop columns that aren't being mapped
    if len(df.columns) > len(dataset["mappings"]) and len(dataset["mappings"]) > 0:
        extra_columns = set(df.columns) - set(dataset["mappings"].values())
        df.drop(columns=list(extra_columns), inplace=True)

    dataset_path = os.path.join(job_dir, "./temp.json")
    with open(dataset_path, "w") as file:
        df.to_csv(file, index=False)
    return dataset_path


def fetch_inferred_parameters(parameters_id: Optional[str], job_id):
    if parameters_id is None:
        return
    job_dir = get_job_dir(job_id)
    logging.debug(f"Fetching inferred parameters {parameters_id}")
    download_url = f"{TDS_URL}{TDS_SIMULATIONS}/{parameters_id}/download-url?filename=parameters.dill"

    parameters_url = tds_session().get(download_url).json()["url"]
    # response = tds_session().get(parameters_url)

    response = requests.get(parameters_url)
    if response.status_code >= 300:
        raise HTTPException(status_code=400, detail="Unable to retrieve parameters")
    parameters_path = os.path.join(job_dir, "parameters.dill")
    with open(parameters_path, "wb") as file:
        file.write(response.content)
    return dill.loads(response.content)


def get_result_summary(data_result):
    try:
        df2 = data_result.groupby("timepoint_id", as_index=False).agg(
            ["min", "max", "mean", "median", "std"]
        )
        df2 = df2.drop(columns=["sample_id", "timepoint_unknown"])
        df2.columns = ["_".join(i) for i in df2.columns]
        return df2
    # If the format of the data_result does not match expected column names ect just throw error
    except:
        raise


def attach_files(output: dict, job_id, status="complete"):
    sim_results_url = TDS_URL + TDS_SIMULATIONS + "/" + str(job_id)
    job_dir = get_job_dir(job_id)
    files = {}

    output_filename = os.path.join(job_dir, "./result.csv")
    data_result = output.get("data", None)
    if data_result is not None:
        data_result.to_csv(output_filename, index=False)
        files[output_filename] = "result.csv"
        # Add a result summary file for the HMI to digest.
        try:
            result_summary_filename = os.path.join(job_dir, "./result_summary.csv")
            summary_data = get_result_summary(data_result)
            summary_df = pd.DataFrame.from_records(summary_data)
            summary_df.to_csv(result_summary_filename)
            files[result_summary_filename] = "result_summary.csv"
        except (
            Exception
        ) as error:  # If the result file is a new format do not fail entire simulation run
            logging.error(f"{job_id} get_result_summary ran into error")
            logging.error(error)

    risk_result = output.get("risk", None)
    if risk_result is not None:
        # Update qoi (tensor) to a list before serializing with json.dumps
        for k, v in risk_result.items():
            risk_result[k]["qoi"] = v["qoi"].tolist()
        risk_json_obj = json.dumps(risk_result, default=str)
        json_obj = json.loads(risk_json_obj)
        json_filename = os.path.join(job_dir, "./risk.json")
        with open(json_filename, "w") as f:
            json.dump(json_obj, f, ensure_ascii=False, indent=4)
        files[json_filename] = "risk.json"

    eval_output_filename = os.path.join(job_dir, "./eval.csv")
    eval_result = output.get("quantiles", None)
    if eval_result is not None:
        eval_result.to_csv(eval_output_filename, index=False)
        files[eval_output_filename] = "eval.csv"

    params_filename = os.path.join(job_dir, "./parameters.dill")
    params_result = output.get("inferred_parameters", None)
    if params_result is not None:
        with open(params_filename, "wb") as file:
            dill.dump(params_result, file)
        files[params_filename] = "parameters.dill"

    policy_filename = os.path.join(job_dir, "./policy.json")
    policy = output.get("policy", None)
    if policy is not None:
        with open(policy_filename, "w") as file:
            json.dump(policy.tolist(), file)
        files[policy_filename] = "policy.json"

    results_filename = os.path.join(job_dir, "./optimize_results.dill")
    results = output.get("OptResults", None)
    if results is not None:
        json_obj = json.loads(json.dumps(results, default=str))
        json_filename = os.path.join(job_dir, "./optimize_result.json")
        with open(json_filename, "w") as f:
            json.dump(json_obj, f, ensure_ascii=False, indent=4)
        files[json_filename] = "optimize_results.json"

        with open(results_filename, "wb") as file:
            dill.dump(results, file)
        files[results_filename] = "optimize_results.dill"

    visualization_filename = os.path.join(job_dir, "./visualization.json")
    viz_result = output.get("visual", None)
    if viz_result is not None:
        with open(visualization_filename, "w") as f:
            json.dump(viz_result, f, indent=2)
        files[visualization_filename] = "visualization.json"

    if status != "error":
        for location, handle in files.items():
            upload_url = f"{sim_results_url}/upload-url?filename={handle}"
            upload_response = tds_session().get(upload_url)
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
        job_id, status=status, result_files=list(files.values()), finish=True
    )
    logging.info("uploaded files to %s", job_id)


def fetch_interventions(policy_intervention_id: str, job_id):
    job_dir = get_job_dir(job_id)
    logging.debug(f"Fetching interventions {policy_intervention_id}")

    intervention_url = TDS_URL + TDS_INTERVENTIONS + "/" + policy_intervention_id
    intervention_response = tds_session().get(intervention_url)
    if intervention_response.status_code == 404:
        raise HTTPException(status_code=404, detail="Intervention not found")

    intervention_path = os.path.join(job_dir, f"./{policy_intervention_id}.json")
    with open(intervention_path, "w") as file:
        # Ensure we don't have null observables which can be problematic downstream, if so convert
        # to empty list
        intervention_json = intervention_response.json()
        json.dump(intervention_json, file)

    return intervention_response.json()
