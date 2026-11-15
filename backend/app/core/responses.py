"""Document existing HTTP errors without changing their runtime payloads."""

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str


class ProfileValidationErrorResponse(BaseModel):
    detail: str | list[dict[str, Any]]


AUTH_ERROR_RESPONSES = {
    401: {
        "model": ErrorResponse,
        "description": "Missing/invalid/expired access token, or deleted Auth account.",
    },
    503: {
        "model": ErrorResponse,
        "description": "Authentication is not configured or the identity provider is unavailable.",
    },
}
