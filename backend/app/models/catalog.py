from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.projects import Project
    from app.models.users import User


class Skill(UUIDPrimaryKey, Base):
    __tablename__ = "skills"
    __table_args__ = (
        UniqueConstraint("name"),
        CheckConstraint("name = lower(trim(name)) AND length(name) > 0", name="canonical_name"),
    )
    name: Mapped[str] = mapped_column(String(100))


class Interest(UUIDPrimaryKey, Base):
    __tablename__ = "interests"
    __table_args__ = (
        UniqueConstraint("name"),
        CheckConstraint("name = lower(trim(name)) AND length(name) > 0", name="canonical_name"),
    )
    name: Mapped[str] = mapped_column(String(100))


class UserSkill(Base):
    __tablename__ = "user_skills"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    user: Mapped[User] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship()


class UserInterest(Base):
    __tablename__ = "user_interests"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    interest_id: Mapped[UUID] = mapped_column(
        ForeignKey("interests.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    user: Mapped[User] = relationship(back_populates="interests")
    interest: Mapped[Interest] = relationship()


class ProjectSkill(Base):
    __tablename__ = "project_skills"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[UUID] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    required: Mapped[bool] = mapped_column(server_default="true")
    project: Mapped[Project] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship()


class ProjectInterest(Base):
    __tablename__ = "project_interests"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    interest_id: Mapped[UUID] = mapped_column(
        ForeignKey("interests.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    project: Mapped[Project] = relationship(back_populates="interests")
    interest: Mapped[Interest] = relationship()
