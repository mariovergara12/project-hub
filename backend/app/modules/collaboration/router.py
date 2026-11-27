from uuid import UUID

from fastapi import APIRouter, HTTPException, Response

from app.core.responses import AUTH_ERROR_RESPONSES, ErrorResponse, ProfileValidationErrorResponse
from app.models.enums import ApplicationStatus, ProjectStatus
from app.modules.collaboration import service
from app.modules.collaboration.schemas import (
    ApplicationCreate,
    ApplicationDecision,
    ApplicationPage,
    ApplicationResponse,
    MemberPage,
    MyTeamPage,
    ProjectApplicationsPage,
    RemovalResponse,
)
from app.modules.projects.router import DatabaseSession, DiscoveryUser, PageCursor, PageLimit
from app.modules.users.service import IdentityNoLongerExists

ERRORS = {
    **AUTH_ERROR_RESPONSES,
    403: {
        "model": ErrorResponse,
        "description": "Not the applicant, project owner, or team member.",
    },
    404: {
        "model": ErrorResponse,
        "description": "Resource is missing or hidden from this account.",
    },
    409: {
        "model": ErrorResponse,
        "description": "Closed/full project, invalid transition, or protected owner membership.",
    },
    422: {
        "model": ProfileValidationErrorResponse,
        "description": "Invalid request fields or query parameters.",
    },
}
router = APIRouter(tags=["applications and teams"], responses=ERRORS)


def perform(action, *args, **kwargs):
    try:
        return action(*args, **kwargs)
    except service.CollaborationError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from None
    except IdentityNoLongerExists:
        raise HTTPException(status_code=401, detail="Account no longer exists") from None


@router.get("/me/teams", response_model=MyTeamPage)
def my_teams(
    user_id: DiscoveryUser,
    session: DatabaseSession,
    limit: PageLimit = 20,
    cursor: PageCursor = None,
    status: ProjectStatus | None = None,
):
    """Current memberships and owned projects. Past acceptances do not grant access."""
    return perform(service.own_teams, session, user_id, limit=limit, cursor=cursor, status=status)


@router.post(
    "/projects/{project_id}/applications",
    response_model=ApplicationResponse,
    status_code=201,
    responses={
        200: {"model": ApplicationResponse, "description": "Resubmitted withdrawn application."}
    },
)
def apply(
    project_id: UUID,
    changes: ApplicationCreate,
    user_id: DiscoveryUser,
    session: DatabaseSession,
    response: Response,
):
    value, created = perform(service.submit, session, user_id, project_id, changes)
    response.status_code = 201 if created else 200
    return value


@router.get("/me/applications", response_model=ApplicationPage)
def my_applications(
    user_id: DiscoveryUser,
    session: DatabaseSession,
    limit: PageLimit = 20,
    cursor: PageCursor = None,
    status: ApplicationStatus | None = None,
    project_id: UUID | None = None,
):
    """Only the caller's applications, ordered by UUID. Filters never grant visibility."""
    return perform(
        service.own_applications,
        session,
        user_id,
        limit=limit,
        cursor=cursor,
        status=status,
        project_id=project_id,
    )


@router.patch("/applications/{application_id}/withdraw", response_model=ApplicationResponse)
def withdraw(application_id: UUID, user_id: DiscoveryUser, session: DatabaseSession):
    """Applicant-only pending → withdrawn. Repeating withdrawal is a no-op."""
    return perform(service.withdraw, session, user_id, application_id)


@router.get("/projects/{project_id}/applications", response_model=ProjectApplicationsPage)
def project_applications(
    project_id: UUID,
    user_id: DiscoveryUser,
    session: DatabaseSession,
    limit: PageLimit = 20,
    cursor: PageCursor = None,
    status: ApplicationStatus | None = None,
):
    """Owner-only application messages and public applicant summaries."""
    return perform(
        service.project_applications,
        session,
        user_id,
        project_id,
        limit=limit,
        cursor=cursor,
        status=status,
    )


@router.patch("/applications/{application_id}/decision", response_model=ApplicationResponse)
def decide(
    application_id: UUID,
    changes: ApplicationDecision,
    user_id: DiscoveryUser,
    session: DatabaseSession,
):
    """Owner-only accept/reject. Acceptance and capacity check share the project lock."""
    return perform(service.decide, session, user_id, application_id, changes.status)


@router.get("/projects/{project_id}/members", response_model=MemberPage)
def members(
    project_id: UUID,
    user_id: DiscoveryUser,
    session: DatabaseSession,
    limit: PageLimit = 20,
    cursor: PageCursor = None,
):
    """Owner/member-only public summaries; cursor is a member user UUID."""
    return perform(service.members, session, user_id, project_id, limit=limit, cursor=cursor)


@router.delete("/projects/{project_id}/members/{member_id}", response_model=RemovalResponse)
def remove_member(
    project_id: UUID, member_id: UUID, user_id: DiscoveryUser, session: DatabaseSession
):
    """Owner removes a member, or a member leaves. Owner membership is protected."""
    return perform(service.remove_member, session, user_id, project_id, member_id)
