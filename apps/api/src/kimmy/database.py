from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from kimmy.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        connect_args={
            "options": "-c timezone=UTC -c statement_timeout=5000",
            "connect_timeout": 5,
        },
    )
