"""Persistent league slots preserve sporting history when a human replaces a bot."""

from datetime import timedelta

from bson import ObjectId
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.config.game import GameConfig
from app.models.game import public, utcnow
from app.services.chemistry import ChemistryService
from app.services.match_engine import MatchEngine, MatchPlayer, MatchTeam, arrange_formation
from app.services.player_contracts import ContractService
from app.services.player_development import PlayerAgingService, PlayerGeneratorService
from app.services.player_morale import PlayerMoraleService
from app.services.player_ratings import PlayerRatingService
from app.services.player_statistics import PlayerStatisticsService, match_player_summaries
from app.services.tactics import TacticsService


def division_name(tier):
    name = ""
    number = tier + 1
    while number:
        number, remainder = divmod(number - 1, 26)
        name = chr(65 + remainder) + name
    return name


def round_robin(slots):
    """Circle method: 19 rounds, then reversed venues for another 19."""
    if len(slots) != 20 or len(set(slots)) != 20:
        raise ValueError("A division requires twenty distinct slots")
    rotation = list(slots)
    first = []
    for round_index in range(19):
        pairs = [(rotation[i], rotation[-i - 1]) for i in range(10)]
        if round_index % 2:
            pairs = [(away, home) for home, away in pairs]
        first.append(pairs)
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]
    return first + [[(away, home) for home, away in pairs] for pairs in first]


def ranked(rows):
    return sorted(
        rows,
        key=lambda row: (
            -row["points"],
            -row["goal_difference"],
            -row["goals_for"],
            -row["wins"],
            str(row["_id"]),
        ),
    )


def movement(tables, config):
    destinations = {}
    last = max(tables)
    for tier, rows in tables.items():
        for position, row in enumerate(ranked(rows), 1):
            destination = tier
            if tier > 0 and position <= config.PROMOTION_COUNT:
                destination -= 1
            elif tier < last and position > 20 - config.RELEGATION_COUNT:
                destination += 1
            destinations[row["club_id"]] = destination
    return destinations


