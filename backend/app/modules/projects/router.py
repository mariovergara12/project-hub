from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.responses import AUTH_ERROR_RESPONSES, ErrorResponse, ProfileValidationErrorResponse
from app.core.security import CurrentUserId
from app.models import Interest, Skill
from app.models.enums import ProjectStatus, ProjectType
from app.modules.projects import repository, service
from app.modules.projects.schemas import (
    CatalogPage,
    ProjectCreate,
    ProjectPage,
    ProjectResponse,
    ProjectStatusUpdate,
    ProjectUpdate,
)
from app.modules.recommendations import service as recommendations
from app.modules.recommendations.schemas import RecommendedProjects
from app.modules.users.service import IdentityNoLongerExists, read_me

router = APIRouter(tags=["discovery"], responses=AUTH_ERROR_RESPONSES)


def discovery_user(
    user_id: CurrentUserId, session: Annotated[Session, Depends(get_session)]
) -> UUID:
    # Checks the hosted Auth FK even for an unexpired token belonging to a deleted account.
    try:
        read_me(session, user_id, include_selections=False)
    except IdentityNoLongerExists:
        raise HTTPException(status_code=401, detail="Account no longer exists") from None
    return user_id


DiscoveryUser = Annotated[UUID, Depends(discovery_user)]
DatabaseSession = Annotated[Session, Depends(get_session)]
PageLimit = Annotated[int, Query(ge=1, le=100, description="Page size; defaults to 20.")]
PageCursor = Annotated[
    UUID | None,
    Query(description="Previous next_cursor; UUID ascending, exclusive. Omit on the first page."),
]


@router.get("/projects", response_model=ProjectPage)
def list_projects(
    user_id: DiscoveryUser,
    session: DatabaseSession,
    limit: PageLimit = 20,
    cursor: PageCursor = None,
    q: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=200,
            description="Case-insensitive literal substring in title or description; trimmed.",
        ),
    ] = None,
    project_type: ProjectType | None = None,
    status: ProjectStatus | None = None,
    skill_id: UUID | None = None,
    interest_id: UUID | None = None,
) -> ProjectPage:
    """List visible projects in ascending UUID order, combining filters with AND.

    Open projects are visible to every signed-in user. Other statuses require
    ownership or membership; the status filter never grants access. No status
    filter means all visible statuses. Unknown catalog UUIDs return an empty page.
    Keep filters unchanged between pages. next_cursor=null means the end;
    an empty page is {"items": [], "next_cursor": null}. No total count is returned.
    """
    rows = repository.list_projects(
        session,
        user_id,
        limit=limit,
        cursor=cursor,
        q=q.strip() if q else None,
        project_type=project_type,
        status=status,
        skill_id=skill_id,
        interest_id=interest_id,
    )
    return service.project_page(rows, limit)


@router.get("/projects/recommended", response_model=RecommendedProjects)
def recommended_projects(user_id: CurrentUserId, session: DatabaseSession) -> RecommendedProjects:
    """Top ten positive matches, ordered by score descending then project UUID.

    Skills: 50 points (required skills count twice); interests: 25;
    availability: 15; experience: 10. Missing values earn no points.
    Only projects the caller can still apply to are considered. No pagination.
    """
    try:
        return recommendations.recommend(session, user_id)
    except IdentityNoLongerExists:
        raise HTTPException(status_code=401, detail="Account no longer exists") from None


@router.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Project is hidden or does not exist."}
    },
)
def get_project(
    project_id: UUID, user_id: DiscoveryUser, session: DatabaseSession
) -> ProjectResponse:
    """Return the same project fields as a list item, with a public owner summary."""
    row = repository.get_project(session, user_id, project_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return service.project_response(*row)


@router.get("/skills", response_model=CatalogPage)
def list_skills(
    user_id: DiscoveryUser,
    session: DatabaseSession,
    limit: PageLimit = 20,
    cursor: PageCursor = None,
) -> CatalogPage:
    """List skill IDs/names in ascending UUID order; next_cursor=null ends pagination."""
    return service.catalog_page(session, Skill, limit=limit, cursor=cursor)


@router.get("/interests", response_model=CatalogPage)
def list_interests(
    user_id: DiscoveryUser,
    session: DatabaseSession,
    limit: PageLimit = 20,
    cursor: PageCursor = None,
) -> CatalogPage:
    """List interest IDs/names in ascending UUID order; next_cursor=null ends pagination."""
    return service.catalog_page(session, Interest, limit=limit, cursor=cursor)


MANAGEMENT_ERRORS = {
    code: {"model": ErrorResponse, "description": description}
    for code, description in {
        403: "Owner-only action or verified faculty required.",
        404: "Project is hidden or does not exist.",
        409: "Invalid transition, archived project, or capacity below current membership.",
    }.items()
}
MANAGEMENT_ERRORS[422] = {
    "model": ProfileValidationErrorResponse,
    "description": "Invalid fields or unknown catalog IDs.",
}


def perform_write(session, user_id, **kwargs):
    try:
        return service.write_project(session, user_id, **kwargs)
    except service.ProjectError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from None
    except IdentityNoLongerExists:
        raise HTTPException(status_code=401, detail="Account no longer exists") from None


@router.post(
    "/projects", response_model=ProjectResponse, status_code=201, responses=MANAGEMENT_ERRORS
)
def create_project(changes: ProjectCreate, user_id: CurrentUserId, session: DatabaseSession):
    """Create a draft and its owner membership atomically. Ownership comes from the token."""
    return perform_write(session, user_id, changes=changes)


@router.patch("/projects/{project_id}", response_model=ProjectResponse, responses=MANAGEMENT_ERRORS)
def update_project(
    project_id: UUID, changes: ProjectUpdate, user_id: CurrentUserId, session: DatabaseSession
):
    """Owner-only partial edit. Omitted fields persist; empty selections clear links."""
    return perform_write(session, user_id, project_id=project_id, changes=changes)


@router.patch(
    "/projects/{project_id}/status", response_model=ProjectResponse, responses=MANAGEMENT_ERRORS
)
def change_status(
    project_id: UUID, changes: ProjectStatusUpdate, user_id: CurrentUserId, session: DatabaseSession
):
    """draft → open → in_progress → completed; archive from any non-archived status."""
    return perform_write(session, user_id, project_id=project_id, status=changes.status)


@router.get("/me/projects", response_model=ProjectPage)
def my_projects(
    user_id: DiscoveryUser,
    session: DatabaseSession,
    limit: PageLimit = 20,
    cursor: PageCursor = None,
    status: ProjectStatus | None = None,
):
    """List only owned projects, including private drafts and archived projects."""
    return service.project_page(
        repository.owned_projects(session, user_id, limit=limit, cursor=cursor, status=status),
        limit,
    )
