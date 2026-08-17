from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.repositories.master_data_repository import MasterDataRepository
from app.schemas.master_data import (
    AmenityResponse,
    CityResponse,
    LocalityResponse,
    PropertyCategoryResponse,
    PropertyTypeResponse,
    StateResponse,
)

router = APIRouter(prefix="/master-data", tags=["Master Data"])
Db = Annotated[Session, Depends(get_db_session)]


@router.get("/states", response_model=list[StateResponse])
def states(session: Db) -> list[object]:
    return list(MasterDataRepository(session).states())


@router.get("/cities", response_model=list[CityResponse])
def cities(
    session: Db, state_id: Annotated[int | None, Query(alias="stateId")] = None
) -> list[object]:
    return list(MasterDataRepository(session).cities(state_id))


@router.get("/localities", response_model=list[LocalityResponse])
def localities(
    session: Db, city_id: Annotated[int | None, Query(alias="cityId")] = None
) -> list[object]:
    return list(MasterDataRepository(session).localities(city_id))


@router.get("/property-categories", response_model=list[PropertyCategoryResponse])
def categories(session: Db) -> list[object]:
    return list(MasterDataRepository(session).categories())


@router.get("/property-types", response_model=list[PropertyTypeResponse])
def property_types(
    session: Db, category_id: Annotated[int | None, Query(alias="categoryId")] = None
) -> list[object]:
    return list(MasterDataRepository(session).types(category_id))


@router.get("/amenities", response_model=list[AmenityResponse])
def amenities(session: Db) -> list[object]:
    return list(MasterDataRepository(session).amenities())
