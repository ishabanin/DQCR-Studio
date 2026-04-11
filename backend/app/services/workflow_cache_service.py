from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.fs import ensure_within_base

WORKFLOW_CACHE_DIR = Path(".dqcr_workflow_cache")
WORKFLOW_META_SUFFIX = ".meta.json"
WORKFLOW_SCHEMA_VERSION = 1

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

WORKFLOW_REQUIRED_STEP_FIELDS = (
    "step_id",
    "step_scope",
    "step_type",
    "context",
    "enabled",
    "dependencies",
)


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


def _coerce_feature_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    features: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        feature = item.strip()
        if not feature or feature in seen:
            continue
        seen.add(feature)
        features.append(feature)
    return sorted(features)


def infer_payload_features(workflow_payload: dict[str, object]) -> list[str]:
    features: set[str] = set()
    steps = workflow_payload.get("steps")
    if isinstance(steps, list) and steps:
        features.add("steps")

    if isinstance(workflow_payload.get("all_contexts"), (list, dict)):
        features.add("all_contexts")
    if isinstance(workflow_payload.get("folders"), (list, dict)):
        features.add("folders")
    if isinstance(workflow_payload.get("project_properties"), dict):
        features.add("project_properties")
    if isinstance(workflow_payload.get("target_table"), dict):
        features.add("target_table")
    if isinstance(workflow_payload.get("config"), dict):
        features.add("config")
    if isinstance(workflow_payload.get("settings"), dict):
        features.add("settings")
    if isinstance(workflow_payload.get("graph"), (dict, list)):
        features.add("graph")
    if isinstance(workflow_payload.get("template"), dict):
        features.add("template")
    if isinstance(workflow_payload.get("sql_objects"), list):
        features.add("sql_objects")

    for step in steps if isinstance(steps, list) else []:
        if not isinstance(step, dict):
            continue
        if "dependencies" in step:
            features.add("step_dependencies")
        if "context" in step:
            features.add("step_context")
        if "tools" in step:
            features.add("step_tools")
        if "param_model" in step and isinstance(step.get("param_model"), dict):
            features.add("param_model")

        sql_model = step.get("sql_model")
        if isinstance(sql_model, dict):
            features.add("sql_model")
            if sql_model.get("source_sql") not in {None, ""}:
                features.add("sql_source")
            if isinstance(sql_model.get("prepared_sql"), dict):
                features.add("sql_prepared")
            if isinstance(sql_model.get("rendered_sql"), dict):
                features.add("sql_rendered")
            if isinstance(sql_model.get("metadata"), dict):
                features.add("sql_metadata")
            if isinstance(sql_model.get("cte_table_names"), dict):
                features.add("cte_table_names")

    return sorted(features)


def normalize_workflow_payload_contract(workflow_payload: dict[str, object]) -> tuple[dict[str, object], bool]:
    normalized = dict(workflow_payload)
    had_contract_metadata = "workflow_schema_version" in normalized and "payload_features" in normalized
    schema_version_raw = normalized.get("workflow_schema_version")
    normalized["workflow_schema_version"] = (
        int(schema_version_raw) if isinstance(schema_version_raw, int) and schema_version_raw > 0 else WORKFLOW_SCHEMA_VERSION
    )
    normalized["payload_features"] = _coerce_feature_list(normalized.get("payload_features")) or infer_payload_features(normalized)
    return normalized, had_contract_metadata


