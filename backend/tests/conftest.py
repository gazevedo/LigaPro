import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

os.environ.setdefault("MONGODB_CONNECTION_STRING", "mongodb://localhost:27017")
os.environ["MONGODB_DATABASE_NAME"] = f"ligapro_test_{uuid4().hex}"

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    mongo = MongoClient(os.environ["MONGODB_CONNECTION_STRING"])
    mongo.drop_database(os.environ["MONGODB_DATABASE_NAME"])
    mongo.close()


@pytest.fixture(autouse=True)
def clear_settings(client):
    app.state.database["app_settings"].delete_many({})
