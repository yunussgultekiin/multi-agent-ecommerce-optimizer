import asyncio
import json
import logging
import google.auth.exceptions
import google.api_core.exceptions
from pydantic import ValidationError
from google import genai
from google.genai import types
from google.genai.types import HttpOptions
from app.config import settings
from app.core import ToolResult
from .models_market import MarketGapResult
from .prompts_market import (
    build_market_gap_prompt,
    build_fallback_prompt,
    build_self_correction_prompt,
)
from .utils_market import filter_valid_competitors, normalize_user_product, clean_json_response, log_tool_call

logger = logging.getLogger(__name__)

_client = genai.Client(
    vertexai=True,
    project=settings.google_cloud_project,
    location=settings.google_cloud_location,
    http_options=HttpOptions(api_version="v1"),
)


async def _call_gemini(prompt: str, max_output_tokens: int = 1600) -> str:
    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: _client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                    max_output_tokens=max_output_tokens,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            ),
        )
    except google.auth.exceptions.DefaultCredentialsError as exc:
        raise RuntimeError(
            "Google Cloud credentials not configured. "
            "Run: gcloud auth application-default login"
        ) from exc
    except google.api_core.exceptions.NotFound as exc:
        raise RuntimeError(
            f"Model '{settings.gemini_model}' not found in region '{settings.google_cloud_location}'."
        ) from exc
    except google.api_core.exceptions.PermissionDenied as exc:
        raise RuntimeError(
            f"Permission denied for project '{settings.google_cloud_project}'."
        ) from exc

    return response.text or ""


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
            response_text = await _call_gemini(
                current_prompt,
                max_output_tokens=1000 if attempt > 0 else 1600,
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
