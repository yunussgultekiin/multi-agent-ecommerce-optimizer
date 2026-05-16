from .models_price import CompetitorVariantOverlap, Positioning, VariantPricing
import logging
import math
import re
import statistics
from typing import Optional

logger = logging.getLogger(__name__)

def filter_valid_competitors(tool_results: list) -> list[dict]:
    valid = []
    for result in tool_results:
        if result.success and isinstance(result.data, dict) and result.data:
            data = result.data
            valid.append(
                {
                    "competitor_name": data.get("competitor_name", ""),
                    "estimated_price": data.get("estimated_price"),
                    "rating": data.get("rating"),
                    "review_count": data.get("review_count"),
                    "brand": data.get("brand"),
                    "features": data.get("features", []),
                    "variants": data.get("variants", []),
                }
            )
    return valid

def extract_valid_prices(competitors: list[dict]) -> list[float]:
    return [
        c["estimated_price"]
        for c in competitors
        if c.get("estimated_price") is not None
        and isinstance(c["estimated_price"], (int, float))
        and c["estimated_price"] > 0
    ]

def calculate_price_stats(prices: list[float]) -> dict:
    sorted_prices = sorted(prices)
    median = statistics.median(sorted_prices)
    mid = len(sorted_prices) // 2
    lower_half = sorted_prices[:mid]
    upper_half = (
        sorted_prices[mid:] if len(sorted_prices) % 2 == 0 else sorted_prices[mid + 1 :]
    )
    q1 = statistics.median(lower_half) if lower_half else median
    q3 = statistics.median(upper_half) if upper_half else median
    iqr = q3 - q1

    return {
        "median": median,
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "price_range_min": max(0.0, q1 - 1.5 * iqr),
        "price_range_max": q3 + 1.5 * iqr,
    }

def determine_positioning(user_price: float, q1: float, q3: float) -> Positioning:
    if user_price < q1:
        return Positioning.underpriced
    elif user_price > q3:
        return Positioning.overpriced
    return Positioning.optimal

def calculate_positioning_score(
    user_price: float, q1: float, q3: float, median: float
) -> float:
    if q1 == q3:
        return 1.0 if user_price == median else 0.5

    distance = abs(user_price - median)
    max_distance = max(abs(q3 - median), abs(q1 - median))

    if max_distance == 0:
        return 1.0

    return round(1.0 - min(distance / max_distance, 1.0), 4)

def calculate_market_power_score(
    rating: Optional[float], review_count: Optional[int]
) -> float:
    if rating is None or review_count is None:
        return 0.0
    return round(rating * math.log(review_count + 1), 4)

def calculate_market_power_gap(
    user_rating: Optional[float],
    user_review_count: Optional[int],
    competitors: list[dict],
) -> str:
    user_score = calculate_market_power_score(user_rating, user_review_count)
    competitor_scores = [
        calculate_market_power_score(c.get("rating"), c.get("review_count"))
        for c in competitors
    ]

    if not competitor_scores:
        return "No competitor market power data available."

    avg = sum(competitor_scores) / len(competitor_scores)
    gap = user_score - avg

    if gap > 1.0:
        return f"User product is strongly positioned vs competitors (gap: +{gap:.2f})"
    elif gap < -1.0:
        return f"User product is weakly positioned vs competitors (gap: {gap:.2f})"
    return f"User product has similar market power to competitors (gap: {gap:.2f})"

def calculate_confidence_score(valid_price_count: int) -> float:
    if valid_price_count >= 7:
        return 0.9
    elif 4 <= valid_price_count <= 6:
        return 0.7
    elif 2 <= valid_price_count <= 3:
        return 0.5
    return 0.0

def calculate_variant_pricing(
    user_variants: list[dict],
    q1: float,
    q3: float,
    median: float,
) -> list[VariantPricing]:
    if not user_variants:
        return []

    result = []
    for variant in user_variants:
        base_price = variant.get("price", median)
        price_delta = base_price - median
        suggested_price = max(q1, min(base_price, q3))
        result.append(
            VariantPricing(
                variant_name=variant.get("name", ""),
                base_price=base_price,
                price_delta=round(price_delta, 3),
                suggested_price=round(suggested_price, 3),
                positioning=determine_positioning(base_price, q1, q3),
            )
        )

    return result

def calculate_competitor_variant_overlap(
    user_variants: list[dict],
    competitors: list[dict],
) -> list[CompetitorVariantOverlap]:
    if not user_variants:
        return []

    overlap_results = []
    for user_variant in user_variants:
        user_name = user_variant.get("name", "").lower()
        matching = []

        for competitor in competitors:
            for comp_variant in competitor.get("variants", []):
                comp_name = (
                    comp_variant.lower()
                    if isinstance(comp_variant, str)
                    else comp_variant.get("name", "").lower()
                )
                if (
                    user_name
                    and comp_name
                    and (user_name in comp_name or comp_name in user_name)
                ):
                    matching.append(competitor["competitor_name"])
                    break

        overlap_results.append(
            CompetitorVariantOverlap(
                variant_name=user_variant.get("name", ""),
                matching_competitors=matching,
            )
        )

    return overlap_results

def normalize_user_product(user_product: dict) -> dict:
    return {
        "title": user_product.get("title", ""),
        "brand": user_product.get("brand", ""),
        "price": user_product.get("price"),
        "category": user_product.get("category", ""),
        "features": user_product.get("features", []),
        "variants": user_product.get("variants", []),
        "rating": user_product.get("rating"),
        "review_count": user_product.get("review_count"),
    }

def clean_json_response(raw_text: str) -> str:
    text = (raw_text or "").strip()

    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()

    first_brace = text.find("{")
    last_brace = text.rfind("}")

    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1].strip()

    return text

def log_tool_call(
    valid_price_count: int,
    positioning: Optional[str],
    confidence_score: Optional[float],
    fallback_used: bool,
) -> None:
    logger.info(
        "SmartPricingEngine call completed",
        extra={
            "valid_price_count": valid_price_count,
            "positioning": positioning,
            "confidence_score": confidence_score,
            "fallback_used": fallback_used,
        },
    )
