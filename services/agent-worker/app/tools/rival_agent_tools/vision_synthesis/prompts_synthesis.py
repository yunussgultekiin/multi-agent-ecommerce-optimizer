import json

def _extract_product_summary(user_product: dict) -> dict:
    return {
        "name": user_product.get("name")
        or user_product.get("title")
        or user_product.get("product_name"),
        "category": user_product.get("category"),
        "brand": user_product.get("brand"),
        "description": user_product.get("description"),
        "features": user_product.get("features") or [],
    }

def _extract_variant_color(variant: dict) -> str | None:
    return (
        variant.get("color")
        or variant.get("color_name")
        or variant.get("hex")
        or variant.get("hex_color")
        or variant.get("colour")
        or variant.get("colour_name")
    )

def _format_variants_for_prompt(user_product: dict) -> str:
    variants = user_product.get("variants") or []

    if not variants:
        return ""

    formatted_variants = []

    for variant in variants:
        if not isinstance(variant, dict):
            continue

        name = variant.get("name")
        color = _extract_variant_color(variant)

        if name or color:
            formatted_variants.append(
                {
                    "name": name,
                    "color": color,
                    "price_delta": variant.get("price_delta"),
                }
            )

    if not formatted_variants:
        return ""

    primary_variant = formatted_variants[0]

    return f"""
PRODUCT VARIANTS:
{json.dumps(formatted_variants, ensure_ascii=False)}

PRIMARY VARIANT TO EDIT:
{json.dumps(primary_variant, ensure_ascii=False)}

Variant rules for generation_prompt:
- If the primary variant has a color, clearly mention that exact color.
- If the primary variant has only a name, clearly mention that variant name.
- Edit only the primary variant.
- Do not show or generate all variants together.
- Do not invent variant colors if no color is provided.
"""

def _format_competitor_context(
    competitor_analyses: list[dict],
    synthesis_mode: str,
    valid_competitor_image_count: int,
) -> str:
    if not competitor_analyses:
        return f"""
COMPETITOR IMAGE CONTEXT:
No sufficient competitor image analyses are available.

SYNTHESIS MODE:
{synthesis_mode}

VALID COMPETITOR IMAGE COUNT:
{valid_competitor_image_count}

Fallback rules:
- Generate the style brief using only user_product.
- Do not pretend competitor visual patterns were analyzed.
- Use safe, generic e-commerce best practices: clean background, centered product, studio lighting, soft natural shadow, sharpness, and truthful product preservation.
"""

    return f"""
COMPETITOR IMAGE CONTEXT:
{valid_competitor_image_count} competitor images were successfully analyzed.

SYNTHESIS MODE:
{synthesis_mode}

COMPETITOR PRODUCT IMAGE ANALYSES:
{json.dumps([a["raw_analysis"] for a in competitor_analyses], ensure_ascii=False)}

Competitor pattern rules:
- Extract only presentation patterns from competitor images.
- Do not copy competitor product design, logos, labels, colors, or unique product details.
- Apply competitor-inspired improvements only to background, lighting, shadow, crop, framing, angle, sharpness, and e-commerce polish.
"""

def build_synthesis_prompt(
    user_product: dict,
    competitor_analyses: list[dict],
    synthesis_mode: str = "fallback_user_product_only",
    valid_competitor_image_count: int = 0,
) -> str:
    product_summary = _extract_product_summary(user_product)
    variants_section = _format_variants_for_prompt(user_product)

    competitor_context = _format_competitor_context(
        competitor_analyses=competitor_analyses,
        synthesis_mode=synthesis_mode,
        valid_competitor_image_count=valid_competitor_image_count,
    )

    return f"""Analyze the available competitor product image analyses and the user product data.
Produce a structured e-commerce style brief for ImageGenerationTool / Imagen 3.

IMPORTANT:
The final generation_prompt must be an IMAGE EDITING instruction.
It must not ask the model to create a new product from scratch.
It must preserve the real product identity and only improve the presentation style.

USER PRODUCT:
{json.dumps(product_summary, ensure_ascii=False)}

{competitor_context}

{variants_section}

TASK:
1. If competitor analyses are available, identify successful visual presentation patterns.
2. If competitor analyses are not sufficient, use safe e-commerce best practices instead.
3. Extract or infer patterns related to background, lighting, shadow, crop, framing, angle, product focus, sharpness, quality, and premium/e-commerce style.
4. Apply all improvements only to the product presentation style.
5. Combine visual presentation guidance with the user product name, category, brand, description, features, and variant information.
6. Create a truthful image edit generation_prompt for Imagen 3 / ImageGenerationTool.

generation_prompt RULES:
- Write the prompt as an image editing instruction, not a from-scratch generation prompt.
- Start exactly with "Edit the provided product image into"
- Preserve the exact product identity, shape, color, material, texture, proportions, scale, and distinctive details.
- Do not redesign the product.
- Do not create a different product.
- Do not add new product parts, accessories, decorations, labels, patterns, logos, features, or colors that are not visible or described in user_product.
- Apply improvements only to presentation style: background, lighting, shadow, framing, crop, angle, sharpness, and e-commerce polish.
- If competitor images use clean white background, background removal, subtle shadow, centered framing, or studio lighting, convert those into edit instructions.
- If no sufficient competitor image analysis exists, use generic e-commerce style: clean white or neutral background, natural soft shadow, studio lighting, centered framing, and improved sharpness.
- If variants are provided, edit only the primary variant and preserve its exact color/name.
- If variants are not provided, ignore variant logic and do not invent variant colors.
- Keep the result truthful, non-misleading, and suitable for an e-commerce listing image.
- Minimum 20 characters.
- Maximum 500 characters.
- Write in English.

Respond ONLY in this JSON format, nothing else:
{{
    "dominant_colors": ["#hex1", "#hex2"],
    "composition_style": "string",
    "background_type": "string",
    "product_focus_score": 0.0,
    "quality_score": 0.0,
    "style_tags": ["tag1", "tag2"],
    "improvement_suggestions": ["suggestion1", "suggestion2"],
    "generation_prompt": "Edit the provided product image into..."
}}
"""