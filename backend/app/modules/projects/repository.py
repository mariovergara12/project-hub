from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    Interest,
    Membership,
    Project,
    ProjectInterest,
    ProjectSkill,
    Skill,
    User,
)
from app.models.enums import ProjectStatus, ProjectType


def visible_projects(user_id: UUID) -> Select:
    member_counts = (
        select(Membership.project_id, func.count().label("member_count"))
        .group_by(Membership.project_id)
        .subquery()
    )
    return (
        select(Project, func.coalesce(member_counts.c.member_count, 0))
        .outerjoin(member_counts, member_counts.c.project_id == Project.id)
        .where(
            or_(
                Project.status == ProjectStatus.OPEN,
                Project.owner_id == user_id,
                Project.memberships.any(Membership.user_id == user_id),
            )
        )
        .options(
            joinedload(Project.owner).joinedload(User.profile),
            selectinload(Project.skills).joinedload(ProjectSkill.skill),
            selectinload(Project.interests).joinedload(ProjectInterest.interest),
        )
    )


def list_projects(
    session: Session,
    user_id: UUID,
    *,
    limit: int,
    cursor: UUID | None,
    q: str | None,
    project_type: ProjectType | None,
    status: ProjectStatus | None,
    skill_id: UUID | None,
    interest_id: UUID | None,
) -> list:
    query = visible_projects(user_id)
    if cursor is not None:
        query = query.where(Project.id > cursor)
    if q:
        query = query.where(
            or_(
                Project.title.icontains(q, autoescape=True),
                Project.description.icontains(q, autoescape=True),
            )
        )
    if project_type is not None:
        query = query.where(Project.project_type == project_type)
    if status is not None:
        query = query.where(Project.status == status)
    if skill_id is not None:
        query = query.where(Project.skills.any(ProjectSkill.skill_id == skill_id))
    if interest_id is not None:
        query = query.where(Project.interests.any(ProjectInterest.interest_id == interest_id))
    return list(session.execute(query.order_by(Project.id).limit(limit + 1)))


def get_project(session: Session, user_id: UUID, project_id: UUID):
    return session.execute(visible_projects(user_id).where(Project.id == project_id)).one_or_none()


def list_catalog(
    session: Session, model: type[Skill] | type[Interest], *, limit: int, cursor: UUID | None
) -> list:
    query = select(model).order_by(model.id).limit(limit + 1)
    if cursor is not None:
        query = query.where(model.id > cursor)
    return list(session.scalars(query))
