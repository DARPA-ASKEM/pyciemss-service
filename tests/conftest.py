import json
import os

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseSettings
from fakeredis import FakeStrictRedis
from rq import Queue


from service.api import app


@pytest.fixture
def client():
    return TestClient(app)


class Environment(BaseSettings):
    IS_LIVE: bool = False


@pytest.fixture
def environment():
    return Environment()


@pytest.fixture
def redis_queue():
    return Queue(is_async=False, connection=FakeStrictRedis())


@pytest.fixture
def example_context(request):
    ctx = {}
    chosen = request.node.get_closest_marker("example_dir").args[0]
    path_prefix = f"./tests/examples/{chosen}"
    with open(f"{path_prefix}/input/request.json", "r") as file:
        ctx["request"] = json.load(file)
    with open(f"{path_prefix}/output/tds_simulation.json", "r") as file:
        ctx["tds_simulation"] = json.load(file)

    def fetch(handle, return_path=False):
        io_dir = (
            "input" if os.path.exists(f"{path_prefix}/input/{handle}") else "output"
        )
        path = f"{path_prefix}/{io_dir}/{handle}"
        if return_path:
            return os.path.abspath(path)
        with open(path, "r") as file:
            return file.read()

    ctx["fetch"] = fetch
    return ctx
