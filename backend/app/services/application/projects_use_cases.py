from __future__ import annotations

import io
from pathlib import Path
import zipfile

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.fs import ensure_within_base, resolve_project_path
from app.services.project_facade_service import (
    append_validation_history,
    apply_quickfix_add_field,
    apply_quickfix_rename_folder,
    attach_workflow_context,
    build_files_tree,
    build_validation_result,
    find_project_build,
    get_fw_service,
    get_project_build_history,
    get_supported_build_engines,
    get_validation_history,
    record_build_result,
    render_engine_preview_sql,
    resolve_existing_build_output_dir,
    resolve_model_id_for_build,
    resolve_model_id_for_validation,
    resolve_model_id_from_file_path,
    resolve_model_path,
)


def run_project_build_use_case(project_id: str, payload: dict[str, object]) -> dict[str, object]:
    fw_service = get_fw_service()
    project_path = fw_service.load_project(project_id)

    model_id_raw = payload.get("model_id")
    model_id = resolve_model_id_for_build(project_path, model_id_raw if isinstance(model_id_raw, str) else None)

    engine_raw = payload.get("engine")
    engine = str(engine_raw).strip() if isinstance(engine_raw, str) and engine_raw.strip() else "dqcr"

    context_raw = payload.get("context")
    context = str(context_raw).strip() if isinstance(context_raw, str) and context_raw.strip() else "default"

    dry_run_raw = payload.get("dry_run")
    dry_run = bool(dry_run_raw) if dry_run_raw is not None else False

    output_path_raw = payload.get("output_path")
    output_path = str(output_path_raw).strip() if isinstance(output_path_raw, str) and output_path_raw.strip() else None

    result_raw = fw_service.run_generation(project_id, model_id, engine, context, dry_run, output_path)
    result = attach_workflow_context(result_raw, project_path, model_id)
    record_build_result(project_id, result)
    return result


def get_project_build_history_use_case(project_id: str) -> list[dict[str, object]]:
    return get_project_build_history(project_id)


def get_project_build_files_use_case(project_id: str, build_id: str) -> dict[str, object]:
    build_item = find_project_build(project_id, build_id)
    files_raw = build_item.get("files")
    files = files_raw if isinstance(files_raw, list) else []
    return {
        "project_id": project_id,
        "build_id": build_id,
        "engine": build_item.get("engine"),
        "output_path": build_item.get("output_path"),
        "files": files,
        "tree": build_files_tree([item for item in files if isinstance(item, dict)]),
    }


def download_project_build_use_case(project_id: str, build_id: str, path: str | None = None) -> StreamingResponse:
    output_dir = resolve_existing_build_output_dir(project_id, build_id)

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


def get_project_build_file_content_use_case(project_id: str, build_id: str, path: str) -> dict[str, str]:
    output_dir = resolve_existing_build_output_dir(project_id, build_id)
    target_file = ensure_within_base(output_dir, output_dir / path)
    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Build file '{path}' not found.")
    return {
        "build_id": build_id,
        "path": path,
        "content": target_file.read_text(encoding="utf-8", errors="ignore"),
    }


def preview_generated_sql_use_case(project_id: str, build_id: str, payload: dict[str, str]) -> dict[str, str]:
    model_id = payload.get("model_id")
    sql_path = payload.get("sql_path")
    inline_sql = payload.get("inline_sql")

    if not model_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="model_id is required.")
    if not sql_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sql_path is required.")

    build_item = find_project_build(project_id, build_id)
    engine_raw = build_item.get("engine")
    engine = str(engine_raw).strip() if isinstance(engine_raw, str) and engine_raw.strip() else ""
    if engine not in get_supported_build_engines():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Build '{build_id}' has unsupported engine '{engine or 'unknown'}'.",
        )

    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    _ = resolve_model_path(project_path, model_id)
    sql_file = ensure_within_base(project_path, project_path / sql_path)
    if not sql_file.exists() or not sql_file.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"SQL file '{sql_path}' not found.")

    raw_sql = inline_sql if inline_sql is not None else sql_file.read_text(encoding="utf-8")
    rendered = render_engine_preview_sql(raw_sql, engine)
    return {
        "project_id": project_id,
        "model_id": model_id,
        "build_id": build_id,
        "engine": engine,
        "sql_path": sql_path,
        "preview": rendered,
    }


def run_project_validation_use_case(project_id: str, payload: dict[str, object]) -> dict[str, object]:
    fw_service = get_fw_service()
    project_path = fw_service.load_project(project_id)

    model_id = resolve_model_id_for_validation(project_path, payload.get("model_id") if isinstance(payload, dict) else None)
    categories = payload.get("categories") if isinstance(payload, dict) else None
    categories_list = categories if isinstance(categories, list) else None

    result_raw = fw_service.run_validation(project_id, model_id, categories_list)
    result = attach_workflow_context(result_raw, project_path, model_id)
    append_validation_history(project_id, result)
    return result


def apply_validation_quickfix_use_case(project_id: str, payload: dict[str, object]) -> dict[str, object]:
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
        model_id = resolve_model_id_from_file_path(project_path, file_path_value)
    if model_id is None:
        model_id = resolve_model_id_for_validation(project_path, None)

    result: dict[str, object]
    if fix_type == "add_field":
        field_name = payload.get("field_name") if isinstance(payload, dict) else None
        field_name_value = field_name if isinstance(field_name, str) and field_name.strip() else "description"
        result = apply_quickfix_add_field(project_path, model_id, field_name_value)
    elif fix_type == "rename_folder":
        if not file_path_value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_path is required for rename_folder.")
        new_name = payload.get("new_name") if isinstance(payload, dict) else None
        new_name_value = new_name if isinstance(new_name, str) else None
        result = apply_quickfix_rename_folder(project_path, file_path_value, new_name_value)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported quickfix type '{fix_type}'.")

    rerun_payload = payload.get("rerun") if isinstance(payload, dict) else None
    rerun = bool(rerun_payload) if rerun_payload is not None else True
    validation_result: dict[str, object] | None = None
    if rerun:
        validation_result = build_validation_result(project_path, project_id, model_id, None)
        append_validation_history(project_id, validation_result)

    return {
        "project_id": project_id,
        "model_id": model_id,
        "type": fix_type,
        **result,
        "validation": validation_result,
    }


def get_validation_history_use_case(project_id: str) -> list[dict[str, object]]:
    return get_validation_history(project_id, limit=5)
