from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, HttpUrl
from app.models.enums import TaskStatus

class Taskcreate(BaseModel):
    input_url: HttpUrl
    keywords: list[str]

class TaskResponse(BaseModel):
    id:UUID
    user_id: str
    status: TaskStatus
    input_url: str
    keywords: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {'from_attributes':True}

class TaskResultResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    limit: int
    offset: int

