import json
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import TaskStatus
from app.task_repositories import TaskRepository
from app.tasks import AnalysisResult, Task

VALID_TRANSITIONS = {
    TaskStatus.pending: [TaskStatus.running, TaskStatus.cancelled],
    TaskStatus.running: [TaskStatus.completed, TaskStatus.failed, TaskStatus.cancelled],
    TaskStatus.completed: [],
    TaskStatus.cancelled: [],
    TaskStatus.failed: [],
}

class TaskService:
    def __init__(self, session: AsyncSession, redis: aioredis.Redis):
        self.repo = TaskRepository(session)
        self.redis = redis

    async def create_task(self, user_id: str, payload: dict) -> Task:
        task = await self.repo.create(user_id=user_id, payload=payload)
        await self.redis.lpush(
            "task_queue",
            json.dumps({"task_id": str(task.id), "payload": payload}),
        )
        return task

    async def get_task(self, task_id: UUID) -> Task | None:
        return await self.repo.get_by_id(task_id)

    async def list_tasks(self, user_id: str, limit: int = 10, offset: int = 0) -> tuple[list[Task], int]:
        tasks = await self.repo.get_by_user(user_id=user_id, limit=limit, offset=offset)
        total = await self.repo.count_by_user(user_id)
        return tasks, total

    async def update_status(self, task_id: UUID, new_status: TaskStatus, error_message: str | None = None) -> Task | None:
        task = await self.repo.get_by_id(task_id)
        if not task:
            return None
        allowed = VALID_TRANSITIONS.get(task.status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Transition '{task.status}' -> '{new_status}' is not allowed. Allowed: {allowed}"
            )
        return await self.repo.update_status(task_id, new_status, error_message=error_message)

    async def cancel_task(self, task_id: UUID) -> Task | None:
        task = await self.update_status(task_id, TaskStatus.cancelled)
        if not task:
            return None
        await self.redis.set(f"cancelled:{task_id}", "1")
        return task

    async def save_result(self, task_id: UUID, result: dict) -> AnalysisResult:
        return await self.repo.save_result(task_id, result)

    async def get_result(self, task_id: UUID) -> tuple[AnalysisResult | None, bool]:
        task = await self.repo.get_by_id(task_id)
        if not task:
            return None, False
        return task.result, True
