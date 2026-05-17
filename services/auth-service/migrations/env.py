from alembic import context
from app.database import Base
import asyncio
from logging.config import fileConfig
from app.config import settings
from google.cloud.sql.connector import Connector, IPTypes
from sqlalchemy.ext.asyncio import create_async_engine

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


async def run_migrations_online() -> None:
    if settings.cloud_sql_instance:
        async with Connector() as connector:
            ip_type = (
                IPTypes.PRIVATE if settings.db_ip_type == "PRIVATE" else IPTypes.PUBLIC
            )

            async def _getconn():
                return await connector.connect_async(
                    settings.cloud_sql_instance,
                    "asyncpg",
                    user=settings.db_user,
                    password=settings.db_pass,
                    db=settings.db_name,
                    ip_type=ip_type,
                )

            engine = create_async_engine(
                "postgresql+asyncpg://",
                async_creator=_getconn,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
            )
            async with engine.connect() as connection:
                await connection.run_sync(_run_sync_migrations)
            await engine.dispose()
    else:
        engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            echo=False,
        )
        async with engine.connect() as connection:
            await connection.run_sync(_run_sync_migrations)
        await engine.dispose()


def _run_sync_migrations(connection) -> None:
    version_table = config.get_main_option("version_table", "alembic_version")
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
    asyncio.run(run_migrations_online())
