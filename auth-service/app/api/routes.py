from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.models.schemas import UserRegister, UserLogin, UserResponse
from app.service.auth_service import AuthService
from app.repository.user_repository import UserRepository
from app.database import get_session, get_redis

router = APIRouter()

COOKIE_NAME = "robotops_token"


def _make_service(
    session: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> AuthService:
    return AuthService(UserRepository(session), redis)


def _get_token(request: Request) -> str:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    body: UserRegister,
    service: AuthService = Depends(_make_service),
):
    return await service.register(body.username, body.email, body.password)


@router.post("/login", response_model=UserResponse)
async def login(
    body: UserLogin,
    response: Response,
    service: AuthService = Depends(_make_service),
):
    token, user = await service.login(body.username, body.password)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="strict",
        max_age=60 * 60,  # 1 hour, matches JWT_EXPIRE_MINUTES
    )
    return user


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    service: AuthService = Depends(_make_service),
):
    token = _get_token(request)
    await service.logout(token)
    response.delete_cookie(COOKIE_NAME)
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def me(
    request: Request,
    service: AuthService = Depends(_make_service),
):
    token = _get_token(request)
    user_id = await service.get_current_user_id(token)
    user = await service.repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user