from app.tools.json_prompt_rules import STRICT_JSON_SYNTAX_RULES

PLATFORM_TITLE_LIMITS: dict[str, int] = {
    "trendyol": 100,
    "amazon": 200,
    "hepsiburada": 120,
}

PLATFORM_TITLE_RECOMMENDED: dict[str, int] = {
    "amazon": 80,
}

TONE_DIRECTIVES: dict[str, str] = {
    "casual": (
        "Warm, friendly, and relatable. Use 'sen' (second person singular in Turkish). "
        "Focus on lifestyle integration and emotional connection. Short sentences, active voice. "
        "Suitable for Z-gen and millennial audiences on Trendyol."
    ),
    "professional": (
        "Professional, authoritative, and data-driven. Avoid unverified superlatives. "
        "Use specific numbers and measurable claims ('3-year warranty', '10,000 mAh'). "
        "Suitable for informed, comparison-shopping buyers."
    ),
    "premium": (
        "Aspirational, exclusive, and high-end. Emphasize craftsmanship, superior quality, "
        "and brand prestige. Position as the luxury or top-tier choice. Confident, polished tone."
    ),
}

def get_description_directive(platform: str) -> str:
    if platform == "trendyol":
        return (
            "meta_description: 150-500 words. "
            "First 2 sentences must be keyword-dense and state the main benefit. "
            "Use bullet list for features. End with a usage scenario. Warm, engaging tone."
        )
    if platform == "amazon":
        return (
            "meta_description: Max 2000 characters total. Lead paragraph covers top 3 benefits. "
            "In addition, populate platform_specific_tips with exactly 5 bullet points "
            "(each max 255 chars, format: [FEATURE KEYWORD]: Benefit explanation in Turkish). "
            "Professional, factual tone. No unverified superlatives."
        )
    if platform == "hepsiburada":
        return (
            "meta_description: Minimum 200 words. "
            "Structure: technical summary paragraph → feature bullet list → usage advantages → warranty/guarantee info. "
            "Professional, informative tone. Include technical specs (capacity, dimensions, certifications)."
        )
    return (
        "meta_description: Keyword-rich, benefit-focused product description. "
        "First sentence states the main use case and key feature."
    )

