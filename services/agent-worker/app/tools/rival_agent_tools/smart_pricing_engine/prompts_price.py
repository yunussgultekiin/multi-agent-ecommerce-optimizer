import json
from typing import Optional

from app.tools.json_prompt_rules import JSON_SELF_CORRECTION_SYNTAX, STRICT_JSON_SYNTAX_RULES

def build_fallback_pricing_prompt(
    user_product: dict,
    competitors: list[dict],
    gap_result: Optional[dict] = None,
    sentiment_result: Optional[dict] = None,
    trend_result: Optional[dict] = None,
    target_platform: str = "",
) -> str:
    gap_block = (
        f"\nMARKET GAP ANALYSIS:\n{json.dumps(gap_result, ensure_ascii=False)}\n"
        if gap_result
        else ""
    )
    sentiment_block = (
        f"\nCUSTOMER SENTIMENT:\n{json.dumps(sentiment_result, ensure_ascii=False)}\n"
        if sentiment_result
        else ""
    )
    trend_block = (
        f"\nMARKET TRENDS:\n{json.dumps(trend_result, ensure_ascii=False)}\n"
        if trend_result
        else ""
    )
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

RESPOND ONLY in this exact JSON format (no markdown, no comments, no trailing commas):
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
    "variant_pricing": [
        {{
            "variant_name": "Example Variant",
            "base_price": 0.0,
            "price_delta": 0.0,
            "suggested_price": 0.0,
            "positioning": "optimal"
        }}
    ],
    "competitor_variant_overlap": [
        {{
            "variant_name": "Example Variant",
            "matching_competitors": []
        }}
    ]
}}

Rules:
- positioning (top-level and inside variant_pricing): must be exactly "underpriced", "optimal", or "overpriced".
- positioning_score: 0.0–1.0.
- confidence_score: maximum 0.4 (this is a fallback analysis).
- fallback_used: always true.
- variant_pricing items MUST use keys: variant_name, base_price, price_delta, suggested_price, positioning.
- competitor_variant_overlap items MUST use keys: variant_name, matching_competitors (list of strings).
- If no variants exist, return empty lists: "variant_pricing": [], "competitor_variant_overlap": [].
- Keep JSON keys and enum labels in English, but write all natural-language values in Turkish (e.g., market_power_gap text and any descriptive variant names).
- Do not invent specific competitor prices.
- All price and score fields must be finite JSON numbers or null — never NaN or Infinity.
- Use null only where the schema allows missing values; otherwise use conservative finite estimates (0.0 is not a substitute for unknown competitor prices in upstream data).
{STRICT_JSON_SYNTAX_RULES}
"""

def build_fallback_self_correction_prompt(original_prompt: str, last_error: str) -> str:
    return f"""
THE PREVIOUS ATTEMPT FAILED. Pydantic validation error:
{last_error}

Fix ALL errors and return ONLY valid JSON.
Key rules:
- positioning (top-level and inside variant_pricing) must be "underpriced", "optimal", or "overpriced".
- positioning_score and confidence_score must be 0.0–1.0.
- confidence_score must not exceed 0.4.
- fallback_used must be true.
- variant_pricing items MUST use keys: variant_name, base_price, price_delta, suggested_price, positioning.
- competitor_variant_overlap items MUST use keys: variant_name, matching_competitors (list of strings).
- If no variants, return empty lists: "variant_pricing": [], "competitor_variant_overlap": [].
- Keep JSON keys in English, but write all value texts in Turkish.
- Never output NaN or Infinity for any numeric field — use null or a finite number.
{JSON_SELF_CORRECTION_SYNTAX}

ORIGINAL TASK:
{original_prompt}
"""
