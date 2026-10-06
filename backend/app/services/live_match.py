"""One server-owned progressive session per match; connection affects only cadence.

A single FastAPI process owns these rooms. Restart recovery replays the saved initial
context + ordered accepted commands to the last committed checkpoint using the same
seed; it never broadcasts or settles that replay. No result is calculated on join.
"""

import asyncio
from copy import deepcopy
from dataclasses import asdict
from time import monotonic

from bson import ObjectId
from fastapi import HTTPException
from pymongo import UpdateOne

from app.models.game import public, utcnow
from app.services.match_engine import (
    MatchConfig,
    MatchEngine,
    MatchPlayer,
    MatchTeam,
    validate_commands,
)

MIN_CONNECTED_USERS_TO_RUN = 0
MATCH_MUST_NEVER_WAIT_FOR_PLAYER_CONNECTION = True
LIVE_MATCH_REAL_SECONDS_PER_GAME_MINUTE = 1.0
MAX_TACTICAL_PAUSES_PER_USER = 3
TACTICAL_PAUSE_SECONDS = 15
RELEVANT = {
    "attack",
    "chance",
    "goal",
    "shot_saved",
    "shot_off_target",
    "foul",
    "yellow_card",
    "red_card",
    "second_yellow",
    "penalty_awarded",
    "injury",
    "substitution",
    "formation_change",
    "play_style_change",
    "marking_change",
    "attack_focus_change",
    "kickoff",
    "halftime",
    "fulltime",
}
MATCH_COLLECTIONS = ("matches", "competition_matches", "friendly_matches")


def busy_clubs(repo):
    return {
        club_id
        for collection in MATCH_COLLECTIONS
        for live in repo.many(
            collection,
            {"status": "live"},
            projection={"home_club_id": 1, "away_club_id": 1},
            limit=None,
        )
        for club_id in [live["home_club_id"], live["away_club_id"]]
    }


IMPORTANT = RELEVANT - {"attack", "chance", "shot_saved", "shot_off_target", "foul"}


class MatchNarrationService:
    @staticmethod
    def narrate(event, names):
        actor = names.get(event.get("player_id"), "A equipe")
        text = {
            "kickoff": "Começa a partida",
            "attack": f"{actor} avança",
            "chance": "Grande chance de gol",
            "goal": f"GOL! {actor} finaliza",
            "shot_saved": "Defesa do goleiro",
            "shot_off_target": "Finalização para fora",
            "foul": "Falta marcada",
            "yellow_card": f"Amarelo para {actor}",
            "red_card": f"Vermelho para {actor}",
            "second_yellow": "Segundo amarelo",
            "penalty_awarded": "Pênalti marcado",
            "injury": f"{actor} sentiu uma lesão",
            "substitution": (
                f"{names.get(event.get('in_player_id'), 'Reserva')} entra no lugar de "
                f"{names.get(event.get('out_player_id'), 'Titular')}"
            ),
            "halftime": "Intervalo",
            "fulltime": "Fim de jogo",
        }.get(event["type"], "A equipe ajustou sua tática")
        if event.get("penalty"):
            text = (
                "Gol de pênalti"
                if event["type"] == "goal"
                else "Pênalti defendido"
                if event["type"] == "shot_saved"
                else "Pênalti para fora"
            )
        return f"{event['minute']}′ {text}."


def team_from_snapshot(doc):
    values = deepcopy(doc)
    values["lineup"] = [
        MatchPlayer(**{**p, "traits": tuple(p.get("traits", ()))}) for p in values["lineup"]
    ]
    values["reserves"] = [
        MatchPlayer(**{**p, "traits": tuple(p.get("traits", ()))})
        for p in values.get("reserves", [])
    ]
    return MatchTeam(**values)


