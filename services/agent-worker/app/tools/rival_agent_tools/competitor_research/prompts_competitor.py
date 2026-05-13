def build_product_details_prompt(competitor_name: str) -> str:
    return f"""
    Research the following information about the product "{competitor_name}" and return ONLY in JSON format:

    Respond ONLY in this JSON format and do not write anything else:
    {{
        "competitor_name": "{competitor_name}",
        "price": 0.0,
        "features": ["feature1", "feature2"],
        "image_urls": ["https://..."],
        "rating": 0.0,
        "review_count": 0
    }}

    Rules:
    - price must be numeric, use null if unavailable
    - rating must be between 0.0 and 5.0, use null if unavailable
    - image_urls must contain real product image URLs
    - review_count must be an integer, use null if unavailable
    """


def build_trends_prompt(competitor_name: str, category: str) -> str:
    return f"""
    Research the current trends in the "{category}" category
    that the product "{competitor_name}" belongs to, and return ONLY in JSON format:

    Respond ONLY in this JSON format and do not write anything else:
    {{
        "trending_keywords": ["keyword1", "keyword2"],
        "category_trends": "short category trend summary"
    }}

    Rules:
    - trending_keywords must contain at least 3 keywords
    - category_trends should be short and concise
    - Must reflect current search trends and popular features
    """