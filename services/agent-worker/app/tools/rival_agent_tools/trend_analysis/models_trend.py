from pydantic import BaseModel, Field, field_validator


class TrendResult(BaseModel):
    trending_features: list[str] = Field(..., min_length=1)
    demand_signals: list[str] = Field(default_factory=list)
    platform_trends: list[str] = Field(default_factory=list)
    category_trend_summary: str = Field(..., min_length=1)

    @field_validator("trending_features", "demand_signals", "platform_trends")
    @classmethod
    def normalize_list(cls, values: list[str]) -> list[str]:
        result = []
        for v in values or []:
            if isinstance(v, str) and v.strip():
                result.append(v.strip())
        return list(dict.fromkeys(result))

    @field_validator("category_trend_summary")
    @classmethod
    def normalize_summary(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("category_trend_summary cannot be empty")
        return value
