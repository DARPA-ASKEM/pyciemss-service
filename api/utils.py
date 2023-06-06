# WIP
from __future__ import annotations
from ast import Dict
import logging
import os
import time
from typing import Any, Optional

from fastapi import APIRouter, Response, File, UploadFile, status
from rq import Queue
from rq.job import Job
from rq.exceptions import NoSuchJobError
from redis import Redis

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


# REDIS CONNECTION AND QUEUE OBJECTS
redis = Redis(
    os.environ.get("REDIS_HOST", "redis.pyciemss-api"),
    os.environ.get("REDIS_PORT", "6379"),
)
q = Queue(connection=redis, default_timeout=-1)

def job(uuid: str, job_string: str, options: Optional[Dict[Any, Any]] = None):
    if options is None:
        options = {}

    force_restart = options.pop("force_restart", False)
    synchronous = options.pop("synchronous", False)
    timeout = options.pop("timeout", 60)
    recheck_delay = 0.5

    job_id = f"{uuid}_{job_string}"
    job = q.fetch_job(job_id)

    if job and force_restart:
        job.cleanup(ttl=0)  # Cleanup/remove data immediately

    if not job or force_restart:

        job = q.enqueue_call(
            func=job_string, args=[], kwargs=options, job_id=job_id
        )
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
        "job_error": job_error,
        "result": job_result,
    }
    return response

def fetch_job_status(job_id):
    """Fetch a job's results from RQ.

    Args:
        job_id (str): The id of the job being run in RQ. Comes from the job/enqueue/{job_string} endpoint.

    Returns:
        Response:
            status_code: 200 if successful, 404 if job does not exist.
            content: contains the job's results.
    """
    try:
        job = Job.fetch(job_id, connection=redis)
        result = job.result
        return result
    except NoSuchJobError:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f"Job with id = {job_id} not found",
        )