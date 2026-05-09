from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.models.schemas import UserRegister, UserLogin, UserResponse, TokenResponse
from app.service.auth_service import AuthService
from app.repository.user_repository import UserRepository
from app.database import get_session, get_redis

router = APIRouter()
_bearer = HTTPBearer()


def _make_service(
    session: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> AuthService:
    return AuthService(UserRepository(session), redis)


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    body: UserRegister,
    service: AuthService = Depends(_make_service),
):
    return await service.register(body.username, body.email, body.password)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLogin,
    service: AuthService = Depends(_make_service),
):
    return await service.login(body.username, body.password)


@router.post("/logout")
async def logout(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    service: AuthService = Depends(_make_service),
):
    await service.logout(creds.credentials)
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def me(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    service: AuthService = Depends(_make_service),
):
    user_id = await service.get_current_user_id(creds.credentials)
    user = await service.repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
