import json

_JSON_SCHEMA = """{
    "pain_points": ["recurring complaint 1", "recurring complaint 2"],
    "praised_features": ["praised feature 1", "praised feature 2"],
    "competitor_sentiments": [
        {
            "competitor_name": "Brand X",
            "positive": ["fast delivery", "good build quality"],
            "negative": ["poor packaging", "misleading size info"]
        }
    ],
    "marketing_angles": ["angle the seller can use against competitor weaknesses"],
    "risk_warnings": ["pitfall to avoid based on competitor failures"]
}"""

_COMMON_RULES = """
Rules:
- pain_points: at least 1 recurring customer complaint; focus on quality, shipping, packaging,
  material, sizing, durability, performance, ease-of-use, and price/value ratio.
- praised_features: at least 1 feature customers consistently rate positively in this category.
- competitor_sentiments: only include competitors where specific review evidence is found; [] if none.
- marketing_angles: concrete phrases the seller can use to position against competitor weaknesses; [] if none.
- risk_warnings: specific pitfalls to avoid, derived from competitor failures; [] if none.
- Do not invent data. If a competitor has no findable reviews, omit it from competitor_sentiments.
- Do not include markdown, comments, or trailing commas.
"""


def build_sentiment_prompt(
    competitor_names: list[str],
    category: str,
    target_platform: str,
    product_title: str,
    brand: str,
    research_context: list[dict],
    correction_context: str | None = None,
) -> str:
    correction_block = ""
    if correction_context:
        correction_block = f"PREVIOUS ATTEMPT FAILED:\n{correction_context}\n\nFix the output.\n"

    competitors_block = "\n".join(f"- {name}" for name in competitor_names)

    research_block = ""
    if research_context:
        research_block = f"""
COMPETITOR RESEARCH DATA (features, ratings, trends):
{json.dumps(research_context, ensure_ascii=False)}
"""

    return f"""{correction_block}
Search for real customer reviews and complaints for the following competitor products
in the "{category}" category.

USER PRODUCT CONTEXT:
- Title: {product_title or "unknown"}
- Brand: {brand or "unknown"}
- Category: {category}
- Platform: {target_platform}

COMPETITORS TO ANALYZE:
{competitors_block}
{research_block}
SOURCES TO SEARCH (in order of priority):
1. sikayetvar.com — search for each competitor brand name to find chronic complaint threads.
2. eksisozluk.com — search for competitor brand/product entries to find user opinions and experiences.
3. {target_platform} — product review sections and Q&A for rating-based feedback.

TASK:
1. Search all three sources above for each competitor.
2. Identify the most frequently reported customer pain points across these products.
3. Identify features that customers consistently praise in this category.
4. For each competitor where you find concrete evidence, record their positive and negative points.
5. Derive marketing angles the user can use by targeting competitor weaknesses.
6. Identify risk warnings (e.g. a competitor's chronic complaint the user must not replicate).

Focus especially on chronic issues: quality defects, shipping delays, misleading size/specs,
poor packaging, material failures, durability problems, performance gaps, ease-of-use issues,
and poor price/value perception.

RESPOND ONLY in this JSON format:
{_JSON_SCHEMA}
{_COMMON_RULES}
"""


def build_fallback_sentiment_prompt(
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
No specific competitor names are available. Search sikayetvar.com and eksisozluk.com
for general complaints and opinions about the "{category}" category on {target_platform}.

USER PRODUCT CONTEXT:
- Title: {product_title or "unknown"}
- Brand: {brand or "unknown"}
- Category: {category}
- Platform: {target_platform}

SOURCES TO SEARCH:
1. sikayetvar.com — search for "{category}" or "{target_platform} {category}" to find recurring complaints.
2. eksisozluk.com — search for "{category}" entries to find user opinions and experiences.

TASK:
1. Based on what you find on sikayetvar.com and eksisozluk.com, identify the most common pain points in this category.
2. Identify features customers in this category typically praise.
3. Leave competitor_sentiments as an empty list since no specific competitors are provided.
4. Suggest marketing angles based on common category weaknesses.
5. Warn about risks the seller should avoid based on category-level patterns.

Focus on: quality, shipping, packaging, material, sizing, durability, performance,
ease-of-use, and price/value issues typical to "{category}" on {target_platform}.

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
- pain_points must have at least 1 item.
- praised_features must have at least 1 item.
- competitor_sentiments, marketing_angles, risk_warnings may be empty lists but must be present.
- All string values must be non-empty.

ORIGINAL TASK:
{original_prompt}
"""
