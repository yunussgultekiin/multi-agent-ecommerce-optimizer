import json
from typing import Optional
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_redis
from app.task_schemas import (
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskResultCreate,
    TaskResultResponse,
    TaskStatusUpdate,
)
from app.task_service import TaskService

router = APIRouter()

def get_service(
    session: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> TaskService:
    return TaskService(session=session, redis=redis)

@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(body: TaskCreate, service: TaskService = Depends(get_service)):
    task = await service.create_task(user_id=body.user_id, payload=body.payload)
    return task

@router.get("", response_model=TaskListResponse)
async def list_tasks(
    user_id: str = Query(...),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    service: TaskService = Depends(get_service),
):
    tasks, total = await service.list_tasks(user_id=user_id, limit=limit, offset=offset)
    return TaskListResponse(items=tasks, total=total, limit=limit, offset=offset)

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    user_id: Optional[str] = Query(default=None),
    service: TaskService = Depends(get_service),
):
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if user_id is not None and task.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return task

@router.post("/{task_id}/result", status_code=201)
async def save_result(task_id: UUID, body: TaskResultCreate, service: TaskService = Depends(get_service)):
    result = await service.save_result(task_id, body.result)
    return {"task_id": str(task_id), "created_at": str(result.created_at)}

@router.get("/{task_id}/result", response_model=TaskResultResponse)
async def get_result(
    task_id: UUID,
    user_id: Optional[str] = Query(default=None),
    service: TaskService = Depends(get_service),
):
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if user_id is not None and task.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if task.result is None:
        raise HTTPException(status_code=404, detail="Result not ready")
    return task.result

@router.patch("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(task_id: UUID, body: TaskStatusUpdate, service: TaskService = Depends(get_service)):
    try:
        task = await service.update_status(task_id, body.status, error_message=body.error_message)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.delete("/{task_id}", status_code=204)
async def cancel_task(task_id: UUID, service: TaskService = Depends(get_service)):
    task = await service.cancel_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

@router.get("/{task_id}/status/stream")
async def stream_status(task_id: UUID, redis: aioredis.Redis = Depends(get_redis)):
    async def event_generator():
        current = await redis.hgetall(f"task_progress:{task_id}")
        if current:
            yield f"data: {json.dumps(current)}\n\n"
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"progress:{task_id}")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield f"data: {message['data']}\n\n"
                    data = json.loads(message["data"])
                    if data.get("status") in ("completed", "failed", "cancelled"):
                        break
        finally:
            await pubsub.unsubscribe(f"progress:{task_id}")
            await pubsub.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
