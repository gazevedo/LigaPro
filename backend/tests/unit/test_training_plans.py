from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from bson import ObjectId
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.game import utcnow
from app.schemas.game import TrainingPlanInput
from app.services.player_development import TrainingService
from app.services.physical_condition import PhysicalConditionService


def scenario(intensity="normal"):
    now = utcnow()
    club = {"_id": ObjectId()}
    player = {
        "_id": ObjectId(),
        "current_club_id": club["_id"],
        "position": "MID",
        "age": 22,
        "status": "available",
        "strength": 50,
        "energy": 100,
        "physical_condition": 100,
        "individual_skills": {
            key: 50
            for key in (
                "goalkeeping",
                "speed",
                "technique",
                "passing",
                "tackling",
                "playmaking",
                "finishing",
            )
        },
    }
    plan = {
        "_id": club["_id"],
        "enabled": True,
        "next_session_at": now - timedelta(hours=12),
        "ends_at": now,
        "intensity": intensity,
        "skill": "passing",
        "individual": {},
        "sessions_completed": 0,
    }
    repo = Mock(session=None)
    repo.find.side_effect = lambda collection, query: (
        (deepcopy(plan) if plan["enabled"] else None)
        if collection == "training_plans"
        else deepcopy(club)
        if collection == "clubs"
        else deepcopy(player)
        if collection == "players"
        else None
    )
    repo.many.return_value = [deepcopy(player)]

    def update(collection, query, changes):
        target = plan if collection == "training_plans" else player
        target.update(changes.get("$set", {}))
        for key, value in changes.get("$inc", {}).items():
            target[key] = target.get(key, 0) + value
        return deepcopy(target)

    repo.update.side_effect = update
    return repo, plan, player, now


def test_offline_sessions_catch_up_once_and_end_the_plan():
    repo, plan, player, now = scenario()
    with (
        patch.object(PhysicalConditionService, "prepare"),
        patch.object(TrainingService, "train_for_club") as train,
    ):
        TrainingService.apply_plan(repo, plan["_id"], now)
        assert train.call_count == 3
        assert train.call_args.kwargs["multiplier"] == 2
        assert plan["sessions_completed"] == 3 and not plan["enabled"]
        assert player["energy"] == 94
        TrainingService.apply_plan(repo, plan["_id"], now)
        assert train.call_count == 3


@pytest.mark.parametrize("mode", ["rest", "individual_rest", "low_condition", "joined_late"])
def test_rest_and_unfit_or_not_yet_signed_players_do_not_train(mode):
    repo, plan, player, now = scenario()
    if mode == "rest":
        plan["intensity"] = "rest"
    if mode == "individual_rest":
        plan["individual"][str(player["_id"])] = "rest"
    if mode == "low_condition":
        player["physical_condition"] = 60
    if mode == "joined_late":
        player["joined_at"] = now + timedelta(hours=1)
    repo.many.side_effect = lambda *args, **kwargs: [deepcopy(player)]
    with (
        patch.object(PhysicalConditionService, "prepare"),
        patch.object(TrainingService, "train_for_club") as train,
    ):
        TrainingService.apply_plan(repo, plan["_id"], now)
    train.assert_not_called()
    assert player["energy"] == 100


def test_individual_skill_overrides_collective_and_batches_resume():
    repo, plan, player, now = scenario("intense")
    plan["individual"] = {str(player["_id"]): "finishing"}
    with (
        patch.object(PhysicalConditionService, "prepare"),
        patch.object(TrainingService, "train_for_club") as train,
    ):
        TrainingService.apply_plan(repo, plan["_id"], now, batch=1)
        assert plan["enabled"] and plan["sessions_completed"] == 1
        assert train.call_args.args[-1] == "finishing"
        assert train.call_args.kwargs["multiplier"] == 3
        TrainingService.apply_plan(repo, plan["_id"], now)
        assert train.call_count == 3


def test_gain_records_real_evolution_and_uses_existing_training_formula():
    repo, _, player, now = scenario()

    def find(collection, query):
        if collection == "players":
            return deepcopy(player)
        if collection == "player_training":
            return {"progress": 99}
        return None

    repo.find.side_effect = find
    with patch("app.services.player_development.MarketValueService"):
        result = TrainingService.train_for_club(
            repo, {"_id": player["current_club_id"]}, str(player["_id"]), "passing", at=now
        )
    assert result["individual_skills"]["passing"] == 51
    history = repo.insert.call_args.args[1]
    assert history["previous_skill"] == 50 and history["individual_skills"]["passing"] == 51
    assert history["created_at"] == now


def test_plan_rejects_foreign_player_and_invalid_settings():
    repo, plan, _, _ = scenario()
    repo.owned.return_value = {"_id": plan["_id"]}
    repo.transaction.side_effect = lambda operation: operation(repo)
    with pytest.raises(HTTPException) as error:
        TrainingService(repo).save_plan(
            SimpleNamespace(id=ObjectId()), TrainingPlanInput(individual={str(ObjectId()): "rest"})
        )
    assert error.value.status_code == 422
    for value in ({"days": 0}, {"days": 31}, {"intensity": "invalid"}, {"skill": "invalid"}):
        with pytest.raises(ValidationError):
            TrainingPlanInput(**value)
