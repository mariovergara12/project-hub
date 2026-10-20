"""Import all models here so Alembic and SQLAlchemy see the complete schema."""

from app.models.base import Base
from app.models.catalog import (
    Interest,
    ProjectInterest,
    ProjectSkill,
    Skill,
    UserInterest,
    UserSkill,
)
from app.models.collaboration import Application, Membership, Milestone
from app.models.projects import Project
from app.models.users import Profile, User

__all__ = [
    "Application",
    "Base",
    "Interest",
    "Membership",
    "Milestone",
    "Profile",
    "Project",
    "ProjectInterest",
    "ProjectSkill",
    "Skill",
    "User",
    "UserInterest",
    "UserSkill",
]
