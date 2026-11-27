from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Milestone
from app.models.enums import MilestoneStatus, ProjectStatus
from app.modules.collaboration.repository import membership
from app.modules.collaboration.schemas import ProjectSummary
from app.modules.collaboration.service import CollaborationError, transaction
from app.modules.milestones import repository
from app.modules.milestones.schemas import (
    MilestoneCreate,
    MilestonePage,
    MilestoneProgress,
    MilestoneResponse,
    MilestoneUpdate,
)
from app.modules.users.repository import get_or_create_user


def require_team(session: Session, user_id: UUID, project_id: UUID, *, write: bool):
    # Use the same project lock as removal and status changes. Recheck membership
    # after acquiring it so a concurrent removal cannot authorize a stale write.
    project = repository.project(session, project_id, write=write)
    if project is None or (
        project.owner_id != user_id and membership(session, project_id, user_id) is None
    ):
        raise CollaborationError(404, "Milestones are unavailable for this account")
    if write and project.status in (ProjectStatus.COMPLETED, ProjectStatus.ARCHIVED):
        raise CollaborationError(409, "Completed and archived projects have read-only milestones")
    return project


def list_milestones(
    session: Session,
    user_id: UUID,
    project_id: UUID,
    *,
    limit: int,
    cursor: UUID | None,
    status: MilestoneStatus | None,
) -> MilestonePage:
    with transaction(session):
        project = require_team(session, user_id, project_id, write=False)
        rows = repository.list_milestones(
            session, project_id, limit=limit, cursor=cursor, status=status
        )
        counts = repository.progress(session, project_id)
        return MilestonePage(
            project=ProjectSummary.model_validate(project),
            items=[MilestoneResponse.model_validate(item) for item in rows[:limit]],
            next_cursor=rows[limit - 1].id if len(rows) > limit else None,
            progress=MilestoneProgress(
                total=sum(counts.values()),
                todo=counts.get(MilestoneStatus.TODO, 0),
                in_progress=counts.get(MilestoneStatus.IN_PROGRESS, 0),
                completed=counts.get(MilestoneStatus.COMPLETED, 0),
            ),
        )


def create(
    session: Session, user_id: UUID, project_id: UUID, changes: MilestoneCreate
) -> MilestoneResponse:
    with transaction(session):
        get_or_create_user(session, user_id)
        require_team(session, user_id, project_id, write=True)
        value = Milestone(project_id=project_id, **changes.model_dump())
        session.add(value)
        session.flush()
        return MilestoneResponse.model_validate(value)


def change(
    session: Session,
    user_id: UUID,
    milestone_id: UUID,
    changes: MilestoneUpdate | None = None,
) -> MilestoneResponse | None:
    with transaction(session):
        get_or_create_user(session, user_id)
        project_id = repository.project_hint(session, user_id, milestone_id)
        if project_id is None:
            raise CollaborationError(404, "Milestone not found")
        require_team(session, user_id, project_id, write=True)
        value = repository.milestone(session, project_id, milestone_id)
        if value is None:
            raise CollaborationError(404, "Milestone not found")
        if changes is None:
            session.delete(value)
            return None
        for field, content in changes.model_dump(exclude_unset=True).items():
            setattr(value, field, content)
        session.flush()
        return MilestoneResponse.model_validate(value)
