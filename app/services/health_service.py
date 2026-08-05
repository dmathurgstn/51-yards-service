from collections.abc import Callable
from datetime import UTC, datetime

from app.core.config import Settings
from app.db.health import database_is_ready
from app.schemas.health import HealthResponse, LivenessResponse, ReadinessResponse


class HealthService:
    def __init__(
        self,
        settings: Settings,
        database_checker: Callable[[], bool] = database_is_ready,
    ) -> None:
        self._settings = settings
        self._database_checker = database_checker

    def liveness(self) -> LivenessResponse:
        return LivenessResponse(
            status="healthy",
            service=self._settings.application_name,
            version=self._settings.application_version,
        )

    def readiness(self) -> ReadinessResponse:
        connected = self._database_checker()
        return ReadinessResponse(
            status="ready" if connected else "not_ready",
            service=self._settings.application_name,
            database="connected" if connected else "disconnected",
        )

    def summary(self) -> HealthResponse:
        connected = self._database_checker()
        return HealthResponse(
            status="healthy" if connected else "degraded",
            service=self._settings.application_name,
            version=self._settings.application_version,
            environment=self._settings.environment,
            database="connected" if connected else "disconnected",
            timestamp=datetime.now(UTC),
        )
