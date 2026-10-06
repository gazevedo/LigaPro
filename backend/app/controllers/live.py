"""Authenticated REST controls and one WebSocket room shared by both managers."""

import asyncio
from typing import Annotated

from anyio import CancelScope
from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import get_current_user
from app.config.settings import get_settings
from app.models.game import public, utcnow
from app.repositories.auth import AuthRepository
from app.services.auth import AuthService

router = APIRouter(tags=["live-matches"])
User = Annotated[object, Depends(get_current_user)]


class LiveCommandInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_id: str = Field(min_length=1, max_length=80)
    payload: dict


class SpeedInput(BaseModel):
    speed: int


async def apply_command(room, user, message):
    # A disconnect must not interrupt persistence between accepting and queueing.
    with CancelScope(shield=True):
        return await room.command(user, message)


@router.get("/api/matches/{identity}/live-state")
async def live_state(identity: str, request: Request, user: User):
    room = await request.app.state.match_rooms.get(identity, user)
    club = await asyncio.to_thread(room.authorize, user)
    async with room.lock:
        await room.start()
        return room.state(str(club["_id"]))


@router.get("/api/matches/{identity}/events")
async def events(identity: str, request: Request, user: User, after: int = -1):
    room = await request.app.state.match_rooms.get(identity, user)
    club = await asyncio.to_thread(room.authorize, user)
    return public([e for e in room.events(str(club["_id"])) if e["sequence"] > after])


@router.post("/api/matches/{identity}/commands/{kind}")
async def command(identity: str, kind: str, data: LiveCommandInput, request: Request, user: User):
    if kind not in {"substitution", "formation", "tactics", "combined_change"}:
        raise HTTPException(422, "Tipo de comando inválido.")
    room = await request.app.state.match_rooms.get(identity, user)
    return await apply_command(
        room,
        user,
        {
            "type": "substitution" if kind == "substitution" else "tactics_change",
            **data.model_dump(),
        },
    )


@router.post("/api/matches/{identity}/pause")
async def pause(identity: str, request: Request, user: User):
    room = await request.app.state.match_rooms.get(identity, user)
    return await apply_command(room, user, {"type": "pause"})


@router.post("/api/matches/{identity}/resume")
async def resume(identity: str, request: Request, user: User):
    room = await request.app.state.match_rooms.get(identity, user)
    return await apply_command(room, user, {"type": "resume"})


@router.post("/api/matches/{identity}/speed")
async def speed(identity: str, data: SpeedInput, request: Request, user: User):
    room = await request.app.state.match_rooms.get(identity, user)
    return await apply_command(room, user, {"type": "set_speed", **data.model_dump()})


@router.websocket("/ws/matches/{identity}")
async def websocket_match(websocket: WebSocket, identity: str):
    # Native clients send an Authorization header; browsers send the token as a
    # subprotocol, avoiding access tokens in URLs and access logs.
    protocols = websocket.headers.get("sec-websocket-protocol", "").split(",")
    token_protocol = next((p.strip() for p in protocols if p.strip().startswith("bearer.")), None)
    auth = websocket.headers.get("authorization", "")
    token = (
        auth[7:]
        if auth.lower().startswith("bearer ")
        else token_protocol[7:]
        if token_protocol
        else None
    )
    manager = websocket.app.state.match_rooms
    try:
        if not token:
            raise HTTPException(401, "Autenticação necessária.")
        service = AuthService(AuthRepository(manager.repo.database), get_settings())
        user = await asyncio.to_thread(service.current_user, token)
        room = await manager.get(identity, user, start_task=False)
        club = await asyncio.to_thread(room.authorize, user)
    except HTTPException:
        await websocket.close(code=1008)
        return
    await websocket.accept(subprotocol=token_protocol)
    cid = str(club["_id"])
    participant_id = f"{identity}:{user.id}"
    role = "home_manager" if cid == str(room.match["home_club_id"]) else "away_manager"
    async with room.lock:
        room.connections[websocket] = (user, cid)
        await asyncio.to_thread(
            manager.repo.database.match_participants.update_one,
            {"_id": participant_id},
            {
                "$set": {
                    "match_id": room.match["_id"],
                    "user_id": user.id,
                    "club_id": club["_id"],
                    "role": role,
                    "connected": True,
                    "last_seen_at": utcnow(),
                    "disconnected_at": None,
                },
                "$setOnInsert": {"joined_at": utcnow()},
            },
            upsert=True,
        )
        await room.start()
        await room.broadcast("participant_connected")
        await websocket.send_json({"type": "sync", "data": room.state(cid)})
    if room.task is None or room.task.done():
        room.task = asyncio.create_task(room.run())
    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_json(), timeout=45)
                # Session revocation/expiry must invalidate a long-lived socket too.
                await asyncio.to_thread(service.current_user, token)
                if not isinstance(message, dict):
                    raise HTTPException(422, "Mensagem inválida.")
                kind = message.get("type")
                if kind in {"join", "heartbeat"}:
                    await asyncio.to_thread(
                        manager.repo.database.match_participants.update_one,
                        {"_id": participant_id},
                        {"$set": {"last_seen_at": utcnow()}},
                    )
                    await websocket.send_json({"type": "sync", "data": room.state(cid)})
                    continue
                result = await apply_command(room, user, message)
                await websocket.send_json(
                    {
                        "type": "command_pending"
                        if result.get("status") == "pending"
                        else "command_applied",
                        "data": public(result),
                    }
                )
            except HTTPException as exc:
                await websocket.send_json(
                    {"type": "command_rejected", "data": {"reason": exc.detail}}
                )
                if exc.status_code == 401:
                    await websocket.close(code=1008)
                    break
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        # ASGI disconnect cancellation must not leave stale online participants.
        with CancelScope(shield=True):
            async with room.lock:
                room.connections.pop(websocket, None)
                still_online = user.id in room.connected_users
                await asyncio.to_thread(
                    manager.repo.database.match_participants.update_one,
                    {"_id": participant_id},
                    {
                        "$set": {
                            "connected": still_online,
                            "disconnected_at": None if still_online else utcnow(),
                        }
                    },
                )
                await room.broadcast("participant_disconnected")
