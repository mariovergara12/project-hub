from uuid import uuid4

import pytest
from sqlalchemy import event, text

from app.demo.seed import demo_id
from tests.test_auth import signing_key as signing_key
from tests.test_auth import verifier as verifier
from tests.test_profiles import profiles as profiles
from tests.test_projects import demo as demo

pytestmark = pytest.mark.integration


def configure(demo, slug="leo"):
    client, headers = demo.profiles.client, demo.headers(slug)
    for kind, field, value in [
        ("skills", "skill_ids", demo_id("skills", "react")),
        ("interests", "interest_ids", demo_id("interests", "community")),
    ]:
        assert (
            client.put(f"/me/{kind}", headers=headers, json={field: [str(value)]}).status_code
            == 200
        )
    assert (
        client.patch(
            "/me/profile", headers=headers, json={"availability_hours": 6, "experience_years": 2}
        ).status_code
        == 200
    )


def candidate(demo, *, owner="maya", status="open", **changes):
    client, headers = demo.profiles.client, demo.headers(owner)
    result = client.post(
        "/projects",
        headers=headers,
        json={
            "title": "Matching project",
            "description": "Build a community tool",
            "max_members": None,
            "skills": [{"skill_id": str(demo_id("skills", "react")), "required": True}],
            "interest_ids": [str(demo_id("interests", "community"))],
            "weekly_hours": 5,
            "minimum_experience_years": 1,
            **changes,
        },
    )
    assert result.status_code == 201, result.text
    value = result.json()
    steps = {
        "draft": [],
        "open": ["open"],
        "in_progress": ["open", "in_progress"],
        "completed": ["open", "in_progress", "completed"],
        "archived": ["archived"],
    }[status]
    for next_status in steps:
        assert (
            client.patch(
                f"/projects/{value['id']}/status", headers=headers, json={"status": next_status}
            ).status_code
            == 200
        )
    return value["id"]


def recommendations(demo, slug="leo"):
    result = demo.profiles.client.get("/projects/recommended", headers=demo.headers(slug))
    assert result.status_code == 200, result.text
    return result.json()


def ids(demo, slug="leo"):
    return [item["project"]["id"] for item in recommendations(demo, slug)["items"]]


def application(demo, project_id, slug="leo"):
    result = demo.profiles.client.post(
        f"/projects/{project_id}/applications", headers=demo.headers(slug), json={}
    )
    assert result.status_code == 201, result.text
    return result.json()["id"]


def decide(demo, application_id, status):
    result = demo.profiles.client.patch(
        f"/applications/{application_id}/decision", headers=demo.headers(), json={"status": status}
    )
    assert result.status_code == 200, result.text


def test_static_recommended_route_returns_personalized_public_projects(demo):
    configure(demo)
    project_id = candidate(demo)
    body = recommendations(demo)
    match = next(item for item in body["items"] if item["project"]["id"] == project_id)
    assert match["score"] == 100 and len(match["reasons"]) == 4 and match["cautions"] == []
    assert body["missing_fields"] == []
    assert match["project"]["member_count"] == 1
    assert set(match["project"]["owner"]) == {"id", "display_name", "role", "faculty_verified"}
    assert "next_cursor" not in body
    assert recommendations(demo) == body


def test_top_ten_use_score_then_uuid_and_do_not_expand_from_unrecognized_query(demo):
    configure(demo)
    created = [candidate(demo) for _ in range(15)]
    result = recommendations(demo)
    assert [item["score"] for item in result["items"]] == [100] * 10
    assert ids(demo) == sorted(created)[:10]
    response = demo.profiles.client.get(
        f"/projects/recommended?limit=9999&user_id={demo.identities['maya']}",
        headers=demo.headers("leo"),
    )
    assert response.json() == result


@pytest.mark.parametrize("status", ["draft", "in_progress", "completed", "archived"])
def test_private_and_closed_projects_are_excluded_even_if_the_caller_can_see_them(demo, status):
    configure(demo)
    private = candidate(demo, status=status)
    demo.profiles.connection.execute(
        text("INSERT INTO memberships(id, project_id, user_id) VALUES (:id, :project, :user)"),
        {"id": uuid4(), "project": private, "user": demo.identities["leo"]},
    )
    assert (
        demo.profiles.client.get(f"/projects/{private}", headers=demo.headers("leo")).status_code
        == 200
    )
    assert private not in ids(demo)


def test_excludes_full_owned_and_joined_projects_but_keeps_available_and_unlimited(demo):
    configure(demo)
    available = candidate(demo, max_members=2)
    unlimited = candidate(demo)
    full = candidate(demo, max_members=1)
    owned = candidate(demo, owner="leo")
    joined = candidate(demo)
    decide(demo, application(demo, joined), "accepted")
    result = ids(demo)
    assert available in result and unlimited in result
    assert not set([full, owned, joined]) & set(result)


