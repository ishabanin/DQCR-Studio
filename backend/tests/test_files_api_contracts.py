from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.core.config import settings


def test_files_content_blocks_path_traversal(api_client: TestClient) -> None:
    response = api_client.get(
        "/api/v1/projects/demo/files/content",
        params={"path": "../outside.txt"},
    )

    assert response.status_code == 400, response.text
    assert "Path traversal attempt detected" in response.json()["detail"]


def test_files_rename_rejects_path_separators(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/projects/demo/files/rename",
        json={"path": "project.yml", "new_name": "../renamed.yml"},
    )

    assert response.status_code == 400, response.text
    assert "must not contain path separators" in response.json()["detail"]


def test_files_delete_directory_recursive_roundtrip(api_client: TestClient) -> None:
    create_response = api_client.put(
        "/api/v1/projects/demo/files/content",
        json={
            "path": "model/SampleModel/workflow/99_tmp/001_tmp.sql",
            "content": "select 1\n",
        },
    )
    assert create_response.status_code == 200, create_response.text

    delete_response = api_client.delete(
        "/api/v1/projects/demo/files",
        params={"path": "model/SampleModel/workflow/99_tmp"},
    )
    assert delete_response.status_code == 200, delete_response.text

    read_response = api_client.get(
        "/api/v1/projects/demo/files/content",
        params={"path": "model/SampleModel/workflow/99_tmp/001_tmp.sql"},
    )
    assert read_response.status_code == 200
    assert read_response.json()["content"] == ""


def test_smoke_core_api_contract(api_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "fw_use_cli", False)

    health_response = api_client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}

    ready_response = api_client.get("/ready")
    assert ready_response.status_code == 200, ready_response.text
    ready_payload = ready_response.json()
    assert ready_payload["status"] == "ready"
    assert "checks" in ready_payload
    assert "projects_path" in ready_payload["checks"]
    assert "catalog_path" in ready_payload["checks"]

    projects_response = api_client.get("/api/v1/projects")
    assert projects_response.status_code == 200, projects_response.text
    payload = projects_response.json()
    assert isinstance(payload, list)
    assert payload
    first = payload[0]
    assert "id" in first
    assert "name" in first
    assert "source_type" in first

    project_root = Path(settings.projects_path) / "demo"
    assert project_root.exists()
