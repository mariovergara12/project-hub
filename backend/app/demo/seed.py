"""Run with python -m app.demo.seed; inserts missing demo records without resetting edits."""

import argparse
import json
import os
import secrets
import ssl
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID, uuid5

import certifi
from pydantic import SecretStr
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR, Settings, is_supabase_host
from app.core.database import create_database_engine
from app.models import (
    Interest,
    Profile,
    Project,
    ProjectInterest,
    ProjectSkill,
    Skill,
    User,
    UserInterest,
    UserSkill,
)

NAMESPACE = UUID("22aa00d6-d737-4cd4-9b97-7e779ae7b634")
DEMO_TAG = "project-hub-demo-v1"
ACCOUNTS_FILE = BACKEND_DIR / ".demo-accounts.json"
DATA = json.loads(Path(__file__).with_name("data.json").read_text())


class SeedError(Exception):
    pass


class DemoSettings(Settings):
    # These credentials belong only to this operator tool, never to the running API.
    supabase_secret_key: SecretStr | None = None
    supabase_service_role_key: SecretStr | None = None


def demo_id(kind: str, slug: str) -> UUID:
    return uuid5(NAMESPACE, f"{kind}:{slug}")


def demo_email(slug: str) -> str:
    return f"project-hub-demo-{slug}@example.com"


