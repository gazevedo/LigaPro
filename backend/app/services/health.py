from os import getenv

from pymongo.database import Database

from app.repositories.game import GameRepository
from app.services.competition import CompetitionService


class HealthService:
    def __init__(self, database: Database):
        self.database = database

    def check(self) -> dict[str, object]:
        self.database.command("ping")
        repository = GameRepository(self.database)
        competition = CompetitionService(repository)
        # A cached connection is not proof that the persistent league still exists.
        competition.initialize_universe()
        season = competition.current(repository)
        divisions = repository.many(
            "divisions", {"active": {"$ne": False}}, limit=None, projection={"_id": 1}
        )
        query = {"season_id": season["_id"], "division_id": {"$in": [d["_id"] for d in divisions]}}
        return {
            "status": "ok",
            "api": "ok",
            "mongodb": "ok",
            "revision": getenv("VERCEL_GIT_COMMIT_SHA"),
            "league": {
                "status": "ready",
                "divisions": len(divisions),
                "clubs": self.database.season_clubs.count_documents(query),
                "bots": self.database.standings.count_documents({**query, "is_bot": True}),
                "matches": self.database.matches.count_documents(query),
            },
        }
