from collections.abc import Iterator
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.demo.seed import DATA, demo_id, seed_data
from app.main import create_app
from tests.test_auth import signing_key as signing_key
from tests.test_auth import verifier as verifier
from tests.test_profiles import ProfileContext
from tests.test_profiles import profiles as profiles


@dataclass
class DemoContext:
    profiles: ProfileContext
    identities: dict[str, UUID]

    def headers(self, slug: str = "maya") -> dict[str, str]:
        return self.profiles.headers(self.identities[slug])


@pytest.fixture
def demo(profiles: ProfileContext) -> Iterator[DemoContext]:
    identities = {user["slug"]: demo_id("user", user["slug"]) for user in DATA["users"]}
    identities["maya"] = profiles.first
    identities["leo"] = profiles.second
    for identity in identities.values():
        profiles.connection.execute(
            text("INSERT INTO auth.users(id) VALUES (:id) ON CONFLICT DO NOTHING"),
            {"id": identity},
        )
    with Session(bind=profiles.connection, join_transaction_mode="create_savepoint") as session:
        with session.begin():
            seed_data(session, identities)
    yield DemoContext(profiles, identities)


@pytest.mark.integration
def test_discovery_list_and_detail_include_frontend_fields(demo: DemoContext) -> None:
    client = demo.profiles.client
    response = client.get("/projects", headers=demo.headers())
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 6 and body["next_cursor"] is None
    assert all(item["status"] == "open" for item in body["items"])
    project_id = str(demo_id("project", "campus-access"))
    project = client.get(f"/projects/{project_id}", headers=demo.headers()).json()
    assert project["owner"] == {
        "id": str(demo.identities["maya"]),
        "display_name": "Maya Chen",
        "role": "student",
        "faculty_verified": False,
    }
    assert project["member_count"] == 0
    assert project["weekly_hours"] == 6 and project["max_members"] == 5
    assert {skill["name"]: skill["required"] for skill in project["skills"]} == {
        "react": True,
        "typescript": True,
        "figma": False,
    }
    assert {item["name"] for item in project["interests"]} == {"accessibility", "community"}
    for sensitive in ("email", "bio", "availability_hours", "learning_goals", "applications"):
        assert sensitive not in project["owner"]


@pytest.mark.integration
def test_private_statuses_are_hidden_from_unrelated_users(demo: DemoContext) -> None:
    client = demo.profiles.client
    for slug in ("robotics-workshop", "repair-directory", "pollinator-guide", "study-spaces"):
        project_id = demo_id("project", slug)
        assert client.get(f"/projects/{project_id}", headers=demo.headers()).status_code == 404
    assert client.get(f"/projects/{uuid4()}", headers=demo.headers()).status_code == 404
    assert client.get("/projects?status=draft", headers=demo.headers()).json()["items"] == []
    draft_id = demo_id("project", "robotics-workshop")
    assert client.get(f"/projects/{draft_id}", headers=demo.headers("noah")).status_code == 200
    assert (
        len(client.get("/projects?status=draft", headers=demo.headers("noah")).json()["items"]) == 1
    )


@pytest.mark.integration
def test_team_members_can_read_their_non_open_project(demo: DemoContext) -> None:
    project_id = demo_id("project", "repair-directory")
    demo.profiles.connection.execute(
        text("INSERT INTO memberships(id, project_id, user_id) VALUES (:id, :project, :user)"),
        {"id": uuid4(), "project": project_id, "user": demo.identities["maya"]},
    )
    response = demo.profiles.client.get(f"/projects/{project_id}", headers=demo.headers())
    assert response.status_code == 200 and response.json()["member_count"] == 1
    listed = demo.profiles.client.get("/projects", headers=demo.headers()).json()["items"]
    assert str(project_id) in {item["id"] for item in listed}
    assert (
        demo.profiles.client.get(
            f"/projects/{project_id}", headers=demo.headers("jordan")
        ).status_code
        == 404
    )


