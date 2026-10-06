"""Derive actual playing intervals from the initial snapshot and ordered events."""

from bson import ObjectId
from fastapi import HTTPException
from pymongo import UpdateOne

from app.models.game import public

STAT_FIELDS = (
    "matches",
    "starts",
    "minutes",
    "goals",
    "yellow_cards",
    "red_cards",
    "penalties_scored",
    "penalties_missed",
    "assists",
    "saves",
    "clean_sheets",
)


def match_player_summaries(result):
    if result.get("walkover") or not result.get("snapshot"):
        return []
    rows, active, entries, teams = {}, {}, {}, {}
    documents = {}
    for side in ("home", "away"):
        team = result["snapshot"][side]
        teams[team["id"]] = team
        active[team["id"]] = set()
        for player in team["lineup"] + team.get("reserves", []):
            documents[player["id"]] = player
        for player in team["lineup"]:
            identity = player["id"]
            rows[identity] = {
                "player_id": identity,
                "club_id": team["id"],
                "position": player["assigned_position"],
                **dict.fromkeys(STAT_FIELDS, 0),
                "shots": 0,
                "offensive_actions": 0,
                "defensive_actions": 0,
                "goals_conceded": 0,
            }
            rows[identity]["starts"] = 1
            active[team["id"]].add(identity)
            entries[identity] = 0

    def leave(identity, minute, club_id):
        if identity in active[club_id]:
            rows[identity]["minutes"] += max(0, minute - entries[identity])
            active[club_id].remove(identity)

    for event in result["events"]:
        kind, club_id, identity = event["type"], event["team_id"], event.get("player_id")
        if club_id not in active:
            continue
        if kind == "injury" and event.get("cannot_continue") and identity in rows:
            leave(identity, event["minute"], club_id)
        if kind == "substitution":
            outgoing, incoming = event["out_player_id"], event["in_player_id"]
            if outgoing not in rows or incoming not in documents:
                continue
            leave(outgoing, event["minute"], club_id)
            rows[incoming] = {
                "player_id": incoming,
                "club_id": club_id,
                "position": rows[outgoing]["position"],
                **dict.fromkeys(STAT_FIELDS, 0),
                "shots": 0,
                "offensive_actions": 0,
                "defensive_actions": 0,
                "goals_conceded": 0,
            }
            rows[incoming]["starts"] = int(event["minute"] == 0)
            active[club_id].add(incoming)
            entries[incoming] = event["minute"]
            continue
        if kind in {"phase_participation", "defensive_action"}:
            field = "offensive_actions" if kind == "phase_participation" else "defensive_actions"
            for participant in event.get("player_ids", []):
                if participant in active[club_id]:
                    rows[participant][field] += 1
        if kind == "duel":
            winner = event["winner_id"]
            if winner in rows and winner in active[rows[winner]["club_id"]]:
                field = (
                    "defensive_actions" if winner == event["defender_id"] else "offensive_actions"
                )
                rows[winner][field] += 1
        if kind == "goal":
            for rival_id in active:
                if rival_id != club_id:
                    for rival in active[rival_id]:
                        rows[rival]["goals_conceded"] += 1
        if identity in rows:
            row = rows[identity]
            if kind in {"goal", "shot_saved", "shot_off_target"}:
                row["shots"] += 1
                if event.get("penalty"):
                    row["penalties_scored" if kind == "goal" else "penalties_missed"] += 1
            if kind == "goal":
                row["goals"] += 1
            if kind == "yellow_card":
                row["yellow_cards"] += 1
            if kind == "red_card":
                row["red_cards"] += 1
                leave(identity, event["minute"], club_id)
        if kind == "shot_saved" and event.get("goalkeeper_id") in rows:
            rows[event["goalkeeper_id"]]["saves"] += 1
    for club_id, participants in active.items():
        for identity in list(participants):
            leave(identity, result.get("duration", 90), club_id)
    for row in rows.values():
        row["matches"] = int(row["minutes"] > 0)
        row["clean_sheets"] = int(
            row["goals_conceded"] == 0
            and row["minutes"] >= 60
            and row["position"] in {"GK", "CB", "FB"}
        )
    return [row for row in rows.values() if row["matches"]]


