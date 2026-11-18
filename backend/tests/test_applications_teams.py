from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.demo.seed import demo_id
from app.models import Application, Membership, Project, User
from app.models.enums import ApplicationStatus, ProjectStatus
from app.modules.collaboration import service
from app.modules.collaboration.schemas import ApplicationCreate
from app.modules.projects.schemas import ProjectCreate, ProjectUpdate
from app.modules.projects.service import ProjectError, write_project
from tests.test_auth import signing_key as signing_key
from tests.test_auth import verifier as verifier
from tests.test_profiles import profiles as profiles
from tests.test_projects import demo as demo

pytestmark = pytest.mark.integration


def project_path(demo):
    return "/projects/" + str(demo_id("project", "campus-access"))


def apply(demo, slug="leo", message="I would like to help"):
    return demo.profiles.client.post(
        project_path(demo) + "/applications", headers=demo.headers(slug), json={"message": message}
    )


def decision(demo, app, status="accepted", slug="maya"):
    return demo.profiles.client.patch(
        "/applications/" + app["id"] + "/decision",
        headers=demo.headers(slug),
        json={"status": status},
    )


def withdraw(demo, app, slug="leo"):
    return demo.profiles.client.patch(
        "/applications/" + app["id"] + "/withdraw", headers=demo.headers(slug), json={}
    )


def test_apply_review_accept_and_private_team_flow(demo):
    client, path = demo.profiles.client, project_path(demo)
    assert client.get(path + "/members", headers=demo.headers("leo")).status_code == 403
    result = apply(demo, message="  Private application message  ")
    assert result.status_code == 201, result.text
    app = result.json()
    assert app["message"] == "Private application message" and app["status"] == "pending"
    assert app["applicant"]["id"] == str(demo.identities["leo"])
    mine = client.get("/me/applications", headers=demo.headers("leo")).json()
    assert mine == {"items": [app], "next_cursor": None}
    assert client.get("/me/applications", headers=demo.headers()).json()["items"] == []
    review = client.get(path + "/applications", headers=demo.headers()).json()
    assert review["items"] == [app]
    accepted = decision(demo, app)
    assert accepted.status_code == 200 and accepted.json()["status"] == "accepted"
    assert decision(demo, app).json() == accepted.json()
    assert client.get(path, headers=demo.headers()).json()["member_count"] == 2
    for slug in ("maya", "leo"):
        roster = client.get(path + "/members", headers=demo.headers(slug)).json()
        assert roster["member_count"] == 2
        assert {item["user"]["id"] for item in roster["items"]} == {
            str(demo.identities["maya"]),
            str(demo.identities["leo"]),
        }
        assert sum(item["is_owner"] for item in roster["items"]) == 1
        assert all(
            set(item["user"]) == {"id", "display_name", "role", "faculty_verified"}
            for item in roster["items"]
        )
    # Starting makes the project private while preserving member access.
    assert (
        client.patch(
            path + "/status", headers=demo.headers(), json={"status": "in_progress"}
        ).status_code
        == 200
    )
    assert client.get(path, headers=demo.headers("leo")).status_code == 200
    assert client.get(path, headers=demo.headers("noah")).status_code == 404
    assert client.get(path + "/members", headers=demo.headers("noah")).status_code == 404
    assert withdraw(demo, app).status_code == 409
    assert decision(demo, app, "rejected").status_code == 409


def test_withdraw_resubmit_same_record_and_reject_final(demo):
    app = apply(demo).json()
    assert apply(demo).status_code == 409
    first = withdraw(demo, app)
    assert first.status_code == 200 and first.json()["status"] == "withdrawn"
    assert withdraw(demo, app).json() == first.json()
    assert decision(demo, app).status_code == 409
    resubmitted = apply(demo, message="New message")
    assert resubmitted.status_code == 200
    assert resubmitted.json()["id"] == app["id"] and resubmitted.json()["message"] == "New message"
    assert resubmitted.json()["created_at"] == app["created_at"]
    rejected = decision(demo, app, "rejected")
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected"
    assert decision(demo, app, "rejected").json() == rejected.json()
    assert withdraw(demo, app).status_code == 409
    assert apply(demo).status_code == 409


