from uuid import UUID

import procrastinate
from psycopg import AsyncConnection
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from kimmy.config import Settings

CHAT_TASK = "kimmy.chat.execute"
CHAT_QUEUE = "chat"


def create_queue(settings: Settings) -> procrastinate.App:
    url = make_url(settings.database_url.get_secret_value()).set(
        drivername="postgresql"
    )
    return procrastinate.App(
        connector=procrastinate.PsycopgConnector(
            conninfo=url.render_as_string(hide_password=False),
            min_size=1,
            max_size=5,
            kwargs={
                "options": "-c timezone=UTC -c statement_timeout=5000",
                "connect_timeout": 5,
            },
        )
    )


async def enqueue_run(
    queue: procrastinate.App,
    session: AsyncSession,
    run_id: UUID,
    thread_id: UUID,
    user_id: str,
) -> int:
    # Borrow the actual psycopg connection. The SQLAlchemy transaction remains
    # the sole owner of commit/rollback, including Procrastinate's job INSERT.
    connection = await session.connection()
    raw = await connection.get_raw_connection()
    driver = raw.driver_connection
    if not isinstance(driver, AsyncConnection):
        raise TypeError("Chat delivery requires async psycopg")
    return await queue.configure_task(
        CHAT_TASK, queue=CHAT_QUEUE, connection=driver
    ).defer_async(run_id=str(run_id), thread_id=str(thread_id), user_id=user_id)
