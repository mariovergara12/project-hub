from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core import security
from app.core.config import BACKEND_DIR, get_settings
from app.core.database import get_session
from app.main import create_app
from app.modules.auth.verifier import SupabaseTokenVerifier
from tests.test_auth import claims_for, sign_token
from tests.test_auth import signing_key as signing_key
from tests.test_auth import verifier as verifier


@dataclass
class ProfileContext:
    client: TestClient
    connection: Connection
    first: UUID
    second: UUID
    key: EllipticCurvePrivateKey

    def headers(self, user_id: UUID | None = None, **changes: Any) -> dict[str, str]:
        token = sign_token(self.key, claims_for(user_id or self.first) | changes)
        return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def profiles(
    migrated_engine: Engine,
    signing_key: EllipticCurvePrivateKey,
    verifier: SupabaseTokenVerifier,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[ProfileContext]:
    # Only this isolated test transaction gets a minimal provider stub. Application
    # migrations never create auth.users, and the real hosted schema is untouched.
    with migrated_engine.connect() as connection:
        outer = connection.begin()
        connection.exec_driver_sql("CREATE SCHEMA auth")
        connection.exec_driver_sql("CREATE TABLE auth.users (id uuid PRIMARY KEY)")
        scripts = ScriptDirectory.from_config(Config(str(BACKEND_DIR / "alembic.ini")))
        with Operations.context(MigrationContext.configure(connection)):
            scripts.get_revision("cc1194778d46").module.upgrade()
        first, second = uuid4(), uuid4()
        connection.execute(
            text("INSERT INTO auth.users(id) VALUES (:first), (:second)"),
            {"first": first, "second": second},
        )
        factory = sessionmaker(
            bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )

        def sessions() -> Iterator[Session]:
            with factory() as session:
                yield session

        monkeypatch.setattr(security, "get_token_verifier", lambda: verifier)
        get_settings.cache_clear()
        app = create_app()
        app.dependency_overrides[get_session] = sessions
        try:
            with TestClient(app) as client:
                yield ProfileContext(client, connection, first, second, signing_key)
        finally:
            outer.rollback()
            get_settings.cache_clear()


@pytest.mark.integration
def test_self_profile_flow_and_idempotent_provisioning(profiles: ProfileContext) -> None:
    client, headers = profiles.client, profiles.headers()
    for _ in range(2):
        result = client.get("/me", headers=headers)
        assert result.status_code == 200
        assert result.json() == {
            "id": str(profiles.first),
            "role": "student",
            "faculty_verified_at": None,
            "profile": None,
        }
    response = client.patch(
        "/me/profile",
        headers=headers,
        json={"display_name": "  Student  ", "bio": "Hello", "availability_hours": 10},
    )
    assert response.status_code == 200
    assert response.json()["display_name"] == "Student"
    response = client.patch("/me/profile", headers=headers, json={"major": "Computer Science"})
    assert response.status_code == 200
    assert response.json()["display_name"] == "Student"
    assert response.json()["bio"] == "Hello"
    assert client.get("/me", headers=headers).json()["profile"]["major"] == "Computer Science"
    assert profiles.connection.scalar(text("SELECT count(*) FROM public.users")) == 1


@pytest.mark.integration
def test_patch_can_create_profile_without_get(profiles: ProfileContext) -> None:
    response = profiles.client.patch(
        "/me/profile", headers=profiles.headers(), json={"display_name": "New student"}
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == str(profiles.first)


@pytest.mark.integration
@pytest.mark.parametrize(
    "payload",
    [
        {"role": "administrator"},
        {"role": "faculty"},
        {"faculty_verified_at": "2026-10-19T00:00:00Z"},
        {"user_id": str(uuid4())},
        {"id": str(uuid4())},
        {"display_name": "Attempt", "role": "administrator"},
    ],
)
def test_protected_fields_rejected(profiles: ProfileContext, payload: dict) -> None:
    headers = profiles.headers()
    assert profiles.client.get("/me", headers=headers).status_code == 200
    response = profiles.client.patch("/me/profile", headers=headers, json=payload)
    assert response.status_code == 422
    me = profiles.client.get("/me", headers=headers).json()
    assert me["role"] == "student" and me["faculty_verified_at"] is None
    assert me["profile"] is None


@pytest.mark.integration
def test_other_users_remain_private(profiles: ProfileContext) -> None:
    for identity, name in ((profiles.first, "First"), (profiles.second, "Private second")):
        assert (
            profiles.client.patch(
                "/me/profile", headers=profiles.headers(identity), json={"display_name": name}
            ).status_code
            == 200
        )
    response = profiles.client.get("/me", headers=profiles.headers())
    assert response.json()["profile"]["display_name"] == "First"
    assert "Private second" not in response.text
    assert (
        profiles.client.get(f"/users/{profiles.second}", headers=profiles.headers()).status_code
        == 404
    )
    assert (
        profiles.client.patch(
            f"/users/{profiles.second}/profile",
            headers=profiles.headers(),
            json={"display_name": "Hacked"},
        ).status_code
        == 404
    )
    assert (
        profiles.client.patch(
            "/me/profile",
            headers=profiles.headers(),
            json={"user_id": str(profiles.second), "display_name": "Hacked"},
        ).status_code
        == 422
    )
    assert (
        profiles.client.get("/me", headers=profiles.headers(profiles.second)).json()["profile"][
            "display_name"
        ]
        == "Private second"
    )


@pytest.mark.integration
def test_metadata_never_grants_application_privileges(profiles: ProfileContext) -> None:
    response = profiles.client.get(
        "/me",
        headers=profiles.headers(
            user_metadata={"role": "administrator", "faculty_verified_at": "2026-10-19"},
            app_metadata={"role": "administrator"},
        ),
    )
    assert response.status_code == 200
    assert response.json()["role"] == "student"
    assert response.json()["faculty_verified_at"] is None


@pytest.mark.integration
def test_existing_trusted_role_and_verification_are_preserved(profiles: ProfileContext) -> None:
    profiles.connection.execute(
        text(
            "INSERT INTO public.users (id, role, faculty_verified_at) "
            "VALUES (:id, 'faculty', now())"
        ),
        {"id": profiles.first},
    )
    response = profiles.client.get("/me", headers=profiles.headers())
    assert response.status_code == 200
    assert response.json()["role"] == "faculty"
    assert response.json()["faculty_verified_at"] is not None
    assert (
        profiles.client.patch(
            "/me/profile",
            headers=profiles.headers(),
            json={"display_name": "Faculty", "bio": "About me"},
        ).status_code
        == 200
    )
    response = profiles.client.patch("/me/profile", headers=profiles.headers(), json={"bio": None})
    assert response.status_code == 200 and response.json()["bio"] is None
    assert profiles.client.get("/me", headers=profiles.headers()).json()["role"] == "faculty"


@pytest.mark.integration
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"display_name": None},
        {"display_name": "   "},
        {"display_name": "x" * 151},
        {"display_name": "Student", "availability_hours": -1},
        {"display_name": "Student", "availability_hours": 169},
        {"display_name": "Student", "availability_hours": True},
        {"display_name": "Student", "experience_years": -1},
    ],
)
def test_invalid_profile_does_not_create_account(profiles: ProfileContext, payload: dict) -> None:
    response = profiles.client.patch("/me/profile", headers=profiles.headers(), json=payload)
    assert response.status_code == 422
    assert profiles.connection.scalar(text("SELECT count(*) FROM public.users")) == 0


