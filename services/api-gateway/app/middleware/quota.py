import logging
import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.clients.quota_client import QuotaClient

logger = logging.getLogger(__name__)

_quota_client = QuotaClient()

class QuotaCheckMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/analyze"):
            return await call_next(request)

        user_id = getattr(request.state, "user_id", None)
        if user_id is None:
            return JSONResponse(
                {"detail": "Not authenticated"},
                status_code=401,
            )

        try:
            response = await _quota_client.check(user_id)

            if response.status_code == 429:
                return JSONResponse(
                    {"detail": "Quota exceeded"},
                    status_code=429,
                )

        except Exception as exc:
            logger.error(
                "quota_check_failed",
                extra={"user_id": user_id, "error": str(exc)},
            )
            return JSONResponse(
                {"detail": "Quota service unavailable"},
                status_code=503,
            )

        return await call_next(request)