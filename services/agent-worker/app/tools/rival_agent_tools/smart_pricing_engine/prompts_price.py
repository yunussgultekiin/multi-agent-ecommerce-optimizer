import json
from typing import Optional


def build_fallback_pricing_prompt(
    user_product: dict,
    competitors: list[dict],
    gap_result: Optional[dict] = None,
    sentiment_result: Optional[dict] = None,
    trend_result: Optional[dict] = None,
    target_platform: str = "",
) -> str:
    gap_block = f"\nMARKET GAP ANALYSIS:\n{json.dumps(gap_result, ensure_ascii=False)}\n" if gap_result else ""
    sentiment_block = f"\nCUSTOMER SENTIMENT:\n{json.dumps(sentiment_result, ensure_ascii=False)}\n" if sentiment_result else ""
    trend_block = f"\nMARKET TRENDS:\n{json.dumps(trend_result, ensure_ascii=False)}\n" if trend_result else ""
    platform_note = f"TARGET PLATFORM: {target_platform}\n" if target_platform else ""

    return f"""
Perform a pricing analysis for the user product below.
Pricing data is insufficient for deterministic analysis — generate a conservative estimated pricing interpretation.

{platform_note}
USER PRODUCT:
{json.dumps(user_product, ensure_ascii=False)}

COMPETITOR DATA:
{json.dumps(competitors, ensure_ascii=False)}
{gap_block}{sentiment_block}{trend_block}
TASK:
1. Estimate a reasonable price range from available competitor data, category knowledge, and context.
2. Determine the user product's positioning within this range.
3. Use gap, sentiment, and trend data if provided to refine the recommendation.
4. Be conservative — do not invent specific competitor prices.
5. If evidence is weak, return a lower confidence_score.

RESPOND ONLY in this JSON format:
{{
    "price_median": 0.0,
    "price_q1": 0.0,
    "price_q3": 0.0,
    "predicted_price": 0.0,
    "price_range_min": 0.0,
    "price_range_max": 0.0,
    "positioning": "optimal",
    "positioning_score": 0.0,
    "market_power_gap": "description",
    "confidence_score": 0.4,
    "fallback_used": true,
    "variant_pricing": [],
    "competitor_variant_overlap": []
}}

Rules:
- positioning: must be "underpriced", "optimal", or "overpriced".
- positioning_score: 0.0–1.0.
- confidence_score: maximum 0.4 (this is a fallback analysis).
- fallback_used: always true.
- Do not invent specific competitor prices.
- Do not include markdown, comments, or trailing commas.
"""


def build_fallback_self_correction_prompt(original_prompt: str, last_error: str) -> str:
    return f"""
THE PREVIOUS ATTEMPT FAILED. Pydantic validation error:
{last_error}

Fix ALL errors and return ONLY valid JSON.
Key rules:
- positioning must be "underpriced", "optimal", or "overpriced".
- positioning_score and confidence_score must be 0.0–1.0.
- confidence_score must not exceed 0.4.
- fallback_used must be true.
- variant_pricing and competitor_variant_overlap must be lists ([] if empty).

ORIGINAL TASK:
{original_prompt}
"""
