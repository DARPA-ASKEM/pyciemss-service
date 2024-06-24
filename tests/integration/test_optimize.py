import json

import pytest

from service.settings import settings

TDS_URL = settings.TDS_URL


@pytest.mark.example_dir("optimize")
def test_optimize_example(
    example_context, client, worker, file_storage, file_check, requests_mock
):
    job_id = "9ed74639-7778-4bb9-96fd-7509d68cd425"

    request = example_context["request"]
    config_id = request["model_config_id"]
    model = json.loads(example_context["fetch"](config_id + ".json"))

    requests_mock.post(f"{TDS_URL}/simulations", json={"id": str(job_id)})

    response = client.post(
        "/optimize",
        json=request,
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
    requests_mock.get(
        f"{TDS_URL}/model-configurations/as-configured-model/{config_id}", json=model
    )

    worker.work(burst=True)

    response = client.get(
        f"/status/{simulation_id}",
    )
    status = response.json()["status"]
    policy = file_storage("policy.json")

    # Checks
    assert status == "complete"

    assert policy is not None
    assert file_check("json", policy)
