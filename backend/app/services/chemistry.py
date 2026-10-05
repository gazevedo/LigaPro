from hashlib import sha256

from pymongo import UpdateOne

from app.config.team_performance import ChemistryConfig
from app.models.game import utcnow


class ChemistryService:
    def __init__(self, config=None):
        self.config = config or ChemistryConfig()

    def get(self, repo, club_id):
        return repo.find("club_chemistry", {"_id": club_id}) or {
            "_id": club_id,
            "club_id": club_id,
            "value": self.config.initial,
            "last_lineup_hash": None,
            "last_formation": None,
            "last_lineup_ids": [],
        }

    def save(self, repo, club_id, changes, now=None):
        baseline = self.get(repo, club_id)
        values = {**baseline, **changes, "updated_at": now or utcnow()}
        values.pop("_id", None)
        values["value"] = max(0, min(100, values["value"]))
        repo.database.club_chemistry.update_one(
            {"_id": club_id}, {"$set": values}, upsert=True, session=repo.session
        )
        return values

    def lineup_change(self, repo, club_id, previous, starters, formation):
        changes = len(set(previous["starters"]) - set(starters))
        loss = min(12, changes * 2) + (2 if previous["formation"] != formation else 0)
        if loss:
            state = self.get(repo, club_id)
            self.save(repo, club_id, {"value": state["value"] - loss})

    def recruit(self, repo, club_id):
        state = self.get(repo, club_id)
        self.save(repo, club_id, {"value": state["value"] - self.config.signing_loss})

    def available(self, repo, club_id, players):
        state = self.get(repo, club_id)
        integration = sum(p.get("integration", self.config.initial) for p in players) / max(
            1, len(players)
        )
        return min(state["value"], integration)

    def after_match(self, repo, match, result, summaries):
        for side in ("home", "away"):
            club_id = match[side + "_club_id"]
            team = result["snapshot"][side]
            ids = sorted(p["id"] for p in team["lineup"])
            state = self.get(repo, club_id)
            if state.get("last_match_id") == match["_id"]:
                continue
            overlap = len(set(ids) & set(state.get("last_lineup_ids", [])))
            gain = 1 + (2 if overlap == 11 else 1 if overlap >= 8 else 0)
            if state["last_formation"] == team["formation"]:
                gain += 1
            if state.get("last_lineup_ids") and overlap < 8:
                gain -= min(12, (11 - overlap) * 2)
            switches = sum(
                e["type"] == "formation_change" and e["team_id"] == team["id"]
                for e in result["events"]
            )
            gain -= min(5, switches)
            players = repo.many(
                "players", {"current_club_id": club_id, "status": {"$ne": "retired"}}, limit=None
            )
            by_id = {row["player_id"]: row for row in summaries if row["club_id"] == str(club_id)}
            updates, tenured = [], 0
            for player in players:
                row = by_id.get(str(player["_id"]))
                tenure = max(
                    0,
                    (
                        match["date"]
                        - player.get("joined_at", player.get("created_at", match["date"]))
                    ).total_seconds(),
                )
                time_gain = int(tenure >= 86400)
                tenured += time_gain
                played_gain = row["minutes"] // 15 if row else 0
                value = min(
                    100, player.get("integration", self.config.initial) + time_gain + played_gain
                )
                updates.append(UpdateOne({"_id": player["_id"]}, {"$set": {"integration": value}}))
            if players and tenured >= len(players) / 2:
                gain += 1
            if updates:
                repo.database.players.bulk_write(updates, session=repo.session)
            final = next(t for t in result["final_lineups"] if t["id"] == team["id"])
            self.save(
                repo,
                club_id,
                {
                    "value": state["value"] + gain,
                    "last_lineup_hash": sha256(",".join(ids).encode()).hexdigest(),
                    "last_lineup_ids": ids,
                    "last_formation": final["formation"],
                    "last_match_id": match["_id"],
                },
                match["date"],
            )
