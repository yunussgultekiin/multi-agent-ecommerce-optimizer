from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.tasks import Task, AnalysisResult
from app.enums import TaskStatus

class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: str, input_url: str, keywords: list[str]) -> Task:
        task = Task(
            user_id = user_id,
            input_url = input_url,
            keywords = keywords
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get_by_id(self, task_id: UUID) -> Task | None:
        result = await self.session.execute(
            select(Task)
            .options(selectinload(Task.result))
            .where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def count_by_user(self, user_id: str) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Task).where(Task.user_id == user_id)
        )
        return result.scalar_one()

    async def get_by_user(
        self, user_id: str, limit: int = 10, offset: int = 0
    ) -> list[Task]:
        result = await self.session.execute(
            select(Task)
            .where(Task.user_id == user_id)
            .order_by(Task.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update_status(self, task_id: UUID, status: TaskStatus) -> Task | None:
        task = await self.get_by_id(task_id)
        if not task:
            return None
        task.status = status
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def save_result(self, task_id: UUID, result: dict) -> AnalysisResult:
        analysis_result = AnalysisResult(
            task_id = task_id,
            result = result
        )
        self.session.add(analysis_result)
        await self.session.commit()
        await self.session.refresh(analysis_result)
        return analysis_result
