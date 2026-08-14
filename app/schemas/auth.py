from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.schemas.user import UserResponse

PublicRole = Literal["USER", "OWNER", "AGENT", "BUILDER"]


class RegistrationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    full_name: str = Field(alias="fullName", min_length=2, max_length=120)
    email: EmailStr
    mobile_number: str | None = Field(
        default=None, alias="mobileNumber", pattern=r"^(?:\+91)?[6-9]\d{9}$"
    )
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(alias="confirmPassword", min_length=8, max_length=128)
    user_type: PublicRole = Field(alias="userType")

    @field_validator("full_name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Full name cannot be blank")
        return value

    @model_validator(mode="after")
    def passwords_match(self) -> "RegistrationRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    refresh_token: str = Field(alias="refreshToken", min_length=1)


class LogoutRequest(RefreshRequest):
    pass


class TokenResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    access_token: str = Field(serialization_alias="accessToken")
    refresh_token: str = Field(serialization_alias="refreshToken")
    token_type: Literal["bearer"] = Field(default="bearer", serialization_alias="tokenType")
    expires_in: int = Field(serialization_alias="expiresIn")
    user: UserResponse


class MessageResponse(BaseModel):
    message: str
