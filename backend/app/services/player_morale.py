from pymongo import UpdateOne

from app.config.team_performance import MoraleConfig


class PlayerMoraleService:
    def __init__(self, config=None):
        self.config = config or MoraleConfig()

    @staticmethod
    def bounded(value):
        return max(0, min(100, value))

    def change(self, repo, player, influence):
        value = self.bounded(player.get("morale", self.config.initial) + influence)
        return repo.update("players", {"_id": player["_id"]}, {"$set": {"morale": value}})

    def after_match(self, repo, match, result, summaries):
        players = repo.many(
            "players",
            {
                "current_club_id": {"$in": [match["home_club_id"], match["away_club_id"]]},
                "status": {"$ne": "retired"},
            },
            limit=None,
        )
        by_id = {row["player_id"]: row for row in summaries}
        outcomes = {}
        for side, other in (("home", "away"), ("away", "home")):
            club_id = match[side + "_club_id"]
            difference = (
                result["score"][str(club_id)] - result["score"][str(match[other + "_club_id"])]
            )
            club = repo.find("clubs", {"_id": club_id}, {"result_streak": 1})
            previous = club.get("result_streak", 0)
            streak = (
                0
                if difference == 0
                else ((max(0, previous) + 1) if difference > 0 else (min(0, previous) - 1))
            )
            repo.update("clubs", {"_id": club_id}, {"$set": {"result_streak": streak}})
            outcomes[club_id] = streak
        changes = []
        for player in players:
            row = by_id.get(str(player["_id"]))
            played = row is not None and row["minutes"] > 0
            streak = outcomes[player["current_club_id"]]
            delta = self.config.victory if streak > 0 else self.config.defeat if streak < 0 else 0
            if played:
                delta += (
                    (min(3, max(0, abs(streak) - 1)) * (1 if streak > 0 else -1)) if streak else 0
                )
                delta += self.config.starting * row["starts"] + min(
                    6, self.config.goal * row["goals"]
                )
            else:
                delta = 1 if delta > 0 else -1 if delta < 0 else 0
            absent = 0 if played else player.get("matches_without_playing", 0) + 1
            if absent >= self.config.absence_threshold:
                delta -= min(6, 2 + (absent - self.config.absence_threshold) // 3)
            values = {
                "morale": self.bounded(player.get("morale", self.config.initial) + delta),
                "matches_without_playing": absent,
            }
            if played:
                values["last_played_at"] = match["date"]
            changes.append(UpdateOne({"_id": player["_id"]}, {"$set": values}))
        if changes:
            repo.database.players.bulk_write(changes, session=repo.session)
