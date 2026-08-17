from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.property import (
    AreaUnit,
    ConstructionStatus,
    FurnishingStatus,
    ListingPurpose,
    PropertyStatus,
)
from app.schemas.master_data import (
    AmenityResponse,
    CityResponse,
    LocalityResponse,
    PropertyCategoryResponse,
    PropertyTypeResponse,
    StateResponse,
)


class PropertyFields(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    property_category_id: int | None = Field(None, alias="propertyCategoryId")
    property_type_id: int | None = Field(None, alias="propertyTypeId")
    listing_purpose: ListingPurpose | None = Field(None, alias="listingPurpose")
    title: str | None = Field(None, min_length=3, max_length=180)
    description: str | None = Field(None, min_length=10)
    bedrooms: int | None = Field(None, ge=0)
    bathrooms: int | None = Field(None, ge=0)
    balconies: int | None = Field(None, ge=0)
    furnishing_status: FurnishingStatus | None = Field(None, alias="furnishingStatus")
    construction_status: ConstructionStatus | None = Field(None, alias="constructionStatus")
    property_age_years: int | None = Field(None, alias="propertyAgeYears", ge=0)
    floor_number: int | None = Field(None, alias="floorNumber", ge=0)
    total_floors: int | None = Field(None, alias="totalFloors", ge=0)
    facing: str | None = Field(None, max_length=30)
    carpet_area: Decimal | None = Field(None, alias="carpetArea", gt=0)
    built_up_area: Decimal | None = Field(None, alias="builtUpArea", gt=0)
    super_built_up_area: Decimal | None = Field(None, alias="superBuiltUpArea", gt=0)
    plot_area: Decimal | None = Field(None, alias="plotArea", gt=0)
    area_unit: AreaUnit | None = Field(None, alias="areaUnit")
    state_id: int | None = Field(None, alias="stateId")
    city_id: int | None = Field(None, alias="cityId")
    locality_id: int | None = Field(None, alias="localityId")
    address_line: str | None = Field(None, alias="addressLine", max_length=255)
    landmark: str | None = Field(None, max_length=180)
    pin_code: str | None = Field(None, alias="pinCode", pattern=r"^\d{6}$")
    latitude: Decimal | None = Field(None, ge=-90, le=90)
    longitude: Decimal | None = Field(None, ge=-180, le=180)
    price: Decimal | None = Field(None, gt=0)
    maintenance_charge: Decimal | None = Field(None, alias="maintenanceCharge", ge=0)
    security_deposit: Decimal | None = Field(None, alias="securityDeposit", ge=0)
    brokerage_amount: Decimal | None = Field(None, alias="brokerageAmount", ge=0)
    is_negotiable: bool | None = Field(None, alias="isNegotiable")
    available_from: date | None = Field(None, alias="availableFrom")
    possession_status: str | None = Field(None, alias="possessionStatus", max_length=50)
    amenity_ids: list[int] | None = Field(None, alias="amenityIds")

    @field_validator("amenity_ids")
    @classmethod
    def unique_amenities(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return value
        if len(value) != len(set(value)):
            raise ValueError("Amenity IDs must be unique")
        return value

    @model_validator(mode="after")
    def floor_is_sensible(self) -> "PropertyFields":
        if (
            self.floor_number is not None
            and self.total_floors is not None
            and self.floor_number > self.total_floors
        ):
            raise ValueError("Floor number cannot exceed total floors")
        return self


class PropertyCreateRequest(PropertyFields):
    pass


class PropertyUpdateRequest(PropertyFields):
    pass


class PropertySummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: str = Field(validation_alias="public_id", serialization_alias="id")
    title: str | None
    listing_purpose: ListingPurpose | None = Field(serialization_alias="listingPurpose")
    price: Decimal | None
    status: PropertyStatus
    city: CityResponse | None
    locality: LocalityResponse | None
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class PropertyResponse(PropertySummaryResponse):
    description: str | None
    property_category_id: int | None = Field(serialization_alias="propertyCategoryId")
    property_type_id: int | None = Field(serialization_alias="propertyTypeId")
    category: PropertyCategoryResponse | None
    property_type: PropertyTypeResponse | None = Field(serialization_alias="propertyType")
    bedrooms: int | None
    bathrooms: int | None
    balconies: int | None
    furnishing_status: FurnishingStatus | None = Field(serialization_alias="furnishingStatus")
    construction_status: ConstructionStatus | None = Field(serialization_alias="constructionStatus")
    property_age_years: int | None = Field(serialization_alias="propertyAgeYears")
    floor_number: int | None = Field(serialization_alias="floorNumber")
    total_floors: int | None = Field(serialization_alias="totalFloors")
    facing: str | None
    carpet_area: Decimal | None = Field(serialization_alias="carpetArea")
    built_up_area: Decimal | None = Field(serialization_alias="builtUpArea")
    super_built_up_area: Decimal | None = Field(serialization_alias="superBuiltUpArea")
    plot_area: Decimal | None = Field(serialization_alias="plotArea")
    area_unit: AreaUnit | None = Field(serialization_alias="areaUnit")
    state: StateResponse | None
    address_line: str | None = Field(serialization_alias="addressLine")
    landmark: str | None
    pin_code: str | None = Field(serialization_alias="pinCode")
    latitude: Decimal | None
    longitude: Decimal | None
    maintenance_charge: Decimal | None = Field(serialization_alias="maintenanceCharge")
    security_deposit: Decimal | None = Field(serialization_alias="securityDeposit")
    brokerage_amount: Decimal | None = Field(serialization_alias="brokerageAmount")
    is_negotiable: bool = Field(serialization_alias="isNegotiable")
    available_from: date | None = Field(serialization_alias="availableFrom")
    possession_status: str | None = Field(serialization_alias="possessionStatus")
    rejection_reason: str | None = Field(serialization_alias="rejectionReason")
    submitted_at: datetime | None = Field(serialization_alias="submittedAt")
    approved_at: datetime | None = Field(serialization_alias="approvedAt")
    amenities: list[AmenityResponse]
