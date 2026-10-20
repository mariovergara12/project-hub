"""Link application users to Supabase Auth

Revision ID: cc1194778d46
Revises: 523b77890196
Create Date: 2026-10-19 19:48:11.979645

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cc1194778d46"
down_revision: str | Sequence[str] | None = "523b77890196"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Link identities when the provider-managed Auth schema exists.

    Plain local PostgreSQL deliberately has no Auth schema. Do not create a fake
    one or let application migrations manage provider-owned objects.
    """
    op.execute("""DO $block$
    BEGIN
        IF to_regclass('auth.users') IS NOT NULL THEN
            ALTER TABLE public.users
                ADD CONSTRAINT fk_users_id_auth_users
                FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;
        END IF;
    END
    $block$;""")


def downgrade() -> None:
    """Remove only the application-owned reference."""
    op.execute("ALTER TABLE public.users DROP CONSTRAINT IF EXISTS fk_users_id_auth_users")
