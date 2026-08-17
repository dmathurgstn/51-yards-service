from pydantic import BaseModel, ConfigDict, Field


class MasterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: int
    name: str


class StateResponse(MasterResponse):
    code: str


class CityResponse(MasterResponse):
    state_id: int = Field(serialization_alias="stateId")
    slug: str


class LocalityResponse(MasterResponse):
    city_id: int = Field(serialization_alias="cityId")
    slug: str
    pin_code: str | None = Field(serialization_alias="pinCode")


class PropertyCategoryResponse(MasterResponse):
    code: str
    description: str | None


class PropertyTypeResponse(PropertyCategoryResponse):
    category_id: int = Field(serialization_alias="categoryId")


class AmenityResponse(MasterResponse):
    code: str
    icon_key: str | None = Field(serialization_alias="iconKey")
    category: str | None
