"""Compatibility entry point for the shared bot management policy."""


class BotMarketService:
    def __init__(self, repository):
        self.repo = repository

    @staticmethod
    def score(player):
        return player.get("strength", player.get("overall", 50))

    def process_due(self):
        from app.services.bot_manager import BotManagerService

        BotManagerService(self.repo).process_due()
