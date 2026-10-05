"""Recent sporting ranking, and slower historical reputation."""

from bson import ObjectId

from app.models.game import utcnow


class ClubReputationService:
    @staticmethod
    def season(repo, club_id, tier, position, trophy=False):
        club = repo.find("clubs", {"_id": club_id})
        change = (2 if trophy else 0) + (1 if tier == 0 and position <= 10 else 0)
        fans = min(1, club.get("supporters", 1000) // 10000)
        value = min(100, club.get("reputation", 10) + change + fans)
        repo.update("clubs", {"_id": club_id}, {"$set": {"reputation": value}})

    @staticmethod
    def cup_title(repo, club_id):
        club = repo.find("clubs", {"_id": club_id})
        repo.update(
            "clubs",
            {"_id": club_id},
            {"$set": {"reputation": min(100, club.get("reputation", 10) + 2)}},
        )


class ClubRankingService:
    @staticmethod
    def points(club, row, recent):
        tier = row.get("tier", club.get("division_tier", 0))
        return max(
            0,
            round(
                1000 / (tier + 1)
                + (21 - row.get("position", 20)) * 20
                + row.get("points", 0) * 2
                + recent * 15
                + club.get("recent_title_points", 0)
            ),
        )

    @classmethod
    def refresh(cls, repo, season_id, reference=None):
        rows = repo.many("standings", {"season_id": season_id}, limit=None)
        clubs = {
            c["_id"]: c
            for c in repo.many("clubs", {"_id": {"$in": [r["club_id"] for r in rows]}}, limit=None)
        }
        scored = []
        for row in rows:
            club = clubs.get(row["club_id"])
            if not club:
                continue
            recent = club.get("recent_results", [])
            weighted = sum(
                points * (i + 1) / max(1, len(recent)) for i, points in enumerate(recent)
            )
            scored.append((cls.points(club, row, weighted), club["_id"]))
        scored.sort(key=lambda item: (-item[0], str(item[1])))
        for position, (points, club_id) in enumerate(scored, 1):
            club = clubs[club_id]
            repo.update(
                "clubs",
                {"_id": club_id},
                {
                    "$set": {
                        "ranking_points": points,
                        "ranking_position": position,
                        "ranking": points,
                    }
                },
            )
            if reference is not None and (
                club.get("ranking_points") != points or club.get("ranking_position") != position
            ):
                repo.insert(
                    "club_ranking_history",
                    {
                        "_id": ObjectId(),
                        "club_id": club_id,
                        "season_id": season_id,
                        "reference_id": reference,
                        "ranking_points": points,
                        "ranking_position": position,
                        "created_at": utcnow(),
                    },
                )

    @staticmethod
    def result(repo, club_id, points):
        repo.update(
            "clubs",
            {"_id": club_id},
            {"$push": {"recent_results": {"$each": [points], "$slice": -5}}},
        )
