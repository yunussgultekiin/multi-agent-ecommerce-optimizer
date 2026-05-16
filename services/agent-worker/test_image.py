import argparse
import asyncio
import json
import logging
import os
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv
from app.config import settings
from app.tools.seo_agent_tools.image_generation import tools_image
from app.tools.seo_agent_tools.image_generation.background_removal import (
    compose_clean_canvas,
    crop_to_subject,
    remove_background,
)
from app.tools.seo_agent_tools.image_generation.models_image import ImageGenerationInput
from app.tools.seo_agent_tools.image_generation.utils_image import select_variant

SERVICE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SERVICE_DIR.parents[1]
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(SERVICE_DIR / ".env", override=True)
os.environ.setdefault("JWT_SECRET_KEY", "test-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TASK_SERVICE_URL", "http://localhost:8080")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
os.environ.setdefault("GCS_BUCKET", "local-test-bucket")
sys.path.insert(0, str(SERVICE_DIR))
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s — %(message)s")
logger = logging.getLogger("test_image_live")
SUPPORTED_PLATFORMS = ["amazon", "trendyol", "hepsiburada"]
SAMPLE_PRODUCT = {
    "title": "Keep Calm and Carry On Baskılı Kırmızı Kupa",
    "brand": "",
    "image_urls": ["LOCAL_FILE"],
    "features": ["kırmızı seramik gövde", "beyaz baskı", "taç ve yazı detayı"],
    "variants": [
        {"name": "Kırmızı", "price": 150.0},
        {"name": "Siyah", "price": 150.0},
    ],
}

SAMPLE_RIVAL_JSON = {
    "pricing_result": {
        "competitor_variant_overlap": [
            {"variant_name": "Kırmızı", "matching_competitors": ["A", "B"]},
            {"variant_name": "Siyah", "matching_competitors": ["A", "B", "C"]},
        ]
    }
}

def _detect_extension(image_bytes: bytes) -> str:
    if image_bytes[:3] == b"\xff\xd8\xff":
        return "jpg"
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "webp"
    return "png"

def _save(path: Path, data: bytes) -> None:
    path.write_bytes(data)
    logger.info("Saved | path=%s size=%d bytes", path, len(data))

