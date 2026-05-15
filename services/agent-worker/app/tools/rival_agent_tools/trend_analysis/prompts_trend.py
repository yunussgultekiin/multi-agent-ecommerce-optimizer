_JSON_SCHEMA = """{
    "trending_features": ["feature1", "feature2"],
    "demand_signals": ["signal1", "signal2"],
    "platform_trends": ["platform-specific trend1", "platform-specific trend2"],
    "category_trend_summary": "2-3 sentence summary of the current category trend landscape"
}"""

_COMMON_RULES = """
Rules:
- trending_features: at least 1 feature or keyword currently rising in search/demand in this category.
- demand_signals: observable buyer behavior or preference shifts (e.g. "increasing preference for eco-friendly materials"); [] if none found.
- platform_trends: platform-specific listing or search behavior patterns on the target platform (e.g. bestseller badge patterns, bundle trends); [] if none found.
- category_trend_summary: required, 2-3 sentences summarizing the current trend direction.
- All strings must be non-empty.
- Keep JSON keys in English, but write all natural-language values in Turkish.
- Do not include markdown, comments, or trailing commas.
"""

_PLATFORM_BESTSELLER_PAGES = {
    "trendyol": "trendyol.com/en-cok-satanlar and trendyol.com category trending pages",
    "hepsiburada": "hepsiburada.com category bestseller and 'cok satanlar' pages",
    "amazon": "amazon.com.tr/bestsellers for the relevant category",
}

def _get_platform_source(target_platform: str) -> str:
    return _PLATFORM_BESTSELLER_PAGES.get(
        target_platform.lower(),
        f"{target_platform} bestseller and trending pages",
    )

def build_trend_prompt(
    category: str,
    target_platform: str,
    product_title: str,
    brand: str,
    correction_context: str | None = None,
) -> str:
    correction_block = ""
    if correction_context:
        correction_block = f"PREVIOUS ATTEMPT FAILED:\n{correction_context}\n\nFix the output.\n"

    platform_source = _get_platform_source(target_platform)

    return f"""{correction_block}
Search for the latest trends in the "{category}" category on {target_platform}.

USER PRODUCT CONTEXT:
- Title: {product_title or "unknown"}
- Brand: {brand or "unknown"}
- Category: {category}
- Platform: {target_platform}

SOURCES TO SEARCH (in order of priority):
1. Google Trends TR (trends.google.com.tr) — search "{category}" to find rising search terms and keywords in Turkey.
2. {target_platform} bestsellers — {platform_source}.

TASK:
1. From Google Trends TR: identify rising search keywords and features for "{category}" in Turkey.
2. From {target_platform} bestseller and trending pages: identify which product attributes, features, or sub-categories are climbing in ranking.
3. Identify demand signals: buyer behavior shifts, emerging preferences, seasonal patterns, or growing sub-niches on {target_platform}.
4. Identify {target_platform}-specific trends: bundle/set popularity, pricing tier movements, listing badge patterns.
5. Summarize the overall trend direction for "{category}" on {target_platform} in 2-3 sentences.

Focus on actionable, specific trends — not generic observations.
Prefer data-backed signals (search volume rise, bestseller movement, review volume increase).

RESPOND ONLY in this JSON format:
{_JSON_SCHEMA}
{_COMMON_RULES}
"""

def build_fallback_trend_prompt(
    category: str,
    target_platform: str,
    product_title: str,
    brand: str,
    correction_context: str | None = None,
) -> str:
    correction_block = ""
    if correction_context:
        correction_block = f"PREVIOUS ATTEMPT FAILED:\n{correction_context}\n\nFix the output.\n"

    return f"""{correction_block}
Real-time trend data is unavailable. Use your knowledge of the "{category}" category
and {target_platform} to infer trend patterns.

USER PRODUCT CONTEXT:
- Title: {product_title or "unknown"}
- Brand: {brand or "unknown"}
- Category: {category}
- Platform: {target_platform}

TASK:
1. List features or attributes that are typically trending or in high demand in "{category}" on {target_platform}.
2. Describe common demand signals for this category (buyer behavior, seasonal patterns, price sensitivity).
3. Describe any known bestseller or listing behavior patterns for "{category}" on {target_platform}.
4. Summarize the general trend direction for this category in 2-3 sentences.

RESPOND ONLY in this JSON format:
{_JSON_SCHEMA}
{_COMMON_RULES}
"""


def build_self_correction_prompt(original_prompt: str, last_error: str) -> str:
    return f"""
THE PREVIOUS ATTEMPT FAILED. Pydantic validation error:
{last_error}

Fix ALL errors and return ONLY valid JSON.
Key rules:
- trending_features must have at least 1 item.
- category_trend_summary must be a non-empty string.
- demand_signals and platform_trends may be empty lists but must be present.
- Keep JSON keys in English, but write all value texts in Turkish.

ORIGINAL TASK:
{original_prompt}
"""
