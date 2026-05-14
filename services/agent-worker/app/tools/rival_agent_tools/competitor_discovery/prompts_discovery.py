PLATFORM_SITES = {
    "trendyol": "site:trendyol.com",
    "amazon": "site:amazon.com.tr",
    "hepsiburada": "site:hepsiburada.com",
}

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

    return f"""{correction_block}
Search for competitor product detail pages on {platform} using Google Search grounding.

Search context:
- Platform: {platform}
- Site filter: {site_filter}
- Category: "{category}"
- User product title: "{product_title}"
- User brand: "{brand or 'unknown'}"

Goal:
Find up to 5 competing products in the same category and similar to the user product.
Return exactly 5 competitors if enough valid products exist.
If fewer valid products exist, return at least 3 competitors.
Prefer competitors from different brands when possible.

Important exclusion:
{brand_rule}

Return ONLY valid JSON in this exact format, nothing else:
{{
    "competitors": [
        {{
            "competitor_name": "Brand Name - Product Name",
            "product_url": "https://...",
            "platform": "{platform}"
        }}
    ]
}}

Rules:
- Use the platform-specific search filter: {site_filter}
- product_url must be a real product detail page URL on {platform}
- product_url must not be a homepage, category page, search result page, cart page, or campaign page
- competitor_name must include both brand and product name when available
- competitors must be relevant to the category "{category}"
- competitors must be similar to "{product_title}"
- Return 3 to 5 competitors
- Return 5 competitors if enough valid results exist
- Exclude duplicate product_url values
- Exclude duplicate or nearly identical competitor_name values
- Exclude products from the user brand "{brand}"
- Do not include markdown
- Do not include comments
- Do not include trailing commas
"""