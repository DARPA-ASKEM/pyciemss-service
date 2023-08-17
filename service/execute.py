import logging

# from juliacall import newmodule
from settings import settings
from utils.rabbitmq import gen_rabbitmq_hook
from utils.tds import (
    update_tds_status,
    cleanup_job_dir,
    attach_files,
)

from pyciemss.PetriNetODE.interfaces import (  # noqa: F401
    load_and_calibrate_and_sample_petri_model,
    load_and_sample_petri_model,
)

from pyciemss.Ensemble.interfaces import (  # noqa: F401
    load_and_sample_petri_ensemble,
    load_and_calibrate_and_sample_ensemble_model,
)


TDS_SIMULATIONS = "/simulations/"
TDS_URL = settings.TDS_URL

# jl = newmodule("SciMLIntegration")
# jl.seval("using SciMLIntegration, PythonCall")

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


def run(request, *, job_id, progress_enabled):
    logging.debug(f"STARTED {job_id} (username: {request.username})")
    sim_results_url = TDS_URL + TDS_SIMULATIONS + job_id
    update_tds_status(sim_results_url, status="running", start=True)

    # if request.engine == "ciemss":
    operation_name = request.__class__.pyciemss_lib_function
    if progress_enabled:
        kwargs = request.gen_pyciemss_args(
            job_id, progress_hook=gen_rabbitmq_hook(job_id)
        )
    else:
        kwargs = request.gen_pyciemss_args(job_id)
    if len(operation_name) == 0:
        raise Exception("No operation provided in request")
    else:
        output = eval(operation_name)(**kwargs)
    # else:
    #     operation = request.__class__.sciml_lib_function
    #     output = operation(job_id, jl)

    attach_files(output, TDS_URL, TDS_SIMULATIONS, job_id)
    cleanup_job_dir(job_id)
    logging.debug(f"FINISHED {job_id} (username: {request.username})")
