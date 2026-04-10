from fastapi.testclient import TestClient
import pytest

from app.core.config import settings


def test_ready_returns_200_when_paths_writable_and_cli_disabled(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "fw_use_cli", False)

    response = api_client.get("/ready")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["checks"]["projects_path"]["ok"] is True
    assert payload["checks"]["catalog_path"]["ok"] is True
    assert payload["checks"]["fw_cli"]["ok"] is True


def test_ready_returns_503_when_fw_cli_is_required_but_missing(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "fw_use_cli", True)
    monkeypatch.setattr(settings, "fw_cli_command", "__dqcr_missing_cli__")

    response = api_client.get("/ready")

    assert response.status_code == 503, response.text
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["checks"]["fw_cli"]["ok"] is False