async def run_single_platform(
    *,
    image_path: Path,
    local_image_bytes: bytes,
    platform: str,
    base_output_dir: Path,
) -> dict:
    platform_dir = base_output_dir / platform
    platform_dir.mkdir(parents=True, exist_ok=True)
    uid = uuid.uuid4().hex[:8]

    async def _local_fetch(url: str) -> bytes:
        logger.info("fetch_image_bytes (local) | platform=%s", platform)
        return local_image_bytes

    async def _local_upload(image_bytes: bytes, project: str, bucket_name: str) -> str:
        if not isinstance(image_bytes, bytes):
            raise TypeError(f"upload_to_gcs: expected bytes, got {type(image_bytes)!r}")
        ext = _detect_extension(image_bytes)
        out_path = platform_dir / f"{platform}_final_{uid}.{ext}"
        _save(out_path, image_bytes)
        return str(out_path)

    async def _instrumented_remove(img_bytes: bytes) -> bytes:
        rgba = await remove_background(img_bytes)
        _save(platform_dir / f"{platform}_transparent_{uid}.png", rgba)
        return rgba

    async def _instrumented_crop(rgba_bytes: bytes) -> bytes:
        cropped = await crop_to_subject(rgba_bytes)
        _save(platform_dir / f"{platform}_cropped_{uid}.png", cropped)
        return cropped

    async def _instrumented_canvas(
        rgba_bytes: bytes,
        canvas_size: tuple,
        canvas_color: tuple,
    ) -> bytes:
        canvas = await compose_clean_canvas(rgba_bytes, canvas_size, canvas_color)
        _save(platform_dir / f"{platform}_canvas_{uid}.png", canvas)
        return canvas

    original_fetch = tools_image.fetch_image_bytes
    original_upload = tools_image.upload_to_gcs
    original_remove = tools_image.remove_background
    original_crop = tools_image.crop_to_subject
    original_canvas = tools_image.compose_clean_canvas

    tools_image.fetch_image_bytes = _local_fetch
    tools_image.upload_to_gcs = _local_upload
    tools_image.remove_background = _instrumented_remove
    tools_image.crop_to_subject = _instrumented_crop
    tools_image.compose_clean_canvas = _instrumented_canvas

    try:
        product = {**SAMPLE_PRODUCT, "image_urls": [str(image_path)]}
        input_data = ImageGenerationInput(
            user_product=product,
            target_platform=platform,
            rival_json=SAMPLE_RIVAL_JSON,
        )
        chosen_variant = select_variant(product, SAMPLE_RIVAL_JSON["pricing_result"])

        print("\n" + "═" * 80)
        print(f"PLATFORM : {platform.upper()}")
        print(f"VARIANT  : {json.dumps(chosen_variant, ensure_ascii=False)}")
        print(f"OUT DIR  : {platform_dir}")
        print("═" * 80)

        tool = tools_image.ImageGenerationTool()
        result = await tool.run(input_data)

        print(f"\nRESULT [{platform}]")
        print(f"  success          : {result.success}")
        print(f"  fallback_used    : {result.fallback_used}")
        print(f"  selected_variant : {result.data.get('selected_variant')}")
        print(f"  error            : {result.data.get('error')}")
        print(f"  output           : {result.data.get('generated_image_url')}")

        return {
            "platform": platform,
            "success": result.success,
            "fallback_used": result.fallback_used,
            "error": result.data.get("error"),
            "output": result.data.get("generated_image_url"),
        }

    finally:
        tools_image.fetch_image_bytes = original_fetch
        tools_image.upload_to_gcs = original_upload
        tools_image.remove_background = original_remove
        tools_image.crop_to_subject = original_crop
        tools_image.compose_clean_canvas = original_canvas

async def run_test(image_path: str, platform: str, output_dir: str) -> None:
    if not settings.google_cloud_project:
        print("[ENV ERROR] GOOGLE_CLOUD_PROJECT is not set.")
        sys.exit(1)

    src = Path(image_path).expanduser()
    if not src.exists():
        logger.error("Image not found: %s", src)
        sys.exit(1)

    local_bytes = src.read_bytes()
    logger.info("Loaded image | path=%s size=%d bytes", src, len(local_bytes))

    base_dir = Path(output_dir).expanduser().resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    platforms = SUPPORTED_PLATFORMS if platform == "all" else [platform]

    print("\n" + "─" * 80)
    print(f"PROJECT  : {settings.google_cloud_project}")
    print(f"IMAGE    : {src}")
    print(f"OUT DIR  : {base_dir}")
    print(f"PLATFORMS: {', '.join(platforms)}")
    print("─" * 80)

    results = []
    for p in platforms:
        r = await run_single_platform(
            image_path=src,
            local_image_bytes=local_bytes,
            platform=p,
            base_output_dir=base_dir,
        )
        results.append(r)

    print("\n" + "═" * 80)
    print("SUMMARY")
    print("═" * 80)
    for item in results:
        status = "OK  " if item["success"] else "FAIL"
        fallback = " [pillow fallback]" if item.get("fallback_used") else ""
        print(f"[{status}] {item['platform']:<15}{fallback}")
        print(f"         {item['output'] or item['error']}")
    print("═" * 80)
    print(f"\n{sum(1 for r in results if r['success'])}/{len(results)} successful")

def main() -> None:
    parser = argparse.ArgumentParser(
        description="ImageGenerationTool test — rembg + Pillow + Imagen PRODUCT_IMAGE"
    )
    parser.add_argument("--image", default="test_input.jpg")
    parser.add_argument(
        "--platform",
        default="all",
        choices=["all", "amazon", "trendyol", "hepsiburada"],
    )
    parser.add_argument("--output", default="./test_output")
    args = parser.parse_args()
    asyncio.run(run_test(args.image, args.platform, args.output))

if __name__ == "__main__":
    main()