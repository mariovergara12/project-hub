from uuid import UUID

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Interest, Membership, Project, Skill, User
from app.models.enums import ProjectStatus, ProjectType, UserRole
from app.modules.projects import repository
from app.modules.projects.schemas import (
    CatalogItem,
    CatalogPage,
    ProjectCreate,
    ProjectOwner,
    ProjectPage,
    ProjectResponse,
    ProjectSkillResponse,
    ProjectUpdate,
)
from app.modules.users.repository import get_or_create_user
from app.modules.users.service import IdentityNoLongerExists, is_missing_auth_identity


def project_response(project: Project, member_count: int) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        project_type=project.project_type,
        status=project.status,
        weekly_hours=project.weekly_hours,
        minimum_experience_years=project.minimum_experience_years,
        max_members=project.max_members,
        member_count=member_count,
        owner=ProjectOwner(
            id=project.owner.id,
            display_name=project.owner.profile.display_name if project.owner.profile else None,
            role=project.owner.role,
            faculty_verified=project.owner.faculty_verified_at is not None,
        ),
        skills=[
            ProjectSkillResponse(id=link.skill.id, name=link.skill.name, required=link.required)
            for link in sorted(project.skills, key=lambda link: link.skill.name)
        ],
        interests=[
            CatalogItem.model_validate(link.interest)
            for link in sorted(project.interests, key=lambda link: link.interest.name)
        ],
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def project_page(rows: list, limit: int) -> ProjectPage:
    return ProjectPage(
        items=[project_response(project, count) for project, count in rows[:limit]],
        next_cursor=rows[limit - 1][0].id if len(rows) > limit else None,
    )


def catalog_page(
    session: Session, model: type[Skill] | type[Interest], *, limit: int, cursor: UUID | None
) -> CatalogPage:
    rows = repository.list_catalog(session, model, limit=limit, cursor=cursor)
    return CatalogPage(
        items=[CatalogItem.model_validate(row) for row in rows[:limit]],
        next_cursor=rows[limit - 1].id if len(rows) > limit else None,
    )


class ProjectError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(message)


def require_faculty(user: User, project_type: ProjectType) -> None:
    if project_type == ProjectType.RESEARCH_OPPORTUNITY and not (
        user.role == UserRole.FACULTY and user.faculty_verified_at is not None
    ):
        raise ProjectError(403, "Research opportunities require verified faculty")


def validate_catalogs(session: Session, changes: ProjectCreate | ProjectUpdate) -> None:
    if changes.skills is not None:
        ids = [item.skill_id for item in changes.skills]
        if len(repository.catalog_items(session, Skill, ids)) != len(ids):
            raise ProjectError(422, "Unknown skill IDs")
    if changes.interest_ids is not None:
        if len(repository.catalog_items(session, Interest, changes.interest_ids)) != len(
            changes.interest_ids
        ):
            raise ProjectError(422, "Unknown interest IDs")


def write_project(
    session: Session,
    user_id: UUID,
    *,
    changes: ProjectCreate | ProjectUpdate | None = None,
    project_id: UUID | None = None,
    status: ProjectStatus | None = None,
) -> ProjectResponse:
    try:
        with session.begin():
            # Shared lock order with profile/faculty writes: user, project, catalogs.
            user = get_or_create_user(session, user_id)
            if project_id is None:
                require_faculty(user, changes.project_type)
                validate_catalogs(session, changes)
                project = Project(
                    owner_id=user_id,
                    status=ProjectStatus.DRAFT,
                    **changes.model_dump(exclude={"skills", "interest_ids"}),
                )
                session.add(project)
                session.flush()
                session.add(Membership(project_id=project.id, user_id=user_id))
            else:
                project = repository.locked_project(session, user_id, project_id)
                if project is None:
                    raise ProjectError(404, "Project not found")
                if project.owner_id != user_id:
                    raise ProjectError(403, "Only the project owner can change this project")
                if status is not None:
                    if status != project.status:
                        next_status = {
                            ProjectStatus.DRAFT: ProjectStatus.OPEN,
                            ProjectStatus.OPEN: ProjectStatus.IN_PROGRESS,
                            ProjectStatus.IN_PROGRESS: ProjectStatus.COMPLETED,
                        }.get(project.status)
                        if project.status == ProjectStatus.ARCHIVED or (
                            status != ProjectStatus.ARCHIVED and status != next_status
                        ):
                            raise ProjectError(409, "Invalid project status transition")
                        if status == ProjectStatus.OPEN:
                            require_faculty(user, project.project_type)
                        project.status = status
                else:
                    if project.status == ProjectStatus.ARCHIVED:
                        raise ProjectError(409, "Archived projects are read-only")
                    require_faculty(user, changes.project_type or project.project_type)
                    validate_catalogs(session, changes)
                    values = changes.model_dump(
                        exclude_unset=True, exclude={"skills", "interest_ids"}
                    )
                    capacity = values.get("max_members", project.max_members)
                    if capacity is not None and capacity < repository.member_count(
                        session, project.id
                    ):
                        raise ProjectError(
                            409, "Team capacity cannot be less than the current member count"
                        )
                    for field, value in values.items():
                        setattr(project, field, value)
            if changes is not None:
                repository.replace_requirements(
                    session, project, skills=changes.skills, interests=changes.interest_ids
                )
                if changes.model_fields_set:
                    project.updated_at = func.now()
            session.flush()
            return project_response(
                *repository.get_project(session, user_id, project.id, refresh=True)
            )
    except IntegrityError as exc:
        if is_missing_auth_identity(exc):
            raise IdentityNoLongerExists from None
        raise
