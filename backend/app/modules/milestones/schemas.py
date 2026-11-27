import re
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.json_schema import SkipJsonSchema

from app.models.enums import MilestoneStatus
from app.modules.collaboration.schemas import ProjectSummary
from app.modules.projects.schemas import Title, omit_patch_default


class MilestoneCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: Title
    description: str | None = Field(default=None, max_length=10000)
    due_date: date | None = None
    status: MilestoneStatus = MilestoneStatus.TODO

    @field_validator("description")
    @classmethod
    def empty_description(cls, value):
        return value or None

    @field_validator("due_date", mode="before")
    @classmethod
    def calendar_date(cls, value):
        if value is None or type(value) is date:
            return value
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("Use a calendar date in YYYY-MM-DD format")
        return date.fromisoformat(value)


class MilestoneUpdate(MilestoneCreate):
    title: Title | SkipJsonSchema[None] = Field(default=None, json_schema_extra=omit_patch_default)
    status: MilestoneStatus | SkipJsonSchema[None] = Field(
        default=None, json_schema_extra=omit_patch_default
    )

    @field_validator("title", "status", mode="before")
    @classmethod
    def cannot_be_null(cls, value):
        if value is None:
            raise ValueError("This field cannot be null")
        return value

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        return self


class MilestoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    due_date: date | None
    status: MilestoneStatus
    created_at: datetime
    updated_at: datetime


class MilestoneProgress(BaseModel):
    total: int
    todo: int
    in_progress: int
    completed: int


class MilestonePage(BaseModel):
    project: ProjectSummary
    items: list[MilestoneResponse]
    next_cursor: UUID | None
    progress: MilestoneProgress
