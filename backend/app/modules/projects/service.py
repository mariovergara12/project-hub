from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Interest, Project, Skill
from app.modules.projects import repository
from app.modules.projects.schemas import (
    CatalogItem,
    CatalogPage,
    ProjectOwner,
    ProjectPage,
    ProjectResponse,
    ProjectSkillResponse,
)


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
