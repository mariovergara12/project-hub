from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Profile, User
from app.modules.users.repository import get_or_create_user
from app.modules.users.schemas import ProfileUpdate


class IdentityNoLongerExists(Exception):
    pass


class DisplayNameRequired(Exception):
    pass


def is_missing_auth_identity(exc: IntegrityError) -> bool:
    return (
        getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        == "fk_users_id_auth_users"
    )


def read_me(session: Session, user_id: UUID) -> User:
    try:
        with session.begin():
            return get_or_create_user(session, user_id)
    except IntegrityError as exc:
        if is_missing_auth_identity(exc):
            raise IdentityNoLongerExists from None
        raise


def update_my_profile(session: Session, user_id: UUID, changes: ProfileUpdate) -> Profile:
    try:
        with session.begin():
            user = get_or_create_user(session, user_id)
            values = changes.model_dump(exclude_unset=True)
            if user.profile is None:
                if "display_name" not in values:
                    raise DisplayNameRequired
                user.profile = Profile(user_id=user_id, **values)
            else:
                for name, value in values.items():
                    setattr(user.profile, name, value)
            session.flush()
            return user.profile
    except IntegrityError as exc:
        if is_missing_auth_identity(exc):
            raise IdentityNoLongerExists from None
        raise
