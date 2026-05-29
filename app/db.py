import ssl as ssl_lib
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


def _build_dsn() -> str:
    s = get_settings().postgres
    return f"postgresql+asyncpg://{s.username}:{s.password}@{s.host}:{s.port}/{s.name}"


def _build_ssl_arg() -> ssl_lib.SSLContext | bool:
    """Return the value to pass as asyncpg's `ssl` kwarg.

    asyncpg's default ssl mode is `prefer` — meaning the client sends an
    SSLRequest and upgrades to TLS if the server accepts. That defeats
    Keploy's wire-protocol capture even when we *think* we've disabled
    TLS. Return False explicitly when require_ssl=False so the connection
    stays plaintext and Keploy's postgres_v3 parser can see queries.
    """
    s = get_settings().postgres
    if not s.require_ssl:
        return False
    if not s.ssl_ca_file:
        return True
    ctx = ssl_lib.create_default_context(cafile=s.ssl_ca_file)
    if not s.ssl_verify_hostname:
        ctx.check_hostname = False
        ctx.verify_mode = ssl_lib.CERT_REQUIRED
    return ctx


_settings = get_settings().postgres
_connect_args: dict[str, Any] = {"ssl": _build_ssl_arg()}

engine = create_async_engine(
    _build_dsn(),
    pool_size=_settings.pool_size,
    max_overflow=_settings.max_overflow,
    pool_timeout=_settings.pool_timeout,
    pool_recycle=_settings.pool_recycle_seconds,
    pool_pre_ping=_settings.pool_pre_ping,
    connect_args=_connect_args,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    from app import models  # noqa: F401  -- register models on metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
