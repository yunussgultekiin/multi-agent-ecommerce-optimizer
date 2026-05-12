from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = Field(alias="REDIS_URL")
    task_queue_name: str = Field(default="task_queue", alias="TASK_QUEUE_NAME")

    database_url: str = Field(alias="BROKER_DATABASE_URL")

    agent_worker_url: str = Field(alias="AGENT_WORKER_URL")

    max_retry_count: int = Field(default=3, alias="MAX_RETRY_COUNT")
    retry_base_delay: float = Field(default=2.0, alias="RETRY_BASE_DELAY")

    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

settings = Settings()