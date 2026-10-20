from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core import config
from app.core.config import Settings, get_settings


@pytest.fixture(autouse=True)
def isolate_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for name in ("DATABASE_URL", "DATABASE_PASSWORD", "PROJECT_HUB_ENV_FILE"):
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_require_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize("url", ["sqlite:///test.db", "not-a-url", "postgresql://host/db"])
def test_settings_reject_unsupported_database_url(url: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url=url)


def test_environment_controls_connection_and_hides_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "postgresql+psycopg://user:secret@localhost/db?sslmode=require"
    monkeypatch.setenv("DATABASE_URL", url)
    settings = Settings(_env_file=None)
    assert settings.database_url.get_secret_value() == url
    assert "secret" not in repr(settings)


@pytest.mark.parametrize("env_file", [".env", ".env.supabase"])
def test_explicit_environment_file_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, env_file: str
) -> None:
    local_url = "postgresql+psycopg://local:local@localhost/local"
    hosted_url = (
        "postgresql+psycopg://postgres.test@aws-test.pooler.supabase.com/postgres?sslmode=require"
    )
    (tmp_path / ".env").write_text(f"DATABASE_URL={local_url}\n")
    (tmp_path / ".env.supabase").write_text(
        f"DATABASE_URL={hosted_url}\nDATABASE_PASSWORD='hosted-test-password'\n"
    )
    monkeypatch.setattr(config, "BACKEND_DIR", tmp_path)
    if env_file == ".env.supabase":
        monkeypatch.setenv("PROJECT_HUB_ENV_FILE", env_file)
    settings = get_settings()
    assert settings.database_url.get_secret_value() == (
        local_url if env_file == ".env" else hosted_url
    )
    assert settings.connection_url().password == (
        "local" if env_file == ".env" else "hosted-test-password"
    )


def test_process_environment_overrides_selected_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".env").write_text("DATABASE_URL=postgresql+psycopg://localhost/file_db\n")
    monkeypatch.setattr(config, "BACKEND_DIR", tmp_path)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/environment_db")
    assert get_settings().connection_url().database == "environment_db"


def test_invalid_environment_file_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROJECT_HUB_ENV_FILE", "../unexpected.env")
    with pytest.raises(ValueError, match="PROJECT_HUB_ENV_FILE"):
        get_settings()


def test_separate_password_handles_url_special_characters() -> None:
    password = "test@password:/?#%$& with spaces"
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user@localhost/db",
        database_password=password,
    )
    assert settings.connection_url().password == password
    assert password not in repr(settings)
    assert password not in str(settings.connection_url())


@pytest.mark.parametrize("sslmode", [None, "disable", "allow", "prefer"])
def test_supabase_requires_encrypted_connections(sslmode: str | None) -> None:
    url = "postgresql+psycopg://postgres.test:dummy@aws-test.pooler.supabase.com/postgres"
    if sslmode:
        url += f"?sslmode={sslmode}"
    with pytest.raises(ValidationError, match="Supabase connections require"):
        Settings(_env_file=None, database_url=url)


@pytest.mark.parametrize("sslmode", ["require", "verify-ca", "verify-full"])
def test_supabase_accepts_encrypted_ssl_modes(sslmode: str) -> None:
    settings = Settings(
        _env_file=None,
        database_url=(
            "postgresql+psycopg://postgres.test@aws-test.pooler.supabase.com/postgres"
            f"?sslmode={sslmode}"
        ),
        database_password="test-password",
    )
    assert settings.connection_url().query["sslmode"] == sslmode


@pytest.mark.parametrize("password", [None, "", "[YOUR-PASSWORD]"])
def test_supabase_missing_password_fails_before_connecting(password: str | None) -> None:
    settings = Settings(
        _env_file=None,
        database_url=(
            "postgresql+psycopg://postgres.test@aws-test.pooler.supabase.com/postgres"
            "?sslmode=require"
        ),
        database_password=password,
    )
    with pytest.raises(ValueError, match="DATABASE_PASSWORD"):
        settings.connection_url()


@pytest.mark.parametrize(
    "url",
    [
        "http://project.supabase.co",
        "https://project.supabase.co/path",
        "https://user:secret@project.supabase.co",
        "https://project.supabase.co?redirect=elsewhere",
    ],
)
def test_auth_project_url_must_be_https_origin(url: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="postgresql+psycopg://localhost/db", supabase_url=url)
