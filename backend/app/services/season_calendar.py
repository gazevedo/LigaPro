from datetime import timedelta

from bson import ObjectId
from fastapi import HTTPException

from app.config.game import GameConfig
from app.models.game import public, utcnow


class SeasonCalendarService:
    @staticmethod
    def ensure(repo, club_id, season):
        config = GameConfig(**season["config"])
        events = [
            ("season_start", season["starts_at"], "Início da temporada"),
            ("season_end", season["ends_at"], "Fim da temporada"),
        ]
        for start, length in [
            (0, config.PRESEASON_DAYS),
            (config.midseason_start, config.MIDSEASON_TRANSFER_WINDOW_DAYS),
        ]:
            events.extend(
                [
                    (
                        "transfer_window_open",
                        season["starts_at"] + timedelta(days=start),
                        "Abertura da janela",
                    ),
                    (
                        "transfer_window_close",
                        season["starts_at"] + timedelta(days=start + length),
                        "Fechamento da janela",
                    ),
                ]
            )
        for month in range(1, 13):
            events.append(
                (
                    "financial_close",
                    season["starts_at"] + timedelta(days=config.SEASON_DURATION_DAYS * month / 12),
                    "Fechamento financeiro",
                )
            )
        for kind, date, title in events:
            identity = f"{club_id}:{season['_id']}:{kind}:{date.isoformat(timespec='milliseconds')}"
            repo.database.calendar_events.update_one(
                {"_id": identity},
                {
                    "$setOnInsert": {
                        "club_id": club_id,
                        "season_id": season["_id"],
                        "type": kind,
                        "kind": kind,
                        "title": title,
                        "date": date,
                        "reference_id": season["_id"],
                    }
                },
                upsert=True,
                session=repo.session,
            )

    @staticmethod
    def free(repo, clubs, date, exclude=None):
        for collection in ["matches", "competition_matches", "friendly_matches"]:
            query = {
                "status": {"$in": ["scheduled", "pending", "live"]},
                "date": {"$gt": date - timedelta(minutes=90), "$lt": date + timedelta(minutes=90)},
                "$or": [{"home_club_id": {"$in": clubs}}, {"away_club_id": {"$in": clubs}}],
            }
            if exclude:
                query["_id"] = {"$ne": exclude}
            if repo.find(collection, query):
                raise HTTPException(409, "Horário ocupado por outra partida.")


class FriendlyService:
    def __init__(self, repo):
        self.repo = repo

    def create(self, user, data):
        def operation(repo):
            from app.services.competition import CompetitionService

            CompetitionService.lock(repo)
            club, rival = repo.owned(user.id), repo.document("clubs", data.opponent_club_id)
            season = CompetitionService.current(repo)
            if rival["_id"] == club["_id"] or rival.get("active") is False:
                raise HTTPException(409, "Adversário indisponível.")
            if (
                not season
                or data.date.tzinfo is None
                or not utcnow() < data.date < season["ends_at"]
            ):
                raise HTTPException(422, "Escolha um horário futuro nesta temporada.")
            SeasonCalendarService.free(repo, [club["_id"], rival["_id"]], data.date)
            match = repo.insert(
                "friendly_matches",
                {
                    "_id": ObjectId(),
                    "season_id": season["_id"],
                    "home_club_id": club["_id"],
                    "away_club_id": rival["_id"],
                    "date": data.date,
                    "seed": str(ObjectId()),
                    "status": "scheduled" if rival.get("is_bot") else "pending",
                    "created_at": utcnow(),
                },
            )
            if match["status"] == "scheduled":
                for club_id in [club["_id"], rival["_id"]]:
                    repo.event(club_id, "friendly", "Amistoso", match["date"], match["_id"])
            return public(match)

        return self.repo.transaction(operation)

    def accept(self, user, identity):
        def operation(repo):
            from app.services.competition import CompetitionService

            CompetitionService.lock(repo)
            club, match = repo.owned(user.id), repo.document("friendly_matches", identity)
            if club["_id"] != match["away_club_id"]:
                raise HTTPException(403, "Somente o clube convidado pode aceitar.")
            if match["status"] != "pending" or match["date"] <= utcnow():
                raise HTTPException(409, "Convite encerrado.")
            SeasonCalendarService.free(
                repo, [match["home_club_id"], match["away_club_id"]], match["date"], match["_id"]
            )
            for club_id in [match["home_club_id"], match["away_club_id"]]:
                repo.event(club_id, "friendly", "Amistoso", match["date"], match["_id"])
            return public(
                repo.update(
                    "friendly_matches", {"_id": match["_id"]}, {"$set": {"status": "scheduled"}}
                )
            )

        return self.repo.transaction(operation)

    def play(self, identity, now, result_override=None):
        def operation(repo):
            from app.services.bot_manager import BotManagerService
            from app.services.competition import CompetitionService
            from app.services.fan_base import FanBaseService
            from app.services.game import MarketService
            from app.services.match_engine import MatchEngine
            from app.services.physical_condition import InjuryService, PhysicalConditionService
            from app.services.player_statistics import match_player_summaries

            CompetitionService.lock(repo)
            match = repo.find(
                "friendly_matches",
                {
                    "_id": identity,
                    "status": "live" if result_override is not None else "scheduled",
                    "date": {"$lte": now},
                },
            )
            if not match:
                return
            for club_id in (
                []
                if result_override is not None
                else [match["home_club_id"], match["away_club_id"]]
            ):
                PhysicalConditionService().prepare(repo, club_id, match["date"])
                BotManagerService.prepare(repo, club_id, match["date"])
                try:
                    MarketService.repair_lineup(repo, club_id)
                except HTTPException as exc:
                    if exc.status_code != 409:
                        raise
            home, away = [
                CompetitionService.match_team(repo, match[f"{side}_club_id"])
                for side in ["home", "away"]
            ]
            if result_override is not None:
                result = result_override
            elif not home or not away:
                result = {
                    "walkover": True,
                    "events": [],
                    "score": {
                        str(match["home_club_id"]): 3 if home else 0,
                        str(match["away_club_id"]): 3 if away else 0,
                    },
                }
            else:
                result = MatchEngine().simulate(home, away, match["seed"])
            if not result.get("walkover"):
                from app.services.player_ratings import PlayerRatingService

                rows = match_player_summaries(result)
                PlayerRatingService.after_match(repo, match, result, rows)
                PhysicalConditionService().after_match(repo, match, result, rows)
                InjuryService.after_match(repo, match, result)
                FanBaseService.after_match(
                    repo,
                    match,
                    result["score"][str(match["home_club_id"])],
                    result["score"][str(match["away_club_id"])],
                    0.65,
                )
            repo.update(
                "friendly_matches",
                {"_id": identity},
                {"$set": {"status": "completed", "result": result, "completed_at": now}},
            )
            from app.services.game_history import MatchReportService

            MatchReportService.persist(repo, match, result)
            return public(repo.find("friendly_matches", {"_id": identity}))

        return self.repo.transaction(operation)
