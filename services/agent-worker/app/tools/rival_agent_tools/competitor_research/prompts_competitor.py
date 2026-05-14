def build_product_details_prompt(
    competitor_name: str,
    platform: str,
    product_url: str = "",
    correction_context: str | None = None,
) -> str:
    url_context = ""

    if product_url:
        url_context = (
            f'\nThe product page URL is: "{product_url}". '
            "Prioritize information from this exact product page when possible. "
            "Use search grounding to verify details and avoid unrelated products."
        )

    correction_block = ""

    if correction_context:
        correction_block = f"""
PREVIOUS ATTEMPT FAILED:
{correction_context}

Fix the JSON according to the schema and rules below.
"""

    return f"""{correction_block}
Research the product "{competitor_name}" on platform "{platform}" using Google Search grounding.{url_context}

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
- competitor_name: use the exact competitor/product name provided.
- price: numeric value, null if unavailable.
- features: concrete product features only.
- image_urls: real product image URLs only, http or https, no placeholder URLs.
- image_urls should contain direct product image URLs when available.
- rating: between 0.0 and 5.0, null if unavailable.
- review_count: integer, null if unavailable.
- brand: manufacturer or seller brand name, null if unavailable.
- variants: list of product variants with name and price difference from base price.
- variants.price_delta: numeric value, null if unknown.
- product_url: exact product page URL if known, otherwise null.
- Do not include markdown.
- Do not include comments.
- Do not include trailing commas.
"""

def build_trends_prompt(
    competitor_name: str,
    category: str,
    platform: str,
    correction_context: str | None = None,
) -> str:
    correction_block = ""

    if correction_context:
        correction_block = f"""
PREVIOUS ATTEMPT FAILED:
{correction_context}

Fix the JSON according to the schema and rules below.
"""

    return f"""{correction_block}
Research current market trends in the "{category}" category related to the product "{competitor_name}" on platform "{platform}" using Google Search grounding.

Return ONLY valid JSON, nothing else:
{{
    "trending_keywords": ["keyword1", "keyword2", "keyword3"],
    "category_trends": "short category trend summary"
}}

Rules:
- trending_keywords: at least 3 current keywords reflecting search trends, popular product attributes, buying intent, or marketplace demand.
- category_trends: concise summary of popular features, visual trends, pricing direction, customer preferences, and market direction.
- Do not invent exact search volumes.
- Do not include markdown.
- Do not include comments.
- Do not include trailing commas.
"""