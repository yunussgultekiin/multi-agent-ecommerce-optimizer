from app.tools.json_prompt_rules import JSON_SELF_CORRECTION_SYNTAX, STRICT_JSON_SYNTAX_RULES
from .models_discovery import MIN_COMPETITORS, PLATFORM_SITES, TARGET_COMPETITORS

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
        correction_block = (
            f"PREVIOUS ATTEMPT FAILED:\n{correction_context}\n\nFix the output.\n"
        )

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
- User brand: "{brand or "unknown"}"

Goal:
Find products that directly compete with the user's product on {platform}.
Prefer well-known brands with significant market presence on {platform}.
Prefer diversity: avoid multiple products from the same brand when possible.

SEGMENT ANALYSIS — Read user product carefully and extract:
- Product type (e.g., termos, kupa, kulaklık, çanta)
- Measurable quantity (volume, weight, capacity, count, length)
- Use case (daily, gift, professional, outdoor, office, home)
- Target audience (children, adults, athletes, general)
- Personalization flags (kişiselleştirilebilir, custom, özel baskı, isim yazma)
- Price segment inferred from title/context (budget / mid-range / premium)

Volume / size matching (CRITICAL):
- If the user product title contains a measurable size or quantity
  (volume, weight, capacity, count, length, etc.), extract that value.
- Only include competitors whose size/quantity is within 30% of the
  user product's value.
  Example: if user product is "X units", acceptable range is 0.7X – 1.3X.
- Competitors clearly outside this range should receive low similarity_score (0-30).
- If no measurable size/quantity is found in the title,
  focus on the same product subcategory and skip this filter.

Use-case and segment matching:
- If user product is a gift item (hediye), competitors without gift positioning get lower score.
- If user product is personalized (kişiselleştirilmiş), non-personalized competitors get lower score.
- If user product is professional/premium, budget alternatives get lower score.
- Competitors with completely different use cases (e.g., industrial vs. consumer) get score 0-20.

{brand_rule}
Exclude products that are clearly in a different category than "{category}".

SIMILARITY SCORING for each competitor:
- similarity_score: integer 0-100
  - Product type exact match: +30
  - Same subcategory: +20
  - Size/volume within 30%: +15 (or skip if not applicable)
  - Same use case / target audience: +15
  - Same personalization level: +10
  - Price band similar (within 50%): +10
  - Deductions: different use case -20, different product type -40, clearly off-segment -60
- similarity_label: "Yüksek" (70-100), "Orta" (40-69), "Düşük" (0-39)
- similarity_reason: short Turkish sentence explaining the score (1 sentence, mention key match/mismatch)

Return ONLY valid JSON in this exact format, nothing else:
{{
    "competitors": [
        {{
            "competitor_name": "Brand - Product Model",
            "platform": "{platform}",
            "reason": "Why this directly competes with the user product — must include the competitor's price segment (budget / mid-range / premium)",
            "similarity_score": 75,
            "similarity_label": "Yüksek",
            "similarity_reason": "Aynı ürün tipinde, benzer hacim ve kullanım amacıyla doğrudan rakip."
        }}
    ]
}}

Rules:
- Return up to {TARGET_COMPETITORS} competitors (minimum {MIN_COMPETITORS}).
- competitor_name must include both brand name and product model.
- reason must be a concise 1-sentence explanation that always ends with the price segment in parentheses, e.g. "(budget)", "(mid-range)", or "(premium)".
- similarity_score: integer 0–100, required.
- similarity_label: exactly "Yüksek", "Orta", or "Düşük", required.
- similarity_reason: 1 Turkish sentence, required.
- Keep JSON keys and enum labels in English, but write all natural-language explanations in Turkish.
- Do NOT include product URLs, prices, images, or any other fields.
- Do NOT include products from brand "{brand}".
- Avoid duplicate or nearly identical competitor_name values.
- Do not include markdown, comments, or trailing commas.
{STRICT_JSON_SYNTAX_RULES}
"""

def build_discovery_correction_context(last_error: str) -> str:
    return (
        f"Validation or JSON parsing failed:\n{last_error}\n\n"
        f"Return between {MIN_COMPETITORS} and {TARGET_COMPETITORS} unique competitors.\n"
        "Each competitor must have: competitor_name, platform, reason, similarity_score, similarity_label, similarity_reason.\n"
        "reason must end with the price segment in parentheses: (budget), (mid-range), or (premium).\n"
        "similarity_score: integer 0–100.\n"
        "similarity_label: exactly 'Yüksek', 'Orta', or 'Düşük'.\n"
        "similarity_reason: 1 Turkish sentence.\n"
        "Write all natural-language texts in Turkish while keeping JSON keys and enum labels in English.\n"
        "Do NOT include URLs or any extra fields.\n"
        "Do not include duplicate competitor_name values.\n"
        "Do not include the user's own brand."
        f"{JSON_SELF_CORRECTION_SYNTAX}"
    )
