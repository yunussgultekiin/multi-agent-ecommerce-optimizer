import logging
from app.repositories import QuotaRepository
from app.schemas import QuotaResponse, ConsumeResponse
from app.config import settings

logger = logging.getLogger(__name__)


class QuotaExceededError(Exception):
    pass


class QuotaService:
    def __init__(self, repo: QuotaRepository) -> None:
        self._repo = repo

    async def get_quota(self, user_id: str) -> QuotaResponse:
        used = await self._repo.get(user_id)
        ttl = await self._repo.get_ttl(user_id)

        return QuotaResponse(
            user_id=user_id,
            used=used,
            limit=settings.quota_limit,
            remaining=max(0, settings.quota_limit - used),
            reset_in_seconds=ttl if ttl > 0 else None,
        )

    async def consume(self, user_id: str) -> ConsumeResponse:
        used = await self._repo.get(user_id)

        if used >= settings.quota_limit:
            logger.warning(
                "quota_exceeded",
                extra={"user_id": user_id, "used": used, "limit": settings.quota_limit},
            )
            raise QuotaExceededError(f"Quota exceeded for user {user_id}")

        new_value = await self._repo.increment(user_id)
        await self._repo.set_ttl_if_new(user_id)

        logger.info(
            "quota_consumed",
            extra={"user_id": user_id, "used": new_value, "limit": settings.quota_limit},
        )

        return ConsumeResponse(
            user_id=user_id,
            used=new_value,
            limit=settings.quota_limit,
            remaining=max(0, settings.quota_limit - new_value),
        )

    async def reset(self, user_id: str) -> None:
        await self._repo.reset(user_id)
        logger.info("quota_reset", extra={"user_id": user_id})