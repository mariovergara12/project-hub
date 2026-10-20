from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.core import security
from app.core.config import Settings
from app.main import create_app
from app.modules.auth.verifier import Identity, IdentityProviderUnavailable


def test_missing_auth_configuration_fails_closed(monkeypatch: MonkeyPatch) -> None:
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://localhost/unused")
    monkeypatch.setattr(security, "get_settings", lambda: settings)
    security.get_token_verifier.cache_clear()
    try:
        with TestClient(create_app()) as client:
            assert client.get("/health").status_code == 200
            assert client.get("/me").status_code == 401
            response = client.get("/me", headers={"Authorization": "Bearer some-token"})
            assert response.status_code == 503
    finally:
        security.get_token_verifier.cache_clear()


def test_auth_provider_failure_is_unavailable_not_anonymous(monkeypatch: MonkeyPatch) -> None:
    class UnavailableVerifier:
        def verify(self, token: str) -> Identity:
            raise IdentityProviderUnavailable

    monkeypatch.setattr(security, "get_token_verifier", lambda: UnavailableVerifier())
    with TestClient(create_app()) as client:
        response = client.get("/me", headers={"Authorization": "Bearer some-token"})
        assert response.status_code == 503
        assert response.json() == {"detail": "Identity provider is unavailable"}
