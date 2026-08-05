from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

EnvironmentName = Literal["development", "testing", "staging", "production"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="YARDS_",
        case_sensitive=False,
        extra="ignore",
    )

    application_name: str = Field(min_length=1)
    application_version: str = "1.0.0"
    environment: EnvironmentName = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    frontend_origins: list[str] = Field(default_factory=lambda: ["http://localhost:4200"])
    database_url: str = Field(min_length=1)
    database_echo: bool = False
    log_level: str = "INFO"

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        normalized = value.rstrip("/")
        if not normalized.startswith("/") or " " in normalized:
            raise ValueError("API prefix must begin with '/' and contain no spaces")
        return normalized

    @field_validator("frontend_origins")
    @classmethod
    def validate_origins(cls, origins: list[str]) -> list[str]:
        if not origins:
            raise ValueError("At least one frontend origin is required")
        for origin in origins:
            parsed = urlparse(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path not in {"", "/"}
            ):
                raise ValueError(f"Invalid CORS origin: {origin}")
        return [origin.rstrip("/") for origin in origins]

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith("mysql+pymysql://"):
            raise ValueError("DATABASE_URL must use the mysql+pymysql driver")
        return value

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Unsupported log level")
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
