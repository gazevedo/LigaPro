"""Immutable season/career projections and atomic universe record maxima."""

from bson import ObjectId

from app.models.game import public, utcnow
from app.services.news import NewsService


class HistoryService:
    @staticmethod
    def save(repo, collection, identity, values):
        repo.database[collection].update_one(
            {"_id": identity}, {"$setOnInsert": values}, upsert=True, session=repo.session
        )

    @staticmethod
    def record(repo, kind, value, reference, club_id=None, player_id=None, now=None):
        if value <= 0:
            return
        doc = repo.database.game_records.find_one_and_update(
            {"_id": kind},
            [
                {
                    "$set": {
                        "value": {"$max": [{"$ifNull": ["$value", -1]}, value]},
                        "holder": {
                            "$cond": [
                                {"$gt": [value, {"$ifNull": ["$value", -1]}]},
                                {
                                    "$literal": {
                                        "reference_id": reference,
                                        "club_id": club_id,
                                        "player_id": player_id,
                                        "created_at": now or utcnow(),
                                    }
                                },
                                "$holder",
                            ]
                        },
                    }
                }
            ],
            upsert=True,
            session=repo.session,
        )
        if doc is None or value > doc.get("value", -1):
            label = {
                "biggest_win": "goleada",
                "longest_win_streak": "vitórias consecutivas",
                "largest_attendance": "público",
                "largest_transfer": "transferência",
                "most_goals_player": "gols na carreira",
                "highest_market_value": "valor de mercado",
            }.get(kind, "do universo")
            NewsService.publish(
                repo,
                "record",
                f"Novo recorde de {label}: "
                + (
                    f"R$ {value / 100:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")
                    if kind in {"largest_transfer", "highest_market_value"}
                    else str(value)
                ),
                club_id,
                reference,
                player_id=player_id,
                now=now,
            )

    @classmethod
    def transfer(cls, repo, player, offer, kind, now):
        cls.save(
            repo,
            "player_career_history",
            f"transfer:{offer['_id']}",
            {
                "player_id": player["_id"],
                "player_name": player["name"],
                "type": "transfer",
                "from_club_id": offer["seller_club_id"],
                "club_id": offer["buyer_club_id"],
                "amount": offer["amount"],
                "transfer_type": kind,
                "created_at": now,
            },
        )
        if kind == "sale":
            cls.record(
                repo,
                "largest_transfer",
                offer["amount"],
                offer["_id"],
                offer["buyer_club_id"],
                player["_id"],
                now,
            )

    @classmethod
    def season(cls, repo, season, tables, destinations):
        leaders = list(
            repo.database.player_season_stats.aggregate(
                [
                    {"$match": {"season_id": season["_id"]}},
                    {"$group": {"_id": "$player_id", "goals": {"$sum": "$goals"}}},
                    {"$sort": {"goals": -1, "_id": 1}},
                    {"$limit": 1},
                ],
                session=repo.session,
            )
        )
        top = leaders[0] if leaders else None
        histories = []
        cups = repo.many(
            "competitions", {"season_id": season["_id"], "status": "completed"}, limit=None
        )
        for tier, table in tables.items():
            promoted = [r["club_id"] for r in table if destinations[r["club_id"]] < tier]
            relegated = [r["club_id"] for r in table if destinations[r["club_id"]] > tier]
            champion = table[0]["club_id"]
            champion_name = (repo.find("clubs", {"_id": champion}) or {}).get("name", "Clube")
            histories.append(
                {
                    "tier": tier,
                    "champion_club_id": champion,
                    "champion_name": champion_name,
                    "final_table": table,
                    "promoted": promoted,
                    "relegated": relegated,
                }
            )
            NewsService.publish(
                repo,
                "title",
                "Campeão da divisão",
                champion,
                season["_id"],
                competition_id=season["_id"],
                now=season["ends_at"],
            )
            for position, row in enumerate(table, 1):
                club_id = row["club_id"]
                finance = repo.find("club_finances", {"_id": club_id}) or {}
                transfers = repo.many(
                    "transfer_offers",
                    {
                        "status": "accepted",
                        "$or": [{"buyer_club_id": club_id}, {"seller_club_id": club_id}],
                    },
                    sort=[("amount", -1)],
                    limit=100,
                )
                cls.save(
                    repo,
                    "club_history",
                    f"{season['_id']}:{club_id}",
                    {
                        "club_id": club_id,
                        "season_id": season["_id"],
                        "season_number": season["number"],
                        "division_tier": tier,
                        "position": position,
                        "title": position == 1,
                        "cash": finance.get("balance", 0),
                        "largest_purchases": [
                            t for t in transfers if t["buyer_club_id"] == club_id
                        ][:5],
                        "largest_sales": [t for t in transfers if t["seller_club_id"] == club_id][
                            :5
                        ],
                        "created_at": season["ends_at"],
                    },
                )
                for kind, members in [("promotion", promoted), ("relegation", relegated)]:
                    if club_id in members:
                        NewsService.publish(
                            repo,
                            kind,
                            "Acesso confirmado"
                            if kind == "promotion"
                            else "Rebaixamento confirmado",
                            club_id,
                            season["_id"],
                            now=season["ends_at"],
                        )
        cls.save(
            repo,
            "season_history",
            season["_id"],
            {
                "season_number": season["number"],
                "champion_club_id": tables[0][0]["club_id"],
                "champion_name": (repo.find("clubs", {"_id": tables[0][0]["club_id"]}) or {}).get(
                    "name", "Clube"
                ),
                "divisions": histories,
                "top_scorer": top,
                "created_at": season["ends_at"],
            },
        )
        if top:
            player = repo.find("players", {"_id": top["_id"]}) or {}
            NewsService.publish(
                repo,
                "top_scorer",
                f"Artilheiro: {player.get('name', 'Jogador')} · {top['goals']} gols",
                player.get("current_club_id"),
                season["_id"],
                player_id=top["_id"],
                now=season["ends_at"],
            )
        for row in repo.many("player_season_stats", {"season_id": season["_id"]}, limit=None):
            player = repo.find("players", {"_id": row["player_id"]}) or {}
            titles = [h["tier"] for h in histories if h["champion_club_id"] == row["club_id"]]
            cls.save(
                repo,
                "player_career_history",
                f"{season['_id']}:{row['player_id']}:{row['club_id']}",
                {
                    **{k: v for k, v in row.items() if k != "_id"},
                    "type": "season",
                    "player_name": player.get("name", "Jogador"),
                    "titles": titles,
                    "stars": player.get("stars", 0),
                    "cup_titles": [
                        c["_id"] for c in cups if c.get("champion_club_id") == row["club_id"]
                    ],
                    "created_at": season["ends_at"],
                },
            )

    @staticmethod
    def get(repo, club_id):
        player_ids = [
            p["_id"]
            for p in repo.many(
                "players",
                {"$or": [{"current_club_id": club_id}, {"owner_club_id": club_id}]},
                projection={"name": 1},
                limit=None,
            )
        ]
        return public(
            {
                "seasons": repo.many("season_history", {}, sort=[("season_number", -1)], limit=30),
                "clubs": repo.many(
                    "club_history", {"club_id": club_id}, sort=[("season_number", -1)], limit=30
                ),
                "records": repo.many("game_records", {}),
                "players": repo.many(
                    "player_career_history",
                    {"$or": [{"club_id": club_id}, {"player_id": {"$in": player_ids}}]},
                    sort=[("created_at", -1)],
                    limit=100,
                ),
            }
        )


