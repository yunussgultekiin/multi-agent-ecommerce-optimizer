import asyncio
import logging
import google.api_core.exceptions
import google.auth.exceptions
from google import genai
from google.genai import types
from google.genai.types import HttpOptions
from app.config import settings
from app.core import ToolResult
from .models_image import ImageGenerationInput
from .prompts_image import build_image_prompt
from .utils_image import fetch_image_bytes, log_image_tool_call, select_variant, upload_to_gcs

logger = logging.getLogger(__name__)

_IMAGEN_TIMEOUT_SECONDS = 60

_client = genai.Client(
    vertexai=True,
    project=settings.google_cloud_project,
    location=settings.google_cloud_location,
    http_options=HttpOptions(api_version="v1"),
)

async def _edit_with_imagen(source_url: str, prompt: str) -> bytes | None:
    try:
        image_bytes = await fetch_image_bytes(source_url)
    except Exception as exc:
        logger.warning("Failed to fetch source image | url=%s error=%s", source_url, exc)
        return None

    loop = asyncio.get_running_loop()
    try:
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: _client.models.edit_image(
                    model=settings.imagen_model,
                    prompt=prompt,
                    reference_images=[
                        types.RawReferenceImage(
                            reference_image=types.Image(image_bytes=image_bytes),
                            reference_id=1,
                        ),
                        types.MaskReferenceImage(
                            reference_id=2,
                            config=types.MaskReferenceConfig(
                                mask_mode="MASK_MODE_BACKGROUND",
                            ),
                        ),
                    ],
                    config=types.EditImageConfig(
                        edit_mode="EDIT_MODE_BGSWAP",
                        number_of_images=1,
                    ),
                ),
            ),
            timeout=_IMAGEN_TIMEOUT_SECONDS,
        )

        if response.generated_images:
            return response.generated_images[0].image.image_bytes

        logger.warning("Imagen returned no images")
        return None

    except asyncio.TimeoutError:
        logger.warning("Imagen call timed out after %ds", _IMAGEN_TIMEOUT_SECONDS)
        return None
    except google.auth.exceptions.DefaultCredentialsError as exc:
        logger.warning("Imagen credentials error | error=%s", exc)
        return None
    except google.api_core.exceptions.PermissionDenied as exc:
        logger.warning("Imagen permission denied | error=%s", exc)
        return None
    except Exception as exc:
        logger.warning("Imagen edit failed | error=%s", exc)
        return None

class ImageGenerationTool:
    async def run(self, input_data: ImageGenerationInput) -> ToolResult:
        user_product = input_data.user_product
        target_platform = input_data.target_platform
        image_urls: list = user_product.get("image_urls", [])

        if not image_urls:
            logger.info("ImageGenerationTool skipped | reason=no_source_image platform=%s", target_platform)
            return ToolResult(
                success=False,
                fallback_used=True,
                data={
                    "generated_image_url": None,
                    "selected_variant": None,
                    "error": "No source product image provided",
                },
            )

        pricing_result = input_data.rival_json.get("pricing_result", {})
        gap_result = input_data.rival_json.get("gap_result", {})

        chosen_variant = select_variant(user_product, pricing_result)
        prompt = build_image_prompt(
            user_product=user_product,
            selected_variant=chosen_variant,
            gap_result=gap_result,
            target_platform=target_platform,
        )

        source_url = image_urls[0]
        variant_name = chosen_variant.get("name") if chosen_variant else None

        logger.info(
            "ImageGenerationTool started | platform=%s variant=%s source_url=%s",
            target_platform,
            variant_name,
            source_url,
        )

        img_bytes = await _edit_with_imagen(source_url, prompt)

        if img_bytes is None:
            log_image_tool_call(
                target_platform=target_platform,
                selected_variant=variant_name,
                generated_image_success=False,
                fallback_used=True,
            )
            return ToolResult(
                success=False,
                fallback_used=True,
                data={
                    "generated_image_url": None,
                    "selected_variant": chosen_variant,
                    "error": "Imagen edit returned no output",
                },
            )

        public_url = await upload_to_gcs(
            image_bytes=img_bytes,
            project=settings.google_cloud_project,
            bucket_name=settings.gcs_bucket,
        )

        if public_url is None:
            log_image_tool_call(
                target_platform=target_platform,
                selected_variant=variant_name,
                generated_image_success=False,
                fallback_used=True,
            )
            return ToolResult(
                success=False,
                fallback_used=True,
                data={
                    "generated_image_url": None,
                    "selected_variant": chosen_variant,
                    "error": "GCS upload failed",
                },
            )

        log_image_tool_call(
            target_platform=target_platform,
            selected_variant=variant_name,
            generated_image_success=True,
            fallback_used=False,
        )
        return ToolResult(
            success=True,
            fallback_used=False,
            data={
                "generated_image_url": public_url,
                "selected_variant": chosen_variant,
                "error": None,
            },
        )
