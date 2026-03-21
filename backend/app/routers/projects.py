import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import tempfile
import zipfile
from uuid import uuid4

from fastapi import APIRouter, Body, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import settings
from app.core.fs import ensure_within_base, resolve_project_path
from app.core.project_registry import (
    derive_link_availability,
    get_registry_entry,
    load_registry,
    save_registry,
    upsert_registry_entry,
)
from app.schemas.project import ContextSchema, ProjectSchema
from app.services import (
    FWService,
    TemplateRegistry,
    WORKFLOW_SOURCE_FALLBACK as _WORKFLOW_SOURCE_FALLBACK,
    WORKFLOW_SOURCE_FRAMEWORK as _WORKFLOW_SOURCE_FRAMEWORK,
    WORKFLOW_STATUS_BUILDING as _WORKFLOW_STATUS_BUILDING,
    WORKFLOW_STATUS_ERROR as _WORKFLOW_STATUS_ERROR,
    WORKFLOW_STATUS_MISSING as _WORKFLOW_STATUS_MISSING,
    WORKFLOW_STATUS_READY as _WORKFLOW_STATUS_READY,
    WORKFLOW_STATUS_STALE as _WORKFLOW_STATUS_STALE,
    read_workflow_cache as _read_workflow_cache,
    resolve_project_workflow_status as _resolve_project_workflow_status_core,
    workflow_cache_file as _workflow_cache_file,
    workflow_state_for_model as _workflow_state_for_model,
    write_workflow_cache as _write_workflow_cache,
    write_workflow_meta as _write_workflow_meta,
)

router = APIRouter(prefix="/projects", tags=["projects"])

DQCR_CONFIG_KEYS = [
    "enabled",
    "materialized",
    "target_table",
    "depends_on",
    "description",
    "schema",
    "engine",
    "tags",
]

DEFAULT_MACROS = [
    "ref",
    "source",
    "var",
    "env_var",
    "config",
    "adapter",
    "run_query",
]

PARAMETER_NAME_PATTERN = re.compile(r"^\s*name:\s*['\"]?([A-Za-z_][\w.]*)['\"]?\s*$", re.MULTILINE)
PARAMETER_DESCRIPTION_PATTERN = re.compile(r"^\s*description:\s*['\"]?([^\"\n]*)['\"]?\s*$", re.MULTILINE)
PARAMETER_DOMAIN_TYPE_PATTERN = re.compile(r"^\s*domain_type:\s*['\"]?([^'\"\n#]+)['\"]?\s*$", re.MULTILINE)
PARAMETER_VALUE_TYPE_PATTERN = re.compile(r"^\s*value_type:\s*['\"]?([^'\"\n#]+)['\"]?\s*$", re.MULTILINE)
PARAMETER_TYPE_PATTERN = re.compile(r"^\s*type:\s*['\"]?([^'\"\n#]+)['\"]?\s*$", re.MULTILINE)
INLINE_EXPR_PATTERN = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")
WITH_FIRST_CTE_PATTERN = re.compile(r"(?is)\bwith\s+([A-Za-z_][\w]*)\s+as\s*\(")
WITH_NEXT_CTE_PATTERN = re.compile(r"(?is),\s*([A-Za-z_][\w]*)\s+as\s*\(")
ENABLED_CONTEXTS_PATTERN = re.compile(r"^\s*contexts:\s*\[([^\]]*)\]\s*$", re.MULTILINE)
ENABLED_BOOL_PATTERN = re.compile(r"^\s*enabled:\s*(true|false)\s*$", re.MULTILINE | re.IGNORECASE)
INLINE_CONFIG_BLOCK_PATTERN = re.compile(r"@config\s*\((.*?)\)", re.IGNORECASE | re.DOTALL)
_VALIDATION_HISTORY: dict[str, list[dict[str, object]]] = {}
_BUILD_HISTORY: dict[str, list[dict[str, object]]] = {}
_SUPPORTED_BUILD_ENGINES = {"dqcr", "airflow", "oracle_plsql", "dbt"}
_BUILD_HISTORY_LIMIT = 10
PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{1,63}$")
LOGGER = logging.getLogger(__name__)


def _build_history_file(project_path: Path) -> Path:
    return ensure_within_base(project_path, project_path / ".dqcr_builds" / "history.json")


def _read_build_history_from_disk(project_path: Path) -> list[dict[str, object]]:
    history_file = _build_history_file(project_path)
    if not history_file.exists() or not history_file.is_file():
        return []
    try:
        raw = json.loads(history_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(raw, list):
        return []
    parsed: list[dict[str, object]] = []
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("build_id"), str):
            parsed.append(item)
    return parsed[:_BUILD_HISTORY_LIMIT]


def _write_build_history_to_disk(project_path: Path, history: list[dict[str, object]]) -> None:
    history_file = _build_history_file(project_path)
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history_file.write_text(
        json.dumps(history[:_BUILD_HISTORY_LIMIT], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _detect_model_from_generated_files(files: list[dict[str, object]], project_path: Path) -> str:
    candidate_paths: list[str] = []
    for item in files:
        raw = item.get("path")
        if isinstance(raw, str) and raw.strip():
            candidate_paths.append(raw.strip().replace("\\", "/"))
    if candidate_paths:
        first_parts = [Path(path).parts[0] for path in candidate_paths if Path(path).parts]
        unique = sorted(set(first_parts), key=str.lower)
        if len(unique) == 1 and unique[0]:
            return unique[0]
        if unique:
            return unique[0]
    model_ids = _list_model_ids(project_path)
    return model_ids[0] if model_ids else "unknown"


def _collect_generated_files_from_output_dir(output_dir: Path) -> list[dict[str, object]]:
    files: list[dict[str, object]] = []
    for file_path in sorted(output_dir.rglob("*"), key=lambda item: str(item).lower()):
        if not file_path.is_file():
            continue
        files.append(
            {
                "path": str(file_path.relative_to(output_dir)).replace("\\", "/"),
                "source_path": None,
                "size_bytes": file_path.stat().st_size,
            }
        )
    return files


def _discover_build_history_from_disk(project_id: str, project_path: Path) -> list[dict[str, object]]:
    candidates: list[Path] = []
    ignored_roots = {".git", "node_modules", ".venv", "__pycache__"}
    for candidate in project_path.rglob("bld-*"):
        if not candidate.is_dir():
            continue
        relative_parts = candidate.relative_to(project_path).parts
        if any(part in ignored_roots for part in relative_parts):
            continue
        candidates.append(candidate)

    if not candidates:
        return []

    discovered: list[dict[str, object]] = []
    seen: set[str] = set()
    for output_dir in sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True):
        relative_output = str(output_dir.relative_to(project_path)).replace("\\", "/")
        if relative_output in seen:
            continue
        seen.add(relative_output)
        files = _collect_generated_files_from_output_dir(output_dir)
        model_id = _detect_model_from_generated_files(files, project_path)
        mtime = datetime.fromtimestamp(output_dir.stat().st_mtime, tz=timezone.utc).isoformat()
        workflow_state = _workflow_state_for_model(project_path, model_id) if model_id and model_id != "unknown" else {}
        discovered.append(
            {
                "build_id": output_dir.name,
                "timestamp": mtime,
                "project": project_id,
                "model": model_id,
                "engine": "dqcr",
                "context": "default",
                "dry_run": False,
                "output_path": relative_output,
                "files_count": len(files),
                "files": files,
                "workflow_updated_at": _workflow_updated_at_for_model(project_path, model_id) if model_id and model_id != "unknown" else None,
                "workflow_status": workflow_state.get("status"),
                "workflow_source": workflow_state.get("source"),
                "workflow_attached": bool(workflow_state.get("has_cache")),
                "discovered_from_disk": True,
            }
        )
        if len(discovered) >= _BUILD_HISTORY_LIMIT:
            break
    return discovered[:_BUILD_HISTORY_LIMIT]


def _get_project_build_history(project_id: str) -> list[dict[str, object]]:
    cached = _BUILD_HISTORY.get(project_id)
    if cached is not None:
        return cached[:_BUILD_HISTORY_LIMIT]

    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    persisted = _read_build_history_from_disk(project_path)
    if not persisted:
        persisted = _discover_build_history_from_disk(project_id, project_path)
        if persisted:
            _write_build_history_to_disk(project_path, persisted)
    _BUILD_HISTORY[project_id] = persisted[:_BUILD_HISTORY_LIMIT]
    return _BUILD_HISTORY[project_id]


def _record_build_result(project_id: str, result: dict[str, object]) -> None:
    build_id = str(result.get("build_id", "")).strip()
    if not build_id:
        return
    history = list(_get_project_build_history(project_id))
    history = [item for item in history if str(item.get("build_id")) != build_id]
    history.insert(0, result)
    history = history[:_BUILD_HISTORY_LIMIT]
    _BUILD_HISTORY[project_id] = history

    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    _write_build_history_to_disk(project_path, history)


def _extract_parameter_name(raw: str) -> str | None:
    match = PARAMETER_NAME_PATTERN.search(raw)
    if not match:
        return None
    return match.group(1)


def _strip_yaml_scalar(value: str) -> str:
    trimmed = value.strip().rstrip(",")
    if len(trimmed) >= 2 and ((trimmed.startswith('"') and trimmed.endswith('"')) or (trimmed.startswith("'") and trimmed.endswith("'"))):
        return trimmed[1:-1]
    return trimmed


def _extract_parameter_description(raw: str) -> str:
    match = PARAMETER_DESCRIPTION_PATTERN.search(raw)
    if not match:
        return ""
    return _strip_yaml_scalar(match.group(1))


def _parse_parameter_values(raw: str) -> dict[str, dict[str, str]]:
    values: dict[str, dict[str, str]] = {}
    lines = raw.splitlines()
    in_values = False
    current_context: str | None = None

    for line in lines:
        if re.match(r"^\s*values:\s*$", line):
            in_values = True
            current_context = None
            continue

        if not in_values:
            continue

        if line.strip() and len(line) - len(line.lstrip(" ")) <= 2:
            in_values = False
            current_context = None
            continue

        context_match = re.match(r"^\s{4}([A-Za-z0-9_.-]+):\s*$", line)
        if context_match:
            current_context = context_match.group(1)
            values.setdefault(current_context, {"type": "static", "value": ""})
            continue

        if not current_context:
            continue

        type_match = re.match(r"^\s{6}type:\s*(.+?)\s*$", line)
        if type_match:
            values[current_context]["type"] = _strip_yaml_scalar(type_match.group(1)).lower()
            continue

        value_match = re.match(r"^\s{6}value:\s*(.+?)\s*$", line)
        if value_match:
            values[current_context]["value"] = _strip_yaml_scalar(value_match.group(1))

    return values


def _resolve_parameter_scope(project_path: Path, scope: str) -> str:
    normalized = scope.strip()
    if normalized == "global":
        return "global"
    if normalized.startswith("model:"):
        model_id = normalized.split(":", 1)[1].strip()
        if not model_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="scope must be 'global' or 'model:<model_id>'.")
        _ = _resolve_model_path(project_path, model_id)
        return f"model:{model_id}"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="scope must be 'global' or 'model:<model_id>'.")


def _parameter_file_for(project_path: Path, name: str, scope: str) -> Path:
    if scope == "global":
        target = project_path / "parameters" / f"{name}.yml"
        return ensure_within_base(project_path, target)

    model_id = scope.split(":", 1)[1]
    target = project_path / "model" / model_id / "parameters" / f"{name}.yml"
    return ensure_within_base(project_path, target)


def _extract_scope_from_parameter_path(project_path: Path, file_path: Path) -> str:
    relative = file_path.relative_to(project_path)
    parts = list(relative.parts)
    if len(parts) >= 2 and parts[0] == "parameters":
        return "global"
    if len(parts) >= 4 and parts[0] == "model" and parts[2] == "parameters":
        return f"model:{parts[1]}"
    return "global"


def _parse_parameter_file(project_path: Path, file_path: Path) -> dict[str, object]:
    raw = file_path.read_text(encoding="utf-8")
    name = _extract_parameter_name(raw) or file_path.stem
    description = _extract_parameter_description(raw)
    domain_type, value_type = _extract_parameter_meta(raw)
    values = _parse_parameter_values(raw)
    scope = _extract_scope_from_parameter_path(project_path, file_path)

    if value_type is None:
        detected_types = {item.get("type", "static") for item in values.values()}
        if "dynamic" in detected_types:
            value_type = "dynamic"
        elif detected_types:
            value_type = sorted(detected_types)[0]
        else:
            value_type = "static"

    return {
        "name": name,
        "scope": scope,
        "path": str(file_path.relative_to(project_path)),
        "description": description,
        "domain_type": domain_type or "string",
        "value_type": value_type,
        "values": values,
    }


def _collect_parameter_objects(project_path: Path) -> list[dict[str, object]]:
    files: list[Path] = []
    global_params_dir = project_path / "parameters"
    if global_params_dir.exists():
        files.extend(sorted(global_params_dir.glob("*.yml"), key=lambda p: p.name.lower()))

    model_dir = project_path / "model"
    if model_dir.exists():
        files.extend(sorted(model_dir.glob("*/parameters/*.yml"), key=lambda p: str(p).lower()))

    return sorted(
        [_parse_parameter_file(project_path, file_path) for file_path in files],
        key=lambda item: (str(item["name"]).lower(), str(item["scope"]).lower()),
    )


def _validate_parameter_name(name: str) -> str:
    candidate = name.strip()
    if not re.match(r"^[A-Za-z_][\w.]*$", candidate):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="parameter name must match ^[A-Za-z_][\\w.]*$",
        )
    return candidate


def _normalize_parameter_values(values_raw: object) -> dict[str, dict[str, str]]:
    if not isinstance(values_raw, dict):
        return {"all": {"type": "static", "value": ""}}

    normalized: dict[str, dict[str, str]] = {}
    for key, value in values_raw.items():
        if not isinstance(key, str) or not key.strip():
            continue
        context = key.strip()
        row = value if isinstance(value, dict) else {}
        value_type_raw = row.get("type", "static") if isinstance(row, dict) else "static"
        value_type = str(value_type_raw).strip().lower()
        if value_type not in {"static", "dynamic"}:
            value_type = "static"
        value_value_raw = row.get("value", "") if isinstance(row, dict) else ""
        normalized[context] = {"type": value_type, "value": str(value_value_raw)}

    if not normalized:
        normalized["all"] = {"type": "static", "value": ""}
    return normalized


