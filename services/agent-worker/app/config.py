from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent.parent.parent / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    task_service_url: str = Field(
        default="http://task-service:8080", alias="TASK_SERVICE_URL"
    )
    google_cloud_project: str = Field(
        default="ai-driven-seller-support", alias="GOOGLE_CLOUD_PROJECT"
    )
    google_cloud_location: str = Field(
        default="us-central1", alias="GOOGLE_CLOUD_LOCATION"
    )
    gemini_flash_model: str = Field(
        default="gemini-2.5-flash", alias="GEMINI_FLASH_MODEL"
    )
    gemini_pro_model: str = Field(default="gemini-2.5-pro", alias="GEMINI_PRO_MODEL")
    chroma_collection_name: str = Field(
        default="seo_rules", alias="CHROMA_COLLECTION_NAME"
    )
    chroma_top_k: int = Field(default=6, alias="CHROMA_TOP_K")
    imagen_model: str = Field(default="imagen-3.0-capability-001", alias="IMAGEN_MODEL")
    gcs_bucket: str = Field(default="ai-driven-seller-support-images", alias="GCS_BUCKET")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    jwt_secret_key: str = Field(default="local-dev-secret", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")

settings = Settings()
