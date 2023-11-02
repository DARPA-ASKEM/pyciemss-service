import json
from inspect import signature

import pytest

from pyciemss.interfaces import sample  # noqa: F401

from service.models import (
    Simulate,
    Calibrate,
    OptimizeSimulate,
    OptimizeCalibrate,
    EnsembleSimulate,
    EnsembleCalibrate,
)
from service.settings import settings

TDS_URL = settings.TDS_URL


def is_satisfactory(kwargs, f):
    parameters = signature(f).parameters
    for key, value in kwargs.items():
        if key in parameters:
            # TODO: Check types as well
            # param = parameters[key]
            # if param.annotation != Signature.empty and not isinstance(
            #     value, param.annotation
            # ):
            #     return False
            continue
        return False
    return True


class TestSimulate:
    @pytest.mark.example_dir("simulate")
    def test_example_conversion(self, example_context, requests_mock):
        job_id = example_context["tds_simulation"]["id"]

        config_id = example_context["request"]["model_config_id"]
        model = json.loads(example_context["fetch"](config_id + ".json"))
        requests_mock.get(f"{TDS_URL}/model_configurations/{config_id}", json=model)

        ### Act and Assert

        operation_request = Simulate(**example_context["request"])
        kwargs = operation_request.gen_pyciemss_args(job_id)

        assert kwargs.get("visual_options", False)
        assert is_satisfactory(kwargs, sample)


class TestCalibrate:
    @pytest.mark.example_dir("calibrate")
    def test_example_conversion(self, example_context, requests_mock):
        job_id = example_context["tds_simulation"]["id"]

        config_id = example_context["request"]["model_config_id"]
        model = json.loads(example_context["fetch"](config_id + ".json"))
        requests_mock.get(f"{TDS_URL}/model_configurations/{config_id}", json=model)

        dataset_id = example_context["request"]["dataset"]["id"]
        filename = example_context["request"]["dataset"]["filename"]
        dataset = example_context["fetch"](filename, True)
        dataset_loc = {"method": "GET", "url": dataset}
        requests_mock.get(
            f"{TDS_URL}/datasets/{dataset_id}/download-url?filename={filename}",
            json=dataset_loc,
        )

        ### Act and Assert
        operation_request = Calibrate(**example_context["request"])
        kwargs = operation_request.gen_pyciemss_args(job_id)

        assert kwargs.get("visual_options", False)
        assert is_satisfactory(kwargs, sample)


class TestOptimizeSimulate:
    @pytest.mark.example_dir("optimize-simulate")
    def test_example_conversion(self, example_context, requests_mock):
        job_id = example_context["tds_simulation"]["id"]

        config_id = example_context["request"]["model_config_id"]
        model = json.loads(example_context["fetch"](config_id + ".json"))
        requests_mock.get(f"{TDS_URL}/model_configurations/{config_id}", json=model)

        ### Act and Assert

        operation_request = OptimizeSimulate(**example_context["request"])
        kwargs = operation_request.gen_pyciemss_args(job_id)

        assert kwargs.get("visual_options", False)
        assert is_satisfactory(kwargs, sample)


class TestOptimizeCalibrate:
    @pytest.mark.example_dir("optimize-calibrate")
    def test_example_conversion(self, example_context, requests_mock):
        job_id = example_context["tds_simulation"]["id"]

        config_id = example_context["request"]["model_config_id"]
        model = json.loads(example_context["fetch"](config_id + ".json"))
        requests_mock.get(f"{TDS_URL}/model_configurations/{config_id}", json=model)

        dataset_id = example_context["request"]["dataset"]["id"]
        filename = example_context["request"]["dataset"]["filename"]
        dataset = example_context["fetch"](filename, True)
        dataset_loc = {"method": "GET", "url": dataset}
        requests_mock.get(
            f"{TDS_URL}/datasets/{dataset_id}/download-url?filename={filename}",
            json=dataset_loc,
        )

        ### Act and Assert
        operation_request = OptimizeCalibrate(**example_context["request"])
        kwargs = operation_request.gen_pyciemss_args(job_id)

        assert kwargs.get("visual_options", False)
        assert is_satisfactory(kwargs, sample)


class TestEnsembleSimulate:
    @pytest.mark.example_dir("ensemble-simulate")
    def test_example_conversion(self, example_context, requests_mock):
        job_id = example_context["tds_simulation"]["id"]

        config_ids = [
            config["id"] for config in example_context["request"]["model_configs"]
        ]
        for config_id in config_ids:
            model = json.loads(example_context["fetch"](config_id + ".json"))
            requests_mock.get(f"{TDS_URL}/model_configurations/{config_id}", json=model)

        ### Act and Assert

        operation_request = EnsembleSimulate(**example_context["request"])
        kwargs = operation_request.gen_pyciemss_args(job_id)

        assert kwargs.get("visual_options", False)
        assert is_satisfactory(kwargs, sample)


class TestEnsembleCalibrate:
    @pytest.mark.example_dir("ensemble-calibrate")
    def test_example_conversion(self, example_context, requests_mock):
        job_id = example_context["tds_simulation"]["id"]

        config_ids = [
            config["id"] for config in example_context["request"]["model_configs"]
        ]
        for config_id in config_ids:
            model = json.loads(example_context["fetch"](config_id + ".json"))
            requests_mock.get(f"{TDS_URL}/model_configurations/{config_id}", json=model)

        dataset_id = example_context["request"]["dataset"]["id"]
        filename = example_context["request"]["dataset"]["filename"]
        dataset = example_context["fetch"](filename, True)
        dataset_loc = {"method": "GET", "url": dataset}
        requests_mock.get(
            f"{TDS_URL}/datasets/{dataset_id}/download-url?filename={filename}",
            json=dataset_loc,
        )
        requests_mock.get("http://dataset", text=dataset)

        ### Act and Assert

        operation_request = EnsembleCalibrate(**example_context["request"])
        kwargs = operation_request.gen_pyciemss_args(job_id)

        assert kwargs.get("visual_options", False)
        assert is_satisfactory(kwargs, sample)
