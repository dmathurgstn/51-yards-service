"""SQLAlchemy model registry used by Alembic metadata discovery."""

from app.models.master_data import Amenity, City, Locality, PropertyCategory, PropertyType, State
from app.models.property import (
    Property,
    PropertyAmenity,
    PropertyLeaseDetails,
    PropertyLocation,
    PropertyRentDetails,
    PropertySellDetails,
    PropertyStatusHistory,
)
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole

__all__ = [
    "Amenity",
    "City",
    "Locality",
    "Property",
    "PropertyAmenity",
    "PropertyLeaseDetails",
    "PropertyLocation",
    "PropertyRentDetails",
    "PropertySellDetails",
    "PropertyCategory",
    "PropertyStatusHistory",
    "PropertyType",
    "RefreshToken",
    "Role",
    "State",
    "User",
    "UserRole",
]
