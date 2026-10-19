from os import getenv
from time import monotonic

from pymongo import timeout
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.repositories.game import GameRepository
from app.services.competition import CompetitionService


class HealthService:
    def __init__(self, database: Database):
        self.database = database

    def check(self) -> dict[str, object]:
        repository = GameRepository(self.database)
        competition = CompetitionService(repository)
        complete = False
        # Each committed step survives a cancelled serverless request.
        deadline = monotonic() + 4
        try:
            with timeout(5):
                self.database.command("ping")
                while monotonic() < deadline:
                    if competition.initialize_universe(max_steps=1) is not None:
                        complete = True
                        break
        except PyMongoError as error:
            if not error.timeout:
                raise
        with timeout(2):
            return self.progress(repository, competition, complete)

    def progress(self, repository, competition, complete):
        season = competition.current(repository)
        divisions = repository.many(
            "divisions", {"active": {"$ne": False}}, limit=None, projection={"_id": 1}
        )
        query = {
            "season_id": season["_id"] if season else None,
            "division_id": {"$in": [d["_id"] for d in divisions]},
        }
        return {
            "status": "ok" if complete else "initializing",
            "api": "ok",
            "mongodb": "ok",
            "revision": getenv("VERCEL_GIT_COMMIT_SHA"),
            "league": {
                "status": "ready" if complete else "initializing",
                "divisions": len(divisions),
                "clubs": self.database.season_clubs.count_documents(query),
                "bots": self.database.standings.count_documents({**query, "is_bot": True}),
                "matches": self.database.matches.count_documents(query),
            },
        }
