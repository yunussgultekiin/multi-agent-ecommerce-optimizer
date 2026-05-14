import logging
from collections.abc import AsyncGenerator
from typing import Any
import httpx
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from shared.oidc_client import InternalTokenProvider
from app.clients.quota_client import QuotaClient, QuotaServiceError
from app.clients.task_client import TaskClient, TaskServiceError
from app.config import settings
from app import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["analyze"])
_task_client = TaskClient()
_quota_client = QuotaClient()
_stream_auth = InternalTokenProvider(secret=settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

class AnalyzeRequest(BaseModel):
    payload: dict[str, Any]

@router.post("", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(settings.rate_limit)
async def create_analysis(request: Request, body: AnalyzeRequest):
    user_id = request.state.user_id

    try:
        quota_response = await _quota_client.consume(user_id)
    except QuotaServiceError as exc:
        logger.error("quota_consume_failed", extra={"user_id": user_id, "error": str(exc)})
        raise HTTPException(status_code=503, detail="Quota service unavailable")

    if quota_response.status_code == 429:
        raise HTTPException(status_code=429, detail="Quota exceeded")
    if quota_response.status_code not in {200, 201, 204}:
        logger.error(
            "quota_consume_unexpected_status",
            extra={"user_id": user_id, "status_code": quota_response.status_code},
        )
        raise HTTPException(status_code=503, detail="Quota service error")

    try:
        task_response = await _task_client.create_task(user_id, body.payload)
    except TaskServiceError:
        raise HTTPException(status_code=503, detail="Task service unavailable")

    if task_response.status_code != 201:
        raise HTTPException(status_code=502, detail="Task service error")

    return task_response.json()

@router.get("")
@limiter.limit(settings.rate_limit)
async def get_history(request: Request):
    user_id = request.state.user_id
    try:
        response = await _task_client.get_history(user_id)
    except TaskServiceError:
        raise HTTPException(status_code=503, detail="Task service unavailable")

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Task service error")
    return response.json()

@router.get("/{task_id}")
@limiter.limit(settings.rate_limit)
async def get_analysis(request: Request, task_id: str):
    user_id = request.state.user_id
    try:
        response = await _task_client.get_task(task_id, user_id)
    except TaskServiceError:
        raise HTTPException(status_code=503, detail="Task service unavailable")

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Task not found")
    if response.status_code == 403:
        raise HTTPException(status_code=403, detail="Forbidden")
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Task service error")
    return response.json()

@router.get("/{task_id}/result")
@limiter.limit(settings.rate_limit)
async def get_result(request: Request, task_id: str):
    user_id = request.state.user_id
    try:
        response = await _task_client.get_result(task_id, user_id)
    except TaskServiceError:
        raise HTTPException(status_code=503, detail="Task service unavailable")

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Result not found")
    if response.status_code == 403:
        raise HTTPException(status_code=403, detail="Forbidden")
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Task service error")
    return response.json()

@router.get("/{task_id}/status/stream")
@limiter.limit(settings.rate_limit)
async def stream_status(request: Request, task_id: str):
    user_id = request.state.user_id
    try:
        task_response = await _task_client.get_task(task_id, user_id)
    except TaskServiceError:
        raise HTTPException(status_code=503, detail="Task service unavailable")

    if task_response.status_code == 404:
        raise HTTPException(status_code=404, detail="Task not found")
    if task_response.status_code == 403:
        raise HTTPException(status_code=403, detail="Forbidden")
    if task_response.status_code != 200:
        raise HTTPException(status_code=502, detail="Task service error")

    task_service_url = f"{settings.task_service_url}/tasks/{task_id}/status/stream"

    try:
        headers = await _stream_auth.attach_header({"Accept": "text/event-stream"})
    except Exception as exc:
        logger.error("internal_token_failed", extra={"task_id": task_id, "user_id": user_id, "error": str(exc)})
        raise HTTPException(status_code=503, detail="Internal token unavailable")

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", task_service_url, headers=headers) as response:
                    if response.status_code == 404:
                        yield "event: error\ndata: Task not found\n\n"
                        return
                    if response.status_code == 403:
                        yield "event: error\ndata: Forbidden\n\n"
                        return
                    if response.status_code != 200:
                        yield "event: error\ndata: Task service error\n\n"
                        return

                    async for chunk in response.aiter_text():
                        if await request.is_disconnected():
                            break
                        yield chunk
        except httpx.HTTPError:
            yield "event: error\ndata: Task service unavailable\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
