from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import connect, disconnect
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect()
    yield
    await disconnect()


app = FastAPI(title="RobotOps — Robot Service", lifespan=lifespan)
app.include_router(router, prefix="/robots", tags=["robots"])
