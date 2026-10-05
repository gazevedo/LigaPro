from unittest.mock import patch

from bson import ObjectId
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.main import app


def test_health_and_docs(authenticated_client):
    response = authenticated_client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "api": "ok", "mongodb": "ok"}
    assert authenticated_client.get("/docs").status_code == 200
    assert authenticated_client.get("/openapi.json").json()["info"]["version"] == "0.1.0"


def test_settings_roundtrip_and_upsert(authenticated_client):
    assert authenticated_client.get("/api/settings").json() == []
    first = authenticated_client.put("/api/settings/language", json={"value": "pt-BR"})
    assert first.status_code == 200
    data = first.json()
    assert "_id" not in data
    assert ObjectId.is_valid(data["id"])
    assert data["created_at"].endswith("Z")
    second = authenticated_client.put(
        "/api/settings/language", json={"value": {"code": "en"}}
    ).json()
    assert second["id"] == data["id"]
    assert second["created_at"] == data["created_at"]
    assert second["updated_at"] >= data["updated_at"]
    assert authenticated_client.get("/api/settings/language").json() == second
    assert authenticated_client.get("/api/settings").json() == [second]
    assert app.state.database["app_settings"].count_documents({}) == 1


def test_missing_and_invalid_settings(authenticated_client):
    assert authenticated_client.get("/api/settings/absent").status_code == 404
    assert authenticated_client.put("/api/settings/key", json={}).status_code == 422
    assert (
        authenticated_client.put("/api/settings/" + "x" * 101, json={"value": 1}).status_code == 422
    )
    assert (
        authenticated_client.put("/api/settings/nullable", json={"value": None}).status_code == 200
    )


def test_key_unique_index(authenticated_client):
    import pytest

    collection = app.state.database["app_settings"]
    collection.insert_one({"key": "unique"})
    with pytest.raises(DuplicateKeyError):
        collection.insert_one({"key": "unique"})


def test_database_unavailable_has_safe_error(authenticated_client):
    with patch("app.services.health.HealthService.check", side_effect=PyMongoError("secret")):
        response = authenticated_client.get("/api/health")
    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}


def test_unexpected_error_has_no_trace(authenticated_client):
    with patch("app.services.settings.SettingsService.list", side_effect=RuntimeError("secret")):
        response = authenticated_client.get("/api/settings")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
