import asyncio
import base64
import logging
from typing import Optional
import httpx
import google.auth.exceptions
import google.api_core.exceptions
from pydantic import BaseModel
from google import genai
from google.genai import types
from google.genai.types import HttpOptions
from app.config import settings
from app.core import ToolResult

logger = logging.getLogger(__name__)

_client = genai.Client(
    vertexai=True,
    project=settings.google_cloud_project,
    location=settings.google_cloud_location,
    http_options=HttpOptions(api_version="v1"),
)

_PLATFORM_BG = {
    "amazon": "pure white background, clean studio lighting",
    "trendyol": "clean neutral background, soft shadow",
    "hepsiburada": "clean neutral background, soft shadow",
}

_IMAGEN_MODEL = "imagen-3.0-capability-001"


class ImageGenerationInput(BaseModel):
    user_product: dict
    target_platform: str
    rival_json: dict = {}


def _select_variant(user_product: dict, pricing_result: dict) -> Optional[dict]:
    variants = user_product.get("variants", [])
    if not variants:
        return None

    overlap_data = pricing_result.get("competitor_variant_overlap", [])
    if not overlap_data:
        return variants[0] if isinstance(variants[0], dict) else None

    best, min_overlap = None, None
    for v in variants:
        if not isinstance(v, dict):
            continue
        name = v.get("name", "")
        count = next(
            (len(o.get("matching_competitors", [])) for o in overlap_data if o.get("variant_name") == name),
            0,
        )
        if min_overlap is None or count < min_overlap:
            min_overlap = count
            best = v

    return best


def _build_image_generation_prompt(
    user_product: dict,
    target_platform: str,
    selected_variant: Optional[dict],
) -> str:
    bg_rule = _PLATFORM_BG.get(target_platform, "clean neutral background, soft shadow")
    title = user_product.get("title", "product")
    brand = user_product.get("brand", "")

    variant_note = ""
    if selected_variant and isinstance(selected_variant, dict):
        name = selected_variant.get("name", "")
        if name:
            variant_note = f" Show the {name} variant of the product."

    brand_note = f" Preserve the {brand} brand logo and markings if visible." if brand else ""

    return (
        f"Edit the provided product image into a clean marketplace hero image. "
        f"{bg_rule}, centered 1:1 hero image.{variant_note}{brand_note} "
        f"Preserve the exact product identity: shape, color, material, texture, proportions, and all distinctive details. "
        f"Do not redesign the product. Do not create a different product. "
        f"Do not add accessories, labels, new patterns, extra objects, different colors, or different models. "
        f"Product: {title}."
    )


async def _fetch_image_bytes(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=15.0) as http:
        response = await http.get(url)
        response.raise_for_status()
        return response.content


async def _edit_with_imagen(source_url: str, prompt: str) -> Optional[str]:
    try:
        image_bytes = await _fetch_image_bytes(source_url)
    except Exception as exc:
        logger.warning("Failed to fetch source image | url=%s error=%s", source_url, exc)
        return None

    loop = asyncio.get_running_loop()
    try:
        response = await loop.run_in_executor(
            None,
            lambda: _client.models.generate_images(
                model=_IMAGEN_MODEL,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="1:1",
                    safety_filter_level="BLOCK_SOME_THRESHOLD",
                    edit_mode="EDIT_MODE_BGSWAP",
                ),
                reference_images=[
                    types.RawReferenceImage(
                        reference_image=types.Image(image_bytes=image_bytes),
                        reference_id=1,
                    )
                ],
            ),
        )

        if response.generated_images:
            img_bytes = response.generated_images[0].image.image_bytes
            b64 = base64.b64encode(img_bytes).decode()
            return f"data:image/png;base64,{b64}"

        logger.warning("Vertex AI Imagen returned no images")
        return None

    except google.auth.exceptions.DefaultCredentialsError as exc:
        logger.warning("Imagen credentials error: %s", exc)
        return None
    except google.api_core.exceptions.PermissionDenied as exc:
        logger.warning("Imagen permission denied: %s", exc)
        return None
    except Exception as exc:
        logger.warning("Vertex AI Imagen edit failed: %s", exc)
        return None


class ImageGenerationTool:
    async def run(self, input: ImageGenerationInput) -> ToolResult:
        user_product = input.user_product
        image_urls = user_product.get("image_urls", [])

        if not image_urls:
            logger.info("ImageGenerationTool skipped: no source image provided")
            return ToolResult(
                success=False,
                fallback_used=True,
                data={
                    "generated_image_url": None,
                    "selected_variant": None,
                    "error": "No source product image provided",
                },
            )

        pricing_result = input.rival_json.get("pricing_result", {})
        gap_result = input.rival_json.get("gap_result", {})

        selected_variant = _select_variant(user_product, pricing_result)
        prompt = _build_image_generation_prompt(
            user_product=user_product,
            target_platform=input.target_platform,
            selected_variant=selected_variant,
        )

        source_url = image_urls[0]
        logger.info(
            "ImageGenerationTool started | platform=%s source_url=%s variant=%s",
            input.target_platform,
            source_url,
            selected_variant.get("name") if selected_variant else None,
        )

        generated_url = await _edit_with_imagen(source_url, prompt)

        if generated_url:
            logger.info("ImageGenerationTool completed | platform=%s", input.target_platform)
            return ToolResult(
                success=True,
                data={
                    "generated_image_url": generated_url,
                    "selected_variant": selected_variant,
                    "error": None,
                },
                fallback_used=False,
            )

        logger.warning("ImageGenerationTool: image edit failed, returning null")
        return ToolResult(
            success=False,
            fallback_used=True,
            data={
                "generated_image_url": None,
                "selected_variant": selected_variant,
                "error": "Image editing failed",
            },
        )
