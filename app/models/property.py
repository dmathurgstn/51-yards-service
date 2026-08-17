from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.master_data import Amenity, PropertyCategory, PropertyType
    from app.models.user import User


class ListingPurpose(StrEnum):
    SELL = "SELL"
    RENT = "RENT"
    LEASE = "LEASE"


class PropertyStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    PAUSED = "PAUSED"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"


class AreaUnit(StrEnum):
    SQ_FT = "SQ_FT"
    SQ_YARD = "SQ_YARD"
    SQ_METER = "SQ_METER"
    ACRE = "ACRE"


class FurnishingStatus(StrEnum):
    UNFURNISHED = "UNFURNISHED"
    SEMI_FURNISHED = "SEMI_FURNISHED"
    FULLY_FURNISHED = "FULLY_FURNISHED"


class ConstructionStatus(StrEnum):
    READY_TO_MOVE = "READY_TO_MOVE"
    UNDER_CONSTRUCTION = "UNDER_CONSTRUCTION"
    NEW_LAUNCH = "NEW_LAUNCH"


class Property(Base):
    """Core row in the existing normalized property aggregate."""

    __tablename__ = "properties"
    __table_args__ = (Index("ix_properties_owner_status", "user_id", "status"),)
    id: Mapped[int] = mapped_column("property_id", primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, default=lambda: str(uuid4())
    )
    owner_user_id: Mapped[int] = mapped_column("user_id", ForeignKey("users.user_id"), index=True)
    listing_purpose: Mapped[str] = mapped_column("transaction_type", String(16))
    legacy_category: Mapped[str | None] = mapped_column("property_category", String(20))
    legacy_property_type: Mapped[str] = mapped_column("property_type", String(100), default="")
    property_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("property_categories.id"), index=True
    )
    property_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("property_types.id"), index=True
    )
    configuration: Mapped[str | None] = mapped_column(String(50))
    ownership_type: Mapped[str | None] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    area_type: Mapped[str | None] = mapped_column(String(24))
    area_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    area_unit: Mapped[str | None] = mapped_column(String(16))
    bedrooms: Mapped[int | None]
    bathrooms: Mapped[int | None]
    balconies: Mapped[int | None]
    furnishing_status: Mapped[str | None] = mapped_column(String(65))
    construction_status: Mapped[str | None] = mapped_column(String(24))
    facing: Mapped[str | None] = mapped_column(String(50))
    property_age_years: Mapped[int | None] = mapped_column("property_age")
    floor_number: Mapped[int | None]
    total_floors: Mapped[int | None]
    status: Mapped[str] = mapped_column(String(24), default=PropertyStatus.DRAFT.value, index=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    owner: Mapped["User"] = relationship()
    category: Mapped["PropertyCategory | None"] = relationship()
    property_type: Mapped["PropertyType | None"] = relationship()
    location: Mapped["PropertyLocation | None"] = relationship(
        back_populates="property", cascade="all, delete-orphan", uselist=False
    )
    sell_details: Mapped["PropertySellDetails | None"] = relationship(
        back_populates="property", cascade="all, delete-orphan", uselist=False
    )
    rent_details: Mapped["PropertyRentDetails | None"] = relationship(
        back_populates="property", cascade="all, delete-orphan", uselist=False
    )
    lease_details: Mapped["PropertyLeaseDetails | None"] = relationship(
        back_populates="property", cascade="all, delete-orphan", uselist=False
    )
    amenities: Mapped[list["Amenity"]] = relationship(
        secondary="property_amenities", back_populates="properties", lazy="selectin"
    )
    status_history: Mapped[list["PropertyStatusHistory"]] = relationship(
        back_populates="property", cascade="all, delete-orphan"
    )


class PropertyLocation(Base):
    __tablename__ = "property_location"
    id: Mapped[int] = mapped_column("location_id", primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.property_id", ondelete="CASCADE"), unique=True
    )
    address_line: Mapped[str | None] = mapped_column("address_line1", String(255))
    address_line2: Mapped[str | None] = mapped_column(String(255))
    locality_society: Mapped[str | None] = mapped_column(String(255))
    landmark: Mapped[str | None] = mapped_column(String(255))
    legacy_city: Mapped[str | None] = mapped_column("city", String(100))
    legacy_state: Mapped[str | None] = mapped_column("state", String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    pin_code: Mapped[str | None] = mapped_column("pincode", String(10))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    state_id: Mapped[int | None] = mapped_column(ForeignKey("states.id"), index=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), index=True)
    locality_id: Mapped[int | None] = mapped_column(ForeignKey("localities.id"), index=True)
    property: Mapped[Property] = relationship(back_populates="location")


class PropertySellDetails(Base):
    __tablename__ = "property_sell_details"
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.property_id", ondelete="CASCADE"), primary_key=True
    )
    price: Mapped[Decimal | None] = mapped_column("expected_price", Numeric(16, 2))
    is_negotiable: Mapped[bool | None] = mapped_column("negotiable", Boolean)
    possession_date: Mapped[date | None] = mapped_column(Date)
    maintenance_charge: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    brokerage_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    property: Mapped[Property] = relationship(back_populates="sell_details")


class PropertyRentDetails(Base):
    __tablename__ = "property_rent_details"
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.property_id", ondelete="CASCADE"), primary_key=True
    )
    price: Mapped[Decimal | None] = mapped_column("monthly_rent", Numeric(16, 2))
    security_deposit: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    available_from: Mapped[date | None] = mapped_column(Date)
    is_negotiable: Mapped[bool | None] = mapped_column(Boolean)
    maintenance_charge: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    brokerage_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    property: Mapped[Property] = relationship(back_populates="rent_details")


class PropertyLeaseDetails(Base):
    __tablename__ = "property_lease_details"
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.property_id", ondelete="CASCADE"), primary_key=True
    )
    price: Mapped[Decimal | None] = mapped_column("lease_amount", Numeric(16, 2))
    lease_tenure: Mapped[str | None] = mapped_column(String(50))
    lock_in_period: Mapped[str | None] = mapped_column(String(50))
    available_from: Mapped[date | None] = mapped_column(Date)
    security_deposit: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    is_negotiable: Mapped[bool | None] = mapped_column(Boolean)
    maintenance_charge: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    brokerage_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    property: Mapped[Property] = relationship(back_populates="lease_details")


class PropertyAmenity(Base):
    __tablename__ = "property_amenities"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.property_id", ondelete="CASCADE")
    )
    amenity_id: Mapped[int] = mapped_column(
        ForeignKey("amenities_master.amenity_id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PropertyStatusHistory(Base):
    __tablename__ = "property_status_history"
    id: Mapped[int] = mapped_column("history_id", primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.property_id", ondelete="CASCADE"), index=True
    )
    old_status: Mapped[str | None] = mapped_column(String(50))
    new_status: Mapped[str] = mapped_column(String(50))
    changed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), index=True
    )
    reason: Mapped[str | None] = mapped_column("remarks", Text)
    created_at: Mapped[datetime] = mapped_column(
        "changed_at", DateTime(timezone=True), default=utc_now, index=True
    )
    property: Mapped[Property] = relationship(back_populates="status_history")
