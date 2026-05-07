from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from src.socmint.config import load_settings
from src.socmint.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = load_settings(require_secret=False)
if settings.database_url.startswith('sqlite:///'):
    sqlite_path = settings.database_url.replace('sqlite:///', '', 1)
    if sqlite_path and sqlite_path != ':memory:':
        os.makedirs(os.path.dirname(os.path.abspath(sqlite_path)), exist_ok=True)
config.set_main_option('sqlalchemy.url', settings.database_url)
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
