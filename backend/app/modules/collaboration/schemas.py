from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApplicationStatus, ProjectStatus
from app.modules.projects.schemas import ProjectOwner, ProjectResponse


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    message: str | None = Field(default=None, max_length=2000)


class ApplicationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal[ApplicationStatus.ACCEPTED, ApplicationStatus.REJECTED]


class ProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    status: ProjectStatus
    owner_id: UUID


class ApplicationResponse(BaseModel):
    id: UUID
    project: ProjectSummary
    applicant: ProjectOwner
    message: str | None
    status: ApplicationStatus
    created_at: datetime
    updated_at: datetime


class ApplicationPage(BaseModel):
    items: list[ApplicationResponse]
    next_cursor: UUID | None


class ProjectApplicationsPage(ApplicationPage):
    project: ProjectSummary


class MemberResponse(BaseModel):
    user: ProjectOwner
    joined_at: datetime
    is_owner: bool


class MemberPage(BaseModel):
    project: ProjectSummary
    max_members: int | None
    member_count: int
    items: list[MemberResponse]
    next_cursor: UUID | None


class RemovalResponse(BaseModel):
    project_id: UUID
    user_id: UUID
    removed: bool


class MyTeamResponse(BaseModel):
    project: ProjectResponse
    joined_at: datetime | None
    is_owner: bool


class MyTeamPage(BaseModel):
    items: list[MyTeamResponse]
    next_cursor: UUID | None
