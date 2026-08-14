from pydantic import BaseModel, ConfigDict, Field


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str = Field(validation_alias="public_id", serialization_alias="id")
    full_name: str = Field(serialization_alias="fullName")
    email: str
    mobile_number: str | None = Field(serialization_alias="mobileNumber")
    is_active: bool = Field(serialization_alias="isActive")
    is_verified: bool = Field(serialization_alias="isVerified")
    roles: list[str]
