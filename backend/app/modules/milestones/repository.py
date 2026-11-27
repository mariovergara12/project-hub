from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Membership, Milestone, Project
from app.models.enums import MilestoneStatus


def project(session: Session, project_id: UUID, *, write: bool) -> Project | None:
    return session.scalar(
        select(Project).where(Project.id == project_id).with_for_update(read=not write)
    )


def project_hint(session: Session, user_id: UUID, milestone_id: UUID) -> UUID | None:
    return session.scalar(
        select(Milestone.project_id)
        .join(Project)
        .where(
            Milestone.id == milestone_id,
            or_(
                Project.owner_id == user_id, Project.memberships.any(Membership.user_id == user_id)
            ),
        )
    )


def milestone(session: Session, project_id: UUID, milestone_id: UUID) -> Milestone | None:
    return session.scalar(
        select(Milestone)
        .where(Milestone.id == milestone_id, Milestone.project_id == project_id)
        .with_for_update()
    )


def list_milestones(
    session: Session,
    project_id: UUID,
    *,
    limit: int,
    cursor: UUID | None,
    status: MilestoneStatus | None,
):
    query = select(Milestone).where(Milestone.project_id == project_id)
    if cursor is not None:
        query = query.where(Milestone.id > cursor)
    if status is not None:
        query = query.where(Milestone.status == status)
    return list(session.scalars(query.order_by(Milestone.id).limit(limit + 1)))


def progress(session: Session, project_id: UUID):
    return dict(
        session.execute(
            select(Milestone.status, func.count())
            .where(Milestone.project_id == project_id)
            .group_by(Milestone.status)
        ).all()
    )
