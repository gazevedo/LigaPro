from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.schemas.game import LineupInput
from app.services.game import SquadService
from app.services.match_engine import (
    MatchConfig,
    MatchPlayer,
    PlayerEffectiveStrengthCalculator,
    arrange_formation,
)


def setup_squad():
    club_id = ObjectId()
    players = [
        {"_id": ObjectId(), "position": position, "status": "available"}
        for position in ["GK", *["CB"] * 5, *["MID"] * 3, *["ATT"] * 2]
    ]
    repo = MagicMock()
    repo.transaction.side_effect = lambda operation: operation(repo)
    repo.owned.return_value = {"_id": club_id}
    repo.rules.return_value = {"formations": {"4-4-2": {"DEF": 4, "MED": 4, "ATA": 2}}}
    repo.many.return_value = players
    repo.find.return_value = {
        "formation": "4-4-2",
        "starters": [player["_id"] for player in players],
        "play_style": "balanced",
        "marking": "light",
        "attack_focus": "normal",
    }
    repo.update.side_effect = lambda collection, query, changes: {
        "_id": club_id,
        **changes.get("$set", {}),
    }
    data = LineupInput(
        formation="4-4-2", starters=[str(player["_id"]) for player in players], reserves=[]
    )
    return repo, players, data


def test_improvised_lineup_saves_and_has_a_real_strength_penalty():
    repo, documents, data = setup_squad()
    with (
        patch("app.services.game.ChemistryService.lineup_change"),
        patch("app.services.game.TacticsService.persist"),
    ):
        result = SquadService(repo).save(SimpleNamespace(id="user"), data)
    assert result["starters"] == data.starters
    assigned = arrange_formation([MatchPlayer.from_document(p) for p in documents], "4-4-2")
    improvised = next(
        player
        for player in assigned
        if player.position == "CB" and player.assigned_position == "MID"
    )
    calculator = PlayerEffectiveStrengthCalculator(MatchConfig(), "classic")
    penalized = calculator.calculate(improvised, "passing")
    improvised.assigned_position = "CB"
    assert penalized == pytest.approx(calculator.calculate(improvised, "passing") * 0.72)


def test_missing_keeper_or_incomplete_lineup_is_still_rejected():
    for invalid in ("keeper", "count"):
        repo, players, data = setup_squad()
        if invalid == "keeper":
            players[0]["position"] = "CB"
        else:
            players.pop()
            data.starters.pop()
        with pytest.raises(HTTPException) as error:
            SquadService(repo).save(SimpleNamespace(id="user"), data)
        assert error.value.status_code == 422
