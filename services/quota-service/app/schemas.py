from pydantic import BaseModel, Field


class QuotaResponse(BaseModel):
    user_id: str
    used: int
    limit: int
    remaining: int
    reset_in_seconds: int | None = Field(default=None)


class ConsumeResponse(BaseModel):
    user_id: str
    used: int
    limit: int
    remaining: int


class ResetResponse(BaseModel):
    user_id: str
    message: str = "Quota reset successfully"