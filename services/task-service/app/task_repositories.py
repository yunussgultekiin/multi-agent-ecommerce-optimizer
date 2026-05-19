from app.enums import SeoTone, TaskStatus
from app.tasks import AnalysisResult, Task
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID

class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, user_id: str, payload: dict, seo_tone: SeoTone | None = None
    ) -> Task:
        task = Task(user_id=user_id, payload=payload, seo_tone=seo_tone)
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get_by_id(self, task_id: UUID) -> Task | None:
        result = await self.session.execute(
            select(Task).options(selectinload(Task.result)).where(Task.id == task_id)
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

    async def update_status(
        self, task_id: UUID, status: TaskStatus, error_message: str | None = None
    ) -> Task | None:
        task = await self.get_by_id(task_id)
        if not task:
            return None
        task.status = status
        if error_message is not None:
            task.error_message = error_message
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def save_result(self, task_id: UUID, result: dict) -> AnalysisResult:
        analysis_result = AnalysisResult(task_id=task_id, result=result)
        self.session.add(analysis_result)
        await self.session.commit()
        await self.session.refresh(analysis_result)
        return analysis_result

    async def delete_by_id(self, task_id: UUID) -> bool:
        task = await self.get_by_id(task_id)
        if not task:
            return False
        await self.session.execute(
            delete(AnalysisResult).where(AnalysisResult.task_id == task_id)
        )
        await self.session.execute(delete(Task).where(Task.id == task_id))
        await self.session.commit()
        return True

    async def delete_all_by_user(self, user_id: str) -> None:
        task_ids_result = await self.session.execute(
            select(Task.id).where(Task.user_id == user_id)
        )
        task_ids = list(task_ids_result.scalars().all())

        if task_ids:
            await self.session.execute(
                delete(AnalysisResult).where(AnalysisResult.task_id.in_(task_ids))
            )
            await self.session.execute(delete(Task).where(Task.user_id == user_id))

        await self.session.commit()
