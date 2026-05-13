"""
Consumer side of the CQRS pattern.
Runs in a background daemon thread with its own asyncio event loop.
Reads missions from the Hazelcast Queue and updates PostgreSQL.
"""
import asyncio
import json
import logging
import threading
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.repository.mission_repository import MissionRepository

logger = logging.getLogger(__name__)

QUEUE_NAME = "mission-queue"


class MissionProcessor:
    def __init__(self) -> None:
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self, hz_queue, postgres_url: str) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(hz_queue, postgres_url),
            daemon=True,
            name="mission-processor",
        )
        self._thread.start()
        logger.info("Mission processor started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Mission processor stopped")

    # ── private ───────────────────────────────────────────────────────────────

    def _run_loop(self, hz_queue, postgres_url: str) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        engine = create_async_engine(postgres_url, echo=False)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        while self._running:
            try:
                # poll with 1-second timeout so we can check _running regularly
                item = hz_queue.poll(timeout=1)
                if item:
                    data = json.loads(item)
                    loop.run_until_complete(self._process(data, session_factory))
            except Exception as exc:
                logger.error("Processor error: %s", exc)

        loop.run_until_complete(engine.dispose())
        loop.close()

    async def _process(self, data: dict, session_factory) -> None:
        mission_id: str = data["mission_id"]
        robot_id: str | None = data.get("robot_id")
        logger.info("Processing mission %s for robot %s", mission_id, robot_id)

        async with session_factory() as session:
            repo = MissionRepository(session)
            await repo.update_status(mission_id, "active", started_at=datetime.utcnow())

        # Simulate work (e.g., commanding the robot)
        await asyncio.sleep(3)

        async with session_factory() as session:
            repo = MissionRepository(session)
            await repo.update_status(mission_id, "completed", completed_at=datetime.utcnow())

        logger.info("Mission %s completed", mission_id)
