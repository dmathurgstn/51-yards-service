from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.config import get_settings
from app.schemas.health import HealthResponse, LivenessResponse, ReadinessResponse
from app.services.health_service import HealthService

router = APIRouter(prefix="/health", tags=["health"])


def get_health_service() -> HealthService:
    return HealthService(get_settings())


HealthServiceDependency = Annotated[HealthService, Depends(get_health_service)]


@router.get("", response_model=HealthResponse)
def health_summary(service: HealthServiceDependency) -> HealthResponse:
    """Return diagnostic health; degraded dependency state intentionally remains HTTP 200."""
    return service.summary()


@router.get("/live", response_model=LivenessResponse)
def liveness(service: HealthServiceDependency) -> LivenessResponse:
    return service.liveness()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
def readiness(service: HealthServiceDependency, response: Response) -> ReadinessResponse:
    result = service.readiness()
    if result.status == "not_ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
