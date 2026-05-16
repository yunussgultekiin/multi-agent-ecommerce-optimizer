import asyncio
import logging

import google.api_core.exceptions
import google.auth.exceptions
from google import genai
from google.genai import types
from google.genai.types import HttpOptions

from app.config import settings
from app.core import ToolResult
from .background_removal import (
    compose_clean_canvas,
    crop_to_subject,
    get_platform_spec,
    remove_background,
)
from .models_image import ImageGenerationInput
from .utils_image import (
    fetch_image_bytes,
    log_image_tool_call,
    select_variant,
    upload_to_gcs,
)

logger = logging.getLogger(__name__)
_GEMINI_TIMEOUT_SECONDS = 60

_SHADOW_PROMPT = (
    "Add a soft, realistic drop shadow directly beneath the product. "
    "The shadow should be subtle, naturally blurred, and grounded. "
    "Do not change the product, its colors, or the background in any way."
)

_client = genai.Client(
    vertexai=True,
    project=settings.google_cloud_project,
    location=settings.google_cloud_location,
    http_options=HttpOptions(api_version="v1beta"),
)

async def _enhance_with_gemini(image_bytes: bytes) -> bytes | None:
    loop = asyncio.get_running_loop()
    try:
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: _client.models.generate_content(
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
                                types.Part(text=_SHADOW_PROMPT),
                            ],
                        )
                    ],
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                    ),
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

        spec = get_platform_spec(target_platform)
        source_url = image_urls[0]

        logger.info(
            "ImageGenerationTool started | platform=%s variant=%s canvas=%s source=%s",
            target_platform,
            variant_name,
            spec.canvas_size,
            source_url,
        )

        try:
            raw_bytes = await fetch_image_bytes(source_url)
        except Exception as exc:
            logger.warning("Image fetch failed | url=%s error=%s", source_url, exc)
            log_image_tool_call(target_platform, variant_name, success=False)
            return _failure_result("Image fetch failed", chosen_variant)

        try:
            rgba_bytes = await remove_background(raw_bytes)
        except Exception as exc:
            logger.warning("Background removal failed | error=%s", exc)
            log_image_tool_call(target_platform, variant_name, success=False)
            return _failure_result("Background removal failed", chosen_variant)

        try:
            rgba_bytes = await crop_to_subject(rgba_bytes)
        except Exception as exc:
            logger.warning("Bbox crop failed | error=%s", exc)
            log_image_tool_call(target_platform, variant_name, success=False)
            return _failure_result("Subject crop failed", chosen_variant)

        try:
            canvas_bytes = await compose_clean_canvas(
                rgba_bytes=rgba_bytes,
                canvas_size=spec.canvas_size,
                canvas_color=spec.canvas_color,
            )
        except Exception as exc:
            logger.warning("Canvas composition failed | error=%s", exc)
            log_image_tool_call(target_platform, variant_name, success=False)
            return _failure_result("Canvas composition failed", chosen_variant)

        enhanced_bytes = await _enhance_with_gemini(canvas_bytes)
        if enhanced_bytes is None:
            logger.warning(
                "Gemini shadow enhancement failed — using Pillow canvas | platform=%s",
                target_platform,
            )

        final_bytes = enhanced_bytes if enhanced_bytes is not None else canvas_bytes
        fallback_used = enhanced_bytes is None

        public_url = await upload_to_gcs(
            image_bytes=final_bytes,
            project=settings.google_cloud_project,
            bucket_name=settings.gcs_bucket,
        )
        if public_url is None:
            log_image_tool_call(target_platform, variant_name, success=False)
            return _failure_result("GCS upload failed", chosen_variant)

        log_image_tool_call(target_platform, variant_name, success=not fallback_used)
        return ToolResult(
            success=True,
            fallback_used=fallback_used,
            data={
                "generated_image_url": public_url,
                "selected_variant": chosen_variant,
                "error": None,
            },
        )