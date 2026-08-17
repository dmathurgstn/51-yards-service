from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import ApplicationError
from app.models.property import (
    ListingPurpose,
    Property,
    PropertyLeaseDetails,
    PropertyLocation,
    PropertyRentDetails,
    PropertySellDetails,
    PropertyStatus,
    PropertyStatusHistory,
)
from app.models.user import User
from app.repositories.master_data_repository import MasterDataRepository
from app.repositories.property_repository import PropertyRepository
from app.schemas.property import PropertyCreateRequest, PropertyUpdateRequest


class PropertyService:
    """Composes the normalized property tables into one API aggregate."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.master = MasterDataRepository(session)
        self.properties = PropertyRepository(session)

    def create(self, request: PropertyCreateRequest, user: User) -> dict[str, Any]:
        values = request.model_dump(exclude_none=True)
        amenities = self._validate(values, request.amenity_ids or [])
        purpose = request.listing_purpose or ListingPurpose.SELL
        category = self.master.category(request.property_category_id or 0)
        property_type = self.master.property_type(request.property_type_id or 0)
        item = Property(
            owner_user_id=user.id,
            listing_purpose=purpose.value,
            legacy_category=category.code if category else None,
            legacy_property_type=property_type.name if property_type else "",
            property_category_id=request.property_category_id,
            property_type_id=request.property_type_id,
            title=request.title or "Untitled property",
            description=request.description,
            bedrooms=request.bedrooms,
            bathrooms=request.bathrooms,
            balconies=request.balconies,
            furnishing_status=request.furnishing_status,
            construction_status=request.construction_status,
            property_age_years=request.property_age_years,
            floor_number=request.floor_number,
            total_floors=request.total_floors,
            facing=request.facing,
            area_type=self._area(request)[0],
            area_value=self._area(request)[1],
            area_unit=request.area_unit,
            status=PropertyStatus.DRAFT.value,
        )
        item.location = self._location(request)
        self._replace_pricing(item, request)
        item.amenities = amenities
        try:
            self.properties.add(item)
            self.session.add(
                PropertyStatusHistory(
                    property_id=item.id,
                    old_status=None,
                    new_status=PropertyStatus.DRAFT.value,
                    changed_by_user_id=user.id,
                )
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return self.response(self._reload(item))

    def mine(self, user: User, status: PropertyStatus | None) -> list[dict[str, Any]]:
        return [
            self.summary(item)
            for item in self.properties.list_owned(user.id, status.value if status else None)
        ]

    def details(self, public_id: str, user: User | None) -> dict[str, Any]:
        item = self.properties.by_public_id(public_id)
        if item is None or (
            item.status != PropertyStatus.ACTIVE.value
            and (user is None or item.owner_user_id != user.id)
        ):
            raise ApplicationError("PROPERTY_NOT_FOUND", "Property was not found.", status_code=404)
        return self.response(item)

    def update(self, public_id: str, request: PropertyUpdateRequest, user: User) -> dict[str, Any]:
        item = self._owned(public_id, user)
        if item.status not in {PropertyStatus.DRAFT.value, PropertyStatus.REJECTED.value}:
            self._invalid_status()
        changes = request.model_dump(exclude_unset=True)
        amenity_ids = changes.pop("amenity_ids", None)
        self._validate_update(item, changes, amenity_ids)
        self._apply_core(item, request, changes)
        self._apply_location(item, request, changes)
        if "listing_purpose" in changes or self._pricing_changed(changes):
            self._replace_pricing(item, request, changes)
        if amenity_ids is not None:
            item.amenities = self.master.amenities_by_ids(amenity_ids)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return self.response(self._reload(item))

    def submit(self, public_id: str, user: User) -> dict[str, Any]:
        item = self._owned(public_id, user)
        if item.status not in {PropertyStatus.DRAFT.value, PropertyStatus.REJECTED.value}:
            self._invalid_status()
        self._validate_complete(item)
        old = item.status
        item.status = PropertyStatus.PENDING_REVIEW.value
        item.submitted_at = datetime.now(UTC)
        item.rejection_reason = None
        self._history(item, old, user)
        self.session.commit()
        return self.response(self._reload(item))

    def archive(self, public_id: str, user: User) -> dict[str, Any]:
        item = self._owned(public_id, user)
        if item.status == PropertyStatus.ARCHIVED.value:
            self._invalid_status()
        old = item.status
        item.status = PropertyStatus.ARCHIVED.value
        self._history(item, old, user)
        self.session.commit()
        return self.response(self._reload(item))

    def summary(self, item: Property) -> dict[str, Any]:
        location = item.location
        return {
            "public_id": item.public_id,
            "title": item.title,
            "listing_purpose": item.listing_purpose,
            "price": self._price(item),
            "status": item.status,
            "city": self.master.city(location.city_id) if location and location.city_id else None,
            "locality": (
                self.master.locality(location.locality_id)
                if location and location.locality_id
                else None
            ),
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    def response(self, item: Property) -> dict[str, Any]:
        location = item.location
        price = self._price_details(item)
        return {
            **self.summary(item),
            "description": item.description,
            "property_category_id": item.property_category_id,
            "property_type_id": item.property_type_id,
            "category": item.category,
            "property_type": item.property_type,
            "bedrooms": item.bedrooms,
            "bathrooms": item.bathrooms,
            "balconies": item.balconies,
            "furnishing_status": item.furnishing_status,
            "construction_status": item.construction_status,
            "property_age_years": item.property_age_years,
            "floor_number": item.floor_number,
            "total_floors": item.total_floors,
            "facing": item.facing,
            "carpet_area": item.area_value if item.area_type == "CARPET" else None,
            "built_up_area": item.area_value if item.area_type == "BUILTUP" else None,
            "super_built_up_area": item.area_value if item.area_type == "SUPER_BUILTUP" else None,
            "plot_area": item.area_value if item.area_type == "PLOT" else None,
            "area_unit": item.area_unit,
            "state": self.master.state(location.state_id)
            if location and location.state_id
            else None,
            "address_line": location.address_line if location else None,
            "landmark": location.landmark if location else None,
            "pin_code": location.pin_code if location else None,
            "latitude": location.latitude if location else None,
            "longitude": location.longitude if location else None,
            "maintenance_charge": getattr(price, "maintenance_charge", None),
            "security_deposit": getattr(price, "security_deposit", None),
            "brokerage_amount": getattr(price, "brokerage_amount", None),
            "is_negotiable": bool(getattr(price, "is_negotiable", False)),
            "available_from": getattr(price, "available_from", None),
            "possession_status": None,
            "rejection_reason": item.rejection_reason,
            "submitted_at": item.submitted_at,
            "approved_at": item.approved_at,
            "amenities": item.amenities,
        }

    def _validate_update(
        self, item: Property, changes: dict[str, Any], amenity_ids: list[int] | None
    ) -> None:
        values = {
            "property_category_id": item.property_category_id,
            "property_type_id": item.property_type_id,
            "state_id": item.location.state_id if item.location else None,
            "city_id": item.location.city_id if item.location else None,
            "locality_id": item.location.locality_id if item.location else None,
        }
        values.update(changes)
        ids = amenity_ids if amenity_ids is not None else [value.id for value in item.amenities]
        self._validate(values, ids)

    def _validate(self, values: dict[str, Any], amenity_ids: list[int]) -> list[Any]:
        category = self.master.category(values.get("property_category_id") or 0)
        property_type = self.master.property_type(values.get("property_type_id") or 0)
        if values.get("property_category_id") and (category is None or not category.is_active):
            raise ApplicationError("PROPERTY_CATEGORY_INVALID", "Property category is invalid.")
        if values.get("property_type_id") and (
            property_type is None or not property_type.is_active
        ):
            raise ApplicationError("PROPERTY_TYPE_INVALID", "Property type is invalid.")
        if category and property_type and property_type.category_id != category.id:
            raise ApplicationError(
                "PROPERTY_TYPE_INVALID", "Property type does not belong to the category."
            )
        state = self.master.state(values.get("state_id") or 0)
        city = self.master.city(values.get("city_id") or 0)
        locality = self.master.locality(values.get("locality_id") or 0)
        if (
            values.get("state_id")
            and (state is None or not state.is_active)
            or values.get("city_id")
            and (city is None or not city.is_active)
            or values.get("locality_id")
            and (locality is None or not locality.is_active)
            or state
            and city
            and city.state_id != state.id
            or city
            and locality
            and locality.city_id != city.id
        ):
            raise ApplicationError(
                "PROPERTY_LOCATION_INVALID", "Property location hierarchy is invalid."
            )
        amenities = self.master.amenities_by_ids(amenity_ids)
        if len(amenities) != len(amenity_ids) or any(not value.is_active for value in amenities):
            raise ApplicationError("PROPERTY_AMENITY_INVALID", "One or more amenities are invalid.")
        return amenities

    @staticmethod
    def _area(
        request: PropertyCreateRequest | PropertyUpdateRequest,
    ) -> tuple[str | None, Decimal | None]:
        for name, code in (
            ("carpet_area", "CARPET"),
            ("built_up_area", "BUILTUP"),
            ("super_built_up_area", "SUPER_BUILTUP"),
            ("plot_area", "PLOT"),
        ):
            value = getattr(request, name)
            if value is not None:
                return code, value
        return None, None

    def _location(self, request: PropertyCreateRequest) -> PropertyLocation:
        state = self.master.state(request.state_id or 0)
        city = self.master.city(request.city_id or 0)
        locality = self.master.locality(request.locality_id or 0)
        return PropertyLocation(
            address_line=request.address_line,
            landmark=request.landmark,
            pin_code=request.pin_code,
            latitude=request.latitude,
            longitude=request.longitude,
            state_id=request.state_id,
            city_id=request.city_id,
            locality_id=request.locality_id,
            legacy_state=state.name if state else None,
            legacy_city=city.name if city else None,
            locality_society=locality.name if locality else None,
            country="India",
        )

    def _apply_location(
        self, item: Property, request: PropertyUpdateRequest, changes: dict[str, Any]
    ) -> None:
        names = {
            "address_line",
            "landmark",
            "pin_code",
            "latitude",
            "longitude",
            "state_id",
            "city_id",
            "locality_id",
        }
        if not names.intersection(changes):
            return
        if item.location is None:
            item.location = PropertyLocation()
        for name in names.intersection(changes):
            setattr(item.location, name, getattr(request, name))
        state = self.master.state(item.location.state_id or 0)
        city = self.master.city(item.location.city_id or 0)
        locality = self.master.locality(item.location.locality_id or 0)
        item.location.legacy_state = state.name if state else None
        item.location.legacy_city = city.name if city else None
        item.location.locality_society = locality.name if locality else None

    def _apply_core(
        self, item: Property, request: PropertyUpdateRequest, changes: dict[str, Any]
    ) -> None:
        direct = {
            "title",
            "description",
            "bedrooms",
            "bathrooms",
            "balconies",
            "furnishing_status",
            "construction_status",
            "property_age_years",
            "floor_number",
            "total_floors",
            "facing",
            "property_category_id",
            "property_type_id",
            "area_unit",
        }
        for name in direct.intersection(changes):
            setattr(item, name, getattr(request, name))
        if "listing_purpose" in changes and request.listing_purpose:
            item.listing_purpose = request.listing_purpose.value
        if {"carpet_area", "built_up_area", "super_built_up_area", "plot_area"}.intersection(
            changes
        ):
            item.area_type, item.area_value = self._area(request)

    def _replace_pricing(
        self,
        item: Property,
        request: PropertyCreateRequest | PropertyUpdateRequest,
        changes: dict[str, Any] | None = None,
    ) -> None:
        purpose = request.listing_purpose.value if request.listing_purpose else item.listing_purpose
        existing = self._price_details(item)
        price = request.price if request.price is not None else getattr(existing, "price", None)
        common = {
            "price": price,
            "is_negotiable": request.is_negotiable,
            "maintenance_charge": request.maintenance_charge,
            "brokerage_amount": request.brokerage_amount,
        }
        item.sell_details = None
        item.rent_details = None
        item.lease_details = None
        if purpose == ListingPurpose.SELL.value:
            item.sell_details = PropertySellDetails(**common)
        elif purpose == ListingPurpose.RENT.value:
            item.rent_details = PropertyRentDetails(
                **common,
                security_deposit=request.security_deposit,
                available_from=request.available_from,
            )
        else:
            item.lease_details = PropertyLeaseDetails(
                **common,
                security_deposit=request.security_deposit,
                available_from=request.available_from,
            )

    @staticmethod
    def _pricing_changed(changes: dict[str, Any]) -> bool:
        return bool(
            {
                "price",
                "maintenance_charge",
                "security_deposit",
                "brokerage_amount",
                "is_negotiable",
                "available_from",
            }.intersection(changes)
        )

    @staticmethod
    def _price_details(item: Property) -> Any:
        return item.sell_details or item.rent_details or item.lease_details

    def _price(self, item: Property) -> Decimal | None:
        details = self._price_details(item)
        return details.price if details else None

    def _validate_complete(self, item: Property) -> None:
        location = item.location
        required = (
            item.title,
            item.description,
            item.property_category_id,
            item.property_type_id,
            item.listing_purpose,
            location and location.state_id,
            location and location.city_id,
            location and location.locality_id,
            location and location.address_line,
            self._price(item),
            item.area_value,
            item.area_unit,
        )
        if any(value is None or value == "" for value in required):
            raise ApplicationError(
                "PROPERTY_INCOMPLETE", "Property is incomplete and cannot be submitted."
            )

    def _owned(self, public_id: str, user: User) -> Property:
        item = self.properties.by_public_id(public_id)
        if item is None:
            raise ApplicationError("PROPERTY_NOT_FOUND", "Property was not found.", status_code=404)
        if item.owner_user_id != user.id:
            raise ApplicationError(
                "PROPERTY_FORBIDDEN", "You do not own this property.", status_code=403
            )
        return item

    def _history(self, item: Property, old: str, user: User) -> None:
        self.session.add(
            PropertyStatusHistory(
                property_id=item.id,
                old_status=old,
                new_status=item.status,
                changed_by_user_id=user.id,
            )
        )

    def _reload(self, item: Property) -> Property:
        refreshed = self.properties.by_public_id(item.public_id)
        assert refreshed is not None
        return refreshed

    @staticmethod
    def _invalid_status() -> None:
        raise ApplicationError(
            "PROPERTY_INVALID_STATUS",
            "Property lifecycle transition is not allowed.",
            status_code=409,
        )
