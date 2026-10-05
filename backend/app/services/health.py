from pymongo.database import Database


class HealthService:
    def __init__(self, database: Database):
        self.database = database

    def check(self) -> dict[str, str]:
        self.database.command("ping")
        return {"status": "ok", "api": "ok", "mongodb": "ok"}
