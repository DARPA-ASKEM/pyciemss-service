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
import shutil
import requests
from ast import Dict
from typing import Any, Optional
from copy import deepcopy
from datetime import datetime

import pandas
import numpy as np
from fastapi import Response, status
from pydantic import BaseModel
from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from settings import settings
from utils.tds import update_tds_status

TDS_SIMULATIONS = "/simulations/"
TDS_URL = settings.TDS_URL

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


# REDIS CONNECTION AND QUEUE OBJECTS
redis = Redis(
    settings.REDIS_HOST,
    settings.REDIS_PORT
)
q = Queue(connection=redis, default_timeout=-1)


def create_job(operation_name: str, request_payload, sim_type: str):
    random_id = str(uuid.uuid4())
    job_id = f"ciemss-{random_id}"
    job = q.fetch_job(job_id)

    post_url = TDS_URL + TDS_SIMULATIONS #+ job_id
    payload = {
        "id": job_id,
        "execution_payload": request_payload.dict(),
        "result_files": [],
        "type": sim_type,
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

    job = q.enqueue_call(func=operation_name, args=[request_payload], kwargs={"job_id": job_id}, job_id=job_id)

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


def update_status_on_job_fail(function):
    """
    decorator that catches failed wrapped rq jobs and make sure the simulation status is set in tds.
    """
    def wrapped(request, *, job_id):
        try:
            start_time = time.perf_counter()
            result = function(request, job_id=job_id)
            end_time = time.perf_counter()
            logging.info(
                "Elapsed time for %s for %s: %f",
                function.__name__, request.username, end_time - start_time
                )
            return result
        except Exception as e:

            log_message = f"""
                ###############################

                There was an exception in CIEMSS Service
                
                Error occured in function: {function.__name__}

                Username: {request.username}

                ################################
            """
            logging.exception(log_message)
            raise e
    return wrapped