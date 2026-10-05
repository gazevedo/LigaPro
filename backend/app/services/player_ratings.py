from bson import ObjectId


class PlayerRatingService:
    @staticmethod
    def calculate(row, result):
        score = result["score"]
        goals = score[row["club_id"]]
        against = next(value for key, value in score.items() if key != row["club_id"])
        rating = (
            6.0
            + 0.8 * row["goals"]
            + 0.12 * row["shots"]
            + 0.025 * row["offensive_actions"]
            + 0.06 * row["defensive_actions"]
            + 0.20 * row["saves"]
            + 0.4 * row["clean_sheets"]
            + (0.2 if goals > against else 0)
            - 0.25 * row["yellow_cards"]
            - 0.9 * row["red_cards"]
            - 0.7 * row["penalties_missed"]
        )
        if row["position"] in {"GK", "CB", "FB"}:
            rating -= 0.15 * row["goals_conceded"]
        if (
            row["minutes"] >= 60
            and row["offensive_actions"] + row["defensive_actions"] + row["shots"] + row["saves"]
            < 2
        ):
            rating -= 0.3
        return round(max(5.0, min(10.0, rating)), 1)

    @classmethod
    def after_match(cls, repo, match, result, summaries):
        rows = [
            {
                "_id": ObjectId(),
                "match_id": match["_id"],
                "match_date": match["date"],
                "player_id": ObjectId(row["player_id"]),
                "club_id": ObjectId(row["club_id"]),
                "rating": cls.calculate(row, result),
                "minutes": row["minutes"],
                "events_summary": {
                    key: value for key, value in row.items() if key not in {"player_id", "club_id"}
                },
            }
            for row in summaries
        ]
        if rows:
            repo.insert_many("player_match_ratings", rows)
