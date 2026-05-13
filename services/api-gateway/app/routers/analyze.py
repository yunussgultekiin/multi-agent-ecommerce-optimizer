import logging
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
from app.clients.quota_client import QuotaClient, QuotaServiceError
from app.clients.task_client import TaskClient, TaskServiceError
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["analyze"])
_task_client = TaskClient()
_quota_client = QuotaClient()

class AnalyzeRequest(BaseModel):
    payload: dict

@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_analysis(
    request: AnalyzeRequest,
    http_request: Request,
):
    user_id = http_request.state.user_id

    try:
        response = await _task_client.create_task(user_id, request.payload)
        if response.status_code != 201:
            raise HTTPException(status_code=502, detail="Task service error")
        task_data = response.json()
    except TaskServiceError:
        raise HTTPException(status_code=503, detail="Task service unavailable")

    try:
        await _quota_client.consume(user_id)
    except QuotaServiceError:
        logger.error(
            "quota_consume_failed",
            extra={"user_id": user_id, "task_id": task_data.get("task_id")},
        )

    return task_data

@router.get("/{task_id}")
async def get_analysis(task_id: str):
    try:
        response = await _task_client.get_task(task_id)
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Task not found")
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Task service error")
        return response.json()
    except TaskServiceError:
        raise HTTPException(status_code=503, detail="Task service unavailable")


@router.get("/{task_id}/result")
async def get_result(task_id: str):
    try:
        response = await _task_client.get_result(task_id)
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Result not found")
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Task service error")
        return response.json()
    except TaskServiceError:
        raise HTTPException(status_code=503, detail="Task service unavailable")


@router.get("/{task_id}/status/stream")
async def stream_status(task_id: str, http_request: Request):
    task_service_url = f"{settings.task_service_url}/tasks/{task_id}/status/stream"

    async def event_generator():
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "GET",
                task_service_url,
                headers={"Accept": "text/event-stream"},
                timeout=None,
            ) as response:
                async for chunk in response.aiter_text():
                    if await http_request.is_disconnected():
                        break
                    yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

@router.get("")
async def get_history(http_request: Request):
    user_id = http_request.state.user_id
    try:
        response = await _task_client.get_history(user_id)
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Task service error")
        return response.json()
    except TaskServiceError:
        raise HTTPException(status_code=503, detail="Task service unavailable")