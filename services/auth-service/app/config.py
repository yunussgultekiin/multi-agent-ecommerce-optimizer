from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = Field(default="", alias="DATABASE_URL")
    cloud_sql_instance: str = Field(default="", alias="CLOUD_SQL_INSTANCE")
    db_user: str = Field(default="", alias="DB_USER")
    db_pass: str = Field(default="", alias="DB_PASS")
    db_name: str = Field(default="", alias="DB_NAME")
    db_ip_type: str = Field(default="PUBLIC", alias="DB_IP_TYPE")
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    gcp_project_id: str = Field(default="", alias="GCP_PROJECT_ID")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    registration_enabled: bool = Field(default=True, alias="REGISTRATION_ENABLED")

settings = Settings()
