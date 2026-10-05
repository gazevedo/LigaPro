"""Club tactics and planned commands for the offline match scheduler."""

from bson import ObjectId
from fastapi import HTTPException

from app.models.game import public, utcnow
from app.services.match_engine import MatchPlayer, arrange_formation, validate_commands


class TacticsService:
    def __init__(self, repository):
        self.repo = repository

    @staticmethod
    def settings(repo, club_id, lineup):
        stored = repo.find("club_tactics", {"_id": club_id})
        return stored or {
            "_id": club_id,
            "club_id": club_id,
            "formation": lineup["formation"],
            "play_style": lineup.get("style", "balanced"),
            "marking": lineup.get("marking", "light"),
            "attack_focus": lineup.get("attack_focus", "normal"),
        }

    @staticmethod
    def persist(repo, club_id, changes):
        repo.database.club_tactics.update_one(
            {"_id": club_id},
            {"$set": {"club_id": club_id, **changes, "updated_at": utcnow()}},
            upsert=True,
            session=repo.session,
        )

    def get(self, user):
        club = self.repo.owned(user.id)
        lineup = self.repo.find("lineups", {"_id": club["_id"]})
        return public(self.settings(self.repo, club["_id"], lineup))

    def save(self, user, data):
        def operation(repo):
            club = repo.owned(user.id)
            repo.update("clubs", {"_id": club["_id"]}, {"$inc": {"roster_revision": 1}})
            lineup = repo.find("lineups", {"_id": club["_id"]})
            players = repo.many(
                "players",
                {"current_club_id": club["_id"], "status": {"$ne": "retired"}},
                limit=None,
            )
            by_id = {p["_id"]: p for p in players}
            if any(identity not in by_id for identity in lineup["starters"]):
                raise HTTPException(409, "Atualize a escalação antes de salvar a tática.")
            assigned = arrange_formation(
                [MatchPlayer.from_document(by_id[i]) for i in lineup["starters"]], data.formation
            )
            # Role assignments are computed by the engine; keep the actual starters.
            repo.update(
                "lineups",
                {"_id": club["_id"]},
                {
                    "$set": {
                        "formation": data.formation,
                        "starters": [ObjectId(p.id) for p in assigned],
                    }
                },
            )
            self.persist(repo, club["_id"], data.model_dump())
            return public(repo.find("club_tactics", {"_id": club["_id"]}))

        return self.repo.transaction(operation)

    def command(self, user, identity, data):
        def operation(repo):
            club = repo.owned(user.id)
            match = repo.document("matches", identity)
            if club["_id"] not in {match["home_club_id"], match["away_club_id"]}:
                raise HTTPException(403, "Esta partida não pertence ao seu clube.")
            if match["status"] != "scheduled" or match["date"] <= utcnow():
                raise HTTPException(409, "A partida já começou.")
            command = {"team_id": str(club["_id"]), **data.model_dump()}
            try:
                validate_commands([command], {str(club["_id"])})
            except (ValueError, TypeError) as exc:
                raise HTTPException(422, str(exc)) from exc
            queued = [c for c in match.get("commands", []) if c["team_id"] == str(club["_id"])]
            if len(queued) >= 30:
                raise HTTPException(422, "Limite de 30 comandos por clube.")
            if data.type == "substitution":
                if sum(c["type"] == "substitution" for c in queued) >= 5:
                    raise HTTPException(422, "Máximo de cinco substituições.")
                lineup = repo.find("lineups", {"_id": club["_id"]})
                starters, reserves = (
                    {str(i) for i in lineup["starters"]},
                    {str(i) for i in lineup["reserves"]},
                )
                for previous in sorted(queued + [command], key=lambda c: c["minute"]):
                    if previous["type"] != "substitution":
                        continue
                    out_id, in_id = (
                        previous["payload"]["out_player_id"],
                        previous["payload"]["in_player_id"],
                    )
                    if out_id not in starters or in_id not in reserves:
                        raise HTTPException(422, "Jogadores indisponíveis para esta substituição.")
                    starters.remove(out_id)
                    starters.add(in_id)
                    reserves.remove(in_id)
            updated = repo.update(
                "matches",
                {"_id": match["_id"], "status": "scheduled"},
                {"$push": {"commands": command}},
            )
            if not updated:
                raise HTTPException(409, "A partida já começou.")
            return public(updated["commands"])

        return self.repo.transaction(operation)
