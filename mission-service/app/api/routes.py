from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.models.schemas import MissionCreate, MissionResponse
from app.service.mission_service import MissionService
from app.repository.mission_repository import MissionRepository
from app.database import get_session
from app.api.deps import get_current_user_id

router = APIRouter()


def _service(request: Request, session: AsyncSession = Depends(get_session)) -> MissionService:
    return MissionService(MissionRepository(session), request.app.state.hz_queue)


@router.get("/", response_model=List[MissionResponse])
async def list_missions(
    svc: MissionService = Depends(_service),
    _uid: str = Depends(get_current_user_id),
):
    return await svc.get_all()


@router.post("/", response_model=MissionResponse, status_code=202)
async def create_mission(
    body: MissionCreate,
    svc: MissionService = Depends(_service),
    uid: str = Depends(get_current_user_id),
):
    return await svc.create(body, uid)


@router.get("/{mission_id}", response_model=MissionResponse)
async def get_mission(
    mission_id: str,
    svc: MissionService = Depends(_service),
    _uid: str = Depends(get_current_user_id),
):
    return await svc.get(mission_id)
