from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Application, Membership, Project, User
from app.models.enums import ApplicationStatus, ProjectStatus
from app.modules.collaboration import repository
from app.modules.collaboration.schemas import (
    ApplicationCreate,
    ApplicationPage,
    ApplicationResponse,
    MemberPage,
    MemberResponse,
    ProjectApplicationsPage,
    ProjectSummary,
    RemovalResponse,
)
from app.modules.projects import repository as projects
from app.modules.projects.schemas import ProjectOwner
from app.modules.users.repository import get_or_create_user
from app.modules.users.service import IdentityNoLongerExists, is_missing_auth_identity


class CollaborationError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(message)


@contextmanager
def transaction(session: Session) -> Iterator[None]:
    try:
        with session.begin():
            yield
    except IntegrityError as exc:
        if is_missing_auth_identity(exc):
            raise IdentityNoLongerExists from None
        raise


def public_user(user: User) -> ProjectOwner:
    return ProjectOwner(
        id=user.id,
        display_name=user.profile.display_name if user.profile else None,
        role=user.role,
        faculty_verified=user.faculty_verified_at is not None,
    )


def response(session: Session, application_id: UUID) -> ApplicationResponse:
    value = repository.application(session, application_id)
    return application_response(value)


def application_response(value: Application) -> ApplicationResponse:
    return ApplicationResponse(
        id=value.id,
        project=ProjectSummary.model_validate(value.project),
        applicant=public_user(value.applicant),
        message=value.message,
        status=value.status,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def visible_project(session: Session, user_id: UUID, project_id: UUID, *, lock=False) -> Project:
    if lock:
        value = projects.locked_project(session, user_id, project_id)
    else:
        value = session.scalar(
            select(Project).where(Project.id == project_id, projects.visibility_filter(user_id))
        )
    if value is None:
        raise CollaborationError(404, "Project not found")
    return value


def owner_only(project: Project, user_id: UUID) -> None:
    if project.owner_id != user_id:
        raise CollaborationError(403, "Only the project owner can review applications")


def require_space(session: Session, project: Project) -> None:
    if project.status != ProjectStatus.OPEN:
        raise CollaborationError(409, "Applications require an open project")
    # Prevent undercounting if a deployment has not applied the reviewed backfill.
    if repository.membership(session, project.id, project.owner_id) is None:
        raise CollaborationError(409, "Project owner membership is missing; contact support")
    if (
        project.max_members is not None
        and projects.member_count(session, project.id) >= project.max_members
    ):
        raise CollaborationError(409, "The project team is full")


def submit(
    session: Session, user_id: UUID, project_id: UUID, changes: ApplicationCreate
) -> tuple[ApplicationResponse, bool]:
    with transaction(session):
        get_or_create_user(session, user_id)
        project = visible_project(session, user_id, project_id, lock=True)
        if project.owner_id == user_id:
            raise CollaborationError(409, "Owners cannot apply to their own project")
        if repository.membership(session, project_id, user_id) is not None:
            raise CollaborationError(409, "You are already a member of this team")
        require_space(session, project)
        value = session.scalar(
            select(Application)
            .where(Application.project_id == project_id, Application.applicant_id == user_id)
            .with_for_update()
        )
        created = value is None
        if value is not None and value.status != ApplicationStatus.WITHDRAWN:
            raise CollaborationError(409, "Only withdrawn applications can be resubmitted")
        if created:
            value = Application(project_id=project_id, applicant_id=user_id)
            session.add(value)
        value.message = changes.message
        value.status = ApplicationStatus.PENDING
        session.flush()
        return response(session, value.id), created


def hint(session: Session, user_id: UUID, application_id: UUID):
    value = repository.application_hint(session, user_id, application_id)
    if value is None:
        raise CollaborationError(404, "Application not found")
    return value


def withdraw(session: Session, user_id: UUID, application_id: UUID) -> ApplicationResponse:
    with transaction(session):
        get_or_create_user(session, user_id)
        metadata = hint(session, user_id, application_id)
        if metadata.applicant_id != user_id:
            raise CollaborationError(403, "Only the applicant can withdraw this application")
        repository.lock_project(session, metadata.project_id)
        value = repository.lock_application(session, application_id)
        if value is None:
            raise CollaborationError(404, "Application not found")
        if value.status == ApplicationStatus.PENDING:
            value.status = ApplicationStatus.WITHDRAWN
        elif value.status != ApplicationStatus.WITHDRAWN:
            raise CollaborationError(409, "Only pending applications can be withdrawn")
        session.flush()
        return response(session, application_id)


def decide(
    session: Session, user_id: UUID, application_id: UUID, status: ApplicationStatus
) -> ApplicationResponse:
    with transaction(session):
        metadata = hint(session, user_id, application_id)
        if metadata.owner_id != user_id:
            raise CollaborationError(403, "Only the project owner can decide this application")
        # Acceptance inserts an FK to the applicant. Lock both users BEFORE the project,
        # in UUID order, so applicant withdrawal/deletion cannot cause a lock cycle.
        repository.lock_users(session, {user_id, metadata.applicant_id})
        get_or_create_user(session, user_id)
        project = repository.lock_project(session, metadata.project_id)
        value = repository.lock_application(session, application_id)
        if project is None or value is None:
            raise CollaborationError(404, "Application not found")
        owner_only(project, user_id)
        if value.status == status:
            # An accepted application remains history after leave/removal. Never re-add.
            return response(session, application_id)
        if value.status != ApplicationStatus.PENDING:
            raise CollaborationError(409, "Only pending applications can be decided")
        if project.status == ProjectStatus.ARCHIVED:
            raise CollaborationError(409, "Archived projects are read-only")
        if status == ApplicationStatus.ACCEPTED:
            require_space(session, project)
            if repository.membership(session, project.id, value.applicant_id) is not None:
                raise CollaborationError(409, "Applicant is already a member")
            session.add(Membership(project_id=project.id, user_id=value.applicant_id))
        value.status = status
        session.flush()
        return response(session, application_id)


def application_page(rows: list[Application], limit: int) -> ApplicationPage:
    return ApplicationPage(
        items=[application_response(item) for item in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


def own_applications(
    session: Session,
    user_id: UUID,
    *,
    limit: int,
    cursor: UUID | None,
    status: ApplicationStatus | None,
    project_id: UUID | None,
) -> ApplicationPage:
    return application_page(
        repository.applications(
            session,
            applicant_id=user_id,
            limit=limit,
            cursor=cursor,
            status=status,
            project_id=project_id,
        ),
        limit,
    )


def project_applications(
    session: Session,
    user_id: UUID,
    project_id: UUID,
    *,
    limit: int,
    cursor: UUID | None,
    status: ApplicationStatus | None,
) -> ProjectApplicationsPage:
    project = visible_project(session, user_id, project_id)
    owner_only(project, user_id)
    page = application_page(
        repository.applications(
            session, project_id=project_id, limit=limit, cursor=cursor, status=status
        ),
        limit,
    )
    return ProjectApplicationsPage(
        project=ProjectSummary.model_validate(project), **page.model_dump()
    )


def members(
    session: Session, user_id: UUID, project_id: UUID, *, limit: int, cursor: UUID | None
) -> MemberPage:
    project = visible_project(session, user_id, project_id)
    if project.owner_id != user_id and repository.membership(session, project_id, user_id) is None:
        raise CollaborationError(403, "The team roster is available only to the owner and members")
    rows = repository.members(session, project_id, cursor=cursor, limit=limit)
    return MemberPage(
        project=ProjectSummary.model_validate(project),
        max_members=project.max_members,
        member_count=projects.member_count(session, project_id),
        items=[
            MemberResponse(
                user=public_user(item.user),
                joined_at=item.joined_at,
                is_owner=item.user_id == project.owner_id,
            )
            for item in rows[:limit]
        ],
        next_cursor=rows[limit - 1].user_id if len(rows) > limit else None,
    )


def remove_member(
    session: Session, user_id: UUID, project_id: UUID, target_id: UUID
) -> RemovalResponse:
    with transaction(session):
        get_or_create_user(session, user_id)
        project = visible_project(session, user_id, project_id, lock=True)
        if user_id != project.owner_id and user_id != target_id:
            raise CollaborationError(403, "Only the owner can remove another member")
        if target_id == project.owner_id:
            raise CollaborationError(409, "The project owner cannot leave or be removed")
        if project.status == ProjectStatus.ARCHIVED:
            raise CollaborationError(409, "Archived projects are read-only")
        removed = repository.remove_member(session, project_id, target_id)
        return RemovalResponse(project_id=project_id, user_id=target_id, removed=removed)
