import json

_JSON_SCHEMA = """{
    "clusters": [
        {
            "label": "budget",
            "competitors": ["competitor1", "competitor2"],
            "price_range_min": 0.0,
            "price_range_max": 0.0
        },
        {
            "label": "value_for_money",
            "competitors": ["competitor3"],
            "price_range_min": 0.0,
            "price_range_max": 0.0
        },
        {
            "label": "premium",
            "competitors": ["competitor4"],
            "price_range_min": 0.0,
            "price_range_max": 0.0
        }
    ],
    "user_product_cluster": "value_for_money",
    "gap_opportunities": ["opportunity1", "opportunity2"],
    "brand_landscape": {
        "premium_brands": ["brand1"],
        "budget_brands": ["brand2"],
        "user_brand_position": "position of the user brand"
    },
    "positioning_score": 0.0,
    "positioning_rationale": "1-2 sentence explanation",
    "variant_gap_opportunities": []
}"""

_COMMON_RULES = """
    Rules:
    - positioning_score must be between 0.0 and 1.0
    - positioning_rationale is required and explains Gemini's decision in 1-2 sentences
    - clusters must contain at least 1 segment
    - gap_opportunities must contain at least 1 opportunity
    - price_range_min and price_range_max must always be a number (float). If price data is unknown, use 0.0. NEVER use null or omit these fields.
"""


def build_market_gap_prompt(user_product: dict, competitors: list[dict]) -> str:
    return f"""
    Analyze the user product and competitor products below to identify market gaps.

    USER PRODUCT:
    {json.dumps(user_product, ensure_ascii=False)}

    COMPETITOR PRODUCTS:
    {json.dumps(competitors, ensure_ascii=False)}

    TASK:
    1. Segment competitor products by price and perceived value as: budget, value_for_money, premium
    2. Determine which segment the user product is positioned in
    3. Identify market gaps the user's product can fill compared to competitors
    4. Compare the user brand with competitor brands and analyze brand positioning
    5. If the user has product variants, evaluate whether they provide an advantage in terms of market gaps
    6. If there are no variants, return variant_gap_opportunities as an empty list

    RESPOND ONLY in this JSON format and do not write anything else:
    {_JSON_SCHEMA}
    {_COMMON_RULES}
    """


def build_user_product_only_prompt(user_product: dict) -> str:
    return f"""
    No competitor data is available. Use your general knowledge of this product category
    to estimate typical market segments and identify positioning opportunities for the user product.

    USER PRODUCT:
    {json.dumps(user_product, ensure_ascii=False)}

    TASK:
    1. Based on the product category and features, infer typical market segments: budget, value_for_money, premium
    2. Estimate realistic price ranges for each segment using your general knowledge (use 0.0 if truly unknown)
    3. Determine which segment best fits the user product
    4. Identify market gaps or positioning advantages the user product could exploit
    5. Assess the brand positioning based on the brand name and product features alone
    6. If the user has product variants, evaluate whether they provide an advantage in terms of market gaps
    7. If there are no variants, return variant_gap_opportunities as an empty list
    8. For competitors fields in clusters, use empty lists since no competitor data is available

    RESPOND ONLY in this JSON format and do not write anything else:
    {_JSON_SCHEMA}
    {_COMMON_RULES}
    """

def build_self_correction_prompt(original_prompt: str, last_error: str) -> str:
    return f"""
    THE PREVIOUS ATTEMPT FAILED. Pydantic validation error:
    {last_error}

    Fix these errors and return ONLY valid JSON.
    Pay special attention to:
    - positioning_score must be between 0.0 and 1.0
    - clusters must contain at least 1 item
    - positioning_rationale cannot be empty
    - if there are no variant_gap_opportunities, return an empty list []
    - price_range_min and price_range_max must always be a number (float). Use 0.0 if unknown. NEVER use null.

    ORIGINAL TASK:
    {original_prompt}
    """