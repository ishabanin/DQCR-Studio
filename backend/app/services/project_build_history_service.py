from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import json
from pathlib import Path

from app.core.fs import ensure_within_base


def _build_history_file(project_path: Path) -> Path:
    return ensure_within_base(project_path, project_path / ".dqcr_builds" / "history.json")


def _read_build_history_from_disk(project_path: Path, history_limit: int) -> list[dict[str, object]]:
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
    return parsed[:history_limit]


def _write_build_history_to_disk(project_path: Path, history: list[dict[str, object]], history_limit: int) -> None:
    history_file = _build_history_file(project_path)
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history_file.write_text(
        json.dumps(history[:history_limit], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


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


def _detect_model_from_generated_files(
    files: list[dict[str, object]],
    project_path: Path,
    list_model_ids_fn: Callable[[Path], list[str]],
) -> str:
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
    model_ids = list_model_ids_fn(project_path)
    return model_ids[0] if model_ids else "unknown"


def _discover_build_history_from_disk(
    project_id: str,
    project_path: Path,
    history_limit: int,
    list_model_ids_fn: Callable[[Path], list[str]],
    workflow_state_for_model_fn: Callable[[Path, str], dict[str, object]],
    workflow_updated_at_for_model_fn: Callable[[Path, str], str | None],
) -> list[dict[str, object]]:
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
        model_id = _detect_model_from_generated_files(files, project_path, list_model_ids_fn)
        mtime = datetime.fromtimestamp(output_dir.stat().st_mtime, tz=timezone.utc).isoformat()
        workflow_state = workflow_state_for_model_fn(project_path, model_id) if model_id and model_id != "unknown" else {}
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
                "workflow_updated_at": workflow_updated_at_for_model_fn(project_path, model_id) if model_id and model_id != "unknown" else None,
                "workflow_status": workflow_state.get("status"),
                "workflow_source": workflow_state.get("source"),
                "workflow_attached": bool(workflow_state.get("has_cache")),
                "discovered_from_disk": True,
            }
        )
        if len(discovered) >= history_limit:
            break
    return discovered[:history_limit]


def get_project_build_history(
    *,
    project_id: str,
    projects_base_path: Path,
    cache: dict[str, list[dict[str, object]]],
    history_limit: int,
    resolve_project_path_fn: Callable[[Path, str], Path],
    list_model_ids_fn: Callable[[Path], list[str]],
    workflow_state_for_model_fn: Callable[[Path, str], dict[str, object]],
    workflow_updated_at_for_model_fn: Callable[[Path, str], str | None],
) -> list[dict[str, object]]:
    cached = cache.get(project_id)
    if cached is not None:
        return cached[:history_limit]

    project_path = resolve_project_path_fn(projects_base_path, project_id)
    persisted = _read_build_history_from_disk(project_path, history_limit)
    if not persisted:
        persisted = _discover_build_history_from_disk(
            project_id=project_id,
            project_path=project_path,
            history_limit=history_limit,
            list_model_ids_fn=list_model_ids_fn,
            workflow_state_for_model_fn=workflow_state_for_model_fn,
            workflow_updated_at_for_model_fn=workflow_updated_at_for_model_fn,
        )
        if persisted:
            _write_build_history_to_disk(project_path, persisted, history_limit)
    cache[project_id] = persisted[:history_limit]
    return cache[project_id]


def record_build_result(
    *,
    project_id: str,
    result: dict[str, object],
    projects_base_path: Path,
    cache: dict[str, list[dict[str, object]]],
    history_limit: int,
    resolve_project_path_fn: Callable[[Path, str], Path],
    list_model_ids_fn: Callable[[Path], list[str]],
    workflow_state_for_model_fn: Callable[[Path, str], dict[str, object]],
    workflow_updated_at_for_model_fn: Callable[[Path, str], str | None],
) -> None:
    build_id = str(result.get("build_id", "")).strip()
    if not build_id:
        return
    history = list(
        get_project_build_history(
            project_id=project_id,
            projects_base_path=projects_base_path,
            cache=cache,
            history_limit=history_limit,
            resolve_project_path_fn=resolve_project_path_fn,
            list_model_ids_fn=list_model_ids_fn,
            workflow_state_for_model_fn=workflow_state_for_model_fn,
            workflow_updated_at_for_model_fn=workflow_updated_at_for_model_fn,
        )
    )
    history = [item for item in history if str(item.get("build_id")) != build_id]
    history.insert(0, result)
    history = history[:history_limit]
    cache[project_id] = history

    project_path = resolve_project_path_fn(projects_base_path, project_id)
    _write_build_history_to_disk(project_path, history, history_limit)
