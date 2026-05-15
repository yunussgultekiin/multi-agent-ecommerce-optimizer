from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    redis_url: str = Field(alias="REDIS_URL")
    quota_limit: int = Field(default=10, alias="QUOTA_LIMIT")
    quota_ttl_seconds: int = Field(default=86400, alias="QUOTA_TTL_SECONDS")
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

settings = Settings()
