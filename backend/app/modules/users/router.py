from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.responses import AUTH_ERROR_RESPONSES, ProfileValidationErrorResponse
from app.core.security import CurrentUserId
from app.modules.users import service
from app.modules.users.schemas import (
    InterestSelectionUpdate,
    InterestsResponse,
    MeResponse,
    ProfileResponse,
    ProfileUpdate,
    SkillSelectionUpdate,
    SkillsResponse,
)

router = APIRouter(prefix="/me", tags=["profile"], responses=AUTH_ERROR_RESPONSES)
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.get("", response_model=MeResponse)
def read_me(user_id: CurrentUserId, session: DatabaseSession) -> MeResponse:
    """Return the current account; profile is null until created with PATCH /me/profile."""
    try:
        return service.me_response(service.read_me(session, user_id))
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


SELECTION_ERRORS = {
    422: {
        "model": ProfileValidationErrorResponse,
        "description": "Invalid, duplicate, or unknown catalog IDs; at most 50 selections.",
    }
}


@router.put("/skills", response_model=SkillsResponse, responses=SELECTION_ERRORS)
def replace_my_skills(
    changes: SkillSelectionUpdate, user_id: CurrentUserId, session: DatabaseSession
) -> SkillsResponse:
    """Replace your skills atomically with up to 50 unique catalog IDs; [] clears them."""
    try:
        return SkillsResponse(
            skills=service.replace_selections(session, user_id, changes.skill_ids, skills=True)
        )
    except service.IdentityNoLongerExists:
        raise HTTPException(status_code=401, detail="Account no longer exists") from None
    except service.UnknownCatalogIds:
        raise HTTPException(status_code=422, detail="Unknown skill IDs") from None


@router.put("/interests", response_model=InterestsResponse, responses=SELECTION_ERRORS)
def replace_my_interests(
    changes: InterestSelectionUpdate, user_id: CurrentUserId, session: DatabaseSession
) -> InterestsResponse:
    """Replace your interests atomically with up to 50 unique catalog IDs; [] clears them."""
    try:
        return InterestsResponse(
            interests=service.replace_selections(
                session, user_id, changes.interest_ids, skills=False
            )
        )
    except service.IdentityNoLongerExists:
        raise HTTPException(status_code=401, detail="Account no longer exists") from None
    except service.UnknownCatalogIds:
        raise HTTPException(status_code=422, detail="Unknown interest IDs") from None
