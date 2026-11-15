from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ProjectStatus, ProjectType, UserRole


class CatalogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class ProjectSkillResponse(CatalogItem):
    required: bool


class ProjectOwner(BaseModel):
    id: UUID
    display_name: str | None
    role: UserRole
    faculty_verified: bool


class ProjectResponse(BaseModel):
    id: UUID
    title: str
    description: str
    project_type: ProjectType
    status: ProjectStatus
    weekly_hours: int | None
    minimum_experience_years: int | None
    max_members: int | None
    member_count: int
    owner: ProjectOwner
    skills: list[ProjectSkillResponse]
    interests: list[CatalogItem]
    created_at: datetime
    updated_at: datetime


class ProjectPage(BaseModel):
    items: list[ProjectResponse]
    next_cursor: UUID | None


class CatalogPage(BaseModel):
    items: list[CatalogItem]
    next_cursor: UUID | None
