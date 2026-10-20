from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import UserRole

Name = Annotated[str, Field(min_length=1, max_length=150)]


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: Name | None = None
    university: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    major: Name | None = None
    department: Name | None = None
    bio: Annotated[str, Field(max_length=5000)] | None = None
    availability_hours: Annotated[int, Field(strict=True, ge=0, le=168)] | None = None
    learning_goals: Annotated[str, Field(max_length=2000)] | None = None
    experience_years: Annotated[int, Field(strict=True, ge=0, le=100)] | None = None

    @field_validator("display_name")
    @classmethod
    def display_name_cannot_be_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("display_name cannot be null")
        return value


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    display_name: str
    university: str | None
    major: str | None
    department: str | None
    bio: str | None
    availability_hours: int | None
    learning_goals: str | None
    experience_years: int | None


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: UserRole
    faculty_verified_at: datetime | None
    profile: ProfileResponse | None
