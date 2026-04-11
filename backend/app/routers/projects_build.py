from __future__ import annotations

from fastapi import APIRouter, Body, Query
from fastapi.responses import StreamingResponse

from app.services.application.projects_use_cases import (
    download_project_build_use_case,
    get_project_build_file_content_use_case,
    get_project_build_files_use_case,
    get_project_build_history_use_case,
    preview_generated_sql_use_case,
    run_project_build_use_case,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/{project_id}/build")
def run_project_build(project_id: str, payload: dict[str, object] = Body(default={})) -> dict[str, object]:
    return run_project_build_use_case(project_id, payload if isinstance(payload, dict) else {})


@router.get("/{project_id}/build/history")
def get_project_build_history(project_id: str) -> list[dict[str, object]]:
    return get_project_build_history_use_case(project_id)


@router.get("/{project_id}/build/{build_id}/files")
def get_project_build_files(project_id: str, build_id: str) -> dict[str, object]:
    return get_project_build_files_use_case(project_id, build_id)


@router.get("/{project_id}/build/{build_id}/download")
def download_project_build(project_id: str, build_id: str, path: str | None = Query(default=None)) -> StreamingResponse:
    return download_project_build_use_case(project_id, build_id, path)


@router.get("/{project_id}/build/{build_id}/files/content")
def get_project_build_file_content(project_id: str, build_id: str, path: str = Query(...)) -> dict[str, str]:
    return get_project_build_file_content_use_case(project_id, build_id, path)


@router.post("/{project_id}/build/{build_id}/preview")
def preview_generated_sql(
    project_id: str,
    build_id: str,
    payload: dict[str, str] = Body(...),
) -> dict[str, str]:
    return preview_generated_sql_use_case(project_id, build_id, payload if isinstance(payload, dict) else {})