def _render_parameter_yaml(payload: dict[str, object]) -> str:
    name = _validate_parameter_name(str(payload.get("name", "")))
    description = str(payload.get("description", "")).replace('"', '\\"')
    domain_type = str(payload.get("domain_type", "string")).strip() or "string"
    values = _normalize_parameter_values(payload.get("values"))

    lines = [
        "parameter:",
        f"  name: {name}",
        f'  description: "{description}"',
        f"  domain_type: {domain_type}",
        "",
        "  values:",
    ]

    for context, row in values.items():
        row_type = row.get("type", "static")
        row_value = row.get("value", "").replace('"', '\\"')
        lines.extend(
            [
                f"    {context}:",
                f"      type: {row_type}",
                f'      value: "{row_value}"',
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def _resolve_parameter_candidates(project_path: Path, parameter_id: str) -> list[Path]:
    candidates: list[Path] = []
    global_path = project_path / "parameters" / f"{parameter_id}.yml"
    if global_path.exists() and global_path.is_file():
        candidates.append(ensure_within_base(project_path, global_path))

    model_dir = project_path / "model"
    if model_dir.exists():
        for local_file in sorted(model_dir.glob(f"*/parameters/{parameter_id}.yml"), key=lambda p: str(p).lower()):
            if local_file.is_file():
                candidates.append(ensure_within_base(project_path, local_file))

    return candidates


def _resolve_parameter_file(project_path: Path, parameter_id: str, scope: str | None) -> Path:
    safe_id = _validate_parameter_name(parameter_id)
    if scope:
        normalized_scope = _resolve_parameter_scope(project_path, scope)
        target = _parameter_file_for(project_path, safe_id, normalized_scope)
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Parameter '{safe_id}' not found in scope '{normalized_scope}'.")
        return target

    candidates = _resolve_parameter_candidates(project_path, safe_id)
    if not candidates:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Parameter '{safe_id}' not found.")
    if len(candidates) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Parameter '{safe_id}' exists in multiple scopes. Provide 'scope' query param.",
        )
    return candidates[0]


def _extract_parameter_meta(raw: str) -> tuple[str | None, str | None]:
    domain_type_match = PARAMETER_DOMAIN_TYPE_PATTERN.search(raw)
    value_type_match = PARAMETER_VALUE_TYPE_PATTERN.search(raw)
    loose_type_match = PARAMETER_TYPE_PATTERN.search(raw)

    domain_type = domain_type_match.group(1).strip() if domain_type_match else None
    value_type = value_type_match.group(1).strip() if value_type_match else None

    if value_type is None and loose_type_match:
        candidate = loose_type_match.group(1).strip().lower()
        if candidate in {"static", "dynamic"}:
            value_type = candidate

    if value_type is None:
        if re.search(r"(?im)^\s*(sql|query|dynamic_sql)\s*:", raw):
            value_type = "dynamic"
        elif re.search(r"(?im)^\s*(value|default)\s*:", raw):
            value_type = "static"

    return domain_type, value_type


def _extract_materialized(folder_yml_path: Path) -> str | None:
    if not folder_yml_path.exists():
        return None
    raw = folder_yml_path.read_text(encoding="utf-8")
    match = re.search(r"^\s*materialized:\s*([A-Za-z_][\w.]*)\s*$", raw, re.MULTILINE)
    if not match:
        return None
    return match.group(1)


def _extract_enabled_contexts(folder_yml_path: Path) -> list[str] | None:
    if not folder_yml_path.exists():
        return None

    raw = folder_yml_path.read_text(encoding="utf-8")
    contexts_match = ENABLED_CONTEXTS_PATTERN.search(raw)
    if contexts_match:
        raw_items = contexts_match.group(1).split(",")
        contexts = [item.strip().strip("'\"") for item in raw_items if item.strip()]
        return contexts if contexts else None

    bool_match = ENABLED_BOOL_PATTERN.search(raw)
    if bool_match and bool_match.group(1).lower() == "false":
        return []

    return None


def _collect_sql_files(folder_path: Path) -> list[str]:
    return [item.name for item in sorted(folder_path.glob("*.sql"), key=lambda p: p.name.lower())]


def _resolve_model_path(project_path: Path, model_id: str) -> Path:
    model_root = project_path / "model"
    model_path = model_root / model_id
    if not model_path.exists() or not model_path.is_dir():
        raise ValueError(f"Model '{model_id}' not found.")
    return model_path


def _detect_workflow_root(model_path: Path) -> Path:
    sql_root = model_path / "SQL"
    workflow_root = model_path / "workflow"
    if sql_root.exists() and sql_root.is_dir():
        return sql_root
    if workflow_root.exists() and workflow_root.is_dir():
        return workflow_root
    raise ValueError(f"Model '{model_path.name}' has no SQL/workflow folders.")


def _collect_lineage_nodes(project_path: Path, model_id: str) -> tuple[list[dict[str, object]], int]:
    model_path = _resolve_model_path(project_path, model_id)
    workflow_root = _detect_workflow_root(model_path)
    model_yml_path = model_path / "model.yml"
    nodes: list[dict[str, object]] = []
    unique_params: set[str] = set()
    ordered_folders: list[Path] = []
    seen_folder_names: set[str] = set()

    if model_yml_path.exists() and model_yml_path.is_file():
        model_obj = _parse_model_yml_to_object(model_yml_path)
        workflow = model_obj.get("workflow")
        workflow_folders = workflow.get("folders") if isinstance(workflow, dict) else None
        if isinstance(workflow_folders, list):
            for item in workflow_folders:
                if not isinstance(item, dict):
                    continue
                folder_id = str(item.get("id", "")).strip()
                if not folder_id or folder_id in seen_folder_names:
                    continue
                folder_path = workflow_root / folder_id
                if folder_path.exists() and folder_path.is_dir():
                    ordered_folders.append(folder_path)
                    seen_folder_names.add(folder_id)

    for folder in sorted(workflow_root.iterdir(), key=lambda p: p.name.lower()):
        if not folder.is_dir():
            continue
        if folder.name in seen_folder_names:
            continue
        ordered_folders.append(folder)
        seen_folder_names.add(folder.name)

    for folder in ordered_folders:
        sql_files = _collect_sql_files(folder)
        folder_params: set[str] = set()
        folder_ctes: set[str] = set()
        for sql_file in sql_files:
            sql_path = folder / sql_file
            raw_sql = sql_path.read_text(encoding="utf-8")
            for match in INLINE_EXPR_PATTERN.findall(raw_sql):
                expr = match.strip()
                if "(" in expr:
                    continue
                if not expr:
                    continue
                token = expr.split()[0]
                unique_params.add(token)
                folder_params.add(token)

            first_cte = WITH_FIRST_CTE_PATTERN.findall(raw_sql)
            next_ctes = WITH_NEXT_CTE_PATTERN.findall(raw_sql)
            for cte_name in [*first_cte, *next_ctes]:
                folder_ctes.add(cte_name)

        materialized = _extract_materialized(folder / "folder.yml")
        enabled_contexts = _extract_enabled_contexts(folder / "folder.yml")
        relative_folder = folder.relative_to(project_path)
        nodes.append(
            {
                "id": folder.name,
                "name": folder.name,
                "path": str(relative_folder),
                "materialized": materialized or "n/a",
                "enabled_contexts": enabled_contexts,
                "queries": sql_files,
                "parameters": sorted(folder_params),
                "ctes": sorted(folder_ctes),
            }
        )

    return nodes, len(unique_params)


def _collect_lineage_edges(nodes: list[dict[str, object]]) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for idx in range(len(nodes) - 1):
        source = str(nodes[idx]["id"])
        target = str(nodes[idx + 1]["id"])
        edges.append(
            {
                "id": f"{source}->{target}",
                "source": source,
                "target": target,
                "status": "resolved",
            }
        )
    return edges


def _extract_scalar_value(raw: str, key: str) -> str | None:
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*:\s*(.+?)\s*$", re.MULTILINE)
    match = pattern.search(raw)
    if not match:
        return None

    value = match.group(1).strip().rstrip(",")
    if not value or value.startswith("#"):
        return None

    return value.strip("'\"")


def _extract_yaml_level_values(path: Path | None) -> dict[str, str | None]:
    values = {key: None for key in DQCR_CONFIG_KEYS}
    if path is None or not path.exists() or not path.is_file():
        return values

    raw = path.read_text(encoding="utf-8")
    for key in DQCR_CONFIG_KEYS:
        values[key] = _extract_scalar_value(raw, key)
    return values


def _extract_inline_config_values(sql_path: Path | None) -> dict[str, str | None]:
    values = {key: None for key in DQCR_CONFIG_KEYS}
    if sql_path is None or not sql_path.exists() or not sql_path.is_file():
        return values

    raw = sql_path.read_text(encoding="utf-8")
    match = INLINE_CONFIG_BLOCK_PATTERN.search(raw)
    if not match:
        return values

    block_body = match.group(1)
    for key in DQCR_CONFIG_KEYS:
        pair_pattern = re.compile(rf"\b{re.escape(key)}\b\s*[:=]\s*([^,\n]+)")
        pair_match = pair_pattern.search(block_body)
        if pair_match:
            values[key] = pair_match.group(1).strip().strip("'\"")
    return values


def _as_relative_path(project_path: Path, target_path: Path | None) -> str | None:
    if target_path is None:
        return None
    try:
        return str(target_path.relative_to(project_path))
    except ValueError:
        return str(target_path)


def _resolve_sql_path(project_path: Path, relative_sql_path: str | None) -> Path | None:
    if not relative_sql_path:
        return None
    return ensure_within_base(project_path, project_path / relative_sql_path)


def _resolve_folder_yaml_path(sql_path: Path | None) -> Path | None:
    if sql_path is None:
        return None
    return sql_path.parent / "folder.yml"


def _normalize_path_for_compare(path: str | None) -> str:
    if not path:
        return ""
    return path.replace("\\", "/").strip().lstrip("./")


def _extract_config_values_from_map(raw: object) -> dict[str, str | None]:
    if not isinstance(raw, dict):
        return {key: None for key in DQCR_CONFIG_KEYS}
    result = {key: None for key in DQCR_CONFIG_KEYS}
    for key in DQCR_CONFIG_KEYS:
        value = raw.get(key)
        if value is not None:
            result[key] = str(value)
    return result


def _extract_sql_metadata_from_step(sql_step: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(sql_step, dict):
        return {"parameters": [], "ctes": [], "inline_cte_configs": {}}

    sql_model_raw = sql_step.get("sql_model")
    sql_model = sql_model_raw if isinstance(sql_model_raw, dict) else {}
    metadata_raw = sql_model.get("metadata")
    metadata = metadata_raw if isinstance(metadata_raw, dict) else {}

    parameters: list[str] = []
    parameters_raw = metadata.get("parameters")
    if isinstance(parameters_raw, list):
        for item in parameters_raw:
            if isinstance(item, str) and item.strip():
                parameters.append(item.strip())

    ctes: list[str] = []
    cte_raw = metadata.get("cte")
    if isinstance(cte_raw, dict):
        for cte_name in cte_raw.keys():
            if isinstance(cte_name, str) and cte_name.strip():
                ctes.append(cte_name.strip())

    inline_cte_configs: dict[str, str] = {}
    inline_raw = metadata.get("inline_cte_configs")
    if isinstance(inline_raw, dict):
        for key, value in inline_raw.items():
            if isinstance(key, str) and key.strip():
                inline_cte_configs[key.strip()] = "" if value is None else str(value)

    return {
        "parameters": sorted(set(parameters)),
        "ctes": sorted(set(ctes)),
        "inline_cte_configs": inline_cte_configs,
    }


def _extract_folder_from_relative_sql(relative_sql_path: str | None) -> str | None:
    if not relative_sql_path:
        return None
    parts = [part for part in relative_sql_path.replace("\\", "/").split("/") if part]
    if len(parts) >= 5 and parts[0] == "model" and parts[3] == "workflow":
        return parts[4]
    return None


def _extract_cte_settings_from_workflow(workflow_payload: dict[str, object]) -> dict[str, object]:
    config_raw = workflow_payload.get("config")
    if not isinstance(config_raw, dict):
        return {"default": None, "by_context": {}}
    cte_raw = config_raw.get("cte")
    if not isinstance(cte_raw, dict):
        return {"default": None, "by_context": {}}

    default_raw = cte_raw.get("cte_materialization")
    default_value = str(default_raw).strip() if isinstance(default_raw, str) and default_raw.strip() else None
    by_context: dict[str, str] = {}
    by_context_raw = cte_raw.get("by_context")
    if isinstance(by_context_raw, dict):
        for key, value in by_context_raw.items():
            if isinstance(key, str) and isinstance(value, str) and key.strip() and value.strip():
                by_context[key.strip()] = value.strip()
    return {"default": default_value, "by_context": by_context}


def _build_config_chain_response_workflow(
    project_path: Path,
    project_id: str,
    model_id: str,
    relative_sql_path: str | None,
    workflow_payload: dict[str, object],
) -> dict[str, object]:
    config_raw = workflow_payload.get("config")
    config = config_raw if isinstance(config_raw, dict) else {}
    folders_raw = config.get("folders")
    folder_map = folders_raw if isinstance(folders_raw, dict) else {}
    folder_id = _extract_folder_from_relative_sql(relative_sql_path)
    folder_cfg = folder_map.get(folder_id) if isinstance(folder_map, dict) and isinstance(folder_id, str) else None

    selected_sql_step: dict[str, object] | None = None
    steps_raw = workflow_payload.get("steps")
    steps = [item for item in steps_raw if isinstance(item, dict)] if isinstance(steps_raw, list) else []
    normalized_target = _normalize_path_for_compare(relative_sql_path)
    if normalized_target:
        for step in steps:
            if str(step.get("step_type", "")).lower() != "sql":
                continue
            sql_model_raw = step.get("sql_model")
            sql_model = sql_model_raw if isinstance(sql_model_raw, dict) else {}
            candidate_path_raw = sql_model.get("path")
            candidate_path = str(candidate_path_raw).strip() if isinstance(candidate_path_raw, str) else ""
            if not candidate_path:
                continue
            if _normalize_path_for_compare(candidate_path).endswith(normalized_target):
                selected_sql_step = step
                break

    sql_level_values = {key: None for key in DQCR_CONFIG_KEYS}
    if isinstance(selected_sql_step, dict):
        step_cfg = selected_sql_step.get("config")
        if isinstance(step_cfg, dict):
            sql_level_values = _extract_config_values_from_map(step_cfg)
        else:
            sql_model_raw = selected_sql_step.get("sql_model")
            sql_model = sql_model_raw if isinstance(sql_model_raw, dict) else {}
            sql_level_values = _extract_config_values_from_map(sql_model.get("config"))
    sql_metadata = _extract_sql_metadata_from_step(selected_sql_step)

    model_level_values = _extract_config_values_from_map(config)
    folder_level_values = _extract_config_values_from_map(folder_cfg)
    levels: list[dict[str, object]] = [
        {
            "id": "template",
            "label": "Template",
            "source_path": None,
            "values": {key: None for key in DQCR_CONFIG_KEYS},
        },
        {
            "id": "project",
            "label": "Project",
            "source_path": "project.yml",
            "values": {key: None for key in DQCR_CONFIG_KEYS},
        },
        {
            "id": "model",
            "label": "Model",
            "source_path": f"model/{model_id}/model.yml",
            "values": model_level_values,
        },
        {
            "id": "folder",
            "label": "Folder",
            "source_path": relative_sql_path,
            "values": folder_level_values,
        },
        {
            "id": "sql",
            "label": "SQL @config",
            "source_path": relative_sql_path,
            "values": sql_level_values,
        },
    ]

    precedence = ["sql", "folder", "model", "project", "template"]
    levels_by_id = {str(level["id"]): level for level in levels}
    resolved: list[dict[str, object]] = []
    for key in DQCR_CONFIG_KEYS:
        selected_level = "template"
        selected_value: str | None = None
        overridden_levels: list[str] = []
        for level_id in precedence:
            values = levels_by_id[level_id]["values"]
            if not isinstance(values, dict):
                continue
            value = values.get(key)
            if value is not None:
                selected_level = level_id
                selected_value = str(value)
                break
        for level_id in precedence:
            if level_id == selected_level:
                continue
            values = levels_by_id[level_id]["values"]
            if isinstance(values, dict) and values.get(key) is not None:
                overridden_levels.append(level_id)
        resolved.append(
            {
                "key": key,
                "value": selected_value,
                "source_level": selected_level,
                "overridden_levels": overridden_levels,
            }
        )

    workflow_state = _workflow_state_for_model(project_path, model_id)
    return {
        "project_id": project_id,
        "model_id": model_id,
        "sql_path": relative_sql_path,
        "levels": levels,
        "resolved": resolved,
        "cte_settings": _extract_cte_settings_from_workflow(workflow_payload),
        "generated_outputs": ["dqcr", "airflow", "oracle_plsql", "dbt"],
        "data_source": "workflow",
        "fallback": False,
        "sql_metadata": sql_metadata,
        "workflow_status": workflow_state.get("status"),
        "workflow_source": workflow_state.get("source"),
        "workflow_updated_at": workflow_state.get("updated_at"),
    }


def _build_config_chain_response_fallback(
    project_path: Path, project_id: str, model_id: str, relative_sql_path: str | None
) -> dict[str, object]:
    model_path = _resolve_model_path(project_path, model_id)
    sql_path = _resolve_sql_path(project_path, relative_sql_path)
    folder_cfg_path = _resolve_folder_yaml_path(sql_path)

    template_cfg_path = model_path / "template.yml"
    project_cfg_path = project_path / "project.yml"
    model_cfg_path = model_path / "model.yml"

    levels: list[dict[str, object]] = [
        {
            "id": "template",
            "label": "Template",
            "source_path": _as_relative_path(project_path, template_cfg_path),
            "values": _extract_yaml_level_values(template_cfg_path),
        },
        {
            "id": "project",
            "label": "Project",
            "source_path": _as_relative_path(project_path, project_cfg_path),
            "values": _extract_yaml_level_values(project_cfg_path),
        },
        {
            "id": "model",
            "label": "Model",
            "source_path": _as_relative_path(project_path, model_cfg_path),
            "values": _extract_yaml_level_values(model_cfg_path),
        },
        {
            "id": "folder",
            "label": "Folder",
            "source_path": _as_relative_path(project_path, folder_cfg_path),
            "values": _extract_yaml_level_values(folder_cfg_path),
        },
        {
            "id": "sql",
            "label": "SQL @config",
            "source_path": _as_relative_path(project_path, sql_path) if sql_path else relative_sql_path,
            "values": _extract_inline_config_values(sql_path),
        },
    ]

    precedence = ["sql", "folder", "model", "project", "template"]
    levels_by_id = {str(level["id"]): level for level in levels}
    resolved: list[dict[str, object]] = []
    for key in DQCR_CONFIG_KEYS:
        selected_level = "template"
        selected_value: str | None = None
        overridden_levels: list[str] = []
        for level_id in precedence:
            values = levels_by_id[level_id]["values"]
            if not isinstance(values, dict):
                continue
            value = values.get(key)
            if value is not None:
                selected_level = level_id
                selected_value = str(value)
                break

        for level_id in precedence:
            if level_id == selected_level:
                continue
            values = levels_by_id[level_id]["values"]
            if isinstance(values, dict) and values.get(key) is not None:
                overridden_levels.append(level_id)

        resolved.append(
            {
                "key": key,
                "value": selected_value,
                "source_level": selected_level,
                "overridden_levels": overridden_levels,
            }
        )

    response = {
        "project_id": project_id,
        "model_id": model_id,
        "sql_path": relative_sql_path,
        "levels": levels,
        "resolved": resolved,
        "cte_settings": _extract_cte_settings(model_cfg_path),
        "generated_outputs": ["dqcr", "airflow", "oracle_plsql", "dbt"],
        "data_source": "fallback",
        "fallback": True,
        "sql_metadata": {
            "parameters": [],
            "ctes": [],
            "inline_cte_configs": {},
        },
    }
    return response


def _build_config_chain_response(
    project_path: Path, project_id: str, model_id: str, relative_sql_path: str | None
) -> dict[str, object]:
    workflow_payload = _ensure_workflow_payload(project_id, model_id, force_rebuild=False)
    if isinstance(workflow_payload, dict):
        try:
            return _build_config_chain_response_workflow(project_path, project_id, model_id, relative_sql_path, workflow_payload)
        except Exception:
            LOGGER.exception(
                "workflow.config_chain.fallback project_id=%s model_id=%s",
                project_id,
                model_id,
            )
            _log_workflow_fallback(
                endpoint="config-chain",
                project_id=project_id,
                model_id=model_id,
                reason="workflow_response_build_failed",
            )
    else:
        _log_workflow_fallback(
            endpoint="config-chain",
            project_id=project_id,
            model_id=model_id,
            reason="workflow_payload_missing",
        )
    return _build_config_chain_response_fallback(project_path, project_id, model_id, relative_sql_path)


def _extract_cte_settings(model_cfg_path: Path) -> dict[str, object]:
    if not model_cfg_path.exists() or not model_cfg_path.is_file():
        return {"default": None, "by_context": {}}

    raw = model_cfg_path.read_text(encoding="utf-8")

    default_match = re.search(r"(?im)^\s*(cte_default|cte_materialization_default|default)\s*:\s*([^\n#]+)\s*$", raw)
    default_value = default_match.group(2).strip().strip("'\"") if default_match else None

    by_context: dict[str, str] = {}
    block_match = re.search(r"(?is)^\s*by_context\s*:\s*\n((?:\s{2,}[^\n]+\n?)*)", raw, re.MULTILINE)
    if block_match:
        for line in block_match.group(1).splitlines():
            pair = re.match(r"^\s*([A-Za-z0-9_.-]+)\s*:\s*([^\n#]+)\s*$", line)
            if pair:
                by_context[pair.group(1)] = pair.group(2).strip().strip("'\"")

    return {"default": default_value, "by_context": by_context}


def _render_engine_preview_sql(raw_sql: str, engine: str) -> str:
    normalized = raw_sql.strip()
    if engine == "oracle_plsql":
        return "\n".join(
            [
                "BEGIN",
                "  EXECUTE IMMEDIATE q'[",
                normalized,
                "]';",
                "END;",
                "/",
            ]
        )
    if engine == "airflow":
        return f"-- airflow.sql preview\n{normalized}"
    if engine == "dbt":
        return f"-- dbt model preview\n{normalized}"
    return normalized


def _list_sql_files_for_model(project_path: Path, model_id: str) -> list[Path]:
    model_path = _resolve_model_path(project_path, model_id)
    workflow_root = _detect_workflow_root(model_path)
    return sorted(workflow_root.rglob("*.sql"), key=lambda item: str(item).lower())


def _resolve_model_id_for_build(project_path: Path, explicit_model_id: str | None) -> str:
    return _resolve_model_id_for_validation(project_path, explicit_model_id)


def _resolve_build_output_dir(project_path: Path, build_id: str, output_path: str | None) -> Path:
    if output_path and output_path.strip():
        safe_target = ensure_within_base(project_path, project_path / output_path.strip())
        return ensure_within_base(project_path, safe_target / build_id)
    return ensure_within_base(project_path, project_path / ".dqcr_builds" / build_id)


def _workflow_updated_at_for_model(project_path: Path, model_id: str) -> str | None:
    state = _workflow_state_for_model(project_path, model_id)
    value = state.get("updated_at")
    return str(value) if isinstance(value, str) and value.strip() else None


def _attach_workflow_context(
    payload: dict[str, object],
    project_path: Path,
    model_id: str,
) -> dict[str, object]:
    state = _workflow_state_for_model(project_path, model_id)
    result = dict(payload)
    result["workflow_updated_at"] = _workflow_updated_at_for_model(project_path, model_id)
    result["workflow_status"] = state.get("status")
    result["workflow_source"] = state.get("source")
    result["workflow_attached"] = bool(state.get("has_cache"))
    return result


def _run_project_generation(
    project_path: Path,
    project_id: str,
    model_id: str,
    engine: str,
    context: str,
    dry_run: bool,
    output_path: str | None,
) -> dict[str, object]:
    if engine not in _SUPPORTED_BUILD_ENGINES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported engine '{engine}'.")

    sql_files = _list_sql_files_for_model(project_path, model_id)
    build_id = f"bld-{uuid4().hex[:8]}"
    output_dir = _resolve_build_output_dir(project_path, build_id, output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_files: list[dict[str, object]] = []
    timestamp = datetime.now(timezone.utc).isoformat()
    header = "\n".join(
        [
            f"-- build_id: {build_id}",
            f"-- generated_at: {timestamp}",
            f"-- engine: {engine}",
            f"-- context: {context}",
            "",
        ]
    )

    for sql_file in sql_files:
        relative_sql = sql_file.relative_to(project_path)
        relative_generated = Path(model_id) / relative_sql.relative_to(Path("model") / model_id)
        target_file = ensure_within_base(output_dir, output_dir / relative_generated)
        target_file.parent.mkdir(parents=True, exist_ok=True)

        raw_sql = sql_file.read_text(encoding="utf-8")
        rendered_sql = _render_engine_preview_sql(raw_sql, engine)
        if dry_run:
            rendered = f"{header}-- dry_run: true\n{rendered_sql}"
        else:
            rendered = f"{header}{rendered_sql}"
            target_file.write_text(rendered, encoding="utf-8")

        generated_files.append(
            {
                "path": str(relative_generated),
                "source_path": str(relative_sql),
                "size_bytes": len(rendered.encode("utf-8")),
            }
        )

    if dry_run:
        output_path_relative = str(output_dir.relative_to(project_path))
    else:
        output_path_relative = str(output_dir.relative_to(project_path))

    workflow_payload = _ensure_workflow_payload(project_id, model_id, force_rebuild=False)
    workflow_state = _workflow_state_for_model(project_path, model_id)
    result = {
        "build_id": build_id,
        "timestamp": timestamp,
        "project": project_id,
        "model": model_id,
        "engine": engine,
        "context": context,
        "dry_run": dry_run,
        "output_path": output_path_relative,
        "files_count": len(generated_files),
        "files": generated_files,
        "workflow_updated_at": _workflow_updated_at_for_model(project_path, model_id),
        "workflow_status": workflow_state.get("status"),
        "workflow_source": workflow_state.get("source"),
        "workflow_attached": isinstance(workflow_payload, dict),
    }
    _record_build_result(project_id, result)
    return result


def _find_project_build(project_id: str, build_id: str) -> dict[str, object]:
    for item in _get_project_build_history(project_id):
        if str(item.get("build_id")) == build_id:
            return item
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Build '{build_id}' not found.")


def _resolve_existing_build_output_dir(project_id: str, build_id: str) -> Path:
    build_item = _find_project_build(project_id, build_id)
    output_path_raw = build_item.get("output_path")
    if not isinstance(output_path_raw, str) or not output_path_raw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Build '{build_id}' has no output path.")

    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    output_dir = ensure_within_base(project_path, project_path / output_path_raw)
    if not output_dir.exists() or not output_dir.is_dir():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Build '{build_id}' output not found on disk.")
    return output_dir


def _build_files_tree(items: list[dict[str, object]]) -> dict[str, object]:
    root: dict[str, object] = {"name": "root", "path": "", "type": "directory", "children": []}

    for item in items:
        raw_path = item.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            continue
        parts = [part for part in Path(raw_path).parts if part not in {"", "."}]
        cursor = root
        children = cursor.setdefault("children", [])
        if not isinstance(children, list):
            continue
        for idx, part in enumerate(parts):
            is_last = idx == len(parts) - 1
            existing = next((node for node in children if node.get("name") == part), None)
            if existing is None:
                existing = {
                    "name": part,
                    "path": str(Path(*parts[: idx + 1])),
                    "type": "file" if is_last else "directory",
                }
                if not is_last:
                    existing["children"] = []
                children.append(existing)
            if is_last:
                existing["size_bytes"] = item.get("size_bytes")
                existing["source_path"] = item.get("source_path")
            else:
                if "children" not in existing:
                    existing["children"] = []
                next_children = existing["children"]
                if not isinstance(next_children, list):
                    existing["children"] = []
                children = existing["children"]

    return root


def _build_validation_result(
    project_path: Path,
    project_id: str,
    model_id: str,
    categories: list[str] | None,
) -> dict[str, object]:
    workflow_payload = _ensure_workflow_payload(project_id, model_id, force_rebuild=False)
    workflow_state = _workflow_state_for_model(project_path, model_id)
    sql_files = _list_sql_files_for_model(project_path, model_id)
    allowed_categories = set(categories or ["general", "sql", "descriptions", "adb", "oracle", "postgresql"])
    rules: list[dict[str, object]] = []

    for sql_file in sql_files:
        relative = str(sql_file.relative_to(project_path))
        raw = sql_file.read_text(encoding="utf-8")
        trimmed = raw.strip()
        lower = trimmed.lower()

        if "general" in allowed_categories:
            rules.append(
                {
                    "rule_id": "general.sql_file_exists",
                    "name": f"{sql_file.name}: file exists",
                    "status": "pass",
                    "message": "SQL file is available.",
                    "file_path": relative,
                    "line": 1,
                }
            )

        if "sql" in allowed_categories:
            if not trimmed:
                rules.append(
                    {
                        "rule_id": "sql.non_empty",
                        "name": f"{sql_file.name}: non-empty query",
                        "status": "error",
                        "message": "SQL file is empty.",
                        "file_path": relative,
                        "line": 1,
                    }
                )
            elif "select" not in lower and "insert" not in lower and "update" not in lower and "delete" not in lower:
                rules.append(
                    {
                        "rule_id": "sql.statement_shape",
                        "name": f"{sql_file.name}: has DML statement",
                        "status": "warning",
                        "message": "Could not detect SELECT/INSERT/UPDATE/DELETE statement.",
                        "file_path": relative,
                        "line": 1,
                    }
                )
            else:
                rules.append(
                    {
                        "rule_id": "sql.statement_shape",
                        "name": f"{sql_file.name}: has DML statement",
                        "status": "pass",
                        "message": "Statement looks valid.",
                        "file_path": relative,
                        "line": 1,
                    }
                )

        if "descriptions" in allowed_categories:
            if "--" not in raw:
                rules.append(
                    {
                        "rule_id": "descriptions.comment_present",
                        "name": f"{sql_file.name}: has comment",
                        "status": "warning",
                        "message": "No SQL comments found.",
                        "file_path": relative,
                        "line": 1,
                    }
                )
            else:
                rules.append(
                    {
                        "rule_id": "descriptions.comment_present",
                        "name": f"{sql_file.name}: has comment",
                        "status": "pass",
                        "message": "Comment found.",
                        "file_path": relative,
                        "line": 1,
                    }
                )

    passed = sum(1 for item in rules if item["status"] == "pass")
    warnings = sum(1 for item in rules if item["status"] == "warning")
    errors = sum(1 for item in rules if item["status"] == "error")

    return {
        "run_id": f"val-{uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": project_id,
        "model": model_id,
        "summary": {
            "passed": passed,
            "warnings": warnings,
            "errors": errors,
        },
        "rules": rules,
        "workflow_updated_at": _workflow_updated_at_for_model(project_path, model_id),
        "workflow_status": workflow_state.get("status"),
        "workflow_source": workflow_state.get("source"),
        "workflow_attached": isinstance(workflow_payload, dict),
    }


def _resolve_model_id_for_validation(project_path: Path, explicit_model_id: str | None) -> str:
    if explicit_model_id:
        _ = _resolve_model_path(project_path, explicit_model_id)
        return explicit_model_id

    model_root = project_path / "model"
    candidates = sorted([item.name for item in model_root.iterdir() if item.is_dir()], key=str.lower) if model_root.exists() else []
    if not candidates:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No models found in project.")
    return candidates[0]


def _list_model_ids(project_path: Path) -> list[str]:
    model_root = project_path / "model"
    if not model_root.exists() or not model_root.is_dir():
        return []
    return sorted([item.name for item in model_root.iterdir() if item.is_dir()], key=str.lower)


def _resolve_project_workflow_status(project_path: Path) -> dict[str, object]:
    model_ids = _list_model_ids(project_path)
    return _resolve_project_workflow_status_core(project_path, model_ids)


def _extract_model_id_from_project_path(path: str) -> str | None:
    normalized = path.replace("\\", "/").strip().strip("/")
    if not normalized:
        return None
    parts = [part for part in normalized.split("/") if part]
    if len(parts) < 2:
        return None
    if parts[0].lower() not in {"model", "models"}:
        return None
    return parts[1]


def _resolve_models_for_rebuild(project_path: Path, changed_paths: list[str] | None) -> list[str]:
    all_models = _list_model_ids(project_path)
    if not all_models:
        return []
    if not changed_paths:
        return all_models

    explicit_models: set[str] = set()
    requires_all = False

    for raw_path in changed_paths:
        if not isinstance(raw_path, str):
            continue
        normalized = raw_path.replace("\\", "/").strip().lstrip("/")
        if not normalized:
            continue
        model_id = _extract_model_id_from_project_path(normalized)
        if model_id:
            explicit_models.add(model_id)
            continue
        if normalized == "project.yml" or normalized.startswith("contexts/") or normalized.startswith("parameters/"):
            requires_all = True
            break

    if requires_all:
        return all_models
    if not explicit_models:
        return []
    return sorted([model_id for model_id in explicit_models if model_id in all_models], key=str.lower)


def _normalize_sql_relative_path(
    project_id: str,
    model_id: str,
    workflow_root_relative: str,
    folder: str,
    raw_sql_path: str | None,
) -> str:
    if isinstance(raw_sql_path, str) and raw_sql_path.strip():
        normalized = raw_sql_path.replace("\\", "/").strip()
        if normalized.startswith("./"):
            normalized = normalized[2:]
        parts = [part for part in normalized.split("/") if part]
        if "model" in parts:
            idx = parts.index("model")
            tail = parts[idx:]
            if len(tail) >= 2:
                return "/".join(tail)
        project_marker = f"{project_id}/model/"
        marker_index = normalized.find(project_marker)
        if marker_index >= 0:
            return normalized[marker_index + len(project_id) + 1 :]
        if normalized.startswith("model/"):
            return normalized

    folder_path = folder.strip("/").replace("\\", "/")
    if folder_path:
        return f"{workflow_root_relative}/{folder_path}"
    return workflow_root_relative


def _resolve_existing_sql_relative_path(
    project_path: Path,
    project_id: str,
    model_id: str,
    workflow_root_relative: str,
    folder: str,
    raw_sql_path: str | None,
    sql_model_name: str | None,
) -> str | None:
    normalized_relative_path = _normalize_sql_relative_path(
        project_id=project_id,
        model_id=model_id,
        workflow_root_relative=workflow_root_relative,
        folder=folder,
        raw_sql_path=raw_sql_path,
    )

    candidates: list[str] = [normalized_relative_path]
    if isinstance(sql_model_name, str) and sql_model_name.strip():
        normalized_name = sql_model_name.strip()
        if not normalized_name.endswith(".sql"):
            normalized_name = f"{normalized_name}.sql"
        folder_relative = str((Path(workflow_root_relative) / folder).as_posix())
        candidates.append(str((Path(folder_relative) / normalized_name).as_posix()))

    for relative_candidate in candidates:
        try:
            candidate = _resolve_sql_path(project_path, relative_candidate)
        except HTTPException:
            continue
        if candidate is None or not candidate.exists() or not candidate.is_file():
            continue
        if candidate.suffix.lower() != ".sql":
            continue
        relative = _as_relative_path(project_path, candidate)
        if isinstance(relative, str) and relative:
            return relative.replace("\\", "/")
    return None


def _build_lineage_from_workflow(
    project_path: Path,
    project_id: str,
    model_id: str,
    workflow_payload: dict[str, object],
) -> dict[str, object]:
    steps_raw = workflow_payload.get("steps")
    steps = [item for item in steps_raw if isinstance(item, dict)] if isinstance(steps_raw, list) else []
    sql_steps = [
        step
        for step in steps
        if str(step.get("step_type", "")).lower() == "sql" and isinstance(step.get("sql_model"), dict)
    ]

    model_path = _resolve_model_path(project_path, model_id)
    workflow_root = _detect_workflow_root(model_path)
    workflow_root_relative = str(workflow_root.relative_to(project_path)).replace("\\", "/")

    folder_config_map = {}
    config_raw = workflow_payload.get("config")
    if isinstance(config_raw, dict):
        folders_raw = config_raw.get("folders")
        if isinstance(folders_raw, dict):
            folder_config_map = folders_raw

    folder_runtime_map = {}
    runtime_raw = workflow_payload.get("folders")
    if isinstance(runtime_raw, dict):
        folder_runtime_map = runtime_raw

    folder_order: list[str] = []
    folder_nodes: dict[str, dict[str, object]] = {}
    sql_step_by_full_name: dict[str, dict[str, object]] = {}
    unique_params: set[str] = set()

    for step in sql_steps:
        folder = str(step.get("folder", "")).strip().replace("\\", "/")
        if not folder:
            continue
        folder_relative_path = str((Path(workflow_root_relative) / folder).as_posix())
        if folder not in folder_order:
            folder_order.append(folder)
        sql_step_by_full_name[str(step.get("full_name", ""))] = step

        sql_model = step.get("sql_model")
        if not isinstance(sql_model, dict):
            continue

        raw_sql_path = sql_model.get("path")
        existing_sql_relative_path = _resolve_existing_sql_relative_path(
            project_path=project_path,
            project_id=project_id,
            model_id=model_id,
            workflow_root_relative=workflow_root_relative,
            folder=folder,
            raw_sql_path=str(raw_sql_path) if isinstance(raw_sql_path, str) else None,
            sql_model_name=str(sql_model.get("name")) if isinstance(sql_model.get("name"), str) else None,
        )
        file_name = Path(existing_sql_relative_path).name if isinstance(existing_sql_relative_path, str) else None

        node = folder_nodes.get(folder)
        if node is None:
            folder_cfg = folder_config_map.get(folder) if isinstance(folder_config_map, dict) else None
            runtime_cfg = folder_runtime_map.get(folder) if isinstance(folder_runtime_map, dict) else None
            materialized = None
            if isinstance(folder_cfg, dict):
                raw_mat = folder_cfg.get("materialized")
                if isinstance(raw_mat, str) and raw_mat.strip():
                    materialized = raw_mat.strip()
            if materialized is None and isinstance(runtime_cfg, dict):
                raw_mat = runtime_cfg.get("materialized")
                if isinstance(raw_mat, str) and raw_mat.strip():
                    materialized = raw_mat.strip()

            node = {
                "id": folder,
                "name": folder,
                "path": folder_relative_path,
                "materialized": materialized or "n/a",
                "enabled_contexts_set": set(),
                "enabled_for_all_contexts": False,
                "queries_set": set(),
                "parameters_set": set(),
                "ctes_set": set(),
            }
            folder_nodes[folder] = node

        context_name = str(step.get("context", "all")).strip()
        if not context_name or context_name == "all":
            node["enabled_for_all_contexts"] = True
        else:
            enabled_set = node.get("enabled_contexts_set")
            if isinstance(enabled_set, set):
                enabled_set.add(context_name)

        if isinstance(file_name, str) and file_name:
            query_set = node.get("queries_set")
            if isinstance(query_set, set):
                query_set.add(file_name)

        materialization = sql_model.get("materialization")
        if (
            isinstance(file_name, str)
            and file_name
            and isinstance(materialization, str)
            and materialization.strip()
            and str(node.get("materialized")) == "n/a"
        ):
            node["materialized"] = materialization.strip()

        metadata = sql_model.get("metadata")
        if isinstance(file_name, str) and file_name and isinstance(metadata, dict):
            parameters = metadata.get("parameters")
            if isinstance(parameters, list):
                for item in parameters:
                    if not isinstance(item, str) or not item.strip():
                        continue
                    param_name = item.strip()
                    unique_params.add(param_name)
                    params_set = node.get("parameters_set")
                    if isinstance(params_set, set):
                        params_set.add(param_name)

            cte_data = metadata.get("cte")
            if isinstance(cte_data, dict):
                for cte_name in cte_data.keys():
                    if isinstance(cte_name, str) and cte_name.strip():
                        ctes_set = node.get("ctes_set")
                        if isinstance(ctes_set, set):
                            ctes_set.add(cte_name.strip())
            inline_cte = metadata.get("inline_cte_configs")
            if isinstance(inline_cte, dict):
                for cte_name in inline_cte.keys():
                    if isinstance(cte_name, str) and cte_name.strip():
                        ctes_set = node.get("ctes_set")
                        if isinstance(ctes_set, set):
                            ctes_set.add(cte_name.strip())

    nodes: list[dict[str, object]] = []
    for folder in folder_order:
        node = folder_nodes.get(folder)
        if not node:
            continue
        enabled_contexts = None
        if not bool(node.get("enabled_for_all_contexts")):
            enabled_set = node.get("enabled_contexts_set")
            enabled_contexts = sorted(enabled_set) if isinstance(enabled_set, set) and enabled_set else None

        nodes.append(
            {
                "id": str(node.get("id")),
                "name": str(node.get("name")),
                "path": str(node.get("path")),
                "materialized": str(node.get("materialized") or "n/a"),
                "enabled_contexts": enabled_contexts,
                "queries": sorted(node.get("queries_set")) if isinstance(node.get("queries_set"), set) else [],
                "parameters": sorted(node.get("parameters_set")) if isinstance(node.get("parameters_set"), set) else [],
                "ctes": sorted(node.get("ctes_set")) if isinstance(node.get("ctes_set"), set) else [],
            }
        )

    edge_pairs: set[tuple[str, str]] = set()
    node_ids = {str(node["id"]) for node in nodes}

    for step in sql_steps:
        target_folder = str(step.get("folder", "")).strip().replace("\\", "/")
        if target_folder not in node_ids:
            continue
        dependencies = step.get("dependencies")
        if not isinstance(dependencies, list):
            continue
        for dependency in dependencies:
            if not isinstance(dependency, str):
                continue
            source_step = sql_step_by_full_name.get(dependency)
            if not source_step:
                continue
            source_folder = str(source_step.get("folder", "")).strip().replace("\\", "/")
            if source_folder in node_ids and source_folder != target_folder:
                edge_pairs.add((source_folder, target_folder))

    if not edge_pairs and len(nodes) > 1:
        for index in range(len(nodes) - 1):
            edge_pairs.add((str(nodes[index]["id"]), str(nodes[index + 1]["id"])))

    edges = [
        {
            "id": f"{source}->{target}",
            "source": source,
            "target": target,
            "status": "resolved",
        }
        for source, target in sorted(edge_pairs)
    ]

    return {
        "project_id": project_id,
        "model_id": model_id,
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "folders": len(nodes),
            "queries": sum(len(node["queries"]) for node in nodes),
            "params": len(unique_params),
        },
    }


def _extract_ordered_folders_from_workflow(workflow_payload: dict[str, object]) -> list[str]:
    steps_raw = workflow_payload.get("steps")
    steps = [item for item in steps_raw if isinstance(item, dict)] if isinstance(steps_raw, list) else []
    ordered: list[str] = []
    seen: set[str] = set()

    for step in steps:
        if str(step.get("step_type", "")).lower() != "sql":
            continue
        folder = str(step.get("folder", "")).strip().replace("\\", "/")
        if not folder or folder in seen:
            continue
        seen.add(folder)
        ordered.append(folder)

    config_raw = workflow_payload.get("config")
    if isinstance(config_raw, dict):
        folders_raw = config_raw.get("folders")
        if isinstance(folders_raw, dict):
            for folder in sorted(folders_raw.keys()):
                normalized = str(folder).strip().replace("\\", "/")
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    ordered.append(normalized)

    return ordered


def _enabled_rule_to_bool(enabled_raw: object) -> bool:
    if isinstance(enabled_raw, bool):
        return enabled_raw
    if isinstance(enabled_raw, dict):
        if enabled_raw.get("value") is False:
            return False
        return True
    return True


def _build_model_object_from_workflow(
    workflow_payload: dict[str, object],
) -> dict[str, object]:
    target_table_raw = workflow_payload.get("target_table")
    target_table_obj = target_table_raw if isinstance(target_table_raw, dict) else {}
    attributes_raw = target_table_obj.get("attributes")
    attrs = [item for item in attributes_raw if isinstance(item, dict)] if isinstance(attributes_raw, list) else []

    target_table = {
        "name": target_table_obj.get("name"),
        "schema": target_table_obj.get("schema"),
        "description": target_table_obj.get("description"),
        "template": target_table_obj.get("template"),
        "engine": target_table_obj.get("engine"),
        "attributes": [
            {
                "name": attr.get("name"),
                "domain_type": attr.get("domain_type"),
                "is_key": attr.get("is_key"),
                "required": attr.get("required"),
                "default_value": attr.get("default_value"),
            }
            for attr in attrs
        ],
    }

    config_raw = workflow_payload.get("config")
    config = config_raw if isinstance(config_raw, dict) else {}
    folders_cfg_raw = config.get("folders")
    folders_cfg = folders_cfg_raw if isinstance(folders_cfg_raw, dict) else {}
    runtime_folders_raw = workflow_payload.get("folders")
    runtime_folders = runtime_folders_raw if isinstance(runtime_folders_raw, dict) else {}
    ordered_folders = _extract_ordered_folders_from_workflow(workflow_payload)

    folders: list[dict[str, object]] = []
    for folder_id in ordered_folders:
        cfg_item = folders_cfg.get(folder_id)
        cfg = cfg_item if isinstance(cfg_item, dict) else {}
        runtime_item = runtime_folders.get(folder_id)
        runtime = runtime_item if isinstance(runtime_item, dict) else {}

        materialization = cfg.get("materialized")
        if not isinstance(materialization, str) or not materialization.strip():
            runtime_materialized = runtime.get("materialized")
            if isinstance(runtime_materialized, str) and runtime_materialized.strip():
                materialization = runtime_materialized
            else:
                materialization = None

        folders.append(
            {
                "id": folder_id,
                "description": cfg.get("description"),
                "enabled": _enabled_rule_to_bool(cfg.get("enabled")),
                "materialization": materialization,
                "pattern": None,
            }
        )

    cte_default = None
    cte_by_context: dict[str, str] = {}
    cte_raw = config.get("cte")
    if isinstance(cte_raw, dict):
        raw_default = cte_raw.get("cte_materialization")
        if isinstance(raw_default, str) and raw_default.strip():
            cte_default = raw_default.strip()
        raw_by_context = cte_raw.get("by_context")
        if isinstance(raw_by_context, dict):
            for key, value in raw_by_context.items():
                if isinstance(key, str) and isinstance(value, str) and key.strip() and value.strip():
                    cte_by_context[key.strip()] = value.strip()

    return {
        "target_table": target_table,
        "workflow": {
            "description": config.get("description"),
            "folders": folders,
        },
        "cte_settings": {
            "default": cte_default,
            "by_context": cte_by_context,
        },
    }


def _infer_parameter_scope_from_path(source_path: str | None, fallback_model_id: str) -> str:
    if not source_path:
        return f"model:{fallback_model_id}"
    normalized = source_path.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part]
    if "parameters" in parts:
        params_idx = parts.index("parameters")
        if params_idx == 0:
            return "global"
        if params_idx >= 2 and parts[params_idx - 2] == "model":
            return f"model:{parts[params_idx - 1]}"
    return f"model:{fallback_model_id}"


def _collect_parameters_from_workflow(
    project_path: Path,
    project_id: str,
    model_id: str,
    workflow_payload: dict[str, object],
    file_parameters: list[dict[str, object]],
) -> list[dict[str, object]]:
    steps_raw = workflow_payload.get("steps")
    steps = [item for item in steps_raw if isinstance(item, dict)] if isinstance(steps_raw, list) else []
    param_steps = [step for step in steps if str(step.get("step_type", "")).lower() == "param"]
    if not param_steps:
        return file_parameters

    file_map: dict[tuple[str, str], dict[str, object]] = {}
    name_to_scopes: dict[str, set[str]] = {}
    for item in file_parameters:
        name = str(item.get("name", "")).strip()
        scope = str(item.get("scope", "")).strip()
        if not name or not scope:
            continue
        file_map[(name, scope)] = item
        name_to_scopes.setdefault(name, set()).add(scope)

    merged: dict[tuple[str, str], dict[str, object]] = dict(file_map)

    for step in param_steps:
        param_raw = step.get("param_model")
        param = param_raw if isinstance(param_raw, dict) else {}
        name = str(param.get("name", "")).strip()
        if not name:
            continue

        source_sql = param.get("source_sql")
        source_path = str(source_sql).strip() if isinstance(source_sql, str) and source_sql.strip() else None
        guessed_scope = _infer_parameter_scope_from_path(source_path, model_id)
        possible_scopes = sorted(name_to_scopes.get(name) or [])
        if len(possible_scopes) == 1:
            guessed_scope = possible_scopes[0]
        elif guessed_scope not in possible_scopes and ("global" in possible_scopes):
            guessed_scope = "global"

        key = (name, guessed_scope)
        existing = merged.get(key, {})

        values_obj: dict[str, dict[str, str]] = {}
        values_raw = param.get("values")
        if isinstance(values_raw, dict):
            for ctx, row in values_raw.items():
                if not isinstance(ctx, str) or not ctx.strip():
                    continue
                if isinstance(row, dict):
                    row_type = row.get("type")
                    row_value = row.get("value")
                    values_obj[ctx.strip()] = {
                        "type": str(row_type).lower() if isinstance(row_type, str) and row_type.strip() else "static",
                        "value": "" if row_value is None else str(row_value),
                    }

        if not values_obj:
            step_context = str(step.get("context", "all")).strip() or "all"
            values_obj = {step_context: {"type": "static", "value": ""}}

        value_types = sorted({item.get("type", "static") for item in values_obj.values()})
        value_type = "dynamic" if "dynamic" in value_types else value_types[0] if value_types else "static"

        default_path = f"parameters/{name}.yml" if guessed_scope == "global" else f"model/{model_id}/parameters/{name}.yml"
        if source_path:
            normalized_source = source_path.replace("\\", "/")
            if normalized_source.startswith(f"{project_id}/"):
                normalized_source = normalized_source[len(project_id) + 1 :]
            if normalized_source.startswith("model/") or normalized_source.startswith("parameters/"):
                default_path = normalized_source

        merged[key] = {
            "name": name,
            "scope": guessed_scope,
            "path": str(existing.get("path", default_path)),
            "description": str(param.get("description") or existing.get("description") or ""),
            "domain_type": str(param.get("domain_type") or existing.get("domain_type") or "string"),
            "value_type": str(existing.get("value_type") or value_type),
            "values": values_obj,
        }

    return sorted(merged.values(), key=lambda item: (str(item.get("name", "")).lower(), str(item.get("scope", "")).lower()))


def _collect_all_contexts_from_workflow(workflow_payload: dict[str, object]) -> list[str]:
    contexts: set[str] = set()
    all_contexts_raw = workflow_payload.get("all_contexts")
    if isinstance(all_contexts_raw, list):
        for item in all_contexts_raw:
            if isinstance(item, str) and item.strip():
                contexts.add(item.strip())

    steps_raw = workflow_payload.get("steps")
    steps = [item for item in steps_raw if isinstance(item, dict)] if isinstance(steps_raw, list) else []
    for step in steps:
        context_raw = step.get("context")
        if isinstance(context_raw, str) and context_raw.strip() and context_raw.strip() != "all":
            contexts.add(context_raw.strip())

    config_raw = workflow_payload.get("config")
    if isinstance(config_raw, dict):
        cte_raw = config_raw.get("cte")
        if isinstance(cte_raw, dict):
            by_context_raw = cte_raw.get("by_context")
            if isinstance(by_context_raw, dict):
                for key in by_context_raw.keys():
                    if isinstance(key, str) and key.strip():
                        contexts.add(key.strip())

        folders_raw = config_raw.get("folders")
        if isinstance(folders_raw, dict):
            for folder_config in folders_raw.values():
                if not isinstance(folder_config, dict):
                    continue
                enabled_raw = folder_config.get("enabled")
                if not isinstance(enabled_raw, dict):
                    continue
                enabled_contexts_raw = enabled_raw.get("contexts")
                if isinstance(enabled_contexts_raw, list):
                    for item in enabled_contexts_raw:
                        if isinstance(item, str) and item.strip():
                            contexts.add(item.strip())

    return sorted(contexts)


def _log_workflow_fallback(
    *,
    endpoint: str,
    project_id: str,
    model_id: str | None = None,
    reason: str,
) -> None:
    LOGGER.warning(
        "workflow.fallback endpoint=%s project_id=%s model_id=%s reason=%s",
        endpoint,
        project_id,
        model_id or "-",
        reason,
    )


def _collect_project_parameters_primary(
    project_path: Path,
    project_id: str,
) -> tuple[list[dict[str, object]], set[str], list[str]]:
    merged: list[dict[str, object]] = _collect_parameter_objects(project_path)
    all_contexts: set[str] = set()
    fallback_models: list[str] = []

    for model_id in _list_model_ids(project_path):
        workflow_payload = _ensure_workflow_payload(project_id, model_id, force_rebuild=False)
        if not isinstance(workflow_payload, dict):
            fallback_models.append(model_id)
            continue
        merged = _collect_parameters_from_workflow(project_path, project_id, model_id, workflow_payload, merged)
        all_contexts.update(_collect_all_contexts_from_workflow(workflow_payload))

    return merged, all_contexts, fallback_models


def _ensure_workflow_payload(
    project_id: str,
    model_id: str,
    force_rebuild: bool = False,
) -> dict[str, object] | None:
    project_path = FW_SERVICE.load_project(project_id)
    cached = _read_workflow_cache(project_path, model_id)
    if cached is not None and not force_rebuild:
        state = _workflow_state_for_model(project_path, model_id)
        if state["status"] == _WORKFLOW_STATUS_MISSING:
            _write_workflow_meta(
                project_path,
                model_id,
                status_value=_WORKFLOW_STATUS_READY,
                error=None,
                source=_WORKFLOW_SOURCE_FRAMEWORK,
            )
        return cached

    _write_workflow_meta(
        project_path,
        model_id,
        status_value=_WORKFLOW_STATUS_BUILDING,
        error=None,
        source=_WORKFLOW_SOURCE_FRAMEWORK,
    )

    try:
        build_result = FW_SERVICE.run_workflow_build(project_id=project_id, model_id=model_id, context=None)
        workflow_payload_raw = build_result.get("workflow")
        if not isinstance(workflow_payload_raw, dict):
            if cached is not None:
                _write_workflow_meta(
                    project_path,
                    model_id,
                    status_value=_WORKFLOW_STATUS_STALE,
                    error="Workflow build returned invalid payload.",
                    source=_WORKFLOW_SOURCE_FALLBACK,
                )
            else:
                _write_workflow_meta(
                    project_path,
                    model_id,
                    status_value=_WORKFLOW_STATUS_ERROR,
                    error="Workflow build returned invalid payload.",
                    source=_WORKFLOW_SOURCE_FRAMEWORK,
                )
            return cached
        _write_workflow_cache(project_path, model_id, workflow_payload_raw)
        _write_workflow_meta(
            project_path,
            model_id,
            status_value=_WORKFLOW_STATUS_READY,
            error=None,
            source=_WORKFLOW_SOURCE_FRAMEWORK,
        )
        LOGGER.info(
            "workflow.rebuild.succeeded project_id=%s model_id=%s source=%s",
            project_id,
            model_id,
            _WORKFLOW_SOURCE_FRAMEWORK,
        )
        return workflow_payload_raw
    except Exception as exc:
        if cached is not None:
            _write_workflow_meta(
                project_path,
                model_id,
                status_value=_WORKFLOW_STATUS_STALE,
                error=str(exc),
                source=_WORKFLOW_SOURCE_FALLBACK,
            )
            LOGGER.warning(
                "workflow.rebuild.soft_failed project_id=%s model_id=%s source=%s error=%s",
                project_id,
                model_id,
                _WORKFLOW_SOURCE_FALLBACK,
                str(exc),
            )
            return cached
        _write_workflow_meta(
            project_path,
            model_id,
            status_value=_WORKFLOW_STATUS_ERROR,
            error=str(exc),
            source=_WORKFLOW_SOURCE_FRAMEWORK,
        )
        LOGGER.exception(
            "workflow.rebuild.failed project_id=%s model_id=%s source=%s",
            project_id,
            model_id,
            _WORKFLOW_SOURCE_FRAMEWORK,
        )
        return cached


def trigger_workflow_rebuild(project_id: str, changed_paths: list[str] | None = None) -> dict[str, object]:
    try:
        project_path = FW_SERVICE.load_project(project_id)
    except Exception as exc:
        return {"project_id": project_id, "rebuilt_models": [], "errors": [str(exc)]}

    model_ids = _resolve_models_for_rebuild(project_path, changed_paths)
    rebuilt_models: list[str] = []
    errors: list[str] = []

    for model_id in model_ids:
        workflow_payload = _ensure_workflow_payload(project_id, model_id, force_rebuild=True)
        if workflow_payload is None:
            errors.append(f"Workflow build failed for model '{model_id}'.")
            continue
        rebuilt_models.append(model_id)

    status_payload = _resolve_project_workflow_status(project_path)
    LOGGER.info(
        "workflow.rebuild.batch project_id=%s changed_paths=%s rebuilt_models=%s errors=%s",
        project_id,
        changed_paths or [],
        rebuilt_models,
        errors,
    )
    return {"project_id": project_id, "rebuilt_models": rebuilt_models, "errors": errors, "status": status_payload}


def ensure_project_workflow_cache(project_id: str) -> dict[str, object]:
    try:
        project_path = FW_SERVICE.load_project(project_id)
    except Exception as exc:
        return {"project_id": project_id, "rebuilt_models": [], "errors": [str(exc)]}

    missing_paths: list[str] = []
    for model_id in _list_model_ids(project_path):
        cache_file = _workflow_cache_file(project_path, model_id)
        if not cache_file.exists():
            missing_paths.append(f"model/{model_id}/model.yml")
    if not missing_paths:
        return {"project_id": project_id, "rebuilt_models": [], "errors": []}
    LOGGER.info(
        "workflow.ensure_cache.missing project_id=%s changed_paths=%s",
        project_id,
        missing_paths,
    )
    return trigger_workflow_rebuild(project_id, changed_paths=missing_paths)


FW_SERVICE = FWService(
    projects_base_path=Path(settings.projects_path),
    model_loader=_resolve_model_path,
    lineage_nodes_builder=_collect_lineage_nodes,
    lineage_edges_builder=_collect_lineage_edges,
    validation_runner=_build_validation_result,
    generation_runner=_run_project_generation,
    template_registry=TemplateRegistry(templates=("dqcr", "airflow", "dbt", "oracle_plsql")),
    cli_command=settings.fw_cli_command,
    prefer_cli=settings.fw_use_cli,
)


def _parse_model_yml_to_object(model_yml_path: Path) -> dict[str, object]:
    raw = model_yml_path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    target_table: dict[str, object] = {
        "name": None,
        "schema": None,
        "description": None,
        "template": None,
        "engine": None,
        "attributes": [],
    }
    attributes: list[dict[str, object]] = []
    workflow: dict[str, object] = {
        "description": None,
        "folders": [],
    }
    cte_settings: dict[str, object] = {
        "default": None,
        "by_context": {},
    }
    folders: list[dict[str, object]] = []

    in_target_table = False
    in_attributes = False
    current_attribute: dict[str, object] | None = None
    in_workflow = False
    in_folders = False
    in_cte_settings = False
    in_cte_by_context = False

    for line in lines:
        if re.match(r"^\S", line):
            in_target_table = line.strip() == "target_table:"
            in_workflow = line.strip() == "workflow:"
            in_cte_settings = line.strip() == "cte_settings:"
            in_attributes = False
            in_folders = False
            in_cte_by_context = False
            current_attribute = None
            continue

        if in_target_table:
            if re.match(r"^\s{2}attributes:\s*$", line):
                in_attributes = True
                current_attribute = None
                continue
            if re.match(r"^\s{2}[A-Za-z_][\w]*:\s*", line):
                in_attributes = False
                key, value = line.strip().split(":", 1)
                target_table[key] = value.strip().strip("'\"") if value.strip() else None
                continue
            if in_attributes:
                attr_name_match = re.match(r"^\s{4}-\s*name:\s*(.+?)\s*$", line)
                if attr_name_match:
                    if current_attribute:
                        attributes.append(current_attribute)
                    current_attribute = {"name": attr_name_match.group(1).strip().strip("'\"")}
                    continue
                if current_attribute:
                    kv_match = re.match(r"^\s{6}([A-Za-z_][\w]*):\s*(.+?)\s*$", line)
                    if kv_match:
                        key = kv_match.group(1)
                        value = kv_match.group(2).strip().strip("'\"")
                        if value.lower() == "true":
                            current_attribute[key] = True
                        elif value.lower() == "false":
                            current_attribute[key] = False
                        else:
                            current_attribute[key] = value
                continue

        if in_workflow:
            if re.match(r"^\s{2}description:\s*", line):
                workflow["description"] = line.split(":", 1)[1].strip().strip("'\"")
                continue
            if re.match(r"^\s{2}folders:\s*$", line):
                in_folders = True
                continue
            if in_folders:
                folder_match = re.match(r"^\s{4}([A-Za-z0-9_.-]+):\s*$", line)
                if folder_match:
                    folders.append({"id": folder_match.group(1)})
                    continue
                if folders:
                    folder_desc_match = re.match(r"^\s{6}description:\s*(.+?)\s*$", line)
                    folder_enabled_match = re.match(r"^\s{6}enabled:\s*(true|false)\s*$", line, re.IGNORECASE)
                    if folder_desc_match:
                        folders[-1]["description"] = folder_desc_match.group(1).strip().strip("'\"")
                    elif folder_enabled_match:
                        folders[-1]["enabled"] = folder_enabled_match.group(1).lower() == "true"

        if in_cte_settings:
            cte_default_match = re.match(r"^\s{2}default:\s*(.+?)\s*$", line)
            if cte_default_match:
                cte_settings["default"] = cte_default_match.group(1).strip().strip("'\"")
                continue
            if re.match(r"^\s{2}by_context:\s*$", line):
                in_cte_by_context = True
                continue
            if in_cte_by_context:
                ctx_match = re.match(r"^\s{4}([A-Za-z0-9_.-]+):\s*(.+?)\s*$", line)
                if ctx_match:
                    by_context = cte_settings.get("by_context")
                    if isinstance(by_context, dict):
                        by_context[ctx_match.group(1)] = ctx_match.group(2).strip().strip("'\"")

    if current_attribute:
        attributes.append(current_attribute)
    target_table["attributes"] = attributes
    workflow["folders"] = folders
    model_path = model_yml_path.parent
    try:
        workflow_root = _detect_workflow_root(model_path)
    except ValueError:
        workflow_root = None

    folder_map = {str(item.get("id")): item for item in folders if isinstance(item, dict) and item.get("id")}
    if workflow_root is not None and workflow_root.exists():
        for folder_dir in sorted([item for item in workflow_root.iterdir() if item.is_dir()], key=lambda p: p.name.lower()):
            entry = folder_map.get(folder_dir.name)
            if entry is None:
                entry = {"id": folder_dir.name}
                folders.append(entry)
                folder_map[folder_dir.name] = entry

            folder_yml = folder_dir / "folder.yml"
            if folder_yml.exists() and folder_yml.is_file():
                raw_folder = folder_yml.read_text(encoding="utf-8")
                mat_match = re.search(r"^\s*materialized:\s*([A-Za-z_][\w.-]*)\s*$", raw_folder, re.MULTILINE)
                if mat_match:
                    entry["materialization"] = mat_match.group(1)
                enabled_match = re.search(r"^\s*enabled:\s*(true|false)\s*$", raw_folder, re.MULTILINE | re.IGNORECASE)
                if enabled_match:
                    entry["enabled"] = enabled_match.group(1).lower() == "true"

    return {
        "target_table": target_table,
        "workflow": workflow,
        "cte_settings": cte_settings,
    }


def _build_model_yml_schema() -> dict[str, object]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "DQCR Model YML",
        "type": "object",
        "required": ["target_table", "workflow"],
        "properties": {
            "target_table": {
                "type": "object",
                "required": ["name", "schema", "attributes"],
                "properties": {
                    "name": {"type": "string"},
                    "schema": {"type": "string"},
                    "description": {"type": ["string", "null"]},
                    "template": {"type": ["string", "null"]},
                    "engine": {"type": ["string", "null"]},
                    "attributes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name"],
                            "properties": {
                                "name": {"type": "string"},
                                "domain_type": {"type": ["string", "null"]},
                                "is_key": {"type": ["boolean", "null"]},
                                "required": {"type": ["boolean", "null"]},
                                "default_value": {"type": ["string", "number", "boolean", "null"]},
                            },
                        },
                    },
                },
            },
            "workflow": {
                "type": "object",
                "properties": {
                    "description": {"type": ["string", "null"]},
                    "folders": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["id"],
                            "properties": {
                                "id": {"type": "string"},
                                "description": {"type": ["string", "null"]},
                                "enabled": {"type": ["boolean", "null"]},
                                "materialization": {"type": ["string", "null"]},
                                "pattern": {"type": ["string", "null"]},
                            },
                        },
                    },
                },
            },
            "cte_settings": {
                "type": "object",
                "properties": {
                    "default": {"type": ["string", "null"]},
                    "by_context": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                    },
                },
            },
        },
    }


