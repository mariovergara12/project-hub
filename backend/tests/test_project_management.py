from importlib import import_module
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import delete, select, text

from app.demo.seed import demo_id, seed_data
from app.models import Membership, Project, ProjectInterest, ProjectSkill
from tests.test_auth import signing_key as signing_key
from tests.test_auth import verifier as verifier
from tests.test_profiles import profiles as profiles
from tests.test_projects import DemoContext
from tests.test_projects import demo as demo

pytestmark = pytest.mark.integration


def create(demo, **values):
    return demo.profiles.client.post(
        "/projects",
        headers=demo.headers(),
        json={"title": " A new project ", "description": " Build something together ", **values},
    )


def test_create_publish_and_owner_only_lifecycle(demo: DemoContext):
    client, headers = demo.profiles.client, demo.headers()
    response = create(demo, max_members=1, weekly_hours=0)
    assert response.status_code == 201, response.text
    project = response.json()
    path = "/projects/" + project["id"]
    assert project["title"] == "A new project"
    assert project["status"] == "draft" and project["member_count"] == 1
    assert project["weekly_hours"] == 0 and project["owner"]["id"] == str(demo.identities["maya"])
    assert client.get(path, headers=demo.headers("leo")).status_code == 404
    assert (
        client.patch(path, headers=demo.headers("leo"), json={"title": "Steal"}).status_code == 404
    )
    for status in ("open", "in_progress", "completed", "archived"):
        result = client.patch(path + "/status", headers=headers, json={"status": status})
        assert result.status_code == 200 and result.json()["status"] == status
        assert (
            client.patch(path + "/status", headers=headers, json={"status": status}).status_code
            == 200
        )
        if status == "open":
            assert client.get(path, headers=demo.headers("leo")).status_code == 200
            assert (
                client.patch(path, headers=demo.headers("leo"), json={"title": "Steal"}).status_code
                == 403
            )
            assert (
                client.patch(
                    path + "/status", headers=demo.headers("leo"), json={"status": "archived"}
                ).status_code
                == 403
            )
    assert client.patch(path, headers=headers, json={}).status_code == 409
    assert (
        client.patch(path + "/status", headers=headers, json={"status": "open"}).status_code == 409
    )


@pytest.mark.parametrize(
    "values",
    [
        {"title": ""},
        {"title": " " * 4},
        {"title": "x" * 201},
        {"description": None},
        {"description": "x" * 10001},
        {"weekly_hours": 169},
        {"weekly_hours": True},
        {"weekly_hours": 1.5},
        {"minimum_experience_years": 101},
        {"max_members": 0},
        {"max_members": 101},
        {"owner_id": str(uuid4())},
        {"status": "open"},
        {"id": str(uuid4())},
        {"skills": None},
        {"interest_ids": None},
        {"project_type": None},
        {"skills": [{"skill_id": str(uuid4()), "required": "true"}]},
    ],
)
def test_create_validation(demo, values):
    assert create(demo, **values).status_code == 422


@pytest.mark.parametrize(
    "field", ["title", "description", "project_type", "skills", "interest_ids"]
)
def test_patch_rejects_explicit_null_but_allows_omission(demo, field):
    path = "/projects/" + create(demo).json()["id"]
    assert (
        demo.profiles.client.patch(path, headers=demo.headers(), json={field: None}).status_code
        == 422
    )
    assert demo.profiles.client.patch(path, headers=demo.headers(), json={}).status_code == 200


