from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.dependencies import get_current_user, get_settings_service
from app.schemas.settings import SettingResponse, SettingUpdate
from app.services.settings import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(get_current_user)])
Service = Annotated[SettingsService, Depends(get_settings_service)]
Key = Annotated[str, Path(min_length=1, max_length=100)]


@router.get("", response_model=list[SettingResponse])
def list_settings(service: Service):
    return service.list()


@router.get("/{key}", response_model=SettingResponse)
def get_setting(key: Key, service: Service):
    return service.get(key)


@router.put("/{key}", response_model=SettingResponse)
def put_setting(key: Key, body: SettingUpdate, service: Service):
    return service.put(key, body.value)
