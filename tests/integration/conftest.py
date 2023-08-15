from mock import patch
from uuid import UUID
import pytest

from fastapi.testclient import TestClient
from fakeredis import FakeStrictRedis

from service.api import app


@pytest.fixture
def redis(environment, autouse=True):
    if environment.MOCK_REDIS:
        with patch("service.utils.get_redis", return_value=FakeStrictRedis()):
            yield
    else:
        yield


@pytest.fixture
def patch_uuid(request, autouse=True):
    if "example_context" in request.fixturenames:
        context = request.getfixturevalue("example_context")
        job_id = context["tds_simulation"]["id"]
        with patch(
            "uuid.uuid4",
            return_value=UUID(job_id.strip("ciemss-")),
        ):
            yield
    else:
        yield


@pytest.fixture
def client():
    return TestClient(app)