def test_requirements_are_atomic_and_patch_can_clear_optional_values(demo):
    client, headers = demo.profiles.client, demo.headers()
    skill = str(demo_id("skills", "python"))
    interest = str(demo_id("interests", "robotics"))
    original = create(
        demo,
        skills=[{"skill_id": skill, "required": False}],
        interest_ids=[interest],
        weekly_hours=5,
        max_members=3,
    ).json()
    path = "/projects/" + original["id"]
    assert original["skills"][0]["required"] is False
    for changes in (
        {"title": "Must rollback", "interest_ids": [str(uuid4())]},
        {"skills": [{"skill_id": str(uuid4())}]},
        {"skills": [{"skill_id": skill}] * 2},
        {"interest_ids": [interest] * 2},
    ):
        assert client.patch(path, headers=headers, json=changes).status_code == 422
        assert client.get(path, headers=headers).json() == original
    updated = client.patch(
        path,
        headers=headers,
        json={
            "title": "Updated",
            "weekly_hours": None,
            "max_members": None,
            "skills": [],
            "interest_ids": [],
        },
    ).json()
    assert updated["skills"] == updated["interests"] == []
    assert updated["weekly_hours"] is None and updated["max_members"] is None
    assert updated["description"] == original["description"]
    assert create(demo, interest_ids=[str(uuid4())]).status_code == 422


def test_capacity_and_invalid_transitions_do_not_change_project(demo):
    client, headers = demo.profiles.client, demo.headers()
    project = create(demo, max_members=3).json()
    demo.profiles.connection.execute(
        text("INSERT INTO memberships(id,project_id,user_id) VALUES (:id,:p,:u)"),
        {"id": uuid4(), "p": project["id"], "u": demo.identities["leo"]},
    )
    path = "/projects/" + project["id"]
    assert (
        client.patch(
            path, headers=headers, json={"max_members": 1, "title": "Rollback"}
        ).status_code
        == 409
    )
    assert client.get(path, headers=headers).json()["title"] == project["title"]
    assert client.patch(path, headers=headers, json={"max_members": 2}).status_code == 200
    assert (
        client.patch(path + "/status", headers=headers, json={"status": "completed"}).status_code
        == 409
    )
    # Membership permits reading, never editing or inclusion in My Projects.
    assert (
        client.patch(path, headers=demo.headers("leo"), json={"title": "Steal"}).status_code == 403
    )
    own = client.get("/me/projects", headers=demo.headers("leo")).json()["items"]
    assert project["id"] not in {p["id"] for p in own}


def test_research_requires_both_faculty_role_and_verification(demo):
    client = demo.profiles.client
    assert create(demo, project_type="research_opportunity").status_code == 403
    # Select a seeded verified faculty without depending on fixture display names.
    identity = demo.profiles.connection.execute(
        text("SELECT id FROM users WHERE role='faculty' LIMIT 1")
    ).scalar_one()
    headers = demo.profiles.headers(identity)
    response = client.post(
        "/projects",
        headers=headers,
        json={"title": "Research", "description": "Study", "project_type": "research_opportunity"},
    )
    assert response.status_code == 201
    path = "/projects/" + response.json()["id"]
    demo.profiles.connection.execute(
        text("UPDATE users SET faculty_verified_at=NULL WHERE id=:id"), {"id": identity}
    )
    assert client.patch(path, headers=headers, json={"title": "No"}).status_code == 403
    assert (
        client.patch(path + "/status", headers=headers, json={"status": "open"}).status_code == 403
    )
    assert (
        client.patch(path, headers=headers, json={"project_type": "student_project"}).status_code
        == 200
    )
    assert (
        client.patch(path + "/status", headers=headers, json={"status": "archived"}).status_code
        == 200
    )


