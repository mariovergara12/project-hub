from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.security import CurrentUserId
from app.models import Interest, Skill
from app.models.enums import ProjectStatus, ProjectType
from app.modules.projects import repository, service
from app.modules.projects.schemas import CatalogPage, ProjectPage, ProjectResponse
from app.modules.users.service import IdentityNoLongerExists, read_me

router = APIRouter(tags=["discovery"])


def discovery_user(
    user_id: CurrentUserId, session: Annotated[Session, Depends(get_session)]
) -> UUID:
    # Checks the hosted Auth FK even for an unexpired token belonging to a deleted account.
    try:
        read_me(session, user_id)
    except IdentityNoLongerExists:
        raise HTTPException(status_code=401, detail="Account no longer exists") from None
    return user_id


DiscoveryUser = Annotated[UUID, Depends(discovery_user)]
DatabaseSession = Annotated[Session, Depends(get_session)]
PageLimit = Annotated[int, Query(ge=1, le=100)]


@router.get("/projects", response_model=ProjectPage)
def list_projects(
    user_id: DiscoveryUser,
    session: DatabaseSession,
    limit: PageLimit = 20,
    cursor: UUID | None = None,
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    project_type: ProjectType | None = None,
    status: ProjectStatus | None = None,
    skill_id: UUID | None = None,
    interest_id: UUID | None = None,
) -> ProjectPage:
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


@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID, user_id: DiscoveryUser, session: DatabaseSession
) -> ProjectResponse:
    row = repository.get_project(session, user_id, project_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return service.project_response(*row)


@router.get("/skills", response_model=CatalogPage)
def list_skills(
    user_id: DiscoveryUser,
    session: DatabaseSession,
    limit: PageLimit = 20,
    cursor: UUID | None = None,
) -> CatalogPage:
    return service.catalog_page(session, Skill, limit=limit, cursor=cursor)


@router.get("/interests", response_model=CatalogPage)
def list_interests(
    user_id: DiscoveryUser,
    session: DatabaseSession,
    limit: PageLimit = 20,
    cursor: UUID | None = None,
) -> CatalogPage:
    return service.catalog_page(session, Interest, limit=limit, cursor=cursor)
