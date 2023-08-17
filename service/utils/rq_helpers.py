# WIP
from __future__ import annotations

import logging
from uuid import uuid4
import json
import requests

from fastapi import Response, status
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


def get_redis():
    return Redis(settings.REDIS_HOST, settings.REDIS_PORT)


def update_status_on_job_fail(job, connection, etype, value, traceback):
    update_tds_status(TDS_URL + TDS_SIMULATIONS + str(job.id), "error")
    log_message = f"""
        ###############################

        There was an exception in CIEMSS Service
    
        job: {job.id}
        {etype}: {value} 
        ################################
    """
    logging.exception(log_message)


def create_job(request_payload, sim_type, redis_conn):
    job_id = f"ciemss-{uuid4()}"

    post_url = TDS_URL + TDS_SIMULATIONS
    payload = {
        "id": job_id,
        "execution_payload": request_payload.dict(),
        "result_files": [],
        "type": sim_type,
        "status": "queued",
        "engine": request_payload.engine,
        "workflow_id": job_id,
    }
    logging.info(payload)
    response = requests.post(post_url, json=payload)
    if response.status_code >= 300:
        raise Exception(
            (
                "Failed to create simulation on TDS "
                f"(status: {response.status_code}): {json.dumps(payload)}"
            )
        )
    logging.info(response.content)

    queue = Queue(connection=redis_conn, default_timeout=-1)
    queue.enqueue_call(
        func="execute.run",
        args=[request_payload],
        kwargs={"job_id": job_id},
        job_id=job_id,
        on_failure=update_status_on_job_fail,
    )

    return {"simulation_id": job_id}


def fetch_job_status(job_id, redis_conn):
    """Fetch a job's results from RQ.

    Args:
        job_id (str): The id of the job being run in RQ.

    Returns:
        Response:
            status_code: 200 if successful, 404 if job does not exist.
            content: contains the job's results.
    """
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        # r = job.latest_result()
        # string_res = r.return_value
        result = job.get_status()
        return result
    except NoSuchJobError:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f"Simulation {job_id} not found",
        )


def kill_job(job_id, redis_conn):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
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
