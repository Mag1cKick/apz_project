"""
common/consul_client.py
Shared Consul registration, discovery, and KV config helper.
"""
import logging
import socket
import httpx
import random
import base64

logger = logging.getLogger(__name__)

CONSUL_URL = "http://consul:8500"


def _container_ip() -> str:
    return socket.gethostbyname(socket.gethostname())


async def register(
    service_name: str,
    service_id: str,
    port: int,
    health_path: str = "/health",
) -> None:
    ip = _container_ip()
    payload = {
        "ID": service_id,
        "Name": service_name,
        "Address": ip,
        "Port": port,
        "Tags": ["robotops"],
        "Check": {
            "HTTP": f"http://{ip}:{port}{health_path}",
            "Interval": "10s",
            "Timeout": "3s",
            "DeregisterCriticalServiceAfter": "30s",
        },
    }
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{CONSUL_URL}/v1/agent/service/register",
            json=payload,
            timeout=5,
        )
        resp.raise_for_status()
    logger.info("Registered with Consul: %s (%s:%d)", service_id, ip, port)


async def deregister(service_id: str) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{CONSUL_URL}/v1/agent/service/deregister/{service_id}",
            timeout=5,
        )
        resp.raise_for_status()
    logger.info("Deregistered from Consul: %s", service_id)


async def discover(service_name: str) -> str:
    """Return base URL of a random healthy service instance from Consul."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{CONSUL_URL}/v1/health/service/{service_name}?passing=true",
            timeout=5,
        )
        instances = resp.json()
        if not instances:
            raise RuntimeError(f"No healthy instances of {service_name}")
        svc = random.choice(instances)["Service"]
        return f"http://{svc['Address']}:{svc['Port']}"


async def kv_get(key: str) -> str | None:
    """Read a value from Consul KV store. Returns None if key doesn't exist."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{CONSUL_URL}/v1/kv/{key}",
            timeout=5,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        # Consul returns value as base64-encoded string
        data = resp.json()
        return base64.b64decode(data[0]["Value"]).decode()


async def kv_put(key: str, value: str) -> None:
    """Write a value to Consul KV store."""
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{CONSUL_URL}/v1/kv/{key}",
            content=value,
            timeout=5,
        )
        resp.raise_for_status()
    logger.info("Consul KV set: %s", key)

