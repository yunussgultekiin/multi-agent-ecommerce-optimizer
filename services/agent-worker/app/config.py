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
        default="synapse-btk-hackathon-2026", alias="GOOGLE_CLOUD_PROJECT"
    )
    google_cloud_location: str = Field(
        default="us-central1", alias="GOOGLE_CLOUD_LOCATION"
    )

    rival_discovery_model: str = Field(
        default="gemini-2.5-flash-lite", alias="RIVAL_DISCOVERY_MODEL"
    )
    rival_research_model: str = Field(
        default="gemini-2.5-flash-lite", alias="RIVAL_RESEARCH_MODEL"
    )
    rival_sentiment_model: str = Field(
        default="gemini-2.5-flash", alias="RIVAL_SENTIMENT_MODEL"
    )
    rival_trends_model: str = Field(
        default="gemini-2.5-flash", alias="RIVAL_TRENDS_MODEL"
    )
    rival_market_gap_model: str = Field(
        default="gemini-2.5-flash", alias="RIVAL_MARKET_GAP_MODEL"
    )
    rival_pricing_model: str = Field(
        default="gemini-2.5-flash", alias="RIVAL_PRICING_MODEL"
    )

    seo_optimizer_model: str = Field(
        default="gemini-2.5-flash", alias="SEO_OPTIMIZER_MODEL"
    )
    chroma_collection_name: str = Field(
        default="seo_rules", alias="CHROMA_COLLECTION_NAME"
    )
    chroma_top_k: int = Field(default=6, alias="CHROMA_TOP_K")

    removebg_api_key: str = Field(default="", alias="REMOVEBG_API_KEY")
    
    gemini_image_model: str = Field(
        default="gemini-2.5-flash-image",
        alias="GEMINI_IMAGE_MODEL",
    )
    gcs_bucket: str = Field(
        default="synapse-btk-hackathon-images", alias="GCS_BUCKET"
    )
    api_gateway_local_url: str = Field(
        default="http://localhost:8000", alias="API_GATEWAY_LOCAL_URL"
    )
    api_gateway_internal_url: str = Field(
        default="http://api-gateway:8080", alias="API_GATEWAY_INTERNAL_URL"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    jwt_secret_key: str = Field(default="local-dev-secret", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")

settings = Settings()