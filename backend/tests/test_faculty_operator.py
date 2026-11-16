import json
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR, Settings
from app.models import FacultyRoleChange
from app.operators import faculty
from tests.test_auth import signing_key as signing_key
from tests.test_auth import verifier as verifier
from tests.test_profiles import ProfileContext
from tests.test_profiles import profiles as profiles


def change(profiles: ProfileContext, **options):
    profiles.client.get("/me", headers=profiles.headers()).raise_for_status()
    with Session(
        bind=profiles.connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    ) as session:
        return faculty.change_faculty_status(
            session,
            profiles.first,
            status="verified",
            operator="Course operator",
            reason="Faculty identity checked",
            **options,
        )


@pytest.mark.integration
def test_dry_run_and_verified_change_are_audited(profiles: ProfileContext) -> None:
    preview = change(profiles)
    assert preview.changed and not preview.applied and preview.audit_id is None
    assert profiles.client.get("/me", headers=profiles.headers()).json()["role"] == "student"
    assert profiles.connection.scalar(text("SELECT count(*) FROM faculty_role_changes")) == 0
    applied = change(profiles, apply=True)
    me = profiles.client.get("/me", headers=profiles.headers()).json()
    assert me["role"] == "faculty" and me["faculty_verified_at"] is not None
    assert applied.applied and applied.audit_id is not None
    with Session(bind=profiles.connection) as session:
        record = session.get(FacultyRoleChange, applied.audit_id)
        assert record.user_id == profiles.first
        assert record.operator == "Course operator" and record.reason == "Faculty identity checked"
        assert record.database_principal == session.scalar(text("SELECT session_user"))
        assert record.previous_role.value == "student" and record.new_role.value == "faculty"
        assert (
            record.previous_verified_at is None
            and record.new_verified_at == applied.new_verified_at
        )
        assert record.performed_at.tzinfo is not None
    repeated = change(profiles, apply=True)
    assert not repeated.changed and repeated.audit_id is None
    assert repeated.new_verified_at == applied.new_verified_at
    assert profiles.connection.scalar(text("SELECT count(*) FROM faculty_role_changes")) == 1


@pytest.mark.integration
def test_operator_can_remove_verification_or_faculty_status(profiles: ProfileContext) -> None:
    change(profiles, apply=True)
    for status, role in [("unverified", "faculty"), ("student", "student")]:
        with Session(
            bind=profiles.connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        ) as session:
            result = faculty.change_faculty_status(
                session,
                profiles.first,
                status=status,
                operator="Operator",
                reason="Status reviewed",
                apply=True,
            )
        assert result.applied
        me = profiles.client.get("/me", headers=profiles.headers()).json()
        assert me["role"] == role and me["faculty_verified_at"] is None
    assert profiles.connection.scalar(text("SELECT count(*) FROM faculty_role_changes")) == 3


@pytest.mark.integration
def test_audit_failure_rolls_back_role_change(profiles: ProfileContext) -> None:
    profiles.client.get("/me", headers=profiles.headers())
    with Session(
        bind=profiles.connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    ) as session:

        def fail_audit(session, flush_context, instances):
            if any(isinstance(item, FacultyRoleChange) for item in session.new):
                raise RuntimeError("Audit unavailable")

        event.listen(session, "before_flush", fail_audit)
        with pytest.raises(RuntimeError, match="Audit unavailable"):
            faculty.change_faculty_status(
                session,
                profiles.first,
                status="verified",
                operator="Operator",
                reason="Check",
                apply=True,
            )
    me = profiles.client.get("/me", headers=profiles.headers()).json()
    assert me["role"] == "student" and me["faculty_verified_at"] is None
    assert profiles.connection.scalar(text("SELECT count(*) FROM faculty_role_changes")) == 0


@pytest.mark.integration
def test_audit_history_survives_auth_account_deletion(profiles: ProfileContext) -> None:
    applied = change(profiles, apply=True)
    profiles.connection.execute(text("DELETE FROM auth.users WHERE id=:id"), {"id": profiles.first})
    assert profiles.connection.scalar(text("SELECT count(*) FROM users")) == 0
    assert (
        profiles.connection.scalar(
            text("SELECT count(*) FROM faculty_role_changes WHERE id=:id"), {"id": applied.audit_id}
        )
        == 1
    )


@pytest.mark.integration
def test_no_role_changes_through_http_and_no_audit_exposure(profiles: ProfileContext) -> None:
    change(profiles, apply=True)
    client, headers = profiles.client, profiles.headers()
    for body in [{"role": "administrator"}, {"faculty_verified_at": None}, {"operator": "Student"}]:
        assert client.patch("/me/profile", headers=headers, json=body).status_code == 422
    assert client.get("/faculty_role_changes", headers=headers).status_code == 404
    assert client.patch("/me/role", headers=headers, json={"role": "faculty"}).status_code == 404
    me = client.get("/me", headers=headers).json()
    assert me["role"] == "faculty" and "operator" not in me and "reason" not in me