class LiveMatchSession:
    def __init__(self, home, away, seed, commands=None, knockout=False, config=None):
        self.initial = {"home": asdict(home), "away": asdict(away), "seed": seed}
        self.home_club_id, self.away_club_id = home.id, away.id
        self.started_at = utcnow()
        self.finished_at = None
        self.last_snapshot_at = None
        self.engine = MatchEngine(
            MatchConfig(**{k: tuple(v) if isinstance(v, list) else v for k, v in config.items()})
            if config
            else None
        )
        self.knockout = knockout
        self.iterator = self.engine.progressive(
            home,
            away,
            seed,
            commands=commands or [],
            minutes=120 if knockout else 90,
            knockout=knockout,
        )
        self.frame = next(self.iterator)
        self.result = None
        self.speed = 1
        self.paused = False
        self.status = "first_half"
        self.version = 0
        self.queue = []
        self.pause_deadline = 0.0
        self.pause_counts = {}
        self.skip_target = 0

    def advance(self):
        if self.result is not None or self.paused:
            return self.frame
        queued, self.queue = self.queue, []
        try:
            self.frame = self.iterator.send(queued)
        except StopIteration as finished:
            self.result = finished.value
            final = self.result.pop("_live_final", {})
            self.frame = {
                "minute": self.result.get("duration", 90),
                "score": self.result["score"],
                "statistics": self.result["statistics"],
                "events": self.result["events"],
                "lineups": self.result.get("final_lineups", []),
                **final,
            }
            self.status = "finished"
            self.finished_at = utcnow()
        else:
            self.status = (
                "halftime"
                if self.frame["minute"] == 45
                else "extra_time"
                if self.frame["minute"] >= 90
                else "second_half"
                if self.frame["minute"] > 45
                else "first_half"
            )
        self.version += 1
        return self.frame

    def simulate_to_end(self):
        self.paused = False
        while self.result is None:
            self.advance()
        return self.result


