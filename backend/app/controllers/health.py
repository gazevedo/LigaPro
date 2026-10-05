from fastapi import APIRouter, Depends

from app.api.dependencies import get_health_service
from app.services.health import HealthService

router = APIRouter(tags=["health"])


@router.get("/health")
def health(service: HealthService = Depends(get_health_service)) -> dict[str, str]:
    return service.check()
