import json
import os

from mock import patch
import pytest

from service.models import Simulate, Calibrate, EnsembleSimulate, EnsembleCalibrate
from service.settings import settings

TDS_URL = settings.TDS_URL


@pytest.fixture
def operation_context(request):
    ctx = {}
    chosen = request.node.get_closest_marker("operation").args[0]
    path_prefix = f"./tests/examples/{chosen}"
    with open(f"{path_prefix}/input/request.json", "r") as file:
        ctx["request"] = json.load(file)
    with open(f"{path_prefix}/output/tds_simulation.json", "r") as file:
        ctx["tds_simulation"] = json.load(file)

    def fetch(handle):
        io_dir = (
            "input" if os.path.exists(f"{path_prefix}/input/{handle}") else "output"
        )
        with open(f"./tests/examples/{chosen}/{io_dir}/{handle}", "r") as file:
            return file.read()

    ctx["fetch"] = fetch
    return ctx


class TestSimulate:
    @pytest.mark.operation("simulate")
    def test_example_conversion(self, operation_context, requests_mock):
        job_id = operation_context["tds_simulation"]["id"]

        config_id = operation_context["request"]["model_config_id"]
        model = json.loads(operation_context["fetch"](config_id + ".json"))
        requests_mock.get(f"{TDS_URL}/model_configurations/{config_id}", json=model)

        ### Act and Assert

        operation_request = Simulate(**operation_context["request"])
        kwargs = operation_request.gen_pyciemss_args(job_id)

        assert kwargs.get("visual_options", False)


class TestCalibrate:
    @pytest.mark.operation("calibrate")
    def test_example_conversion(self, operation_context, requests_mock):
        job_id = operation_context["tds_simulation"]["id"]

        config_id = operation_context["request"]["model_config_id"]
        model = json.loads(operation_context["fetch"](config_id + ".json"))
        requests_mock.get(f"{TDS_URL}/model_configurations/{config_id}", json=model)

        dataset_id = operation_context["request"]["dataset"]["id"]
        filename = operation_context["request"]["dataset"]["filename"]
        dataset = operation_context["fetch"](filename)
        dataset_loc = {"method": "GET", "url": "http://dataset"}
        requests_mock.get(
            f"{TDS_URL}/datasets/{dataset_id}/download-url?filename={filename}",
            json=dataset_loc,
        )
        requests_mock.get("http://dataset", text=dataset)

        ### Act and Assert

        with patch("service.models.gen_rabbitmq_hook", return_value=lambda _: None):
            operation_request = Calibrate(**operation_context["request"])
            kwargs = operation_request.gen_pyciemss_args(job_id)

        assert kwargs.get("visual_options", False)


class TestEnsembleSimulate:
    @pytest.mark.operation("ensemble-simulate")
    def test_example_conversion(self, operation_context, requests_mock):
        job_id = operation_context["tds_simulation"]["id"]

        config_ids = [
            config["id"] for config in operation_context["request"]["model_configs"]
        ]
        for config_id in config_ids:
            model = json.loads(operation_context["fetch"](config_id + ".json"))
            requests_mock.get(f"{TDS_URL}/model_configurations/{config_id}", json=model)

        ### Act and Assert

        operation_request = EnsembleSimulate(**operation_context["request"])
        kwargs = operation_request.gen_pyciemss_args(job_id)

        assert kwargs.get("visual_options", False)


class TestEnsembleCalibrate:
    @pytest.mark.operation("ensemble-calibrate")
    def test_example_conversion(self, operation_context, requests_mock):
        job_id = operation_context["tds_simulation"]["id"]

        config_ids = [
            config["id"] for config in operation_context["request"]["model_configs"]
        ]
        for config_id in config_ids:
            model = json.loads(operation_context["fetch"](config_id + ".json"))
            requests_mock.get(f"{TDS_URL}/model_configurations/{config_id}", json=model)

        dataset_id = operation_context["request"]["dataset"]["id"]
        filename = operation_context["request"]["dataset"]["filename"]
        dataset = operation_context["fetch"](filename)
        dataset_loc = {"method": "GET", "url": "http://dataset"}
        requests_mock.get(
            f"{TDS_URL}/datasets/{dataset_id}/download-url?filename={filename}",
            json=dataset_loc,
        )
        requests_mock.get("http://dataset", text=dataset)

        ### Act and Assert

        operation_request = EnsembleCalibrate(**operation_context["request"])
        kwargs = operation_request.gen_pyciemss_args(job_id)

        assert kwargs.get("visual_options", False)
