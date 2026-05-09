from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import redis.asyncio as aioredis
from typing import AsyncGenerator
from app.config import settings
from app.models.user import Base

engine = create_async_engine(settings.postgres_url, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

_redis_pool: aioredis.ConnectionPool | None = None


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_redis_pool() -> aioredis.ConnectionPool:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.ConnectionPool.from_url(settings.redis_url)
    return _redis_pool


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    client = aioredis.Redis(connection_pool=get_redis_pool())
    try:
        yield client
    finally:
        await client.aclose()
