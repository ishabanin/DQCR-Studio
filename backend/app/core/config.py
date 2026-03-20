from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DQCR Studio Backend"
    api_prefix: str = "/api/v1"
    projects_path: str = "/app/projects"
    cors_origins: list[str] = ["http://localhost:80", "http://127.0.0.1:80"]
    secret_key: str
    log_level: Literal["debug", "info", "warning", "error"] = "info"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