class PlayerStatisticsService:
    def __init__(self, repository):
        self.repo = repository

    @staticmethod
    def after_match(repo, match, summaries):
        season_updates, career_updates = [], []
        for row in summaries:
            player_id, club_id = ObjectId(row["player_id"]), ObjectId(row["club_id"])
            increments = {key: row[key] for key in STAT_FIELDS}
            key = {"player_id": player_id, "club_id": club_id, "season_id": match["season_id"]}
            season_updates.append(
                UpdateOne(
                    key,
                    {
                        "$inc": increments,
                        "$set": {"updated_at": match["date"]},
                        "$setOnInsert": {"_id": ObjectId()},
                    },
                    upsert=True,
                )
            )
            career_updates.append(
                UpdateOne(
                    {"_id": player_id},
                    {
                        "$inc": increments,
                        "$set": {"player_id": player_id, "updated_at": match["date"]},
                    },
                    upsert=True,
                )
            )
        if summaries:
            repo.database.player_season_stats.bulk_write(season_updates, session=repo.session)
            repo.database.player_career_stats.bulk_write(career_updates, session=repo.session)

    def player(self, identity):
        player = self.repo.document("players", identity)
        return public(
            {
                "player_id": player["_id"],
                "career": self.repo.find("player_career_stats", {"_id": player["_id"]}),
                "seasons": self.repo.many(
                    "player_season_stats",
                    {"player_id": player["_id"]},
                    limit=None,
                    sort=[("season_id", -1)],
                ),
            }
        )

    def rankings(self, ranking, season_id=None, club_id=None):
        if season_id:
            season = self.repo.document("seasons", season_id)
        else:
            season = self.repo.find("seasons", {"status": "active"})
        if not season:
            return {"season": None, "ranking": ranking, "rows": []}
        group = {
            "_id": "$player_id",
            "club_ids": {"$addToSet": "$club_id"},
            **{key: {"$sum": "$" + key} for key in STAT_FIELDS},
        }
        metric = {
            "goals": "$goals",
            "matches": "$matches",
            "cards": {"$add": ["$yellow_cards", "$red_cards"]},
        }[ranking]
        rows = list(
            self.repo.database.player_season_stats.aggregate(
                [
                    {"$match": {"season_id": season["_id"]}},
                    {"$group": group},
                    {"$set": {"total": metric}},
                    {"$sort": {"total": -1, "minutes": -1, "_id": 1}},
                    {"$limit": 20},
                    {
                        "$lookup": {
                            "from": "players",
                            "localField": "_id",
                            "foreignField": "_id",
                            "as": "player",
                        }
                    },
                    {
                        "$set": {
                            "player_id": "$_id",
                            "name": {"$arrayElemAt": ["$player.name", 0]},
                            "position": {"$arrayElemAt": ["$player.position", 0]},
                        }
                    },
                    {"$unset": "player"},
                ],
                session=self.repo.session,
            )
        )
        seasons = self.repo.many(
            "seasons", {}, projection={"number": 1}, sort=[("number", -1)], limit=20
        )
        recent = (
            self.repo.many(
                "matches",
                {
                    "season_id": season["_id"],
                    "status": "completed",
                    "$or": [{"home_club_id": club_id}, {"away_club_id": club_id}],
                },
                projection={
                    "date": 1,
                    "round": 1,
                    "home_club_id": 1,
                    "away_club_id": 1,
                    "home_goals": 1,
                    "away_goals": 1,
                },
                sort=[("date", -1)],
                limit=10,
            )
            if club_id
            else []
        )
        return public(
            {
                "season": season,
                "seasons": seasons,
                "ranking": ranking,
                "rows": rows,
                "recent_matches": recent,
            }
        )

    def report(self, user, identity):
        club = self.repo.owned(user.id)
        if not ObjectId.is_valid(identity):
            raise HTTPException(404, "Registro não encontrado.")
        match = (
            self.repo.find("matches", {"_id": ObjectId(identity)})
            or self.repo.find("competition_matches", {"_id": ObjectId(identity)})
            or self.repo.document("friendly_matches", identity)
        )
        involved = club["_id"] in {match["home_club_id"], match["away_club_id"]}
        inherited = (
            self.repo.find(
                "season_clubs",
                {
                    "_id": {"$in": [match.get("home_slot_id"), match.get("away_slot_id")]},
                    "club_id": club["_id"],
                },
            )
            if not involved
            else None
        )
        if not involved and not inherited:
            raise HTTPException(403, "Partida de outro clube.")
        if match["status"] != "completed":
            raise HTTPException(409, "Partida ainda não concluída.")
        ratings = self.repo.many(
            "player_match_ratings",
            {"match_id": match["_id"]},
            limit=None,
            sort=[("club_id", 1), ("rating", -1)],
        )
        players = {
            p["_id"]: p
            for p in self.repo.many(
                "players",
                {"_id": {"$in": [r["player_id"] for r in ratings]}},
                projection={"name": 1, "position": 1},
                limit=None,
            )
        }
        clubs = {
            c["_id"]: c
            for c in self.repo.many(
                "clubs",
                {"_id": {"$in": [match["home_club_id"], match["away_club_id"]]}},
                projection={"name": 1},
            )
        }
        projection = self.repo.find("match_stats", {"_id": match["_id"]}) or {}
        return public(
            {
                "match": {
                    key: match.get(
                        key,
                        match.get("result", {})
                        .get("score", {})
                        .get(
                            str(
                                match.get("home_club_id" if key == "home_goals" else "away_club_id")
                            ),
                            0,
                        )
                        if key in {"home_goals", "away_goals"}
                        else None,
                    )
                    for key in (
                        "_id",
                        "date",
                        "round",
                        "season_id",
                        "home_club_id",
                        "away_club_id",
                        "home_goals",
                        "away_goals",
                    )
                }
                | {key: match[key] for key in ("phase", "winner_club_id") if key in match}
                | {
                    key: match.get("result", {}).get(key)
                    for key in ("extra_time", "shootout_score")
                },
                "competition": "Copa Nacional"
                if "competition_id" in match
                else "Amistoso"
                if "division_id" not in match
                else "Campeonato",
                "events": self.repo.many(
                    "match_events", {"match_id": match["_id"]}, limit=None, sort=[("sequence", 1)]
                )
                or match.get("result", {}).get("events", []),
                **{
                    key: projection.get(
                        key,
                        match.get("result", {}).get("statistics", {})
                        if key == "statistics"
                        else []
                        if key == "consequences"
                        else {},
                    )
                    for key in ["statistics", "financial", "consequences"]
                },
                "home_name": clubs.get(match["home_club_id"], {}).get("name", "Mandante"),
                "away_name": clubs.get(match["away_club_id"], {}).get("name", "Visitante"),
                "ratings": [
                    {
                        **r,
                        "name": players.get(r["player_id"], {}).get("name", "Jogador"),
                        "position": players.get(r["player_id"], {}).get("position", ""),
                    }
                    for r in ratings
                ],
            }
        )
