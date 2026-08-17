from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.master_data import router as master_data_router
from app.api.v1.endpoints.properties import router as properties_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(master_data_router)
api_router.include_router(properties_router)
