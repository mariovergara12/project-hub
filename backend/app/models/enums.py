from enum import StrEnum

from sqlalchemy import Enum


class UserRole(StrEnum):
    STUDENT = "student"
    FACULTY = "faculty"
    ADMINISTRATOR = "administrator"


class ProjectType(StrEnum):
    STUDENT_PROJECT = "student_project"
    RESEARCH_OPPORTUNITY = "research_opportunity"


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ApplicationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class MilestoneStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


def enum_column(enum: type[StrEnum], name: str) -> Enum:
    # VARCHAR + CHECK is easier to evolve than PostgreSQL-native enum types.
    return Enum(
        enum,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )
