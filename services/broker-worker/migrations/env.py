from alembic import context
from app.config import settings
from app.database import Base
from logging.config import fileConfig
from sqlalchemy import create_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    version_table = config.get_main_option("version_table", "alembic_version")
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=version_table,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    version_table = config.get_main_option("version_table", "alembic_version")
    engine = create_engine(settings.database_url)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table=version_table,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