def save_accounts(accounts: dict, path: Path) -> None:
    """Atomic, owner-only operator handoff. Never write credentials to stdout."""
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            json.dump(accounts, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fchmod(handle.fileno(), 0o600)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


class AuthAdmin:
    def __init__(self, project_url: str, key: str) -> None:
        self.url = project_url.rstrip("/") + "/auth/v1/admin/users"
        self.headers = {"apikey": key, "Content-Type": "application/json"}
        if not key.startswith("sb_secret_"):
            self.headers["Authorization"] = f"Bearer {key}"
        self.context = ssl.create_default_context(cafile=certifi.where())

    def request(self, method: str, suffix: str = "", payload: dict | None = None) -> dict:
        request = Request(
            self.url + suffix,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers=self.headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=15, context=self.context) as response:
                return json.load(response)
        except HTTPError as exc:
            # Provider error bodies may include sensitive data; don't print them.
            raise SeedError(f"Supabase Auth admin request failed (HTTP {exc.code})") from None
        except (URLError, TimeoutError, ValueError):
            raise SeedError(
                "Supabase Auth admin request failed; check connectivity and key"
            ) from None

    def demo_users(self) -> dict[str, dict]:
        emails = {demo_email(user["slug"]) for user in DATA["users"]}
        found = {}
        page = 1
        while True:
            users = self.request("GET", f"?page={page}&per_page=100")["users"]
            for user in users:
                if user.get("email") in emails:
                    if user.get("app_metadata", {}).get("demo_dataset") != DEMO_TAG:
                        raise SeedError(
                            "A demo email belongs to an unmarked account; refusing reuse"
                        )
                    found[user["email"]] = user
            if len(users) < 100:
                return found
            page += 1

    def provision(self, project_url: str, accounts_path: Path = ACCOUNTS_FILE) -> dict[str, UUID]:
        existing = self.demo_users()
        accounts = json.loads(accounts_path.read_text()) if accounts_path.exists() else {}
        if accounts and accounts.get("supabase_url") != project_url.rstrip("/"):
            raise SeedError("Existing demo credential file belongs to another project")
        accounts.setdefault("supabase_url", project_url.rstrip("/"))
        accounts.setdefault("accounts", {})
        identities = {}
        for user in DATA["users"]:
            slug = user["slug"]
            email = demo_email(slug)
            if email not in existing:
                password = secrets.token_urlsafe(24)
                created = self.request(
                    "POST",
                    payload={
                        "email": email,
                        "password": password,
                        "email_confirm": True,
                        "app_metadata": {"demo_dataset": DEMO_TAG},
                        "user_metadata": {"display_name": user["display_name"]},
                    },
                )
                existing[email] = created
                accounts["accounts"][slug] = {
                    "id": created["id"],
                    "email": email,
                    "password": password,
                }
                save_accounts(accounts, accounts_path)
            identity = existing[email]
            identities[slug] = UUID(identity["id"])
            saved = accounts["accounts"].get(slug)
            if saved and saved["id"] != identity["id"]:
                # Never claim an old password works for a replaced identity.
                accounts["accounts"].pop(slug)
                save_accounts(accounts, accounts_path)
        return identities


def insert_missing(session: Session, model: type, values: dict) -> None:
    session.execute(insert(model).values(**values).on_conflict_do_nothing())


def seed_data(session: Session, identities: dict[str, UUID]) -> dict[str, int]:
    """Caller owns the transaction. Reuse canonical catalogs and preserve existing demo edits."""
    for user in DATA["users"]:
        identity = identities[user["slug"]]
        insert_missing(
            session,
            User,
            {
                "id": identity,
                "role": user["role"],
                "faculty_verified_at": (
                    datetime(2026, 11, 1, tzinfo=UTC) if user["role"] == "faculty" else None
                ),
            },
        )
        insert_missing(
            session,
            Profile,
            {
                "user_id": identity,
                "display_name": user["display_name"],
                "university": "Example University",
                "major": user["major"],
                "department": user.get("department"),
                "bio": user["bio"],
                "availability_hours": user["hours"],
                "experience_years": user["experience"],
                "learning_goals": "Practice collaboration and share knowledge across disciplines.",
            },
        )

    catalogs = {}
    for kind, model in (("skills", Skill), ("interests", Interest)):
        names = {name for user in DATA["users"] for name in user[kind]}
        for project in DATA["projects"]:
            names.update(
                project["required"] + project["optional"]
                if kind == "skills"
                else project["interests"]
            )
        for name in sorted(names):
            insert_missing(session, model, {"id": demo_id(kind, name), "name": name})
        catalogs[kind] = dict(
            session.execute(select(model.name, model.id).where(model.name.in_(names))).all()
        )

    for user in DATA["users"]:
        for kind, model, column in (
            ("skills", UserSkill, "skill_id"),
            ("interests", UserInterest, "interest_id"),
        ):
            for name in user[kind]:
                insert_missing(
                    session,
                    model,
                    {"user_id": identities[user["slug"]], column: catalogs[kind][name]},
                )

    for project in DATA["projects"]:
        project_id = demo_id("project", project["slug"])
        owner_id = identities[project["owner"]]
        existing = session.get(Project, project_id)
        if existing is not None and existing.owner_id != owner_id:
            raise SeedError("A demo project ID belongs to another owner; refusing to change it")
        insert_missing(
            session,
            Project,
            {
                "id": project_id,
                "owner_id": owner_id,
                "title": project["title"],
                "description": project["description"],
                "project_type": project["type"],
                "status": project["status"],
                "weekly_hours": project["hours"],
                "minimum_experience_years": project["experience"],
                "max_members": project["max_members"],
            },
        )
        for required, names in ((True, project["required"]), (False, project["optional"])):
            for name in names:
                insert_missing(
                    session,
                    ProjectSkill,
                    {
                        "project_id": project_id,
                        "skill_id": catalogs["skills"][name],
                        "required": required,
                    },
                )
        for name in project["interests"]:
            insert_missing(
                session,
                ProjectInterest,
                {"project_id": project_id, "interest_id": catalogs["interests"][name]},
            )
    return {
        "demo_users": len(identities),
        "demo_projects": len(DATA["projects"]),
        "skills": len(catalogs["skills"]),
        "interests": len(catalogs["interests"]),
    }


def validate_target(settings: DemoSettings, expected_project_ref: str | None) -> bool:
    url = settings.connection_url()
    hosted = is_supabase_host(url.host)
    local = url.host in {None, "localhost", "127.0.0.1", "::1"} or (url.host or "").startswith("/")
    if not hosted and not local:
        raise SeedError(
            "Demo seeding supports local PostgreSQL or an explicitly selected Supabase project"
        )
    if hosted:
        if settings.supabase_url is None or not expected_project_ref:
            raise SeedError("Hosted seeding requires SUPABASE_URL and --expected-project-ref")
        auth_host = settings.supabase_url.host
        if auth_host != f"{expected_project_ref}.supabase.co":
            raise SeedError("Expected project ref does not match SUPABASE_URL")
        if not (
            url.host == f"db.{expected_project_ref}.supabase.co"
            or (url.username or "").endswith(f".{expected_project_ref}")
        ):
            raise SeedError("Database connection and Auth project do not match")
    return hosted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-project-ref", help="Required for hosted development seeding")
    args = parser.parse_args()
    env_file = os.environ.get("PROJECT_HUB_ENV_FILE", ".env")
    if env_file not in {".env", ".env.supabase"}:
        parser.error("PROJECT_HUB_ENV_FILE must be .env or .env.supabase")
    settings = DemoSettings(_env_file=BACKEND_DIR / env_file)
    engine = create_database_engine(settings)
    try:
        hosted = validate_target(settings, args.expected_project_ref)
        with Session(engine) as session, session.begin():
            # Include Auth provisioning in the lock so simultaneous runs cannot create
            # duplicate accounts or race while updating the local credential handoff.
            session.execute(text("SELECT pg_advisory_xact_lock(742091326)"))
            revision = session.scalar(text("SELECT version_num FROM alembic_version"))
            if revision != "cc1194778d46":
                raise SeedError("Run alembic upgrade head before seeding")
            if hosted and not session.scalar(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_constraint "
                    "WHERE conname='fk_users_id_auth_users')"
                )
            ):
                raise SeedError("Hosted Auth identity constraint is missing")
            if hosted:
                key = settings.supabase_secret_key or settings.supabase_service_role_key
                if key is None:
                    raise SeedError("Set SUPABASE_SECRET_KEY in the ignored .env.supabase file")
                admin = AuthAdmin(str(settings.supabase_url), key.get_secret_value())
                identities = admin.provision(str(settings.supabase_url))
            else:
                identities = {user["slug"]: demo_id("user", user["slug"]) for user in DATA["users"]}
            summary = seed_data(session, identities)
        print(json.dumps(summary))
        if hosted:
            print(f"Private demo sign-in credentials: {ACCOUNTS_FILE}")
        else:
            print(
                "Local demo UUIDs are database fixtures only; "
                "Supabase sign-in requires hosted seeding."
            )
    except SeedError as exc:
        parser.exit(1, f"Seed stopped: {exc}\n")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
