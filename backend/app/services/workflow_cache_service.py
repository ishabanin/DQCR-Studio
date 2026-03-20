from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.fs import ensure_within_base

WORKFLOW_CACHE_DIR = Path(".dqcr_workflow_cache")
WORKFLOW_META_SUFFIX = ".meta.json"

WORKFLOW_STATUS_READY = "ready"
WORKFLOW_STATUS_STALE = "stale"
WORKFLOW_STATUS_BUILDING = "building"
WORKFLOW_STATUS_ERROR = "error"
WORKFLOW_STATUS_MISSING = "missing"

WORKFLOW_SOURCE_FRAMEWORK = "framework_cli"
WORKFLOW_SOURCE_FALLBACK = "fallback"

WORKFLOW_VALID_STATUSES = {
    WORKFLOW_STATUS_READY,
    WORKFLOW_STATUS_STALE,
    WORKFLOW_STATUS_BUILDING,
    WORKFLOW_STATUS_ERROR,
    WORKFLOW_STATUS_MISSING,
}


def workflow_cache_file(project_path: Path, model_id: str) -> Path:
    return ensure_within_base(project_path, project_path / WORKFLOW_CACHE_DIR / f"{model_id}.json")


def workflow_meta_file(project_path: Path, model_id: str) -> Path:
    return ensure_within_base(project_path, project_path / WORKFLOW_CACHE_DIR / f"{model_id}{WORKFLOW_META_SUFFIX}")


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_workflow_status(value: object, fallback: str = WORKFLOW_STATUS_MISSING) -> str:
    status_value = str(value).strip().lower() if isinstance(value, str) else ""
    if status_value in WORKFLOW_VALID_STATUSES:
        return status_value
    return fallback


def read_workflow_meta(project_path: Path, model_id: str) -> dict[str, object] | None:
    meta_file = workflow_meta_file(project_path, model_id)
    if not meta_file.exists() or not meta_file.is_file():
        return None
    try:
        payload = json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def write_workflow_meta(
    project_path: Path,
    model_id: str,
    *,
    status_value: str,
    error: str | None = None,
    source: str = WORKFLOW_SOURCE_FRAMEWORK,
    updated_at: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "project_id": project_path.name,
        "model_id": model_id,
        "status": normalize_workflow_status(status_value),
        "updated_at": updated_at or iso_now(),
        "source": source,
        "error": error,
    }
    meta_file = workflow_meta_file(project_path, model_id)
    meta_file.parent.mkdir(parents=True, exist_ok=True)
    meta_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def workflow_state_for_model(project_path: Path, model_id: str) -> dict[str, object]:
    cache_file = workflow_cache_file(project_path, model_id)
    cache_exists = cache_file.exists() and cache_file.is_file()
    meta = read_workflow_meta(project_path, model_id) or {}
    normalized_status = normalize_workflow_status(meta.get("status"), WORKFLOW_STATUS_READY if cache_exists else WORKFLOW_STATUS_MISSING)
    if not cache_exists and normalized_status == WORKFLOW_STATUS_READY:
        normalized_status = WORKFLOW_STATUS_MISSING

    updated_at_raw = meta.get("updated_at")
    updated_at = str(updated_at_raw).strip() if isinstance(updated_at_raw, str) and updated_at_raw.strip() else None
    error_raw = meta.get("error")
    error = str(error_raw) if isinstance(error_raw, str) and error_raw.strip() else None
    source_raw = meta.get("source")
    source = str(source_raw).strip() if isinstance(source_raw, str) and str(source_raw).strip() else WORKFLOW_SOURCE_FRAMEWORK
    if normalized_status in {WORKFLOW_STATUS_STALE, WORKFLOW_STATUS_ERROR} and cache_exists:
        source = WORKFLOW_SOURCE_FALLBACK

    return {
        "project_id": project_path.name,
        "model_id": model_id,
        "status": normalized_status,
        "updated_at": updated_at,
        "error": error,
        "source": source,
        "has_cache": cache_exists,
    }


def resolve_project_workflow_status(project_path: Path, model_ids: list[str]) -> dict[str, object]:
    models = [workflow_state_for_model(project_path, model_id) for model_id in model_ids]
    model_statuses = [str(item.get("status", WORKFLOW_STATUS_MISSING)) for item in models]
    if not models:
        project_status = WORKFLOW_STATUS_MISSING
    elif any(status_value == WORKFLOW_STATUS_ERROR for status_value in model_statuses):
        project_status = WORKFLOW_STATUS_ERROR
    elif any(status_value == WORKFLOW_STATUS_STALE for status_value in model_statuses):
        project_status = WORKFLOW_STATUS_STALE
    elif any(status_value == WORKFLOW_STATUS_BUILDING for status_value in model_statuses):
        project_status = WORKFLOW_STATUS_BUILDING
    elif any(status_value == WORKFLOW_STATUS_MISSING for status_value in model_statuses):
        project_status = WORKFLOW_STATUS_MISSING
    else:
        project_status = WORKFLOW_STATUS_READY

    return {
        "project_id": project_path.name,
        "status": project_status,
        "models": models,
    }


def read_workflow_cache(project_path: Path, model_id: str) -> dict[str, object] | None:
    cache_file = workflow_cache_file(project_path, model_id)
    if not cache_file.exists() or not cache_file.is_file():
        return None
    try:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def write_workflow_cache(project_path: Path, model_id: str, workflow_payload: dict[str, object]) -> None:
    cache_file = workflow_cache_file(project_path, model_id)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(workflow_payload, ensure_ascii=False, indent=2), encoding="utf-8")
