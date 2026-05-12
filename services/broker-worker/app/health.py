from fastapi import APIRouter
from app.database import check_db_connectivity

router = APIRouter()

@router.get("/health")
async def health() -> dict:
    db_status = check_db_connectivity()
    return {
        "status": "ok",
        "service": "broker-worker",
        "version": "1.0.0",
        "dependencies": {
            "postgres": db_status,
        },
    }