def _sync_workflow_folders(
    project_path: Path,
    model_id: str,
    folders: list[dict[str, object]],
) -> None:
    model_path = _resolve_model_path(project_path, model_id)
    workflow_root = _detect_workflow_root(model_path)
    existing_dirs = {item.name: item for item in workflow_root.iterdir() if item.is_dir()}

    for folder in folders:
        folder_id = str(folder.get("id", "")).strip()
        if not folder_id:
            continue
        folder_dir = existing_dirs.get(folder_id) or (workflow_root / folder_id)
        folder_dir.mkdir(parents=True, exist_ok=True)

        materialization = str(folder.get("materialization", "")).strip()
        if not materialization:
            materialization = "insert_fc"
        enabled_value = folder.get("enabled")
        enabled = bool(enabled_value) if isinstance(enabled_value, bool) else True

        folder_yml_lines = [
            f"{folder_id}:",
            "  enabled:",
            f"    contexts: [{'default' if enabled else ''}]",
            f"  materialized: {materialization}",
        ]
        (folder_dir / "folder.yml").write_text("\n".join(folder_yml_lines).rstrip() + "\n", encoding="utf-8")

        pattern = str(folder.get("pattern", "")).strip().lower()
        sql_file = folder_dir / "001_Query.sql"
        if pattern and not sql_file.exists():
            if pattern == "load":
                content = "SELECT *\nFROM source_table;\n"
            elif pattern == "transform":
                content = "WITH src AS (\n  SELECT * FROM source_table\n)\nSELECT * FROM src;\n"
            elif pattern == "aggregate":
                content = "SELECT key, COUNT(*) AS cnt\nFROM source_table\nGROUP BY key;\n"
            else:
                content = "SELECT 1 AS value;\n"
            sql_file.write_text(content, encoding="utf-8")


