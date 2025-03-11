import contextlib
from typing import Any, AsyncIterator
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from nbsapi.config import settings

Base = declarative_base()


def inject_driver(connection_string, driver="psycopg"):
    """
    Modify raw database connection string with the appropriate driver, defaulting to psycopg3

    We need this because SQLAlchemy doesn't accept postgres:// connection strings, as these are
    deprecated. However, many providers (such as Fly) continue to use it.
    Instead, we intercept the string, parse it, substitute 'postgresql' if necessary, and inject
    the psycopg3 driver (named 'psycopg', confusingly) by default

    """
    parsed = urlparse(connection_string)
    if parsed.scheme == "postgres" and "+" not in parsed.scheme:
        scheme = "postgresql"
    elif "+" in parsed.scheme:
        scheme, driver = parsed.scheme.split("+")
        # remove the driver so the scheme can be properly parsed for possible modification, then recur
        return inject_driver(
            parsed._replace(scheme=f"{scheme}").geturl(), driver=driver
        )
    else:
        scheme = parsed.scheme
    # inject driver into connection string
    replaced = parsed._replace(scheme=f"{scheme}+{driver}").geturl()
    return replaced


class DatabaseSessionManager:
    def __init__(self, host: str, engine_kwargs: dict[str, Any] = {}):
        self._engine = create_async_engine(host, **engine_kwargs)
        self._sessionmaker = async_sessionmaker(autocommit=False, bind=self._engine)

    async def close(self):
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self._engine.dispose()

        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


sessionmanager = DatabaseSessionManager(
    inject_driver(settings.database_url), {"echo": settings.echo_sql}
)


async def get_db_session():
    async with sessionmanager.session() as session:
        yield session
