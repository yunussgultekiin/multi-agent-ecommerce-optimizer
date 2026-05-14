import asyncio
import json
import logging
from typing import Optional
from pydantic import ValidationError
import google.auth.exceptions
import google.api_core.exceptions
from google import genai
from google.genai import types
from google.genai.types import HttpOptions
from app.config import settings
from app.core import ToolResult
from .models_price import PricingResult
from .prompts_price import build_fallback_pricing_prompt, build_fallback_self_correction_prompt
from .utils_price import (
    filter_valid_competitors,
    extract_valid_prices,
    calculate_price_stats,
    determine_positioning,
    calculate_positioning_score,
    calculate_market_power_gap,
    calculate_confidence_score,
    calculate_variant_pricing,
    calculate_competitor_variant_overlap,
    normalize_user_product,
    clean_json_response,
    log_tool_call,
)

logger = logging.getLogger(__name__)

_client = genai.Client(
    vertexai=True,
    project=settings.google_cloud_project,
    location=settings.google_cloud_location,
    http_options=HttpOptions(api_version="v1"),
)

async def _call_gemini(prompt: str) -> str:
    loop = asyncio.get_running_loop()

    try:
        response = await loop.run_in_executor(
            None,
            lambda: _client.models.generate_content(
                model=settings.gemini_research_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                    max_output_tokens=800,
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
            f"Model '{settings.gemini_research_model}' not found in region '{settings.google_cloud_location}'. "
            "Check the model name and location."
        ) from exc
    except google.api_core.exceptions.PermissionDenied as exc:
        raise RuntimeError(
            f"Permission denied. Ensure the account has the 'Vertex AI User' role "
            f"in project '{settings.google_cloud_project}'."
        ) from exc

    return response.text or ""

async def run_fallback_analysis(
    user_product: dict,
    competitors: list[dict],
    gap_result: Optional[dict] = None,
    target_platform: str = "",
    max_retries: int = 2,
) -> ToolResult:
    prompt = build_fallback_pricing_prompt(
        user_product=user_product,
        competitors=competitors,
        gap_result=gap_result,
        target_platform=target_platform,
    )
    last_error = None

    for attempt in range(max_retries + 1):
        current_prompt = (
            build_fallback_self_correction_prompt(prompt, last_error)
            if attempt > 0
            else prompt
        )

        try:
            response_text = await _call_gemini(current_prompt)
            cleaned = clean_json_response(response_text)
            data = json.loads(cleaned)
            result = PricingResult(**data)

            log_tool_call(
                valid_price_count=0,
                positioning=result.positioning.value,
                confidence_score=result.confidence_score,
                fallback_used=True,
            )

            return ToolResult(success=True, data=result.model_dump(), fallback_used=True)

        except (ValidationError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            logger.warning(
                "SmartPricingEngine fallback attempt failed | attempt=%d error=%s",
                attempt + 1,
                last_error,
            )

            if attempt == max_retries:
                log_tool_call(
                    valid_price_count=0,
                    positioning=None,
                    confidence_score=None,
                    fallback_used=True,
                )

                return ToolResult(
                    success=False,
                    fallback_used=True,
                    data={"error": f"Maximum retry reached: {last_error}"},
                )

    return ToolResult(success=False, fallback_used=True, data={"error": "Unexpected error"})

def run_deterministic_analysis(
    user_product: dict,
    competitors: list[dict],
    valid_prices: list[float],
) -> ToolResult:
    stats = calculate_price_stats(valid_prices)
    user_price = user_product.get("price") or stats["median"]
    user_variants = user_product.get("variants", [])

    positioning = determine_positioning(user_price, stats["q1"], stats["q3"])
    positioning_score = calculate_positioning_score(
        user_price, stats["q1"], stats["q3"], stats["median"]
    )
    market_power_gap = calculate_market_power_gap(
        user_product.get("rating"),
        user_product.get("review_count"),
        competitors,
    )
    confidence_score = calculate_confidence_score(len(valid_prices))
    variant_pricing = calculate_variant_pricing(
        user_variants, stats["q1"], stats["q3"], stats["median"]
    )
    competitor_variant_overlap = calculate_competitor_variant_overlap(
        user_variants, competitors
    )

    result = PricingResult(
        price_median=stats["median"],
        price_q1=stats["q1"],
        price_q3=stats["q3"],
        predicted_price=stats["median"],
        price_range_min=stats["price_range_min"],
        price_range_max=stats["price_range_max"],
        positioning=positioning,
        positioning_score=positioning_score,
        market_power_gap=market_power_gap,
        confidence_score=confidence_score,
        fallback_used=False,
        variant_pricing=variant_pricing,
        competitor_variant_overlap=competitor_variant_overlap,
    )

    log_tool_call(
        valid_price_count=len(valid_prices),
        positioning=positioning.value,
        confidence_score=confidence_score,
        fallback_used=False,
    )

    return ToolResult(success=True, data=result.model_dump(), fallback_used=False)

async def run_smart_pricing_engine(
    user_product: dict,
    competitor_tool_results: list,
    gap_result: Optional[dict] = None,
    target_platform: str = "",
) -> ToolResult:
    normalized_user_product = normalize_user_product(user_product)
    valid_competitors = filter_valid_competitors(competitor_tool_results)
    valid_prices = extract_valid_prices(valid_competitors)

    logger.info(
        "SmartPricingEngine initialized | valid_competitor_count=%d | valid_price_count=%d",
        len(valid_competitors),
        len(valid_prices),
    )

    if len(valid_prices) < 2:
        logger.warning("Not enough pricing data, activating Gemini fallback.")
        return await run_fallback_analysis(
            user_product=normalized_user_product,
            competitors=valid_competitors,
            gap_result=gap_result,
            target_platform=target_platform,
        )

    return run_deterministic_analysis(normalized_user_product, valid_competitors, valid_prices)
