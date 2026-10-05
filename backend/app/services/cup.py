"""Single-leg national cup, persisted rounds and offline progression."""

from datetime import timedelta
from random import Random

from bson import ObjectId
from fastapi import HTTPException

from app.config.cup import CupConfig
from app.models.game import public, utcnow
from app.services.chemistry import ChemistryService
from app.services.club_prestige import ClubRankingService, ClubReputationService
from app.services.fan_base import FanBaseService
from app.services.market_value import MarketValueService
from app.services.match_engine import MatchEngine
from app.services.monthly_finance import MonthlyFinanceService
from app.services.physical_condition import InjuryService, PhysicalConditionService
from app.services.player_morale import PlayerMoraleService
from app.services.player_ratings import PlayerRatingService
from app.services.player_statistics import PlayerStatisticsService, match_player_summaries


def bracket(clubs, seed):
    if len(set(clubs)) != len(clubs) or len(clubs) < 2:
        raise ValueError("Distinct participants required")
    players = list(clubs)
    Random(str(seed)).shuffle(players)
    size = 1 << (len(players) - 1).bit_length()
    byes = size - len(players)
    return players[:byes], list(zip(players[byes::2], players[byes + 1 :: 2]))


def phase_name(size):
    return {2: "Final", 4: "Semifinal", 8: "Quartas de final", 16: "Oitavas de final"}.get(
        size, "Primeira fase" if size >= 32 else "Eliminatórias"
    )


