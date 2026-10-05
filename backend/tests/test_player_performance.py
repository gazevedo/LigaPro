from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

from bson import ObjectId
from test_game import account, create

from app.config.game import legacy_position
from app.main import app
from app.repositories.game import GameRepository
from app.services.chemistry import ChemistryService
from app.services.competition import CompetitionService
from app.services.match_engine import MatchEngine
from app.services.player_development import bootstrap_player_attributes
from app.services.player_morale import PlayerMoraleService
from app.services.player_statistics import PlayerStatisticsService, match_player_summaries


def setup(client):
    headers = account(client, 1)
    club = create(client, headers)
    db = app.state.database
    match = db.matches.find_one({"home_club_id": ObjectId(club["id"])}, sort=[("date", 1)])
    repo = GameRepository(db)
    home = CompetitionService.match_team(repo, match["home_club_id"])
    away = CompetitionService.match_team(repo, match["away_club_id"])
    return headers, club, match, home, away


def test_potential_is_hidden_everywhere_and_training_respects_ceiling(client):
    headers, club, match, home, away = setup(client)
    db = app.state.database
    player_id = ObjectId(home.lineup[1].id)
    db.player_training.insert_one({"_id": player_id, "progress": 99})
    db.players.update_one({"_id": player_id}, {"$set": {"individual_skills.passing": 99}})
    trained = client.post(
        f"/api/players/{player_id}/train", headers=headers, json={"skill": "passing"}
    )
    assert trained.status_code == 200, trained.text
    assert trained.json()["individual_skills"]["passing"] == 100
    assert "potential" not in trained.json()
    assert (
        client.post(
            f"/api/players/{player_id}/train", headers=headers, json={"skill": "passing"}
        ).status_code
        == 409
    )
    for path in ("/api/training", "/api/youth", "/api/market/players"):
        rows = client.get(path, headers=headers).json()
        assert rows and all("potential" not in player for player in rows)
    assert all(
        "potential" not in p for p in client.get("/api/squad", headers=headers).json()["players"]
    )
    assert "potential" not in client.get(f"/api/players/{player_id}", headers=headers).json()
    youth = db.youth_players.find_one({"current_club_id": ObjectId(club["id"])})
    db.youth_players.update_one({"_id": youth["_id"]}, {"$set": {"age": 18, "morale": 50}})
    promoted = client.post(f"/api/youth/{youth['_id']}/promote", headers=headers)
    assert promoted.status_code == 200
    assert "potential" not in promoted.json()
    assert promoted.json()["morale"] == 55
    assert "integration" not in promoted.json()


def test_win_loss_streak_goals_absence_and_bounds(client):
    headers, club, match, home, away = setup(client)
    result = MatchEngine().simulate(home, away, 43)
    result["score"] = {home.id: 1, away.id: 0}
    result["events"] = [
        {"minute": 15, "type": "goal", "team_id": home.id, "player_id": home.lineup[9].id}
    ]
    summaries = match_player_summaries(result)
    repo, db = GameRepository(app.state.database), app.state.database
    service = PlayerMoraleService()

    def process():
        repo.transaction(lambda active: service.after_match(active, match, result, summaries))

    process()
    winner = db.players.find_one({"_id": ObjectId(home.lineup[1].id)})
    loser = db.players.find_one({"_id": ObjectId(away.lineup[1].id)})
    scorer = db.players.find_one({"_id": ObjectId(home.lineup[9].id)})
    assert winner["morale"] == 54
    assert loser["morale"] == 48
    assert scorer["morale"] == 56
    bench_id = ObjectId(home.reserves[0].id)
    before = db.players.find_one({"_id": bench_id})["morale"]
    process()
    second = db.players.find_one({"_id": winner["_id"]})["morale"]
    assert second - winner["morale"] > winner["morale"] - 50
    process()
    assert db.players.find_one({"_id": bench_id})["matches_without_playing"] == 3
    assert db.players.find_one({"_id": bench_id})["morale"] <= before
    db.players.update_one({"_id": winner["_id"]}, {"$set": {"morale": 99}})
    db.players.update_one({"_id": loser["_id"]}, {"$set": {"morale": 0}})
    process()
    assert db.players.find_one({"_id": winner["_id"]})["morale"] == 100
    assert db.players.find_one({"_id": loser["_id"]})["morale"] == 0


def test_chemistry_repeated_lineup_changes_recruitment_and_limits(client):
    headers, club, match, home, away = setup(client)
    repo, service = GameRepository(app.state.database), ChemistryService()
    result = MatchEngine().simulate(home, away, 6)
    summaries = match_player_summaries(result)
    repo.transaction(lambda active: service.after_match(active, match, result, summaries))
    first = service.get(repo, ObjectId(club["id"]))
    following = {**match, "_id": ObjectId()}
    repo.transaction(lambda active: service.after_match(active, following, result, summaries))
    repeated = service.get(repo, ObjectId(club["id"]))
    assert repeated["value"] > first["value"]
    assert repeated["last_lineup_hash"] == first["last_lineup_hash"]
    original = client.get("/api/squad", headers=headers).json()
    starters = original["lineup"]["starters"][:]
    by_id = {p["id"]: p for p in original["players"]}
    reserves = original["lineup"]["reserves"][:]
    for i in range(6):
        replacement = next(
            identity
            for identity in reserves
            if legacy_position(by_id[identity]["position"])
            == legacy_position(by_id[starters[i]]["position"])
        )
        reserves.remove(replacement)
        reserves.append(starters[i])
        starters[i] = replacement
    updated = client.put(
        "/api/squad/lineup",
        headers=headers,
        json={"formation": "4-4-2", "starters": starters, "reserves": reserves},
    )
    assert updated.status_code == 200, updated.text
    changed = service.get(repo, ObjectId(club["id"]))
    assert changed["value"] < repeated["value"]
    same = client.put(
        "/api/squad/lineup",
        headers=headers,
        json={"formation": "4-4-2", "starters": starters, "reserves": reserves},
    )
    assert same.status_code == 200
    assert service.get(repo, ObjectId(club["id"]))["value"] == changed["value"]
    repo.transaction(lambda active: service.save(active, ObjectId(club["id"]), {"value": 200}))
    assert service.get(repo, ObjectId(club["id"]))["value"] == 100
    repo.transaction(lambda active: service.save(active, ObjectId(club["id"]), {"value": -200}))
    assert service.get(repo, ObjectId(club["id"]))["value"] == 0


def test_statistics_ratings_and_morale_are_saved_once_with_result(client):
    headers, club, match, home, away = setup(client)
    db, repo = app.state.database, GameRepository(app.state.database)
    command = {
        "team_id": home.id,
        "minute": 60,
        "type": "substitution",
        "payload": {"out_player_id": home.lineup[10].id, "in_player_id": home.reserves[0].id},
    }
    db.matches.update_one({"_id": match["_id"]}, {"$set": {"commands": [command]}})
    service = CompetitionService(repo)
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda _: service.play(match["_id"], match["date"]), range(2)))
    saved = db.matches.find_one({"_id": match["_id"]})
    summaries = match_player_summaries(saved["result"])
    assert db.player_match_ratings.count_documents({"match_id": match["_id"]}) == len(summaries)
    for row in summaries:
        stats = db.player_season_stats.find_one(
            {
                "player_id": ObjectId(row["player_id"]),
                "club_id": ObjectId(row["club_id"]),
                "season_id": match["season_id"],
            }
        )
        assert stats["matches"] == 1
        assert stats["minutes"] == row["minutes"]
        assert stats["goals"] == row["goals"]
        assert stats["yellow_cards"] == row["yellow_cards"]
        assert stats["red_cards"] == row["red_cards"]
        assert stats["penalties_scored"] == row["penalties_scored"]
    before = list(db.player_season_stats.find({}).sort("_id", 1))
    morale = list(
        db.players.find({"current_club_id": ObjectId(club["id"])}, {"morale": 1, "integration": 1})
    )
    service.play(match["_id"], match["date"])
    assert list(db.player_season_stats.find({}).sort("_id", 1)) == before
    assert (
        list(
            db.players.find(
                {"current_club_id": ObjectId(club["id"])}, {"morale": 1, "integration": 1}
            )
        )
        == morale
    )
    report = client.get(f"/api/competition/matches/{match['_id']}", headers=headers)
    assert report.status_code == 200, report.text
    assert len(report.json()["ratings"]) == len(summaries)
    assert all(5 <= rating["rating"] <= 10 for rating in report.json()["ratings"])
    assert all("potential" not in rating for rating in report.json()["ratings"])
    for ranking in ("goals", "matches", "cards"):
        response = client.get(f"/api/statistics?ranking={ranking}", headers=headers)
        assert response.status_code == 200, response.text
        rows = response.json()["rows"]
        assert rows and [r["total"] for r in rows] == sorted(
            (r["total"] for r in rows), reverse=True
        )
        assert response.json()["recent_matches"][0]["id"] == str(match["_id"])
    identity = summaries[0]["player_id"]
    stats = client.get(f"/api/players/{identity}/statistics", headers=headers).json()
    assert stats["career"]["matches"] == 1
    assert len(stats["seasons"]) == 1