def _dump_model_object_to_yaml(model: dict[str, object]) -> str:
    target_table = model.get("target_table")
    workflow = model.get("workflow")
    cte_settings = model.get("cte_settings")
    if not isinstance(target_table, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model.target_table is required.")
    if not isinstance(workflow, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model.workflow is required.")
    if cte_settings is not None and not isinstance(cte_settings, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model.cte_settings must be object.")

    lines: list[str] = []
    lines.append("target_table:")
    for key in ["name", "schema", "description", "template", "engine"]:
        value = target_table.get(key)
        if value is None or value == "":
            continue
        lines.append(f"  {key}: {value}")

    attributes = target_table.get("attributes")
    lines.append("  attributes:")
    if isinstance(attributes, list):
        for item in attributes:
            if not isinstance(item, dict):
                continue
            attr_name = str(item.get("name", "")).strip()
            if not attr_name:
                continue
            lines.append(f"    - name: {attr_name}")
            for key in ["domain_type", "is_key", "required", "default_value"]:
                if key not in item or item[key] is None or item[key] == "":
                    continue
                value = item[key]
                if isinstance(value, bool):
                    lines.append(f"      {key}: {'true' if value else 'false'}")
                else:
                    lines.append(f"      {key}: {value}")

    lines.append("")
    lines.append("workflow:")
    workflow_description = workflow.get("description")
    if workflow_description:
        lines.append(f"  description: {workflow_description}")
    lines.append("")
    lines.append("  folders:")
    folders = workflow.get("folders")
    if isinstance(folders, list):
        for item in folders:
            if not isinstance(item, dict):
                continue
            folder_id = str(item.get("id", "")).strip()
            if not folder_id:
                continue
            lines.append(f"    {folder_id}:")
            if item.get("description"):
                lines.append(f"      description: {item['description']}")
            if isinstance(item.get("enabled"), bool):
                lines.append(f"      enabled: {'true' if item['enabled'] else 'false'}")
            if item.get("materialization"):
                lines.append(f"      materialization: {item['materialization']}")
            if item.get("pattern"):
                lines.append(f"      pattern: {item['pattern']}")

    cte_default = cte_settings.get("default") if isinstance(cte_settings, dict) else None
    cte_by_context = cte_settings.get("by_context") if isinstance(cte_settings, dict) else None
    if cte_default or (isinstance(cte_by_context, dict) and len(cte_by_context) > 0):
        lines.append("")
        lines.append("cte_settings:")
        if cte_default:
            lines.append(f"  default: {cte_default}")
        lines.append("  by_context:")
        if isinstance(cte_by_context, dict):
            for key, value in sorted(cte_by_context.items(), key=lambda item: item[0]):
                lines.append(f"    {key}: {value}")

    return "\n".join(lines).rstrip() + "\n"


def _resolve_model_id_from_file_path(project_path: Path, file_path: str | None) -> str | None:
    if not file_path:
        return None
    parts = [item for item in file_path.split("/") if item]
    if "model" not in parts:
        return None
    index = parts.index("model")
    if index + 1 >= len(parts):
        return None
    model_id = parts[index + 1]
    model_path = project_path / "model" / model_id
    if not model_path.exists() or not model_path.is_dir():
        return None
    return model_id


def _apply_quickfix_add_field(project_path: Path, model_id: str, field_name: str) -> dict[str, object]:
    model_path = _resolve_model_path(project_path, model_id)
    model_yml = ensure_within_base(project_path, model_path / "model.yml")
    if not model_yml.exists() or not model_yml.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model.yml not found.")

    raw = model_yml.read_text(encoding="utf-8")
    if re.search(rf"(?m)^\s*-\s*name:\s*{re.escape(field_name)}\s*$", raw):
        return {
            "applied": False,
            "message": f"Field '{field_name}' already exists in model.yml.",
            "changed_files": [],
        }

    lines = raw.splitlines()
    insert_index = None
    for index, line in enumerate(lines):
        if re.match(r"^\s*attributes\s*:\s*$", line):
            insert_index = index + 1
            break

    if insert_index is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to find target_table.attributes in model.yml.")

    snippet = [
        "    - name: description",
        "      domain_type: string",
        "      required: false",
    ]
    next_lines = lines[:insert_index] + snippet + lines[insert_index:]
    model_yml.write_text("\n".join(next_lines).rstrip() + "\n", encoding="utf-8")
    return {
        "applied": True,
        "message": "Added missing description field to target_table.attributes.",
        "changed_files": [str(model_yml.relative_to(project_path))],
    }


def _apply_quickfix_rename_folder(project_path: Path, file_path: str, new_name: str | None) -> dict[str, object]:
    source = ensure_within_base(project_path, project_path / file_path)
    if not source.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Path '{file_path}' not found.")

    folder = source if source.is_dir() else source.parent
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to resolve folder to rename.")

    candidate_name = (new_name or "").strip()
    if not candidate_name:
        candidate_name = f"{folder.name}_renamed"
    if not re.match(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*$", candidate_name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="new_name has invalid characters.")

    destination = folder.parent / candidate_name
    destination = ensure_within_base(project_path, destination)
    if destination.exists():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Folder '{candidate_name}' already exists.")

    folder.rename(destination)
    return {
        "applied": True,
        "message": f"Folder renamed to '{candidate_name}'.",
        "changed_files": [str(destination.relative_to(project_path))],
    }


def _normalize_project_id(name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", name.strip()).strip("-.").lower()
    normalized = re.sub(r"-{2,}", "-", normalized)
    if not normalized:
        normalized = f"project-{uuid4().hex[:8]}"
    if len(normalized) < 2:
        normalized = f"{normalized}-{uuid4().hex[:4]}"
    if len(normalized) > 64:
        normalized = normalized[:64].rstrip("-.")
    return normalized


def _build_model_yaml(
    model_name: str,
    template: str,
    attributes: list[dict[str, object]],
    first_folder: str,
) -> str:
    if not attributes:
        attributes = [
            {"name": "id", "domain_type": "number", "is_key": True},
            {"name": "description", "domain_type": "string"},
        ]
    lines = [
        "target_table:",
        f"  name: {model_name.upper()}",
        "  schema: ANALYTICS",
        f"  description: Auto-generated model for {model_name}",
        f"  template: {template}",
        "  engine: dqcr",
        "  attributes:",
    ]
    for item in attributes:
        attr_name = str(item.get("name", "")).strip() or "field"
        domain_type = str(item.get("domain_type", "")).strip() or "string"
        is_key = bool(item.get("is_key", False))
        lines.append(f"    - name: {attr_name}")
        lines.append(f"      domain_type: {domain_type}")
        if is_key:
            lines.append("      is_key: true")

    lines.extend(
        [
            "",
            "workflow:",
            f"  description: Auto-generated workflow for {model_name}",
            "  folders:",
            f"    {first_folder}:",
            "      description: First stage",
            "      enabled: true",
            "      queries:",
            "        001_main:",
            "          materialized: insert_fc",
            "          enabled: true",
            "",
            "cte_settings:",
            "  default: stage_calcid",
            "  by_context: {}",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _write_project_from_wizard(base_projects: Path, payload: dict[str, object]) -> dict[str, object]:
    name_raw = str(payload.get("name", "")).strip()
    if not name_raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required.")

    project_id_raw = payload.get("project_id")
    project_id = str(project_id_raw).strip().lower() if isinstance(project_id_raw, str) and project_id_raw.strip() else _normalize_project_id(name_raw)
    if not PROJECT_ID_PATTERN.match(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="project_id has invalid format.")

    project_path = ensure_within_base(base_projects, base_projects / project_id)
    if project_path.exists():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Project '{project_id}' already exists.")

    description = str(payload.get("description", "")).strip() or f"Project {name_raw}"
    template = str(payload.get("template", "flx")).strip() or "flx"
    properties_raw = payload.get("properties")
    properties = dict(properties_raw) if isinstance(properties_raw, dict) else {}
    properties["dqcr_visibility"] = _sanitize_visibility(payload.get("visibility", properties.get("dqcr_visibility", "private")))
    properties["dqcr_tags"] = ",".join(_parse_tags(payload.get("tags", properties.get("dqcr_tags", []))))

    contexts_raw = payload.get("contexts")
    contexts_input = contexts_raw if isinstance(contexts_raw, list) else ["default"]
    contexts = [str(item).strip() for item in contexts_input if isinstance(item, str) and item.strip()]
    if "default" not in contexts:
        contexts.insert(0, "default")

    model_raw = payload.get("model")
    model = model_raw if isinstance(model_raw, dict) else {}
    model_name = str(model.get("name", "SampleModel")).strip() or "SampleModel"
    first_folder = str(model.get("first_folder", "01_stage")).strip() or "01_stage"
    attributes_raw = model.get("attributes")
    attributes = [item for item in attributes_raw if isinstance(item, dict)] if isinstance(attributes_raw, list) else []

    project_path.mkdir(parents=True, exist_ok=False)
    (project_path / "contexts").mkdir(parents=True, exist_ok=True)
    (project_path / "parameters").mkdir(parents=True, exist_ok=True)
    model_root = project_path / "model" / model_name
    workflow_root = model_root / "workflow" / first_folder
    workflow_root.mkdir(parents=True, exist_ok=True)

    project_yml_lines = [
        f"name: {name_raw}",
        f"description: {description}",
        f"template: {template}",
        "",
        "properties:",
    ]
    if properties:
        for key, value in properties.items():
            if not isinstance(key, str):
                continue
            project_yml_lines.append(f"  {key}: {value}")
    else:
        project_yml_lines.append("  owner: dq_team")
        project_yml_lines.append("  repsysname: demo")

    (project_path / "project.yml").write_text("\n".join(project_yml_lines).rstrip() + "\n", encoding="utf-8")

    for context_name in contexts:
        ctx_file = project_path / "contexts" / f"{context_name}.yml"
        ctx_file.write_text(f"name: {context_name}\nenabled: true\n", encoding="utf-8")

    model_yml = _build_model_yaml(model_name=model_name, template=template, attributes=attributes, first_folder=first_folder)
    (model_root / "model.yml").write_text(model_yml, encoding="utf-8")
    (workflow_root / "folder.yml").write_text(
        f"{first_folder}:\n  enabled:\n    contexts: [{', '.join(contexts)}]\n  materialized: insert_fc\n",
        encoding="utf-8",
    )
    (workflow_root / "001_main.sql").write_text(
        "\n".join(
            [
                "-- Auto-generated SQL",
                f"-- project: {project_id}",
                f"-- model: {model_name}",
                "",
                "SELECT",
                "  1 AS id,",
                "  'generated' AS description",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "id": project_id,
        "name": name_raw,
        "path": str(project_path),
        "contexts": contexts,
        "model": model_name,
    }


def _extract_project_field_from_yml(project_path: Path, field: str) -> str | None:
    project_file = project_path / "project.yml"
    if not project_file.exists() or not project_file.is_file():
        return None
    raw = project_file.read_text(encoding="utf-8")
    match = re.search(rf"^\s*{re.escape(field)}\s*:\s*(.+?)\s*$", raw, re.MULTILINE)
    if not match:
        return None
    value = str(match.group(1)).strip().strip("\"'")
    return value or None


def _extract_project_name_from_yml(project_path: Path) -> str | None:
    return _extract_project_field_from_yml(project_path, "name")


def _extract_project_description_from_yml(project_path: Path) -> str | None:
    return _extract_project_field_from_yml(project_path, "description")


def _extract_properties_block(raw: str) -> dict[str, str]:
    lines = raw.splitlines()
    in_properties = False
    properties: dict[str, str] = {}
    for line in lines:
        if re.match(r"^\s*properties:\s*$", line):
            in_properties = True
            continue
        if not in_properties:
            continue
        if line.strip() and len(line) - len(line.lstrip(" ")) <= 1:
            break
        prop_match = re.match(r"^\s{2}([A-Za-z0-9_.-]+)\s*:\s*(.*?)\s*$", line)
        if not prop_match:
            continue
        key = prop_match.group(1).strip()
        value = prop_match.group(2).strip().strip("\"'")
        properties[key] = value
    return properties


def _parse_tags(raw: object) -> list[str]:
    if isinstance(raw, list):
        values = [str(item).strip().lower() for item in raw if str(item).strip()]
    elif isinstance(raw, str):
        values = [part.strip().lower() for part in raw.split(",") if part.strip()]
    else:
        values = []
    result: list[str] = []
    seen: set[str] = set()
    for tag in values:
        clean = re.sub(r"[^a-z0-9_-]", "", tag.replace(" ", "-"))[:20]
        if not clean or clean in seen:
            continue
        seen.add(clean)
        result.append(clean)
        if len(result) >= 10:
            break
    return result


def _sanitize_visibility(raw: object) -> str:
    return "public" if str(raw).strip().lower() == "public" else "private"


def _read_project_metadata(project_path: Path, project_type: str, registry_entry: dict[str, object] | None) -> dict[str, object]:
    if project_type == "internal":
        project_file = project_path / "project.yml"
        if project_file.exists() and project_file.is_file():
            raw = project_file.read_text(encoding="utf-8")
            props = _extract_properties_block(raw)
            return {
                "name": _extract_project_name_from_yml(project_path),
                "description": _extract_project_description_from_yml(project_path),
                "visibility": _sanitize_visibility(props.get("dqcr_visibility", "private")),
                "tags": _parse_tags(props.get("dqcr_tags", "")),
            }
    if registry_entry:
        return {
            "name": registry_entry.get("name"),
            "description": registry_entry.get("description"),
            "visibility": _sanitize_visibility(registry_entry.get("visibility", "private")),
            "tags": _parse_tags(registry_entry.get("tags", [])),
        }
    return {"name": None, "description": None, "visibility": "private", "tags": []}


def _count_project_objects(project_path: Path) -> tuple[int, int, int]:
    model_root = project_path / "model"
    if not model_root.exists() or not model_root.is_dir():
        return 0, 0, 0

    model_count = sum(1 for item in model_root.iterdir() if item.is_dir())
    folder_count = 0
    sql_count = 0
    for model_dir in [item for item in model_root.iterdir() if item.is_dir()]:
        for root_name in ("SQL", "workflow"):
            workflow_root = model_dir / root_name
            if not workflow_root.exists() or not workflow_root.is_dir():
                continue
            for folder in workflow_root.iterdir():
                if not folder.is_dir():
                    continue
                folder_count += 1
                sql_count += len([file for file in folder.glob("*.sql") if file.is_file()])
            break
    return model_count, folder_count, sql_count


def _project_modified_at(project_path: Path) -> str:
    latest = datetime.fromtimestamp(project_path.stat().st_mtime, tz=timezone.utc)
    for item in project_path.rglob("*"):
        if not item.exists():
            continue
        if item.name.startswith(".dqcr_"):
            continue
        try:
            ts = datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc)
        except OSError:
            continue
        if ts > latest:
            latest = ts
    return latest.isoformat()


def _update_internal_project_yml_metadata(project_path: Path, payload: dict[str, object]) -> None:
    project_file = project_path / "project.yml"
    if not project_file.exists() or not project_file.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project.yml not found.")

    raw = project_file.read_text(encoding="utf-8")
    lines = raw.splitlines()
    name_value = payload.get("name")
    description_value = payload.get("description")
    visibility_value = payload.get("visibility")
    tags_value = payload.get("tags")

    def _replace_top_level(field: str, value: str | None) -> None:
        if value is None:
            return
        pattern = re.compile(rf"^\s*{re.escape(field)}\s*:\s*.*$")
        for index, line in enumerate(lines):
            if pattern.match(line):
                lines[index] = f"{field}: {value}"
                return
        insert_at = 0
        lines.insert(insert_at, f"{field}: {value}")

    _replace_top_level("name", str(name_value).strip() if isinstance(name_value, str) else None)
    _replace_top_level("description", str(description_value).strip() if isinstance(description_value, str) else None)

    props_start = None
    props_end = None
    for index, line in enumerate(lines):
        if re.match(r"^\s*properties:\s*$", line):
            props_start = index
            props_end = len(lines)
            for j in range(index + 1, len(lines)):
                candidate = lines[j]
                if candidate.strip() and len(candidate) - len(candidate.lstrip(" ")) <= 1:
                    props_end = j
                    break
            break

    prop_lines = lines[props_start + 1 : props_end] if props_start is not None and props_end is not None else []
    props = _extract_properties_block("\n".join(["properties:"] + prop_lines))

    if visibility_value is not None:
        props["dqcr_visibility"] = _sanitize_visibility(visibility_value)
    if tags_value is not None:
        props["dqcr_tags"] = ",".join(_parse_tags(tags_value))

    if props_start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("properties:")
        for key, value in sorted(props.items(), key=lambda pair: pair[0].lower()):
            lines.append(f"  {key}: {value}")
    else:
        rebuilt = ["properties:"]
        for key, value in sorted(props.items(), key=lambda pair: pair[0].lower()):
            rebuilt.append(f"  {key}: {value}")
        lines = lines[:props_start] + rebuilt + lines[props_end:]

    project_file.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _validate_source_project_structure(source_path: Path) -> None:
    required = [
        source_path / "project.yml",
        source_path / "contexts",
        source_path / "model",
    ]
    missing = [item.name for item in required if not item.exists()]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source project is invalid. Missing: {', '.join(missing)}.",
        )


def _resolve_project_identity(payload: dict[str, object], source_path: Path) -> tuple[str, str]:
    requested_name = str(payload.get("name", "")).strip()
    discovered_name = _extract_project_name_from_yml(source_path)
    project_name = requested_name or discovered_name or source_path.name

    project_id_raw = payload.get("project_id")
    if isinstance(project_id_raw, str) and project_id_raw.strip():
        project_id = project_id_raw.strip().lower()
    else:
        project_id = _normalize_project_id(project_name)
    if not PROJECT_ID_PATTERN.match(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="project_id has invalid format.")
    return project_id, project_name


def _ensure_project_id_available(base_projects: Path, project_id: str) -> None:
    target_path = ensure_within_base(base_projects, base_projects / project_id)
    if target_path.exists():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Project '{project_id}' already exists.")
    if get_registry_entry(base_projects, project_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Project '{project_id}' already exists.")


def _infer_contexts_and_model(project_path: Path) -> tuple[list[str], str]:
    contexts_dir = project_path / "contexts"
    contexts = [item.stem for item in sorted(contexts_dir.glob("*.yml"), key=lambda p: p.name.lower())] if contexts_dir.exists() else []
    if "default" not in contexts:
        contexts.insert(0, "default")
    model_root = project_path / "model"
    model_names = [item.name for item in sorted(model_root.iterdir(), key=lambda p: p.name.lower()) if item.is_dir()] if model_root.exists() else []
    model_name = model_names[0] if model_names else "SampleModel"
    return contexts, model_name


def _import_project_from_path(base_projects: Path, payload: dict[str, object]) -> dict[str, object]:
    source_path_raw = payload.get("source_path")
    if not isinstance(source_path_raw, str) or not source_path_raw.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="source_path is required for import mode.")
    source_path = Path(source_path_raw).expanduser().resolve()
    if not source_path.exists() or not source_path.is_dir():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="source_path does not exist or is not a directory.")
    _validate_source_project_structure(source_path)

    project_id, project_name = _resolve_project_identity(payload, source_path)
    _ensure_project_id_available(base_projects, project_id)
    target_path = ensure_within_base(base_projects, base_projects / project_id)
    if target_path == source_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="source_path and target path must be different.")

    shutil.copytree(source_path, target_path)
    contexts, model_name = _infer_contexts_and_model(target_path)
    upsert_registry_entry(
        base_projects,
        {
            "id": project_id,
            "name": project_name,
            "source_type": "imported",
            "source_path": str(source_path),
            "availability_status": "available",
            "description": str(payload.get("description", "")).strip(),
            "visibility": _sanitize_visibility(payload.get("visibility", "private")),
            "tags": _parse_tags(payload.get("tags", [])),
        },
    )
    return {
        "id": project_id,
        "name": project_name,
        "path": str(target_path),
        "contexts": contexts,
        "model": model_name,
        "source_type": "imported",
        "source_path": str(source_path),
        "availability_status": "available",
    }


def _normalize_upload_relative_path(value: str) -> str:
    candidate = value.strip().replace("\\", "/").lstrip("/")
    if not candidate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file path is empty.")
    parts = [part for part in candidate.split("/") if part]
    if any(part in {".", ".."} for part in parts):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file path is invalid.")
    return "/".join(parts)


async def _import_project_from_uploaded_files(
    base_projects: Path,
    files: list[UploadFile],
    relative_paths: list[str],
    payload: dict[str, object],
) -> dict[str, object]:
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one uploaded file is required.")
    if len(files) != len(relative_paths):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="files and relative_paths length mismatch.")

    with tempfile.TemporaryDirectory(prefix="dqcr-upload-", dir=str(base_projects)) as temp_dir:
        temp_root = Path(temp_dir)
        for upload, relative_path in zip(files, relative_paths):
            normalized_path = _normalize_upload_relative_path(relative_path)
            target = ensure_within_base(temp_root, temp_root / normalized_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            contents = await upload.read()
            target.write_bytes(contents)

        _validate_source_project_structure(temp_root)
        project_id, project_name = _resolve_project_identity(payload, temp_root)
        _ensure_project_id_available(base_projects, project_id)
        target_path = ensure_within_base(base_projects, base_projects / project_id)
        shutil.copytree(temp_root, target_path)

    contexts, model_name = _infer_contexts_and_model(target_path)
    upsert_registry_entry(
        base_projects,
        {
            "id": project_id,
            "name": project_name,
            "source_type": "imported",
            "source_path": None,
            "availability_status": "available",
            "description": str(payload.get("description", "")).strip(),
            "visibility": _sanitize_visibility(payload.get("visibility", "private")),
            "tags": _parse_tags(payload.get("tags", [])),
        },
    )
    return {
        "id": project_id,
        "name": project_name,
        "path": str(target_path),
        "contexts": contexts,
        "model": model_name,
        "source_type": "imported",
        "source_path": None,
        "availability_status": "available",
    }


def _connect_project_from_path(base_projects: Path, payload: dict[str, object]) -> dict[str, object]:
    source_path_raw = payload.get("source_path")
    if not isinstance(source_path_raw, str) or not source_path_raw.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="source_path is required for connect mode.")
    source_path = Path(source_path_raw).expanduser().resolve()
    if not source_path.exists() or not source_path.is_dir():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="source_path does not exist or is not a directory.")
    _validate_source_project_structure(source_path)

    project_id, project_name = _resolve_project_identity(payload, source_path)
    _ensure_project_id_available(base_projects, project_id)
    contexts, model_name = _infer_contexts_and_model(source_path)
    availability = derive_link_availability(str(source_path))
    upsert_registry_entry(
        base_projects,
        {
            "id": project_id,
            "name": project_name,
            "source_type": "linked",
            "source_path": str(source_path),
            "availability_status": availability,
            "description": str(payload.get("description", "")).strip(),
            "visibility": _sanitize_visibility(payload.get("visibility", "private")),
            "tags": _parse_tags(payload.get("tags", [])),
        },
    )
    return {
        "id": project_id,
        "name": project_name,
        "path": str(source_path),
        "contexts": contexts,
        "model": model_name,
        "source_type": "linked",
        "source_path": str(source_path),
        "availability_status": availability,
    }


def _resolve_project_source_path(
    base: Path,
    project_id: str,
    source_type: str,
    source_path: str | None,
) -> Path | None:
    local_path = ensure_within_base(base, base / project_id)
    if local_path.exists() and local_path.is_dir():
        return local_path
    if source_type == "linked" and source_path:
        linked = Path(source_path).expanduser().resolve()
        if linked.exists() and linked.is_dir():
            return linked
    return None


def _build_project_schema(base: Path, project_id: str, registry_item: dict[str, object] | None) -> ProjectSchema | None:
    source_type = str(registry_item.get("source_type")) if registry_item else "internal"
    source_path = str(registry_item.get("source_path")) if registry_item and registry_item.get("source_path") else None
    path = _resolve_project_source_path(base, project_id, source_type, source_path)

    availability_status = "available"
    if source_type == "linked":
        availability_status = derive_link_availability(source_path)
        if registry_item and availability_status != registry_item.get("availability_status"):
            upsert_registry_entry(
                base,
                {
                    "id": project_id,
                    "name": str(registry_item.get("name", project_id)),
                    "source_type": "linked",
                    "source_path": source_path,
                    "availability_status": availability_status,
                    "description": str(registry_item.get("description", "")),
                    "visibility": _sanitize_visibility(registry_item.get("visibility", "private")),
                    "tags": _parse_tags(registry_item.get("tags", [])),
                },
            )

    if not path and source_type != "linked":
        return None

    metadata = _read_project_metadata(path, source_type, registry_item) if path else _read_project_metadata(base / project_id, source_type, registry_item)
    model_count, folder_count, sql_count = _count_project_objects(path) if path else (0, 0, 0)
    modified_at = _project_modified_at(path) if path else datetime.now(timezone.utc).isoformat()

    try:
        workflow_status_payload = _resolve_project_workflow_status(path) if path else {}
        cache_status = str(workflow_status_payload.get("overall") or "missing")
    except Exception:
        cache_status = "missing"

    return ProjectSchema(
        id=project_id,
        name=str(metadata.get("name") or (registry_item.get("name") if registry_item else project_id)),
        description=str(metadata.get("description")) if metadata.get("description") is not None else None,
        project_type=source_type,
        source_type=source_type,
        source_path=source_path,
        availability_status=availability_status,
        visibility=_sanitize_visibility(metadata.get("visibility", "private")),
        tags=_parse_tags(metadata.get("tags", [])),
        model_count=model_count,
        folder_count=folder_count,
        sql_count=sql_count,
        modified_at=modified_at,
        cache_status=cache_status,
    )


class ProjectMetadataUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    visibility: str | None = None
    tags: list[str] | None = None


@router.get("")
def list_projects() -> list[ProjectSchema]:
    base = Path(settings.projects_path)
    if not base.exists():
        base.mkdir(parents=True, exist_ok=True)

    registry = load_registry(base)
    project_ids = {
        item.name for item in base.iterdir() if item.is_dir() and not item.name.startswith(".")
    } | set(registry.keys())
    projects: list[ProjectSchema] = []
    for project_id in sorted(project_ids, key=lambda value: value.lower()):
        schema = _build_project_schema(base, project_id, registry.get(project_id))
        if schema:
            projects.append(schema)
    return projects


@router.get("/{project_id}")
def get_project(project_id: str) -> ProjectSchema:
    base = Path(settings.projects_path)
    registry = load_registry(base)
    schema = _build_project_schema(base, project_id, registry.get(project_id))
    if not schema:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")
    return schema


@router.patch("/{project_id}/metadata")
def update_project_metadata(project_id: str, payload: ProjectMetadataUpdate) -> dict[str, object]:
    base = Path(settings.projects_path)
    registry = load_registry(base)
    registry_entry = registry.get(project_id)
    source_type = str(registry_entry.get("source_type")) if registry_entry else "internal"

    if source_type == "internal":
        project_path = resolve_project_path(base, project_id)
        update_payload = payload.model_dump(exclude_unset=True)
        _update_internal_project_yml_metadata(project_path, update_payload)
        if registry_entry:
            registry_entry = {
                **registry_entry,
                "name": update_payload.get("name", registry_entry.get("name", project_id)),
                "description": update_payload.get("description", registry_entry.get("description", "")),
                "visibility": _sanitize_visibility(update_payload.get("visibility", registry_entry.get("visibility", "private"))),
                "tags": _parse_tags(update_payload.get("tags", registry_entry.get("tags", []))),
            }
            registry[project_id] = registry_entry
            save_registry(base, registry)
        trigger_workflow_rebuild(project_id)
        return {"ok": True}

    if not registry_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    updated = payload.model_dump(exclude_unset=True)
    if "name" in updated and isinstance(updated["name"], str):
        registry_entry["name"] = updated["name"].strip() or registry_entry.get("name", project_id)
    if "description" in updated and isinstance(updated["description"], str):
        registry_entry["description"] = updated["description"].strip()
    if "visibility" in updated:
        registry_entry["visibility"] = _sanitize_visibility(updated.get("visibility"))
    if "tags" in updated:
        registry_entry["tags"] = _parse_tags(updated.get("tags"))
    registry[project_id] = registry_entry
    save_registry(base, registry)
    return {"ok": True}


@router.delete("/{project_id}")
def delete_project(project_id: str) -> dict[str, object]:
    base = Path(settings.projects_path)
    registry = load_registry(base)
    registry_entry = registry.get(project_id)
    source_type = str(registry_entry.get("source_type")) if registry_entry else "internal"

    local_path = ensure_within_base(base, base / project_id)
    if source_type in {"internal", "imported"} and local_path.exists() and local_path.is_dir():
        shutil.rmtree(local_path)

    if project_id in registry:
        del registry[project_id]
        save_registry(base, registry)

    return {"ok": True}


@router.post("")
def create_project(payload: dict[str, object] = Body(...)) -> dict[str, object]:
    base = Path(settings.projects_path)
    base.mkdir(parents=True, exist_ok=True)
    mode_raw = payload.get("mode", "create")
    mode = str(mode_raw).strip().lower() if isinstance(mode_raw, str) else "create"
    if mode == "create":
        result = _write_project_from_wizard(base, payload)
        upsert_registry_entry(
            base,
            {
                "id": str(result["id"]),
                "name": str(result["name"]),
                "source_type": "internal",
                "source_path": None,
                "availability_status": "available",
                "description": str(payload.get("description", "")).strip(),
                "visibility": _sanitize_visibility(payload.get("visibility", "private")),
                "tags": _parse_tags(payload.get("tags", [])),
            },
        )
        result["source_type"] = "internal"
        result["source_path"] = None
        result["availability_status"] = "available"
        trigger_workflow_rebuild(str(result["id"]))
        return result
    if mode == "import":
        result = _import_project_from_path(base, payload)
        trigger_workflow_rebuild(str(result["id"]))
        return result
    if mode == "connect":
        result = _connect_project_from_path(base, payload)
        trigger_workflow_rebuild(str(result["id"]))
        return result
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mode must be one of: create, import, connect.")


@router.post("/import-upload")
async def import_uploaded_project(
    files: list[UploadFile] = File(...),
    relative_paths: list[str] = Form(...),
    project_id: str | None = Form(None),
    name: str | None = Form(None),
    description: str | None = Form(None),
) -> dict[str, object]:
    base = Path(settings.projects_path)
    base.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {}
    if project_id is not None:
        payload["project_id"] = project_id
    if name is not None:
        payload["name"] = name
    if description is not None:
        payload["description"] = description
    result = await _import_project_from_uploaded_files(base, files, relative_paths, payload)
    trigger_workflow_rebuild(str(result["id"]))
    return result


@router.get("/{project_id}/contexts")
def list_project_contexts(project_id: str) -> list[ContextSchema]:
    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    contexts_path = project_path / "contexts"

    if not contexts_path.exists() or not contexts_path.is_dir():
        return [ContextSchema(id="default", name="default")]

    contexts = [
        ContextSchema(id=item.stem, name=item.stem)
        for item in sorted(contexts_path.glob("*.yml"), key=lambda p: p.name.lower())
    ]

    if not contexts:
        return [ContextSchema(id="default", name="default")]

    return contexts


@router.get("/{project_id}/workflow/status")
def get_project_workflow_status(project_id: str) -> dict[str, object]:
    project_path = FW_SERVICE.load_project(project_id)
    return _resolve_project_workflow_status(project_path)


@router.get("/{project_id}/models/{model_id}/workflow")
def get_model_workflow(project_id: str, model_id: str) -> dict[str, object]:
    project_path = FW_SERVICE.load_project(project_id)
    _ = FW_SERVICE.load_model(project_id, model_id)
    workflow_payload = _ensure_workflow_payload(project_id, model_id, force_rebuild=False)
    state = _workflow_state_for_model(project_path, model_id)
    if not isinstance(workflow_payload, dict):
        _log_workflow_fallback(
            endpoint="model-workflow",
            project_id=project_id,
            model_id=model_id,
            reason="workflow_payload_missing",
        )
    return {
        "project_id": project_id,
        "model_id": model_id,
        "status": state.get("status"),
        "updated_at": state.get("updated_at"),
        "error": state.get("error"),
        "source": state.get("source"),
        "workflow": workflow_payload if isinstance(workflow_payload, dict) else None,
    }


@router.post("/{project_id}/models/{model_id}/workflow/rebuild")
def rebuild_model_workflow(project_id: str, model_id: str) -> dict[str, object]:
    project_path = FW_SERVICE.load_project(project_id)
    _ = FW_SERVICE.load_model(project_id, model_id)
    workflow_payload = _ensure_workflow_payload(project_id, model_id, force_rebuild=True)
    state = _workflow_state_for_model(project_path, model_id)
    if not isinstance(workflow_payload, dict):
        _log_workflow_fallback(
            endpoint="model-workflow-rebuild",
            project_id=project_id,
            model_id=model_id,
            reason="workflow_payload_missing_after_rebuild",
        )
    return {
        "project_id": project_id,
        "model_id": model_id,
        "status": state.get("status"),
        "updated_at": state.get("updated_at"),
        "error": state.get("error"),
        "source": state.get("source"),
        "workflow": workflow_payload if isinstance(workflow_payload, dict) else None,
    }


@router.get("/{project_id}/autocomplete")
def get_project_autocomplete(project_id: str) -> dict[str, object]:
    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    parameters, all_contexts, fallback_models = _collect_project_parameters_primary(project_path, project_id)

    macros = [{"name": macro_name, "source": "builtin"} for macro_name in DEFAULT_MACROS]
    used_fallback = len(fallback_models) > 0
    if used_fallback:
        _log_workflow_fallback(
            endpoint="autocomplete",
            project_id=project_id,
            reason=f"models={','.join(fallback_models)}",
        )
    return {
        "parameters": [
            {
                "name": str(item.get("name", "")),
                "scope": str(item.get("scope", "")),
                "path": str(item.get("path", "")),
                "domain_type": item.get("domain_type"),
                "value_type": item.get("value_type"),
            }
            for item in parameters
        ],
        "macros": macros,
        "config_keys": DQCR_CONFIG_KEYS,
        "all_contexts": sorted(all_contexts),
        "data_source": "fallback" if used_fallback else "workflow",
        "fallback": used_fallback,
    }


@router.get("/{project_id}/parameters")
def get_project_parameters(project_id: str) -> list[dict[str, object]]:
    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    merged, _all_contexts, fallback_models = _collect_project_parameters_primary(project_path, project_id)
    if fallback_models:
        _log_workflow_fallback(
            endpoint="parameters",
            project_id=project_id,
            reason=f"models={','.join(fallback_models)}",
        )
    return merged


@router.post("/{project_id}/parameters")
def create_project_parameter(project_id: str, payload: dict[str, object] = Body(...)) -> dict[str, object]:
    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)

    name_raw = payload.get("name")
    if not isinstance(name_raw, str) or not name_raw.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required.")
    name = _validate_parameter_name(name_raw)

    scope_raw = payload.get("scope")
    scope = _resolve_parameter_scope(project_path, str(scope_raw) if isinstance(scope_raw, str) else "global")

    target_file = _parameter_file_for(project_path, name, scope)
    if target_file.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Parameter '{name}' already exists in scope '{scope}'.",
        )

    rendered = _render_parameter_yaml(
        {
            "name": name,
            "description": payload.get("description", ""),
            "domain_type": payload.get("domain_type", "string"),
            "values": payload.get("values"),
        }
    )

    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(rendered, encoding="utf-8")
    trigger_workflow_rebuild(project_id, changed_paths=[str(target_file.relative_to(project_path))])
    return _parse_parameter_file(project_path, target_file)


@router.put("/{project_id}/parameters/{parameter_id}")
def update_project_parameter(
    project_id: str,
    parameter_id: str,
    payload: dict[str, object] = Body(...),
    scope: str | None = Query(default=None),
) -> dict[str, object]:
    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)

    source_file = _resolve_parameter_file(project_path, parameter_id, scope)
    current = _parse_parameter_file(project_path, source_file)

    next_name_raw = payload.get("name", current["name"])
    if not isinstance(next_name_raw, str) or not next_name_raw.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name must be non-empty string.")
    next_name = _validate_parameter_name(next_name_raw)

    next_scope_raw = payload.get("scope", current["scope"])
    next_scope = _resolve_parameter_scope(project_path, str(next_scope_raw))

    next_description = payload.get("description", current["description"])
    next_domain_type = payload.get("domain_type", current["domain_type"])
    next_values = payload.get("values", current["values"])

    target_file = _parameter_file_for(project_path, next_name, next_scope)
    if target_file != source_file and target_file.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Parameter '{next_name}' already exists in scope '{next_scope}'.",
        )

    rendered = _render_parameter_yaml(
        {
            "name": next_name,
            "description": next_description,
            "domain_type": next_domain_type,
            "values": next_values,
        }
    )
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(rendered, encoding="utf-8")
    if target_file != source_file and source_file.exists():
        source_file.unlink()

    changed_paths = [str(target_file.relative_to(project_path))]
    if target_file != source_file:
        changed_paths.append(str(source_file.relative_to(project_path)))
    trigger_workflow_rebuild(project_id, changed_paths=changed_paths)

    return _parse_parameter_file(project_path, target_file)


