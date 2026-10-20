from uuid import uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core import database
from app.models import User


@pytest.mark.integration
def test_session_dependency_rolls_back_uncommitted_work(
    migrated_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    factory = sessionmaker(bind=migrated_engine, expire_on_commit=False)
    monkeypatch.setattr(database, "get_session_factory", lambda: factory)
    user_id = uuid4()
    dependency = database.get_session()
    session = next(dependency)
    session.add(User(id=user_id))
    session.flush()
    dependency.close()
    with Session(migrated_engine) as verification:
        assert verification.get(User, user_id) is None
