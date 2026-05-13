from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.enums import TaskStatus

class TaskCreate(BaseModel):
    user_id: str
    payload: dict

class TaskResultCreate(BaseModel):
    result: dict

class TaskResponse(BaseModel):
    id: UUID
    user_id: str
    status: TaskStatus
    payload: dict
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class TaskResultResponse(BaseModel):
    task_id: UUID
    result: dict
    created_at: datetime

    model_config = {"from_attributes": True}

class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    limit: int
    offset: int

class TaskStatusUpdate(BaseModel):
    status: TaskStatus
    error_message: str | None = None
