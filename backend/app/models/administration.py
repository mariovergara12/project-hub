"""Operator-only audit history; it is never exposed through profile endpoints."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKey
from app.models.enums import UserRole, enum_column


class FacultyRoleChange(UUIDPrimaryKey, Base):
    __tablename__ = "faculty_role_changes"
    __table_args__ = (
        CheckConstraint("length(trim(operator)) > 0", name="operator_not_blank"),
        CheckConstraint("length(trim(reason)) > 0", name="reason_not_blank"),
        Index("ix_faculty_role_changes_user_time", "user_id", "performed_at"),
    )

    # No user FK: account deletion must neither erase audit history nor be blocked by it.
    user_id: Mapped[UUID]
    operator: Mapped[str] = mapped_column(String(200))
    database_principal: Mapped[str] = mapped_column(String(128))
    reason: Mapped[str] = mapped_column(String(2000))
    previous_role: Mapped[UserRole] = mapped_column(enum_column(UserRole, "previous_role"))
    new_role: Mapped[UserRole] = mapped_column(enum_column(UserRole, "new_role"))
    previous_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    new_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
