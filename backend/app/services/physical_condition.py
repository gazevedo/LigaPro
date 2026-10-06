from datetime import timedelta

from bson import ObjectId
from pymongo import UpdateOne

from app.config.game import GameConfig
from app.config.physical import PhysicalConfig


class PhysicalConditionService:
    def __init__(self, config=None):
        self.config = config or PhysicalConfig()

    def recover(self, player, now, medical_level=1):
        previous = player.get("condition_updated_at", player.get("created_at", now))
        days = max(0, (now - previous).total_seconds() / 86400)
        age = max(0.65, 1 - max(0, player["age"] - 27) * 0.015)
        current = player.get("physical_condition", 100)
        rate = (self.config.recovery_per_day + self.config.medical_bonus * medical_level) * age
        rest = 1.1 if not player.get("last_played_at") or player["last_played_at"] < previous else 1
        return {
            "physical_condition": min(100, round(current + days * rate * rest, 2)),
            "energy": min(100, round(player.get("energy", 100) + days * 45 * age, 2)),
            "condition_updated_at": max(previous, now),
        }

    @staticmethod
    def wear(player, minutes, marking="light", style="balanced"):
        age = 1 + max(0, player["age"] - 27) * 0.012
        energy = 1 + max(0, 100 - player.get("energy", 100)) / 250
        intensity = {"light": 1, "heavy": 1.15, "very_heavy": 1.30}[marking] * (
            1.12 if style == "all_out_attack" else 1
        )
        return 14 * minutes / 90 * age * energy * intensity

    def prepare(self, repo, club_id, now):
        stadium = repo.find("stadiums", {"_id": club_id}) or {}
        medical = stadium.get("facilities", {}).get("medical", 1)
        updates = []
        for player in repo.many(
            "players", {"current_club_id": club_id, "status": {"$ne": "retired"}}, limit=None
        ):
            changes = self.recover(player, now, medical)
            if player.get("suspended_until") and player["suspended_until"] <= now:
                changes.update(
                    status="injured"
                    if player.get("injury_return_at")
                    and player["injury_return_at"] > now
                    and player.get("status") == "injured"
                    else "available",
                    suspended_until=None,
                )
            if player.get("injury_return_at") and player["injury_return_at"] <= now:
                changes.update(
                    status="suspended"
                    if player.get("suspended_until") and player["suspended_until"] > now
                    else "available",
                    injury_return_at=None,
                    injury_type=None,
                )
                repo.update_many(
                    "player_injuries",
                    {"player_id": player["_id"], "status": "active"},
                    {"$set": {"status": "recovered", "recovered_at": now}},
                )
            if changes.get("status") == "available":
                changes["disease"] = None
            updates.append(UpdateOne({"_id": player["_id"]}, {"$set": changes}))
        if updates:
            repo.database.players.bulk_write(updates, session=repo.session)

    def after_match(self, repo, match, result, summaries):
        documents = {
            p["_id"]: p
            for p in repo.many(
                "players",
                {"current_club_id": {"$in": [match["home_club_id"], match["away_club_id"]]}},
                limit=None,
            )
        }
        final = {
            p["id"]: p
            for team in result.get("final_lineups", [])
            for p in team["lineup"] + team.get("reserves", [])
        }
        teams = {
            result["snapshot"][side]["id"]: result["snapshot"][side] for side in ("home", "away")
        }
        updates = []
        for row in summaries:
            player = documents[ObjectId(row["player_id"])]
            team = teams[row["club_id"]]
            changes = {
                "physical_condition": max(
                    0,
                    round(
                        player.get("physical_condition", 100)
                        - self.wear(player, row["minutes"], team["marking"], team["style"]),
                        2,
                    ),
                ),
                "energy": final.get(row["player_id"], {}).get(
                    "energy", max(0, player.get("energy", 100) - row["minutes"] * 0.3)
                ),
                "condition_updated_at": match["date"],
            }
            if row["red_cards"]:
                from app.services.news import NewsService

                NewsService.publish(
                    repo,
                    "suspension",
                    f"{player['name']} suspenso",
                    player["current_club_id"],
                    match["_id"],
                    player_id=player["_id"],
                    now=match["date"],
                )
                spacing = GameConfig.from_rules(repo.rules()).SEASON_DURATION_DAYS / 38
                changes.update(
                    status="suspended",
                    suspended_until=match["date"] + timedelta(days=spacing * 1.05),
                )
            updates.append(UpdateOne({"_id": player["_id"]}, {"$set": changes}))
        if updates:
            repo.database.players.bulk_write(updates, session=repo.session)


class InjuryService:
    @staticmethod
    def after_match(repo, match, result):
        spacing = GameConfig.from_rules(repo.rules()).SEASON_DURATION_DAYS / 38
        for event in result.get("events", []):
            if event["type"] != "injury":
                continue
            from app.services.news import NewsService

            NewsService.publish(
                repo,
                "injury",
                "Lesão durante a partida",
                ObjectId(event["team_id"]),
                f"{match['_id']}:{event['player_id']}",
                player_id=ObjectId(event["player_id"]),
                body=f"{event['injury_type']} · {event['severity']}",
                now=match["date"],
            )
            identity = ObjectId(event["player_id"])
            club_id = ObjectId(event["team_id"])
            duration = {
                "minor": event.get("matches_out", 2),
                "moderate": event.get("matches_out", 4),
                "serious": event.get("matches_out", 8),
            }[event["severity"]]
            end = match["date"] + timedelta(days=spacing * duration)
            repo.insert(
                "player_injuries",
                {
                    "_id": ObjectId(),
                    "player_id": identity,
                    "club_id": club_id,
                    "match_id": match["_id"],
                    "injury_type": event["injury_type"],
                    "severity": event["severity"],
                    "started_at": match["date"],
                    "expected_return_at": end,
                    "recovered_at": None,
                    "status": "active",
                    "created_at": match["date"],
                },
            )
            repo.update(
                "players",
                {"_id": identity},
                {
                    "$set": {
                        "status": "injured",
                        "injury_type": event["injury_type"],
                        "injury_return_at": end,
                        "disease": event["injury_type"],
                    }
                },
            )