class MatchReportService:
    @staticmethod
    def persist(repo, match, result):
        from pymongo import UpdateOne

        from app.services.player_statistics import match_player_summaries

        events = result.get("events", [])
        if events:
            repo.database.match_events.bulk_write(
                [
                    UpdateOne(
                        {"match_id": match["_id"], "sequence": i},
                        {
                            "$setOnInsert": {
                                "_id": f"{match['_id']}:{i}",
                                **event,
                                "match_id": match["_id"],
                                "sequence": i,
                                "second": event.get("second", 0),
                                "club_id": event.get("team_id"),
                                "created_at": match["date"],
                            }
                        },
                        upsert=True,
                    )
                    for i, event in enumerate(events)
                ],
                session=repo.session,
            )
        summaries = match_player_summaries(result)
        ids = [ObjectId(r["player_id"]) for r in summaries]
        players = {
            str(p["_id"]): p for p in repo.many("players", {"_id": {"$in": ids}}, limit=None)
        }
        original = {
            p["id"]: p
            for side in ["home", "away"]
            for p in result.get("snapshot", {}).get(side, {}).get("lineup", [])
            + result.get("snapshot", {}).get(side, {}).get("reserves", [])
        }
        effects = []
        for row in summaries:
            p = players.get(row["player_id"], {})
            before = original.get(row["player_id"], {})
            effects.append(
                {
                    "player_id": row["player_id"],
                    "name": p.get("name", "Jogador"),
                    "energy_before": before.get("energy", 100),
                    "energy": p.get("energy", 100),
                    "morale_before": before.get("morale", 50),
                    "morale": p.get("morale", 50),
                    "physical_condition": p.get("physical_condition", 100),
                    "injury_type": p.get("injury_type"),
                    "suspended_until": p.get("suspended_until"),
                    "strength": p.get("strength"),
                }
            )
        ticket = repo.find("ticket_history", {"match_id": match["_id"]}) or {}
        HistoryService.save(
            repo,
            "match_stats",
            match["_id"],
            {
                "match_id": match["_id"],
                "statistics": result.get("statistics", {}),
                "financial": {key: ticket.get(key, 0) for key in ["attendance", "price", "income"]},
                "consequences": effects,
                "created_at": match["date"],
            },
        )
        score = list(result.get("score", {}).values())
        if len(score) == 2:
            HistoryService.record(
                repo, "biggest_win", abs(score[0] - score[1]), match["_id"], now=match["date"]
            )
        HistoryService.record(
            repo,
            "largest_attendance",
            ticket.get("attendance", 0),
            match["_id"],
            match["home_club_id"],
            now=match["date"],
        )
        for club_id in [match["home_club_id"], match["away_club_id"]]:
            club = repo.find("clubs", {"_id": club_id}) or {}
            HistoryService.record(
                repo,
                "longest_win_streak",
                max(0, club.get("result_streak", 0)),
                match["_id"],
                club_id,
                now=match["date"],
            )
        leaders = repo.many("player_career_stats", {}, sort=[("goals", -1)], limit=1)
        if leaders:
            leader = leaders[0]
            HistoryService.record(
                repo,
                "most_goals_player",
                leader.get("goals", 0),
                match["_id"],
                player_id=leader["_id"],
                now=match["date"],
            )
