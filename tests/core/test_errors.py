from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.exception_handlers import register_exception_handlers
from app.core.middleware import CorrelationIdMiddleware


def create_error_application() -> FastAPI:
    application = FastAPI()
    application.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(application)

    @application.get("/http-error")
    def http_error() -> None:
        raise HTTPException(status_code=404, detail="Not found")

    @application.get("/unexpected")
    def unexpected() -> None:
        raise RuntimeError("secret technical detail")

    @application.get("/validated")
    def validated(limit: int) -> dict[str, int]:
        return {"limit": limit}

    return application


def test_http_and_validation_error_contracts() -> None:
    with TestClient(create_error_application(), raise_server_exceptions=False) as client:
        http_error = client.get("/http-error")
        validation_error = client.get("/validated?limit=wrong")
    assert http_error.json()["error"]["code"] == "HTTP_ERROR"
    assert http_error.json()["error"]["requestId"]
    assert validation_error.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"
    assert validation_error.json()["error"]["details"]


def test_unexpected_error_is_safe() -> None:
    with TestClient(create_error_application(), raise_server_exceptions=False) as client:
        response = client.get("/unexpected")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "secret technical detail" not in response.text
