from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import create_tables
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(title="RobotOps — Auth Service", lifespan=lifespan)
app.include_router(router, prefix="/auth", tags=["auth"])
