from fastapi import HTTPException
from app.repository.robot_repository import RobotRepository
from app.models.schemas import RobotCreate, RobotUpdate


class RobotService:
    def __init__(self, repo: RobotRepository) -> None:
        self.repo = repo

    async def create(self, data: RobotCreate, owner_id: str) -> dict:
        return await self.repo.create(data, owner_id)

    async def get_all(self) -> list:
        return await self.repo.get_all()

    async def get(self, robot_id: str) -> dict:
        robot = await self.repo.get_by_id(robot_id)
        if not robot:
            raise HTTPException(status_code=404, detail="Robot not found")
        return robot

    async def update(self, robot_id: str, data: RobotUpdate) -> dict:
        robot = await self.repo.update(robot_id, data)
        if not robot:
            raise HTTPException(status_code=404, detail="Robot not found")
        return robot

    async def delete(self, robot_id: str) -> None:
        if not await self.repo.delete(robot_id):
            raise HTTPException(status_code=404, detail="Robot not found")
