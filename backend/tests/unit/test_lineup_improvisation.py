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
from app.services.tactics import TacticsService


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


def test_manual_positions_survive_saving_and_match_assignment_with_penalties():
    repo, documents, data = setup_squad()
    data.manual_positions = True
    data.starters[1], data.starters[9] = data.starters[9], data.starters[1]
    with (
        patch("app.services.game.ChemistryService.lineup_change"),
        patch("app.services.game.TacticsService.persist"),
    ):
        saved = SquadService(repo).save(SimpleNamespace(id="user"), data)
    assert saved["manual_positions"] is True
    by_id = {str(player["_id"]): player for player in documents}
    assigned = arrange_formation(
        [MatchPlayer.from_document(by_id[identity]) for identity in saved["starters"]],
        "4-4-2",
        preserve_order=True,
    )
    assert [player.id for player in assigned] == saved["starters"]
    assert assigned[1].position == "ATT"
    assert assigned[1].assigned_position == "FB"
    assert assigned[9].position == "CB"
    assert assigned[9].assigned_position == "ATT"
    calculator = PlayerEffectiveStrengthCalculator(MatchConfig(), "classic")
    assert calculator.fit.calculate(assigned[1]) == 0.72
    assert calculator.fit.calculate(assigned[9]) == 0.72


@pytest.mark.parametrize("formation,manual", [("4-4-2", True), ("4-3-3", False)])
def test_style_changes_keep_manual_positions_and_new_formations_reassign_them(formation, manual):
    repo, documents, _ = setup_squad()
    lineup = repo.find.return_value
    lineup["manual_positions"] = True
    lineup["starters"][1], lineup["starters"][9] = (
        lineup["starters"][9],
        lineup["starters"][1],
    )
    data = SimpleNamespace(formation=formation, model_dump=lambda: {"formation": formation})
    with patch("app.services.tactics.ChemistryService.lineup_change"):
        TacticsService(repo).save(SimpleNamespace(id="user"), data)
    saved = next(
        call.args[2]["$set"] for call in repo.update.call_args_list if call.args[0] == "lineups"
    )
    assert saved["manual_positions"] is manual
    if manual:
        assert saved["starters"] == lineup["starters"]
    else:
        assert set(saved["starters"]) == {player["_id"] for player in documents}
