from urllib.parse import urlparse, parse_qs
import re
import json
import csv
import io
import pytest
import httpx

from rq import SimpleWorker, Queue
from fastapi.testclient import TestClient
from fakeredis import FakeStrictRedis

from service.api import app, get_redis


@pytest.fixture
def redis():
    return FakeStrictRedis()


@pytest.fixture
def worker(redis):
    queue = Queue(connection=redis, default_timeout=-1)
    return SimpleWorker([queue], connection=redis)


@pytest.fixture
def client(redis):
    app.dependency_overrides[get_redis] = lambda: redis
    transport = httpx.ASGITransport(app=app)
    yield TestClient(transport=transport)
    app.dependency_overrides[get_redis] = get_redis


@pytest.fixture
def file_storage(requests_mock):
    storage = {}

    def get_filename(url):
        return parse_qs(urlparse(url).query)["filename"][0]

    def get_loc(request, _):
        filename = get_filename(request.url)
        return {"url": f"https://filesave?filename={filename}"}

    def save(request, context):
        filename = get_filename(request.url)
        try:
            storage[filename] = request.body.read().decode("utf-8")
        except UnicodeDecodeError:
            storage[filename] = request.body.read()
        return {"status": "success"}

    def retrieve(filename):
        return storage.get(filename, storage)

    get_upload_url = re.compile("upload-url")
    requests_mock.get(get_upload_url, json=get_loc)
    upload_url = re.compile("filesave")
    requests_mock.put(upload_url, json=save)

    yield retrieve


# NOTE: This probably doesn't need to be a fixture
@pytest.fixture
def file_check():
    def checker(file_type, content):
        match file_type:
            case "json":
                try:
                    json.loads(content)
                except json.JSONDecodeError:
                    return False
                else:
                    return True
            case "csv":
                result_csv = csv.reader(io.StringIO(content))
                try:
                    i = 0
                    for _ in result_csv:
                        i += 1
                        if i > 10:
                            return True
                    return True
                except csv.Error:
                    return False
            case _:
                raise NotImplementedError("File type cannot be checked")

    return checker
