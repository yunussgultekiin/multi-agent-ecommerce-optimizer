from .models_trend import TrendResult
from .prompts_trend import (
    build_fallback_trend_prompt,
    build_self_correction_prompt,
    build_trend_prompt,
)
from .utils_trend import log_tool_call, parse_json_response
from app.config import settings
from app.core import ToolResult
from app.gemini_client import call_gemini
from google.genai import types
import logging
from pydantic import ValidationError

logger = logging.getLogger(__name__)

_GROUNDING_TOOL = types.Tool(google_search=types.GoogleSearch())

async def run_trend_analyzer(
    category: str,
    target_platform: str,
    user_product: dict,
    max_retries: int = 2,
) -> ToolResult:
    category = (
        category.strip()
        if isinstance(category, str) and category.strip()
        else "general"
    )
    product_title = user_product.get("title", "").strip()
    brand = user_product.get("brand", "").strip()

    base_prompt = build_trend_prompt(
        category=category,
        target_platform=target_platform,
        product_title=product_title,
        brand=brand,
    )

    last_error: str | None = None
    fallback_used = False
    grounding_hit = False

    for attempt in range(max_retries + 1):
        if attempt > 0:
            fallback_used = True

        current_prompt = (
            build_self_correction_prompt(base_prompt, last_error)
            if attempt > 0
            else base_prompt
        )

        try:
            response_text, grounding_hit = await call_gemini(
                model=settings.gemini_flash_model,
                prompt=current_prompt,
                config=types.GenerateContentConfig(
                    tools=[_GROUNDING_TOOL],
                    temperature=0.2,
                    max_output_tokens=1000,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            data = parse_json_response(response_text)
            result = TrendResult(**data)

            log_tool_call(
                category=category,
                platform=target_platform,
                trend_count=len(result.trending_features),
                grounding_hit=grounding_hit,
                fallback_used=fallback_used,
            )

            return ToolResult(
                success=True,
                fallback_used=fallback_used,
                data=result.model_dump(),
            )

        except (ValidationError, ValueError) as exc:
            last_error = str(exc)
            logger.warning(
                "TrendAnalyzerTool attempt failed | attempt=%d error=%s",
                attempt + 1,
                last_error,
            )
            fallback_used = True

            if attempt == max_retries:
                break

        except Exception as exc:
            logger.exception(
                "Unexpected TrendAnalyzerTool error | category=%s platform=%s",
                category,
                target_platform,
            )
            log_tool_call(
                category=category,
                platform=target_platform,
                trend_count=0,
                grounding_hit=grounding_hit,
                fallback_used=True,
            )
            return ToolResult(
                success=False, fallback_used=True, data={"error": str(exc)}
            )

    fallback_prompt = build_fallback_trend_prompt(
        category=category,
        target_platform=target_platform,
        product_title=product_title,
        brand=brand,
    )

    for attempt in range(max_retries + 1):
        current_prompt = (
            build_self_correction_prompt(fallback_prompt, last_error)
            if attempt > 0
            else fallback_prompt
        )

        try:
            response_text, _ = await call_gemini(
                model=settings.gemini_flash_model,
                prompt=current_prompt,
                config=types.GenerateContentConfig(
                    tools=[_GROUNDING_TOOL],
                    temperature=0.3,
                    max_output_tokens=800,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            data = parse_json_response(response_text)
            result = TrendResult(**data)

            log_tool_call(
                category=category,
                platform=target_platform,
                trend_count=len(result.trending_features),
                grounding_hit=False,
                fallback_used=True,
            )

            return ToolResult(
                success=True, fallback_used=True, data=result.model_dump()
            )

        except (ValidationError, ValueError) as exc:
            last_error = str(exc)
            logger.warning(
                "TrendAnalyzerTool fallback attempt failed | attempt=%d error=%s",
                attempt + 1,
                last_error,
            )

    log_tool_call(
        category=category,
        platform=target_platform,
        trend_count=0,
        grounding_hit=False,
        fallback_used=True,
    )
    return ToolResult(
        success=False,
        fallback_used=True,
        data={"error": f"Max retries reached: {last_error}"},
    )
