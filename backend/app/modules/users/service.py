from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Interest, Profile, Skill, User
from app.modules.projects.schemas import CatalogItem
from app.modules.users import repository
from app.modules.users.schemas import MeResponse, ProfileResponse, ProfileUpdate


class IdentityNoLongerExists(Exception):
    pass


class DisplayNameRequired(Exception):
    pass


class UnknownCatalogIds(Exception):
    pass


def is_missing_auth_identity(exc: IntegrityError) -> bool:
    return (
        getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        == "fk_users_id_auth_users"
    )


def read_me(session: Session, user_id: UUID, *, include_selections: bool = True) -> User:
    try:
        with session.begin():
            return repository.get_or_create_user(
                session, user_id, include_selections=include_selections
            )
    except IntegrityError as exc:
        if is_missing_auth_identity(exc):
            raise IdentityNoLongerExists from None
        raise


def update_my_profile(session: Session, user_id: UUID, changes: ProfileUpdate) -> Profile:
    try:
        with session.begin():
            user = repository.get_or_create_user(session, user_id)
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


def me_response(user: User) -> MeResponse:
    return MeResponse(
        id=user.id,
        role=user.role,
        faculty_verified_at=user.faculty_verified_at,
        profile=ProfileResponse.model_validate(user.profile) if user.profile else None,
        skills=[
            CatalogItem.model_validate(link.skill)
            for link in sorted(user.skills, key=lambda link: link.skill.name)
        ],
        interests=[
            CatalogItem.model_validate(link.interest)
            for link in sorted(user.interests, key=lambda link: link.interest.name)
        ],
    )


def replace_selections(
    session: Session, user_id: UUID, ids: list[UUID], *, skills: bool
) -> list[CatalogItem]:
    try:
        with session.begin():
            # All profile/selection/operator writes lock the user first.
            repository.get_or_create_user(session, user_id)
            rows = repository.catalog_items(session, Skill if skills else Interest, ids)
            if len(rows) != len(ids):
                raise UnknownCatalogIds
            repository.replace_links(session, user_id, ids, skills=skills)
            session.flush()
            return [
                CatalogItem.model_validate(row) for row in sorted(rows, key=lambda row: row.name)
            ]
    except IntegrityError as exc:
        if is_missing_auth_identity(exc):
            raise IdentityNoLongerExists from None
        raise
