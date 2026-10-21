from unittest.mock import MagicMock, patch

from bson import ObjectId

from app.services.market_value import MarketValueService


def test_round_market_values_and_history_are_written_in_batches():
    repo = MagicMock()
    repo.many.return_value = []
    repo.database.player_match_ratings.aggregate.return_value = []
    players = [
        {"_id": ObjectId(), "owner_club_id": ObjectId(), "market_value": 10000} for _ in range(50)
    ]
    reference = ObjectId()
    service = MarketValueService()
    with (
        patch.object(service, "calculate", return_value=20000),
        patch("app.services.game_history.HistoryService.record"),
    ):
        service.recalculate(repo, players, "round", reference)
    operations = repo.database.__getitem__.return_value.bulk_write.call_args.args[0]
    assert len(operations) == 50
    histories = repo.insert_many.call_args.args[1]
    assert len(histories) == 50
    assert {row["player_id"] for row in histories} == {row["_id"] for row in players}
    assert all(row["reason"] == "round" and row["reference_id"] == reference for row in histories)
    repo.update.assert_not_called()
    repo.insert.assert_not_called()