@pytest.mark.integration
def test_missing_deleted_auth_identity_cannot_be_provisioned(profiles: ProfileContext) -> None:
    assert (
        profiles.client.patch(
            "/me/profile", headers=profiles.headers(), json={"display_name": "Student"}
        ).status_code
        == 200
    )
    profiles.connection.execute(
        text("DELETE FROM auth.users WHERE id = :id"), {"id": profiles.first}
    )
    assert profiles.connection.scalar(text("SELECT count(*) FROM public.users")) == 0
    assert profiles.connection.scalar(text("SELECT count(*) FROM public.profiles")) == 0
    assert profiles.client.get("/me", headers=profiles.headers()).status_code == 401
    assert (
        profiles.client.patch(
            "/me/profile", headers=profiles.headers(), json={"display_name": "Resurrected"}
        ).status_code
        == 401
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Basic fake"},
        {"Authorization": "Bearer invalid"},
        {"X-User-ID": str(uuid4())},
    ],
)
def test_unauthenticated_requests_rejected(profiles: ProfileContext, headers: dict) -> None:
    for method, path, kwargs in (
        ("GET", "/me", {}),
        ("PATCH", "/me/profile", {"json": {"display_name": "X"}}),
    ):
        response = profiles.client.request(method, path, headers=headers, **kwargs)
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
    assert profiles.connection.scalar(text("SELECT count(*) FROM public.users")) == 0
