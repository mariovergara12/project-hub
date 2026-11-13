import json
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import AnyHttpUrl, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.demo.seed import (
    DATA,
    DEMO_TAG,
    AuthAdmin,
    DemoSettings,
    SeedError,
    demo_email,
    demo_id,
    save_accounts,
    seed_data,
    validate_target,
)
from app.models import Interest, Profile, Project, ProjectSkill, Skill, User, UserSkill


@pytest.mark.integration
def test_seed_is_repeatable_and_preserves_edits_and_existing_catalogs(db_session: Session) -> None:
    python_id = uuid4()
    db_session.add(Skill(id=python_id, name="python"))
    db_session.flush()
    identities = {user["slug"]: demo_id("user", user["slug"]) for user in DATA["users"]}
    summary = seed_data(db_session, identities)
    assert summary == {"demo_users": 10, "demo_projects": 10, "skills": 12, "interests": 7}
    project = db_session.get(Project, demo_id("project", "campus-access"))
    project.title = "Frontend developer's local edit"
    db_session.get(Profile, identities["maya"]).bio = "A preserved profile edit"
    db_session.flush()
    counts = [
        db_session.scalar(select(func.count()).select_from(model))
        for model in (User, Profile, Project, Skill, Interest, ProjectSkill, UserSkill)
    ]
    seed_data(db_session, identities)
    db_session.expire_all()
    assert counts == [
        db_session.scalar(select(func.count()).select_from(model))
        for model in (User, Profile, Project, Skill, Interest, ProjectSkill, UserSkill)
    ]
    assert db_session.get(Project, project.id).title == "Frontend developer's local edit"
    assert db_session.get(Profile, identities["maya"]).bio == "A preserved profile edit"
    assert db_session.scalar(select(Skill.id).where(Skill.name == "python")) == python_id
    assert (
        db_session.scalar(
            select(func.count()).select_from(User).where(User.role == "administrator")
        )
        == 0
    )


@pytest.mark.integration
def test_seed_rejects_project_owner_collision(db_session: Session) -> None:
    identities = {user["slug"]: demo_id("user", user["slug"]) for user in DATA["users"]}
    seed_data(db_session, identities)
    project = db_session.get(Project, demo_id("project", "campus-access"))
    project.owner_id = identities["leo"]
    db_session.flush()
    with pytest.raises(SeedError, match="another owner"):
        seed_data(db_session, identities)


def test_auth_provision_is_repeatable_without_password_resets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = AuthAdmin("https://test.supabase.co", "sb_secret_dummy")
    users = {}
    created_payloads = []

    def request(method: str, suffix: str = "", payload: dict | None = None) -> dict:
        if method == "GET":
            return {"users": list(users.values())}
        assert method == "POST" and payload is not None
        created_payloads.append(payload)
        user = {"id": str(uuid4()), **payload}
        users[user["email"]] = user
        return user

    monkeypatch.setattr(admin, "request", request)
    path = tmp_path / "accounts.json"
    first = admin.provision("https://test.supabase.co", path)
    credentials = path.read_text()
    assert admin.provision("https://test.supabase.co", path) == first
    assert len(created_payloads) == 10 and path.read_text() == credentials
    assert path.stat().st_mode & 0o777 == 0o600
    assert all(payload["email_confirm"] is True for payload in created_payloads)
    assert all(payload["app_metadata"]["demo_dataset"] == DEMO_TAG for payload in created_payloads)
    assert len({payload["password"] for payload in created_payloads}) == 10
    assert all("role" not in payload["user_metadata"] for payload in created_payloads)


def test_auth_refuses_to_reuse_unmarked_account(monkeypatch: pytest.MonkeyPatch) -> None:
    admin = AuthAdmin("https://test.supabase.co", "sb_secret_dummy")
    monkeypatch.setattr(
        admin,
        "request",
        lambda *args: {"users": [{"email": demo_email("maya"), "app_metadata": {}}]},
    )
    with pytest.raises(SeedError, match="unmarked"):
        admin.demo_users()


def test_private_credentials_are_replaced_atomically(tmp_path: Path) -> None:
    path = tmp_path / "accounts.json"
    save_accounts({"accounts": {}}, path)
    save_accounts({"accounts": {"demo": {"password": "dummy"}}}, path)
    assert json.loads(path.read_text())["accounts"]["demo"]["password"] == "dummy"
    assert path.stat().st_mode & 0o777 == 0o600


def test_hosted_seed_requires_matching_explicit_target() -> None:
    settings = DemoSettings(
        _env_file=None,
        database_url="postgresql+psycopg://postgres.test:dummy@aws.pooler.supabase.com/postgres?sslmode=require",
        supabase_url="https://test.supabase.co",
        supabase_secret_key="sb_secret_dummy",
    )
    assert "sb_secret_dummy" not in repr(settings)
    assert validate_target(settings, "test") is True
    for ref in (None, "different"):
        with pytest.raises(SeedError):
            validate_target(settings, ref)
    settings.supabase_url = AnyHttpUrl("https://different.supabase.co")
    with pytest.raises(SeedError):
        validate_target(settings, "test")


@pytest.mark.parametrize(
    "origin",
    ["*", "https://user:password@example.com", "https://example.com/path", "https://example.com/"],
)
def test_cors_rejects_non_origins(origin: str) -> None:
    with pytest.raises(ValidationError):
        DemoSettings(
            _env_file=None, database_url="postgresql+psycopg://localhost/db", cors_origins=[origin]
        )
