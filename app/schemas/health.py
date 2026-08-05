from datetime import datetime
from typing import Literal

from pydantic import BaseModel

DatabaseStatus = Literal["connected", "disconnected"]


class LivenessResponse(BaseModel):
    status: Literal["healthy"]
    service: str
    version: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    service: str
    database: DatabaseStatus


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    service: str
    version: str
    environment: str
    database: DatabaseStatus
    timestamp: datetime
