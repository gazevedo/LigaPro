from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.services.competition import CompetitionService
from app.services.player_statistics import PlayerStatisticsService


def test_selected_division_requires_participation_in_current_season():
    repo = MagicMock()
    season, club = {"_id": ObjectId()}, {"_id": ObjectId()}
    division_id = ObjectId()
    repo.find.side_effect = [{"division_id": division_id}, {"_id": division_id, "name": "B"}]
    service = CompetitionService(repo)
    assert service.selected_division(season, club, str(division_id))["name"] == "B"
    assert repo.find.call_args_list[0].args == (
        "season_clubs",
        {"season_id": season["_id"], "division_id": division_id},
    )
    for identity in ["invalid", str(ObjectId())]:
        repo.find.side_effect = None
        repo.find.return_value = None
        with pytest.raises(HTTPException) as error:
            service.selected_division(season, club, identity)
        assert error.value.status_code == 404


@pytest.mark.parametrize("selected", [False, True])
def test_matches_preserve_club_default_and_filter_selected_series(selected):
    repo = MagicMock()
    season, slot, division = {"_id": ObjectId()}, {"_id": ObjectId()}, {"_id": ObjectId()}
    repo.find.side_effect = [season, slot]
    repo.many.return_value = []
    with patch.object(CompetitionService, "selected_division", return_value=division):
        CompetitionService(repo).matches(
            SimpleNamespace(id="user"), str(division["_id"]) if selected else None
        )
    query = repo.many.call_args_list[0].args[1]
    assert query["season_id"] == season["_id"]
    if selected:
        assert query["division_id"] == division["_id"] and "$or" not in query
    else:
        assert query["$or"] == [{"home_slot_id": slot["_id"]}, {"away_slot_id": slot["_id"]}]


def test_scorers_only_query_completed_matches_from_selected_series():
    repo = MagicMock()
    season, division = {"_id": ObjectId()}, {"_id": ObjectId()}
    repo.find.side_effect = [season, {"division_id": ObjectId()}]
    repo.many.return_value = []
    repo.database.player_match_ratings.aggregate.return_value = []
    with patch.object(CompetitionService, "selected_division", return_value=division):
        PlayerStatisticsService(repo).competition_rankings(
            SimpleNamespace(id="user"), "league", "goals", str(division["_id"])
        )
    assert repo.many.call_args.args[:2] == (
        "matches",
        {"season_id": season["_id"], "division_id": division["_id"], "status": "completed"},
    )
