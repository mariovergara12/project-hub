from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR


@pytest.mark.integration
def test_external_auth_reference_and_reversible_migration(db_session: Session) -> None:
    # Minimal test-only provider schema, rolled back with the surrounding transaction.
    db_session.execute(text("CREATE SCHEMA auth"))
    db_session.execute(text("CREATE TABLE auth.users (id uuid PRIMARY KEY)"))
    revision = ScriptDirectory.from_config(Config(str(BACKEND_DIR / "alembic.ini"))).get_revision(
        "cc1194778d46"
    )
    with Operations.context(MigrationContext.configure(db_session.connection())):
        revision.module.upgrade()
    fk = next(
        fk
        for fk in inspect(db_session.connection()).get_foreign_keys("users", schema="public")
        if fk["name"] == "fk_users_id_auth_users"
    )
    assert fk["referred_schema"] == "auth" and fk["referred_table"] == "users"
    assert fk["constrained_columns"] == ["id"] and fk["options"]["ondelete"] == "CASCADE"
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(text("INSERT INTO public.users(id) VALUES (:id)"), {"id": uuid4()})
    with Operations.context(MigrationContext.configure(db_session.connection())):
        revision.module.downgrade()
        assert db_session.scalar(text("SELECT to_regclass('auth.users')")) is not None
        revision.module.upgrade()
