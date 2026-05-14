import socket
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.database import connect, disconnect
from app.api.routes import router
from app.config import settings
from common.consul_client import register, deregister

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVICE_NAME = "robot-service"
SERVICE_ID   = f"{SERVICE_NAME}-{socket.gethostname()}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect()

    try:
        await register(SERVICE_NAME, SERVICE_ID, settings.service_port)
    except Exception as e:
        logger.warning("Consul registration failed: %s", e)

    yield

    try:
        await deregister(SERVICE_ID)
    except Exception as e:
        logger.warning("Consul deregistration failed: %s", e)

    await disconnect()


app = FastAPI(title="RobotOps — Robot Service", lifespan=lifespan)
app.include_router(router, prefix="/robots", tags=["robots"])


@app.get("/health", tags=["health"])
async def health():
    return JSONResponse({"status": "ok", "service": SERVICE_ID})