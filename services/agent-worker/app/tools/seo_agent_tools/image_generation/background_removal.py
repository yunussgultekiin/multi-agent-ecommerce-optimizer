import asyncio
import io
import logging
from dataclasses import dataclass
from PIL import Image, ImageEnhance, ImageFilter
from rembg import new_session, remove

logger = logging.getLogger(__name__)
_PRODUCT_FILL_RATIO = 0.85
_PAD_PX = 24
_SHADOW_BLUR = 20
_SHADOW_OPACITY = 0.30
_SHADOW_OFFSET_RATIO = 0.025
_session = None

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

def _refine_alpha_mask_sync(rgba_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(rgba_bytes)).convert("RGBA")
    r, g, b, a = img.split()
    a = a.filter(ImageFilter.GaussianBlur(radius=1.0))
    a = a.point(lambda x: 0 if x < 12 else (255 if x > 243 else x))
    a = a.filter(ImageFilter.GaussianBlur(radius=0.5))
    img_clean = Image.merge("RGBA", (r, g, b, a))
    buf = io.BytesIO()
    img_clean.save(buf, format="PNG")
    return buf.getvalue()

def _crop_to_subject_sync(rgba_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(rgba_bytes)).convert("RGBA")
    bbox = img.getbbox()
    if bbox is None:
        logger.warning("getbbox returned None — returning original rembg output")
        return rgba_bytes
    w, h = img.size
    left = max(0, bbox[0] - _PAD_PX)
    top = max(0, bbox[1] - _PAD_PX)
    right = min(w, bbox[2] + _PAD_PX)
    bottom = min(h, bbox[3] + _PAD_PX)
    buf = io.BytesIO()
    img.crop((left, top, right, bottom)).save(buf, format="PNG")
    return buf.getvalue()

def _compose_clean_canvas_sync(
    rgba_bytes: bytes,
    canvas_size: tuple[int, int],
    canvas_color: tuple[int, int, int],
) -> bytes:
    product = Image.open(io.BytesIO(rgba_bytes)).convert("RGBA")

    max_w = int(canvas_size[0] * _PRODUCT_FILL_RATIO)
    max_h = int(canvas_size[1] * _PRODUCT_FILL_RATIO)

    pw, ph = product.size
    scale = min(max_w / pw, max_h / ph)
    new_w = max(1, int(pw * scale))
    new_h = max(1, int(ph * scale))
    product = product.resize((new_w, new_h), Image.LANCZOS)

    cx, cy = canvas_size
    x = (cx - new_w) // 2
    y = (cy - new_h) // 2

    canvas = Image.new("RGBA", canvas_size, (*canvas_color, 255))

    _, _, _, alpha = product.split()
    shadow_offset_y = max(6, int(new_h * _SHADOW_OFFSET_RATIO))
    shadow_mask = Image.new("L", canvas_size, 0)
    shadow_mask.paste(alpha, (x, y + shadow_offset_y))
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(radius=_SHADOW_BLUR))
    shadow_mask = shadow_mask.point(lambda v: int(v * _SHADOW_OPACITY))
    shadow_layer = Image.new("RGBA", canvas_size, (10, 10, 10, 0))
    shadow_layer.putalpha(shadow_mask)
    canvas.alpha_composite(shadow_layer)

    canvas.paste(product, (x, y), mask=product)

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()

def _enhance_image_sync(image_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Brightness(img).enhance(1.04)
    img = ImageEnhance.Sharpness(img).enhance(1.25)
    img = ImageEnhance.Color(img).enhance(1.08)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()

async def remove_background(image_bytes: bytes) -> bytes:
    loop = asyncio.get_running_loop()
    rgba_bytes: bytes = await loop.run_in_executor(None, _remove_background_sync, image_bytes)
    logger.debug("rembg inference complete | output_size=%d", len(rgba_bytes))
    return rgba_bytes

async def refine_alpha_mask(rgba_bytes: bytes) -> bytes:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _refine_alpha_mask_sync, rgba_bytes)

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

async def enhance_image(image_bytes: bytes) -> bytes:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _enhance_image_sync, image_bytes)
