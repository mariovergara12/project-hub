"""HTTP authentication boundary. Services receive only the verified user's UUID."""

from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.modules.auth.verifier import (
    IdentityProviderUnavailable,
    InvalidAccessToken,
    SupabaseTokenVerifier,
)

bearer = HTTPBearer(auto_error=False)


@lru_cache
def get_token_verifier() -> SupabaseTokenVerifier:
    url = get_settings().supabase_url
    if url is None:
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    return SupabaseTokenVerifier(str(url))


def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> UUID:
    unauthorized = HTTPException(
        status_code=401,
        detail="Invalid or missing access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        return get_token_verifier().verify(credentials.credentials).user_id
    except InvalidAccessToken:
        raise unauthorized from None
    except IdentityProviderUnavailable:
        raise HTTPException(status_code=503, detail="Identity provider is unavailable") from None


CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
