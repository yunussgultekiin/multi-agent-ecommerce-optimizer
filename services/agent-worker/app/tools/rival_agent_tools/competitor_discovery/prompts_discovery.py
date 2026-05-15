from .models_discovery import PLATFORM_SITES, TARGET_COMPETITORS, MIN_COMPETITORS

def build_discovery_prompt(
    platform: str,
    category: str,
    product_title: str,
    brand: str,
    correction_context: str | None = None,
    exclude_names: list[str] | None = None,
) -> str:
    site_filter = PLATFORM_SITES.get(platform, "")
    brand_rule = (
        f'DO NOT include any products from the brand "{brand}".'
        if brand
        else "Exclude the user's own brand if identifiable from the product title."
    )

    correction_block = ""
    if correction_context:
        correction_block = f"PREVIOUS ATTEMPT FAILED:\n{correction_context}\n\nFix the output.\n"

    exclude_block = ""
    if exclude_names:
        exclude_list = "\n".join(f"- {name}" for name in exclude_names)
        exclude_block = f"\nDo NOT include these already-found competitors (they had no retrievable price data):\n{exclude_list}\n"

    return f"""{correction_block}
Search for the top {TARGET_COMPETITORS} most popular and competitive products for "{product_title}" on {platform}.{exclude_block}

Context:
- Platform: {platform} — use search filter: {site_filter}
- Category: "{category}"
- User product: "{product_title}"
- User brand: "{brand or 'unknown'}"

Goal:
Find products that directly compete with the user's product on {platform}.
Prefer well-known brands with significant market presence on {platform}.
Prefer diversity: avoid multiple products from the same brand when possible.

{brand_rule}
Exclude products that are clearly in a different category than "{category}".

Return ONLY valid JSON in this exact format, nothing else:
{{
    "competitors": [
        {{
            "competitor_name": "Brand - Product Model",
            "platform": "{platform}",
            "reason": "Why this directly competes with the user product — must include the competitor's price segment (budget / mid-range / premium)"
        }}
    ]
}}

Rules:
- Return up to {TARGET_COMPETITORS} competitors (minimum {MIN_COMPETITORS}).
- competitor_name must include both brand name and product model.
- reason must be a concise 1-sentence explanation that always ends with the price segment in parentheses, e.g. "(budget)", "(mid-range)", or "(premium)".
- Keep JSON keys and enum labels in English, but write all natural-language explanations in Turkish.
- Do NOT include product URLs, prices, images, or any other fields.
- Do NOT include products from brand "{brand}".
- Avoid duplicate or nearly identical competitor_name values.
- Do not include markdown, comments, or trailing commas.
"""

def build_discovery_correction_context(last_error: str) -> str:
    return (
        f"Validation or JSON parsing failed:\n{last_error}\n\n"
        f"Return between {MIN_COMPETITORS} and {TARGET_COMPETITORS} unique competitors.\n"
        "Each competitor must have competitor_name, platform, and reason.\n"
        "reason must end with the price segment in parentheses: (budget), (mid-range), or (premium).\n"
        "Write reason text in Turkish while keeping JSON keys and enum labels in English.\n"
        "Do NOT include URLs or any extra fields.\n"
        "Do not include duplicate competitor_name values.\n"
        "Do not include the user's own brand."
    )