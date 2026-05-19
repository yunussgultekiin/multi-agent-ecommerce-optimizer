import asyncio
import logging
import uuid
from io import BytesIO
import httpx
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from app.config import settings
logger = logging.getLogger(__name__)

PLATFORM_CANVAS_PRESETS: dict[str, tuple[int, int]] = {
    "amazon": (1600, 1600),
    "hepsiburada": (1200, 1200),
    "trendyol": (1200, 1800),
}

PLATFORM_PRODUCT_RATIOS: dict[str, float] = {
    "amazon": 0.78,
    "hepsiburada": 0.78,
    "trendyol": 0.78,
}

_MIN_SUBJECT_FILL_RATIO = 0.42

def get_platform_canvas_size(target_platform: str) -> tuple[int, int]:
    platform = (target_platform or "").strip().lower()
    return PLATFORM_CANVAS_PRESETS.get(platform, (1200, 1200))

def get_platform_product_ratio(target_platform: str) -> float:
    platform = (target_platform or "").strip().lower()
    return PLATFORM_PRODUCT_RATIOS.get(platform, 0.78)


def _find_alpha_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    alpha_min, _ = alpha.getextrema()

    if alpha_min >= 255:
        return None

    return alpha.getbbox()

def _find_non_white_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    rgb = image.convert("RGB")
    white_bg = Image.new("RGB", rgb.size, (255, 255, 255))
    diff = ImageChops.difference(rgb, white_bg).convert("L")
    mask = diff.point(lambda value: 255 if value > 18 else 0)
    mask = mask.filter(ImageFilter.MinFilter(3))
    mask = mask.filter(ImageFilter.MaxFilter(5))
    return mask.getbbox()

def _pad_bbox(
    bbox: tuple[int, int, int, int],
    image_size: tuple[int, int],
    pad_ratio: float = 0.03,
) -> tuple[int, int, int, int]:
    left, top, right, bottom = bbox
    width = right - left
    height = bottom - top

    pad_x = max(6, int(width * pad_ratio))
    pad_y = max(6, int(height * pad_ratio))

    image_w, image_h = image_size

    return (
        max(0, left - pad_x),
        max(0, top - pad_y),
        min(image_w, right + pad_x),
        min(image_h, bottom + pad_y),
    )

def _crop_product_area(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")

    bbox = _find_alpha_bbox(rgba)
    if bbox is None:
        bbox = _find_non_white_bbox(rgba)

    if bbox is None:
        logger.warning("Product bbox missing | action=return_original")
        return rgba

    bbox = _pad_bbox(bbox, rgba.size)
    return rgba.crop(bbox)

def _subject_fill_ratio(image_bytes: bytes) -> float:
    image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    bbox = _find_alpha_bbox(image)

    if bbox is None:
        bbox = _find_non_white_bbox(image)

    if bbox is None:
        return 0.0

    left, top, right, bottom = bbox
    subject_w = max(1, right - left)
    subject_h = max(1, bottom - top)
    image_w, image_h = image.size

    return max(subject_w / image_w, subject_h / image_h)

def is_subject_too_small(image_bytes: bytes) -> bool:
    ratio = _subject_fill_ratio(image_bytes)
    return ratio < _MIN_SUBJECT_FILL_RATIO

def _resize_to_fit(
    image: Image.Image,
    max_w: int,
    max_h: int,
) -> Image.Image:
    width, height = image.size

    if width <= 0 or height <= 0:
        return image

    scale = min(max_w / width, max_h / height)

    new_w = max(1, int(width * scale))
    new_h = max(1, int(height * scale))

    if new_w == width and new_h == height:
        return image

    return image.resize((new_w, new_h), Image.Resampling.LANCZOS)

def _add_ground_shadow(
    canvas: Image.Image,
    product: Image.Image,
    x: int,
    y: int,
) -> None:
    canvas_w, canvas_h = canvas.size

    shadow_w = int(product.width * 0.72)
    shadow_h = max(16, int(product.height * 0.09))

    shadow_x = x + (product.width - shadow_w) // 2
    shadow_y = y + product.height - int(shadow_h * 0.25)

    shadow_layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow_layer)

    draw.ellipse(
        (
            shadow_x,
            shadow_y,
            shadow_x + shadow_w,
            shadow_y + shadow_h,
        ),
        fill=(0, 0, 0, 32),
    )

    shadow_layer = shadow_layer.filter(
        ImageFilter.GaussianBlur(max(10, int(product.width * 0.028)))
    )

    canvas.alpha_composite(shadow_layer)

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
    add_shadow: bool = True,
) -> bytes:
    product = Image.open(BytesIO(product_image_bytes)).convert("RGBA")
    product = _crop_product_area(product)

    canvas_w, canvas_h = get_platform_canvas_size(target_platform)

    if product_max_ratio is None:
        product_max_ratio = get_platform_product_ratio(target_platform)

    max_w = int(canvas_w * product_max_ratio)
    max_h = int(canvas_h * product_max_ratio)
    product = _resize_to_fit(product, max_w, max_h)
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 255))

    x = (canvas_w - product.width) // 2
    y = (canvas_h - product.height) // 2

    if add_shadow:
        _add_ground_shadow(canvas, product, x, y)

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