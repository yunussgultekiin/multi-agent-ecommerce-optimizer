from uuid import UUID
import json
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
from app.repositories.task_repositories import TaskRepository
from app.models.tasks import Task, AnalysisResult
from app.models.enums import TaskStatus

VALID_TRANSITIONS = {
    TaskStatus.pending : [TaskStatus.running, TaskStatus.cancelled],
    TaskStatus.running : [TaskStatus.completed, TaskStatus.failed, TaskStatus.cancelled],
    TaskStatus.completed : [],
    TaskStatus.cancelled : [],
    TaskStatus.failed : []
}

class TaskService():
    def __init__(self, session : AsyncSession, redis : aioredis.Redis):
        self.repo = TaskRepository(session)
        self.redis = redis
    
    async def create_task(
        self, user_id: str, input_url: str, keywords: list[str]
    ) -> Task:
        task = await self.repo.create(
            user_id=user_id,
            input_url=input_url,
            keywords = keywords
        )

        await self.redis.lpush(
            "task_queue",
            json.dumps({
                "task_id": str(task.id),
                "user_id": task.user_id,
                "input_url": task.input_url,
                "keywords": task.keywords
            })
        )
        return task
    
    async def get_task(self,task_id: UUID) -> Task | None:
        return await self.repo.get_by_id(task_id)
    
    async def list_tasks(
        self, user_id: str, limit: int = 10, offset: int = 0
    ) -> tuple[list[Task], int]:
        tasks = await self.repo.get_by_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
        total = await self.repo.count_by_user(user_id)
        return tasks, total
    
    async def update_status(
        self, task_id: UUID, new_status: TaskStatus
    ) -> Task | None:
        task = await self.repo.get_by_id(task_id)
        if not task:
            return None
        allowed = VALID_TRANSITIONS.get(task.status,[])
        if new_status not in allowed:
            raise ValueError(
                f"'{task.status}' -> '{new_status}' is not allowed. "
                f"Allowed: {allowed}"
            )
        return await self.repo.update_status(task_id,new_status)

    async def cancel_task(self, task_id: UUID) -> Task | None:
        task = await self.update_status(task_id, TaskStatus.cancelled)
        if not task:
            return None
        await self.redis.set(f"cancelled:{task_id}","1")
        return task
    
    async def get_result(self, task_id: UUID) -> tuple[AnalysisResult | None, bool]:
        task = await self.repo.get_by_id(task_id)
        if not task:
            return None, False
        return task.result, True