def test_my_projects_paginates_and_filters_only_owned_projects(demo):
    client, headers = demo.profiles.client, demo.headers()
    created = [create(demo).json()["id"] for _ in range(3)]
    ids, cursor = [], None
    while True:
        page = client.get(
            "/me/projects",
            headers=headers,
            params={"limit": 1, **({"cursor": cursor} if cursor else {})},
        ).json()
        assert all(p["owner"]["id"] == str(demo.identities["maya"]) for p in page["items"])
        ids += [p["id"] for p in page["items"]]
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert ids == sorted(set(ids)) and set(created) <= set(ids)
    drafts = client.get("/me/projects?status=draft", headers=headers).json()["items"]
    assert {p["id"] for p in drafts} == set(created)
    for method, path, body in [
        ("post", "/projects", {}),
        ("patch", "/projects/" + str(uuid4()), {}),
        ("patch", "/projects/" + str(uuid4()) + "/status", {"status": "open"}),
    ]:
        assert getattr(client, method)(path, json=body).status_code == 401
    assert client.get("/me/projects").status_code == 401
    assert (
        client.post(
            "/projects",
            headers=demo.profiles.headers(uuid4()),
            json={"title": "Missing", "description": "Identity"},
        ).status_code
        == 401
    )


def test_seed_preserves_edited_and_cleared_project_links(db_session):
    from app.demo.seed import DATA

    identities = {u["slug"]: demo_id("user", u["slug"]) for u in DATA["users"]}
    seed_data(db_session, identities)
    project_id = demo_id("project", "campus-access")
    db_session.execute(delete(ProjectSkill).where(ProjectSkill.project_id == project_id))
    db_session.execute(delete(ProjectInterest).where(ProjectInterest.project_id == project_id))
    seed_data(db_session, identities)
    assert (
        list(db_session.scalars(select(ProjectSkill).where(ProjectSkill.project_id == project_id)))
        == []
    )
    assert (
        list(
            db_session.scalars(
                select(ProjectInterest).where(ProjectInterest.project_id == project_id)
            )
        )
        == []
    )
    assert len(list(db_session.scalars(select(Membership)))) == 10


def test_owner_backfill_preserves_existing_members_and_rejects_full_teams(db_session):
    from app.demo.seed import DATA

    identities = {u["slug"]: demo_id("user", u["slug"]) for u in DATA["users"]}
    seed_data(db_session, identities)
    module = import_module("migrations.versions.9eb18a4d2620_backfill_owner_memberships")
    project = db_session.get(Project, demo_id("project", "campus-access"))
    owner = db_session.scalar(select(Membership).where(Membership.project_id == project.id))
    old_id = owner.id
    with Operations.context(MigrationContext.configure(db_session.connection())):
        module.upgrade()
        assert db_session.get(Membership, old_id) is not None
        db_session.execute(delete(Membership).where(Membership.id == old_id))
        module.upgrade()
        restored = db_session.scalar(select(Membership).where(Membership.project_id == project.id))
        assert restored.user_id == project.owner_id
        db_session.execute(delete(Membership).where(Membership.project_id == project.id))
        project.max_members = 1
        db_session.add(Membership(project_id=project.id, user_id=identities["leo"]))
        db_session.flush()
        with (
            pytest.raises(Exception, match="exceeds team capacity"),
            db_session.connection().begin_nested(),
        ):
            module.upgrade()
        assert project.max_members == 1
        assert (
            len(
                list(
                    db_session.scalars(
                        select(Membership).where(Membership.project_id == project.id)
                    )
                )
            )
            == 1
        )


def test_project_update_openapi_omits_null_for_nonnullable_fields(demo):
    schema = demo.profiles.client.get("/openapi.json").json()["components"]["schemas"]
    properties = schema["ProjectUpdate"]["properties"]
    for field in ("title", "description", "project_type", "skills", "interest_ids"):
        assert "default" not in properties[field]
        assert not any(
            branch.get("type") == "null" for branch in properties[field].get("anyOf", [])
        )
    assert any(branch.get("type") == "null" for branch in properties["max_members"]["anyOf"])


