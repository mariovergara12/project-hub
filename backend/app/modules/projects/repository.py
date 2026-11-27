from uuid import UUID

from sqlalchemy import Select, delete, func, insert, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    Application,
    Interest,
    Membership,
    Project,
    ProjectInterest,
    ProjectSkill,
    Skill,
    User,
)
from app.models.enums import ApplicationStatus, ProjectStatus, ProjectType
from app.modules.projects.schemas import ProjectSkillInput


def visibility_filter(user_id: UUID):
    return or_(
        Project.status == ProjectStatus.OPEN,
        Project.owner_id == user_id,
        Project.memberships.any(Membership.user_id == user_id),
    )


def visible_projects(user_id: UUID) -> Select:
    member_counts = (
        select(Membership.project_id, func.count().label("member_count"))
        .group_by(Membership.project_id)
        .subquery()
    )
    return (
        select(Project, func.coalesce(member_counts.c.member_count, 0).label("member_count"))
        .outerjoin(member_counts, member_counts.c.project_id == Project.id)
        .where(visibility_filter(user_id))
        .options(
            joinedload(Project.owner).joinedload(User.profile),
            selectinload(Project.skills).joinedload(ProjectSkill.skill),
            selectinload(Project.interests).joinedload(ProjectInterest.interest),
        )
    )


def recommendation_candidates(session: Session, user_id: UUID) -> list:
    query = visible_projects(user_id)
    return list(
        session.execute(
            query.where(
                Project.status == ProjectStatus.OPEN,
                Project.owner_id != user_id,
                ~Project.memberships.any(Membership.user_id == user_id),
                Project.memberships.any(Membership.user_id == Project.owner_id),
                or_(
                    Project.max_members.is_(None),
                    query.selected_columns.member_count < Project.max_members,
                ),
                ~Project.applications.any(
                    (Application.applicant_id == user_id)
                    & (Application.status != ApplicationStatus.WITHDRAWN)
                ),
            ).order_by(Project.id)
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


def get_project(session: Session, user_id: UUID, project_id: UUID, *, refresh: bool = False):
    query = visible_projects(user_id).where(Project.id == project_id)
    return session.execute(query.execution_options(populate_existing=refresh)).one_or_none()


def locked_project(session: Session, user_id: UUID, project_id: UUID) -> Project | None:
    return session.scalar(
        select(Project)
        .where(Project.id == project_id, visibility_filter(user_id))
        .with_for_update()
    )


def member_count(session: Session, project_id: UUID) -> int:
    return session.scalar(
        select(func.count()).select_from(Membership).where(Membership.project_id == project_id)
    )


def owned_projects(
    session: Session,
    user_id: UUID,
    *,
    limit: int,
    cursor: UUID | None,
    status: ProjectStatus | None,
) -> list:
    query = visible_projects(user_id).where(Project.owner_id == user_id)
    if cursor is not None:
        query = query.where(Project.id > cursor)
    if status is not None:
        query = query.where(Project.status == status)
    return list(session.execute(query.order_by(Project.id).limit(limit + 1)))


def catalog_items(session: Session, model: type[Skill] | type[Interest], ids: list[UUID]):
    return list(
        session.scalars(
            select(model)
            .where(model.id.in_(ids))
            .order_by(model.id)
            .with_for_update(read=True, key_share=True)
        )
    )


def replace_requirements(
    session: Session,
    project: Project,
    *,
    skills: list[ProjectSkillInput] | None,
    interests: list[UUID] | None,
) -> None:
    if skills is not None:
        session.execute(delete(ProjectSkill).where(ProjectSkill.project_id == project.id))
        if skills:
            session.execute(
                insert(ProjectSkill),
                [
                    {"project_id": project.id, "skill_id": item.skill_id, "required": item.required}
                    for item in skills
                ],
            )
    if interests is not None:
        session.execute(delete(ProjectInterest).where(ProjectInterest.project_id == project.id))
        if interests:
            session.execute(
                insert(ProjectInterest),
                [{"project_id": project.id, "interest_id": id_} for id_ in interests],
            )


def list_catalog(
    session: Session, model: type[Skill] | type[Interest], *, limit: int, cursor: UUID | None
) -> list:
    query = select(model).order_by(model.id).limit(limit + 1)
    if cursor is not None:
        query = query.where(model.id > cursor)
    return list(session.scalars(query))
