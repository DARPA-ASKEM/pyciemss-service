# WIP
from __future__ import annotations
import logging
import os

from fastapi import APIRouter, Response, File, UploadFile, status
from rq import Queue
from rq.job import Job
from redis import Redis

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


# REDIS CONNECTION AND QUEUE OBJECTS
redis = Redis(
    os.environ.get("REDIS_HOST", "redis.pyciemss"),
    os.environ.get("REDIS_PORT", "6379"),
)
q = Queue(connection=redis, default_timeout=-1)

def job(uuid: str, job_string: str, options: Optional[Dict[Any, Any]] = None):
    if options is None:
        options = {}

    force_restart = options.pop("force_restart", False)
    synchronous = options.pop("synchronous", False)
    timeout = options.pop("timeout", 60)
    preview = options.get("preview_run", False)
    recheck_delay = 0.5

    job_id = f"{uuid}_{job_string}"
    if preview:
        job_id = job_id + "_preview"
    job = q.fetch_job(job_id)

    context = options.pop("context", None)
    if job and force_restart:
        job.cleanup(ttl=0)  # Cleanup/remove data immediately

    if not job or force_restart:
        try:
            if not context:
                context = get_context(uuid=uuid)
        except Exception as e:
            logging.error(e)

        job = q.enqueue_call(
            func=job_string, args=[context], kwargs=options, job_id=job_id
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