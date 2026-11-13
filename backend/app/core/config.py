import os
from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    app_name: str = "Project Hub API"
    database_url: SecretStr
    database_password: SecretStr | None = None
    database_pool_size: int = Field(default=5, ge=1)
    database_max_overflow: int = Field(default=5, ge=0)
    supabase_url: AnyHttpUrl | None = None
    cors_origins: list[str] = Field(default_factory=list)

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            url = AnyHttpUrl(origin)
            if (
                origin != str(url).rstrip("/")
                or url.path not in (None, "/")
                or url.query
                or url.fragment
                or url.username
                or url.password
            ):
                raise ValueError(
                    "CORS_ORIGINS must contain HTTP origins without paths or credentials"
                )
        return list(dict.fromkeys(origins))

    @field_validator("supabase_url")
    @classmethod
    def validate_supabase_url(cls, value: AnyHttpUrl | None) -> AnyHttpUrl | None:
        if value is not None and (
            value.scheme != "https"
            or value.path not in (None, "/")
            or value.query
            or value.fragment
            or value.username
            or value.password
        ):
            raise ValueError("SUPABASE_URL must be an HTTPS project origin without credentials")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
        except ArgumentError:
            raise ValueError("DATABASE_URL must be a valid PostgreSQL URL") from None
        if url.drivername != "postgresql+psycopg" or not url.database:
            raise ValueError("DATABASE_URL must use postgresql+psycopg and name a database")
        if is_supabase_host(url.host) and url.query.get("sslmode") not in {
            "require",
            "verify-ca",
            "verify-full",
        }:
            raise ValueError(
                "Supabase connections require sslmode=require or certificate verification"
            )
        return value

    def connection_url(self) -> URL:
        """Build the URL without requiring URL-encoding of a separate password."""
        url = make_url(self.database_url.get_secret_value())
        if self.database_password is not None:
            url = url.set(password=self.database_password.get_secret_value())
        if is_supabase_host(url.host) and (not url.password or url.password == "[YOUR-PASSWORD]"):
            raise ValueError("Set the real DATABASE_PASSWORD in the private .env.supabase file")
        return url


def is_supabase_host(host: str | None) -> bool:
    return bool(host and host.endswith((".supabase.com", ".supabase.co")))


@lru_cache
def get_settings() -> Settings:
    env_file = os.environ.get("PROJECT_HUB_ENV_FILE", ".env")
    if env_file not in {".env", ".env.supabase"}:
        raise ValueError("PROJECT_HUB_ENV_FILE must be .env or .env.supabase")
    return Settings(_env_file=BACKEND_DIR / env_file)
