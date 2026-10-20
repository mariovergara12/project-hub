from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload

from app.models import User


def get_or_create_user(session: Session, user_id: UUID) -> User:
    # Only the verified subject and the database's default student role are used.
    # ON CONFLICT handles simultaneous first requests without duplicate accounts.
    session.execute(
        insert(User).values(id=user_id).on_conflict_do_nothing(index_elements=[User.id])
    )
    return session.scalars(
        select(User).where(User.id == user_id).options(selectinload(User.profile)).with_for_update()
    ).one()
