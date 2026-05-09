from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from uuid import UUID, uuid4
import redis.asyncio as aioredis
from fastapi import HTTPException, status

from app.config import settings
from app.models.user import User
from app.models.schemas import TokenResponse
from app.repository.user_repository import UserRepository

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, repo: UserRepository, redis: aioredis.Redis) -> None:
        self.repo = repo
        self.redis = redis

    # ── helpers ──────────────────────────────────────────────────────────────

    def _hash(self, password: str) -> str:
        return _pwd_ctx.hash(password)

    def _verify(self, plain: str, hashed: str) -> bool:
        return _pwd_ctx.verify(plain, hashed)

    def _make_token(self, user_id: str) -> str:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
        return jwt.encode(
            {"sub": user_id, "exp": expire},
            settings.jwt_secret,
            algorithm="HS256",
        )

    def _redis_key(self, token: str) -> str:
        return f"jwt:{token}"

    # ── public API ───────────────────────────────────────────────────────────

    async def register(self, username: str, email: str, password: str) -> User:
        if await self.repo.get_by_username(username):
            raise HTTPException(status_code=400, detail="Username already taken")
        user = User(username=username, email=email, password_hash=self._hash(password))
        return await self.repo.create(user)

    async def login(self, username: str, password: str) -> TokenResponse:
        user = await self.repo.get_by_username(username)
        if not user or not self._verify(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = self._make_token(str(user.id))
        await self.redis.setex(
            self._redis_key(token),
            settings.jwt_expire_minutes * 60,
            str(user.id),
        )
        return TokenResponse(access_token=token)

    async def logout(self, token: str) -> None:
        await self.redis.delete(self._redis_key(token))

    async def get_current_user_id(self, token: str) -> UUID:
        user_id_bytes = await self.redis.get(self._redis_key(token))
        if not user_id_bytes:
            raise HTTPException(status_code=401, detail="Token invalid or expired")
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
            return UUID(payload["sub"])
        except (JWTError, KeyError, ValueError):
            raise HTTPException(status_code=401, detail="Token invalid")