def build_workflow_diagnostics(
    workflow_payload: dict[str, object] | None,
    *,
    status: str,
    source: str,
    error: str | None,
    legacy_payload: bool,
) -> dict[str, object]:
    normalized_payload: dict[str, object] | None = None
    schema_version: int | None = None
    payload_features: list[str] = []
    steps: list[dict[str, object]] = []
    missing_fields: set[str] = set()

    if isinstance(workflow_payload, dict):
        normalized_payload, _ = normalize_workflow_payload_contract(workflow_payload)
        schema_version = int(normalized_payload["workflow_schema_version"])
        payload_features = list(normalized_payload.get("payload_features", []))
        raw_steps = normalized_payload.get("steps")
        if isinstance(raw_steps, list):
            steps = [step for step in raw_steps if isinstance(step, dict)]

    sql_steps = [step for step in steps if step.get("step_type") == "sql"]
    param_steps = [step for step in steps if step.get("step_type") == "param"]

    for index, step in enumerate(steps):
        for field_name in WORKFLOW_REQUIRED_STEP_FIELDS:
            if step.get(field_name) is None:
                missing_fields.add(f"steps[{index}].{field_name}")

    sql_with_model = 0
    sql_with_metadata = 0
    sql_with_source = 0
    sql_with_prepared = 0
    sql_with_rendered = 0

    for index, step in enumerate(sql_steps):
        sql_model = step.get("sql_model")
        if not isinstance(sql_model, dict):
            missing_fields.add(f"sql_steps[{index}].sql_model")
            continue
        sql_with_model += 1
        if sql_model.get("source_sql") not in {None, ""}:
            sql_with_source += 1
        else:
            missing_fields.add(f"sql_steps[{index}].sql_model.source_sql")
        if isinstance(sql_model.get("prepared_sql"), dict):
            sql_with_prepared += 1
        else:
            missing_fields.add(f"sql_steps[{index}].sql_model.prepared_sql")
        if isinstance(sql_model.get("rendered_sql"), dict):
            sql_with_rendered += 1
        else:
            missing_fields.add(f"sql_steps[{index}].sql_model.rendered_sql")
        if isinstance(sql_model.get("metadata"), dict):
            sql_with_metadata += 1
        else:
            missing_fields.add(f"sql_steps[{index}].sql_model.metadata")

    param_with_model = sum(1 for step in param_steps if isinstance(step.get("param_model"), dict))
    for index, step in enumerate(param_steps):
        if not isinstance(step.get("param_model"), dict):
            missing_fields.add(f"param_steps[{index}].param_model")

    issues: list[dict[str, str]] = []

    def add_issue(code: str, message: str) -> None:
        issues.append({"code": code, "message": message})

    if status == WORKFLOW_STATUS_MISSING:
        add_issue("workflow_missing", "Workflow cache is missing.")
    if status == WORKFLOW_STATUS_BUILDING:
        add_issue("workflow_building", "Workflow cache is currently rebuilding.")
    if status == WORKFLOW_STATUS_STALE:
        add_issue("stale_payload", "Workflow cache is stale and may be partially outdated.")
    if status == WORKFLOW_STATUS_ERROR:
        add_issue("workflow_error", "Workflow cache is unavailable because build failed.")
    if source == WORKFLOW_SOURCE_FALLBACK:
        add_issue("fallback_source", "IDE is using fallback data instead of a fresh framework payload.")
    if legacy_payload:
        add_issue("legacy_payload", "Workflow payload does not declare schema version and feature flags.")
    if sql_steps and (sql_with_source < len(sql_steps) or sql_with_prepared < len(sql_steps) or sql_with_rendered < len(sql_steps)):
        add_issue("missing_heavy_fields", "Some SQL steps are missing source/prepared/rendered SQL artifacts.")
    if steps and missing_fields:
        add_issue("contract_gaps", "Workflow payload is missing fields required for execution-aware UI.")
    if error:
        add_issue("build_error_detail", error)

    execution_ui_ready = bool(steps) and all(
        field in payload_features for field in ("steps", "step_context", "step_dependencies")
    ) and not any(issue["code"] in {"workflow_missing", "workflow_error"} for issue in issues)

    return {
        "schema_version": schema_version,
        "payload_features": payload_features,
        "legacy_payload": legacy_payload,
        "execution_ui_ready": execution_ui_ready,
        "issues": issues,
        "missing_fields": sorted(missing_fields),
        "coverage": {
            "steps_total": len(steps),
            "sql_steps_total": len(sql_steps),
            "sql_steps_with_sql_model": sql_with_model,
            "sql_steps_with_metadata": sql_with_metadata,
            "sql_steps_with_source_sql": sql_with_source,
            "sql_steps_with_prepared_sql": sql_with_prepared,
            "sql_steps_with_rendered_sql": sql_with_rendered,
            "param_steps_total": len(param_steps),
            "param_steps_with_param_model": param_with_model,
        },
    }


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
    workflow_payload: dict[str, object] | None = None,
) -> dict[str, object]:
    normalized_payload, legacy_payload = normalize_workflow_payload_contract(workflow_payload) if isinstance(workflow_payload, dict) else (None, False)
    payload: dict[str, object] = {
        "project_id": project_path.name,
        "model_id": model_id,
        "status": normalize_workflow_status(status_value),
        "updated_at": updated_at or iso_now(),
        "source": source,
        "error": error,
    }
    if isinstance(normalized_payload, dict):
        payload["workflow_schema_version"] = normalized_payload.get("workflow_schema_version")
        payload["payload_features"] = normalized_payload.get("payload_features")
    payload["diagnostics"] = build_workflow_diagnostics(
        normalized_payload,
        status=str(payload["status"]),
        source=source,
        error=error,
        legacy_payload=legacy_payload,
    )
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

    cache_payload = read_workflow_cache(project_path, model_id) if cache_exists else None
    normalized_payload, legacy_payload = normalize_workflow_payload_contract(cache_payload) if isinstance(cache_payload, dict) else (None, False)
    diagnostics = build_workflow_diagnostics(
        normalized_payload,
        status=normalized_status,
        source=source,
        error=error,
        legacy_payload=legacy_payload or not ("workflow_schema_version" in meta and "payload_features" in meta),
    )
    schema_version_raw = meta.get("workflow_schema_version")
    schema_version = (
        int(schema_version_raw)
        if isinstance(schema_version_raw, int) and schema_version_raw > 0
        else diagnostics.get("schema_version")
    )
    payload_features = _coerce_feature_list(meta.get("payload_features")) or list(diagnostics.get("payload_features", []))

    return {
        "project_id": project_path.name,
        "model_id": model_id,
        "status": normalized_status,
        "updated_at": updated_at,
        "error": error,
        "source": source,
        "has_cache": cache_exists,
        "workflow_schema_version": schema_version,
        "payload_features": payload_features,
        "diagnostics": diagnostics,
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
    normalized, _ = normalize_workflow_payload_contract(payload)
    return normalized


def write_workflow_cache(project_path: Path, model_id: str, workflow_payload: dict[str, object]) -> None:
    normalized_payload, _ = normalize_workflow_payload_contract(workflow_payload)
    cache_file = workflow_cache_file(project_path, model_id)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(normalized_payload, ensure_ascii=False, indent=2), encoding="utf-8")
