from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.services.settings import SettingsService


def setup():
    database = MagicMock()
    database.__getitem__.side_effect = lambda name: getattr(database, name)
    database.list_collection_names.return_value = ["users", "user_sessions", "clubs", "game_state"]
    database.game_state.find_one.return_value = {"status": "ready"}
    repository = MagicMock()
    repository.collection.database = database
    user = SimpleNamespace(id=str(ObjectId()), email="admin@example.com")
    return SettingsService(repository), database, user


def test_reset_retains_requester_until_seed_succeeds_and_then_revokes_every_session():
    service, database, user = setup()
    tx = SimpleNamespace(session=None)
    with (
        patch("app.repositories.game.GameRepository") as repo,
        patch("app.services.competition.CompetitionService.lock"),
        patch("mock_database.import_database") as seed,
    ):
        repo.return_value.transaction.side_effect = lambda operation: operation(tx)
        assert service.reset_database(user) == {"status": "ready"}
    seed.assert_called_once_with(database)
    assert database.users.delete_many.call_args_list[0].args[0] == {
        "_id": {"$ne": ObjectId(user.id)}
    }
    assert database.users.delete_many.call_args_list[-1].args[0] == {}
    assert database.user_sessions.delete_many.call_args_list[-1].args[0] == {}
    assert database.clubs.delete_many.call_args.args[0] == {}


def test_failed_seed_keeps_requester_and_sessions_available_for_retry():
    service, database, user = setup()
    with (
        patch("app.repositories.game.GameRepository") as repo,
        patch("app.services.competition.CompetitionService.lock"),
        patch("mock_database.import_database", side_effect=RuntimeError("seed failed")),
    ):
        repo.return_value.transaction.side_effect = lambda operation: operation(
            SimpleNamespace(session=None)
        )
        with pytest.raises(RuntimeError, match="seed failed"):
            service.reset_database(user)
    assert database.users.delete_many.call_count == 1
    assert database.users.delete_many.call_args.args[0] == {"_id": {"$ne": ObjectId(user.id)}}
    assert database.game_state.update_one.call_args.args[1]["$set"]["status"] == "failed"


def test_concurrent_reset_is_rejected_before_clearing_any_collection():
    service, database, user = setup()
    database.game_state.find_one_and_update.side_effect = DuplicateKeyError("reset in progress")
    with pytest.raises(HTTPException) as error:
        service.reset_database(user)
    assert error.value.status_code == 409
    database.list_collection_names.assert_not_called()
