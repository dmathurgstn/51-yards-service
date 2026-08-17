from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.auth_dependencies import require_active_user
from app.core.config import Settings
from app.core.exceptions import ApplicationError
from app.db.base import Base
from app.db.session import get_db_session
from app.main import create_application
from app.models.master_data import Amenity, City, Locality, PropertyCategory, PropertyType, State
from app.models.property import (
    Property,
    PropertyLeaseDetails,
    PropertyLocation,
    PropertyRentDetails,
    PropertySellDetails,
    PropertyStatusHistory,
)
from app.models.user import User
from app.schemas.property import PropertyCreateRequest
from app.services.property_service import PropertyService

Context = tuple[TestClient, Session, User, dict[str, int]]


@pytest.fixture
def property_context(settings: Settings) -> Iterator[Context]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)
    state = State(code="UP", name="Uttar Pradesh")
    session.add(state)
    session.flush()
    city = City(state_id=state.id, name="Noida", slug="noida")
    session.add(city)
    session.flush()
    locality = Locality(city_id=city.id, name="Sector 62", slug="sector-62")
    category = PropertyCategory(code="RESIDENTIAL", name="Residential", sort_order=1)
    session.add_all([locality, category])
    session.flush()
    property_type = PropertyType(
        category_id=category.id, code="APARTMENT", name="Apartment", sort_order=1
    )
    amenity = Amenity(code="LIFT", name="Lift", sort_order=1)
    user = User(id=10, full_name="Owner", email="owner@example.com", password_hash="hash")
    session.add_all([property_type, amenity, user])
    session.commit()
    ids = {
        "state": state.id,
        "city": city.id,
        "locality": locality.id,
        "category": category.id,
        "type": property_type.id,
        "amenity": amenity.id,
    }
    application = create_application(settings)
    application.dependency_overrides[get_db_session] = lambda: session
    application.dependency_overrides[require_active_user] = lambda: user
    with TestClient(application, raise_server_exceptions=False) as client:
        yield client, session, user, ids
    session.close()
    engine.dispose()


def complete_payload(ids: dict[str, int]) -> dict[str, object]:
    return {
        "propertyCategoryId": ids["category"],
        "propertyTypeId": ids["type"],
        "listingPurpose": "SELL",
        "title": "Apartment in Noida",
        "description": "A sufficiently detailed property description.",
        "carpetArea": "900.00",
        "areaUnit": "SQ_FT",
        "stateId": ids["state"],
        "cityId": ids["city"],
        "localityId": ids["locality"],
        "addressLine": "Sector 62, Noida",
        "price": "8500000.00",
        "amenityIds": [ids["amenity"]],
    }


def test_master_data_is_public_sorted_and_filterable(property_context: Context) -> None:
    client, _, _, ids = property_context
    assert client.get("/api/v1/master-data/states").json()[0]["code"] == "UP"
    cities = client.get(f"/api/v1/master-data/cities?stateId={ids['state']}").json()
    assert cities[0]["name"] == "Noida"
    assert client.get(f"/api/v1/master-data/localities?cityId={ids['city']}").status_code == 200
    types = client.get(f"/api/v1/master-data/property-types?categoryId={ids['category']}").json()
    assert types[0]["code"] == "APARTMENT"
    assert client.get("/api/v1/master-data/amenities").json()[0]["code"] == "LIFT"


def test_create_assigns_owner_draft_amenities_and_history(property_context: Context) -> None:
    client, session, user, ids = property_context
    response = client.post("/api/v1/properties", json=complete_payload(ids))
    assert response.status_code == 201, response.text
    item = session.scalar(select(Property))
    assert item is not None and item.owner_user_id == user.id and item.status == "DRAFT"
    assert [value.code for value in item.amenities] == ["LIFT"]
    history = session.scalar(select(PropertyStatusHistory))
    assert history is not None and history.old_status is None and history.new_status == "DRAFT"
    assert session.scalar(select(PropertyLocation)) is not None
    assert session.scalar(select(PropertySellDetails)) is not None
    assert session.scalar(select(PropertyRentDetails)) is None
    assert session.scalar(select(PropertyLeaseDetails)) is None


