from uuid import UUID

from fastapi import APIRouter, Response

from app.core.responses import ErrorResponse
from app.core.security import CurrentUserId
from app.models.enums import MilestoneStatus
from app.modules.collaboration.router import ERRORS, perform
from app.modules.milestones import service
from app.modules.milestones.schemas import (
    MilestoneCreate,
    MilestonePage,
    MilestoneResponse,
    MilestoneUpdate,
)
from app.modules.projects.router import DatabaseSession, DiscoveryUser, PageCursor, PageLimit

router = APIRouter(
    tags=["milestones"],
    responses={
        **ERRORS,
        404: {
            "model": ErrorResponse,
            "description": "Missing resource or caller is not the owner/current member.",
        },
        409: {
            "model": ErrorResponse,
            "description": "Completed and archived project milestones are read-only.",
        },
    },
)


@router.get("/projects/{project_id}/milestones", response_model=MilestonePage)
def list_milestones(
    project_id: UUID,
    user_id: DiscoveryUser,
    session: DatabaseSession,
    limit: PageLimit = 20,
    cursor: PageCursor = None,
    status: MilestoneStatus | None = None,
):
    """Team-only UUID pagination; progress covers all milestones regardless of filters."""
    return perform(
        service.list_milestones,
        session,
        user_id,
        project_id,
        limit=limit,
        cursor=cursor,
        status=status,
    )


@router.post("/projects/{project_id}/milestones", response_model=MilestoneResponse, status_code=201)
def create(
    project_id: UUID, changes: MilestoneCreate, user_id: CurrentUserId, session: DatabaseSession
):
    return perform(service.create, session, user_id, project_id, changes)


@router.patch("/milestones/{milestone_id}", response_model=MilestoneResponse)
def update(
    milestone_id: UUID, changes: MilestoneUpdate, user_id: CurrentUserId, session: DatabaseSession
):
    """Omitted fields persist; null clears description/due date. Status can be reopened."""
    return perform(service.change, session, user_id, milestone_id, changes)


@router.delete("/milestones/{milestone_id}", status_code=204)
def delete(milestone_id: UUID, user_id: CurrentUserId, session: DatabaseSession):
    perform(service.change, session, user_id, milestone_id)
    return Response(status_code=204)
