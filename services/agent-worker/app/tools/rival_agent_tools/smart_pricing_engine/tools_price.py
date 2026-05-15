from .models_price import PricingResult
from .prompts_price import (
    build_fallback_pricing_prompt,
    build_fallback_self_correction_prompt,
)
from .utils_price import (
    calculate_competitor_variant_overlap,
    calculate_confidence_score,
    calculate_market_power_gap,
    calculate_positioning_score,
    calculate_price_stats,
    calculate_variant_pricing,
    clean_json_response,
    determine_positioning,
    extract_valid_prices,
    filter_valid_competitors,
    log_tool_call,
    normalize_user_product,
)
from app.config import settings
from app.core import ToolResult
from app.gemini_client import call_gemini
from google.genai import types
import json
import logging
from pydantic import ValidationError
from typing import Optional

logger = logging.getLogger(__name__)

async def run_fallback_analysis(
    user_product: dict,
    competitors: list[dict],
    gap_result: Optional[dict] = None,
    sentiment_result: Optional[dict] = None,
    trend_result: Optional[dict] = None,
    target_platform: str = "",
    max_retries: int = 2,
) -> ToolResult:
    prompt = build_fallback_pricing_prompt(
        user_product=user_product,
        competitors=competitors,
        gap_result=gap_result,
        sentiment_result=sentiment_result,
        trend_result=trend_result,
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
            response_text, _ = await call_gemini(
                model=settings.gemini_flash_model,
                prompt=current_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                    max_output_tokens=2048,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            cleaned = clean_json_response(response_text)
            data = json.loads(cleaned)
            result = PricingResult(**data)

            log_tool_call(
                valid_price_count=0,
                positioning=result.positioning.value,
                confidence_score=result.confidence_score,
                fallback_used=True,
            )

            return ToolResult(
                success=True, data=result.model_dump(), fallback_used=True
            )

        except (ValidationError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            logger.warning(
                "SmartPricingEngine fallback failed | attempt=%d error=%s",
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
                    data={"error": f"Max retries reached: {last_error}"},
                )

        except Exception as exc:
            logger.exception("Unexpected SmartPricingEngine error")
            log_tool_call(
                valid_price_count=0,
                positioning=None,
                confidence_score=None,
                fallback_used=True,
            )
            return ToolResult(
                success=False, fallback_used=True, data={"error": str(exc)}
            )

    return ToolResult(
        success=False, fallback_used=True, data={"error": "Unexpected error"}
    )

def run_deterministic_analysis(
    user_product: dict,
    competitors: list[dict],
    valid_prices: list[float],
) -> ToolResult:
    stats = calculate_price_stats(valid_prices)
    price_provided = bool(user_product.get("price"))
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
        fallback_used=not price_provided,
    )

    return ToolResult(
        success=True, data=result.model_dump(), fallback_used=not price_provided
    )

async def run_smart_pricing_engine(
    user_product: dict,
    competitor_tool_results: list,
    gap_result: Optional[dict] = None,
    sentiment_result: Optional[dict] = None,
    trend_result: Optional[dict] = None,
    target_platform: str = "",
) -> ToolResult:
    normalized_user_product = normalize_user_product(user_product)
    valid_competitors = filter_valid_competitors(competitor_tool_results)
    valid_prices = extract_valid_prices(valid_competitors)

    logger.info(
        "SmartPricingEngine | valid_competitors=%d valid_prices=%d",
        len(valid_competitors),
        len(valid_prices),
    )

    if len(valid_prices) < 2:
        logger.warning("Insufficient price data, activating Gemini fallback.")
        return await run_fallback_analysis(
            user_product=normalized_user_product,
            competitors=valid_competitors,
            gap_result=gap_result,
            sentiment_result=sentiment_result,
            trend_result=trend_result,
            target_platform=target_platform,
        )

    user_price = normalized_user_product.get("price")
    if user_price:
        lo, hi = user_price * 0.1, user_price * 4.0
        sane_prices = [p for p in valid_prices if lo <= p <= hi]
        if len(sane_prices) < 2:
            logger.warning(
                "Price outliers detected: user=%.2f competitors=%s — activating Gemini fallback.",
                user_price,
                valid_prices,
            )
            return await run_fallback_analysis(
                user_product=normalized_user_product,
                competitors=valid_competitors,
                gap_result=gap_result,
                sentiment_result=sentiment_result,
                trend_result=trend_result,
                target_platform=target_platform,
            )
        valid_prices = sane_prices

    return run_deterministic_analysis(
        normalized_user_product, valid_competitors, valid_prices
    )
