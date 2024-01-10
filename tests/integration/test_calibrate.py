import json

import pytest

from service.settings import settings

TDS_URL = settings.TDS_URL


@pytest.mark.example_dir("calibrate")
def test_calibrate_example(
    example_context, client, worker, file_storage, file_check, requests_mock
):
    request = example_context["request"]
    config_id = request["model_config_id"]
    model = json.loads(example_context["fetch"](config_id + ".json"))

    dataset_id = example_context["request"]["dataset"]["id"]
    filename = example_context["request"]["dataset"]["filename"]
    dataset = example_context["fetch"](filename, True)
    dataset_loc = {"method": "GET", "url": dataset}
    requests_mock.get(
        f"{TDS_URL}/datasets/{dataset_id}/download-url?filename={filename}",
        json=dataset_loc,
    )

    requests_mock.post(f"{TDS_URL}/simulations/", json={"id": None})

    response = client.post(
        "/calibrate",
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

    worker.work(burst=True)

    response = client.get(
        f"/status/{simulation_id}",
    )
    status = response.json()["status"]
    params = file_storage("parameters.pickle")
    # viz = file_storage("visualization.json")
    # eval = file_storage("eval.csv") # NOTE: Do we want to check this

    # Checks
    assert status == "complete"

    assert params is not None

    # assert viz is not None
    # assert file_check("json", viz)
