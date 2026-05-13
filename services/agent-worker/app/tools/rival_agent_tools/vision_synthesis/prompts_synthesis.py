import json

def build_synthesis_prompt(
    user_analyses: list[dict],
    competitor_analyses: list[dict],
    variants: list[dict] | None = None,
) -> str:
    variants_section = ""
    if variants:
        variant_names = [v.get("name", "") for v in variants if v.get("name")]
        if variant_names:
            variants_section = f"""
PRODUCT VARIANTS: {", ".join(variant_names)}
When writing generation_prompt, specify the primary variant (first in list) so Imagen 3 knows which variant to render.
"""

    return f"""Analyze the following visual analyses and produce a structured output in JSON format.

USER PRODUCT ANALYSES:
{json.dumps([a["raw_analysis"] for a in user_analyses], ensure_ascii=False)}

COMPETITOR PRODUCT ANALYSES:
{json.dumps([a["raw_analysis"] for a in competitor_analyses], ensure_ascii=False)}
{variants_section}
TASK:
1. Identify successful visual patterns in competitor images (quality, composition, backgrounds, lighting)
2. Identify the strong visual features of the user product
3. Combine both to create a detailed generation prompt for Imagen 3

generation_prompt RULES:
- Start with "A professional product photo of [product]"
- Incorporate successful styles observed in competitor visuals
- Specify lighting, composition, and background details
- If variants are listed above, specify the primary variant in the prompt
- Minimum 20, maximum 300 characters
- Write in English

Respond ONLY in this JSON format, nothing else:
{{
    "dominant_colors": ["#hex1", "#hex2"],
    "composition_style": "string",
    "background_type": "string",
    "product_focus_score": 0.0,
    "quality_score": 0.0,
    "style_tags": ["tag1", "tag2"],
    "improvement_suggestions": ["suggestion1", "suggestion2"],
    "generation_prompt": "A professional product photo of..."
}}
"""
