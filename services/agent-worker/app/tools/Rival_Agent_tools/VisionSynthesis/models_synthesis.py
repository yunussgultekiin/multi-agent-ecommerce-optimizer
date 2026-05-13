from pydantic import BaseModel, Field, field_validator
from typing import Optional

class ImageAnalysisResult(BaseModel):
    dominant_colors: list[str] = Field(..., min_length = 1, max_length=10)
    composition_style: str
    background_type: str
    product_focus_score: float = Field(..., ge = 0.0, le = 1.0)
    quality_score: float = Field(..., ge = 0.0, le = 1.0)
    style_tags: list[str] = Field(..., min_length = 1)
    improvement_suggestions: list[str]
    generation_prompt: str = Field(..., min_length = 20)

    @field_validator('dominant_colors')
    def color_must_be_hex_or_named(cls,v):
        return v