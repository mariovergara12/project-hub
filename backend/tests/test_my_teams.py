from uuid import uuid4

import pytest
from sqlalchemy import text

from app.demo.seed import DATA, demo_id
from tests.test_applications_teams import apply, decision, project_path
from tests.test_auth import signing_key as signing_key
from tests.test_auth import verifier as verifier
from tests.test_profiles import profiles as profiles
from tests.test_projects import demo as demo

pytestmark = pytest.mark.integration


def teams(demo, slug="leo", **params):
    response = demo.profiles.client.get("/me/teams", headers=demo.headers(slug), params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_lists_owned_projects_once_without_leaking_other_teams(demo):
    for user in DATA["users"]:
        slug = user["slug"]
        page = teams(demo, slug)
        assert len(page["items"]) == 1
        item = page["items"][0]
        assert item["is_owner"] is True and item["joined_at"]
        assert item["project"]["owner"]["id"] == str(demo.identities[slug])
        assert item["project"]["member_count"] == 1
        assert page["next_cursor"] is None
        assert set(item["project"]["owner"]) == {"id", "display_name", "role", "faculty_verified"}


def test_acceptance_appears_and_leaving_removes_team_but_preserves_history(demo):
    client, path = demo.profiles.client, project_path(demo)
    application = apply(demo).json()
    assert len(teams(demo)["items"]) == 1
    assert decision(demo, application).status_code == 200
    joined = teams(demo)["items"]
    assert len(joined) == 2
    item = next(item for item in joined if not item["is_owner"])
    assert item["project"]["id"] == path.split("/")[-1]
    assert item["project"]["member_count"] == 2 and item["joined_at"]
    assert (
        client.patch(
            path + "/status", headers=demo.headers(), json={"status": "in_progress"}
        ).status_code
        == 200
    )
    assert len(teams(demo, status="in_progress")["items"]) == 2
    assert (
        client.delete(
            path + "/members/" + str(demo.identities["leo"]), headers=demo.headers("leo")
        ).status_code
        == 200
    )
    assert len(teams(demo)["items"]) == 1
    assert (
        client.get("/me/applications", headers=demo.headers("leo")).json()["items"][0]["status"]
        == "accepted"
    )
    assert client.get(path, headers=demo.headers("leo")).status_code == 404


def test_cursor_and_status_filters_never_grant_unrelated_project_access(demo):
    demo.profiles.connection.execute(
        text("INSERT INTO memberships(id, project_id, user_id) VALUES (:id, :project, :user)"),
        {
            "id": uuid4(),
            "project": demo_id("project", "robotics-workshop"),
            "user": demo.identities["leo"],
        },
    )
    first = teams(demo, limit=1)
    assert len(first["items"]) == 1 and first["next_cursor"]
    second = teams(demo, limit=1, cursor=first["next_cursor"])
    assert len(second["items"]) == 1 and second["next_cursor"] is None
    assert first["items"][0]["project"]["id"] < second["items"][0]["project"]["id"]
    assert len(teams(demo, status="draft")["items"]) == 1
    assert teams(demo, status="open")["items"] == []
    assert teams(demo, cursor=str(uuid4()), status="archived")["items"] == []


def test_legacy_owner_without_membership_still_finds_owned_project(demo):
    demo.profiles.connection.execute(
        text("DELETE FROM memberships WHERE user_id=:user"), {"user": demo.identities["maya"]}
    )
    item = teams(demo, "maya")["items"][0]
    assert item["is_owner"] and item["joined_at"] is None


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "cursor=bad", "status=bad"])
def test_query_validation(demo, query):
    assert demo.profiles.client.get("/me/teams?" + query, headers=demo.headers()).status_code == 422


def test_requires_authentication(demo):
    assert demo.profiles.client.get("/me/teams").status_code == 401