def build_seo_prompt(
    user_product: dict,
    rival_json: dict,
    platform: str,
    rag_chunks: list[str],
    tone_key: str,
) -> str:
    sentiment = rival_json.get("sentiment_result", {})
    trend = rival_json.get("trend_result", {})
    gap = rival_json.get("gap_result", {})
    pricing = rival_json.get("pricing_result", {})

    praised_features: list = sentiment.get("praised_features", [])
    pain_points: list = sentiment.get("pain_points", [])
    marketing_angles: list = sentiment.get("marketing_angles", [])
    trending_features: list = trend.get("trending_features", [])
    demand_signals: list = trend.get("demand_signals", [])
    gap_opportunities: list = gap.get("gap_opportunities", [])
    trend_based_opportunities: list = gap.get("trend_based_opportunities", [])
    positioning: str = pricing.get("positioning", "")

    competitor_keywords: list[str] = []
    competitor_names: list[str] = []
    competitor_brands: list[str] = []
    for r in rival_json.get("competitor_research_results", [])[:5]:
        data = r.get("data", {}) if isinstance(r, dict) else {}
        name = data.get("competitor_name", "")
        brand = data.get("brand", "")
        if name:
            competitor_names.append(name)
        if brand and brand not in competitor_brands:
            competitor_brands.append(brand)
        competitor_keywords.extend(data.get("trending_keywords", [])[:5])

    all_keywords = list(dict.fromkeys(competitor_keywords + trending_features))
    strengthen_args = (
        praised_features[:5]
        if praised_features
        else user_product.get("features", [])[:5]
    )

    user_features: list = user_product.get("features", [])
    variants: list = user_product.get("variants", [])
    variant_names = [
        v.get("name", "") for v in variants if isinstance(v, dict) and v.get("name")
    ]
    brand: str = user_product.get("brand", "")
    category: str = user_product.get("category", "")

    title_limit = PLATFORM_TITLE_LIMITS.get(platform, 200)
    title_recommended = PLATFORM_TITLE_RECOMMENDED.get(platform, title_limit)
    description_directive = get_description_directive(platform)

    rag_block = (
        "\n".join(f"  - {chunk}" for chunk in rag_chunks)
        if rag_chunks
        else "  (No platform-specific SEO rules loaded — apply general best practices)"
    )

    tone_desc = TONE_DIRECTIVES.get(tone_key, TONE_DIRECTIVES["professional"])
    tone_override_note = (
        "(USER-DEFINED TONE OVERRIDE — apply this tone exactly)"
        if user_product.get("seo_tone") in TONE_DIRECTIVES
        else f"(Platform default tone for {platform})"
    )

    variant_instruction = (
        f"Generate one variant_seo entry per variant: {variant_names}"
        if variant_names
        else "Variants list is empty — return variant_seo as an empty array []"
    )

    title_limit_note = (
        f"max {title_limit} chars (recommended under {title_recommended})"
        if title_recommended < title_limit
        else f"max {title_limit} chars"
    )

    return f"""You are an expert e-commerce SEO specialist optimizing a product listing for {platform}.
Output language: TURKISH — Every output field value must be written in Turkish.

=== PLATFORM SEO RULES (Follow strictly when writing title, description, and keywords) ===
{rag_block}

=== USER PRODUCT ===
Title: {user_product.get("title", "")}
Brand: {brand}
Category: {category}
Features: {user_features[:10]}
Variants: {variant_names}
Price: {user_product.get("price")}

=== WRITING TONE ===
Tone: {tone_key} — {tone_desc}
{tone_override_note}

=== COMPETITOR INTELLIGENCE ===
Competitor names: {competitor_names[:5]}
Competitor brands: {competitor_brands[:3]}
Trending keywords (competitor data + trend analysis): {all_keywords[:15]}
Competitor pain points (use to differentiate user product): {pain_points[:5]}
Marketing angles (inject directly into description context): {marketing_angles[:5]}

=== MARKET DATA ===
Demand signals (use as usage scenarios in description): {demand_signals[:5]}
Gap opportunities (market niches, check Safe Collision before using): {gap_opportunities[:6]}
Trend-based opportunities: {trend_based_opportunities[:4]}
Market positioning: {positioning or "not specified"}

=== STRENGTHENING ARGUMENTS ===
{"Praised features from customer reviews (use in title/description as product strengths): " + str(strengthen_args) if praised_features else "Fallback — praised_features empty, use product features instead: " + str(strengthen_args)}

=== TITLE RULES FOR {platform.upper()} ===
- Character limit: STRICTLY {title_limit_note} — do not exceed
- Format: Brand + Category/Product Type + Main Feature + Variant (if applicable)
- Must include brand "{brand}" and category keyword "{category}"
- Title Case: capitalize first letter of each major word
- No filler words: no "harika", "mükemmel", "en iyi", "süper", "kaliteli", "uygun"
- First 40-50 characters must contain the highest-volume keywords

=== DESCRIPTION RULES FOR {platform.upper()} ===
{description_directive}

=== SAFE COLLISION RULE — CRITICAL ===
User product confirmed features: {user_features[:10]}
Gap opportunities from market: {gap_opportunities[:6]}
RULE: Only put features in title and meta_description that are ACTUALLY PRESENT in the user product confirmed features.
Gap opportunities NOT in the confirmed features must go ONLY to product_development_ideas[], never in title or description.

=== KEYWORD GAPS RULES ===
Source from: competitor trending keywords {all_keywords[:10]}, gap opportunities, and RAG platform rules.
- Find 5-10 missing keyword opportunities the user product is not currently targeting
- Each keyword: 1-4 words, Turkish longtail combination
- Order by estimated search volume potential (highest first)
- Write all keywords in Turkish

=== VARIANT SEO ===
{variant_instruction}

Respond ONLY with a raw JSON object. No markdown, no explanation, no ```json fences. Just the JSON:
{{
  "title_suggestion": "Turkish title, {title_limit_note}",
  "meta_description": "Turkish description per platform rules above",
  "content_recommendations": ["Türkçe aksiyon önerisi 1", "Türkçe aksiyon önerisi 2", "Türkçe aksiyon önerisi 3"],
  "keyword_gaps": ["türkçe longtail keyword 1", "türkçe longtail keyword 2", "türkçe longtail keyword 3", "türkçe longtail keyword 4", "türkçe longtail keyword 5"],
  "competitor_comparison_summary": "Türkçe rekabetçi konumlandırma özeti (2-3 cümle)",
  "platform_specific_tips": ["Türkçe platform SEO ipucu 1", "Türkçe platform SEO ipucu 2", "Türkçe platform SEO ipucu 3"],
  "variant_seo": [{{"variant_name": "...", "title_suggestion": "...", "keyword_additions": ["..."]}}],
  "product_development_ideas": ["Türkçe ürün geliştirme fikri (gap_opportunities'ten, kullanıcı ürününde olmayan)"]
}}

Field rules:
- title_suggestion: Turkish, {title_limit_note}, include brand and category, no filler words
- meta_description: Turkish, follow platform description rules above
- content_recommendations: 3-5 Turkish actionable items from demand_signals and strengthen_args
- keyword_gaps: 5-10 Turkish longtail keywords (1-4 words each), highest search volume first
- competitor_comparison_summary: 2-3 Turkish sentences on competitive positioning
- platform_specific_tips: 3-5 Turkish SEO tips for {platform}
- variant_seo: one entry per variant OR empty []
- product_development_ideas: Turkish ideas for features in gap_opportunities that user product does NOT have
{STRICT_JSON_SYNTAX_RULES}"""
