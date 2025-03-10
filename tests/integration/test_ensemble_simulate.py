import json

import pytest

from service.settings import settings

TDS_URL = settings.TDS_URL


@pytest.mark.example_dir("ensemble-simulate")
def test_ensemble_simulate_example(
    example_context, client, worker, file_storage, file_check, requests_mock
):
    job_id = "9036f8a8-7e55-4e77-aeec-e8d4ca120d67"

    request = example_context["request"]
    config_ids = [
        config["id"] for config in example_context["request"]["model_configs"]
    ]
    for config_id in config_ids:
        model = json.loads(example_context["fetch"](config_id + ".json"))
        requests_mock.get(
            f"{TDS_URL}/model-configurations/{config_id}/model",
            json=model,
        )

    requests_mock.post(f"{TDS_URL}/simulations", json={"id": str(job_id)})

    response = client.post(
        "/ensemble-simulate",
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

    worker.work(burst=True)

    response = client.get(
        f"/status/{simulation_id}",
    )
    status = response.json()["status"]
    result = file_storage("result.csv")
    # viz = file_storage("visualization.json")
    # eval = file_storage("eval.csv") # NOTE: Do we want to check this

    # Checks
    assert status == "complete"

    assert result is not None
    assert file_check("csv", result)

    # assert viz is not None
    # assert file_check("json", viz)
