import httpx
from fastapi import APIRouter
from app.config import settings

router = APIRouter()

_DOWNSTREAM: dict[str, str] = {
    "auth-service": settings.auth_service_url,
    "task-service": settings.task_service_url,
    "quota-service": settings.quota_service_url,
    "broker-worker": settings.broker_worker_url,
    "agent-worker": settings.agent_worker_url,
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
        "version": "1.0.0",
        "dependencies": dependencies,
    }