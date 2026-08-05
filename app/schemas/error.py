from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None
    request_id: str = Field(alias="requestId")


class ErrorResponse(BaseModel):
    error: ErrorDetail