@router.delete("/{project_id}/parameters/{parameter_id}")
def delete_project_parameter(project_id: str, parameter_id: str, scope: str | None = Query(default=None)) -> dict[str, object]:
    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    target_file = _resolve_parameter_file(project_path, parameter_id, scope)
    relative_path = str(target_file.relative_to(project_path))
    target_file.unlink()
    trigger_workflow_rebuild(project_id, changed_paths=[relative_path])
    return {"deleted": True, "name": parameter_id, "path": relative_path}


@router.post("/{project_id}/parameters/{parameter_id}/test")
def test_project_parameter(
    project_id: str,
    parameter_id: str,
    payload: dict[str, object] = Body(default={}),
    scope: str | None = Query(default=None),
) -> dict[str, object]:
    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    target_file = _resolve_parameter_file(project_path, parameter_id, scope)
    param = _parse_parameter_file(project_path, target_file)

    context_raw = payload.get("context") if isinstance(payload, dict) else None
    context = str(context_raw).strip() if isinstance(context_raw, str) and context_raw.strip() else "default"

    values_raw = param.get("values")
    values = values_raw if isinstance(values_raw, dict) else {}
    selected_raw = values.get(context) or values.get("all") or values.get("default")
    if selected_raw is None and values:
        selected_raw = next(iter(values.values()))

    selected = selected_raw if isinstance(selected_raw, dict) else {"type": "static", "value": ""}
    selected_type = str(selected.get("type", "static")).lower()
    selected_value = str(selected.get("value", ""))

    if selected_type == "dynamic":
        result_value = f"[simulated dynamic result] SQL: {selected_value}"
    else:
        result_value = selected_value

    return {
        "ok": True,
        "parameter": param.get("name"),
        "scope": param.get("scope"),
        "context": context,
        "type": selected_type,
        "resolved_value": result_value,
    }


