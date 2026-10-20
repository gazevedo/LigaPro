from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from pymongo.errors import NetworkTimeout, OperationFailure

from app.repositories.game import GameRepository
from app.schemas.game import ClubInput
from app.services.game import ClubService


def test_creation_database_timeout_returns_retryable_error():
    repo = Mock()
    repo.transaction.side_effect = NetworkTimeout("deadline exceeded")
    with patch("app.services.game.CompetitionService.ensure_lock"):
        with pytest.raises(HTTPException) as error:
            ClubService(repo).create(
                Mock(), ClubInput(name="123", country_id="BR", badge_id="blue", stadium_name="123")
            )
    assert error.value.status_code == 503
    assert "Tente novamente" in error.value.detail


def test_creation_does_not_hide_other_database_errors():
    repo = Mock()
    repo.transaction.side_effect = OperationFailure("database failed")
    with patch("app.services.game.CompetitionService.ensure_lock"):
        with pytest.raises(OperationFailure):
            ClubService(repo).create(
                Mock(), ClubInput(name="123", country_id="BR", badge_id="blue")
            )


@pytest.mark.parametrize("transactional", [False, True])
def test_rules_are_cached_only_inside_a_transaction(transactional):
    repo = GameRepository(Mock(), session=Mock() if transactional else None)
    repo.find = Mock(return_value={"value": {"initial_capacity": 12345}})
    first = repo.rules()
    first["initial_capacity"] = 1
    assert repo.rules()["initial_capacity"] == 12345
    assert repo.find.call_count == (1 if transactional else 2)


def test_ranking_refresh_does_not_rewrite_unchanged_clubs():
    from app.services.club_prestige import ClubRankingService

    identity = "club"
    repo = Mock()
    row = {"club_id": identity, "position": 1, "points": 3}
    points = ClubRankingService.points({}, row, 0)
    repo.many.side_effect = [
        [row],
        [{"_id": identity, "ranking_points": points, "ranking_position": 1, "ranking": points}],
    ]
    ClubRankingService.refresh(repo, "season")
    repo.database.clubs.bulk_write.assert_not_called()
    repo.update.assert_not_called()


def test_existing_record_is_not_written_when_new_value_does_not_beat_it():
    from app.services.game_history import HistoryService

    repo = Mock()
    repo.find.return_value = {"value": 100}
    HistoryService.record(repo, "highest_market_value", 90, "player")
    repo.database.game_records.find_one_and_update.assert_not_called()


@pytest.mark.parametrize("owner_conflict", [True, False])
def test_only_duplicate_owner_is_reported_as_already_having_a_club(owner_conflict):
    from pymongo.errors import DuplicateKeyError

    repo = Mock()
    error = DuplicateKeyError(
        "duplicate key",
        details={
            "keyPattern": {"owner_user_id" if owner_conflict else "_id": 1},
        },
    )
    repo.transaction.side_effect = error
    with pytest.raises(HTTPException if owner_conflict else DuplicateKeyError) as caught:
        ClubService(repo).create(Mock(), ClubInput(name="Clube", country_id="BR", badge_id="blue"))
    if owner_conflict:
        assert caught.value.status_code == 409
    else:
        assert caught.value is error


@pytest.fixture
def takeover_repo():
    from copy import deepcopy

    from bson import ObjectId

    from app.config.game import GameConfig

    club_id, season_id, division_id, slot_id = (ObjectId() for _ in range(4))
    club = {
        "_id": club_id,
        "name": "Bot original",
        "is_bot": True,
        "created_at": "original",
        "supporters": 2345,
        "ranking": 77,
        "trophies": ["taça"],
        "reputation": 20,
    }
    season = {"_id": season_id, "status": "active", "config": GameConfig().snapshot()}
    slot = {"_id": slot_id, "club_id": club_id, "points": 18, "position": 7}
    repo = Mock()
    repo.transaction.side_effect = lambda callback: callback(repo)

    def find(collection, query, *args):
        if collection == "seasons":
            return season
        if collection == "countries":
            return {"_id": "BR", "name": "Brasil"}
        if collection == "club_badges":
            return {"_id": "blue", "name": "Azul"}
        return None

    def many(collection, query, **kwargs):
        if collection == "divisions":
            return [{"_id": division_id, "tier": 2}]
        if collection == "standings":
            assert query["division_id"] == division_id
            assert query["bot_takeover"] == {"$ne": True}
            return [slot]
        return []

    def update(collection, query, changes):
        if collection == "seasons":
            season.update(changes.get("$set", {}))
            for key in changes.get("$unset", {}):
                season.pop(key, None)
            return season
        if collection == "clubs":
            assert query["is_bot"] is True and query["owner_user_id"] is None
            club.update(changes["$set"])
            return deepcopy(club)
        return None

    repo.find.side_effect, repo.many.side_effect, repo.update.side_effect = find, many, update
    return repo, club, season, slot


