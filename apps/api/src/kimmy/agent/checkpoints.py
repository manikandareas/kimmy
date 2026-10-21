from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.engine import make_url

from kimmy.config import Settings


@asynccontextmanager
async def checkpoints(settings: Settings) -> AsyncIterator[AsyncPostgresSaver]:
    url = make_url(settings.database_url.get_secret_value()).set(
        drivername="postgresql"
    )
    async with AsyncConnectionPool[AsyncConnection[dict[str, Any]]](
        conninfo=url.render_as_string(hide_password=False),
        min_size=1,
        max_size=5,
        open=False,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
            "connect_timeout": 5,
            "options": "-c timezone=UTC -c statement_timeout=5000",
        },
    ) as pool:
        await pool.wait(timeout=10)
        yield AsyncPostgresSaver(pool)


async def setup_checkpoints(settings: Settings) -> None:
    async with checkpoints(settings) as saver:
        assert isinstance(saver.conn, AsyncConnectionPool)
        async with saver.conn.connection() as connection:
            await connection.execute("SELECT pg_advisory_lock(704004)")
            try:
                await AsyncPostgresSaver(connection).setup()
            finally:
                await connection.execute("SELECT pg_advisory_unlock(704004)")
