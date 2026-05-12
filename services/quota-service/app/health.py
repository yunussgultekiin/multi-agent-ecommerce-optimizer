from fastapi import APIRouter
from app.redis import check_redis_connectivity

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    redis_status = await check_redis_connectivity()
    return {
        "status": "ok",
        "service": "quota-service",
        "version": "1.0.0",
        "dependencies": {"redis": redis_status},
    }