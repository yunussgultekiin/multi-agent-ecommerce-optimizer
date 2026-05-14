import json

def build_fallback_pricing_prompt(
    user_product: dict,
    competitors: list[dict],
) -> str:
    return f"""
    Perform a pricing analysis for the following user product and competitor data.
    Since there is not enough pricing data available, generate an estimated pricing interpretation.

    USER PRODUCT:
    {json.dumps(user_product, ensure_ascii=False)}

    COMPETITOR DATA:
    {json.dumps(competitors, ensure_ascii=False)}

    TASK:
    1. Estimate a reasonable price range based on the available competitor data, category, and features
    2. Determine the position of the user product within this range
    3. Summarize the market power gap

    RESPOND ONLY in this JSON format and do not write anything else:
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
    - positioning must be "underpriced", "optimal", or "overpriced"
    - positioning_score must be between 0.0 and 1.0
    - confidence_score must be a maximum of 0.4 because this is a fallback analysis
    - fallback_used must always be true
    """

def build_fallback_self_correction_prompt(original_prompt: str, last_error: str) -> str:
    return f"""
    THE PREVIOUS ATTEMPT FAILED. Pydantic validation error:
    {last_error}

    Fix these errors and return ONLY valid JSON.
    Pay special attention to:
    - positioning must be "underpriced", "optimal", or "overpriced"
    - positioning_score and confidence_score must be between 0.0 and 1.0
    - confidence_score must not exceed 0.4
    - fallback_used must be true
    - if variant_pricing and competitor_variant_overlap do not exist, return empty lists []

    ORIGINAL TASK:
    {original_prompt}
    """