import asyncio
import json
import uuid
from fastapi import HTTPException

from app.models.mission import Mission
from app.models.schemas import MissionCreate
from app.repository.mission_repository import MissionRepository


class MissionService:
    def __init__(self, repo: MissionRepository, hz_queue) -> None:
        self.repo = repo
        self._queue = hz_queue

    async def create(self, data: MissionCreate, user_id: str) -> Mission:
        mission = Mission(
            id=uuid.uuid4(),
            title=data.title,
            description=data.description,
            robot_id=data.robot_id,
            status="queued",
            priority=data.priority,
            created_by=user_id,
        )
        saved = await self.repo.create(mission)

        # Producer side — put to Hazelcast Queue (blocking call, run in thread)
        payload = json.dumps(
            {"mission_id": str(saved.id), "robot_id": data.robot_id, "priority": data.priority}
        )
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._queue.put, payload)

        return saved

    async def get_all(self) -> list:
        return await self.repo.get_all()

    async def get(self, mission_id: str) -> Mission:
        try:
            mid = uuid.UUID(mission_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid mission id")
        mission = await self.repo.get_by_id(mid)
        if not mission:
            raise HTTPException(status_code=404, detail="Mission not found")
        return mission
