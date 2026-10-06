from copy import deepcopy
from unittest.mock import patch

from test_match_engine import team

from app.services.live_match import LiveMatchSession
from app.services.match_engine import MatchEngine, MatchPlayer
from app.services.match_fallback import AutoMatchFallbackService


def test_progression_never_precomputes_result_and_pause_never_consumes_rng():
    h, a = team("h"), team("a")
    with patch("app.services.match_engine.Random", wraps=__import__("random").Random) as rng:
        session = LiveMatchSession(h, a, 36)
        assert session.frame["minute"] == 0 and session.result is None
        assert len(session.frame["events"]) == 1 and session.frame["events"][0]["type"] == "kickoff"
        assert rng.call_count == 2
        before = deepcopy(session.frame)
        session.paused = True
        assert session.advance() == before
        session.paused = False
        assert session.advance()["minute"] == 5
        while session.frame["minute"] < 45:
            session.advance()
        assert session.status == "halftime"
        assert any(e["type"] == "halftime" for e in session.frame["events"])
        session.advance()
        assert session.status == "second_half"
        session.simulate_to_end()
        assert session.status == "finished" and session.frame["minute"] == 90
        assert session.frame["events"][-1]["type"] == "fulltime"


def test_speed_presence_skip_and_offline_are_exactly_identical():
    h, a = team("h", is_bot=True), team("a")
    h.reserves = [MatchPlayer("h-bench", "ATT", "ATT")]
    expected = MatchEngine().simulate(h, a, 123)
    for speed in [1, 2, 4]:
        for connected in [0, 1, 2]:
            session = LiveMatchSession(h, a, 123)
            session.speed = speed
            if connected:
                while session.result is None:
                    session.advance()
            else:
                session.simulate_to_end()
            assert session.result == expected
            assert session.frame["statistics"] == expected["statistics"]


def test_command_at_sixty_affects_only_future_and_replays_exactly():
    h, a = team("h"), team("a")
    command = {
        "team_id": "h",
        "minute": 60,
        "type": "tactics_change",
        "payload": {"play_style": "all_out_attack", "marking": "heavy"},
    }
    original = LiveMatchSession(h, a, 737)
    changed = LiveMatchSession(h, a, 737)
    while original.frame["minute"] < 60:
        assert original.advance() == changed.advance()
    prefix = deepcopy(changed.frame["events"])
    changed.queue.append(command)
    result = changed.simulate_to_end()
    assert result["events"][: len(prefix)] == prefix
    assert any(e["type"] == "play_style_change" and e["minute"] == 60 for e in result["events"])
    assert result == MatchEngine().simulate(h, a, 737, commands=[command])


def test_forced_fallback_does_not_change_absent_team_strategy():
    h = team("h")
    dismissed = {h.lineup[0].id}
    restored = AutoMatchFallbackService.restore_keeper(h, dismissed)
    assert restored and restored.id not in dismissed and restored.assigned_position == "GK"
    assert h.style == "balanced" and h.marking == "light" and h.formation == "4-4-2"


def test_progressive_knockout_matches_normal_extra_time_and_shootout():
    h, a = team("h"), team("a")
    extra = penalties = False
    for seed in range(40):
        expected = MatchEngine().simulate_knockout(h, a, seed)
        session = LiveMatchSession(h, a, seed, knockout=True)
        session.simulate_to_end()
        assert session.result == expected
        extra |= bool(expected.get("extra_time"))
        penalties |= bool(expected.get("shootout_score"))
    assert extra and penalties
