import os
import secrets
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

os.environ.setdefault("JWT_SECRET_KEY", secrets.token_urlsafe(48))
os.environ.setdefault("GOOGLE_WEB_CLIENT_ID", "test-client.apps.googleusercontent.com")
os.environ.setdefault(
    "MONGODB_CONNECTION_STRING", "mongodb://localhost:27017/?directConnection=true"
)
os.environ["MONGODB_DATABASE_NAME"] = f"ligapro_test_{uuid4().hex}"

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    # Tests advance game time explicitly; the real-time worker must not mutate fixtures.
    with (
        patch("app.main.process_due"),
        TestClient(app, raise_server_exceptions=False) as test_client,
    ):
        yield test_client
    mongo = MongoClient(os.environ["MONGODB_CONNECTION_STRING"])
    mongo.drop_database(os.environ["MONGODB_DATABASE_NAME"])
    mongo.close()


@pytest.fixture(autouse=True)
def clear_settings(client):
    for collection in app.state.database.list_collection_names():
        if collection in {"countries", "club_badges"}:
            continue
        app.state.database[collection].delete_many({})


@pytest.fixture
def authenticated_client(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Settings test",
            "email": "settings@example.com",
            "password": "test-pass-123",
        },
    )
    assert response.status_code == 201
    client.headers["Authorization"] = "Bearer " + response.json()["access_token"]
    yield client
    client.headers.pop("Authorization", None)