@pytest.mark.parametrize("stadium_name", [None, "Minha arena"])
def test_takeover_preserves_bot_identity_and_assets_without_generation(takeover_repo, stadium_name):
    from bson import ObjectId

    repo, bot, season, slot = takeover_repo
    original_id = bot["_id"]
    user = Mock(id=str(ObjectId()))
    with patch("app.services.player_development.PlayerGeneratorService.squad") as generate:
        result = ClubService(repo).create(
            user,
            ClubInput(
                name="Meu clube", country_id="BR", badge_id="blue", stadium_name=stadium_name
            ),
        )
    assert result["id"] == str(original_id)
    assert result["name"] == "Meu clube"
    assert result["created_at"] == "original"
    assert result["supporters"] == 2345 and result["ranking"] == 77
    assert result["trophies"] == ["taça"] and result["reputation"] == 20
    assert bot["owner_user_id"] == ObjectId(user.id) and bot["is_bot"] is False
    assert season["open_division_pending"] is True
    generate.assert_not_called()
    repo.insert.assert_not_called()
    repo.insert_many.assert_not_called()
    repo.update_many.assert_not_called()
    writes = [call.args[0] for call in repo.update.call_args_list]
    assert set(writes) == {"seasons", "clubs", "season_clubs", "standings"} | (
        {"stadiums"} if stadium_name else set()
    )
    repo.update.assert_any_call(
        "standings", {"_id": slot["_id"]}, {"$set": {"is_bot": False, "club_name": "Meu clube"}}
    )


def test_no_slot_commits_background_preparation_without_generating_club(takeover_repo):
    from bson import ObjectId

    repo, _, season, _ = takeover_repo
    repo.many.return_value = []
    repo.many.side_effect = None
    with pytest.raises(HTTPException) as error:
        ClubService(repo).create(
            Mock(id=str(ObjectId())), ClubInput(name="Meu clube", country_id="BR", badge_id="blue")
        )
    assert error.value.status_code == 503
    assert season["open_division_pending"] is True
    assert all(call.args[0] == "seasons" for call in repo.update.call_args_list)
    repo.insert_many.assert_not_called()


def test_background_preparation_clears_pending_only_after_success(takeover_repo):
    repo, _, season, _ = takeover_repo
    season["open_division_pending"] = True
    repo.many.side_effect = None
    repo.many.return_value = [season]
    with patch(
        "app.services.game.CompetitionService.ensure_open_division",
        side_effect=RuntimeError("retry"),
    ):
        with pytest.raises(RuntimeError):
            ClubService(repo).complete_pending_creations()
    assert season["open_division_pending"] is True
    with (
        patch("app.services.game.CompetitionService.ensure_open_division") as prepare,
        patch("app.services.game.ClubRankingService.refresh") as ranking,
    ):
        ClubService(repo).complete_pending_creations()
    ranking.assert_called_once_with(repo, season["_id"])
    prepare.assert_called_once_with(repo, season)
    assert "open_division_pending" not in season


def test_background_preparation_does_nothing_without_pending_jobs():
    repo = Mock()
    repo.many.return_value = []
    repo.find.return_value = None
    ClubService(repo).complete_pending_creations()
    repo.transaction.assert_not_called()


def test_takeover_rejects_a_club_that_is_no_longer_available(takeover_repo):
    from bson import ObjectId

    repo, _, _, _ = takeover_repo
    original_update = repo.update.side_effect
    repo.update.side_effect = lambda collection, query, changes: (
        None if collection == "clubs" else original_update(collection, query, changes)
    )
    with pytest.raises(HTTPException) as error:
        ClubService(repo).create(
            Mock(id=str(ObjectId())), ClubInput(name="Meu clube", country_id="BR", badge_id="blue")
        )
    assert error.value.status_code == 409
    assert not any(call.args[0] == "standings" for call in repo.update.call_args_list)


def test_takeover_rejects_existing_owner_before_claiming_a_bot(takeover_repo):
    from bson import ObjectId

    repo, bot, _, _ = takeover_repo
    repo.find.side_effect = lambda collection, query: bot if collection == "clubs" else None
    with pytest.raises(HTTPException) as error:
        ClubService(repo).create(
            Mock(id=str(ObjectId())), ClubInput(name="Meu clube", country_id="BR", badge_id="blue")
        )
    assert error.value.status_code == 409
    repo.update.assert_not_called()


def test_background_repairs_initial_zero_ranking_without_a_creation_job(takeover_repo):
    repo, _, season, _ = takeover_repo
    repo.many.side_effect = None
    repo.many.return_value = []
    repo.find.side_effect = None
    repo.find.return_value = season
    with (
        patch("app.services.game.ClubRankingService.refresh") as ranking,
        patch("app.services.game.CompetitionService.ensure_open_division") as prepare,
    ):
        ClubService(repo).complete_pending_creations()
    ranking.assert_called_once_with(repo, season["_id"])
    prepare.assert_not_called()
