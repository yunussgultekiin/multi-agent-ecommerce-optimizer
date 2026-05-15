PLATFORM_SPECS: dict[str, dict] = {
    "amazon": {
        "background": "pure white background (RGB 255,255,255), no gradients, no shadows on the background surface",
        "lighting": "even, flat studio lighting from all sides",
        "policy_note": (
            "Amazon main image policy: background must be pure white. "
            "No watermarks, no props, no extra objects, no text overlays. "
            "Product must fill at least 85% of the frame."
        ),
    },
    "trendyol": {
        "background": "clean light warm-grey gradient background (#F5F5F0 to #EBEBEB)",
        "lighting": "soft diffused studio lighting from upper-left, subtle natural drop shadow directly below the product",
        "policy_note": (
            "Trendyol hero image: warm, inviting marketplace aesthetic. "
            "Soft grounding shadow beneath the product is required. No busy props."
        ),
    },
    "hepsiburada": {
        "background": "clean neutral cool-grey background (#EFEFEF), uniform tone",
        "lighting": "diffused overhead studio lighting, soft drop shadow below the product",
        "policy_note": (
            "Hepsiburada hero image: clean, professional look. "
            "Subtle shadow to ground the product. No decorative elements."
        ),
    },
}

_DEFAULT_SPEC = PLATFORM_SPECS["hepsiburada"]

def build_image_prompt(
    user_product: dict,
    selected_variant: dict | None,
    gap_result: dict,
    target_platform: str,
) -> str:
    spec = PLATFORM_SPECS.get(target_platform, _DEFAULT_SPEC)

    title: str = user_product.get("title", "product")
    brand: str = user_product.get("brand", "")
    features: list = user_product.get("features", [])[:4]
    gap_opportunities: list = gap_result.get("gap_opportunities", [])[:2]

    bg = spec["background"]
    lighting = spec["lighting"]
    policy = spec["policy_note"]

    variant_note = ""
    if selected_variant and isinstance(selected_variant, dict):
        v_name = selected_variant.get("name", "")
        if v_name:
            variant_note = (
                f" Show specifically the '{v_name}' variant. "
                f"Preserve its exact color and finish."
            )

    brand_note = (
        f" Preserve all {brand} brand markings, logo placement, and embossing exactly as they appear on the product."
        if brand
        else ""
    )

    feature_note = (
        f" Key product features to keep clearly visible: {', '.join(str(f) for f in features)}."
        if features
        else ""
    )

    gap_note = (
        f" Visually emphasize these market-differentiating aspects if present on the product: {', '.join(str(g) for g in gap_opportunities)}."
        if gap_opportunities
        else ""
    )

    return (
        f"Edit the provided product photograph into a studio-quality e-commerce hero image. "
        f"This is a background replacement and lighting enhancement — do NOT redraw or reimagine the product itself. "
        f"Replace the background with: {bg}. "
        f"Apply: {lighting}. "
        f"{policy} "
        f"Add a realistic soft drop shadow beneath the product to anchor it naturally. "
        f"Preserve the exact product identity: shape, silhouette, color, material, surface texture, "
        f"proportions, and every distinctive physical detail. "
        f"Do NOT add accessories, change colors, alter patterns, introduce new objects, "
        f"add people, models, text, watermarks, or props of any kind. "
        f"Product: {title}."
        f"{feature_note}{gap_note}{variant_note}{brand_note}"
    )