@pytest.mark.integration
def test_missing_and_administrator_accounts_are_rejected(profiles: ProfileContext) -> None:
    for missing in [True, False]:
        if not missing:
            profiles.client.get("/me", headers=profiles.headers())
            profiles.connection.execute(
                text("UPDATE users SET role='administrator' WHERE id=:id"), {"id": profiles.first}
            )
        with Session(
            bind=profiles.connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        ) as session:
            with pytest.raises(faculty.OperatorError):
                faculty.change_faculty_status(
                    session,
                    uuid4() if missing else profiles.first,
                    status="verified",
                    operator="Operator",
                    reason="Check",
                    apply=True,
                )
    assert profiles.connection.scalar(text("SELECT count(*) FROM faculty_role_changes")) == 0


@pytest.mark.parametrize(
    ("operator", "reason"),
    [("", "check"), ("operator", "  "), ("x" * 201, "check"), ("operator", "x" * 2001)],
)
def test_operator_and_reason_are_required_before_database_access(operator, reason) -> None:
    with pytest.raises(faculty.OperatorError), Session() as session:
        faculty.change_faculty_status(
            session, uuid4(), status="verified", operator=operator, reason=reason, apply=True
        )


def test_target_confirmation_checks() -> None:
    local = Settings(_env_file=None, database_url="postgresql+psycopg://localhost/operator_test")
    faculty.validate_target(local, expected_database="operator_test", expected_project_ref=None)
    with pytest.raises(faculty.OperatorError):
        faculty.validate_target(local, expected_database="wrong", expected_project_ref=None)
    hosted = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://postgres.example@aws-test.pooler.supabase.com/postgres?sslmode=require",
        database_password="test-password",
        supabase_url="https://example.supabase.co",
    )
    faculty.validate_target(hosted, expected_database="postgres", expected_project_ref="example")
    for ref in [None, "other"]:
        with pytest.raises(faculty.OperatorError):
            faculty.validate_target(hosted, expected_database="postgres", expected_project_ref=ref)
    for host in ["unrelated.example", "localhost"]:
        settings = Settings(
            _env_file=None, database_url=f"postgresql+psycopg://{host}/operator_test"
        )
        with pytest.raises(faculty.OperatorError):
            faculty.validate_target(
                settings, expected_database="operator_test", expected_project_ref="example"
            )


@pytest.mark.integration
def test_cli_defaults_to_dry_run_and_requires_apply(profiles, monkeypatch, capsys) -> None:
    import sys
    from types import SimpleNamespace

    profiles.client.get("/me", headers=profiles.headers())
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://localhost/operator_test")
    monkeypatch.setattr(faculty, "get_settings", lambda: settings)
    monkeypatch.setattr(
        faculty, "create_database_engine", lambda settings: SimpleNamespace(dispose=lambda: None)
    )
    monkeypatch.setattr(
        faculty,
        "Session",
        lambda engine, **kwargs: Session(
            bind=profiles.connection, join_transaction_mode="create_savepoint", **kwargs
        ),
    )
    args = [
        "faculty",
        "--user-id",
        str(profiles.first),
        "--status",
        "verified",
        "--operator",
        "Operator",
        "--reason",
        "Identity checked",
        "--expected-database",
        "operator_test",
    ]
    for apply in [False, True]:
        monkeypatch.setattr(sys, "argv", args + (["--apply"] if apply else []))
        faculty.main()
        body = json.loads(capsys.readouterr().out)
        assert body["applied"] is apply
    assert profiles.connection.scalar(text("SELECT count(*) FROM faculty_role_changes")) == 1


@pytest.mark.integration
def test_audit_migration_removes_inherited_client_grants(db_session: Session) -> None:
    for role in ("anon", "authenticated"):
        if not db_session.scalar(
            text("SELECT 1 FROM pg_roles WHERE rolname=:role"), {"role": role}
        ):
            db_session.execute(text(f'CREATE ROLE "{role}" NOLOGIN NOSUPERUSER NOBYPASSRLS'))
    db_session.execute(text("DROP TABLE faculty_role_changes"))
    db_session.execute(
        text(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT ALL ON TABLES TO PUBLIC, anon, authenticated"
        )
    )
    revision = ScriptDirectory.from_config(Config(str(BACKEND_DIR / "alembic.ini"))).get_revision(
        "71d9cfa35335"
    )
    with Operations.context(MigrationContext.configure(db_session.connection())):
        revision.module.upgrade()
    for role in ("anon", "authenticated"):
        assert not db_session.scalar(
            text(
                "SELECT has_table_privilege(:role, 'public.faculty_role_changes', "
                "'SELECT,INSERT,UPDATE,DELETE')"
            ),
            {"role": role},
        )
    assert db_session.scalar(
        text(
            "SELECT relrowsecurity FROM pg_class WHERE oid='public.faculty_role_changes'::regclass"
        )
    )


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://postgres.example@db.other.supabase.co/postgres?sslmode=require",
        "postgresql+psycopg://postgres.example@unrelated.supabase.com/postgres?sslmode=require",
        "postgresql+psycopg://localhost/postgres?host=db.example.supabase.co",
    ],
)
def test_target_mismatch_or_query_override_is_rejected(url) -> None:
    settings = Settings(
        _env_file=None,
        database_url=url,
        database_password="test-password",
        supabase_url="https://example.supabase.co",
    )
    with pytest.raises(faculty.OperatorError):
        faculty.validate_target(
            settings, expected_database="postgres", expected_project_ref="example"
        )
