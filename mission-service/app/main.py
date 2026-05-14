import socket
import logging
from contextlib import asynccontextmanager

import hazelcast
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import create_tables
from app.api.routes import router
from app.service.mission_processor import MissionProcessor
from common.consul_client import register, deregister, kv_put, kv_get

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVICE_NAME = "mission-service"
SERVICE_ID   = f"{SERVICE_NAME}-{socket.gethostname()}"

# Consul KV keys
KV_HZ_MEMBERS      = "config/hazelcast/members"
KV_HZ_CLUSTER_NAME = "config/hazelcast/cluster-name"
KV_HZ_QUEUE_NAME   = "config/hazelcast/queue-name"

processor = MissionProcessor()


async def _seed_consul_kv() -> None:
    """Write Hazelcast config to Consul KV if not already set.
    This ensures the config is always available even on first boot.
    """
    if not await kv_get(KV_HZ_MEMBERS):
        await kv_put(KV_HZ_MEMBERS, settings.hazelcast_members)
        logger.info("Seeded Consul KV: %s", KV_HZ_MEMBERS)

    if not await kv_get(KV_HZ_CLUSTER_NAME):
        await kv_put(KV_HZ_CLUSTER_NAME, settings.hazelcast_cluster_name)
        logger.info("Seeded Consul KV: %s", KV_HZ_CLUSTER_NAME)

    if not await kv_get(KV_HZ_QUEUE_NAME):
        await kv_put(KV_HZ_QUEUE_NAME, "mission-queue")
        logger.info("Seeded Consul KV: %s", KV_HZ_QUEUE_NAME)


async def _load_hz_config() -> tuple[str, list[str], str]:
    """Read Hazelcast config from Consul KV."""
    cluster_name = await kv_get(KV_HZ_CLUSTER_NAME) or settings.hazelcast_cluster_name
    members_raw  = await kv_get(KV_HZ_MEMBERS) or settings.hazelcast_members
    queue_name   = await kv_get(KV_HZ_QUEUE_NAME) or "mission-queue"
    members      = [m.strip() for m in members_raw.split(",")]
    logger.info(
        "Hazelcast config from Consul — cluster: %s, members: %s, queue: %s",
        cluster_name, members, queue_name,
    )
    return cluster_name, members, queue_name


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()

    # Seed KV defaults, then read config from Consul
    await _seed_consul_kv()
    cluster_name, members, queue_name = await _load_hz_config()

    hz_client = hazelcast.HazelcastClient(
        cluster_name=cluster_name,
        cluster_members=members,
    )
    hz_queue = hz_client.get_queue(queue_name).blocking()

    app.state.hz_client = hz_client
    app.state.hz_queue  = hz_queue

    processor.start(hz_queue, settings.postgres_url)
    logger.info("Mission service ready")

    try:
        await register(SERVICE_NAME, SERVICE_ID, settings.service_port)
    except Exception as e:
        logger.warning("Consul registration failed: %s", e)

    yield

    try:
        await deregister(SERVICE_ID)
    except Exception as e:
        logger.warning("Consul deregistration failed: %s", e)

    processor.stop()
    hz_client.shutdown()


app = FastAPI(title="RobotOps — Mission Service", lifespan=lifespan)
app.include_router(router, prefix="/missions", tags=["missions"])


@app.get("/health", tags=["health"])
async def health():
    return JSONResponse({"status": "ok", "service": SERVICE_ID})