@pytest.mark.parametrize("status", ["draft", "in_progress", "completed", "archived"])
def test_closed_project_submission_hidden_and_acceptance_rejected(demo, status):
    client, path = demo.profiles.client, project_path(demo)
    app = apply(demo).json()
    demo.profiles.connection.execute(
        text("UPDATE projects SET status=:s WHERE id=:id"),
        {"s": status, "id": app["project"]["id"]},
    )
    assert apply(demo, "noah").status_code == 404
    assert decision(demo, app).status_code == 409
    assert withdraw(demo, app).status_code == 200
    assert (
        client.get("/me/applications", headers=demo.headers("leo")).json()["items"][0]["status"]
        == "withdrawn"
    )
    assert client.get(path + "/applications", headers=demo.headers()).status_code == 200


def test_no_owner_member_or_full_team_applications(demo):
    client, path = demo.profiles.client, project_path(demo)
    assert apply(demo, "maya").status_code == 409
    app = apply(demo).json()
    assert decision(demo, app).status_code == 200
    assert apply(demo).status_code == 409
    assert client.patch(path, headers=demo.headers(), json={"max_members": 2}).status_code == 200
    assert apply(demo, "noah").status_code == 409
    another = demo.profiles.connection.execute(
        text("SELECT count(*) FROM applications WHERE project_id=:id"), {"id": app["project"]["id"]}
    ).scalar_one()
    assert another == 1


def test_full_team_keeps_losing_application_pending(demo):
    first, second = apply(demo).json(), apply(demo, "noah").json()
    demo.profiles.client.patch(project_path(demo), headers=demo.headers(), json={"max_members": 2})
    assert decision(demo, first).status_code == 200
    assert decision(demo, second).status_code == 409
    assert (
        demo.profiles.client.get("/me/applications", headers=demo.headers("noah")).json()["items"][
            0
        ]["status"]
        == "pending"
    )
    assert decision(demo, second, "rejected").status_code == 200


@pytest.mark.parametrize("role", ["student", "faculty", "administrator"])
def test_applications_are_private_and_decisions_have_no_role_bypass(demo, role):
    client, path = demo.profiles.client, project_path(demo)
    app = apply(demo).json()
    demo.profiles.connection.execute(
        text("UPDATE users SET role=:r WHERE id=:id"), {"r": role, "id": demo.identities["noah"]}
    )
    assert client.get(path + "/applications", headers=demo.headers("leo")).status_code == 403
    assert client.get(path + "/applications", headers=demo.headers("noah")).status_code == 403
    assert client.get(path + "/members", headers=demo.headers("noah")).status_code == 403
    assert decision(demo, app, slug="leo").status_code == 403
    assert decision(demo, app, slug="noah").status_code == 404
    assert withdraw(demo, app, "maya").status_code == 403
    assert withdraw(demo, app, "noah").status_code == 404
    assert (
        client.get(
            "/me/applications",
            headers=demo.headers("noah"),
            params={"project_id": app["project"]["id"]},
        ).json()["items"]
        == []
    )
    for body in (
        client.get(path, headers=demo.headers()).json(),
        client.get("/projects", headers=demo.headers("noah")).json(),
    ):
        assert "I would like to help" not in str(body)
    assert decision(demo, {"id": str(uuid4())}).status_code == 404