class CompetitionService:
    def __init__(self, repository):
        self.repo = repository

    @staticmethod
    def ensure_lock(repo):
        # Initialize outside the transaction so simultaneous first joins contend
        # on an existing document rather than racing its unique insertion.
        try:
            repo.database.game_state.update_one(
                {"_id": "universe"}, {"$setOnInsert": {"revision": 0}}, upsert=True
            )
        except DuplicateKeyError:
            pass

    @staticmethod
    def lock(repo):
        repo.update("game_state", {"_id": "universe"}, {"$inc": {"revision": 1}})

    @staticmethod
    def current(repo):
        return repo.find("seasons", {"status": "active"})

    @staticmethod
    def season_config(season):
        return GameConfig(**season["config"])

    @classmethod
    def require_transfer_window(cls, repo, now=None):
        cls.lock(repo)
        season = cls.current(repo)
        if not season:
            return
        config = cls.season_config(season)
        day = ((now or utcnow()) - season["starts_at"]).total_seconds() / 86400
        if not (
            0 <= day < config.PRESEASON_DAYS
            or config.midseason_start
            <= day
            < config.midseason_start + config.MIDSEASON_TRANSFER_WINDOW_DAYS
        ):
            raise HTTPException(409, "Transferências só podem ser concluídas durante as janelas.")

    @staticmethod
    def create_season(repo, starts_at, number=1):
        config = GameConfig.from_rules(repo.rules())
        season = {
            "_id": ObjectId(),
            "number": number,
            "status": "active",
            "starts_at": starts_at,
            "ends_at": starts_at + timedelta(days=config.SEASON_DURATION_DAYS),
            "config": config.snapshot(),
        }
        repo.insert("seasons", season)
        return season

    @staticmethod
    def create_bot(repo, tier, index, config):
        club_id = ObjectId()
        bot = {
            "_id": club_id,
            "is_bot": True,
            "active": True,
            "name": f"Bot {division_name(tier)} {index + 1:02}",
            "country_id": "BR",
            "badge_id": "blue",
            "created_at": utcnow(),
            "ranking": 0,
            "competition_positions": [],
            "trophies": [],
        }
        repo.insert("clubs", bot)
        players = PlayerGeneratorService(config, str(club_id)).squad(club_id, "BR")
        repo.insert_many("players", players)
        starters = []
        for position, count in (("GK", 1), ("DEF", 4), ("MID", 4), ("ATT", 2)):
            starters.extend([p["_id"] for p in players if p["position"] == position][:count])
        repo.insert(
            "lineups",
            {
                "_id": club_id,
                "formation": "4-4-2",
                "starters": starters,
                "reserves": [p["_id"] for p in players if p["_id"] not in starters],
            },
        )

        TacticsService.persist(
            repo,
            club_id,
            {
                "formation": "4-4-2",
                "play_style": "balanced",
                "marking": "light",
                "attack_focus": "normal",
            },
        )
        repo.insert("club_finances", {"_id": club_id, "balance": 0})
        ChemistryService().save(repo, club_id, {})
        ContractService.initial(repo, players, config)
        return bot

    @staticmethod
    def add_slot(repo, season, division, club):
        slot = {
            "_id": ObjectId(),
            "season_id": season["_id"],
            "division_id": division["_id"],
            "club_id": club["_id"],
            "is_bot": club.get("is_bot", False),
            "previous_club_ids": [],
        }
        repo.insert("season_clubs", slot)
        repo.insert(
            "standings",
            {
                "_id": slot["_id"],
                "season_id": season["_id"],
                "division_id": division["_id"],
                "club_id": club["_id"],
                "club_name": club["name"],
                "is_bot": slot["is_bot"],
                "games": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
                "goal_difference": 0,
                "points": 0,
                "position": 0,
            },
        )
        repo.update("clubs", {"_id": club["_id"]}, {"$set": {"division_tier": division["tier"]}})
        return slot

    @classmethod
    def schedule(cls, repo, season, division, slots):
        config = cls.season_config(season)
        by_id = {slot["_id"]: slot for slot in slots}
        fixtures, events = [], []
        for number, (pairs, offset) in enumerate(
            zip(round_robin(list(by_id)), config.round_offsets()), 1
        ):
            date = season["starts_at"] + timedelta(days=offset)
            for home, away in pairs:
                identity = ObjectId()
                fixture = {
                    "_id": identity,
                    "season_id": season["_id"],
                    "division_id": division["_id"],
                    "round": number,
                    "home_slot_id": home,
                    "away_slot_id": away,
                    "home_club_id": by_id[home]["club_id"],
                    "away_club_id": by_id[away]["club_id"],
                    "date": date,
                    "status": "scheduled",
                    "seed": str(identity),
                }
                fixtures.append(fixture)
                for club_id in (fixture["home_club_id"], fixture["away_club_id"]):
                    events.append(
                        {
                            "_id": ObjectId(),
                            "club_id": club_id,
                            "type": "match",
                            "title": f"Série {division['name']} · rodada {number}",
                            "date": date,
                            "reference_id": identity,
                            "season_id": season["_id"],
                        }
                    )
        repo.insert_many("matches", fixtures)
        repo.insert_many("calendar_events", events)
        cls.refresh_positions(repo, season["_id"], division["_id"])

    @staticmethod
    def refresh_positions(repo, season_id, division_id):
        rows = ranked(
            repo.many("standings", {"season_id": season_id, "division_id": division_id}, limit=None)
        )
        for position, row in enumerate(rows, 1):
            if row["position"] != position:
                repo.update("standings", {"_id": row["_id"]}, {"$set": {"position": position}})
        return rows

    def enroll(self, repo, club, now=None):
        self.lock(repo)
        season = self.current(repo) or self.create_season(repo, now or utcnow())
        existing = repo.find("season_clubs", {"season_id": season["_id"], "club_id": club["_id"]})
        if existing:
            return existing
        config = self.season_config(season)
        divisions = repo.many("divisions", {}, limit=None, sort=[("tier", 1)])
        for division in divisions:
            bots = repo.many(
                "standings",
                {"season_id": season["_id"], "division_id": division["_id"], "is_bot": True},
                limit=None,
                sort=[
                    ("position", -1 if config.BOT_REPLACEMENT_STRATEGY == "lowest_ranked" else 1)
                ],
            )
            if not bots:
                continue
            inherited = bots[0]
            old_club_id = inherited["club_id"]
            slot = repo.update(
                "season_clubs",
                {"_id": inherited["_id"]},
                {
                    "$set": {"club_id": club["_id"], "is_bot": False},
                    "$push": {"previous_club_ids": old_club_id},
                },
            )
            repo.update(
                "standings",
                {"_id": slot["_id"]},
                {"$set": {"club_id": club["_id"], "club_name": club["name"], "is_bot": False}},
            )
            for side in ("home", "away"):
                repo.update_many(
                    "matches",
                    {
                        "season_id": season["_id"],
                        "status": "scheduled",
                        f"{side}_slot_id": slot["_id"],
                    },
                    {"$set": {f"{side}_club_id": club["_id"]}},
                )
            repo.update_many(
                "calendar_events",
                {"season_id": season["_id"], "club_id": old_club_id, "type": "match"},
                {"$set": {"club_id": club["_id"]}},
            )
            repo.insert(
                "club_replacements",
                {
                    "_id": ObjectId(),
                    "season_id": season["_id"],
                    "slot_id": slot["_id"],
                    "division_id": division["_id"],
                    "old_club_id": old_club_id,
                    "new_club_id": club["_id"],
                    "inherited_standing": inherited,
                    "created_at": now or utcnow(),
                },
            )
            repo.update("clubs", {"_id": old_club_id}, {"$set": {"active": False}})
            repo.update(
                "clubs", {"_id": club["_id"]}, {"$set": {"division_tier": division["tier"]}}
            )
            return slot
        tier = len(divisions)
        division = repo.insert(
            "divisions", {"_id": ObjectId(), "tier": tier, "name": division_name(tier)}
        )
        slots = [self.add_slot(repo, season, division, club)]
        for index in range(19):
            bot = self.create_bot(repo, tier, index, config)
            slots.append(self.add_slot(repo, season, division, bot))
            self.generate_youth(repo, bot, season, config)
        self.schedule(repo, season, division, slots)
        self.generate_youth(repo, club, season, config)
        return slots[0]

    @staticmethod
    def generate_youth(repo, club, season, config):
        batch_id = f"{season['_id']}:{club['_id']}"
        if repo.find("youth_batches", {"_id": batch_id}):
            return
        players = PlayerGeneratorService(config, batch_id).youth(club["_id"], club["country_id"])
        if players:
            repo.insert_many(
                "youth_players", [{**p, "generated_season_id": season["_id"]} for p in players]
            )
        repo.insert(
            "youth_batches", {"_id": batch_id, "season_id": season["_id"], "club_id": club["_id"]}
        )

    def bootstrap(self):
        self.ensure_lock(self.repo)
        for club in self.repo.many(
            "clubs", {"is_bot": {"$ne": True}, "active": {"$ne": False}}, limit=None
        ):

            def enroll_existing(repo, identity=club["_id"]):
                current = repo.find("clubs", {"_id": identity})
                self.enroll(repo, current)
                season = self.current(repo)
                self.generate_youth(repo, current, season, self.season_config(season))

            self.repo.transaction(enroll_existing)

    def table(self, user):
        club = self.repo.owned(user.id)
        season = self.current(self.repo)
        slot = self.repo.find("season_clubs", {"season_id": season["_id"], "club_id": club["_id"]})
        division = self.repo.find("divisions", {"_id": slot["division_id"]})
        standings = self.repo.many(
            "standings",
            {"season_id": season["_id"], "division_id": division["_id"]},
            limit=None,
            sort=[("position", 1)],
        )
        return public({"season": season, "division": division, "standings": standings})

    def matches(self, user):
        club = self.repo.owned(user.id)
        season = self.current(self.repo)
        slot = self.repo.find("season_clubs", {"season_id": season["_id"], "club_id": club["_id"]})
        return public(
            self.repo.many(
                "matches",
                {
                    "season_id": season["_id"],
                    "$or": [{"home_slot_id": slot["_id"]}, {"away_slot_id": slot["_id"]}],
                },
                limit=None,
                sort=[("round", 1)],
            )
        )

    @staticmethod
    def match_team(repo, club_id):
        lineup = repo.find("lineups", {"_id": club_id})
        documents = repo.many(
            "players", {"current_club_id": club_id, "status": {"$ne": "retired"}}, limit=None
        )
        if len(documents) < 11:
            return None
        by_id = {p["_id"]: p for p in documents}
        selected = [by_id[p] for p in lineup["starters"] if p in by_id]
        # An aging squad can require improvisation. Fill missing role slots with
        # real active players; position fit in the engine applies the penalty.

        tactics = TacticsService.settings(repo, club_id, lineup)
        formation = tactics["formation"]

        pool = selected + [p for p in documents if p not in selected]
        pool_documents = pool[:11]
        players = arrange_formation(
            [MatchPlayer.from_document(p) for p in pool_documents], formation
        )
        pool = pool[11:]
        return MatchTeam(
            str(club_id),
            players,
            formation,
            tactics["play_style"],
            tactics["marking"],
            tactics["attack_focus"],
            [MatchPlayer.from_document(p) for p in pool if p["_id"] in lineup.get("reserves", [])],
            bool(repo.find("clubs", {"_id": club_id}, {"is_bot": 1}).get("is_bot", False)),
            ChemistryService().available(repo, club_id, pool_documents),
        )

    def play(self, identity, now=None):
        pending = self.repo.find("matches", {"_id": identity, "status": "scheduled"}, {"date": 1})
        if pending and pending["date"] <= (now or utcnow()):
            ContractService(self.repo).process_due(pending["date"])

        def operation(repo):
            self.lock(repo)
            match = repo.find("matches", {"_id": identity, "status": "scheduled"})
            if not match or match["date"] > (now or utcnow()):
                return
            for club_id in sorted([match["home_club_id"], match["away_club_id"]]):
                repo.update("clubs", {"_id": club_id}, {"$inc": {"roster_revision": 1}})
            home, away = (
                self.match_team(repo, match[f"{side}_club_id"]) for side in ("home", "away")
            )
            if home and away:
                result = MatchEngine().simulate(
                    home, away, match["seed"], commands=match.get("commands", [])
                )
                home_goals = result["score"][home.id]
                away_goals = result["score"][away.id]
            else:
                home_goals, away_goals = (3 if home else 0), (3 if away else 0)
                result = {
                    "walkover": True,
                    "seed": match["seed"],
                    "score": {
                        str(match["home_club_id"]): home_goals,
                        str(match["away_club_id"]): away_goals,
                    },
                    "events": [],
                }
            summaries = match_player_summaries(result)
            PlayerStatisticsService.after_match(repo, match, summaries)
            PlayerRatingService.after_match(repo, match, result, summaries)
            if summaries:
                PlayerMoraleService().after_match(repo, match, result, summaries)
                ChemistryService().after_match(repo, match, result, summaries)
            repo.update(
                "matches",
                {"_id": identity},
                {
                    "$set": {
                        "status": "completed",
                        "result": result,
                        "home_goals": home_goals,
                        "away_goals": away_goals,
                        "completed_at": now or utcnow(),
                    }
                },
            )
            for side, goals, against in (
                ("home", home_goals, away_goals),
                ("away", away_goals, home_goals),
            ):
                win, draw, loss = goals > against, goals == against, goals < against
                repo.update(
                    "standings",
                    {"_id": match[f"{side}_slot_id"]},
                    {
                        "$inc": {
                            "games": 1,
                            "wins": int(win),
                            "draws": int(draw),
                            "losses": int(loss),
                            "goals_for": goals,
                            "goals_against": against,
                            "goal_difference": goals - against,
                            "points": 3 if win else 1 if draw else 0,
                        }
                    },
                )
                repo.update(
                    "calendar_events",
                    {"reference_id": identity, "club_id": match[f"{side}_club_id"]},
                    {
                        "$set": {
                            "title": f"Rodada {match['round']} · {goals} x {against}",
                            "status": "completed",
                        }
                    },
                )
            self.refresh_positions(repo, match["season_id"], match["division_id"])
            return public(repo.find("matches", {"_id": identity}))

        return self.repo.transaction(operation)

    def process_due(self, now=None):
        self.ensure_lock(self.repo)
        now = now or utcnow()
        while season := self.current(self.repo):
            for match in self.repo.many(
                "matches",
                {"season_id": season["_id"], "status": "scheduled", "date": {"$lte": now}},
                limit=None,
                sort=[("date", 1), ("_id", 1)],
            ):
                self.play(match["_id"], now)
            if season["ends_at"] > now:
                break
            SeasonFinalizationService(self.repo).finalize(season["_id"], now)


