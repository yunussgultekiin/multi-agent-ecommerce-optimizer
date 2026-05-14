import json

_JSON_SCHEMA = """{
    "clusters": [
        {
            "label": "budget",
            "competitors": ["competitor1"],
            "price_range_min": 0.0,
            "price_range_max": 0.0
        }
    ],
    "user_product_cluster": "value_for_money",
    "gap_opportunities": ["opportunity1"],
    "sentiment_based_opportunities": ["opportunity derived from customer pain points"],
    "trend_based_opportunities": ["opportunity derived from market trends"],
    "strategic_actions": ["concrete action the seller can take"],
    "brand_landscape": {
        "premium_brands": ["brand1"],
        "budget_brands": ["brand2"],
        "user_brand_position": "position description"
    },
    "positioning_score": 0.0,
    "positioning_rationale": "1-2 sentence explanation",
    "variant_gap_opportunities": []
}"""

_COMMON_RULES = """
Rules:
- positioning_score: 0.0 (weakly positioned) to 1.0 (strongly positioned).
- positioning_rationale: required, 1-2 sentences explaining the score.
- clusters: at least 1 segment (budget / value_for_money / premium).
- price_range_min and price_range_max: always a float, use 0.0 if unknown, never null.
- gap_opportunities: at least 1 actionable opportunity.
- sentiment_based_opportunities: opportunities directly derived from customer pain_points; [] if no sentiment data.
- trend_based_opportunities: opportunities derived from trending features; [] if no trend data.
- strategic_actions: concrete next steps the seller can act on; [] if none.
- variant_gap_opportunities: [] if user product has no variants.
- Do not include markdown, comments, or trailing commas.
"""


def build_market_gap_prompt(
    user_product: dict,
    competitors: list[dict],
    sentiment_result: dict,
    trend_result: dict,
) -> str:
    sentiment_block = ""
    if sentiment_result:
        sentiment_block = f"""
CUSTOMER SENTIMENT DATA:
{json.dumps(sentiment_result, ensure_ascii=False)}
"""

    trend_block = ""
    if trend_result:
        trend_block = f"""
MARKET TREND DATA:
{json.dumps(trend_result, ensure_ascii=False)}
"""

    return f"""
Analyze the user product and competitor products to identify market gaps and positioning opportunities.

USER PRODUCT:
{json.dumps(user_product, ensure_ascii=False)}

COMPETITOR PRODUCTS:
{json.dumps(competitors, ensure_ascii=False)}
{sentiment_block}{trend_block}
TASK:
1. Segment competitors by price and perceived value: budget, value_for_money, premium.
2. Determine which segment the user product fits.
3. Identify market gaps the user product can fill based on competitor weaknesses.
4. If sentiment data is provided: derive opportunities from customer pain_points (what competitors fail at) AND praised_features (what competitors do well that the user product should match or exceed).
5. If trend data is provided: derive opportunities from trending_features that the user product could emphasize.
6. Generate at least 2 strategic actions the seller can concretely take.
7. Compare user brand with competitor brands and analyze brand positioning.
8. If user product has variants, evaluate whether they provide a market gap advantage.

RESPOND ONLY in this JSON format:
{_JSON_SCHEMA}
{_COMMON_RULES}
"""


def build_fallback_prompt(user_product: dict, sentiment_result: dict, trend_result: dict) -> str:
    sentiment_block = ""
    if sentiment_result:
        sentiment_block = f"""
CUSTOMER SENTIMENT DATA:
{json.dumps(sentiment_result, ensure_ascii=False)}
"""

    trend_block = ""
    if trend_result:
        trend_block = f"""
MARKET TREND DATA:
{json.dumps(trend_result, ensure_ascii=False)}
"""

    return f"""
No competitor data is available. Use general knowledge of this product category to estimate
typical market segments and positioning opportunities.
{sentiment_block}{trend_block}
USER PRODUCT:
{json.dumps(user_product, ensure_ascii=False)}

TASK:
1. Infer typical market segments (budget / value_for_money / premium) from category knowledge.
2. Estimate realistic price ranges; use 0.0 if truly unknown.
3. Determine the best-fit segment for the user product.
4. Identify positioning opportunities the user product could exploit.
5. If sentiment data is provided: derive sentiment_based_opportunities from pain_points and praised_features.
6. If trend data is provided: derive trend_based_opportunities from trending_features.
7. Generate at least 1 strategic action.
8. Use empty lists for competitors fields in clusters.

RESPOND ONLY in this JSON format:
{_JSON_SCHEMA}
{_COMMON_RULES}
"""


def build_self_correction_prompt(original_prompt: str, last_error: str) -> str:
    return f"""
THE PREVIOUS ATTEMPT FAILED. Pydantic validation error:
{last_error}

Fix ALL errors and return ONLY valid JSON.
Key rules:
- positioning_score must be 0.0–1.0.
- clusters must have at least 1 item.
- positioning_rationale cannot be empty.
- price_range_min and price_range_max must be floats, never null.
- gap_opportunities must have at least 1 item.
- sentiment_based_opportunities, trend_based_opportunities, strategic_actions,
  variant_gap_opportunities may be empty lists but must be present.

ORIGINAL TASK:
{original_prompt}
"""
