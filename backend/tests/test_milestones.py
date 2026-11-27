from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import delete, event, select
from sqlalchemy.orm import Session

from app.demo.seed import demo_id
from app.models import Membership, Milestone, Project
from app.modules.collaboration import service as collaboration
from app.modules.milestones import service
from app.modules.milestones.schemas import MilestoneCreate, MilestoneUpdate
from tests.test_applications_teams import apply, decision, project_path
from tests.test_applications_teams import race as race
from tests.test_auth import signing_key as signing_key
from tests.test_auth import verifier as verifier
from tests.test_profiles import profiles as profiles
from tests.test_projects import demo as demo

pytestmark = pytest.mark.integration


def create(demo, slug="maya", **changes):
    response = demo.profiles.client.post(
        project_path(demo) + "/milestones",
        headers=demo.headers(slug),
        json={"title": "First prototype", **changes},
    )
    assert response.status_code == 201, response.text
    return response.json()


def page(demo, slug="maya", **query):
    response = demo.profiles.client.get(
        project_path(demo) + "/milestones", headers=demo.headers(slug), params=query
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_owner_crud_calendar_dates_optional_clearing_and_reopening(demo):
    client, headers = demo.profiles.client, demo.headers()
    assert page(demo)["progress"] == {"total": 0, "todo": 0, "in_progress": 0, "completed": 0}
    value = create(
        demo, title="  First prototype  ", description="  Outline  ", due_date="2028-02-29"
    )
    assert value["title"] == "First prototype" and value["description"] == "Outline"
    assert value["due_date"] == "2028-02-29" and value["status"] == "todo"
    assert value["created_at"] and value["updated_at"]
    path = "/milestones/" + value["id"]
    result = client.patch(path, headers=headers, json={"status": "completed"}).json()
    assert result["title"] == value["title"] and result["due_date"] == "2028-02-29"
    assert page(demo)["progress"]["completed"] == 1
    result = client.patch(
        path, headers=headers, json={"description": None, "due_date": None, "status": "in_progress"}
    )
    assert result.status_code == 200 and result.json()["description"] is None
    assert result.json()["due_date"] is None
    assert page(demo)["progress"] == {"total": 1, "todo": 0, "in_progress": 1, "completed": 0}
    deleted = client.delete(path, headers=headers)
    assert deleted.status_code == 204 and not deleted.content
    assert page(demo)["items"] == []
    assert page(demo)["progress"]["total"] == 0
    assert client.patch(path, headers=headers, json={"title": "Missing"}).status_code == 404
    assert client.delete(path, headers=headers).status_code == 404


def test_current_members_can_manage_private_project_milestones(demo):
    client, headers = demo.profiles.client, demo.headers("leo")
    assert decision(demo, apply(demo).json()).status_code == 200
    assert (
        client.patch(
            project_path(demo) + "/status", headers=demo.headers(), json={"status": "in_progress"}
        ).status_code
        == 200
    )
    value = create(demo, "leo", description="Private team plan")
    assert page(demo)["items"] == page(demo, "leo")["items"] == [value]
    path = "/milestones/" + value["id"]
    assert client.patch(path, headers=headers, json={"status": "completed"}).status_code == 200
    assert client.delete(path, headers=headers).status_code == 204


@pytest.mark.parametrize("slug", ["leo", "reid", "okafor"])
def test_unrelated_accounts_cannot_read_or_change_even_open_project_milestones(demo, slug):
    value = create(demo, description="Internal plan")
    client, headers = demo.profiles.client, demo.headers(slug)
    path = "/milestones/" + value["id"]
    assert client.get(project_path(demo) + "/milestones", headers=headers).status_code == 404
    assert (
        client.post(
            project_path(demo) + "/milestones", headers=headers, json={"title": "Unwanted"}
        ).status_code
        == 404
    )
    assert client.patch(path, headers=headers, json={"title": "Unwanted"}).status_code == 404
    assert client.delete(path, headers=headers).status_code == 404
    assert page(demo)["items"] == [value]


@pytest.mark.parametrize("remover", ["maya", "leo"])
def test_removal_or_leave_revokes_all_milestone_access_despite_accepted_history(demo, remover):
    client = demo.profiles.client
    application = apply(demo).json()
    assert decision(demo, application).status_code == 200
    value = create(demo, "leo")
    assert (
        client.delete(
            project_path(demo) + "/members/" + str(demo.identities["leo"]),
            headers=demo.headers(remover),
        ).status_code
        == 200
    )
    headers, path = demo.headers("leo"), "/milestones/" + value["id"]
    assert client.get(project_path(demo) + "/milestones", headers=headers).status_code == 404
    assert (
        client.post(
            project_path(demo) + "/milestones", headers=headers, json={"title": "No access"}
        ).status_code
        == 404
    )
    assert client.patch(path, headers=headers, json={"title": "No access"}).status_code == 404
    assert client.delete(path, headers=headers).status_code == 404
    assert page(demo)["items"] == [value]
    assert (
        client.get("/me/applications", headers=headers).json()["items"][0]["status"] == "accepted"
    )


@pytest.mark.parametrize("status", ["completed", "archived"])
@pytest.mark.parametrize("slug", ["maya", "leo"])
def test_closed_projects_remain_readable_but_all_milestone_writes_are_blocked(demo, status, slug):
    client = demo.profiles.client
    assert decision(demo, apply(demo).json()).status_code == 200
    value = create(demo)
    transitions = ["in_progress", "completed"] if status == "completed" else ["archived"]
    for next_status in transitions:
        assert (
            client.patch(
                project_path(demo) + "/status", headers=demo.headers(), json={"status": next_status}
            ).status_code
            == 200
        )
    assert page(demo, slug)["items"] == [value]
    headers, path = demo.headers(slug), "/milestones/" + value["id"]
    assert (
        client.post(
            project_path(demo) + "/milestones", headers=headers, json={"title": "Too late"}
        ).status_code
        == 409
    )
    assert client.patch(path, headers=headers, json={"status": "completed"}).status_code == 409
    assert client.delete(path, headers=headers).status_code == 409
    assert page(demo)["items"] == [value]


def test_draft_owner_can_plan_milestones(demo):
    path = f"/projects/{demo_id('project', 'robotics-workshop')}/milestones"
    result = demo.profiles.client.post(
        path, headers=demo.headers("noah"), json={"title": "Plan workshop"}
    )
    assert result.status_code == 201
    assert demo.profiles.client.get(path, headers=demo.headers("noah")).json()["items"] == [
        result.json()
    ]
    assert demo.profiles.client.get(path, headers=demo.headers()).status_code == 404


def test_pagination_filters_and_progress_cover_only_this_project(demo):
    for status in ["todo", "todo", "in_progress", "completed", "completed"]:
        create(demo, status=status)
    other = f"/projects/{demo_id('project', 'repair-directory')}/milestones"
    assert (
        demo.profiles.client.post(
            other,
            headers=demo.headers("leo"),
            json={"title": "Other project", "status": "completed"},
        ).status_code
        == 201
    )
    expected = {"total": 5, "todo": 2, "in_progress": 1, "completed": 2}
    ids, cursor = [], None
    while True:
        result = page(demo, limit=1, **({"cursor": cursor} if cursor else {}))
        assert result["progress"] == expected
        ids.extend(item["id"] for item in result["items"])
        cursor = result["next_cursor"]
        if cursor is None:
            break
    assert len(set(ids)) == len(ids) == 5 and ids == sorted(ids)
    result = page(demo, status="completed", limit=1)
    assert len(result["items"]) == 1 and result["items"][0]["status"] == "completed"
    assert result["progress"] == expected and result["next_cursor"]
    last = page(demo, status="completed", limit=1, cursor=result["next_cursor"])
    assert len(last["items"]) == 1 and last["next_cursor"] is None


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"title": "   "},
        {"title": None},
        {"title": "x" * 201},
        {"title": 42},
        {"title": "Test", "description": "x" * 10001},
        {"title": "Test", "description": 42},
        {"title": "Test", "status": None},
        {"title": "Test", "status": "done"},
        {"title": "Test", "due_date": "2026-02-30"},
        {"title": "Test", "due_date": "2026-11-27T00:00:00Z"},
        {"title": "Test", "due_date": 1795737600},
        {"title": "Test", "project_id": str(uuid4())},
    ],
)
def test_create_validation_is_atomic(demo, body):
    assert (
        demo.profiles.client.post(
            project_path(demo) + "/milestones", headers=demo.headers(), json=body
        ).status_code
        == 422
    )
    assert page(demo)["progress"]["total"] == 0


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"title": None},
        {"status": None},
        {"title": "  "},
        {"due_date": "bad"},
        {"project_id": str(uuid4())},
    ],
)
def test_invalid_patch_does_not_change_existing_milestone(demo, body):
    value = create(demo)
    assert (
        demo.profiles.client.patch(
            "/milestones/" + value["id"], headers=demo.headers(), json=body
        ).status_code
        == 422
    )
    assert page(demo)["items"] == [value]


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "cursor=bad", "status=done"])
def test_query_validation(demo, query):
    assert (
        demo.profiles.client.get(
            project_path(demo) + "/milestones?" + query, headers=demo.headers()
        ).status_code
        == 422
    )


