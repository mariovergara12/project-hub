"""Backfill project owner memberships without changing existing capacity.

Revision ID: 9eb18a4d2620
Revises: 71d9cfa35335
"""

from alembic import op

revision = "9eb18a4d2620"
down_revision = "71d9cfa35335"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Match application lock order and exclude concurrent writes during the backfill.
    op.execute("LOCK TABLE public.users IN EXCLUSIVE MODE")
    op.execute("LOCK TABLE public.projects, public.memberships IN SHARE ROW EXCLUSIVE MODE")
    op.execute("""DO $$ BEGIN
        IF EXISTS (
            SELECT 1 FROM public.projects p
            WHERE NOT EXISTS (SELECT 1 FROM public.memberships m
                              WHERE m.project_id=p.id AND m.user_id=p.owner_id)
              AND p.max_members IS NOT NULL
              AND (SELECT count(*) FROM public.memberships m WHERE m.project_id=p.id)
                  >= p.max_members
        ) THEN
            RAISE EXCEPTION 'Owner membership backfill exceeds team capacity; review projects';
        END IF;
    END $$""")
    op.execute("""INSERT INTO public.memberships (id, project_id, user_id)
        SELECT gen_random_uuid(), p.id, p.owner_id FROM public.projects p
        WHERE NOT EXISTS (SELECT 1 FROM public.memberships m
                          WHERE m.project_id=p.id AND m.user_id=p.owner_id)
        ON CONFLICT (project_id, user_id) DO NOTHING""")


def downgrade() -> None:
    # Memberships are legitimate application data, including owners who already existed.
    # Keep them rather than deleting indistinguishable pre-existing records.
    pass
