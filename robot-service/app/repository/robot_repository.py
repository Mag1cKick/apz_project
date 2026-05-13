from datetime import datetime
from typing import Optional, List
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.schemas import RobotCreate, RobotUpdate


class RobotRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db.robots

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _to_dict(doc: dict) -> dict:
        doc["id"] = doc.pop("_id")
        return doc

    # ── CRUD ─────────────────────────────────────────────────────────────────

    async def create(self, data: RobotCreate, owner_id: str) -> dict:
        now = datetime.utcnow()
        doc = {
            "_id": str(uuid.uuid4()),
            "name": data.name,
            "type": data.type,
            "model": data.model,
            "status": "offline",
            "capabilities": data.capabilities,
            "location": data.location.model_dump() if data.location else {"x": 0.0, "y": 0.0, "z": 0.0},
            "assigned_mission_id": None,
            "owner_id": owner_id,
            "created_at": now,
            "updated_at": now,
        }
        await self._col.insert_one(doc)
        return self._to_dict(doc)

    async def get_all(self) -> List[dict]:
        return [self._to_dict(d) async for d in self._col.find({})]

    async def get_by_id(self, robot_id: str) -> Optional[dict]:
        doc = await self._col.find_one({"_id": robot_id})
        return self._to_dict(doc) if doc else None

    async def update(self, robot_id: str, data: RobotUpdate) -> Optional[dict]:
        fields = {k: v for k, v in data.model_dump(exclude_none=True).items()}
        if not fields:
            return await self.get_by_id(robot_id)
        fields["updated_at"] = datetime.utcnow()
        doc = await self._col.find_one_and_update(
            {"_id": robot_id},
            {"$set": fields},
            return_document=True,
        )
        return self._to_dict(doc) if doc else None

    async def delete(self, robot_id: str) -> bool:
        result = await self._col.delete_one({"_id": robot_id})
        return result.deleted_count > 0
