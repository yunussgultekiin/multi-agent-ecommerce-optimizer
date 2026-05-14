import asyncio
from logging.config import fileConfig
from alembic import context
from app.database import Base, _build_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    from app.config import settings

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

async def run_migrations_online() -> None:
    engine = await _build_engine()
    async with engine.connect() as connection:
        await connection.run_sync(_run_sync_migrations)
    await engine.dispose()

def _run_sync_migrations(connection) -> None:
    version_table = config.get_main_option("version_table", "alembic_version")
    context.configure(connection=connection, target_metadata=target_metadata, version_table=version_table)
    with context.begin_transaction():
        context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
