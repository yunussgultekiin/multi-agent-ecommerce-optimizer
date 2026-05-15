import json
import logging
from google.genai import types
from pydantic import ValidationError
from app.config import settings
from app.core import ToolResult
from app.gemini_client import call_gemini
from .models_market import MarketGapResult
from .prompts_market import (
    build_market_gap_prompt,
    build_fallback_prompt,
    build_self_correction_prompt,
)
from .utils_market import filter_valid_competitors, normalize_user_product, clean_json_response, log_tool_call

logger = logging.getLogger(__name__)

async def analyze_market_gap(
    user_product: dict,
    competitors: list[dict],
    sentiment_result: dict,
    trend_result: dict,
    max_retries: int = 2,
) -> ToolResult:
    no_competitors = len(competitors) == 0
    prompt = (
        build_fallback_prompt(user_product, sentiment_result, trend_result)
        if no_competitors
        else build_market_gap_prompt(user_product, competitors, sentiment_result, trend_result)
    )

    last_error = None
    fallback_used = no_competitors
    pain_point_count = len(sentiment_result.get("pain_points", []))
    trend_count = len(trend_result.get("trending_features", []))

    for attempt in range(max_retries + 1):
        if attempt > 0:
            fallback_used = True

        current_prompt = (
            build_self_correction_prompt(prompt, last_error)
            if attempt > 0
            else prompt
        )

        try:
            response_text, _ = await call_gemini(
                model=settings.gemini_flash_model,
                prompt=current_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                    max_output_tokens=2048 if attempt > 0 else 4096,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            cleaned = clean_json_response(response_text)
            data = json.loads(cleaned)
            result = MarketGapResult(**data)

            log_tool_call(
                valid_competitor_count=len(competitors),
                pain_point_count=pain_point_count,
                trend_count=trend_count,
                fallback_used=fallback_used,
                positioning_score=result.positioning_score,
            )

            return ToolResult(success=True, data=result.model_dump(), fallback_used=fallback_used)

        except (ValidationError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            logger.warning(
                "MarketGapAnalyzer attempt failed | attempt=%d error=%s",
                attempt + 1,
                last_error,
            )

            if attempt == max_retries:
                log_tool_call(
                    valid_competitor_count=len(competitors),
                    pain_point_count=pain_point_count,
                    trend_count=trend_count,
                    fallback_used=True,
                    positioning_score=None,
                )
                return ToolResult(
                    success=False,
                    fallback_used=True,
                    data={"error": f"Max retries reached: {last_error}"},
                )

        except Exception as exc:
            logger.exception(
                "Unexpected MarketGapAnalyzer error | competitors=%d",
                len(competitors),
            )
            log_tool_call(
                valid_competitor_count=len(competitors),
                pain_point_count=pain_point_count,
                trend_count=trend_count,
                fallback_used=True,
                positioning_score=None,
            )
            return ToolResult(success=False, fallback_used=True, data={"error": str(exc)})

    return ToolResult(success=False, fallback_used=True, data={"error": "Unexpected error"})

async def run_market_gap_analyzer(
    user_product: dict,
    competitor_tool_results: list[ToolResult],
    sentiment_result: dict,
    trend_result: dict,
) -> ToolResult:
    valid_competitors = filter_valid_competitors(competitor_tool_results)
    normalized_product = normalize_user_product(user_product)

    if not valid_competitors:
        logger.warning("No valid competitors found, running fallback analysis.")

    return await analyze_market_gap(
        user_product=normalized_product,
        competitors=valid_competitors,
        sentiment_result=sentiment_result or {},
        trend_result=trend_result or {},
    )
