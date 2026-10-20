from unittest.mock import Mock

from bson import ObjectId

from app.controllers.game import club_ranking, club_squad


def test_ranking_includes_all_divisions_without_the_default_row_limit():
    repo = Mock()
    repo.many.return_value = []
    assert club_ranking(repo) == []
    assert repo.many.call_args.kwargs["limit"] is None
    assert repo.many.call_args.kwargs["sort"] == [("ranking_position", 1)]


def test_opponent_roster_uses_current_club_and_hides_private_player_fields():
    repo = Mock()
    identity = ObjectId()
    repo.document.return_value = {"_id": identity}
    repo.many.return_value = [
        {
            "_id": ObjectId(),
            "name": "Jogador",
            "position": "GK",
            "strength": 50,
            "age": 25,
            "potential": 90,
        }
    ]
    result = club_squad(str(identity), repo)
    assert result[0]["name"] == "Jogador"
    assert "potential" not in result[0]
    assert repo.many.call_args.args[1] == {
        "current_club_id": identity,
        "status": {"$ne": "retired"},
    }


def test_paginated_ranking_counts_all_active_clubs_and_requests_only_one_page():
    repo = Mock()
    repo.session = None
    repo.database.clubs.count_documents.return_value = 45
    repo.many.return_value = [{"_id": "club", "name": "Novo", "ranking_position": 0}]
    result = club_ranking(repo, page=2, page_size=20)
    assert result["total"] == 45 and result["pages"] == 3 and result["page"] == 2
    assert result["items"][0]["name"] == "Novo"
    repo.database.clubs.count_documents.assert_called_once_with(
        {"active": {"$ne": False}}, session=None
    )
    assert repo.many.call_args.kwargs["skip"] == 20
    assert repo.many.call_args.kwargs["limit"] == 20
    assert repo.many.call_args.kwargs["sort"] == [("ranking_points", -1), ("_id", 1)]


def test_empty_paginated_ranking_has_one_empty_page():
    repo = Mock()
    repo.database.clubs.count_documents.return_value = 0
    repo.many.return_value = []
    result = club_ranking(repo, page=1, page_size=20)
    assert result["items"] == [] and result["pages"] == 1
