import pytest

from rq import SimpleWorker, Queue
from fastapi.testclient import TestClient
from fakeredis import FakeStrictRedis

from service.api import app, get_redis


@pytest.fixture
def redis(environment):
    if not environment.LIVE_REDIS:
        return FakeStrictRedis()
    else:
        return None


@pytest.fixture
def worker(redis):
    if redis is not None:
        queue = Queue(connection=redis, default_timeout=-1)
        return SimpleWorker([queue], connection=redis)
    return None


@pytest.fixture
def client(redis):
    if redis is not None:
        app.dependency_overrides[get_redis] = lambda: redis
    yield TestClient(app)
    app.dependency_overrides[get_redis] = get_redis
