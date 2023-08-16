from collections import namedtuple
from urllib.parse import urlparse, parse_qs
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


@pytest.fixture
def file_storage():
    storage = {}

    def get_filename(url):
        return parse_qs(urlparse(url).query)["filename"][0]

    def get_loc(request, _):
        filename = get_filename(request.url)
        return {"url": f"filesave?filename={filename}"}

    def save(request, context):
        filename = get_filename(request.url)
        storage[filename] = context
        return {"status": "success"}

    def retrieve(filename):
        return storage[filename]

    Storage = namedtuple("Storage", ["get_loc", "save", "retrieve"])
    yield Storage(get_loc, save, retrieve)
