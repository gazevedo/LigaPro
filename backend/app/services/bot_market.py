"""Small bot recruitment policy: potential matters alongside current strength."""

from fastapi import HTTPException

from app.services.player_contracts import ContractService


class BotMarketService:
    def __init__(self, repository):
        self.repo = repository

    @staticmethod
    def score(player):
        strength = player.get("strength", player.get("overall", 50))
        return 0.65 * strength + 0.35 * player.get("potential", strength)

    def process_due(self):
        from app.services.competition import CompetitionService

        season = self.repo.find("seasons", {"status": "active"})
        if not season:
            return
        try:
            CompetitionService.require_transfer_window(self.repo)
        except HTTPException as exc:
            if exc.status_code == 409:
                return
            raise
        funded = self.repo.many(
            "club_finances", {"balance": {"$gt": 0}}, projection={"_id": 1}, limit=None
        )
        bots = self.repo.many(
            "clubs",
            {
                "_id": {"$in": [f["_id"] for f in funded]},
                "is_bot": True,
                "active": {"$ne": False},
                "last_market_season_id": {"$ne": season["_id"]},
            },
            limit=None,
        )
        if not bots:
            return
        for bot in bots:

            def operation(repo, identity=bot["_id"]):
                club = repo.find("clubs", {"_id": identity})
                if (
                    not club.get("is_bot")
                    or club.get("active") is False
                    or club.get("last_market_season_id") == season["_id"]
                ):
                    return
                if not repo.find("seasons", {"_id": season["_id"], "status": "active"}):
                    return
                CompetitionService.require_transfer_window(repo)
                balance = repo.find("club_finances", {"_id": identity})["balance"]
                budget = balance - ContractService.payroll(repo, identity)
                candidates = repo.many(
                    "players",
                    {"status": "free_agent", "owner_club_id": None, "current_club_id": None},
                    limit=None,
                )
                affordable = [
                    p
                    for p in candidates
                    if max(1000, p.get("strength", p.get("overall", 50)) * 100) <= budget
                ]
                if not affordable:
                    return
                player = max(affordable, key=lambda p: (self.score(p), str(p["_id"])))
                salary = max(1000, player.get("strength", player.get("overall", 50)) * 100)
                ContractService.sign_for_club(repo, club, player, salary, 2)
                repo.update(
                    "clubs", {"_id": identity}, {"$set": {"last_market_season_id": season["_id"]}}
                )

            try:
                self.repo.transaction(operation)
            except HTTPException as exc:
                if exc.status_code != 409:
                    raise
