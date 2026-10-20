"""Keep application tables private to backend

Revision ID: 523b77890196
Revises: c579c3d1817a
Create Date: 2026-10-19 19:40:50.970987

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "523b77890196"
down_revision: str | Sequence[str] | None = "c579c3d1817a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove inherited client grants without depending on Supabase roles locally."""
    tables = ", ".join(
        f'public."{name}"'
        for name in (
            "users",
            "profiles",
            "skills",
            "interests",
            "user_skills",
            "user_interests",
            "projects",
            "project_skills",
            "project_interests",
            "applications",
            "memberships",
            "milestones",
            "alembic_version",
        )
    )
    op.execute(f"REVOKE ALL PRIVILEGES ON TABLE {tables} FROM PUBLIC")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL PRIVILEGES ON TABLES FROM PUBLIC"
    )
    for role in ("anon", "authenticated"):
        # Role and table names are fixed migration constants, never external input.
        op.execute(
            f"""DO $block$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                    EXECUTE 'REVOKE ALL PRIVILEGES ON TABLE {tables} FROM {role}';
                    EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public
                             REVOKE ALL PRIVILEGES ON TABLES FROM {role}';
                END IF;
            END
            $block$;"""
        )


def downgrade() -> None:
    """Keep restrictions: restoring unknown prior grants could expose application data.

    Future client access must be granted explicitly alongside reviewed RLS policies.
    Downgrading all the way to base still drops the application tables normally.
    """
    pass
