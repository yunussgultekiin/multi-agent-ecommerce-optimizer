import logging
from fastapi import APIRouter, Depends, HTTPException, status
import redis.asyncio as aioredis
from app.redis import get_redis
from app.repositories import QuotaRepository
from app.schemas import ConsumeResponse, QuotaResponse, ResetResponse
from app.services import QuotaExceededError, QuotaService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quota", tags=["quota"])


def _get_quota_service(redis: aioredis.Redis = Depends(get_redis)) -> QuotaService:
    return QuotaService(repo=QuotaRepository(redis))


@router.get("/{user_id}", response_model=QuotaResponse)
async def get_quota(
    user_id: str,
    service: QuotaService = Depends(_get_quota_service),
) -> QuotaResponse:
    return await service.get_quota(user_id)


@router.post("/{user_id}/consume", response_model=ConsumeResponse)
async def consume(
    user_id: str,
    service: QuotaService = Depends(_get_quota_service),
) -> ConsumeResponse:
    try:
        return await service.consume(user_id)
    except QuotaExceededError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Quota exceeded",
        )


@router.post("/{user_id}/reset", response_model=ResetResponse)
async def reset(
    user_id: str,
    service: QuotaService = Depends(_get_quota_service),
) -> ResetResponse:
    await service.reset(user_id)
    return ResetResponse(user_id=user_id)