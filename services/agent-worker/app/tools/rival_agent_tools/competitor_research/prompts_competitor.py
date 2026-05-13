def build_product_details_prompt(competitor_name: str, product_url: str = "") -> str:
    url_context = f" The product page is at: {product_url}" if product_url else ""
    return f"""Research the product "{competitor_name}".{url_context}
Return ONLY valid JSON, nothing else:
{{
    "competitor_name": "{competitor_name}",
    "price": 0.0,
    "features": ["feature1", "feature2"],
    "image_urls": ["https://..."],
    "rating": 0.0,
    "review_count": 0,
    "brand": "brand name",
    "variants": [
        {{"name": "Color or Size variant name", "price_delta": 0.0}}
    ],
    "product_url": "{product_url}"
}}

Rules:
- price: numeric value, null if unavailable
- rating: between 0.0 and 5.0, null if unavailable
- image_urls: real product image URLs only
- review_count: integer, null if unavailable
- brand: the manufacturer or seller brand name
- variants: list of product variants with name and price difference from base price (null price_delta if unknown)
- product_url: the exact product page URL
"""

def build_trends_prompt(competitor_name: str, category: str) -> str:
    return f"""Research current market trends in the "{category}" category for the product "{competitor_name}".
Return ONLY valid JSON, nothing else:
{{
    "trending_keywords": ["keyword1", "keyword2", "keyword3"],
    "category_trends": "short category trend summary"
}}

Rules:
- trending_keywords: at least 3 keywords reflecting current search trends
- category_trends: concise summary of popular features and market direction
"""
