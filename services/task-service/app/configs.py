from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = ROOT_DIR / ".env.example"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file = str(ENV_FILE),
        env_file_encoding = "utf-8",
        case_sensitive = False,
        extra = "ignore"
    )

    DATABASE_URL: str

    REDIS_URL: str

    APP_ENV: str = "development"

settings = Settings()
