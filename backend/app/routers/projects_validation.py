from __future__ import annotations

from fastapi import APIRouter, Body

from app.services.application.projects_use_cases import (
    apply_validation_quickfix_use_case,
    get_validation_history_use_case,
    run_project_validation_use_case,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/{project_id}/validate")
def run_project_validation(project_id: str, payload: dict[str, object] = Body(default={})) -> dict[str, object]:
    return run_project_validation_use_case(project_id, payload if isinstance(payload, dict) else {})


@router.post("/{project_id}/validate/quickfix")
def apply_validation_quickfix(project_id: str, payload: dict[str, object] = Body(default={})) -> dict[str, object]:
    return apply_validation_quickfix_use_case(project_id, payload if isinstance(payload, dict) else {})


@router.get("/{project_id}/validate/history")
def get_validation_history(project_id: str) -> list[dict[str, object]]:
    return get_validation_history_use_case(project_id)