class SeasonFinalizationService:
    def __init__(self, repository):
        self.repo = repository

    def finalize(self, season_id, now=None):
        service = CompetitionService(self.repo)
        service.ensure_lock(self.repo)
        now = now or utcnow()
        # Finish outstanding games separately; each persisted result is idempotent.
        season = self.repo.find("seasons", {"_id": season_id})
        if not season or season["status"] == "completed" or season["ends_at"] > now:
            return
        for match in self.repo.many(
            "matches",
            {"season_id": season_id, "status": "scheduled"},
            limit=None,
            sort=[("date", 1), ("_id", 1)],
        ):
            service.play(match["_id"], now)

        def operation(repo):
            service.lock(repo)
            current = repo.find("seasons", {"_id": season_id, "status": "active"})
            if not current:
                return
            if repo.find("matches", {"season_id": season_id, "status": "scheduled"}):
                raise HTTPException(409, "Temporada ainda possui partidas pendentes.")
            config = service.season_config(current)
            divisions = repo.many("divisions", {}, limit=None, sort=[("tier", 1)])
            tables = {
                division["tier"]: service.refresh_positions(repo, season_id, division["_id"])
                for division in divisions
            }
            destinations = movement(tables, config)
            champion = tables[0][0]["club_id"]
            trophy = {
                "season_id": season_id,
                "name": "Campeão da Série A",
                "season_number": current["number"],
            }
            repo.update("clubs", {"_id": champion}, {"$push": {"trophies": trophy}})
            for tier, rows in tables.items():
                for position, row in enumerate(rows, 1):
                    repo.update(
                        "clubs",
                        {"_id": row["club_id"]},
                        {
                            "$set": {"division_tier": destinations[row["club_id"]]},
                            "$push": {
                                "competition_positions": {
                                    "season_id": season_id,
                                    "tier": tier,
                                    "position": position,
                                    "points": row["points"],
                                }
                            },
                        },
                    )
            PlayerAgingService().process(repo, season_id, config)
            repo.update(
                "seasons",
                {"_id": season_id},
                {
                    "$set": {
                        "status": "completed",
                        "champion_club_id": champion,
                        "completed_at": now,
                    }
                },
            )
            upcoming = service.create_season(repo, current["ends_at"], current["number"] + 1)
            next_config = service.season_config(upcoming)
            clubs = {
                club["_id"]: club
                for club in repo.many("clubs", {"_id": {"$in": list(destinations)}}, limit=None)
            }
            for division in divisions:
                slots = [
                    service.add_slot(repo, upcoming, division, clubs[club_id])
                    for club_id, tier in destinations.items()
                    if tier == division["tier"]
                ]
                service.schedule(repo, upcoming, division, slots)
                for slot in slots:
                    service.generate_youth(repo, clubs[slot["club_id"]], upcoming, next_config)
            return public(upcoming)

        return self.repo.transaction(operation)