@pytest.mark.integration
def test_cursor_pagination_and_filters(demo: DemoContext) -> None:
    client, headers = demo.profiles.client, demo.headers()
    all_ids = []
    cursor = None
    while True:
        params = {"limit": 2}
        if cursor:
            params["cursor"] = cursor
        response = client.get("/projects", headers=headers, params=params)
        assert response.status_code == 200
        page = response.json()
        all_ids.extend(item["id"] for item in page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert len(all_ids) == len(set(all_ids)) == 6
    assert all_ids == sorted(all_ids)
    research = client.get("/projects?project_type=research_opportunity", headers=headers).json()[
        "items"
    ]
    assert len(research) == 2 and all(item["owner"]["faculty_verified"] for item in research)
    assert len(client.get("/projects?q=ACCESSIBILITY", headers=headers).json()["items"]) == 2
    assert client.get("/projects?q=%25", headers=headers).json()["items"] == []
    skill = str(demo_id("skills", "react"))
    interest = str(demo_id("interests", "accessibility"))
    filtered = client.get(
        "/projects", headers=headers, params={"skill_id": skill, "interest_id": interest}
    ).json()["items"]
    assert len(filtered) == 1 and filtered[0]["title"] == "Campus Accessibility Map"
    assert (
        client.get("/projects", headers=headers, params={"skill_id": str(uuid4())}).json()["items"]
        == []
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "query", ["limit=0", "limit=101", "cursor=bad", "status=bad", "q=", "skill_id=bad"]
)
def test_invalid_discovery_queries(demo: DemoContext, query: str) -> None:
    assert demo.profiles.client.get(f"/projects?{query}", headers=demo.headers()).status_code == 422


@pytest.mark.integration
def test_catalogs_are_paginated_and_do_not_expose_user_data(demo: DemoContext) -> None:
    for path in ("/skills", "/interests"):
        response = demo.profiles.client.get(path, headers=demo.headers(), params={"limit": 2})
        page = response.json()
        assert len(page["items"]) == 2 and page["next_cursor"] is not None
        assert all(set(item) == {"id", "name"} for item in page["items"])
        next_page = demo.profiles.client.get(
            path, headers=demo.headers(), params={"limit": 2, "cursor": page["next_cursor"]}
        ).json()
        assert not (
            {item["id"] for item in page["items"]} & {item["id"] for item in next_page["items"]}
        )


@pytest.mark.integration
def test_discovery_rejects_missing_and_deleted_auth_identity(demo: DemoContext) -> None:
    client = demo.profiles.client
    for path in (
        "/projects",
        "/skills",
        "/interests",
        f"/projects/{demo_id('project', 'campus-access')}",
    ):
        assert client.get(path).status_code == 401
        assert (
            client.get(path, headers={"X-User-ID": str(demo.identities["maya"])}).status_code == 401
        )
    missing_id = uuid4()
    assert client.get("/projects", headers=demo.profiles.headers(missing_id)).status_code == 401
    demo.profiles.connection.execute(
        text("INSERT INTO auth.users(id) VALUES (:id)"), {"id": missing_id}
    )
    assert client.get("/projects", headers=demo.profiles.headers(missing_id)).status_code == 200
    demo.profiles.connection.execute(
        text("DELETE FROM auth.users WHERE id=:id"), {"id": missing_id}
    )
    assert client.get("/projects", headers=demo.profiles.headers(missing_id)).status_code == 401


def test_cors_preflight_allows_only_configured_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://localhost/unused",
        cors_origins=["http://localhost:5173"],
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    with TestClient(create_app()) as client:
        for origin, allowed in (
            ("http://localhost:5173", True),
            ("https://unrelated.example", False),
        ):
            response = client.options(
                "/projects",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "authorization",
                },
            )
            assert response.status_code == (200 if allowed else 400)
            assert response.headers.get("access-control-allow-origin") == (
                origin if allowed else None
            )