@router.get("/{project_id}/models/{model_id}/lineage")
def get_model_lineage(project_id: str, model_id: str, context: str | None = Query(default=None)) -> dict[str, object]:
    project_path = FW_SERVICE.load_project(project_id)
    _ = FW_SERVICE.load_model(project_id, model_id)
    requested_context = context.strip() if isinstance(context, str) and context.strip() else None
    if requested_context:
        try:
            build_result = FW_SERVICE.run_workflow_build(project_id=project_id, model_id=model_id, context=requested_context)
            workflow_payload_for_context = build_result.get("workflow")
            if isinstance(workflow_payload_for_context, dict):
                return _build_lineage_from_workflow(project_path, project_id, model_id, workflow_payload_for_context)
            _log_workflow_fallback(
                endpoint="lineage",
                project_id=project_id,
                model_id=model_id,
                reason=f"context_build_invalid_payload:{requested_context}",
            )
        except Exception as exc:
            LOGGER.warning(
                "workflow.context_build_failed endpoint=lineage project_id=%s model_id=%s context=%s error=%s",
                project_id,
                model_id,
                requested_context,
                str(exc),
            )

    workflow_payload = _ensure_workflow_payload(project_id, model_id, force_rebuild=False)
    if isinstance(workflow_payload, dict):
        return _build_lineage_from_workflow(project_path, project_id, model_id, workflow_payload)
    _log_workflow_fallback(
        endpoint="lineage",
        project_id=project_id,
        model_id=model_id,
        reason="workflow_payload_missing",
    )
    return FW_SERVICE.get_lineage(project_id, model_id)


