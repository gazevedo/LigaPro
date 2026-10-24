import asyncio
from typing import Annotated

from anyio import CancelScope
from fastapi import APIRouter, Depends, HTTPException, Path, Request

from app.api.dependencies import get_current_user, get_settings_service
from app.schemas.settings import DatabaseResetInput, SettingResponse, SettingUpdate
from app.services.settings import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(get_current_user)])
Service = Annotated[SettingsService, Depends(get_settings_service)]
Key = Annotated[str, Path(min_length=1, max_length=100)]


@router.get("", response_model=list[SettingResponse])
def list_settings(service: Service):
    return service.list()


@router.get("/database-reset")
def reset_capability(user=Depends(get_current_user)):
    return {"allowed": SettingsService.can_reset_database(user)}


@router.post("/database-reset")
async def reset_database(
    body: DatabaseResetInput, request: Request, service: Service, user=Depends(get_current_user)
):
    if not service.can_reset_database(user):
        raise HTTPException(403, "Somente o administrador pode reinicializar o banco de dados.")
    # Disconnects must not interrupt deletion between clearing and seeding.
    with CancelScope(shield=True):
        manager = getattr(request.app.state, "match_rooms", None)
        if manager:
            await manager.close()
        try:
            return await asyncio.to_thread(service.reset_database, user)
        finally:
            if manager:
                from app.repositories.game import GameRepository
                from app.services.live_match import MatchRoomManager

                request.app.state.match_rooms = MatchRoomManager(
                    GameRepository(service.repository.collection.database)
                )


@router.get("/{key}", response_model=SettingResponse)
def get_setting(key: Key, service: Service):
    return service.get(key)


@router.put("/{key}", response_model=SettingResponse)
def put_setting(key: Key, body: SettingUpdate, service: Service):
    return service.put(key, body.value)
