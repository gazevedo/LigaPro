from types import SimpleNamespace
from unittest.mock import Mock

from bson import ObjectId

from test_match_engine import team
from app.models.game import utcnow
from app.services.match_engine import MatchEngine
from app.services.player_statistics import PlayerStatisticsService, match_player_summaries


def test_assists_follow_a_real_final_pass_without_changing_simulation_results():
    assisted = 0
    for seed in range(50):
        result = MatchEngine().simulate(team("home"), team("away"), seed)
        for i, event in enumerate(result["events"]):
            if event.get("assist_player_id"):
                assisted += 1
                passes = [
                    e
                    for e in result["events"][:i]
                    if e["type"] == "pass_completed" and e["minute"] == event["minute"]
                ]
                assert any(
                    e["player_id"] == event["assist_player_id"]
                    and e["receiver_id"] == event["player_id"]
                    for e in passes
                )
                assert event["type"] == "goal" and not event.get("penalty")
        assert sum(row["assists"] for row in match_player_summaries(result)) == sum(
            bool(e.get("assist_player_id")) for e in result["events"]
        )
    assert assisted > 0


def test_sector_analysis_handles_empty_games_and_computes_actual_rates():
    rows = PlayerStatisticsService.analysis(
        {
            "h": {
                "shots": 5,
                "shots_on_target": 2,
                "phases": {"build": {"attempts": 10, "successes": 4}},
            }
        },
        "h",
        "a",
    )
    assert rows[0]["accuracy"] == 40 and rows[0]["sectors"][0]["rate"] == 40
    assert rows[1]["accuracy"] is None and rows[1]["sectors"][0]["rate"] is None


def test_recent_means_and_trends_use_only_club_appearances_and_real_history():
    repo = Mock()
    club_id, player_id = ObjectId(), ObjectId()
    repo.owned.return_value = {"_id": club_id}
    player = {"_id": player_id, "name": "Pedro", "position": "MID", "strength": 50, "age": 22}
    ratings = [
        {
            "player_id": player_id,
            "match_id": ObjectId(),
            "match_date": utcnow(),
            "rating": value,
            "minutes": 90,
        }
        for value in [8] * 5 + [6] * 5
    ]
    repo.many.side_effect = [[player], ratings, []]
    data = PlayerStatisticsService(repo).performance(SimpleNamespace(id=ObjectId()))
    assert data["players"][0]["average_rating"] == 8
    assert data["players"][0]["rating_change"] == 2
    assert data["players"][0]["development"] == []
    assert repo.many.call_args_list[1].args[1]["club_id"] == club_id


def test_evolution_reuses_existing_season_history_without_fabricating_points():
    repo = Mock()
    identity = ObjectId()
    repo.owned.return_value = {"_id": ObjectId()}
    repo.many.side_effect = [
        [{"_id": identity, "position": "MID", "age": 23, "strength": 51}],
        [],
        [
            {
                "player_id": identity,
                "old_strength": 50,
                "new_strength": 51,
                "reason": "development",
                "created_at": utcnow(),
            }
        ],
    ]
    result = PlayerStatisticsService(repo).performance(SimpleNamespace(id=ObjectId()))
    assert result["players"][0]["development"][0]["strength"] == 51
    assert result["players"][0]["development"][0]["previous_strength"] == 50
