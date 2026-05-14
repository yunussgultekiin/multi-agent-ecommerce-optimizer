def build_competitor_prompt(
    competitor_name: str,
    category: str,
    platform: str,
    product_url: str = "",
    correction_context: str | None = None,
    use_url_context: bool = False,
) -> str:
    if product_url and use_url_context:
        url_context = f"""
Use URL Context for this exact product page:
{product_url}

Your primary job is to extract product evidence from this URL.
Do not use unrelated products.
Do not invent image URLs.
"""
    elif product_url:
        url_context = (
            f'\nThe product page URL is: "{product_url}". '
            "Prioritize information from this exact product page. "
            "Use Google Search grounding to verify details and avoid unrelated products."
        )
    else:
        url_context = ""

    correction_block = ""

    if correction_context:
        correction_block = f"""
PREVIOUS ATTEMPT FAILED:
{correction_context}

Fix the JSON according to the schema and rules below.
"""

    extraction_mode_rules = """
URL Context extraction rules:
- Read the exact product page URL provided above.
- Extract image_urls from product page content when available.
- Prefer URLs from:
  - og:image
  - twitter:image
  - JSON-LD image
  - product media/image fields visible in page content
- Return image_urls=[] if no reliable image URL is visible from URL Context.
""" if use_url_context else """
Search grounding rules:
- Use Google Search grounding for product facts and market context.
- Return image_urls only if direct product image/CDN URLs are visible in grounded results.
- Return image_urls=[] if no reliable grounded image URL is available.
"""

    return f"""{correction_block}
Research the product "{competitor_name}" on platform "{platform}" in the "{category}" category.{url_context}

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
    "product_url": "{product_url}",
    "trending_keywords": ["keyword1", "keyword2", "keyword3"],
    "category_trends": "short category trend summary"
}}

Rules:
- competitor_name: use the exact name provided.
- price: numeric value, null if not visible/reliable.
- features: return at most 8 concrete product features.
- image_urls:
  - Return ONLY real product image URLs visible from the provided URL/context.
  - For Trendyol: prefer cdn.dsmcdn.com URLs.
  - For Hepsiburada: prefer productimages.hepsiburada.net or images.hepsiburada.net URLs.
  - For Amazon TR: prefer m.media-amazon.com or images-na.ssl-images-amazon.com URLs.
  - Do NOT invent image URLs.
  - Do NOT construct CDN paths manually.
  - Do NOT return malformed or partial CDN paths such as "product-.22".
  - If no reliable image URL is available, return image_urls=[].
- rating: between 0.0 and 5.0, null if not visible/reliable.
- review_count: integer, null if not visible/reliable.
- brand: manufacturer or seller brand name, null if unavailable.
- variants: list of product variants with name and price delta from base price. price_delta null if unknown.
- product_url: use the exact product_url provided if given.
- trending_keywords: return 3 to 5 current search/market keywords if available, otherwise [].
- category_trends: max 2 concise sentences; null if unavailable.
- Use null for unavailable numeric/string fields.
- Use [] for unavailable list fields.
- Do not include markdown, comments, or trailing commas.

{extraction_mode_rules}
"""


def build_product_details_prompt(
    competitor_name: str,
    platform: str,
    product_url: str = "",
    correction_context: str | None = None,
) -> str:
    return build_competitor_prompt(
        competitor_name=competitor_name,
        category="",
        platform=platform,
        product_url=product_url,
        correction_context=correction_context,
        use_url_context=bool(product_url),
    )


def build_trends_prompt(
    competitor_name: str,
    category: str,
    platform: str,
    correction_context: str | None = None,
) -> str:
    return build_competitor_prompt(
        competitor_name=competitor_name,
        category=category,
        platform=platform,
        correction_context=correction_context,
        use_url_context=False,
    )