import asyncio
import io
import logging
from dataclasses import dataclass

from PIL import Image
from rembg import new_session, remove

logger = logging.getLogger(__name__)

_PRODUCT_FILL_RATIO = 0.88


@dataclass(frozen=True)
class PlatformSpec:
    display_name: str
    canvas_size: tuple[int, int]
    canvas_color: tuple[int, int, int]


PLATFORM_SPECS: dict[str, PlatformSpec] = {
    "amazon": PlatformSpec(
        display_name="Amazon",
        canvas_size=(2000, 2000),
        canvas_color=(255, 255, 255),
    ),
    "trendyol": PlatformSpec(
        display_name="Trendyol",
        canvas_size=(1200, 1800),
        canvas_color=(255, 255, 255),
    ),
    "hepsiburada": PlatformSpec(
        display_name="Hepsiburada",
        canvas_size=(1500, 1500),
        canvas_color=(255, 255, 255),
    ),
}

_DEFAULT_SPEC = PLATFORM_SPECS["hepsiburada"]

_session = None


def get_platform_spec(target_platform: str) -> PlatformSpec:
    return PLATFORM_SPECS.get((target_platform or "").lower().strip(), _DEFAULT_SPEC)


def _get_session():
    global _session
    if _session is None:
        logger.info("Loading rembg u2net session (first use)")
        _session = new_session("u2net")
        logger.info("rembg u2net session ready")
    return _session


def _remove_background_sync(image_bytes: bytes) -> bytes:
    return remove(image_bytes, session=_get_session())


def _crop_to_subject_sync(rgba_bytes: bytes) -> bytes:
    """Remove transparent padding — getbbox finds the tightest non-transparent bbox."""
    img = Image.open(io.BytesIO(rgba_bytes)).convert("RGBA")
    bbox = img.getbbox()
    if bbox is None:
        logger.warning("getbbox returned None — returning original rembg output")
        return rgba_bytes
    buf = io.BytesIO()
    img.crop(bbox).save(buf, format="PNG")
    return buf.getvalue()


def _compose_clean_canvas_sync(
    rgba_bytes: bytes,
    canvas_size: tuple[int, int],
    canvas_color: tuple[int, int, int],
) -> bytes:
    """Center the cropped product on a platform-colored canvas. No shadow — Gemini adds it."""
    product = Image.open(io.BytesIO(rgba_bytes)).convert("RGBA")

    max_w = int(canvas_size[0] * _PRODUCT_FILL_RATIO)
    max_h = int(canvas_size[1] * _PRODUCT_FILL_RATIO)
    product.thumbnail((max_w, max_h), Image.LANCZOS)

    pw, ph = product.size
    cx, cy = canvas_size
    x = (cx - pw) // 2
    y = (cy - ph) // 2

    canvas = Image.new("RGBA", canvas_size, (*canvas_color, 255))
    canvas.paste(product, (x, y), mask=product)

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


async def remove_background(image_bytes: bytes) -> bytes:
    loop = asyncio.get_running_loop()
    rgba_bytes: bytes = await loop.run_in_executor(None, _remove_background_sync, image_bytes)
    logger.debug("rembg inference complete | output_size=%d", len(rgba_bytes))
    return rgba_bytes


async def crop_to_subject(rgba_bytes: bytes) -> bytes:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _crop_to_subject_sync, rgba_bytes)


async def compose_clean_canvas(
    rgba_bytes: bytes,
    canvas_size: tuple[int, int],
    canvas_color: tuple[int, int, int],
) -> bytes:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, _compose_clean_canvas_sync, rgba_bytes, canvas_size, canvas_color
    )