from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    task_service_url: str = Field(default="http://task-service:8080", alias="TASK_SERVICE_URL")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3.0-flash", alias="GEMINI_MODEL")
    chroma_host: str = Field(default="localhost", alias="CHROMA_HOST")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

settings = Settings()
