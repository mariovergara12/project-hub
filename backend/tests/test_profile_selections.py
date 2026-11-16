from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.models import Interest, Skill, User, UserInterest, UserSkill
from app.modules.users import repository, service
from tests.test_auth import signing_key as signing_key
from tests.test_auth import verifier as verifier
from tests.test_profiles import ProfileContext
from tests.test_profiles import profiles as profiles


@pytest.fixture(params=[("skills", "skill_ids"), ("interests", "interest_ids")])
def selection(request, profiles: ProfileContext):
    name, field = request.param
    ids = [uuid4(), uuid4(), uuid4()]
    profiles.connection.execute(
        text(f"INSERT INTO {name}(id, name) VALUES (:id, :name)"),
        [
            {"id": id_, "name": item}
            for id_, item in zip(ids, ("zeta", "alpha", "beta"), strict=True)
        ],
    )
    return profiles, name, field, ids


@pytest.mark.integration
def test_replace_reload_repeat_and_clear(selection) -> None:
    profiles, name, field, ids = selection
    client, headers = profiles.client, profiles.headers()
    assert client.get("/me", headers=headers).json()[name] == []
    expected = [{"id": str(ids[1]), "name": "alpha"}, {"id": str(ids[0]), "name": "zeta"}]
    for _ in range(2):
        response = client.put(f"/me/{name}", headers=headers, json={field: list(map(str, ids[:2]))})
        assert response.status_code == 200
        assert response.json() == {name: expected}
        assert client.get("/me", headers=headers).json()[name] == expected
    response = client.put(f"/me/{name}", headers=headers, json={field: [str(ids[2])]})
    assert response.json() == {name: [{"id": str(ids[2]), "name": "beta"}]}
    assert client.put(f"/me/{name}", headers=headers, json={field: []}).json() == {name: []}
    me = client.get("/me", headers=headers).json()
    assert me[name] == [] and me["role"] == "student" and me["faculty_verified_at"] is None


@pytest.mark.integration
@pytest.mark.parametrize(
    "invalid",
    ["unknown", "duplicate", "missing", "null", "scalar", "malformed", "limit", "owner", "role"],
)
def test_invalid_replacement_leaves_existing_selection_unchanged(selection, invalid) -> None:
    profiles, name, field, ids = selection
    client, headers = profiles.client, profiles.headers()
    saved = client.put(f"/me/{name}", headers=headers, json={field: [str(ids[0])]}).json()[name]
    body = {
        "unknown": {field: [str(ids[1]), str(uuid4())]},
        "duplicate": {field: [str(ids[1]), str(ids[1]).upper()]},
        "missing": {},
        "null": {field: None},
        "scalar": {field: str(ids[0])},
        "malformed": {field: ["not-a-uuid"]},
        "limit": {field: [str(uuid4()) for _ in range(51)]},
        "owner": {field: [str(ids[1])], "user_id": str(profiles.second)},
        "role": {field: [str(ids[1])], "role": "faculty"},
    }[invalid]
    response = client.put(f"/me/{name}", headers=headers, json=body)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], (str, list))
    assert client.get("/me", headers=headers).json()[name] == saved


@pytest.mark.integration
def test_unknown_ids_do_not_provision_a_new_account(selection) -> None:
    profiles, name, field, _ = selection
    assert (
        profiles.client.put(
            f"/me/{name}", headers=profiles.headers(), json={field: [str(uuid4())]}
        ).status_code
        == 422
    )
    assert profiles.connection.scalar(text("SELECT count(*) FROM users")) == 0


@pytest.mark.integration
def test_selection_permissions_and_deleted_identity(selection) -> None:
    profiles, name, field, ids = selection
    client, headers = profiles.client, profiles.headers()
    saved = client.put(f"/me/{name}", headers=headers, json={field: [str(ids[0])]}).json()[name]
    other = profiles.headers(profiles.second)
    assert client.get("/me", headers=other).json()[name] == []
    assert (
        client.put(f"/users/{profiles.first}/{name}", headers=other, json={field: []}).status_code
        == 404
    )
    assert client.put(f"/me/{name}", json={field: []}).status_code == 401
    assert (
        client.put(
            f"/me/{name}", headers={"X-User-ID": str(profiles.first)}, json={field: []}
        ).status_code
        == 401
    )
    assert (
        client.put(f"/me/{name}", headers=profiles.headers(exp=1), json={field: []}).status_code
        == 401
    )
    assert client.get("/me", headers=headers).json()[name] == saved
    profiles.connection.execute(text("DELETE FROM auth.users WHERE id=:id"), {"id": profiles.first})
    assert client.put(f"/me/{name}", headers=headers, json={field: []}).status_code == 401
    assert (
        profiles.connection.scalar(
            text("SELECT count(*) FROM users WHERE id=:id"), {"id": profiles.first}
        )
        == 0
    )


