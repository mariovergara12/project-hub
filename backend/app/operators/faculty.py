"""Review or apply a faculty status change with an audit record in the same transaction."""

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings, is_supabase_host
from app.core.database import create_database_engine
from app.models import FacultyRoleChange, User
from app.models.enums import UserRole

Status = Literal["verified", "unverified", "student"]


class OperatorError(Exception):
    pass


@dataclass(frozen=True)
class ChangeResult:
    user_id: UUID
    previous_role: UserRole
    new_role: UserRole
    previous_verified_at: datetime | None
    new_verified_at: datetime | None
    changed: bool
    applied: bool
    audit_id: UUID | None


def validate_target(
    settings: Settings, *, expected_database: str, expected_project_ref: str | None
) -> None:
    url = settings.connection_url()
    if set(url.query) & {"host", "hostaddr", "dbname", "user", "service", "servicefile"}:
        raise OperatorError("Connection target overrides are not supported in DATABASE_URL")
    if url.database != expected_database:
        raise OperatorError("Expected database does not match DATABASE_URL")
    if is_supabase_host(url.host):
        if not expected_project_ref or settings.supabase_url is None:
            raise OperatorError("Hosted changes require --expected-project-ref and SUPABASE_URL")
        direct = url.host == f"db.{expected_project_ref}.supabase.co"
        pooler = url.host.endswith(".pooler.supabase.com") and (url.username or "").endswith(
            f".{expected_project_ref}"
        )
        if settings.supabase_url.host != f"{expected_project_ref}.supabase.co" or not (
            direct or pooler
        ):
            raise OperatorError("Expected project does not match the database and Auth settings")
    elif url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise OperatorError(
            "Only local PostgreSQL or an explicitly selected Supabase project is supported"
        )
    elif expected_project_ref:
        raise OperatorError("Do not supply --expected-project-ref for a local database")


def change_faculty_status(
    session: Session,
    user_id: UUID,
    *,
    status: Status,
    operator: str,
    reason: str,
    apply: bool = False,
) -> ChangeResult:
    operator, reason = operator.strip(), reason.strip()
    if not 1 <= len(operator) <= 200 or not 1 <= len(reason) <= 2000:
        raise OperatorError("Supply an operator (1–200 characters) and reason (1–2000 characters)")
    if status not in {"verified", "unverified", "student"}:
        raise OperatorError("Unsupported faculty status")
    with session.begin():
        user = session.scalar(select(User).where(User.id == user_id).with_for_update())
        if user is None:
            raise OperatorError(
                "Account not found; the user must first sign in and open their profile"
            )
        if user.role == UserRole.ADMINISTRATOR:
            raise OperatorError("This command cannot change administrator accounts")
        now = session.scalar(select(func.clock_timestamp()))
        new_role = UserRole.STUDENT if status == "student" else UserRole.FACULTY
        verified_at = (
            ((user.faculty_verified_at if user.role == UserRole.FACULTY else None) or now)
            if status == "verified"
            else None
        )
        changed = user.role != new_role or user.faculty_verified_at != verified_at
        previous_role, previous_verified_at = user.role, user.faculty_verified_at
        audit_id = None
        if apply and changed:
            principal = session.scalar(text("SELECT session_user"))
            record = FacultyRoleChange(
                user_id=user_id,
                operator=operator,
                database_principal=principal,
                reason=reason,
                previous_role=previous_role,
                new_role=new_role,
                previous_verified_at=previous_verified_at,
                new_verified_at=verified_at,
                performed_at=now,
            )
            user.role, user.faculty_verified_at = new_role, verified_at
            session.add(record)
            session.flush()
            audit_id = record.id
        return ChangeResult(
            user_id,
            previous_role,
            new_role,
            previous_verified_at,
            verified_at,
            changed,
            apply and changed,
            audit_id,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", type=UUID, required=True)
    parser.add_argument("--status", choices=("verified", "unverified", "student"), required=True)
    parser.add_argument(
        "--operator", required=True, help="Trusted operator's name or work identity"
    )
    parser.add_argument("--reason", required=True)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--expected-project-ref")
    parser.add_argument(
        "--apply", action="store_true", help="Commit the change; default is a dry run"
    )
    args = parser.parse_args()
    engine = None
    try:
        settings = get_settings()
        validate_target(
            settings,
            expected_database=args.expected_database,
            expected_project_ref=args.expected_project_ref,
        )
        engine = create_database_engine(settings)
        with Session(engine, expire_on_commit=False) as session:
            result = change_faculty_status(
                session,
                args.user_id,
                status=args.status,
                operator=args.operator,
                reason=args.reason,
                apply=args.apply,
            )
        print(json.dumps(asdict(result), default=str))
    except OperatorError as exc:
        parser.exit(1, f"No changes committed: {exc}\n")
    except (SQLAlchemyError, ValueError):
        parser.exit(
            1, "No changes committed: check database settings and apply the reviewed migrations.\n"
        )
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
