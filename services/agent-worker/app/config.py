from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    task_service_url: str = Field(default="http://task-service:8080", alias="TASK_SERVICE_URL")
    google_cloud_project: str = Field(default="ai-driven-seller-support", alias="GOOGLE_CLOUD_PROJECT")
    google_cloud_location: str = Field(default="us-central1", alias="GOOGLE_CLOUD_LOCATION")
    gemini_model: str = Field(default="gemini-2.5-flash-lite", alias="GEMINI_MODEL")
    gemini_research_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_RESEARCH_MODEL")
    gemini_vision_model: str = Field(default="gemini-2.5-flash-lite", alias="GEMINI_VISION_MODEL")
    chroma_host: str = Field(default="localhost", alias="CHROMA_HOST")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")

settings = Settings()