def test_members_can_leave_owner_can_remove_and_history_does_not_rejoin(demo):
    client, path = demo.profiles.client, project_path(demo)
    app = apply(demo).json()
    decision(demo, app)
    owner_id, member_id = str(demo.identities["maya"]), str(demo.identities["leo"])
    assert client.delete(path + "/members/" + owner_id, headers=demo.headers()).status_code == 409
    assert (
        client.delete(path + "/members/" + owner_id, headers=demo.headers("leo")).status_code == 403
    )
    assert (
        client.delete(path + "/members/" + member_id, headers=demo.headers("noah")).status_code
        == 403
    )
    # A member cannot remove a teammate, even if both have private-project access.
    second = apply(demo, "noah").json()
    decision(demo, second)
    assert (
        client.delete(
            path + "/members/" + str(demo.identities["noah"]), headers=demo.headers("leo")
        ).status_code
        == 403
    )
    removed = client.delete(path + "/members/" + member_id, headers=demo.headers("leo"))
    assert removed.status_code == 200 and removed.json()["removed"] is True
    assert decision(demo, app).json()["status"] == "accepted"
    assert client.get(path, headers=demo.headers()).json()["member_count"] == 2
    assert apply(demo).status_code == 409
    assert client.get(path + "/members", headers=demo.headers("leo")).status_code == 403
    target = str(demo.identities["noah"])
    assert (
        client.delete(path + "/members/" + target, headers=demo.headers()).json()["removed"] is True
    )
    assert (
        client.delete(path + "/members/" + target, headers=demo.headers()).json()["removed"]
        is False
    )
    assert decision(demo, second).status_code == 200
    assert client.get(path, headers=demo.headers()).json()["member_count"] == 1


def test_archived_roster_is_read_only_and_pending_withdrawal_remains_available(demo):
    client, path = demo.profiles.client, project_path(demo)
    accepted, pending = apply(demo).json(), apply(demo, "noah").json()
    decision(demo, accepted)
    client.patch(path + "/status", headers=demo.headers(), json={"status": "archived"})
    assert (
        client.delete(
            path + "/members/" + str(demo.identities["leo"]), headers=demo.headers()
        ).status_code
        == 409
    )
    assert (
        client.delete(
            path + "/members/" + str(demo.identities["leo"]), headers=demo.headers("leo")
        ).status_code
        == 409
    )
    assert decision(demo, pending, "rejected").status_code == 409
    assert decision(demo, accepted).status_code == 200
    assert withdraw(demo, pending, "noah").status_code == 200


@pytest.mark.parametrize(
    "body",
    [
        {"message": "x" * 2001},
        {"message": 123},
        {"applicant_id": str(uuid4())},
        {"status": "accepted"},
        {"project_id": str(uuid4())},
        {"owner_id": str(uuid4())},
    ],
)
def test_application_request_validation(demo, body):
    result = demo.profiles.client.post(
        project_path(demo) + "/applications", headers=demo.headers("leo"), json=body
    )
    assert result.status_code == 422
    assert demo.profiles.connection.scalar(text("SELECT count(*) FROM applications")) == 0


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"status": "withdrawn"},
        {"status": "pending"},
        {"status": None},
        {"status": "accepted", "applicant_id": str(uuid4())},
    ],
)
def test_decision_request_validation(demo, body):
    app = apply(demo).json()
    result = demo.profiles.client.patch(
        "/applications/" + app["id"] + "/decision", headers=demo.headers(), json=body
    )
    assert result.status_code == 422
    assert (
        demo.profiles.connection.scalar(
            select(Application.status).where(Application.id == app["id"])
        )
        == ApplicationStatus.PENDING
    )


def test_default_and_null_messages(demo):
    client, path = demo.profiles.client, project_path(demo)
    result = client.post(path + "/applications", headers=demo.headers("leo"), json={})
    assert result.status_code == 201 and result.json()["message"] is None
    result = client.post(
        path + "/applications", headers=demo.headers("noah"), json={"message": None}
    )
    assert result.status_code == 201 and result.json()["message"] is None