def test_all_routes_require_auth_and_unknown_resources_are_hidden(demo):
    client = demo.profiles.client
    collection, item = f"/projects/{uuid4()}/milestones", f"/milestones/{uuid4()}"
    for method, path, body in [
        ("get", collection, None),
        ("post", collection, {"title": "Test"}),
        ("patch", item, {"title": "Test"}),
        ("delete", item, None),
    ]:
        kwargs = {"json": body} if body is not None else {}
        assert getattr(client, method)(path, **kwargs).status_code == 401
        assert getattr(client, method)(path, headers=demo.headers(), **kwargs).status_code == 404


def test_removal_rechecks_membership_after_waiting_for_project_lock(race):
    engine, project, (owner, member, _), apps = race
    with Session(engine) as session:
        collaboration.decide(session, owner, apps[0].id, "accepted")
        value = service.create(session, owner, project.id, MilestoneCreate(title="Original"))
    waiting = Event()

    def before_execute(connection, cursor, statement, parameters, context, many):
        if "FROM projects" in statement and "FOR UPDATE" in statement:
            waiting.set()

    def update():
        with Session(engine) as session:
            try:
                return service.change(
                    session, member, value.id, MilestoneUpdate(title="Stale edit")
                )
            except collaboration.CollaborationError as exc:
                return exc

    with Session(engine) as removing:
        removing.scalar(select(Project).where(Project.id == project.id).with_for_update())
        removing.execute(
            delete(Membership).where(
                Membership.project_id == project.id, Membership.user_id == member
            )
        )
        event.listen(engine, "before_cursor_execute", before_execute)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(update)
                reached_lock = waiting.wait(timeout=5)
                removing.commit()
                result = future.result(timeout=10)
                assert reached_lock
        finally:
            event.remove(engine, "before_cursor_execute", before_execute)
    assert isinstance(result, collaboration.CollaborationError) and result.status == 404
    with Session(engine) as session:
        assert session.get(Milestone, value.id).title == "Original"
