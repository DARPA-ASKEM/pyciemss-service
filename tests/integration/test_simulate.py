import json

import pytest

from service.settings import settings

TDS_URL = settings.TDS_URL


@pytest.mark.example_dir("simulate")
def test_simulate_example(example_context, client, worker, file_storage, requests_mock):
    request = example_context["request"]
    config_id = request["model_config_id"]
    model = json.loads(example_context["fetch"](config_id + ".json"))

    requests_mock.post(f"{TDS_URL}/simulations/", json={"id": None})

    response = client.post(
        "/simulate",
        json=request,
        headers={"Content-Type": "application/json"},
    )
    simulation_id = response.json()["simulation_id"]
    response = client.get(
        f"/status/{simulation_id}",
    )
    status = response.json()["status"]
    assert status == "queued"

    tds_sim = example_context["tds_simulation"]
    tds_sim["id"] = simulation_id

    requests_mock.get(f"{TDS_URL}/simulations/{simulation_id}", json=tds_sim)
    requests_mock.put(
        f"{TDS_URL}/simulations/{simulation_id}", json={"status": "success"}
    )
    requests_mock.get(f"{TDS_URL}/model_configurations/{config_id}", json=model)

    # TODO: Mock PyCIEMSS lib
    worker.work(burst=True)

    response = client.get(
        f"/status/{simulation_id}",
    )
    status = response.json()["status"]
    assert status == "complete"