def test_cursor_filters_and_public_roster_fields(demo):
    client, path = demo.profiles.client, project_path(demo)
    apps = [apply(demo, slug).json() for slug in ("leo", "noah", "jordan")]
    ids = []
    cursor = None
    while True:
        page = client.get(
            path + "/applications",
            headers=demo.headers(),
            params={"limit": 1, **({"cursor": cursor} if cursor else {})},
        ).json()
        ids.extend(item["id"] for item in page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert ids == sorted({app["id"] for app in apps})
    decision(demo, apps[0])
    rejected = decision(demo, apps[1], "rejected").json()
    filtered = client.get(path + "/applications?status=rejected", headers=demo.headers()).json()
    assert filtered["items"] == [rejected] and filtered["next_cursor"] is None
    mine = client.get(
        "/me/applications",
        headers=demo.headers("leo"),
        params={"project_id": apps[0]["project"]["id"], "status": "accepted", "limit": 1},
    ).json()
    assert mine["items"][0]["id"] == apps[0]["id"] and mine["next_cursor"] is None
    ids, cursor = [], None
    while True:
        page = client.get(
            path + "/members",
            headers=demo.headers(),
            params={"limit": 1, **({"cursor": cursor} if cursor else {})},
        ).json()
        ids += [item["user"]["id"] for item in page["items"]]
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert ids == sorted([str(demo.identities["maya"]), str(demo.identities["leo"])])
    for query in ("limit=0", "limit=101", "cursor=bad", "status=bad", "project_id=bad"):
        assert client.get("/me/applications?" + query, headers=demo.headers()).status_code == 422


def test_all_routes_reject_missing_or_deleted_identity(demo):
    client, path = demo.profiles.client, project_path(demo)
    app = apply(demo).json()
    for method, url, body in [
        ("post", path + "/applications", {}),
        ("get", "/me/applications", None),
        ("get", path + "/applications", None),
        ("get", path + "/members", None),
        ("patch", "/applications/" + app["id"] + "/decision", {"status": "accepted"}),
        ("patch", "/applications/" + app["id"] + "/withdraw", {}),
        ("delete", path + "/members/" + str(demo.identities["leo"]), None),
    ]:
        kwargs = {"json": body} if body is not None else {}
        assert client.request(method, url, **kwargs).status_code == 401
        assert (
            client.request(
                method, url, headers=demo.profiles.headers(uuid4()), **kwargs
            ).status_code
            == 401
        )


def test_missing_owner_backfill_blocks_submission_and_acceptance(demo):
    app = apply(demo).json()
    demo.profiles.connection.execute(
        delete(Membership).where(Membership.user_id == demo.identities["maya"])
    )
    assert apply(demo, "noah").status_code == 409
    assert decision(demo, app).status_code == 409


def test_membership_insert_failure_rolls_back_acceptance(demo, monkeypatch):
    from sqlalchemy import event

    app = apply(demo).json()

    def fail(connection, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO memberships"):
            raise RuntimeError("Simulated membership failure")

    event.listen(demo.profiles.connection, "before_cursor_execute", fail)
    try:
        with pytest.raises(RuntimeError, match="Simulated membership failure"):
            decision(demo, app)
    finally:
        event.remove(demo.profiles.connection, "before_cursor_execute", fail)
    assert (
        demo.profiles.connection.scalar(
            select(Application.status).where(Application.id == app["id"])
        )
        == ApplicationStatus.PENDING
    )
    assert (
        demo.profiles.connection.scalar(
            select(func.count())
            .select_from(Membership)
            .where(Membership.project_id == app["project"]["id"])
        )
        == 1
    )


@pytest.fixture(params=[False, True], ids=["owner-first", "applicant-first"])
def race(migrated_engine, request):
    ids = sorted([uuid4(), uuid4(), uuid4()])
    owner, first, second = (ids[2], ids[1], ids[0]) if request.param else ids
    users = [owner, first, second]
    with Session(migrated_engine) as session, session.begin():
        session.add_all(User(id=id_) for id_ in users)
    with Session(migrated_engine) as session:
        project = write_project(
            session,
            owner,
            changes=ProjectCreate(title="Race", description="Local test", max_members=2),
        )
        write_project(session, owner, project_id=project.id, status=ProjectStatus.OPEN)
        apps = [
            service.submit(session, user, project.id, ApplicationCreate())[0]
            for user in (first, second)
        ]
    try:
        yield migrated_engine, project, users, apps
    finally:
        with Session(migrated_engine) as session, session.begin():
            session.execute(delete(Project).where(Project.id == project.id))
            session.execute(delete(User).where(User.id.in_(users)))


def parallel(actions):
    gate = Barrier(len(actions))

    def run(action):
        gate.wait(timeout=5)
        try:
            return action()
        except (service.CollaborationError, ProjectError) as exc:
            return exc

    with ThreadPoolExecutor(max_workers=len(actions)) as pool:
        futures = [pool.submit(run, action) for action in actions]
        return [future.result(timeout=15) for future in futures]


def test_concurrent_acceptances_cannot_take_same_last_place(race):
    engine, project, (owner, _, _), apps = race

    def accept(app):
        with Session(engine) as session:
            return service.decide(session, owner, app.id, ApplicationStatus.ACCEPTED)

    results = parallel([lambda: accept(apps[0]), lambda: accept(apps[1])])
    assert sum(isinstance(result, service.CollaborationError) for result in results) == 1
    assert [
        result.status for result in results if isinstance(result, service.CollaborationError)
    ] == [409]
    with Session(engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(Membership)
                .where(Membership.project_id == project.id)
            )
            == 2
        )
        statuses = list(
            session.scalars(select(Application.status).where(Application.project_id == project.id))
        )
        assert sorted(statuses) == ["accepted", "pending"]
        accepted = session.scalar(
            select(Application).where(
                Application.project_id == project.id,
                Application.status == ApplicationStatus.ACCEPTED,
            )
        )
        accepted_id = accepted.id
    with Session(engine) as session:
        service.decide(session, owner, accepted_id, ApplicationStatus.ACCEPTED)
    with Session(engine) as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(Membership)
                .where(Membership.project_id == project.id)
            )
            == 2
        )


