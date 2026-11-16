from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.json_schema import SkipJsonSchema

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


Title = Annotated[str, Field(min_length=1, max_length=200)]
Description = Annotated[str, Field(min_length=1, max_length=10000)]
Hours = Annotated[int, Field(strict=True, ge=0, le=168)]
Experience = Annotated[int, Field(strict=True, ge=0, le=100)]
TeamSize = Annotated[int, Field(strict=True, ge=1, le=100)]


class ProjectSkillInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill_id: UUID
    required: bool = Field(default=True, strict=True)


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: Title
    description: Description
    project_type: ProjectType = ProjectType.STUDENT_PROJECT
    weekly_hours: Hours | None = None
    minimum_experience_years: Experience | None = None
    max_members: TeamSize | None = None
    skills: list[ProjectSkillInput] = Field(default_factory=list, max_length=50)
    interest_ids: list[UUID] = Field(default_factory=list, max_length=50)

    @field_validator("skills")
    @classmethod
    def unique_skills(cls, values: list[ProjectSkillInput]) -> list[ProjectSkillInput]:
        if values is None:
            raise ValueError("skills cannot be null")
        if len(values) != len({item.skill_id for item in values}):
            raise ValueError("skills must not contain duplicate IDs")
        return values

    @field_validator("interest_ids")
    @classmethod
    def unique_interests(cls, values: list[UUID]) -> list[UUID]:
        if values is None:
            raise ValueError("interest_ids cannot be null")
        if len(values) != len(set(values)):
            raise ValueError("interest_ids must not contain duplicates")
        return values


def omit_patch_default(schema: dict) -> None:
    # None is an internal omitted-field marker, not an accepted request value here.
    schema.pop("default", None)


class ProjectUpdate(ProjectCreate):
    title: Title | SkipJsonSchema[None] = Field(default=None, json_schema_extra=omit_patch_default)
    description: Description | SkipJsonSchema[None] = Field(
        default=None, json_schema_extra=omit_patch_default
    )
    project_type: ProjectType | SkipJsonSchema[None] = Field(
        default=None, json_schema_extra=omit_patch_default
    )
    skills: list[ProjectSkillInput] | SkipJsonSchema[None] = Field(
        default=None, max_length=50, json_schema_extra=omit_patch_default
    )
    interest_ids: list[UUID] | SkipJsonSchema[None] = Field(
        default=None, max_length=50, json_schema_extra=omit_patch_default
    )

    @field_validator(
        "title", "description", "project_type", "skills", "interest_ids", mode="before"
    )
    @classmethod
    def cannot_be_null(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value


class ProjectStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: ProjectStatus
