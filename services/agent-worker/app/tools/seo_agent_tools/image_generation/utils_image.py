import asyncio
import logging
import uuid
import httpx

logger = logging.getLogger(__name__)

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
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content

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
        blob.make_public()
        return blob.public_url

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
) -> None:
    logger.info(
        "ImageGenerationTool completed | platform=%s variant=%s success=%s",
        target_platform,
        selected_variant,
        success,
    )