def test_acceptance_and_withdrawal_resolve_without_deadlock(race):
    engine, project, (owner, applicant, _), apps = race

    def accept():
        with Session(engine) as session:
            return service.decide(session, owner, apps[0].id, ApplicationStatus.ACCEPTED)

    def cancel():
        with Session(engine) as session:
            return service.withdraw(session, applicant, apps[0].id)

    results = parallel([accept, cancel])
    assert sum(isinstance(result, service.CollaborationError) for result in results) == 1
    with Session(engine) as session:
        status = session.scalar(select(Application.status).where(Application.id == apps[0].id))
        count = session.scalar(
            select(func.count()).select_from(Membership).where(Membership.project_id == project.id)
        )
        assert (status, count) in [
            (ApplicationStatus.ACCEPTED, 2),
            (ApplicationStatus.WITHDRAWN, 1),
        ]


def test_capacity_edit_and_acceptance_use_same_project_lock(race):
    engine, project, (owner, _, _), apps = race

    def accept():
        with Session(engine) as session:
            return service.decide(session, owner, apps[0].id, ApplicationStatus.ACCEPTED)

    def shrink():
        with Session(engine) as session:
            return write_project(
                session, owner, project_id=project.id, changes=ProjectUpdate(max_members=1)
            )

    results = parallel([accept, shrink])
    assert (
        sum(isinstance(result, (service.CollaborationError, ProjectError)) for result in results)
        == 1
    )
    with Session(engine) as session:
        capacity = session.get(Project, project.id).max_members
        count = session.scalar(
            select(func.count()).select_from(Membership).where(Membership.project_id == project.id)
        )
        assert count <= capacity