@router.get("/{project_id}/models/{model_id}/config-chain")
def get_model_config_chain(project_id: str, model_id: str, sql_path: str | None = None) -> dict[str, object]:
    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    return _build_config_chain_response(project_path, project_id, model_id, sql_path)


@router.get("/schema/model-yml")
def get_model_yml_schema() -> dict[str, object]:
    return _build_model_yml_schema()


@router.get("/{project_id}/models/{model_id}")
def get_model_as_object(project_id: str, model_id: str) -> dict[str, object]:
    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    model_path = _resolve_model_path(project_path, model_id)
    model_yml_path = ensure_within_base(project_path, model_path / "model.yml")
    if not model_yml_path.exists() or not model_yml_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model.yml not found.")

    workflow_payload = _ensure_workflow_payload(project_id, model_id, force_rebuild=False)
    workflow_state = _workflow_state_for_model(project_path, model_id)
    if isinstance(workflow_payload, dict):
        return {
            "project_id": project_id,
            "model_id": model_id,
            "path": str(model_yml_path.relative_to(project_path)),
            "model": _build_model_object_from_workflow(workflow_payload),
            "data_source": "workflow",
            "workflow_status": workflow_state.get("status"),
            "workflow_source": workflow_state.get("source"),
            "workflow_updated_at": workflow_state.get("updated_at"),
        }

    _log_workflow_fallback(
        endpoint="model-object",
        project_id=project_id,
        model_id=model_id,
        reason="workflow_payload_missing",
    )
    return {
        "project_id": project_id,
        "model_id": model_id,
        "path": str(model_yml_path.relative_to(project_path)),
        "model": _parse_model_yml_to_object(model_yml_path),
        "data_source": "fallback",
        "workflow_status": workflow_state.get("status"),
        "workflow_source": workflow_state.get("source"),
        "workflow_updated_at": workflow_state.get("updated_at"),
    }


