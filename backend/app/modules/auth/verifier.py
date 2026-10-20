"""Verify provider-issued access tokens; never mint tokens or handle passwords."""

from dataclasses import dataclass
from uuid import UUID

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWTError


class InvalidAccessToken(Exception):
    pass


class IdentityProviderUnavailable(Exception):
    pass


@dataclass(frozen=True)
class Identity:
    user_id: UUID


class SupabaseTokenVerifier:
    def __init__(self, project_url: str) -> None:
        self.issuer = project_url.rstrip("/") + "/auth/v1"
        self.jwks = PyJWKClient(self.issuer + "/.well-known/jwks.json", lifespan=300, timeout=5)

    def verify(self, token: str) -> Identity:
        try:
            if len(token) > 16384:
                raise InvalidAccessToken
            header = jwt.get_unverified_header(token)
            if (
                header.get("alg") not in {"ES256", "RS256"}
                or not isinstance(header.get("kid"), str)
                or not header["kid"]
            ):
                raise InvalidAccessToken
            key = self.jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                key.key,
                algorithms=["ES256", "RS256"],
                issuer=self.issuer,
                audience="authenticated",
                options={
                    "require": ["exp", "iat", "iss", "aud", "sub", "role", "session_id"],
                    "strict_aud": True,
                },
            )
            if claims["role"] != "authenticated" or claims.get("is_anonymous", False) is not False:
                raise InvalidAccessToken
            if not isinstance(claims["sub"], str) or not isinstance(claims["session_id"], str):
                raise InvalidAccessToken
            # No application permissions are taken from JWT role or user_metadata.
            UUID(claims["session_id"])
            return Identity(user_id=UUID(claims["sub"]))
        except PyJWKClientConnectionError:
            raise IdentityProviderUnavailable from None
        except (PyJWTError, ValueError, TypeError, KeyError):
            raise InvalidAccessToken from None