@pytest.mark.parametrize(
    "status, included",
    [("pending", False), ("accepted", False), ("rejected", False), ("withdrawn", True)],
)
def test_only_applications_that_can_be_resubmitted_are_recommended(demo, status, included):
    configure(demo)
    project_id = candidate(demo)
    app_id = application(demo, project_id)
    if status in {"accepted", "rejected"}:
        decide(demo, app_id, status)
    if status == "accepted":
        assert (
            demo.profiles.client.delete(
                f"/projects/{project_id}/members/{demo.identities['leo']}", headers=demo.headers()
            ).status_code
            == 200
        )
    if status == "withdrawn":
        assert (
            demo.profiles.client.patch(
                f"/applications/{app_id}/withdraw", headers=demo.headers("leo"), json={}
            ).status_code
            == 200
        )
    assert (project_id in ids(demo)) is included


def test_another_applicants_history_does_not_change_the_callers_suggestions(demo):
    configure(demo)
    project_id = candidate(demo)
    decide(demo, application(demo, project_id, "noah"), "rejected")
    assert project_id in ids(demo)


def test_legacy_projects_without_owner_membership_are_not_promoted(demo):
    configure(demo)
    project_id = candidate(demo)
    demo.profiles.connection.execute(
        text("DELETE FROM memberships WHERE project_id=:project"), {"project": project_id}
    )
    assert project_id not in ids(demo)


def test_profile_edits_and_selection_replacements_change_scores_without_stale_data(demo):
    configure(demo)
    project_id = candidate(demo)
    client, headers = demo.profiles.client, demo.headers("leo")

    def score():
        return next(
            item["score"]
            for item in recommendations(demo)["items"]
            if item["project"]["id"] == project_id
        )

    assert score() == 100
    assert client.put("/me/skills", headers=headers, json={"skill_ids": []}).status_code == 200
    assert score() == 50
    assert (
        client.put("/me/interests", headers=headers, json={"interest_ids": []}).status_code == 200
    )
    assert score() == 25
    assert (
        client.patch(
            "/me/profile", headers=headers, json={"availability_hours": 0, "experience_years": 0}
        ).status_code
        == 200
    )
    assert project_id not in ids(demo)
    assert (
        client.patch(
            "/me/profile",
            headers=headers,
            json={"availability_hours": None, "experience_years": None},
        ).status_code
        == 200
    )
    assert recommendations(demo) == {
        "items": [],
        "missing_fields": ["skills", "interests", "availability_hours", "experience_years"],
    }


def test_no_profile_signals_returns_setup_state_and_zero_values_are_not_missing(demo):
    client, headers = demo.profiles.client, demo.headers("leo")
    for kind in ["skills", "interests"]:
        field = "skill_ids" if kind == "skills" else "interest_ids"
        assert client.put(f"/me/{kind}", headers=headers, json={field: []}).status_code == 200
    assert (
        client.patch(
            "/me/profile", headers=headers, json={"availability_hours": 0, "experience_years": 0}
        ).status_code
        == 200
    )
    result = recommendations(demo)
    assert result["missing_fields"] == ["skills", "interests"]
    assert all(item["score"] > 0 for item in result["items"])


def test_caution_explains_requirements_without_claiming_a_time_or_experience_match(demo):
    configure(demo)
    project_id = candidate(demo, weekly_hours=10, minimum_experience_years=3)
    result = next(
        item for item in recommendations(demo)["items"] if item["project"]["id"] == project_id
    )
    assert result["score"] == 75
    assert result["cautions"] == [
        "Time: needs 10 hrs/week; you listed 6",
        "Experience: needs 3 years; you listed 2",
    ]
    assert len(result["reasons"]) == 2


def test_reads_are_batched_instead_of_querying_each_candidate(demo):
    configure(demo)

    def select_count():
        statements = []

        def capture(connection, cursor, statement, parameters, context, many):
            if statement.lstrip().startswith("SELECT"):
                statements.append(statement)

        event.listen(demo.profiles.connection, "before_cursor_execute", capture)
        try:
            recommendations(demo)
        finally:
            event.remove(demo.profiles.connection, "before_cursor_execute", capture)
        return len(statements)

    before = select_count()
    for _ in range(20):
        candidate(demo)
    after = select_count()
    assert before == after and after <= 10


def test_requires_auth_and_empty_candidate_lists_are_valid(demo):
    assert demo.profiles.client.get("/projects/recommended").status_code == 401
    configure(demo)
    demo.profiles.connection.execute(text("UPDATE projects SET status='archived'"))
    assert recommendations(demo) == {"items": [], "missing_fields": []}