@pytest.mark.parametrize(
    "role,verified", [("student", True), ("faculty", False), ("administrator", True)]
)
def test_research_creation_has_no_role_or_verification_bypass(demo, role, verified):
    demo.profiles.connection.execute(
        text(
            "UPDATE users SET role=:role, "
            "faculty_verified_at=CASE WHEN :verified THEN now() ELSE NULL END WHERE id=:id"
        ),
        {"role": role, "verified": verified, "id": demo.identities["maya"]},
    )
    assert create(demo, project_type="research_opportunity").status_code == 403


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        ("draft", "open", 200),
        ("draft", "completed", 409),
        ("draft", "archived", 200),
        ("open", "draft", 409),
        ("open", "completed", 409),
        ("open", "archived", 200),
        ("in_progress", "open", 409),
        ("in_progress", "archived", 200),
        ("completed", "open", 409),
        ("completed", "in_progress", 409),
        ("completed", "archived", 200),
        ("archived", "draft", 409),
        ("archived", "archived", 200),
    ],
)
def test_status_contract(demo, before, after, expected):
    project = create(demo).json()
    demo.profiles.connection.execute(
        text("UPDATE projects SET status=:s WHERE id=:id"), {"s": before, "id": project["id"]}
    )
    result = demo.profiles.client.patch(
        "/projects/" + project["id"] + "/status", headers=demo.headers(), json={"status": after}
    )
    assert result.status_code == expected
    saved = demo.profiles.client.get("/projects/" + project["id"], headers=demo.headers()).json()
    assert saved["status"] == (after if expected == 200 else before)


def test_database_failure_rolls_back_project_and_links(demo, monkeypatch):
    from app.modules.projects import repository

    original = repository.replace_requirements
    project = create(demo).json()
    path = "/projects/" + project["id"]
    count = demo.profiles.connection.scalar(text("SELECT count(*) FROM projects"))
    memberships = demo.profiles.connection.scalar(text("SELECT count(*) FROM memberships"))

    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("Simulated link failure")

    monkeypatch.setattr(repository, "replace_requirements", fail)
    with pytest.raises(RuntimeError, match="Simulated link failure"):
        create(demo)
    assert demo.profiles.connection.scalar(text("SELECT count(*) FROM projects")) == count
    assert demo.profiles.connection.scalar(text("SELECT count(*) FROM memberships")) == memberships
    with pytest.raises(RuntimeError, match="Simulated link failure"):
        demo.profiles.client.patch(path, headers=demo.headers(), json={"title": "Rollback"})
    assert demo.profiles.client.get(path, headers=demo.headers()).json() == project


def test_concurrent_project_edits_never_mix_fields_and_requirements(migrated_engine):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from sqlalchemy.orm import Session

    from app.models import Skill, User
    from app.modules.projects.schemas import ProjectCreate, ProjectSkillInput, ProjectUpdate
    from app.modules.projects.service import write_project

    owner, skills = uuid4(), [uuid4(), uuid4()]
    with Session(migrated_engine) as session, session.begin():
        session.add(User(id=owner))
        session.add_all(Skill(id=id_, name="project-edit-" + id_.hex) for id_ in skills)
    with Session(migrated_engine) as session:
        project = write_project(
            session, owner, changes=ProjectCreate(title="Concurrent", description="Test")
        )
    gate = Barrier(2)

    def edit(index):
        with Session(migrated_engine) as session:
            gate.wait(timeout=5)
            return write_project(
                session,
                owner,
                project_id=project.id,
                changes=ProjectUpdate(
                    title=f"Edit {index}", skills=[ProjectSkillInput(skill_id=skills[index])]
                ),
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(edit, index) for index in range(2)]
            for future in futures:
                result = future.result(timeout=10)
                assert len(result.skills) == 1
        with Session(migrated_engine) as session:
            saved = session.get(Project, project.id)
            selected = session.scalar(
                select(ProjectSkill.skill_id).where(ProjectSkill.project_id == project.id)
            )
            assert selected == skills[int(saved.title[-1])]
    finally:
        with Session(migrated_engine) as session, session.begin():
            session.execute(delete(Project).where(Project.id == project.id))
            session.execute(delete(User).where(User.id == owner))
            session.execute(delete(Skill).where(Skill.id.in_(skills)))
