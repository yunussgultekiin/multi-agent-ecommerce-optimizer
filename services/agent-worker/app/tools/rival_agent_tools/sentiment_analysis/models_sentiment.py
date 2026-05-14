from pydantic import BaseModel, Field, field_validator


class CompetitorSentiment(BaseModel):
    competitor_name: str
    positive: list[str] = Field(default_factory=list)
    negative: list[str] = Field(default_factory=list)


class SentimentResult(BaseModel):
    pain_points: list[str] = Field(..., min_length=1)
    praised_features: list[str] = Field(..., min_length=1)
    competitor_sentiments: list[CompetitorSentiment] = Field(default_factory=list)
    marketing_angles: list[str] = Field(default_factory=list)
    risk_warnings: list[str] = Field(default_factory=list)

    @field_validator("pain_points", "praised_features", "marketing_angles", "risk_warnings")
    @classmethod
    def normalize_list(cls, values: list[str]) -> list[str]:
        result = []
        for v in values or []:
            if isinstance(v, str) and v.strip():
                result.append(v.strip())
        return list(dict.fromkeys(result))
