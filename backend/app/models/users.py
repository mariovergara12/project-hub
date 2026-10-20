from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Timestamps
from app.models.enums import UserRole, enum_column

if TYPE_CHECKING:
    from app.models.catalog import UserInterest, UserSkill
    from app.models.collaboration import Application, Membership
    from app.models.projects import Project


class User(Timestamps, Base):
    __tablename__ = "users"

    # Verified Auth subject UUID. The cross-schema FK is managed explicitly by
    # Alembic, so this model doesn't require or manage Supabase's Auth schema.
    id: Mapped[UUID] = mapped_column(primary_key=True)
    role: Mapped[UserRole] = mapped_column(
        enum_column(UserRole, "user_role"), server_default=UserRole.STUDENT.value
    )
    faculty_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    profile: Mapped[Profile | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    skills: Mapped[list[UserSkill]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    interests: Mapped[list[UserInterest]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    owned_projects: Mapped[list[Project]] = relationship(
        back_populates="owner", passive_deletes="all"
    )
    applications: Mapped[list[Application]] = relationship(
        back_populates="applicant", cascade="all, delete-orphan", passive_deletes=True
    )
    memberships: Mapped[list[Membership]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class Profile(Timestamps, Base):
    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint("availability_hours BETWEEN 0 AND 168", name="availability_range"),
        CheckConstraint("experience_years >= 0", name="experience_nonnegative"),
        CheckConstraint("length(trim(display_name)) > 0", name="display_name_not_blank"),
    )

    # Shared UUID primary key also enforces one profile per user.
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str] = mapped_column(String(150))
    university: Mapped[str | None] = mapped_column(String(200))
    major: Mapped[str | None] = mapped_column(String(150))
    department: Mapped[str | None] = mapped_column(String(150))
    bio: Mapped[str | None] = mapped_column(Text)
    availability_hours: Mapped[int | None]
    learning_goals: Mapped[str | None] = mapped_column(Text)
    experience_years: Mapped[int | None]

    user: Mapped[User] = relationship(back_populates="profile")
