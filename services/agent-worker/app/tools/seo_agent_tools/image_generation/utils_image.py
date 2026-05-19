import asyncio
import logging
import uuid
from io import BytesIO
import httpx
from PIL import Image, ImageFilter
from app.config import settings

logger = logging.getLogger(__name__)

PLATFORM_CANVAS_PRESETS: dict[str, tuple[int, int]] = {
    "amazon": (1600, 1600),
    "hepsiburada": (1200, 1200),
    "trendyol": (1200, 1800),
}

def get_platform_canvas_size(target_platform: str) -> tuple[int, int]:
    platform = (target_platform or "").strip().lower()
    return PLATFORM_CANVAS_PRESETS.get(platform, (1200, 1200))

def get_platform_product_ratio(target_platform: str) -> float:
    platform = (target_platform or "").strip().lower()

    if platform == "trendyol":
        return 0.78

    if platform == "amazon":
        return 0.76

    if platform == "hepsiburada":
        return 0.76

    return 0.76

def _crop_transparent_padding(product: Image.Image) -> Image.Image:
    rgba = product.convert("RGBA")
    alpha = rgba.getchannel("A")
    bbox = alpha.getbbox()

    if bbox is None:
        logger.warning("Product alpha bbox missing | action=return_original")
        return rgba

    left, top, right, bottom = bbox
    pad_x = max(8, int((right - left) * 0.04))
    pad_y = max(8, int((bottom - top) * 0.04))

    left = max(0, left - pad_x)
    top = max(0, top - pad_y)
    right = min(rgba.width, right + pad_x)
    bottom = min(rgba.height, bottom + pad_y)

    return rgba.crop((left, top, right, bottom))

def select_variant(user_product: dict, pricing_result: dict) -> dict | None:
    variants = user_product.get("variants", [])
    valid = [v for v in variants if isinstance(v, dict)]

    if not valid:
        return None

    overlap_data = pricing_result.get("competitor_variant_overlap", [])

    if not overlap_data:
        return valid[0]

    best: dict | None = None
    min_overlap: int | None = None

    for v in valid:
        name = v.get("name", "")

        count = next(
            (
                len(o.get("matching_competitors", []))
                for o in overlap_data
                if isinstance(o, dict) and o.get("variant_name") == name
            ),
            0,
        )

        if min_overlap is None or count < min_overlap:
            min_overlap = count
            best = v

    return best

async def fetch_image_bytes(url: str) -> bytes:
    url = url.replace(settings.api_gateway_local_url, settings.api_gateway_internal_url)

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content

def build_marketplace_canvas(
    product_image_bytes: bytes,
    target_platform: str = "default",
    product_max_ratio: float | None = None,
) -> bytes:
    product = Image.open(BytesIO(product_image_bytes)).convert("RGBA")
    product = _crop_transparent_padding(product)

    canvas_w, canvas_h = get_platform_canvas_size(target_platform)

    if product_max_ratio is None:
        product_max_ratio = get_platform_product_ratio(target_platform)

    max_w = int(canvas_w * product_max_ratio)
    max_h = int(canvas_h * product_max_ratio)

    product.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 255))

    x = (canvas_w - product.width) // 2
    y = (canvas_h - product.height) // 2

    alpha = product.getchannel("A")
    alpha_min, _ = alpha.getextrema()
    has_transparency = alpha_min < 255

    if has_transparency:
        shadow_alpha = alpha.filter(ImageFilter.GaussianBlur(18))
        shadow_alpha = shadow_alpha.point(lambda value: int(value * 0.22))

        shadow_layer = Image.new("RGBA", product.size, (0, 0, 0, 0))
        shadow_layer.putalpha(shadow_alpha)

        shadow_canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

        shadow_x = x + int(product.width * 0.025)
        shadow_y = y + int(product.height * 0.055)

        shadow_canvas.alpha_composite(shadow_layer, (shadow_x, shadow_y))
        canvas.alpha_composite(shadow_canvas)

    canvas.alpha_composite(product, (x, y))

    output = BytesIO()
    canvas.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()

async def upload_to_gcs(
    image_bytes: bytes,
    project: str,
    bucket_name: str,
) -> str | None:
    def _sync_upload() -> str:
        from google.cloud import storage

        gcs = storage.Client(project=project)
        bucket = gcs.bucket(bucket_name)

        blob_name = f"generated-images/{uuid.uuid4()}.png"
        blob = bucket.blob(blob_name)

        blob.upload_from_string(image_bytes, content_type="image/png")

        url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
        logger.info("GCS upload complete | url=%s", url)

        return url

    loop = asyncio.get_running_loop()

    try:
        return await loop.run_in_executor(None, _sync_upload)
    except Exception as exc:
        logger.warning("GCS upload failed | bucket=%s error=%s", bucket_name, exc)
        return None

def log_image_tool_call(
    target_platform: str,
    selected_variant: str | None,
    *,
    success: bool,
    fallback_used: bool = False,
) -> None:
    logger.info(
        "ImageGenerationTool completed | platform=%s variant=%s success=%s fallback_used=%s",
        target_platform,
        selected_variant,
        success,
        fallback_used,
    )