@pytest.mark.parametrize(
    ("purpose", "expected", "absent"),
    [
        ("RENT", PropertyRentDetails, PropertyLeaseDetails),
        ("LEASE", PropertyLeaseDetails, PropertyRentDetails),
    ],
)
def test_pricing_is_routed_to_purpose_table(
    property_context: Context,
    purpose: str,
    expected: type[PropertyRentDetails] | type[PropertyLeaseDetails],
    absent: type[PropertyRentDetails] | type[PropertyLeaseDetails],
) -> None:
    client, session, _, ids = property_context
    payload = complete_payload(ids)
    payload["listingPurpose"] = purpose
    assert client.post("/api/v1/properties", json=payload).status_code == 201
    assert session.scalar(select(expected)) is not None
    assert session.scalar(select(absent)) is None
    assert session.scalar(select(PropertySellDetails)) is None


def test_create_rejects_master_data_mismatches(property_context: Context) -> None:
    client, session, _, ids = property_context
    other = PropertyCategory(code="LAND", name="Land", sort_order=2)
    session.add(other)
    session.commit()
    payload = complete_payload(ids)
    payload["propertyCategoryId"] = other.id
    response = client.post("/api/v1/properties", json=payload)
    assert response.json()["error"]["code"] == "PROPERTY_TYPE_INVALID"
    payload = complete_payload(ids)
    payload["cityId"] = 999
    response = client.post("/api/v1/properties", json=payload)
    assert response.json()["error"]["code"] == "PROPERTY_LOCATION_INVALID"


def test_mine_route_precedes_details_and_filters(property_context: Context) -> None:
    client, _, _, ids = property_context
    client.post("/api/v1/properties", json=complete_payload(ids))
    response = client.get("/api/v1/properties/mine?status=DRAFT")
    assert response.status_code == 200 and len(response.json()) == 1


def test_update_submit_archive_lifecycle(property_context: Context) -> None:
    client, session, _, ids = property_context
    public_id = client.post("/api/v1/properties", json=complete_payload(ids)).json()["id"]
    updated = client.patch(f"/api/v1/properties/{public_id}", json={"title": "Updated apartment"})
    assert updated.json()["title"] == "Updated apartment"
    submitted = client.post(f"/api/v1/properties/{public_id}/submit")
    assert submitted.json()["status"] == "PENDING_REVIEW" and submitted.json()["submittedAt"]
    archived = client.delete(f"/api/v1/properties/{public_id}")
    assert archived.json()["status"] == "ARCHIVED"
    assert len(list(session.scalars(select(PropertyStatusHistory)))) == 3


def test_incomplete_draft_cannot_submit(property_context: Context) -> None:
    _, session, user, ids = property_context
    item = PropertyService(session).create(
        PropertyCreateRequest(propertyCategoryId=ids["category"]), user
    )
    with pytest.raises(ApplicationError, match="incomplete") as error:
        PropertyService(session).submit(str(item["public_id"]), user)
    assert error.value.code == "PROPERTY_INCOMPLETE"


def test_other_user_cannot_access_private_draft(property_context: Context) -> None:
    client, session, _, ids = property_context
    public_id = client.post("/api/v1/properties", json=complete_payload(ids)).json()["id"]
    other = User(id=11, full_name="Other", email="other@example.com", password_hash="hash")
    session.add(other)
    session.commit()
    service = PropertyService(session)
    with pytest.raises(ApplicationError) as hidden:
        service.details(public_id, other)
    assert hidden.value.code == "PROPERTY_NOT_FOUND"
    with pytest.raises(ApplicationError) as forbidden:
        service.archive(public_id, other)
    assert forbidden.value.code == "PROPERTY_FORBIDDEN"
