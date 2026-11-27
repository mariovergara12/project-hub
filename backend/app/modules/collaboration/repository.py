from uuid import UUID

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import Application, Membership, Project, User
from app.models.enums import ApplicationStatus, ProjectStatus
from app.modules.projects.repository import visible_projects


def own_teams(
    session: Session,
    user_id: UUID,
    *,
    limit: int,
    cursor: UUID | None,
    status: ProjectStatus | None,
):
    query = (
        visible_projects(user_id)
        .add_columns(Membership.joined_at)
        .outerjoin(
            Membership,
            and_(Membership.project_id == Project.id, Membership.user_id == user_id),
        )
        .where(or_(Project.owner_id == user_id, Membership.user_id == user_id))
    )
    if cursor is not None:
        query = query.where(Project.id > cursor)
    if status is not None:
        query = query.where(Project.status == status)
    return list(session.execute(query.order_by(Project.id).limit(limit + 1)))


def membership(session: Session, project_id: UUID, user_id: UUID) -> Membership | None:
    return session.scalar(
        select(Membership).where(Membership.project_id == project_id, Membership.user_id == user_id)
    )


def lock_project(session: Session, project_id: UUID) -> Project | None:
    return session.scalar(select(Project).where(Project.id == project_id).with_for_update())


def lock_application(session: Session, application_id: UUID) -> Application | None:
    return session.scalar(
        select(Application)
        .where(Application.id == application_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def application_hint(session: Session, user_id: UUID, application_id: UUID):
    # Only the applicant and owner may learn that this application exists.
    return session.execute(
        select(Application.project_id, Application.applicant_id, Project.owner_id)
        .join(Project)
        .where(
            Application.id == application_id,
            or_(Application.applicant_id == user_id, Project.owner_id == user_id),
        )
    ).one_or_none()


def lock_users(session: Session, ids: set[UUID]) -> None:
    list(session.scalars(select(User).where(User.id.in_(ids)).order_by(User.id).with_for_update()))


def application_query():
    return select(Application).options(
        joinedload(Application.project), joinedload(Application.applicant).joinedload(User.profile)
    )


def application(session: Session, application_id: UUID) -> Application:
    return session.scalar(
        application_query()
        .where(Application.id == application_id)
        .execution_options(populate_existing=True)
    )


def applications(
    session: Session,
    *,
    applicant_id: UUID | None = None,
    project_id: UUID | None = None,
    status: ApplicationStatus | None = None,
    cursor: UUID | None = None,
    limit: int,
) -> list[Application]:
    query = application_query()
    if applicant_id is not None:
        query = query.where(Application.applicant_id == applicant_id)
    if project_id is not None:
        query = query.where(Application.project_id == project_id)
    if status is not None:
        query = query.where(Application.status == status)
    if cursor is not None:
        query = query.where(Application.id > cursor)
    return list(session.scalars(query.order_by(Application.id).limit(limit + 1)))


def members(session: Session, project_id: UUID, *, cursor: UUID | None, limit: int):
    query = (
        select(Membership)
        .where(Membership.project_id == project_id)
        .options(joinedload(Membership.user).joinedload(User.profile))
    )
    if cursor is not None:
        query = query.where(Membership.user_id > cursor)
    return list(session.scalars(query.order_by(Membership.user_id).limit(limit + 1)))


def remove_member(session: Session, project_id: UUID, user_id: UUID) -> bool:
    return (
        session.execute(
            delete(Membership).where(
                Membership.project_id == project_id, Membership.user_id == user_id
            )
        ).rowcount
        > 0
    )
