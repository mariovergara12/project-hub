from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Timestamps, UUIDPrimaryKey
from app.models.enums import ApplicationStatus, MilestoneStatus, enum_column

if TYPE_CHECKING:
    from app.models.projects import Project
    from app.models.users import User


class Application(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("project_id", "applicant_id"),)

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    applicant_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ApplicationStatus] = mapped_column(
        enum_column(ApplicationStatus, "application_status"),
        server_default=ApplicationStatus.PENDING.value,
    )
    project: Mapped[Project] = relationship(back_populates="applications")
    applicant: Mapped[User] = relationship(back_populates="applications")


class Membership(UUIDPrimaryKey, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("project_id", "user_id"),)

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    project: Mapped[Project] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class Milestone(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "milestones"
    __table_args__ = (CheckConstraint("length(trim(title)) > 0", name="title_not_blank"),)

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[date | None]
    status: Mapped[MilestoneStatus] = mapped_column(
        enum_column(MilestoneStatus, "milestone_status"),
        server_default=MilestoneStatus.TODO.value,
    )
    project: Mapped[Project] = relationship(back_populates="milestones")
