from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.fs import ensure_within_base, resolve_project_path
from app.routers.projects import ensure_project_workflow_cache, trigger_workflow_rebuild

router = APIRouter(prefix="/projects/{project_id}/files", tags=["files"])


class FileNode(BaseModel):
    name: str
    path: str
    type: str
    children: list["FileNode"] | None = None


class FileContentRequest(BaseModel):
    path: str
    content: str


class RenameRequest(BaseModel):
    path: str
    new_name: str


class FolderCreateRequest(BaseModel):
    path: str


FileNode.model_rebuild()


def _build_tree(root: Path, current: Path) -> FileNode:
    relative = current.relative_to(root)
    node_path = str(relative) if str(relative) else "."

    if current.is_file():
        return FileNode(name=current.name, path=node_path, type="file")

    children = sorted(current.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
    return FileNode(
        name=current.name if node_path != "." else root.name,
        path=node_path,
        type="directory",
        children=[_build_tree(root, child) for child in children],
    )


@router.get("/tree")
def get_files_tree(project_id: str) -> FileNode:
    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    ensure_project_workflow_cache(project_id)
    return _build_tree(project_path, project_path)


@router.get("/content")
def get_file_content(project_id: str, path: str = Query(..., min_length=1)) -> dict[str, str]:
    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    target = ensure_within_base(project_path, project_path / path)

    if not target.exists() or not target.is_file():
        return {"path": path, "content": ""}

    return {"path": path, "content": target.read_text(encoding="utf-8")}


@router.put("/content")
def put_file_content(project_id: str, payload: FileContentRequest = Body(...)) -> dict[str, str]:
    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    target = ensure_within_base(project_path, project_path / payload.path)

    if target.exists() and not target.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path '{payload.path}' is not a file.",
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.content, encoding="utf-8")
    trigger_workflow_rebuild(project_id, changed_paths=[payload.path])
    return {"status": "saved", "path": payload.path}


@router.post("/folder")
def create_folder(project_id: str, payload: FolderCreateRequest = Body(...)) -> dict[str, str]:
    normalized_path = payload.path.strip().strip("/")
    if not normalized_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Folder path is required.",
        )

    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    target = ensure_within_base(project_path, project_path / normalized_path)

    if target.exists() and not target.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path '{normalized_path}' already exists and is not a directory.",
        )

    target.mkdir(parents=True, exist_ok=True)
    relative_path = str(target.relative_to(project_path))
    trigger_workflow_rebuild(project_id, changed_paths=[relative_path])
    return {"status": "created", "path": relative_path}


@router.post("/rename")
def rename_file_or_directory(project_id: str, payload: RenameRequest = Body(...)) -> dict[str, str]:
    if "/" in payload.new_name or "\\" in payload.new_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New name must not contain path separators.",
        )

    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    source = ensure_within_base(project_path, project_path / payload.path)

    if not source.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Path '{payload.path}' not found.",
        )

    target = ensure_within_base(project_path, source.parent / payload.new_name)
    source.rename(target)
    trigger_workflow_rebuild(
        project_id,
        changed_paths=[payload.path, str(target.relative_to(project_path))],
    )
    return {
        "status": "renamed",
        "from": payload.path,
        "to": str(target.relative_to(project_path)),
    }


@router.delete("")
def delete_file_or_directory(project_id: str, path: str = Query(..., min_length=1)) -> dict[str, str]:
    base_projects = Path(settings.projects_path)
    project_path = resolve_project_path(base_projects, project_id)
    target = ensure_within_base(project_path, project_path / path)

    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Path '{path}' not found.",
        )

    if target.is_file():
        target.unlink()
    else:
        for child in sorted(target.rglob("*"), reverse=True):
            if child.is_file():
                child.unlink()
            else:
                child.rmdir()
        target.rmdir()

    trigger_workflow_rebuild(project_id, changed_paths=[path])
    return {"status": "deleted", "path": path}
