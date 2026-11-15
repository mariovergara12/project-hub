from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.responses import AUTH_ERROR_RESPONSES, ProfileValidationErrorResponse
from app.core.security import CurrentUserId
from app.modules.users import service
from app.modules.users.schemas import MeResponse, ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/me", tags=["profile"], responses=AUTH_ERROR_RESPONSES)
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.get("", response_model=MeResponse)
def read_me(user_id: CurrentUserId, session: DatabaseSession) -> MeResponse:
    """Return the current account; profile is null until created with PATCH /me/profile."""
    try:
        return MeResponse.model_validate(service.read_me(session, user_id))
    except service.IdentityNoLongerExists:
        raise HTTPException(status_code=401, detail="Account no longer exists") from None


@router.patch(
    "/profile",
    response_model=ProfileResponse,
    responses={
        422: {
            "model": ProfileValidationErrorResponse,
            "description": (
                "Invalid fields (detail is a list), or a new profile is missing display_name "
                "(detail is a string)."
            ),
        }
    },
)
def update_my_profile(
    changes: ProfileUpdate, user_id: CurrentUserId, session: DatabaseSession
) -> ProfileResponse:
    """Create or partially update only the current user's profile.

    Omitted fields stay unchanged. Explicit null clears optional fields, but
    display_name cannot be null and is required when creating a profile.
    Role, faculty verification, user_id, skills, and interests are not editable here.
    """
    try:
        return ProfileResponse.model_validate(service.update_my_profile(session, user_id, changes))
    except service.IdentityNoLongerExists:
        raise HTTPException(status_code=401, detail="Account no longer exists") from None
    except service.DisplayNameRequired:
        raise HTTPException(
            status_code=422, detail="display_name is required to create a profile"
        ) from None