def test_season_club_separation_career_totals_and_report_permissions(client):
    headers, club, match, home, away = setup(client)
    repo, db = GameRepository(app.state.database), app.state.database
    result = MatchEngine().simulate(home, away, 7)
    summaries = match_player_summaries(result)
    second_season = ObjectId()
    second = {**match, "season_id": second_season, "_id": ObjectId()}
    moved = deepcopy(summaries)
    moved[0]["club_id"] = away.id
    repo.transaction(lambda active: PlayerStatisticsService.after_match(active, match, summaries))
    repo.transaction(lambda active: PlayerStatisticsService.after_match(active, second, summaries))
    repo.transaction(lambda active: PlayerStatisticsService.after_match(active, match, moved))
    assert (
        db.player_season_stats.count_documents({"player_id": ObjectId(summaries[0]["player_id"])})
        == 3
    )
    assert (
        db.player_career_stats.find_one({"_id": ObjectId(summaries[0]["player_id"])})["matches"]
        == 3
    )
    response = client.get(
        f"/api/statistics?season_id={match['season_id']}&ranking=matches", headers=headers
    )
    assert response.status_code == 200
    own = next(r for r in response.json()["rows"] if r["player_id"] == summaries[0]["player_id"])
    assert own["matches"] == 2 and len(own["club_ids"]) == 2
    assert (
        client.get(f"/api/competition/matches/{match['_id']}", headers=headers).status_code == 409
    )
    stranger = account(client, 2)
    stranger_club = create(client, stranger, "Outro clube")
    foreign_fixture = db.matches.find_one(
        {
            "home_club_id": ObjectId(club["id"]),
            "away_club_id": {"$ne": ObjectId(stranger_club["id"])},
        }
    )
    assert (
        client.get(
            f"/api/competition/matches/{foreign_fixture['_id']}", headers=stranger
        ).status_code
        == 403
    )


def test_legacy_player_model_migration_preserves_contract_and_removes_potential(client):
    headers, club, _, home, _ = setup(client)
    db = app.state.database
    player_id = ObjectId(home.lineup[0].id)
    contract = db.player_contracts.find_one({"player_id": player_id})
    db.players.update_one(
        {"_id": player_id},
        {
            "$set": {"potential": 99, "integration": 40, "training_level": 55},
            "$unset": {"model_version": "", "morale": ""},
        },
    )
    repo = GameRepository(db)
    bootstrap_player_attributes(repo)
    player = db.players.find_one({"_id": player_id})
    assert (
        "potential" not in player and "integration" not in player and "training_level" not in player
    )
    assert player["morale"] == 50
    assert len(player["individual_skills"]) == 7
    assert db.player_training.find_one({"_id": player_id})["progress"] == 55
    assert db.player_contracts.find_one({"_id": contract["_id"]}) == contract
    bootstrap_player_attributes(repo)
    assert db.players.find_one({"_id": player_id}) == player
