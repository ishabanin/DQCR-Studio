from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DQCR Studio Backend"
    api_prefix: str = "/api/v1"
    projects_path: str = "/app/projects"
    catalog_path: str = "/app/catalog"
    cors_origins: list[str] = ["http://localhost:80", "http://127.0.0.1:80"]
    secret_key: str
    log_level: Literal["debug", "info", "warning", "error"] = "info"
    fw_use_cli: bool = True
    fw_cli_command: str = "fw2"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def model_post_init(self, __context: object) -> None:
        self.projects_path = _resolve_runtime_path(self.projects_path, "projects")
        self.catalog_path = _resolve_runtime_path(self.catalog_path, "catalog")


def _resolve_runtime_path(configured_path: str, local_dir_name: str) -> str:
    path = Path(configured_path)
    try:
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    except OSError:
        # Allow docker defaults (/app/*) to work in containers and transparently
        # fall back to repo-local folders during host/dev runs.
        repo_root = Path(__file__).resolve().parents[3]
        fallback = repo_root / local_dir_name
        fallback.mkdir(parents=True, exist_ok=True)
        return str(fallback)


settings = Settings()
