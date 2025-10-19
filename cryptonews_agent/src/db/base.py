from __future__ import annotations

import contextlib
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import get_settings


class Base(DeclarativeBase):
    pass


def _build_database_url() -> str:
    settings = get_settings()
    if settings.db_backend == "postgres":
        url = settings.get_database_url()
        if url.startswith("postgresql+"):
            return url.replace("postgresql+psycopg", "postgresql+asyncpg")
        return url.replace("postgresql://", "postgresql+asyncpg://")
    if settings.get_database_url().startswith("sqlite+aiosqlite"):
        return settings.get_database_url()
    return settings.get_database_url()


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine, _session_factory
    if _engine is None:
        database_url = _build_database_url()
        _engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        get_engine()
    assert _session_factory is not None
    return _session_factory


@contextlib.asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
