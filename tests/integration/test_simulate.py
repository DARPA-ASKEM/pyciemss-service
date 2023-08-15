# import json

import pytest

from service.settings import settings

TDS_URL = settings.TDS_URL


@pytest.mark.example_dir("simulate")
def test_simulate_example(example_context, client, requests_mock):
    job_id = example_context["tds_simulation"]["id"]
    request = example_context["request"]
    # config_id = request["model_config_id"]
    # model = json.loads(example_context["fetch"](config_id + ".json"))

    requests_mock.post(f"{TDS_URL}/simulations/", json={"id": None})

    full_response = client.post(
        "/simulate",
        json=request,
        headers={"Content-Type": "application/json"},
    )
    response = full_response.json()

    assert response["simulation_id"] == job_id