class CupService:
    def __init__(self, repo):
        self.repo = repo

    @staticmethod
    def ensure(repo, season):
        existing = repo.find("competitions", {"season_id": season["_id"], "name": "Copa Nacional"})
        if existing:
            return existing
        config = CupConfig.from_rules(repo.rules())
        slots = repo.many("season_clubs", {"season_id": season["_id"]}, limit=None)
        clubs = repo.many(
            "clubs",
            {
                "_id": {"$in": [s["club_id"] for s in slots]},
                "active": {"$ne": False},
                "division_tier": {"$lte": config.MAX_DIVISION_TIER},
            },
            limit=None,
            sort=[("division_tier", 1), ("ranking_points", -1), ("_id", 1)],
        )[: config.MAX_PARTICIPANTS]
        if len(clubs) < 2:
            return None
        ids = [c["_id"] for c in clubs]
        byes, pairs = bracket(ids, season["_id"])
        rounds = (len(ids) - 1).bit_length()
        duration = (season["ends_at"] - season["starts_at"]).total_seconds() / 86400
        competition = repo.insert(
            "competitions",
            {
                "_id": ObjectId(),
                "season_id": season["_id"],
                "name": "Copa Nacional",
                "status": "active",
                "round_count": rounds,
                "round_dates": [
                    season["starts_at"]
                    + timedelta(
                        days=season["config"]["PRESEASON_DAYS"]
                        + (duration - season["config"]["PRESEASON_DAYS"] - 1)
                        * (i + 1)
                        / (rounds + 1)
                        + 0.125
                    )
                    for i in range(rounds)
                ],
                "config": {
                    "PHASE_PRIZE": config.PHASE_PRIZE,
                    "CHAMPION_PRIZE": config.CHAMPION_PRIZE,
                },
            },
        )
        repo.insert_many(
            "competition_entries",
            [
                {
                    "_id": ObjectId(),
                    "competition_id": competition["_id"],
                    "club_id": identity,
                    "status": "active",
                    "phase": phase_name(1 << rounds),
                }
                for identity in ids
            ],
        )
        CupService.create_round(repo, competition, 1, pairs, byes)
        return competition

    @staticmethod
    def create_round(repo, competition, number, pairs, byes=()):
        phase = phase_name(1 << (competition["round_count"] - number + 1))
        round_doc = repo.insert(
            "competition_rounds",
            {
                "_id": ObjectId(),
                "competition_id": competition["_id"],
                "number": number,
                "phase": phase,
                "byes": list(byes),
                "status": "scheduled",
            },
        )
        for home, away in pairs:
            identity = ObjectId()
            date = competition["round_dates"][number - 1]
            repo.insert(
                "competition_matches",
                {
                    "_id": identity,
                    "competition_id": competition["_id"],
                    "season_id": competition["season_id"],
                    "round_id": round_doc["_id"],
                    "round": number,
                    "phase": phase,
                    "home_club_id": home,
                    "away_club_id": away,
                    "date": date,
                    "seed": str(identity),
                    "status": "scheduled",
                },
            )
            for club_id in (home, away):
                repo.event(club_id, "match", f"Copa Nacional · {phase}", date, identity)
        repo.update_many(
            "competition_entries",
            {"competition_id": competition["_id"], "status": "active"},
            {"$set": {"phase": phase}},
        )

    def play(self, identity, now=None):
        from app.services.competition import CompetitionService
        from app.services.player_contracts import ContractService

        now = now or utcnow()
        pending = self.repo.find("competition_matches", {"_id": identity, "status": "scheduled"})
        if pending and pending["date"] <= now:
            from app.services.game import MarketService

            MarketService.return_loans(self.repo, pending["date"])
            MonthlyFinanceService.process_due(self.repo, pending["date"])
            from app.services.bot_manager import BotManagerService

            BotManagerService(self.repo).process_due(pending["date"])
            ContractService(self.repo).process_due(pending["date"])

        def operation(repo):
            CompetitionService.lock(repo)
            match = repo.find("competition_matches", {"_id": identity, "status": "scheduled"})
            if not match or match["date"] > now:
                return
            for club_id in sorted([match["home_club_id"], match["away_club_id"]]):
                repo.update("clubs", {"_id": club_id}, {"$inc": {"roster_revision": 1}})
            for club_id in (match["home_club_id"], match["away_club_id"]):
                PhysicalConditionService().prepare(repo, club_id, match["date"])
                from app.services.bot_manager import BotManagerService

                if repo.find("clubs", {"_id": club_id}).get("is_bot"):
                    BotManagerService.prepare(repo, club_id, match["date"])
                else:
                    try:
                        MarketService.repair_lineup(repo, club_id)
                    except HTTPException as exc:
                        if exc.status_code != 409:
                            raise
            home, away = [
                CompetitionService.match_team(repo, match[f"{side}_club_id"])
                for side in ("home", "away")
            ]
            if home and away:
                result = MatchEngine().simulate_knockout(home, away, match["seed"])
            else:
                winner = (
                    match["home_club_id"]
                    if home
                    else match["away_club_id"]
                    if away
                    else min(match["home_club_id"], match["away_club_id"])
                )
                result = {
                    "walkover": True,
                    "winner_id": str(winner),
                    "score": {
                        str(match["home_club_id"]): 3 if home else 0,
                        str(match["away_club_id"]): 3 if away else 0,
                    },
                    "events": [],
                }
            winner = ObjectId(result["winner_id"])
            loser = (
                match["away_club_id"] if winner == match["home_club_id"] else match["home_club_id"]
            )
            summaries = match_player_summaries(result)
            PlayerStatisticsService.after_match(repo, match, summaries)
            PlayerRatingService.after_match(repo, match, result, summaries)
            if summaries:
                PlayerMoraleService().after_match(repo, match, result, summaries)
                ChemistryService().after_match(repo, match, result, summaries)
                PhysicalConditionService().after_match(repo, match, result, summaries)
                InjuryService.after_match(repo, match, result)
            goals = [result["score"][str(match[f"{side}_club_id"])] for side in ("home", "away")]
            FanBaseService.after_match(repo, match, *goals, importance=1.3)
            ClubRankingService.result(repo, winner, 3)
            ClubRankingService.result(repo, loser, 0)
            competition = repo.find("competitions", {"_id": match["competition_id"]})
            repo.money(winner, competition["config"]["PHASE_PRIZE"], "prize", identity)
            repo.update(
                "competition_entries",
                {"competition_id": competition["_id"], "club_id": loser},
                {"$set": {"status": "eliminated"}},
            )
            repo.update(
                "competition_matches",
                {"_id": identity},
                {
                    "$set": {
                        "status": "completed",
                        "result": result,
                        "winner_club_id": winner,
                        "home_goals": goals[0],
                        "away_goals": goals[1],
                        "completed_at": now,
                    }
                },
            )
            for club_id in (match["home_club_id"], match["away_club_id"]):
                repo.update(
                    "calendar_events",
                    {"club_id": club_id, "reference_id": identity},
                    {
                        "$set": {
                            "status": "completed",
                            "title": f"Copa Nacional · {match['phase']} · {goals[0]} x {goals[1]}",
                        }
                    },
                )
            if not repo.find(
                "competition_matches", {"round_id": match["round_id"], "status": "scheduled"}
            ):
                round_doc = repo.find("competition_rounds", {"_id": match["round_id"]})
                winners = list(round_doc["byes"]) + [
                    m["winner_club_id"]
                    for m in repo.many(
                        "competition_matches",
                        {"round_id": match["round_id"]},
                        limit=None,
                        sort=[("_id", 1)],
                    )
                ]
                repo.update(
                    "competition_rounds",
                    {"_id": round_doc["_id"]},
                    {"$set": {"status": "completed"}},
                )
                if len(winners) > 1:
                    self.create_round(
                        repo,
                        competition,
                        match["round"] + 1,
                        list(zip(winners[::2], winners[1::2])),
                    )
                else:
                    repo.money(
                        winner, competition["config"]["CHAMPION_PRIZE"], "prize", competition["_id"]
                    )
                    repo.update(
                        "competitions",
                        {"_id": competition["_id"]},
                        {
                            "$set": {
                                "status": "completed",
                                "champion_club_id": winner,
                                "completed_at": now,
                            }
                        },
                    )
                    repo.update(
                        "competition_entries",
                        {"competition_id": competition["_id"], "club_id": winner},
                        {"$set": {"status": "champion", "phase": "Campeão"}},
                    )
                    repo.update(
                        "clubs",
                        {"_id": winner},
                        {
                            "$push": {
                                "trophies": {
                                    "name": "Copa Nacional",
                                    "season_id": match["season_id"],
                                    "competition_id": competition["_id"],
                                }
                            },
                            "$inc": {"recent_title_points": 100},
                        },
                    )
                    FanBaseService.change(
                        repo, winner, "cup_title", competition["_id"], satisfaction=10, growth=0.08
                    )
                    ClubReputationService.cup_title(repo, winner)
            ClubRankingService.refresh(repo, match["season_id"], identity)
            MarketValueService().recalculate(
                repo,
                repo.many(
                    "players",
                    {"current_club_id": {"$in": [match["home_club_id"], match["away_club_id"]]}},
                    limit=None,
                ),
                "cup_match",
                identity,
                match["date"],
            )
            return public(repo.find("competition_matches", {"_id": identity}))

        return self.repo.transaction(operation)

    def process_due(self, season, now):
        from app.services.competition import CompetitionService

        def ensure(repo):
            CompetitionService.lock(repo)
            return self.ensure(repo, season)

        competition = self.repo.transaction(ensure)
        if not competition:
            return
        while True:
            pending = self.repo.many(
                "competition_matches",
                {
                    "competition_id": competition["_id"],
                    "status": "scheduled",
                    "date": {"$lte": now},
                },
                limit=None,
                sort=[("date", 1), ("_id", 1)],
            )
            if not pending:
                break
            for match in pending:
                self.play(match["_id"], now)

    def summary(self, user):
        from app.services.competition import CompetitionService

        club = self.repo.owned(user.id)
        season = CompetitionService.current(self.repo)
        competition = (
            self.repo.find("competitions", {"season_id": season["_id"], "name": "Copa Nacional"})
            if season
            else None
        )
        if not competition:
            return {"competition": None, "entry": None, "matches": []}
        entry = self.repo.find(
            "competition_entries", {"competition_id": competition["_id"], "club_id": club["_id"]}
        )
        matches = self.repo.many(
            "competition_matches",
            {
                "competition_id": competition["_id"],
                "$or": [{"home_club_id": club["_id"]}, {"away_club_id": club["_id"]}],
            },
            limit=None,
            sort=[("round", 1)],
            projection={"result": 0},
        )
        return public({"competition": competition, "entry": entry, "matches": matches})
