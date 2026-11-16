"""audit faculty role changes

Revision ID: 71d9cfa35335
Revises: cc1194778d46
Create Date: 2026-11-16 16:06:37.693444

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "71d9cfa35335"
down_revision: str | Sequence[str] | None = "cc1194778d46"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add private audit history without changing existing users or roles."""
    op.create_table(
        "faculty_role_changes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("operator", sa.String(200), nullable=False),
        sa.Column("database_principal", sa.String(128), nullable=False),
        sa.Column("reason", sa.String(2000), nullable=False),
        sa.Column(
            "previous_role",
            sa.Enum(
                "student",
                "faculty",
                "administrator",
                name="previous_role",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "new_role",
            sa.Enum(
                "student",
                "faculty",
                "administrator",
                name="new_role",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("previous_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("new_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "performed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("length(trim(operator)) > 0", name="operator_not_blank"),
        sa.CheckConstraint("length(trim(reason)) > 0", name="reason_not_blank"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_faculty_role_changes_user_time", "faculty_role_changes", ["user_id", "performed_at"]
    )
    op.execute("ALTER TABLE public.faculty_role_changes ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.faculty_role_changes FROM PUBLIC")
    for role in ("anon", "authenticated"):
        op.execute(f"""DO $block$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE
                             public.faculty_role_changes FROM {role}';
                END IF;
            END
            $block$;""")


def downgrade() -> None:
    """Remove audit storage only; this does not undo any role assignments."""
    op.drop_index("ix_faculty_role_changes_user_time", table_name="faculty_role_changes")
    op.drop_table("faculty_role_changes")
