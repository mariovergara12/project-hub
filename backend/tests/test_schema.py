from uuid import uuid4

import pytest
from sqlalchemy import Engine, delete, func, inspect, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session, configure_mappers

from app.models import (
    Application,
    Base,
    Interest,
    Membership,
    Milestone,
    Profile,
    Project,
    ProjectInterest,
    ProjectSkill,
    Skill,
    User,
    UserInterest,
    UserSkill,
)
from app.models.enums import ApplicationStatus, ProjectStatus, ProjectType, UserRole


def test_all_models_import_and_map() -> None:
    configure_mappers()
    assert len(Base.metadata.tables) == 12
    assert "auth.users" not in Base.metadata.tables


@pytest.fixture
def project(db_session: Session) -> Project:
    owner = User(id=uuid4(), role=UserRole.FACULTY)
    project = Project(
        owner=owner,
        title="Campus collaboration",
        description="Connect students across majors.",
        project_type=ProjectType.RESEARCH_OPPORTUNITY,
    )
    db_session.add(project)
    db_session.flush()
    return project


@pytest.mark.integration
def test_migrated_schema_and_rls(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        assert set(inspect(connection).get_table_names()) == set(Base.metadata.tables) | {
            "alembic_version"
        }
        secured = set(
            connection.scalars(
                text(
                    "SELECT relname FROM pg_class WHERE relnamespace = 'public'::regnamespace "
                    "AND relkind = 'r' AND relrowsecurity"
                )
            )
        )
        assert secured == set(Base.metadata.tables)


@pytest.mark.integration
def test_relationships_defaults_and_uuid_roundtrip(db_session: Session, project: Project) -> None:
    student = User(id=uuid4())
    student.profile = Profile(display_name="Student", availability_hours=10)
    skill, interest = Skill(name="python"), Interest(name="robotics")
    student.skills.append(UserSkill(skill=skill))
    student.interests.append(UserInterest(interest=interest))
    project.skills.append(ProjectSkill(skill=skill))
    project.interests.append(ProjectInterest(interest=interest))
    application = Application(project=project, applicant=student)
    membership = Membership(project=project, user=student)
    milestone = Milestone(project=project, title="First prototype")
    db_session.add_all([application, membership, milestone])
    db_session.flush()
    student_id = student.id
    db_session.expire_all()
    assert db_session.get(User, student_id).profile.user_id == student_id
    assert student.role == UserRole.STUDENT
    assert project.owner.faculty_verified_at is None
    assert project.status == ProjectStatus.DRAFT
    assert application.status == ApplicationStatus.PENDING
    assert project.skills[0].skill.name == "python"
    assert project.interests[0].interest.name == "robotics"
    assert student.created_at.tzinfo is not None


@pytest.mark.integration
@pytest.mark.parametrize("model", [Application, Membership])
def test_duplicate_project_participation_rejected(
    db_session: Session, project: Project, model: type[Application] | type[Membership]
) -> None:
    student = User(id=uuid4())
    db_session.add(student)
    db_session.flush()
    values = {"project_id": project.id}
    values["applicant_id" if model is Application else "user_id"] = student.id
    db_session.add(model(**values))
    db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(model(**values))
        db_session.flush()


@pytest.mark.integration
@pytest.mark.parametrize("hours", [-1, 169])
def test_invalid_availability_rejected(db_session: Session, hours: int) -> None:
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(
            User(id=uuid4(), profile=Profile(display_name="Student", availability_hours=hours))
        )
        db_session.flush()


@pytest.mark.integration
def test_foreign_key_and_enum_constraints(db_session: Session) -> None:
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.add(Profile(user_id=uuid4(), display_name="Missing user"))
        db_session.flush()
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.execute(
            text("INSERT INTO users (id, role) VALUES (:id, 'not_a_role')"), {"id": uuid4()}
        )


@pytest.mark.integration
def test_catalog_names_are_canonical_and_unique(db_session: Session) -> None:
    db_session.add(Skill(name="python"))
    db_session.flush()
    for name in ("python", "Python", " python ", ""):
        with pytest.raises(IntegrityError), db_session.begin_nested():
            db_session.add(Skill(name=name))
            db_session.flush()


@pytest.mark.integration
def test_deleting_owner_requires_project_cleanup(db_session: Session, project: Project) -> None:
    with pytest.raises(IntegrityError), db_session.begin_nested():
        db_session.delete(project.owner)
        db_session.flush()


@pytest.mark.integration
def test_database_cascades_project_children(db_session: Session, project: Project) -> None:
    student = User(id=uuid4())
    db_session.add_all(
        [
            Application(project=project, applicant=student),
            Membership(project=project, user=student),
            Milestone(project=project, title="Prototype"),
            ProjectSkill(project=project, skill=Skill(name="python")),
            ProjectInterest(project=project, interest=Interest(name="robotics")),
        ]
    )
    db_session.flush()
    db_session.execute(delete(Project).where(Project.id == project.id))
    for model in (Application, Membership, Milestone, ProjectSkill, ProjectInterest):
        assert db_session.scalar(select(func.count()).select_from(model)) == 0
    assert db_session.get(User, student.id) is not None


@pytest.mark.integration
def test_rls_blocks_nonowner_even_with_grants(db_session: Session, project: Project) -> None:
    # Requires CREATEROLE on the disposable test database's connection role.
    # All role/grant changes are transactional and rolled back by the fixture.
    role = "rls_test_" + uuid4().hex
    db_session.execute(text(f'CREATE ROLE "{role}" NOLOGIN NOSUPERUSER NOBYPASSRLS'))
    db_session.execute(text(f'GRANT USAGE ON SCHEMA public TO "{role}"'))
    db_session.execute(text(f'GRANT SELECT, INSERT, UPDATE, DELETE ON users TO "{role}"'))
    db_session.execute(text(f'SET LOCAL ROLE "{role}"'))
    assert db_session.execute(text("SELECT * FROM users")).all() == []
    assert db_session.execute(text("UPDATE users SET role = 'administrator'")).rowcount == 0
    assert db_session.execute(text("DELETE FROM users")).rowcount == 0
    with pytest.raises(DBAPIError, match="row-level security"), db_session.begin_nested():
        db_session.execute(text("INSERT INTO users (id) VALUES (:id)"), {"id": uuid4()})
    db_session.execute(text("RESET ROLE"))
