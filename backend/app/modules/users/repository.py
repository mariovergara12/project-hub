from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy import insert as insert_rows
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload

from app.models import Interest, Skill, User, UserInterest, UserSkill


def get_or_create_user(
    session: Session, user_id: UUID, *, include_selections: bool = False
) -> User:
    # Only the verified subject and the database's default student role are used.
    # ON CONFLICT handles simultaneous first requests without duplicate accounts.
    session.execute(
        insert(User).values(id=user_id).on_conflict_do_nothing(index_elements=[User.id])
    )
    query = select(User).where(User.id == user_id).options(selectinload(User.profile))
    if include_selections:
        query = query.options(
            selectinload(User.skills).joinedload(UserSkill.skill),
            selectinload(User.interests).joinedload(UserInterest.interest),
        )
    return session.scalars(query.with_for_update()).one()


def catalog_items(
    session: Session, model: type[Skill] | type[Interest], ids: list[UUID]
) -> list[Skill] | list[Interest]:
    # Prevent a concurrent catalog deletion between validation and link insertion.
    return list(
        session.scalars(
            select(model)
            .where(model.id.in_(ids))
            .order_by(model.id)
            .with_for_update(read=True, key_share=True)
        )
    )


def replace_links(session: Session, user_id: UUID, ids: list[UUID], *, skills: bool) -> None:
    model, column = (UserSkill, "skill_id") if skills else (UserInterest, "interest_id")
    session.execute(delete(model).where(model.user_id == user_id))
    if ids:
        session.execute(insert_rows(model), [{"user_id": user_id, column: id_} for id_ in ids])
