"""Bounded supporter growth and ticket demand."""

from bson import ObjectId

from app.config.stadium import effects, sectors
from app.models.game import utcnow


class FanBaseService:
    ATTENDANCE_SHARE = 0.10

    @staticmethod
    def confidence(club):
        # Keep the persisted supporter score and historical records compatible.
        return max(0, min(100, club.get("fan_satisfaction", 50)))

    @staticmethod
    def initialize(repo, club_id):
        repo.update(
            "clubs",
            {"_id": club_id, "supporters": {"$exists": False}},
            {
                "$set": {
                    "supporters": 1000,
                    "fan_satisfaction": 50,
                    "reputation": 10,
                    "ranking_points": 0,
                    "ranking_position": 0,
                }
            },
        )

    @staticmethod
    def attendance(club, stadium, importance=1.0, price=None, opponent=None, position=None):
        ticket = stadium["ticket_price"] if price is None else price
        price_factor = min(1.5, 2000 / max(500, ticket))
        satisfaction = 0.4 + 0.8 * FanBaseService.confidence(club) / 100
        prestige = 1 + club.get("reputation", 10) / 200
        return max(
            0,
            min(
                stadium["capacity"],
                round(
                    club.get("supporters", 1000)
                    * FanBaseService.ATTENDANCE_SHARE
                    * satisfaction
                    * price_factor
                    * prestige
                    * importance
                    * (1 + effects(stadium)["attendance_bonus"])
                    * max(0.85, 1 - min(4, club.get("division_tier", 0)) * 0.03)
                    * (1 + max(0, 10 - (position or 10)) * 0.01)
                    * (1 + min(0.12, (opponent or {}).get("reputation", 0) / 800))
                ),
            ),
        )

    @classmethod
    def sector_ticketing(cls, club, stadium, importance=1.0, opponent=None, position=None):
        rows = []
        for sector in sectors(stadium):
            desired = (
                cls.attendance(
                    club,
                    stadium,
                    importance,
                    price=sector["price"],
                    opponent=opponent,
                    position=position,
                )
                * sector["capacity"]
                / max(1, stadium["capacity"])
            )
            rows.append(
                {
                    **sector,
                    "attendance": min(sector["capacity"], int(desired)),
                    "remainder": desired - int(desired),
                }
            )
        target = round(sum(row["attendance"] + row["remainder"] for row in rows))
        extra = target - sum(row["attendance"] for row in rows)
        for row in sorted(rows, key=lambda row: -row["remainder"]):
            if extra and row["attendance"] < row["capacity"]:
                row["attendance"] += 1
                extra -= 1
        for row in rows:
            row["income"] = row["attendance"] * row["price"]
            row.pop("remainder")
        return rows

    @classmethod
    def change(cls, repo, club_id, reason, reference, *, satisfaction=0, growth=0, now=None):
        cls.initialize(repo, club_id)
        club = repo.find("clubs", {"_id": club_id})
        values = {
            "supporters": max(100, round(club["supporters"] * (1 + growth))),
            "fan_satisfaction": max(0, min(100, club["fan_satisfaction"] + satisfaction)),
        }
        repo.update("clubs", {"_id": club_id}, {"$set": values})
        repo.insert(
            "club_fan_history",
            {
                "_id": ObjectId(),
                "club_id": club_id,
                "reason": reason,
                "reference_id": reference,
                "created_at": now or utcnow(),
                **values,
            },
        )

    @classmethod
    def after_match(cls, repo, match, home_goals, away_goals, importance=1.0):
        for club_id, goals, against in (
            (match["home_club_id"], home_goals, away_goals),
            (match["away_club_id"], away_goals, home_goals),
        ):
            club = repo.find("clubs", {"_id": club_id})
            stadium = repo.find("stadiums", {"_id": club_id}) or {"ticket_price": 2000}
            expected = club.get("reputation", 10) > 50
            delta = 3 if goals > against else -3 if goals < against else (-1 if expected else 0)
            delta -= min(3, max(0, stadium["ticket_price"] // 2000 - 1))
            streak = club.get("result_streak", 0)
            growth = (
                0.003 * (1 + club.get("reputation", 10) / 100)
                if goals > against
                else -0.003
                if streak <= -5
                else 0
            )
            cls.change(
                repo,
                club_id,
                "match",
                match["_id"],
                satisfaction=delta,
                growth=growth,
                now=match["date"],
            )
        stadium = repo.find("stadiums", {"_id": match["home_club_id"]})
        if stadium:
            club = repo.find("clubs", {"_id": match["home_club_id"]})
            rival = repo.find("clubs", {"_id": match["away_club_id"]})
            standing = (
                repo.find(
                    "standings", {"club_id": club["_id"], "season_id": match.get("season_id")}
                )
                or {}
            )
            rows = cls.sector_ticketing(
                club, stadium, importance, opponent=rival, position=standing.get("position")
            )
            attendance = sum(row["attendance"] for row in rows)
            income = sum(row["income"] for row in rows)
            repo.money(club["_id"], income, "ticketing", match["_id"], effective_at=match["date"])
            services_income = attendance * effects(stadium)["services_income_per_attendee"]
            if services_income:
                repo.money(
                    club["_id"],
                    services_income,
                    "other_income",
                    match["_id"],
                    effective_at=match["date"],
                )
            repo.insert(
                "ticket_history",
                {
                    "_id": ObjectId(),
                    "club_id": club["_id"],
                    "match_id": match["_id"],
                    "attendance": attendance,
                    "price": stadium["ticket_price"],
                    "income": income,
                    "services_income": services_income,
                    "sectors": rows,
                    "created_at": match["date"],
                },
            )
