from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import HTTPException, status


def build_files_tree(items: list[dict[str, object]]) -> dict[str, object]:
    root: dict[str, object] = {"name": ".", "path": "", "type": "directory", "children": []}

    def ensure_child(node: dict[str, object], name: str, path: str, node_type: str) -> dict[str, object]:
        children = node.setdefault("children", [])
        if not isinstance(children, list):
            children = []
            node["children"] = children
        for child in children:
            if isinstance(child, dict) and child.get("name") == name and child.get("type") == node_type:
                return child
        child = {"name": name, "path": path, "type": node_type}
        if node_type == "directory":
            child["children"] = []
        children.append(child)
        return child

    for item in items:
        raw_path = item.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        parts = [part for part in raw_path.replace("\\", "/").split("/") if part]
        node = root
        accumulated: list[str] = []
        for idx, part in enumerate(parts):
            accumulated.append(part)
            is_last = idx == len(parts) - 1
            node_type = "file" if is_last else "directory"
            node = ensure_child(node, part, "/".join(accumulated), node_type)
        if isinstance(node, dict):
            node["size_bytes"] = item.get("size_bytes")

    return root


def render_engine_preview_sql(raw_sql: str, engine: str) -> str:
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


def resolve_model_id_for_validation(
    project_path: Path,
    explicit_model_id: str | None,
    resolve_model_path_fn: Callable[[Path, str], Path],
) -> str:
    if explicit_model_id:
        _ = resolve_model_path_fn(project_path, explicit_model_id)
        return explicit_model_id

    model_root = project_path / "model"
    candidates = sorted([item.name for item in model_root.iterdir() if item.is_dir()], key=str.lower) if model_root.exists() else []
    if not candidates:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No models found in project.")
    return candidates[0]


def extract_model_id_from_project_path(path: str) -> str | None:
    normalized = path.replace("\\", "/").strip().strip("/")
    if not normalized:
        return None
    parts = [part for part in normalized.split("/") if part]
    if len(parts) < 2:
        return None
    if parts[0].lower() not in {"model", "models"}:
        return None
    return parts[1]


def resolve_models_for_rebuild(
    project_path: Path,
    changed_paths: list[str] | None,
    list_model_ids_fn: Callable[[Path], list[str]],
) -> list[str]:
    all_models = list_model_ids_fn(project_path)
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
        model_id = extract_model_id_from_project_path(normalized)
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
