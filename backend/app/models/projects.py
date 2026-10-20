from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Timestamps, UUIDPrimaryKey
from app.models.enums import ProjectStatus, ProjectType, enum_column

if TYPE_CHECKING:
    from app.models.catalog import ProjectInterest, ProjectSkill
    from app.models.collaboration import Application, Membership, Milestone
    from app.models.users import User


class Project(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="title_not_blank"),
        CheckConstraint("length(trim(description)) > 0", name="description_not_blank"),
        CheckConstraint("weekly_hours BETWEEN 0 AND 168", name="weekly_hours_range"),
        CheckConstraint("minimum_experience_years >= 0", name="experience_nonnegative"),
        CheckConstraint("max_members > 0", name="max_members_positive"),
    )

    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    project_type: Mapped[ProjectType] = mapped_column(enum_column(ProjectType, "project_type"))
    status: Mapped[ProjectStatus] = mapped_column(
        enum_column(ProjectStatus, "project_status"),
        server_default=ProjectStatus.DRAFT.value,
        index=True,
    )
    weekly_hours: Mapped[int | None]
    minimum_experience_years: Mapped[int | None]
    max_members: Mapped[int | None]

    owner: Mapped[User] = relationship(back_populates="owned_projects")
    skills: Mapped[list[ProjectSkill]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    interests: Mapped[list[ProjectInterest]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    applications: Mapped[list[Application]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    memberships: Mapped[list[Membership]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    milestones: Mapped[list[Milestone]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
