import asyncio
import logging
from contextlib import asynccontextmanager
from functools import partial
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
    is_subject_too_small,
    log_image_tool_call,
    select_variant,
    upload_to_gcs,
)

logger = logging.getLogger(__name__)
_GEMINI_TIMEOUT_SECONDS = 60

_STUDIO_PROMPT = (
    "This is a product photo for a marketplace listing. "
    "Use the provided product image as the exact source. "
    "Do not change the product identity, design, logo, colors, text, pattern, shape, or proportions. "
    "Keep the product centered and clearly visible. "
    "Keep the background pure white. "
    "Improve only the studio lighting, contrast, and natural product appearance. "
    "Do not zoom out. "
    "Do not make the product smaller. "
    "Do not add extra objects, decorations, labels, watermarks, hands, people, or branding. "
    "Do not add a strong artificial shadow. "
    "The result must remain a clean professional marketplace product photo."
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

            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    return part.inline_data.data

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

async def _build_marketplace_canvas_async(
    image_bytes: bytes,
    target_platform: str,
    *,
    add_shadow: bool = True,
) -> bytes:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        partial(
            build_marketplace_canvas,
            image_bytes,
            target_platform=target_platform,
            add_shadow=add_shadow,
        ),
    )

async def _is_subject_too_small_async(image_bytes: bytes) -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, is_subject_too_small, image_bytes)

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
            "ImageGenerationTool started | platform=%s variant=%s source=%s pipeline=removebg_canvas_gemini_validate",
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

        try:
            removed_bg_bytes = await remove_background(raw_bytes)
        except Exception as exc:
            logger.warning("Background removal failed | error=%s", exc)
            log_image_tool_call(target_platform, variant_name, success=False)
            return _failure_result("Background removal failed", chosen_variant)

        try:
            canvas_bytes = await _build_marketplace_canvas_async(
                removed_bg_bytes,
                target_platform,
                add_shadow=True,
            )
        except Exception as exc:
            logger.warning("Marketplace canvas build failed | error=%s", exc)
            log_image_tool_call(target_platform, variant_name, success=False)
            return _failure_result("Marketplace canvas build failed", chosen_variant)

        enhanced_bytes = await _enhance_with_gemini(canvas_bytes)

        if enhanced_bytes is None:
            logger.warning(
                "Gemini studio enhancement failed | platform=%s action=upload_canvas_output",
                target_platform,
            )
            final_bytes = canvas_bytes
            fallback_used = True
        else:
            try:
                normalized_enhanced_bytes = await _build_marketplace_canvas_async(
                    enhanced_bytes,
                    target_platform,
                    add_shadow=True,
                )

                if await _is_subject_too_small_async(normalized_enhanced_bytes):
                    logger.warning(
                        "Gemini output rejected | platform=%s reason=subject_too_small action=upload_canvas_output",
                        target_platform,
                    )
                    final_bytes = canvas_bytes
                    fallback_used = True
                else:
                    final_bytes = normalized_enhanced_bytes
                    fallback_used = False

            except Exception as exc:
                logger.warning(
                    "Post-Gemini canvas rebuild failed | platform=%s error=%s action=upload_canvas_output",
                    target_platform,
                    exc,
                )
                final_bytes = canvas_bytes
                fallback_used = True

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