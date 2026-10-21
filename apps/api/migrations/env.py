import asyncio

from alembic import context
from alembic.runtime.environment import NameFilterParentNames, NameFilterType
from sqlalchemy import Connection

from kimmy.chat.models import ChatBase
from kimmy.config import get_settings
from kimmy.database import create_engine
from kimmy.fleet.models import Base


def include_name(
    name: str | None, type_: NameFilterType, parent_names: NameFilterParentNames
) -> bool:
    # Framework tables have native keys and their own migration lifecycle.
    return not (
        type_ == "table"
        and name is not None
        and (
            name.startswith("procrastinate_")
            or name
            in {
                "checkpoints",
                "checkpoint_blobs",
                "checkpoint_writes",
                "checkpoint_migrations",
            }
        )
    )


def migrate(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=[Base.metadata, ChatBase.metadata],
        include_name=include_name,
    )
    with context.begin_transaction():
        context.run_migrations()


async def online() -> None:
    engine = create_engine(get_settings())
    try:
        async with engine.connect() as connection:
            await connection.run_sync(migrate)
    finally:
        await engine.dispose()


if context.is_offline_mode():
    context.configure(
        dialect_name="postgresql",
        target_metadata=[Base.metadata, ChatBase.metadata],
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(online())
