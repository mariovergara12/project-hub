import pytest
from pydantic import ValidationError

from app.core.config import Settings


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