class MatchRoom:
    def __init__(self, manager, match, collection="matches"):
        self.collection = collection
        self.manager = manager
        self.repo = manager.repo
        self.match = match
        self.identity = str(match["_id"])
        self.connections = {}  # websocket -> (user, club_id)
        self.lock = asyncio.Lock()
        self.session = None
        self.command_queue = []
        self.command_rows = []
        self.last_due = monotonic()
        self.last_saved = -1
        self.last_events = 0
        self.last_messages = 0
        self.sequence = 0
        self.task = None
        self.names = {}
        self.club_names = {}
        self.home_user_id = None
        self.away_user_id = None
        self.settled = False

    @property
    def connected_users(self):
        return {user.id for user, _ in self.connections.values()}

    def authorize(self, user):
        club = self.repo.owned(user.id)
        if club["_id"] not in {self.match["home_club_id"], self.match["away_club_id"]}:
            raise HTTPException(403, "Somente os dois técnicos desta partida podem participar.")
        return club

    async def load_metadata(self):
        clubs = await asyncio.to_thread(
            self.repo.many,
            "clubs",
            {"_id": {"$in": [self.match["home_club_id"], self.match["away_club_id"]]}},
        )
        self.club_names = {str(c["_id"]): c["name"] for c in clubs}
        self.home_user_id = next(
            (
                str(c["owner_user_id"])
                for c in clubs
                if c["_id"] == self.match["home_club_id"] and c.get("owner_user_id")
            ),
            None,
        )
        self.away_user_id = next(
            (
                str(c["owner_user_id"])
                for c in clubs
                if c["_id"] == self.match["away_club_id"] and c.get("owner_user_id")
            ),
            None,
        )
        players = await asyncio.to_thread(
            self.repo.many,
            "players",
            {"current_club_id": {"$in": [self.match["home_club_id"], self.match["away_club_id"]]}},
            limit=None,
            projection={"name": 1},
        )
        self.names = {str(p["_id"]): p["name"] for p in players}

    async def start(self):
        if self.session or self.match["status"] == "completed" or self.match["date"] > utcnow():
            return
        from app.services.bot_manager import BotManagerService
        from app.services.competition import CompetitionService
        from app.services.game import MarketService
        from app.services.monthly_finance import MonthlyFinanceService
        from app.services.physical_condition import PhysicalConditionService
        from app.services.player_contracts import ContractService

        def prepare():
            if self.match["status"] == "live":
                return self.repo.find("match_contexts", {"_id": self.match["_id"]})
            MarketService.return_loans(self.repo, self.match["date"])
            MonthlyFinanceService.process_due(self.repo, self.match["date"])
            ContractService(self.repo).process_due(self.match["date"])
            BotManagerService(self.repo).process_due(self.match["date"])

            def operation(tx):
                CompetitionService.lock(tx)
                current = tx.find(
                    self.collection, {"_id": self.match["_id"], "status": "scheduled"}
                )
                if not current:
                    return None
                if {current["home_club_id"], current["away_club_id"]} & busy_clubs(tx):
                    return None
                for club_id in sorted([current["home_club_id"], current["away_club_id"]]):
                    tx.update("clubs", {"_id": club_id}, {"$inc": {"roster_revision": 1}})
                    PhysicalConditionService().prepare(tx, club_id, current["date"])
                    club = tx.find("clubs", {"_id": club_id})
                    if club.get("is_bot"):
                        BotManagerService.prepare(tx, club_id, current["date"])
                    else:
                        try:
                            MarketService.repair_lineup(tx, club_id)
                        except HTTPException as exc:
                            if exc.status_code != 409:
                                raise
                teams = [
                    CompetitionService.match_team(tx, current[f"{side}_club_id"])
                    for side in ["home", "away"]
                ]
                if not all(teams):
                    return {"walkover": True}
                context = {
                    "_id": current["_id"],
                    "home": asdict(teams[0]),
                    "away": asdict(teams[1]),
                    "seed": current["seed"],
                    "config": asdict(MatchConfig()),
                    "commands": current.get("commands", []),
                    "started_at": utcnow(),
                }
                tx.insert("match_contexts", context)
                tx.update(self.collection, {"_id": current["_id"]}, {"$set": {"status": "live"}})
                return context

            return self.repo.transaction(operation)

        context = await asyncio.to_thread(prepare)
        if context and context.get("walkover"):
            from app.services.cup import CupService
            from app.services.season_calendar import FriendlyService

            service = {
                "matches": CompetitionService,
                "competition_matches": CupService,
                "friendly_matches": FriendlyService,
            }[self.collection]
            await asyncio.to_thread(service(self.repo).play, self.match["_id"], utcnow())
            context = None
        if not context:
            self.match = self.repo.find(self.collection, {"_id": self.match["_id"]})
            if self.match and self.match["status"] == "completed":
                await self.load_metadata()
            return
        self.session = LiveMatchSession(
            team_from_snapshot(context["home"]),
            team_from_snapshot(context["away"]),
            context["seed"],
            context.get("commands", []),
            knockout=self.collection == "competition_matches",
            config=context.get("config"),
        )
        await self.load_metadata()
        snapshots = await asyncio.to_thread(
            self.repo.many,
            "match_live_snapshots",
            {"match_id": self.match["_id"]},
            sort=[("minute", -1)],
            limit=1,
        )
        self.command_rows = await asyncio.to_thread(
            self.repo.many,
            "match_commands",
            {"match_id": self.match["_id"]},
            sort=[("sequence_number", 1)],
            limit=None,
        )
        self.sequence = max([r["sequence_number"] for r in self.command_rows], default=0)
        restore_minute = snapshots[0]["minute"] if snapshots else 0
        accepted = [r for r in self.command_rows if r["status"] != "cancelled"]
        # Exact replay to checkpoint, with no economic effects or broadcasts.
        while self.session.frame["minute"] < restore_minute:
            minute = self.session.frame["minute"]
            self.session.queue.extend(
                r["engine_command"] for r in accepted if r["minute"] == minute
            )
            self.session.advance()
        self.session.queue.extend(
            r["engine_command"]
            for r in accepted
            if r["minute"] >= restore_minute and r["status"] == "pending"
        )
        if snapshots:
            self.session.version = max(self.session.version, snapshots[0].get("version", 0))
        self.last_events = len(self.session.frame["events"])
        self.last_messages = self.last_events
        self.last_saved = restore_minute if snapshots else -1
        self.match["status"] = "live"
        self.last_due = monotonic()
        await self.checkpoint(force=True)

    def events(self, club_id=None):
        raw = (
            self.session.frame["events"]
            if self.session
            else self.match.get("result", {}).get("events", [])
        )
        events = [
            {**e, "sequence": i, "narration": MatchNarrationService.narrate(e, self.names)}
            for i, e in enumerate(raw)
            if e["type"] in RELEVANT
        ]
        for e in events:
            if e.get("team_id") != club_id and e["type"].endswith("_change"):
                for key in ["value", "previous", "command", "payload"]:
                    e.pop(key, None)
        return events

    def state(self, club_id):
        session = self.session
        result = self.match.get("result", {})
        frame = (
            session.frame
            if session
            else {
                "minute": result.get("duration", 90) if self.match["status"] == "completed" else 0,
                "score": result.get("score", {}),
                "events": result.get("events", []),
                "statistics": result.get("statistics", {}),
                "lineups": result.get("final_lineups", []),
                "discipline": [],
                "substitutions": [],
            }
        )
        minute = frame["minute"]
        status = (
            session.status
            if session
            else "finished"
            if self.match["status"] == "completed"
            else "not_started"
        )
        own = next((deepcopy(t) for t in frame["lineups"] if t["id"] == club_id), None)
        if own:
            index = 0 if club_id == str(self.match["home_club_id"]) else 1
            discipline = (
                frame["discipline"][index]
                if len(frame["discipline"]) > index
                else {"yellow_cards": {}, "dismissed": [], "injured": []}
            )
            own["substitutions_used"] = (
                frame["substitutions"][index] if len(frame["substitutions"]) > index else 0
            )
            for p in own["lineup"] + own.get("reserves", []):
                p.update(
                    name=self.names.get(p["id"], "Jogador"),
                    yellow_cards=discipline["yellow_cards"].get(p["id"], 0),
                    dismissed=p["id"] in discipline["dismissed"],
                    injured=p["id"] in discipline["injured"],
                )
        recent = [e for e in frame["events"] if e["minute"] >= max(0, minute - 10)]
        pressure = {
            str(cid): sum(
                e["type"] in {"attack", "chance", "goal", "shot_saved", "shot_off_target"}
                and e.get("team_id") == str(cid)
                for e in recent
            )
            for cid in [self.match["home_club_id"], self.match["away_club_id"]]
        }
        state = {
            "match_id": self.identity,
            "status": status,
            "current_minute": minute,
            "current_second": 0,
            "current_period": 1 if minute < 45 else 2,
            "simulation_speed": session.speed if session else 1,
            "paused": session.paused if session else False,
            "updated_at": utcnow(),
            "version": session.version if session else 0,
            "home_club_id": str(self.match["home_club_id"]),
            "away_club_id": str(self.match["away_club_id"]),
            "home_name": self.club_names.get(str(self.match["home_club_id"]), "Mandante"),
            "away_name": self.club_names.get(str(self.match["away_club_id"]), "Visitante"),
            "own_team": own,
            "events": self.events(club_id)[-40:],
            "match_momentum": pressure,
            "connected_users": len(self.connected_users),
            "human_vs_human": bool(self.home_user_id and self.away_user_id),
        }
        for side in ["home", "away"]:
            identity = str(self.match[f"{side}_club_id"])
            stats = frame["statistics"].get(identity, {})
            state[f"{side}_score"] = frame["score"].get(identity, 0)
            for metric in [
                "possession",
                "attacks",
                "chances",
                "shots",
                "shots_on_target",
                "fouls",
                "yellow_cards",
                "red_cards",
            ]:
                state[f"{side}_{metric}"] = round(
                    stats.get(metric, 0.5 if metric == "possession" else 0)
                    * (100 if metric == "possession" else 1),
                    2,
                )
        if minute == 0:
            state["home_possession"] = state["away_possession"] = 50
        else:
            state["away_possession"] = round(100 - state["home_possession"], 2)
        return public(state)

    async def checkpoint(self, force=False):
        if not self.session:
            return
        frame = self.session.frame
        changed = frame["events"][self.last_events :]
        if not force and frame["minute"] % 15 and not any(e["type"] in IMPORTANT for e in changed):
            return
        data = public(frame)
        data.pop("events", None)
        statuses = []
        for row in self.command_rows:
            if row["status"] == "pending" and row["minute"] < frame["minute"]:
                rejected = any(
                    e["type"] == "command_rejected" and e.get("command") == row["engine_command"]
                    for e in frame["events"]
                )
                statuses.append((row, "rejected" if rejected else "applied"))

        def save():
            def operation(tx):
                # Version/checkpoint and events are committed together.
                tx.update(
                    self.collection,
                    {"_id": self.match["_id"], "status": "live"},
                    {
                        "$set": {
                            "live_minute": frame["minute"],
                            "live_version": self.session.version,
                        }
                    },
                )
                tx.database.match_live_snapshots.update_one(
                    {"_id": f"{self.identity}:{frame['minute']}"},
                    {
                        "$set": {
                            "match_id": self.match["_id"],
                            **data,
                            "version": self.session.version,
                            "created_at": utcnow(),
                        }
                    },
                    upsert=True,
                    session=tx.session,
                )
                if changed:
                    tx.database.match_events.bulk_write(
                        [
                            UpdateOne(
                                {"match_id": self.match["_id"], "sequence": i},
                                {
                                    "$setOnInsert": {
                                        "_id": f"{self.identity}:{i}",
                                        "match_id": self.match["_id"],
                                        "sequence": i,
                                        **e,
                                        "second": e.get("second", 0),
                                        "club_id": e.get("team_id"),
                                        "secondary_player_id": e.get(
                                            "in_player_id", e.get("goalkeeper_id")
                                        ),
                                        "metadata": {
                                            k: v
                                            for k, v in e.items()
                                            if k not in {"minute", "type", "team_id", "player_id"}
                                        },
                                        "created_at": self.match["date"],
                                    }
                                },
                                upsert=True,
                            )
                            for i, e in enumerate(changed, start=self.last_events)
                        ],
                        session=tx.session,
                    )
                for row, status in statuses:
                    tx.update(
                        "match_commands",
                        {"_id": row["_id"]},
                        {"$set": {"status": status, "applied_at_minute": row["minute"]}},
                    )

            self.repo.transaction(operation)

        await asyncio.to_thread(save)
        for row, status in statuses:
            row["status"] = status
        self.last_saved = frame["minute"]
        self.session.last_snapshot_at = utcnow()
        self.last_events = len(frame["events"])

    async def broadcast(self, kind="match_state"):
        for socket, (_, club_id) in list(self.connections.items()):
            try:
                await socket.send_json({"type": kind, "data": self.state(club_id)})
            except Exception:
                self.connections.pop(socket, None)

    async def command(self, user, message):
        async with self.lock:
            club = await asyncio.to_thread(self.authorize, user)
            cid = str(club["_id"])
            if message.get("club_id", cid) != cid:
                raise HTTPException(403, "Você controla somente o próprio clube.")
            await self.start()
            if not self.session or self.session.result is not None:
                raise HTTPException(409, "Partida não está em andamento.")
            s = self.session
            kind = message.get("type")
            if kind not in {
                "pause",
                "pause_request",
                "tactical_pause",
                "resume",
                "start_second_half",
                "set_speed",
                "skip_to_end",
                "skip_to_halftime",
                "substitution",
                "formation_change",
                "tactics_change",
                "combined_change",
                "play_style_change",
                "marking_change",
                "attack_focus_change",
            }:
                raise HTTPException(422, "Tipo de comando inválido.")
            human_pair = bool(self.home_user_id and self.away_user_id)
            if kind in {"pause", "pause_request", "tactical_pause"}:
                if s.pause_counts.get(user.id, 0) >= MAX_TACTICAL_PAUSES_PER_USER or s.paused:
                    raise HTTPException(409, "Pausa indisponível.")
                s.pause_counts[user.id] = s.pause_counts.get(user.id, 0) + 1
                s.paused = True
                s.pause_deadline = monotonic() + TACTICAL_PAUSE_SECONDS
            elif kind in {"resume", "start_second_half"}:
                s.paused = False
                self.last_due = monotonic()
            elif kind == "set_speed":
                speed = message.get("speed")
                if type(speed) is not int or speed not in {1, 2, 4} or human_pair and speed != 1:
                    raise HTTPException(422, "Velocidade deve ser 1× entre dois clubes humanos.")
                s.speed = speed
            elif kind in {"skip_to_end", "skip_to_halftime"}:
                if human_pair and len(self.connected_users - {user.id}) > 0:
                    raise HTTPException(
                        409, "Não é permitido pular enquanto o outro técnico acompanha."
                    )
                if kind == "skip_to_halftime" and s.frame["minute"] >= 45:
                    raise HTTPException(409, "O intervalo já ocorreu.")
                s.skip_target = 45 if kind == "skip_to_halftime" else 120 if s.knockout else 90
                s.paused = False
            else:
                client_id = message.get("command_id")
                if not isinstance(client_id, str) or not 1 <= len(client_id) <= 80:
                    raise HTTPException(422, "Informe um identificador de comando válido.")
                saved = next(
                    (
                        r
                        for r in self.command_rows
                        if r["user_id"] == user.id and r["client_id"] == client_id
                    ),
                    None,
                )
                if saved:
                    return public(saved)
                if len([r for r in self.command_rows if r["user_id"] == user.id]) >= 30:
                    raise HTTPException(409, "Limite de comandos por partida atingido.")
                payload = message.get("payload", {})
                command = {
                    "team_id": cid,
                    "minute": s.frame["minute"],
                    "type": "substitution" if kind == "substitution" else "tactics_change",
                    "payload": payload,
                }
                try:
                    validate_commands([command], {cid}, 120 if s.knockout else 90)
                except (ValueError, TypeError) as exc:
                    raise HTTPException(422, str(exc)) from exc
                if kind == "substitution":
                    own = self.state(cid)["own_team"]
                    outgoing = next(
                        (p for p in own["lineup"] if p["id"] == payload.get("out_player_id")), None
                    )
                    incoming = next(
                        (p for p in own["reserves"] if p["id"] == payload.get("in_player_id")), None
                    )
                    pending_subs = [
                        r
                        for r in self.command_rows
                        if r["club_id"] == club["_id"]
                        and r["status"] == "pending"
                        and r["engine_command"]["type"] == "substitution"
                    ]
                    if (
                        not outgoing
                        or not incoming
                        or outgoing["dismissed"]
                        and not outgoing["injured"]
                        or incoming["injured"]
                        or own["substitutions_used"] + len(pending_subs) >= 5
                        or any(
                            incoming["id"] == r["engine_command"]["payload"]["in_player_id"]
                            or outgoing["id"] == r["engine_command"]["payload"]["out_player_id"]
                            for r in pending_subs
                        )
                    ):
                        raise HTTPException(409, "Substituição inelegível ou limite atingido.")
                self.sequence += 1
                s.version += 1
                row = {
                    "_id": f"{self.identity}:{user.id}:{client_id}",
                    "match_id": self.match["_id"],
                    "user_id": user.id,
                    "club_id": club["_id"],
                    "client_id": client_id,
                    "minute": s.frame["minute"],
                    "status": "pending",
                    "engine_command": command,
                    "sequence_number": self.sequence,
                    "created_at": utcnow(),
                }
                await asyncio.to_thread(self.repo.insert, "match_commands", row)
                self.command_rows.append(row)
                s.queue.append(command)
                await self.broadcast("sync")
                return public(row)
            s.version += 1
            await self.broadcast("match_state")
            return {"status": "accepted", "version": s.version}

    async def finish(self):
        if self.settled:
            return
        from app.services.competition import CompetitionService
        from app.services.cup import CupService
        from app.services.season_calendar import FriendlyService

        await self.checkpoint(force=True)
        service = {
            "matches": CompetitionService,
            "competition_matches": CupService,
            "friendly_matches": FriendlyService,
        }[self.collection]
        await asyncio.to_thread(
            service(self.repo).play, self.match["_id"], utcnow(), self.session.result
        )
        self.match = await asyncio.to_thread(
            self.repo.find, self.collection, {"_id": self.match["_id"]}
        )
        self.settled = self.match["status"] == "completed"
        await self.broadcast("match_finished")

    async def run(self):
        while not self.manager.closed:
            try:
                async with self.lock:
                    await self.start()
                    if not self.session and not self.connections and self.match["date"] > utcnow():
                        return
                    if self.session and self.session.result is not None:
                        await self.finish()
                        return
                    if self.match["status"] == "completed":
                        await self.broadcast("match_finished")
                        return
                    if self.session:
                        s = self.session
                        if not self.connections:
                            s.paused = False
                            s.simulate_to_end()
                            await self.finish()
                            return
                        if s.paused and monotonic() >= s.pause_deadline:
                            s.paused = False
                        if not s.paused and (s.skip_target or monotonic() >= self.last_due):
                            before = len(s.frame["events"])
                            s.advance()
                            self.last_due = (
                                monotonic() + 5 * LIVE_MATCH_REAL_SECONDS_PER_GAME_MINUTE / s.speed
                            )
                            if s.status == "halftime" and s.skip_target not in {90, 120}:
                                s.paused = True
                                s.pause_deadline = monotonic() + TACTICAL_PAUSE_SECONDS
                                s.skip_target = 0
                            if s.skip_target and s.frame["minute"] >= s.skip_target:
                                s.skip_target = 0
                            await self.checkpoint()
                            new = s.frame["events"][before:]
                            for e in new:
                                if e["type"] in RELEVANT:
                                    for ws, (_, club_id) in list(self.connections.items()):
                                        safe = next(
                                            (
                                                x
                                                for x in self.events(club_id)
                                                if x["sequence"] == s.frame["events"].index(e)
                                            ),
                                            None,
                                        )
                                        if safe:
                                            await ws.send_json(
                                                {"type": "match_event", "data": public(safe)}
                                            )
                            for row in self.command_rows:
                                if row.get("reported") or row["status"] == "pending":
                                    continue
                                row["reported"] = True
                                for ws, (user, _) in list(self.connections.items()):
                                    if user.id == row["user_id"]:
                                        await ws.send_json(
                                            {
                                                "type": "command_rejected"
                                                if row["status"] == "rejected"
                                                else "command_applied",
                                                "data": public(row),
                                            }
                                        )
                            await self.broadcast(
                                "halftime" if s.status == "halftime" else "match_state"
                            )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.manager.logger.error(
                    "Live match %s failed (%s); retrying", self.identity, type(exc).__name__
                )
            await asyncio.sleep(0.05 if self.session and self.session.skip_target else 0.25)


