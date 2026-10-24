from unittest.mock import patch

from test_game import account, create

from app.main import app
from mock_database import import_database


def test_authenticated_reset_directly_recreates_initial_universe(client):
    database = app.state.database
    import_database(database)
    admin, other = account(client, 81), account(client, 82)
    create(client, admin)
    path = "/api/settings/database-reset"
    assert client.post(path).status_code == 401
    assert database.users.count_documents({}) == 2
    # On import failure the requester can still retry from Settings.
    with patch("mock_database.import_database", side_effect=RuntimeError("failure")):
        assert client.post(path, headers=other).status_code == 500
    assert client.get("/api/auth/me", headers=other).status_code == 200
    response = client.post(path, headers=other)
    assert response.status_code == 200, response.text
    assert database.users.count_documents({}) == 0
    assert database.user_sessions.count_documents({}) == 0
    assert database.clubs.count_documents({"is_bot": True, "owner_user_id": None}) == 20
    assert database.players.count_documents({}) == 500
    assert database.matches.count_documents({"status": "scheduled"}) == 380
    assert database.standings.count_documents({"games": {"$ne": 0}}) == 0
    assert client.get("/api/auth/me", headers=admin).status_code == 401
    fresh = account(client, 83)
    assert create(client, fresh)["name"] == "Clube teste"
