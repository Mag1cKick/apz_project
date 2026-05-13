from fastapi import APIRouter, Depends, Request
from typing import List

from app.models.schemas import RobotCreate, RobotUpdate, RobotResponse
from app.service.robot_service import RobotService
from app.repository.robot_repository import RobotRepository
from app.database import get_db
from app.api.deps import get_current_user_id
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()


def _service(db: AsyncIOMotorDatabase = Depends(get_db)) -> RobotService:
    return RobotService(RobotRepository(db))


@router.get("/", response_model=List[dict])
async def list_robots(
    svc: RobotService = Depends(_service),
    _uid: str = Depends(get_current_user_id),
):
    return await svc.get_all()


@router.post("/", response_model=dict, status_code=201)
async def create_robot(
    body: RobotCreate,
    svc: RobotService = Depends(_service),
    uid: str = Depends(get_current_user_id),
):
    return await svc.create(body, uid)


@router.get("/{robot_id}", response_model=dict)
async def get_robot(
    robot_id: str,
    svc: RobotService = Depends(_service),
    _uid: str = Depends(get_current_user_id),
):
    return await svc.get(robot_id)


@router.patch("/{robot_id}", response_model=dict)
async def update_robot(
    robot_id: str,
    body: RobotUpdate,
    svc: RobotService = Depends(_service),
    _uid: str = Depends(get_current_user_id),
):
    return await svc.update(robot_id, body)


@router.delete("/{robot_id}", status_code=204)
async def delete_robot(
    robot_id: str,
    svc: RobotService = Depends(_service),
    _uid: str = Depends(get_current_user_id),
):
    await svc.delete(robot_id)
