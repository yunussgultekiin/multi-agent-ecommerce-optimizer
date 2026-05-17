import asyncio
from app import limiter
from app.clients.quota_client import QuotaClient, QuotaServiceError
from app.clients.task_client import TaskClient, TaskServiceError
from app.config import settings
from collections.abc import AsyncGenerator
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
import httpx
import logging
from pydantic import BaseModel
from shared.oidc_client import InternalTokenProvider
from typing import Any

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["analyze"])
_task_client = TaskClient()
_quota_client = QuotaClient()
_stream_auth = InternalTokenProvider(
    secret=settings.jwt_secret_key, algorithm=settings.jwt_algorithm
)

class AnalyzeRequest(BaseModel):
    payload: dict[str, Any]
    seo_tone: str | None = None

@router.post("", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(settings.rate_limit)
async def create_analysis(request: Request, body: AnalyzeRequest):
    user_id = request.state.user_id

    try:
        quota_response = await _quota_client.consume(user_id)
    except QuotaServiceError as exc:
        logger.error(
            "quota_consume_failed", extra={"user_id": user_id, "error": str(exc)}
        )
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
        task_response = await _task_client.create_task(
            user_id, body.payload, seo_tone=body.seo_tone
        )
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

@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.rate_limit)
async def delete_history(request: Request):
    user_id = request.state.user_id
    try:
        response = await _task_client.delete_all_tasks(user_id)
    except TaskServiceError:
        raise HTTPException(status_code=503, detail="Task service unavailable")

    if response.status_code not in {200, 204}:
        raise HTTPException(status_code=502, detail="Task service error")

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
        logger.error(
            "internal_token_failed",
            extra={"task_id": task_id, "user_id": user_id, "error": str(exc)},
        )
        raise HTTPException(status_code=503, detail="Internal token unavailable")

    async def event_generator() -> AsyncGenerator[str, None]:
        disconnected = asyncio.Event()

        async def _watch_disconnect() -> None:
            while not disconnected.is_set():
                await asyncio.sleep(5.0)
                if await request.is_disconnected():
                    disconnected.set()
                    return

        watcher = asyncio.create_task(_watch_disconnect())
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "GET", task_service_url, headers=headers
                ) as response:
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
                        if disconnected.is_set():
                            break
                        yield chunk
        except httpx.HTTPError:
            yield "event: error\ndata: Task service unavailable\n\n"
        finally:
            disconnected.set()
            watcher.cancel()
            try:
                await watcher
            except asyncio.CancelledError:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
