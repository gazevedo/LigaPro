from fastapi import APIRouter, Depends, Response

from app.api.dependencies import get_health_service
from app.services.health import HealthService

router = APIRouter(tags=["health"])


@router.get("/health")
def health(
    response: Response, service: HealthService = Depends(get_health_service)
) -> dict[str, object]:
    result = service.check()
    if result["status"] == "initializing":
        response.status_code = 202
        response.headers["Retry-After"] = "1"
    elif result["status"] == "error":
        response.status_code = 503
    return result
