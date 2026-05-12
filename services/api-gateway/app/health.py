import os
import httpx
from fastapi import APIRouter

router = APIRouter()

_DOWNSTREAM: dict[str, str] = {
    "auth-service": os.getenv("AUTH_SERVICE_URL", "http://auth-service:8080"),
    "task-service": os.getenv("TASK_SERVICE_URL", "http://task-service:8080"),
    "quota-service": os.getenv("QUOTA_SERVICE_URL", "http://quota-service:8080"),
    "broker-worker": os.getenv("BROKER_WORKER_URL", "http://broker-worker:8080"),
    "agent-worker": os.getenv("AGENT_WORKER_URL", "http://agent-worker:8080"),
}


@router.get("/health")
async def health() -> dict:
    dependencies: dict[str, str] = {}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, base_url in _DOWNSTREAM.items():
            try:
                resp = await client.get(f"{base_url}/health")
                dependencies[name] = "reachable" if resp.status_code == 200 else "unreachable"
            except Exception:
                dependencies[name] = "unreachable"

    return {
        "status": "ok",
        "service": "api-gateway",
        "version": "0.1.0",
        "dependencies": dependencies,
    }
