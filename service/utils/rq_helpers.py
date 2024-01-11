# WIP
from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import Response, status
from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from settings import settings
from utils.tds import update_tds_status, create_tds_job, cancel_tds_job

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


def get_redis():
    return Redis(settings.REDIS_HOST, settings.REDIS_PORT)


def update_status_on_job_fail(job, connection, etype, value, traceback):
    update_tds_status(str(job.id), "error")
    log_message = f"""
        ###############################

        There was an exception in CIEMSS Service

        job: {job.id}
        {etype}: {value}
        ################################
    """
    logging.exception(log_message)


def create_job(request_payload, sim_type, redis_conn):
    workflow_id = f"ciemss-{uuid4()}"

    payload = {
        "name": workflow_id,
        "execution_payload": request_payload.dict(),
        "result_files": [],
        "type": sim_type,
        "status": "queued",
        "engine": request_payload.engine,
        "workflow_id": workflow_id,
    }
    logging.info(payload)

    res = create_tds_job(payload)
    job_id = res["id"]

    logging.info(res)

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
        job_id (uuid): The id of the job being run in RQ.

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

        cancel_tds_job(str(job_id))

        result = job.get_status()
        return result
