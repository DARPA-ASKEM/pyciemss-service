import logging

# from juliacall import newmodule
from utils.tds import (
    update_tds_status,
    cleanup_job_dir,
    attach_files,
)

from pyciemss.interfaces import (  # noqa: F401
    sample,
    calibrate,
    ensemble_sample,
    ensemble_calibrate,
    optimize,
)

# jl = newmodule("SciMLIntegration")
# jl.seval("using SciMLIntegration, PythonCall")

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def run(request, *, job_id):
    logging.debug(f"STARTED {job_id} (user_id: {request.user_id})")
    update_tds_status(job_id, status="running", start=True)

    # if request.engine == "ciemss":
    operation_name = request.__class__.pyciemss_lib_function
    kwargs = request.gen_pyciemss_args(job_id)
    logger.info(f"{job_id} started with the following args: {kwargs}")
    if len(operation_name) == 0:
        raise Exception("No operation provided in request")
    else:
        output = eval(operation_name)(**kwargs)
    # else:
    #     operation = request.__class__.sciml_lib_function
    #     output = operation(job_id, jl)

    attach_files(output, job_id)
    cleanup_job_dir(job_id)
    logging.debug(f"FINISHED {job_id} (user_id: {request.user_id})")
