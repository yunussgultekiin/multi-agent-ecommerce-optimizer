import uuid
import logging
from pathlib import Path
from app import limiter
from app.config import settings
from fastapi import APIRouter, File, HTTPException, Request, UploadFile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["upload"])
_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_LOCAL_DIR = Path("/tmp/uploads")
_LOCAL_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/image")
@limiter.limit("20/minute")
async def upload_image(request: Request, file: UploadFile = File(...)):
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Sadece JPEG, PNG veya WebP yükleyebilirsiniz")

    content = await file.read()
    if len(content) > _MAX_BYTES:
        raise HTTPException(status_code=400, detail="Dosya boyutu 10 MB'ı geçemez")

    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "jpg"

    try:
        from google.cloud import storage

        blob_name = f"uploads/{uuid.uuid4()}.{ext}"
        gcs = storage.Client(project=settings.google_cloud_project)
        bucket = gcs.bucket(settings.gcs_bucket)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(content, content_type=file.content_type)
        logger.info("image_uploaded_gcs | blob=%s size=%d", blob_name, len(content))
        return {"url": f"https://storage.googleapis.com/{settings.gcs_bucket}/{blob_name}"}
    except Exception as exc:
        logger.warning("gcs_unavailable_using_local | error=%s", exc)

    try:
        filename = f"{uuid.uuid4()}.{ext}"
        (_LOCAL_DIR / filename).write_bytes(content)
        base = str(request.base_url).rstrip("/").replace("http://", "https://")
        url = f"{base}/uploads/{filename}"
        logger.info("image_uploaded_local | file=%s size=%d", filename, len(content))
        return {"url": url}
    except Exception as exc:
        logger.error("local_upload_failed | error=%s", exc)
        raise HTTPException(status_code=500, detail="Görsel yüklenemedi")