@pytest.mark.integration
def test_write_failure_rolls_back_deleted_links(selection, monkeypatch) -> None:
    profiles, name, field, ids = selection
    client, headers = profiles.client, profiles.headers()
    expected = client.put(f"/me/{name}", headers=headers, json={field: [str(ids[0])]}).json()[name]

    def fail_after_delete(session, user_id, ids, *, skills):
        model = UserSkill if skills else UserInterest
        session.execute(delete(model).where(model.user_id == user_id))
        raise RuntimeError("Simulated insert failure")

    monkeypatch.setattr(repository, "replace_links", fail_after_delete)
    with pytest.raises(RuntimeError, match="Simulated insert failure"):
        client.put(f"/me/{name}", headers=headers, json={field: [str(ids[1])]})
    assert client.get("/me", headers=headers).json()[name] == expected


@pytest.mark.integration
@pytest.mark.parametrize("skills", [True, False])
def test_concurrent_replacements_never_mix_selections(migrated_engine, skills) -> None:
    owner = uuid4()
    ids = [uuid4() for _ in range(4)]
    catalog, link = (Skill, UserSkill) if skills else (Interest, UserInterest)
    with Session(migrated_engine) as setup, setup.begin():
        setup.add(User(id=owner))
        setup.add_all(catalog(id=id_, name="selection-" + id_.hex) for id_ in ids)
    gate = Barrier(2)

    def replace(chosen):
        with Session(migrated_engine, expire_on_commit=False) as session:
            gate.wait(timeout=5)
            return service.replace_selections(session, owner, chosen, skills=skills)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(replace, chosen) for chosen in (ids[:2], ids[2:])]
            for future in futures:
                assert len(future.result(timeout=10)) == 2
        with Session(migrated_engine) as session:
            column = link.skill_id if skills else link.interest_id
            saved = set(session.scalars(select(column).where(link.user_id == owner)))
            assert saved in (set(ids[:2]), set(ids[2:]))
    finally:
        with Session(migrated_engine) as cleanup, cleanup.begin():
            cleanup.execute(delete(User).where(User.id == owner))
            cleanup.execute(delete(catalog).where(catalog.id.in_(ids)))


@pytest.mark.integration
def test_exactly_fifty_catalog_ids_are_accepted(selection) -> None:
    profiles, name, field, _ = selection
    ids = [uuid4() for _ in range(50)]
    profiles.connection.execute(
        text(f"INSERT INTO {name}(id, name) VALUES (:id, :name)"),
        [{"id": id_, "name": "limit-" + id_.hex} for id_ in ids],
    )
    response = profiles.client.put(
        f"/me/{name}", headers=profiles.headers(), json={field: list(map(str, ids))}
    )
    assert response.status_code == 200 and len(response.json()[name]) == 50
    assert {item["id"] for item in response.json()[name]} == set(map(str, ids))


@pytest.mark.integration
def test_replacing_one_catalog_preserves_the_other_and_profile(selection) -> None:
    profiles, name, field, ids = selection
    other = "interests" if name == "skills" else "skills"
    other_field = "interest_ids" if other == "interests" else "skill_ids"
    other_id = uuid4()
    profiles.connection.execute(
        text(f"INSERT INTO {other}(id,name) VALUES (:id, :name)"),
        {"id": other_id, "name": "other-catalog"},
    )
    client, headers = profiles.client, profiles.headers()
    client.patch(
        "/me/profile",
        headers=headers,
        json={"display_name": "Preserved profile", "availability_hours": 0},
    )
    client.put(f"/me/{other}", headers=headers, json={other_field: [str(other_id)]})
    before = client.get("/me", headers=headers).json()
    assert (
        client.put(f"/me/{name}", headers=headers, json={field: [str(ids[1])]}).status_code == 200
    )
    after = client.get("/me", headers=headers).json()
    assert after[other] == before[other] and after["profile"] == before["profile"]
    assert (
        after["role"] == before["role"]
        and after["faculty_verified_at"] == before["faculty_verified_at"]
    )
