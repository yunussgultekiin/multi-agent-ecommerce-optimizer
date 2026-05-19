import asyncio
import logging
from contextlib import asynccontextmanager
import google.api_core.exceptions
import google.auth.exceptions
from google import genai
from google.genai import types
from google.genai.types import HttpOptions
from app.config import settings
from app.core import ToolResult
from .background_removal import remove_background
from .models_image import ImageGenerationInput
from .utils_image import (
    build_marketplace_canvas,
    fetch_image_bytes,
    log_image_tool_call,
    select_variant,
    upload_to_gcs,
)

logger = logging.getLogger(__name__)
_GEMINI_TIMEOUT_SECONDS = 60

_STUDIO_PROMPT = (
    "This is a marketplace product photo already placed on a clean pure white studio canvas. "
    "Enhance it into a professional e-commerce listing image. "
    "Keep the product exactly the same: do not alter its shape, color, logo, text, pattern, handle, proportions, or material. "
    "Keep the background pure white. "
    "Improve lighting softly and naturally. "
    "Refine the product edges only if needed. "
    "Add or improve only a subtle realistic ground shadow beneath the product. "
    "Do not add props, decorations, text, watermark, labels, hands, people, or extra objects. "
    "The final image must look like a clean marketplace studio photo."
)

@asynccontextmanager
async def _gemini_image_client():
    client = genai.Client(
        vertexai=True,
        project=settings.google_cloud_project,
        location=settings.google_cloud_location,
        http_options=HttpOptions(api_version="v1beta"),
    )

    try:
        yield client
    finally:
        await client.aio.aclose()
        client.close()

async def _enhance_with_gemini(image_bytes: bytes) -> bytes | None:
    try:
        async with _gemini_image_client() as client:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=settings.gemini_image_model,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part(
                                    inline_data=types.Blob(
                                        mime_type="image/png",
                                        data=image_bytes,
                                    )
                                ),
                                types.Part(text=_STUDIO_PROMPT),
                            ],
                        )
                    ],
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                    ),
                ),
                timeout=_GEMINI_TIMEOUT_SECONDS,
            )

            candidates = getattr(response, "candidates", None) or []

            if not candidates:
                logger.warning("Gemini returned no candidates")
                return None

            content = getattr(candidates[0], "content", None)
            parts = getattr(content, "parts", None) or []

            for part in parts:
                inline_data = getattr(part, "inline_data", None)

                if inline_data and inline_data.data:
                    return inline_data.data

        logger.warning("Gemini returned no image part in response")
        return None

    except asyncio.TimeoutError:
        logger.warning("Gemini image timed out after %ds", _GEMINI_TIMEOUT_SECONDS)
        return None
    except (
        google.auth.exceptions.DefaultCredentialsError,
        google.api_core.exceptions.PermissionDenied,
    ) as exc:
        logger.warning("Gemini auth/permission error | error=%s", exc)
        return None
    except Exception as exc:
        logger.warning("Gemini image enhancement failed | error=%s", exc)
        return None

def _failure_result(
    error_msg: str,
    chosen_variant: dict | None = None,
) -> ToolResult:
    return ToolResult(
        success=False,
        fallback_used=True,
        data={
            "generated_image_url": None,
            "selected_variant": chosen_variant,
            "error": error_msg,
        },
    )

class ImageGenerationTool:
    async def run(self, input_data: ImageGenerationInput) -> ToolResult:
        user_product = input_data.user_product
        target_platform = input_data.target_platform
        image_urls: list = user_product.get("image_urls", [])

        if not image_urls:
            logger.info("ImageGenerationTool skipped | reason=no_source_image")
            return _failure_result("No source product image provided")

        pricing_result = input_data.rival_json.get("pricing_result", {})
        chosen_variant = select_variant(user_product, pricing_result)
        variant_name = chosen_variant.get("name") if chosen_variant else None

        source_url = (
            chosen_variant.get("image_url")
            if chosen_variant and chosen_variant.get("image_url")
            else image_urls[0]
        )

        logger.info(
            "ImageGenerationTool started | platform=%s variant=%s source=%s pipeline=removebg_platform_canvas_gemini",
            target_platform,
            variant_name,
            source_url,
        )

        try:
            raw_bytes = await fetch_image_bytes(source_url)
        except Exception as exc:
            logger.warning("Image fetch failed | url=%s error=%s", source_url, exc)
            log_image_tool_call(target_platform, variant_name, success=False)
            return _failure_result("Image fetch failed", chosen_variant)

        fallback_used = False

        try:
            product_cutout_bytes = await remove_background(raw_bytes)
        except Exception as exc:
            logger.warning(
                "Background removal failed, continuing with original image fallback | error=%s",
                exc,
            )
            product_cutout_bytes = raw_bytes
            fallback_used = True

        try:
            studio_canvas_bytes = build_marketplace_canvas(
                product_cutout_bytes,
                target_platform=target_platform,
            )

            logger.info(
                "Studio canvas generated | platform=%s variant=%s fallback_input=%s",
                target_platform,
                variant_name,
                fallback_used,
            )
        except Exception as exc:
            logger.warning(
                "Studio canvas build failed, using available image bytes | error=%s",
                exc,
            )
            studio_canvas_bytes = product_cutout_bytes
            fallback_used = True

        enhanced_bytes = await _enhance_with_gemini(studio_canvas_bytes)

        if enhanced_bytes is None:
            logger.warning(
                "Gemini studio enhancement failed | platform=%s action=upload_local_studio_canvas",
                target_platform,
            )
            final_bytes = studio_canvas_bytes
            fallback_used = True
        else:
            final_bytes = enhanced_bytes

        public_url = await upload_to_gcs(
            image_bytes=final_bytes,
            project=settings.google_cloud_project,
            bucket_name=settings.gcs_bucket,
        )

        if public_url is None:
            log_image_tool_call(target_platform, variant_name, success=False)
            return _failure_result("GCS upload failed", chosen_variant)

        log_image_tool_call(
            target_platform,
            variant_name,
            success=True,
            fallback_used=fallback_used,
        )

        return ToolResult(
            success=True,
            fallback_used=fallback_used,
            data={
                "generated_image_url": public_url,
                "selected_variant": chosen_variant,
                "error": None,
            },
        )