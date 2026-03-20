from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, status


def ensure_within_base(base_path: Path, requested_path: Path) -> Path:
    """Return resolved path only if it stays within base_path."""
    base_resolved = base_path.resolve()
    requested_resolved = requested_path.resolve()

    if requested_resolved == base_resolved or base_resolved in requested_resolved.parents:
        return requested_resolved

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Path traversal attempt detected.",
    )


def resolve_project_path(base_projects_path: Path, project_id: str) -> Path:
    project_path = ensure_within_base(base_projects_path, base_projects_path / project_id)
    if not project_path.exists() or not project_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )
    return project_path

