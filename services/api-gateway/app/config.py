from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    auth_service_url: str = Field(alias="AUTH_SERVICE_URL")
    quota_service_url: str = Field(alias="QUOTA_SERVICE_URL")
    task_service_url: str = Field(alias="TASK_SERVICE_URL")
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    frontend_origin: str = Field(
        default="http://localhost:3000", alias="FRONTEND_ORIGIN"
    )
    rate_limit: str = Field(default="60/minute", alias="RATE_LIMIT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    gcs_bucket: str = Field(default="ai-driven-seller-support-images", alias="GCS_BUCKET")
    google_cloud_project: str = Field(default="ai-driven-seller-support", alias="GOOGLE_CLOUD_PROJECT")

settings = Settings()
