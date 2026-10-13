from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

from fastapi import HTTPException

from app.main import app
from app.repositories.game import GameRepository
from app.services.game import SquadService


def create_club(client):
    response = client.post(
        "/api/clubs", json={"name": "Clube Camisas", "country_id": "BR", "badge_id": "blue"}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_shirt_number_endpoint_validates_duplicates_range_and_ownership(authenticated_client):
    client = authenticated_client
    club = create_club(client)
    players = client.get("/api/squad").json()["players"]
    assert len({p["shirt_number"] for p in players}) == 25
    target, other = players[:2]
    route = f"/api/squad/players/{target['id']}/shirt-number"
    assert client.put(route, json={"number": other["shirt_number"]}).status_code == 409
    for number in (0, 100, "11", True):
        assert client.put(route, json={"number": number}).status_code == 422
    response = client.put(route, json={"number": 99})
    assert response.status_code == 200
    assert response.json()["shirt_number"] == 99
    assert (
        next(p for p in client.get("/api/squad").json()["players"] if p["id"] == target["id"])[
            "shirt_number"
        ]
        == 99
    )
    from bson import ObjectId

    outsider = app.state.database.players.find_one(
        {"current_club_id": {"$ne": ObjectId(club["id"])}}
    )
    assert (
        client.put(
            f"/api/squad/players/{outsider['_id']}/shirt-number", json={"number": 98}
        ).status_code
        == 403
    )


def test_concurrent_assignment_keeps_shirt_numbers_unique(authenticated_client):
    client = authenticated_client
    club = create_club(client)
    players = client.get("/api/squad").json()["players"][:2]
    repo = GameRepository(app.state.database)
    from bson import ObjectId

    owner = app.state.database.clubs.find_one({"_id": ObjectId(club["id"])})["owner_user_id"]
    user = SimpleNamespace(id=str(owner))

    def assign(player):
        try:
            return SquadService(repo).shirt_number(user, player["id"], 99)
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(assign, players))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert results.count(409) == 1
    updated = client.get("/api/squad").json()["players"]
    assert len({p["shirt_number"] for p in updated}) == 25


def test_missing_legacy_numbers_are_assigned_once(authenticated_client):
    from bson import ObjectId

    client = authenticated_client
    club = create_club(client)
    app.state.database.players.update_many(
        {"current_club_id": ObjectId(club["id"])}, {"$unset": {"shirt_number": ""}}
    )
    first = client.get("/api/squad").json()["players"]
    second = client.get("/api/squad").json()["players"]
    assert {p["id"]: p["shirt_number"] for p in first} == {
        p["id"]: p["shirt_number"] for p in second
    }
    assert len({p["shirt_number"] for p in first}) == 25
