from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.security import CurrentUserId
from app.modules.users import service
from app.modules.users.schemas import MeResponse, ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/me", tags=["profile"])
DatabaseSession = Annotated[Session, Depends(get_session)]


@router.get("", response_model=MeResponse)
def read_me(user_id: CurrentUserId, session: DatabaseSession) -> MeResponse:
    try:
        return MeResponse.model_validate(service.read_me(session, user_id))
    except service.IdentityNoLongerExists:
        raise HTTPException(status_code=401, detail="Account no longer exists") from None


@router.patch("/profile", response_model=ProfileResponse)
def update_my_profile(
    changes: ProfileUpdate, user_id: CurrentUserId, session: DatabaseSession
) -> ProfileResponse:
    try:
        return ProfileResponse.model_validate(service.update_my_profile(session, user_id, changes))
    except service.IdentityNoLongerExists:
        raise HTTPException(status_code=401, detail="Account no longer exists") from None
    except service.DisplayNameRequired:
        raise HTTPException(
            status_code=422, detail="display_name is required to create a profile"
        ) from None
