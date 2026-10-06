from datetime import timedelta

from bson import ObjectId
from test_game import account, create

from app.main import app
from app.models.game import utcnow
from app.repositories.game import GameRepository
from app.services.news import NewsService


def setup(client):
    headers = account(client, 71)
    club = ObjectId(create(client, headers)["id"])
    repo = GameRepository(app.state.database)
    repo.database.news_items.delete_many({})
    return headers, club, repo


def test_reading_messages_persists_and_is_idempotent(client):
    headers, club, repo = setup(client)
    NewsService.publish(repo, "financial", "other_income", club, "income-1")
    NewsService.publish(repo, "record", "Recorde do universo", reference="record-1")
    NewsService.publish(repo, "financial", "Mensagem privada", ObjectId(), "other-club")
    inbox = client.get("/api/news/inbox", headers=headers).json()
    assert inbox["total"] == inbox["unread_count"] == 2
    assert all(not item["read"] for item in inbox["items"])
    news_id = inbox["items"][0]["id"]
    before = repo.find("news_items", {"_id": news_id})
    for _ in range(2):
        response = client.post("/api/news/read", headers=headers, json={"news_id": news_id})
        assert response.status_code == 200, response.text
        assert response.json() == {"id": news_id, "read": True}
    # A fresh request has persisted flags and the correct remaining count.
    inbox = client.get("/api/news/inbox", headers=headers).json()
    assert inbox["unread_count"] == 1
    assert next(item for item in inbox["items"] if item["id"] == news_id)["read"]
    assert repo.database.news_reads.count_documents({}) == 1
    assert repo.find("news_items", {"_id": news_id}) == before


def test_private_messages_cannot_be_read_by_another_club(client):
    headers, club, repo = setup(client)
    NewsService.publish(repo, "injury", "Mensagem privada", ObjectId(), "private")
    news_id = repo.database.news_items.find_one()["_id"]
    assert (
        client.post("/api/news/read", headers=headers, json={"news_id": news_id}).status_code == 404
    )
    assert (
        client.post("/api/news/read", headers=headers, json={"news_id": "missing"}).status_code
        == 404
    )
    assert repo.database.news_reads.count_documents({}) == 0
    assert client.get("/api/news/inbox").status_code == 401


def test_global_read_receipts_are_per_user(client):
    headers, _, repo = setup(client)
    second_headers = account(client, 72)
    create(client, second_headers)
    repo.database.news_items.delete_many({})
    NewsService.publish(repo, "record", "Recorde global", reference="global")
    news_id = repo.database.news_items.find_one()["_id"]
    assert (
        client.post("/api/news/read", headers=headers, json={"news_id": news_id}).status_code == 200
    )
    assert client.get("/api/news/inbox", headers=headers).json()["unread_count"] == 0
    second = client.get("/api/news/inbox", headers=second_headers).json()
    assert second["unread_count"] == 1
    assert not second["items"][0]["read"]


def test_pagination_counts_unread_messages_outside_the_first_page(client):
    headers, club, repo = setup(client)
    now = utcnow()
    for index in range(35):
        NewsService.publish(
            repo,
            "financial",
            "other_income",
            club,
            f"income-{index}",
            now=now + timedelta(seconds=index),
        )
    first = client.get("/api/news/inbox", headers=headers).json()
    assert len(first["items"]) == 30
    assert first["total"] == first["unread_count"] == 35
    second = client.get("/api/news/inbox?offset=30", headers=headers).json()
    assert len(second["items"]) == 5
    assert {item["id"] for item in first["items"]}.isdisjoint(
        item["id"] for item in second["items"]
    )
    assert client.get("/api/news/inbox?offset=-1", headers=headers).status_code == 422
