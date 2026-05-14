PLATFORM_SITES = {
    "trendyol": "site:trendyol.com",
    "amazon": "site:amazon.com.tr",
    "hepsiburada": "site:hepsiburada.com",
}

_TRENDYOL_URL_RULES = """
Trendyol product URL rules:
- URL must contain "-p-" or "/p-" followed by a numeric product ID of at least 6 digits.
- Do NOT use p-123456789 or any obvious placeholder numeric ID.
- Do NOT reuse the same product ID for different competitors.
- Do NOT link to search pages, category pages, brand pages, campaign pages, or homepage URLs.
"""

_URL_AUTHENTICITY_RULES = """
URL authenticity rules:
- Prefer real product detail page URLs found through Google Search grounding.
- Do NOT invent placeholder product URLs.
- Do NOT fabricate obviously fake Trendyol product IDs such as p-123456789, p-112233445, or p-192837462.
- Do NOT manually construct random slugs from product names.
- If a real product URL is uncertain, choose another competitor.
- The application will prefer grounding metadata URLs when available.
- If grounding metadata URLs are unavailable, the application will use product_url as fallback after deterministic validation.
"""


def build_discovery_prompt(
    platform: str,
    category: str,
    product_title: str,
    brand: str,
    correction_context: str | None = None,
) -> str:
    site_filter = PLATFORM_SITES.get(platform, "")

    correction_block = ""

    if correction_context:
        correction_block = f"""
PREVIOUS ATTEMPT FAILED:
{correction_context}

Fix the output according to the schema and rules below.
"""

    brand_rule = (
        f'Do NOT include any products from the brand "{brand}".'
        if brand
        else "Avoid including the user's own brand if it is identifiable from the product title."
    )

    platform_url_rules = _TRENDYOL_URL_RULES if platform == "trendyol" else ""

    return f"""{correction_block}
Search for real competitor product detail pages on {platform} using Google Search grounding.

Search context:
- Platform: {platform}
- Site filter: {site_filter}
- Category: "{category}"
- User product title: "{product_title}"
- User brand: "{brand or 'unknown'}"

Goal:
Find 3 to 5 competing products in the same category and similar to the user product.
Prefer competitors from different brands when possible.

Important exclusion:
{brand_rule}

{_URL_AUTHENTICITY_RULES}
{platform_url_rules}

Return ONLY valid JSON in this exact format, nothing else:
{{
    "competitors": [
        {{
            "competitor_name": "Brand Name - Product Name",
            "product_url": "https://real-product-detail-url",
            "source_url_index": 0,
            "platform": "{platform}"
        }}
    ]
}}

Rules:
- Use the platform-specific search filter: {site_filter}
- product_url is REQUIRED.
- product_url must be a product detail page, not a search/category/homepage URL.
- source_url_index is optional. Use it only if you can associate the competitor with a grounding source index.
- source_url_index must be a non-negative integer or null.
- competitor_name must include both brand and product name when available.
- competitors must be relevant to the category "{category}".
- competitors must be similar to "{product_title}".
- Return 3 to 5 competitors.
- Return 5 competitors if enough likely real product detail pages exist.
- Exclude duplicate product_url values.
- Exclude duplicate or nearly identical competitor_name values.
- Exclude products from the user brand "{brand}".
- Do not include markdown.
- Do not include comments.
- Do not include trailing commas.
"""


def build_discovery_correction_context(last_error: str, min_competitors: int, max_competitors: int) -> str:
    return (
        f"Validation or JSON parsing failed with this error:\n"
        f"{last_error}\n\n"
        "Fix all issues and return ONLY valid JSON matching the requested schema.\n"
        f"Return between {min_competitors} and {max_competitors} unique competitors.\n"
        "Each competitor must have competitor_name, product_url, source_url_index, and platform.\n\n"
        "CRITICAL rules:\n"
        "- product_url is required.\n"
        "- product_url must be a product detail page.\n"
        "- Do NOT use category/search/homepage/campaign URLs.\n"
        "- Do NOT use placeholder product IDs such as p-123456789, p-112233445, or p-192837462.\n"
        "- Do NOT reuse the same product ID for different competitors.\n"
        "- For Trendyol: URL should contain '-p-' or '/p-' followed by a numeric ID of 6+ digits.\n"
        "- source_url_index can be null if grounding source index is unavailable.\n"
        "- Do not include duplicate products.\n"
        "- Do not include the user's own brand."
    )