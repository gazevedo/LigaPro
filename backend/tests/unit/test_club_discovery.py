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
