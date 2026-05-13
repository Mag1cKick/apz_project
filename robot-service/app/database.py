import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None


async def connect() -> None:
    global _client
    for attempt in range(15):
        try:
            _client = AsyncIOMotorClient(
                settings.mongo_uri,
                serverSelectionTimeoutMS=5000,
            )
            await _client.admin.command("ping")
            logger.info("Connected to MongoDB replica set")
            return
        except Exception as exc:
            logger.warning("MongoDB connect attempt %d failed: %s", attempt + 1, exc)
            if attempt < 14:
                await asyncio.sleep(5)
    raise RuntimeError("Cannot connect to MongoDB after 15 attempts")


async def disconnect() -> None:
    global _client
    if _client:
        _client.close()
        _client = None


def get_db() -> AsyncIOMotorDatabase:
    return _client[settings.mongo_db]
