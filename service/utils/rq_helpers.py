# WIP
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
from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from settings import settings
from utils.tds import update_tds_status

OUTPUT_FILENAME = settings.PYCIEMSS_OUTPUT_FILEPATH
TDS_SIMULATIONS = "/simulations/"
TDS_URL = settings.TDS_URL

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


# REDIS CONNECTION AND QUEUE OBJECTS
redis = Redis(
    os.environ.get("REDIS_HOST", "redis.pyciemss-api"),
    os.environ.get("REDIS_PORT", "6379"),
)
q = Queue(connection=redis, default_timeout=-1)

def make_job_dir(job_id):
    path = os.path.join("/tmp", str(job_id))    
    os.makedirs(path)
    return path

def create_job(operation_name: str, options: Optional[Dict[Any, Any]] = None):
    if options is None:
        options = {}

    engine = options.pop("engine", "ciemss")
    force_restart = options.pop("force_restart", False)
    synchronous = options.pop("synchronous", False)
    timeout = options.pop("timeout", 60)
    recheck_delay = 0.5

    assert engine.split(".")[-1] == "ciemss"
    engine_prefix = options.get("engine", "ciemss")
    random_id = str(uuid.uuid4())

    job_id = f"{engine_prefix}-{random_id}"
    options["job_id"] = job_id
    job = q.fetch_job(job_id)

    logging.info(f"OPTIONS: {options}")
    # TODO: Allow extras on payload and simply put full object here
    ex_payload = {
        "engine": "ciemss",
        "model_config_id": options.get("model_config_id", "not_provided"),
        "timespan": {
            "start": options.get("start", 0),
            "end": options.get("end", 1),
        },
        "extra": options.get("extra", None),
    }
    post_url = TDS_URL + TDS_SIMULATIONS #+ job_id
    payload = {
        "id": job_id,
        "execution_payload": ex_payload,
        "result_files": [],
        "type": "simulation",
        "status": "queued",
        "engine": "ciemss",
        "workflow_id": job_id,
    }
    logging.info(payload)
    sys.stdout.flush()
    response = requests.post(post_url, json=payload)
    if response.status_code >= 300:
        raise Exception(f"Failed to create simulation on TDS (status: {response.status_code}): {json.dumps(payload)}")
    logging.info(response.content)

    if job and force_restart:
        job.cleanup(ttl=0)  # Cleanup/remove data immediately

    if not job or force_restart:
        flattened_options = deepcopy(options)
        flattened_options.update(flattened_options.pop("extra"))
        job = q.enqueue_call(func=operation_name, args=[], kwargs=flattened_options, job_id=job_id)
        if synchronous:
            timer = 0.0
            while (
                job.get_status(refresh=True) not in ("finished", "failed")
                and timer < timeout
            ):
                time.sleep(recheck_delay)
                timer += recheck_delay

    status = job.get_status()
    if status in ("finished", "failed"):
        job_result = job.result
        job_error = job.exc_info
        job.cleanup(ttl=0)  # Cleanup/remove data immediately
    else:
        job_result = None
        job_error = None

    response = {
        "id": job_id,
        "created_at": job.created_at,
        "enqueued_at": job.enqueued_at,
        "started_at": job.started_at,
        "status": status,
        "simulation_error": job_error,
        "result": job_result,
    }
    return response


def fetch_job_status(job_id):
    """Fetch a job's results from RQ.

    Args:
        job_id (str): The id of the job being run in RQ. Comes from the job/enqueue/{operation_name} endpoint.

    Returns:
        Response:
            status_code: 200 if successful, 404 if job does not exist.
            content: contains the job's results.
    """
    try:
        job = Job.fetch(job_id, connection=redis)
        # r = job.latest_result()
        # string_res = r.return_value
        result = job.get_status()
        return result
    except NoSuchJobError:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f"Simulation job with id = {job_id} not found",
        )
    

def kill_job(job_id):
    try:
        job = Job.fetch(job_id, connection=redis)
    except NoSuchJobError:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f"Simulation job with id = {job_id} not found",
        )
    else:
        job.cancel()

        url = TDS_URL + TDS_SIMULATIONS + str(job_id)
        tds_payload = requests.get(url).json()
        tds_payload["status"] = "cancelled"
        requests.put(url, json=json.loads(json.dumps(tds_payload, default=str)))

        result = job.get_status()
        return result


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