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
- marketing_angles: derive from TWO sources simultaneously —
    (1) competitor weaknesses: position the user product as solving what competitors fail at;
    (2) praised_features: if the user product shares a praised feature, write an angle that claims or reinforces that strength.
  Each angle must be a concrete phrase the seller can use in listings or ads. [] if neither source yields usable material.
- risk_warnings: specific pitfalls to avoid, derived from competitor failures; [] if none.
- Do not invent data. If a competitor has no findable reviews, omit it from competitor_sentiments.
- Keep JSON keys and enum labels in English, but write all natural-language output strings in Turkish.
- Do not include markdown, comments, or trailing commas.

PRODUCT-SPECIFIC DEFECT FILTER (apply when using brand/company-level findings):
  When a complaint originates from a different product type than the one being analyzed
  (e.g. a thermos review when analyzing a cutlery set), apply this filter:
  - DISCARD the finding if it describes a physical or structural defect that is
    intrinsic to that other product type and cannot logically apply to the analyzed
    product (e.g. "thermos lid breaks", "thermos leaks water", "bag strap tears").
  - KEEP the finding if it describes an operational or fulfilment failure that can
    affect any product from that brand regardless of category (e.g. late delivery,
    order cancellation, return/exchange request not fulfilled, missing item in shipment,
    poor customer service response).
  Rationale: a brand's logistics and after-sales behaviour is consistent across its
  catalogue; a thermos lid cracking has no relevance to a cutlery set.

NEGATIVE EVIDENCE HIERARCHY (apply for every competitor):
  Step 1 — Search for product-specific negative reviews on all three sources.
  Step 2 — Count distinct product-specific negative findings.
           If count >= 2: use only those. Skip Step 3.
           If count < 2:  proceed to Step 3.
  Step 3 — Search the same sources for brand/company-level complaints
           (e.g. general shipping issues, customer service failures, return policy problems).
  Step 4 — CONFLICT FILTER: before adding any company-level negative, check whether
           it contradicts a positive already recorded at the product level.
           Rule: if the product has a product-level positive on topic X,
           discard any company-level negative on the same topic X.
           Example: product reviews praise fast delivery → discard company-level
           "slow shipping" complaints, even if widespread.
  Step 5 — Apply the PRODUCT-SPECIFIC DEFECT FILTER to all remaining company-level findings.
  Step 6 — Add only the company-level negatives that survive both filters.
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
        correction_block = (
            f"PREVIOUS ATTEMPT FAILED:\n{correction_context}\n\nFix the output.\n"
        )

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
1. Search all three sources for each competitor — product-specific pages first.
2. For each competitor, count distinct product-specific negative findings.
   - If >= 2 product-specific negatives found: use them directly. Do NOT search company level.
   - If < 2 product-specific negatives found: additionally search brand/company-level complaints
     on the same sources, then apply the CONFLICT FILTER and the PRODUCT-SPECIFIC DEFECT FILTER
     from the rules below before including them.
3. Identify the most frequently reported customer pain points across these products.
4. Identify features that customers consistently praise in this category.
5. For each competitor where you find concrete evidence, record their positive and negative points.
6. Derive marketing_angles using BOTH of these sources:
   - Competitor weaknesses: write angles that position the user product as solving what competitors fail at.
   - praised_features: if the user product can credibly claim a praised feature, write an angle that asserts that strength directly.
7. Identify risk warnings (e.g. a competitor's chronic complaint the user must not replicate).

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
        correction_block = (
            f"PREVIOUS ATTEMPT FAILED:\n{correction_context}\n\nFix the output.\n"
        )

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
1. Search sikayetvar.com and eksisozluk.com for product-specific complaints in this category.
2. Count distinct product-specific negative findings.
   - If >= 2 found: use them directly.
   - If < 2 found: broaden search to brand/seller-level complaints in this category,
     then apply the CONFLICT FILTER and the PRODUCT-SPECIFIC DEFECT FILTER from the rules
     below before including any finding.
3. Identify the most common pain points based on what you find.
4. Identify features customers in this category typically praise.
5. Leave competitor_sentiments as an empty list since no specific competitors are provided.
6. Derive marketing_angles using BOTH of these sources:
   - Category-level weaknesses: write angles that position the user product as solving what sellers in this category commonly fail at.
   - praised_features: write angles that assert the user product can credibly deliver what buyers already value in this category.
7. Warn about risks the seller should avoid based on category-level patterns.

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
- marketing_angles must be derived from both competitor weaknesses AND praised_features — not only one source.
- competitor_sentiments, marketing_angles, risk_warnings may be empty lists but must be present.
- All string values must be non-empty.
- Keep JSON keys in English, but write all value texts in Turkish.

ORIGINAL TASK:
{original_prompt}
"""
