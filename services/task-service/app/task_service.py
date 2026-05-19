from app.enums import SeoTone, TaskStatus
from app.task_repositories import TaskRepository
from app.tasks import AnalysisResult, Task
import json
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

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

    async def create_task(
        self, user_id: str, payload: dict, seo_tone: SeoTone | None = None
    ) -> Task:
        task = await self.repo.create(
            user_id=user_id, payload=payload, seo_tone=seo_tone
        )
        queue_payload = payload
        if seo_tone is not None:
            user_product = {**payload.get("user_product", {}), "seo_tone": seo_tone.value}
            queue_payload = {**payload, "user_product": user_product}
        await self.redis.lpush(
            "task_queue",
            json.dumps({"task_id": str(task.id), "payload": queue_payload}),
        )
        return task

    async def get_task(self, task_id: UUID) -> Task | None:
        return await self.repo.get_by_id(task_id)

    async def list_tasks(
        self, user_id: str, limit: int = 10, offset: int = 0
    ) -> tuple[list[Task], int]:
        tasks = await self.repo.get_by_user(user_id=user_id, limit=limit, offset=offset)
        total = await self.repo.count_by_user(user_id)
        return tasks, total

    async def update_status(
        self, task_id: UUID, new_status: TaskStatus, error_message: str | None = None
    ) -> Task | None:
        task = await self.repo.get_by_id(task_id)
        if not task:
            return None
        allowed = VALID_TRANSITIONS.get(task.status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Transition '{task.status}' -> '{new_status}' is not allowed. Allowed: {allowed}"
            )
        result = await self.repo.update_status(
            task_id, new_status, error_message=error_message
        )
        if new_status == TaskStatus.completed:
            event = {
                "step": "task",
                "status": "completed",
                "pct": 100,
                "message": "",
            }
            await self.redis.hset(f"task_progress:{task_id}", mapping=event)
            await self.redis.publish(f"progress:{task_id}", json.dumps(event))
        elif new_status in (TaskStatus.failed, TaskStatus.cancelled):
            current = await self.redis.hgetall(f"task_progress:{task_id}")
            event = {
                "step": current.get("step", ""),
                "status": new_status.value,
                "pct": current.get("pct", "0"),
                "message": error_message or "",
            }
            await self.redis.hset(f"task_progress:{task_id}", mapping=event)
            await self.redis.publish(f"progress:{task_id}", json.dumps(event))
        return result

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

    async def delete_task(self, task_id: UUID) -> bool:
        return await self.repo.delete_by_id(task_id)

    async def delete_all_tasks(self, user_id: str) -> None:
        await self.repo.delete_all_by_user(user_id)
