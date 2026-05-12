from fastapi import APIRouter
from app.database import check_database_connectivity

router = APIRouter()

@router.get("/health")
async def health() -> dict:
    pg_status = await check_database_connectivity()
    return {
        "status": "ok",
        "service": "task-service",
        "version": "0.1.0",
        "dependencies": {"postgres": pg_status},
    }
