import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_KEY", "test-secret")

from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.routers import projects as projects_router  # noqa: E402


def _create_demo_project(projects_root: Path, project_id: str = "demo") -> Path:
    project_path = projects_root / project_id
    (project_path / "contexts").mkdir(parents=True, exist_ok=True)
    (project_path / "model" / "SampleModel" / "workflow" / "01_stage").mkdir(parents=True, exist_ok=True)
    (project_path / "parameters").mkdir(parents=True, exist_ok=True)
    (project_path / "project.yml").write_text("name: demo\n", encoding="utf-8")
    (project_path / "contexts" / "default.yml").write_text("name: default\nenabled: true\n", encoding="utf-8")
    (project_path / "model" / "SampleModel" / "model.yml").write_text(
        "\n".join(
            [
                "target_table:",
                "  name: sample_table",
                "  schema: dm",
                "  description: sample",
                "  template: dqcr",
                "  engine: oracle",
                "  attributes:",
                "    - name: id",
                "      domain_type: number",
                "workflow:",
                "  description: sample workflow",
                "  folders:",
                "    01_stage:",
                "      enabled: true",
                "      description: stage",
                "cte_settings:",
                "  default: insert_fc",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project_path / "model" / "SampleModel" / "workflow" / "01_stage" / "folder.yml").write_text(
        "materialized: insert_fc\n",
        encoding="utf-8",
    )
    (project_path / "model" / "SampleModel" / "workflow" / "01_stage" / "001_main.sql").write_text(
        "-- comment\nSELECT 1 AS id\n",
        encoding="utf-8",
    )
    return project_path


@pytest.fixture()
def api_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    projects_root = tmp_path / "projects"
    projects_root.mkdir(parents=True, exist_ok=True)
    _create_demo_project(projects_root)

    monkeypatch.setattr(settings, "projects_path", str(projects_root))
    monkeypatch.setattr(projects_router.settings, "projects_path", str(projects_root))
    monkeypatch.setattr(projects_router.FW_SERVICE, "_projects_base_path", projects_root)
    projects_router._BUILD_HISTORY.clear()
    projects_router._VALIDATION_HISTORY.clear()

    with TestClient(app) as client:
        yield client
