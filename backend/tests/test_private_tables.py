import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR
from app.models import Base


@pytest.mark.integration
def test_private_table_migration_revokes_inherited_and_future_grants(db_session: Session) -> None:
    # Reproduce the Supabase defaults on this disposable local database. All role,
    # table, grant, and default-privilege changes are rolled back by the fixture.
    for role in ("anon", "authenticated"):
        if not db_session.scalar(
            text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": role}
        ):
            db_session.execute(text(f'CREATE ROLE "{role}" NOLOGIN NOSUPERUSER NOBYPASSRLS'))
    db_session.execute(
        text("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO PUBLIC, anon, authenticated")
    )
    db_session.execute(
        text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT ALL PRIVILEGES ON TABLES TO PUBLIC, anon, authenticated"
        )
    )

    scripts = ScriptDirectory.from_config(Config(str(BACKEND_DIR / "alembic.ini")))
    revision = scripts.get_revision("523b77890196")
    with Operations.context(MigrationContext.configure(db_session.connection())):
        revision.module.upgrade()

    db_session.execute(text("CREATE TABLE public.private_table_probe (id integer PRIMARY KEY)"))
    for table in (*Base.metadata.tables, "alembic_version", "private_table_probe"):
        for role in ("anon", "authenticated"):
            assert not db_session.scalar(
                text(
                    "SELECT has_table_privilege(:role, :table, "
                    "'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')"
                ),
                {"role": role, "table": f"public.{table}"},
            )

    # Rolling back this revision must not silently restore broad client privileges.
    with Operations.context(MigrationContext.configure(db_session.connection())):
        revision.module.downgrade()
    assert not db_session.scalar(
        text("SELECT has_table_privilege('anon', 'public.users', 'SELECT')")
    )
