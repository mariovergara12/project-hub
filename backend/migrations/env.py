from logging.config import fileConfig
from typing import Any

from alembic import context

from app.core.config import get_settings
from app.core.database import create_database_engine
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def include_object(
    obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
) -> bool:
    # This externally owned reference is maintained by an explicit migration.
    # Autogenerate must neither manage auth.users nor remove the hosted-only FK.
    return not (type_ == "foreign_key_constraint" and name == "fk_users_id_auth_users")


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().connection_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Read the URL directly instead of ConfigParser interpolation (passwords may contain %).
    settings = get_settings()
    engine = create_database_engine(settings)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                include_object=include_object,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