class MatchRoomManager:
    def __init__(self, repo):
        import logging

        self.repo = repo
        self.rooms = {}
        self.lock = asyncio.Lock()
        self.closed = False
        self.logger = logging.getLogger(__name__)

    async def get(self, identity, user=None, start_task=True):
        if not ObjectId.is_valid(identity):
            raise HTTPException(404, "Partida não encontrada.")
        async with self.lock:
            room = self.rooms.get(identity)
            if room is None:
                match, collection = None, "matches"
                for collection in MATCH_COLLECTIONS:
                    match = await asyncio.to_thread(
                        self.repo.find, collection, {"_id": ObjectId(identity)}
                    )
                    if match:
                        break
                if not match:
                    raise HTTPException(404, "Partida não encontrada.")
                room = MatchRoom(self, match, collection)
                await room.load_metadata()
                if user:
                    await asyncio.to_thread(room.authorize, user)
                self.rooms[identity] = room
            elif user:
                await asyncio.to_thread(room.authorize, user)
            if (
                start_task
                and (room.task is None or room.task.done())
                and room.match["status"] != "completed"
            ):
                room.task = asyncio.create_task(room.run())
            return room

    async def start_due(self):
        for room in list(self.rooms.values()):
            if room.match["date"] <= utcnow() and room.match["status"] != "completed":
                async with room.lock:
                    await room.start()
                if room.session and (room.task is None or room.task.done()):
                    room.task = asyncio.create_task(room.run())
        # Retain active sessions and audiences, without polling empty future rooms.
        self.rooms = {
            key: room
            for key, room in self.rooms.items()
            if room.connections
            or room.session
            and room.match["status"] != "completed"
            or room.task
            and not room.task.done()
        }

    async def recover(self):
        await asyncio.to_thread(
            self.repo.update_many,
            "match_participants",
            {"connected": True},
            {"$set": {"connected": False, "disconnected_at": utcnow()}},
        )
        for collection in MATCH_COLLECTIONS:
            for match in await asyncio.to_thread(
                self.repo.many, collection, {"status": "live"}, limit=None
            ):
                await self.get(str(match["_id"]))

    async def close(self):
        self.closed = True
        tasks = [r.task for r in self.rooms.values() if r.task]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
