def build_competitor_prompt(
    competitor_name: str,
    category: str,
    platform: str,
    correction_context: str | None = None,
) -> str:
    correction_block = ""
    if correction_context:
        correction_block = (
            f"PREVIOUS ATTEMPT FAILED:\n{correction_context}\n\nFix the JSON.\n"
        )

    return f"""{correction_block}
Research the product "{competitor_name}" on platform "{platform}" in the "{category}" category.
Use Google Search grounding to find accurate and up-to-date product information.

Return ONLY valid JSON, nothing else:
{{
    "competitor_name": "{competitor_name}",
    "estimated_price": 0.0,
    "currency": "TRY",
    "features": ["feature1", "feature2"],
    "rating": 0.0,
    "review_count": 0,
    "brand": "brand name",
    "variants": [
        {{"name": "Color or Size variant name", "price_delta": 0.0}}
    ],
    "trending_keywords": ["keyword1", "keyword2", "keyword3"],
    "category_trends": "short category trend summary"
}}

Rules:
- competitor_name: use the exact name provided.
- estimated_price: current listed price as a number in TRY; null if not found.
- currency: always "TRY" for Turkish platforms (trendyol, hepsiburada, amazon.com.tr).
- features: up to 8 concrete product features. Include material, power/wattage, capacity, dimensions, use case, package contents, and connectivity where applicable.
- rating: between 0.0 and 5.0; null if not found.
- review_count: integer; null if not found.
- brand: manufacturer or seller brand; null if unavailable.
- variants: list of product variants with name and price_delta from base price; price_delta null if unknown.
- trending_keywords: 3 to 5 current market/search keywords for this product; [] if unavailable.
- category_trends: max 2 concise sentences about category trends; null if unavailable.
- Use null for unavailable numeric/string fields.
- Use [] for unavailable list fields.
- Do not include URLs, image links, or any fields not listed above.
- Do not include markdown, comments, or trailing commas.
"""
