from uuid import UUID, uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.constants import MAX_REQUEST_ID_LENGTH, REQUEST_ID_HEADER
from app.core.logging import bind_request_id, reset_request_id


def normalize_request_id(candidate: str | None) -> str:
    if candidate is None or len(candidate) > MAX_REQUEST_ID_LENGTH:
        return str(uuid4())
    try:
        return str(UUID(candidate))
    except ValueError:
        return str(uuid4())


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        token = bind_request_id(request_id)
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            reset_request_id(token)
