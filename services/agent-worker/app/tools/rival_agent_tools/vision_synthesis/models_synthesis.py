import re
from typing import Literal
from pydantic import BaseModel, Field, field_validator

HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")

SynthesisMode = Literal[
    "competitor_supported",
    "partial_competitor_supported",
    "fallback_user_product_only",
]

class ImageAnalysisResult(BaseModel):
    dominant_colors: list[str] = Field(..., min_length=1, max_length=10)
    composition_style: str = Field(..., min_length=3)
    background_type: str = Field(..., min_length=3)
    product_focus_score: float = Field(..., ge=0.0, le=1.0)
    quality_score: float = Field(..., ge=0.0, le=1.0)
    style_tags: list[str] = Field(..., min_length=1, max_length=15)
    improvement_suggestions: list[str] = Field(default_factory=list, max_length=10)
    generation_prompt: str = Field(..., min_length=20, max_length=500)

    synthesis_mode: SynthesisMode = "fallback_user_product_only"
    valid_competitor_image_count: int = Field(default=0, ge=0, le=5)
    fallback_used: bool = False

    @field_validator("dominant_colors")
    @classmethod
    def color_must_be_hex_or_named(cls, values: list[str]) -> list[str]:
        for color in values:
            if not isinstance(color, str) or not color.strip():
                raise ValueError("Each dominant color must be a non-empty string")

            normalized = color.strip()

            is_hex = bool(HEX_COLOR_RE.match(normalized))
            is_named_color = normalized.replace(" ", "").replace("-", "").isalpha()

            if not is_hex and not is_named_color:
                raise ValueError(f"Invalid color format: {color}")

        return values

    @field_validator("generation_prompt")
    @classmethod
    def generation_prompt_must_start_correctly(cls, value: str) -> str:
        required_prefix = "Edit the provided product image into"

        if not value.startswith(required_prefix):
            raise ValueError(
                f'generation_prompt must start with "{required_prefix}"'
            )

        return value