@router.put("/{project_id}/models/{model_id}")
def save_model_from_object(project_id: str, model_id: str, payload: dict[str, object] = Body(...)) -> dict[str, object]:
    model_raw = payload.get("model")
    if not isinstance(model_raw, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model object is required.")

    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    model_path = _resolve_model_path(project_path, model_id)
    model_yml_path = ensure_within_base(project_path, model_path / "model.yml")
    if not model_yml_path.exists() or not model_yml_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model.yml not found.")

    rendered = _dump_model_object_to_yaml(model_raw)
    model_yml_path.write_text(rendered, encoding="utf-8")
    workflow_raw = model_raw.get("workflow")
    if isinstance(workflow_raw, dict):
        folders_raw = workflow_raw.get("folders")
        if isinstance(folders_raw, list):
            safe_folders = [item for item in folders_raw if isinstance(item, dict)]
            _sync_workflow_folders(project_path, model_id, safe_folders)
    trigger_workflow_rebuild(project_id, changed_paths=[str(model_yml_path.relative_to(project_path))])

    return {
        "project_id": project_id,
        "model_id": model_id,
        "path": str(model_yml_path.relative_to(project_path)),
        "saved": True,
    }


@router.post("/{project_id}/build")
def run_project_build(project_id: str, payload: dict[str, object] = Body(default={})) -> dict[str, object]:
    project_path = FW_SERVICE.load_project(project_id)

    model_id_raw = payload.get("model_id") if isinstance(payload, dict) else None
    model_id = _resolve_model_id_for_build(project_path, model_id_raw if isinstance(model_id_raw, str) else None)

    engine_raw = payload.get("engine") if isinstance(payload, dict) else None
    engine = str(engine_raw).strip() if isinstance(engine_raw, str) and engine_raw.strip() else "dqcr"

    context_raw = payload.get("context") if isinstance(payload, dict) else None
    context = str(context_raw).strip() if isinstance(context_raw, str) and context_raw.strip() else "default"

    dry_run_raw = payload.get("dry_run") if isinstance(payload, dict) else None
    dry_run = bool(dry_run_raw) if dry_run_raw is not None else False

    output_path_raw = payload.get("output_path") if isinstance(payload, dict) else None
    output_path = str(output_path_raw).strip() if isinstance(output_path_raw, str) and output_path_raw.strip() else None

    result_raw = FW_SERVICE.run_generation(project_id, model_id, engine, context, dry_run, output_path)
    result = _attach_workflow_context(result_raw, project_path, model_id)
    _record_build_result(project_id, result)
    return result


@router.get("/{project_id}/build/history")
def get_project_build_history(project_id: str) -> list[dict[str, object]]:
    return _get_project_build_history(project_id)


@router.get("/{project_id}/build/{build_id}/files")
def get_project_build_files(project_id: str, build_id: str) -> dict[str, object]:
    build_item = _find_project_build(project_id, build_id)
    files_raw = build_item.get("files")
    files = files_raw if isinstance(files_raw, list) else []
    return {
        "project_id": project_id,
        "build_id": build_id,
        "engine": build_item.get("engine"),
        "output_path": build_item.get("output_path"),
        "files": files,
        "tree": _build_files_tree([item for item in files if isinstance(item, dict)]),
    }


@router.get("/{project_id}/build/{build_id}/download")
def download_project_build(project_id: str, build_id: str, path: str | None = Query(default=None)) -> StreamingResponse:
    output_dir = _resolve_existing_build_output_dir(project_id, build_id)

    if path and path.strip():
        target_file = ensure_within_base(output_dir, output_dir / path.strip())
        if not target_file.exists() or not target_file.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Build file '{path}' not found.")
        buffer = io.BytesIO(target_file.read_bytes())
        buffer.seek(0)
        filename = target_file.name
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return StreamingResponse(buffer, media_type="application/octet-stream", headers=headers)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(output_dir.rglob("*"), key=lambda item: str(item).lower()):
            if not file_path.is_file():
                continue
            arcname = file_path.relative_to(output_dir)
            archive.write(file_path, arcname=str(arcname))
    buffer.seek(0)

    filename = f"{project_id}-{build_id}.zip"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(buffer, media_type="application/zip", headers=headers)


@router.get("/{project_id}/build/{build_id}/files/content")
def get_project_build_file_content(project_id: str, build_id: str, path: str = Query(...)) -> dict[str, str]:
    output_dir = _resolve_existing_build_output_dir(project_id, build_id)
    target_file = ensure_within_base(output_dir, output_dir / path)
    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Build file '{path}' not found.")
    return {
        "build_id": build_id,
        "path": path,
        "content": target_file.read_text(encoding="utf-8", errors="ignore"),
    }


@router.post("/{project_id}/build/{build_id}/preview")
def preview_generated_sql(
    project_id: str,
    build_id: str,
    payload: dict[str, str] = Body(...),
) -> dict[str, str]:
    model_id = payload.get("model_id")
    sql_path = payload.get("sql_path")
    inline_sql = payload.get("inline_sql")

    if not model_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model_id is required.")
    if not sql_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sql_path is required.")

    if build_id not in _SUPPORTED_BUILD_ENGINES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported engine '{build_id}'.",
        )

    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    _ = _resolve_model_path(project_path, model_id)
    sql_file = ensure_within_base(project_path, project_path / sql_path)
    if not sql_file.exists() or not sql_file.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"SQL file '{sql_path}' not found.")

    raw_sql = inline_sql if inline_sql is not None else sql_file.read_text(encoding="utf-8")
    rendered = _render_engine_preview_sql(raw_sql, build_id)
    return {
        "project_id": project_id,
        "model_id": model_id,
        "engine": build_id,
        "sql_path": sql_path,
        "preview": rendered,
    }


@router.post("/{project_id}/validate")
def run_project_validation(project_id: str, payload: dict[str, object] = Body(default={})) -> dict[str, object]:
    project_path = FW_SERVICE.load_project(project_id)

    model_id = _resolve_model_id_for_validation(project_path, payload.get("model_id") if isinstance(payload, dict) else None)
    categories = payload.get("categories") if isinstance(payload, dict) else None
    categories_list = categories if isinstance(categories, list) else None

    result_raw = FW_SERVICE.run_validation(project_id, model_id, categories_list)
    result = _attach_workflow_context(result_raw, project_path, model_id)
    history = _VALIDATION_HISTORY.setdefault(project_id, [])
    history.insert(0, result)
    _VALIDATION_HISTORY[project_id] = history[:20]
    return result


@router.post("/{project_id}/validate/quickfix")
def apply_validation_quickfix(project_id: str, payload: dict[str, object] = Body(default={})) -> dict[str, object]:
    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)

    fix_type = payload.get("type") if isinstance(payload, dict) else None
    if not isinstance(fix_type, str) or not fix_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="type is required.")

    file_path = payload.get("file_path") if isinstance(payload, dict) else None
    file_path_value = file_path if isinstance(file_path, str) else None

    explicit_model_id = payload.get("model_id") if isinstance(payload, dict) else None
    model_id = explicit_model_id if isinstance(explicit_model_id, str) else None
    if model_id is None:
        model_id = _resolve_model_id_from_file_path(project_path, file_path_value)
    if model_id is None:
        model_id = _resolve_model_id_for_validation(project_path, None)

    result: dict[str, object]
    if fix_type == "add_field":
        field_name = payload.get("field_name") if isinstance(payload, dict) else None
        field_name_value = field_name if isinstance(field_name, str) and field_name.strip() else "description"
        result = _apply_quickfix_add_field(project_path, model_id, field_name_value)
    elif fix_type == "rename_folder":
        if not file_path_value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_path is required for rename_folder.")
        new_name = payload.get("new_name") if isinstance(payload, dict) else None
        new_name_value = new_name if isinstance(new_name, str) else None
        result = _apply_quickfix_rename_folder(project_path, file_path_value, new_name_value)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported quickfix type '{fix_type}'.")

    rerun_payload = payload.get("rerun") if isinstance(payload, dict) else None
    rerun = bool(rerun_payload) if rerun_payload is not None else True
    validation_result: dict[str, object] | None = None
    if rerun:
        validation_result = _build_validation_result(project_path, project_id, model_id, None)
        history = _VALIDATION_HISTORY.setdefault(project_id, [])
        history.insert(0, validation_result)
        _VALIDATION_HISTORY[project_id] = history[:20]

    return {
        "project_id": project_id,
        "model_id": model_id,
        "type": fix_type,
        **result,
        "validation": validation_result,
    }


@router.get("/{project_id}/validate/history")
def get_validation_history(project_id: str) -> list[dict[str, object]]:
    return _VALIDATION_HISTORY.get(project_id, [])[:5]
