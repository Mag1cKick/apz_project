from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from app.models.mission import Mission


class MissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, mission: Mission) -> Mission:
        self._session.add(mission)
        await self._session.commit()
        await self._session.refresh(mission)
        return mission

    async def get_all(self) -> List[Mission]:
        result = await self._session.execute(
            select(Mission).order_by(Mission.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, mission_id: UUID) -> Optional[Mission]:
        result = await self._session.execute(
            select(Mission).where(Mission.id == mission_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        mission_id: str,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> None:
        values: dict = {"status": status}
        if started_at:
            values["started_at"] = started_at
        if completed_at:
            values["completed_at"] = completed_at
        await self._session.execute(
            update(Mission)
            .where(Mission.id == UUID(mission_id))
            .values(**values)
        )
        await self._session.commit()
