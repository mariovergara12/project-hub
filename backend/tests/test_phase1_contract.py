from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import Settings
from app.demo.seed import demo_id
from app.main import create_app
from tests.test_auth import signing_key as signing_key
from tests.test_auth import verifier as verifier
from tests.test_profiles import ProfileContext
from tests.test_profiles import profiles as profiles
from tests.test_projects import DemoContext
from tests.test_projects import demo as demo

FRONTEND_ORIGIN = "https://project-hub-client-hazel.vercel.app"


def test_openapi_documents_errors_and_bearer_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://localhost/unused")
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    schema = create_app().openapi()
    for path, method in (
        ("/me", "get"),
        ("/me/profile", "patch"),
        ("/projects", "get"),
        ("/projects/{project_id}", "get"),
        ("/skills", "get"),
        ("/interests", "get"),
    ):
        operation = schema["paths"][path][method]
        assert operation["security"] == [{"HTTPBearer": []}]
        for status in ("401", "503"):
            assert operation["responses"][status]["content"]["application/json"]["schema"] == {
                "$ref": "#/components/schemas/ErrorResponse"
            }
    assert "404" in schema["paths"]["/projects/{project_id}"]["get"]["responses"]
    profile_error = schema["components"]["schemas"]["ProfileValidationErrorResponse"]
    assert {item["type"] for item in profile_error["properties"]["detail"]["anyOf"]} == {
        "string",
        "array",
    }
    assert "security" not in schema["paths"]["/health"]["get"]


@pytest.mark.parametrize(
    ("method", "path", "requested_headers"),
    [("GET", "/projects", "authorization"), ("PATCH", "/me/profile", "authorization,content-type")],
)
def test_hosted_origin_cors_and_auth_errors(
    monkeypatch: pytest.MonkeyPatch, method: str, path: str, requested_headers: str
) -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://localhost/unused",
        cors_origins=[FRONTEND_ORIGIN],
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    with TestClient(create_app()) as client:
        for origin, allowed in (
            (FRONTEND_ORIGIN, True),
            (FRONTEND_ORIGIN + ".unrelated.example", False),
        ):
            response = client.options(
                path,
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": method,
                    "Access-Control-Request-Headers": requested_headers,
                },
            )
            assert response.status_code == (200 if allowed else 400)
            assert response.headers.get("access-control-allow-origin") == (
                origin if allowed else None
            )
        # Browser clients must be able to read errors as well as successful responses.
        response = client.request(method, path, headers={"Origin": FRONTEND_ORIGIN})
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid or missing access token"}
        assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN


@pytest.mark.integration
@pytest.mark.parametrize("path", ["/projects", "/skills", "/interests"])
def test_pagination_exact_page_boundary_and_empty_tail(demo: DemoContext, path: str) -> None:
    client, headers = demo.profiles.client, demo.headers()
    complete = client.get(path, headers=headers, params={"limit": 100}).json()
    assert complete["items"] and complete["next_cursor"] is None
    exact = client.get(path, headers=headers, params={"limit": len(complete["items"])}).json()
    assert exact == complete
    tail = client.get(path, headers=headers, params={"cursor": complete["items"][-1]["id"]}).json()
    assert tail == {"items": [], "next_cursor": None}


@pytest.mark.integration
def test_project_nulls_and_empty_links_are_explicit(demo: DemoContext) -> None:
    project_id = demo_id("project", "campus-access")
    connection = demo.profiles.connection
    connection.execute(
        text(
            "UPDATE projects SET weekly_hours=NULL, minimum_experience_years=NULL, "
            "max_members=NULL WHERE id=:id"
        ),
        {"id": project_id},
    )
    for table in ("project_skills", "project_interests"):
        connection.execute(text(f"DELETE FROM {table} WHERE project_id=:id"), {"id": project_id})
    connection.execute(
        text("DELETE FROM profiles WHERE user_id=:id"), {"id": demo.identities["maya"]}
    )
    response = demo.profiles.client.get(f"/projects/{project_id}", headers=demo.headers())
    assert response.status_code == 200
    project = response.json()
    assert all(
        project[field] is None
        for field in ("weekly_hours", "minimum_experience_years", "max_members")
    )
    assert project["owner"]["display_name"] is None
    assert project["skills"] == project["interests"] == []
    assert project["member_count"] == 0
    listed = demo.profiles.client.get("/projects", headers=demo.headers()).json()["items"]
    assert next(item for item in listed if item["id"] == str(project_id)) == project


@pytest.mark.integration
def test_profile_validation_error_shapes_and_null_semantics(profiles: ProfileContext) -> None:
    client, headers = profiles.client, profiles.headers()
    missing_name = client.patch("/me/profile", headers=headers, json={})
    assert missing_name.status_code == 422
    assert missing_name.json() == {"detail": "display_name is required to create a profile"}
    for value in (None, "", "   "):
        invalid = client.patch("/me/profile", headers=headers, json={"display_name": value})
        assert invalid.status_code == 422
        assert isinstance(invalid.json()["detail"], list)
        assert invalid.json()["detail"][0]["loc"] == ["body", "display_name"]
    saved = client.patch(
        "/me/profile",
        headers=headers,
        json={"display_name": "Student", "bio": "Saved", "availability_hours": 0},
    ).json()
    unchanged = client.patch("/me/profile", headers=headers, json={}).json()
    assert unchanged == saved
    cleared = client.patch("/me/profile", headers=headers, json={"bio": None}).json()
    assert cleared == saved | {"bio": None}
    assert client.get("/me", headers=headers).json()["profile"] == cleared


@pytest.mark.integration
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/me"),
        ("PATCH", "/me/profile"),
        ("GET", "/projects"),
        ("GET", f"/projects/{demo_id('project', 'campus-access')}"),
        ("GET", "/skills"),
        ("GET", "/interests"),
    ],
)
def test_expired_token_returns_one_401_without_database_changes(
    profiles: ProfileContext, method: str, path: str
) -> None:
    now = datetime.now(UTC)
    response = profiles.client.request(
        method,
        path,
        headers=profiles.headers(iat=now - timedelta(hours=2), exp=now - timedelta(hours=1)),
        **({"json": {"display_name": "Must not save"}} if method == "PATCH" else {}),
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing access token"}
    assert response.headers["www-authenticate"] == "Bearer"
    assert not response.history
    assert profiles.connection.scalar(text("SELECT count(*) FROM public.users")) == 0
