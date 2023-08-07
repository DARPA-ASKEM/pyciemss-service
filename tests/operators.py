import json
import os

import pytest
from requests_mock import Mocker


from service.models import Simulate, Calibrate, EnsembleSimulate, EnsembleCalibrate


@pytest.fixture
def operation_context(request):
    ctx = {}
    chosen = request.node.get_closest_marker("operation").args[0]
    path_prefix = f"./tests/examples/{chosen}"
    with open(f"{path_prefix}/input/request.json", "r") as file:
        ctx["request"] = json.load(file)
    with open(f"{path_prefix}/output/tds_simulation.json", "r") as file:
        ctx["tds_simulation"] = json.load(file)

    def fetch(uuid, extension="json"):
        io_dir = (
            "input"
            if os.path.exists(f"{path_prefix}/input/{uuid}.{extension}")
            else "output"
        )
        with open(
            f"./tests/examples/{chosen}/{io_dir}/{uuid}.{extension}", "r"
        ) as file:
            return file.read()

    ctx["fetch"] = fetch
    return ctx


class TestSimulate:
    @Mocker()
    @pytest.mark.operation("simulate")
    def test_example_conversion(self, operation_context, mocker):
        job_id = operation_context["tds_simulation"]["id"]

        operation_request = Simulate(**operation_context["request"])
        kwargs = operation_request.gen_pyciemss_args(job_id)

        assert kwargs.get("visual_options", False)


class TestCalibrate:
    @Mocker()
    @pytest.mark.operation("calibrate")
    def test_example_conversion(self, operation_context, mocker):
        job_id = operation_context["tds_simulation"]["id"]

        operation_request = Calibrate(**operation_context["request"])
        kwargs = operation_request.gen_pyciemss_args(job_id)

        assert kwargs.get("visual_options", False)


class TestEnsembleSimulate:
    @Mocker()
    @pytest.mark.operation("ensemble-simulate")
    def test_example_conversion(self, operation_context, mocker):
        job_id = operation_context["tds_simulation"]["id"]

        operation_request = EnsembleSimulate(**operation_context["request"])
        kwargs = operation_request.gen_pyciemss_args(job_id)

        assert kwargs.get("visual_options", False)


class TestEnsembleCalibrate:
    @Mocker()
    @pytest.mark.operation("ensemble-calibrate")
    def test_example_conversion(self, operation_context, mocker):
        job_id = operation_context["tds_simulation"]["id"]

        operation_request = EnsembleCalibrate(**operation_context["request"])
        kwargs = operation_request.gen_pyciemss_args(job_id)

        assert kwargs.get("visual_options", False)
