import asyncio
import json
import logging
from pydantic import ValidationError
from google import genai
from google.genai import types
from app.config import settings
from app.core import ToolResult
from .models_market import MarketGapResult
from .prompts_market import build_market_gap_prompt, build_self_correction_prompt
from .utils_market import filter_valid_competitors, normalize_user_product, clean_json_response, log_tool_call

logger = logging.getLogger(__name__)

_client = genai.Client(api_key=settings.gemini_api_key or None)

async def _call_gemini(prompt: str) -> str:
    loop = asyncio.get_running_loop()

    response = await loop.run_in_executor(
        None,
        lambda: _client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        ),
    )

    return response.text or ""

async def analyze_market_gap(
    user_product: dict,
    competitors: list[dict],
    max_retries: int = 2,
) -> ToolResult:
    normalized_user_product = normalize_user_product(user_product)
    prompt = build_market_gap_prompt(normalized_user_product, competitors)
    last_error = None
    fallback_used = False

    for attempt in range(max_retries + 1):
        if attempt > 0:
            fallback_used = True

        current_prompt = (
            build_self_correction_prompt(prompt, last_error)
            if attempt > 0
            else prompt
        )

        try:
            response_text = await _call_gemini(current_prompt)
            cleaned = clean_json_response(response_text)
            data = json.loads(cleaned)
            result = MarketGapResult(**data)

            log_tool_call(
                valid_competitor_count=len(competitors),
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
    competitor_tool_results: list[ToolResult]
) -> ToolResult:
    valid_competitors = filter_valid_competitors(competitor_tool_results)

    if not valid_competitors:
        logger.warning("Not enough valid competitors found, performing fallback analysis.")

        log_tool_call(
            valid_competitor_count = 0,
            fallback_used = True,
            positioning_score = None
        )

        return ToolResult(
            success=False,
            fallback_used=True,
            data={"error": "Not enough valid competitors found"},
        )

    logger.info(f"Analyzing {len(valid_competitors)} valid competitors")

    return await analyze_market_gap(user_product, valid_competitors)
