from fastapi import HTTPException, Request
import httpx
from common.consul_client import discover

COOKIE_NAME = "robotops_token"


async def get_current_user_id(request: Request) -> str:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        auth_url = await discover("auth-service")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{auth_url}/auth/me",
                cookies={COOKIE_NAME: token},
                timeout=5,
            )
    except (httpx.RequestError, RuntimeError):
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return resp.json()["id"]