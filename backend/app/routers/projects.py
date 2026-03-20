import io
from pathlib import Path
from datetime import datetime, timezone
import re
import zipfile
from uuid import uuid4

from fastapi import APIRouter, Body, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.fs import ensure_within_base, resolve_project_path
from app.schemas.project import ContextSchema, ProjectSchema
from app.services import FWService, TemplateRegistry

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
PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{1,63}$")


def _extract_parameter_name(raw: str) -> str | None:
    match = PARAMETER_NAME_PATTERN.search(raw)
    if not match:
        return None
    return match.group(1)


def _collect_parameters(project_path: Path) -> list[dict[str, str]]:
    entries: dict[tuple[str, str], dict[str, str | None]] = {}

    global_params_dir = project_path / "parameters"
    for param_file in sorted(global_params_dir.glob("*.yml")) if global_params_dir.exists() else []:
        name = _extract_parameter_name(param_file.read_text(encoding="utf-8"))
        if not name:
            name = param_file.stem
        domain_type, value_type = _extract_parameter_meta(param_file.read_text(encoding="utf-8"))
        key = ("global", name)
        entries[key] = {
            "name": name,
            "scope": "global",
            "path": str(param_file.relative_to(project_path)),
            "domain_type": domain_type,
            "value_type": value_type,
        }

    model_dir = project_path / "model"
    if model_dir.exists():
        for param_file in sorted(model_dir.glob("*/parameters/*.yml")):
            name = _extract_parameter_name(param_file.read_text(encoding="utf-8"))
            if not name:
                name = param_file.stem
            model_name = param_file.parents[1].name
            domain_type, value_type = _extract_parameter_meta(param_file.read_text(encoding="utf-8"))
            key = (f"model:{model_name}", name)
            entries[key] = {
                "name": name,
                "scope": f"model:{model_name}",
                "path": str(param_file.relative_to(project_path)),
                "domain_type": domain_type,
                "value_type": value_type,
            }

    return sorted(entries.values(), key=lambda item: (item["name"].lower(), item["scope"]))


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
    nodes: list[dict[str, object]] = []
    unique_params: set[str] = set()

    for folder in sorted(workflow_root.iterdir(), key=lambda p: p.name.lower()):
        if not folder.is_dir():
            continue
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


def _build_config_chain_response(
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

    return {
        "project_id": project_id,
        "model_id": model_id,
        "sql_path": relative_sql_path,
        "levels": levels,
        "resolved": resolved,
        "cte_settings": _extract_cte_settings(model_cfg_path),
        "generated_outputs": ["dqcr", "airflow", "oracle_plsql", "dbt"],
    }


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
    }
    history = _BUILD_HISTORY.setdefault(project_id, [])
    history.insert(0, result)
    _BUILD_HISTORY[project_id] = history[:20]
    return result


def _find_project_build(project_id: str, build_id: str) -> dict[str, object]:
    for item in _BUILD_HISTORY.get(project_id, []):
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


FW_SERVICE = FWService(
    projects_base_path=Path(settings.projects_path),
    model_loader=_resolve_model_path,
    lineage_nodes_builder=_collect_lineage_nodes,
    lineage_edges_builder=_collect_lineage_edges,
    validation_runner=_build_validation_result,
    generation_runner=_run_project_generation,
    template_registry=TemplateRegistry(templates=("dqcr", "airflow", "dbt", "oracle_plsql")),
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
    properties = properties_raw if isinstance(properties_raw, dict) else {}

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


@router.get("")
def list_projects() -> list[ProjectSchema]:
    base = Path(settings.projects_path)
    if not base.exists():
        base.mkdir(parents=True, exist_ok=True)

    projects = [
        ProjectSchema(id=item.name, name=item.name)
        for item in sorted(base.iterdir(), key=lambda p: p.name.lower())
        if item.is_dir() and not item.name.startswith(".")
    ]
    return projects


@router.post("")
def create_project(payload: dict[str, object] = Body(...)) -> dict[str, object]:
    base = Path(settings.projects_path)
    base.mkdir(parents=True, exist_ok=True)
    return _write_project_from_wizard(base, payload)


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


@router.get("/{project_id}/autocomplete")
def get_project_autocomplete(project_id: str) -> dict[str, list[dict[str, str | None]] | list[str]]:
    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    parameters = _collect_parameters(project_path)
    macros = [{"name": macro_name, "source": "builtin"} for macro_name in DEFAULT_MACROS]
    return {
        "parameters": parameters,
        "macros": macros,
        "config_keys": DQCR_CONFIG_KEYS,
    }


@router.get("/{project_id}/parameters")
def get_project_parameters(project_id: str) -> list[dict[str, object]]:
    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    return _collect_parameter_objects(project_path)


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

    return _parse_parameter_file(project_path, target_file)


@router.delete("/{project_id}/parameters/{parameter_id}")
def delete_project_parameter(project_id: str, parameter_id: str, scope: str | None = Query(default=None)) -> dict[str, object]:
    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    target_file = _resolve_parameter_file(project_path, parameter_id, scope)
    relative_path = str(target_file.relative_to(project_path))
    target_file.unlink()
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
def get_model_lineage(project_id: str, model_id: str) -> dict[str, object]:
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

    return {
        "project_id": project_id,
        "model_id": model_id,
        "path": str(model_yml_path.relative_to(project_path)),
        "model": _parse_model_yml_to_object(model_yml_path),
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

    return FW_SERVICE.run_generation(project_id, model_id, engine, context, dry_run, output_path)


@router.get("/{project_id}/build/history")
def get_project_build_history(project_id: str) -> list[dict[str, object]]:
    return _BUILD_HISTORY.get(project_id, [])[:10]


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

    result = FW_SERVICE.run_validation(project_id, model_id, categories_list)
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
