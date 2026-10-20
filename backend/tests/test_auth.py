from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

from app.modules.auth.verifier import (
    IdentityProviderUnavailable,
    InvalidAccessToken,
    SupabaseTokenVerifier,
)

PROJECT_URL = "https://test-project.supabase.co"


@pytest.fixture
def signing_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


def claims_for(user_id: UUID | None = None) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "sub": str(user_id or uuid4()),
        "session_id": str(uuid4()),
        "iss": PROJECT_URL + "/auth/v1",
        "aud": "authenticated",
        "role": "authenticated",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "is_anonymous": False,
    }


def sign_token(key: ec.EllipticCurvePrivateKey, claims: dict[str, Any]) -> str:
    return jwt.encode(claims, key, algorithm="ES256", headers={"kid": "test-key"})


@pytest.fixture
def verifier(
    signing_key: ec.EllipticCurvePrivateKey, monkeypatch: pytest.MonkeyPatch
) -> SupabaseTokenVerifier:
    verifier = SupabaseTokenVerifier(PROJECT_URL)
    monkeypatch.setattr(
        verifier.jwks,
        "get_signing_key_from_jwt",
        lambda token: SimpleNamespace(key=signing_key.public_key()),
    )
    return verifier


def test_valid_signed_token(
    verifier: SupabaseTokenVerifier, signing_key: ec.EllipticCurvePrivateKey
) -> None:
    claims = claims_for()
    assert str(verifier.verify(sign_token(signing_key, claims)).user_id) == claims["sub"]


@pytest.mark.parametrize(
    "change",
    [
        {"exp": 1},
        {"iat": 4102444800},
        {"iss": "https://other.supabase.co/auth/v1"},
        {"aud": "other-app"},
        {"aud": ["authenticated", "other-app"]},
        {"role": "service_role"},
        {"role": "anon"},
        {"is_anonymous": True},
        {"sub": "not-a-uuid"},
        {"session_id": "not-a-uuid"},
        {"session_id": 123},
        {"session_id": []},
        {"sub": None},
    ],
)
def test_invalid_claims_rejected(
    verifier: SupabaseTokenVerifier, signing_key: ec.EllipticCurvePrivateKey, change: dict
) -> None:
    claims = claims_for() | change
    with pytest.raises(InvalidAccessToken):
        verifier.verify(sign_token(signing_key, claims))


@pytest.mark.parametrize("missing", ["exp", "iat", "iss", "aud", "sub", "role", "session_id"])
def test_required_claims(
    verifier: SupabaseTokenVerifier, signing_key: ec.EllipticCurvePrivateKey, missing: str
) -> None:
    claims = claims_for()
    claims.pop(missing)
    with pytest.raises(InvalidAccessToken):
        verifier.verify(sign_token(signing_key, claims))


def test_wrong_signature_rejected(verifier: SupabaseTokenVerifier) -> None:
    other_key = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(InvalidAccessToken):
        verifier.verify(sign_token(other_key, claims_for()))


@pytest.mark.parametrize("token", ["", "not-a-jwt", "x" * 16385])
def test_malformed_token(verifier: SupabaseTokenVerifier, token: str) -> None:
    with pytest.raises(InvalidAccessToken):
        verifier.verify(token)


@pytest.mark.parametrize("algorithm", ["none", "HS256"])
def test_unapproved_algorithm_rejected_before_key_fetch(
    verifier: SupabaseTokenVerifier, algorithm: str
) -> None:
    token = jwt.encode(
        claims_for(),
        "test-secret" * 4 if algorithm == "HS256" else None,
        algorithm=algorithm,
        headers={"kid": "test-key"},
    )
    with pytest.raises(InvalidAccessToken):
        verifier.verify(token)


def test_missing_kid(
    verifier: SupabaseTokenVerifier, signing_key: ec.EllipticCurvePrivateKey
) -> None:
    token = jwt.encode(claims_for(), signing_key, algorithm="ES256")
    with pytest.raises(InvalidAccessToken):
        verifier.verify(token)


@pytest.mark.parametrize("error", [PyJWKClientError, PyJWKClientConnectionError])
def test_key_lookup_failure(
    verifier: SupabaseTokenVerifier,
    signing_key: ec.EllipticCurvePrivateKey,
    monkeypatch: pytest.MonkeyPatch,
    error: type[PyJWKClientError],
) -> None:
    def fail(token: str) -> None:
        raise error("unavailable")

    monkeypatch.setattr(verifier.jwks, "get_signing_key_from_jwt", fail)
    expected = (
        IdentityProviderUnavailable if error is PyJWKClientConnectionError else InvalidAccessToken
    )
    with pytest.raises(expected):
        verifier.verify(sign_token(signing_key, claims_for()))
