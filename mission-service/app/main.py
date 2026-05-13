import logging
from contextlib import asynccontextmanager

import hazelcast
from fastapi import FastAPI

from app.config import settings
from app.database import create_tables
from app.api.routes import router
from app.service.mission_processor import MissionProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

processor = MissionProcessor()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()

    # Connect to Hazelcast cluster (same cluster used in the labs)
    hz_client = hazelcast.HazelcastClient(
        cluster_name=settings.hazelcast_cluster_name,
        cluster_members=settings.hazelcast_member_list(),
    )
    hz_queue = hz_client.get_queue("mission-queue").blocking()

    app.state.hz_client = hz_client
    app.state.hz_queue = hz_queue

    # Start background consumer thread
    processor.start(hz_queue, settings.postgres_url)
    logger.info("Mission service ready")

    yield

    processor.stop()
    hz_client.shutdown()


app = FastAPI(title="RobotOps — Mission Service", lifespan=lifespan)
app.include_router(router, prefix="/missions", tags=["missions"])
