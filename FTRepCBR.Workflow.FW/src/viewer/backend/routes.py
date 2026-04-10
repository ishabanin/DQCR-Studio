"""API routes for FW viewer."""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from . import services


router = APIRouter()


class LoadProjectRequest(BaseModel):
    path: str


class LoadProjectResponse(BaseModel):
    project_name: str
    models: list[str]
    contexts: list[str]


class WorkflowRequest(BaseModel):
    project_path: str
    model_name: str
    context: Optional[str] = None


@router.post("/api/project/load", response_model=LoadProjectResponse)
async def load_project(request: LoadProjectRequest):
    """Load project and return available models and contexts."""
    project_path = Path(request.path)
    
    if not project_path.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {request.path}")
    
    if not (project_path / "project.yml").exists():
        raise HTTPException(status_code=400, detail="Not a valid FW project (no project.yml)")
    
    models = services.list_models_in_project(project_path)
    contexts = services.list_contexts_in_project(project_path)
    
    return LoadProjectResponse(
        project_name=project_path.name,
        models=models,
        contexts=contexts
    )


@router.get("/api/project/tree")
async def get_project_tree(
    project_path: str,
    model_name: Optional[str] = None
):
    """Get project tree structure."""
    path = Path(project_path)
    
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_path}")
    
    return services.get_project_tree(path, model_name)


@router.get("/api/config/project")
async def get_project_config(project_path: str):
    """Get project.yml config."""
    path = Path(project_path)
    
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Project not found: {project_path}")
    
    try:
        return services.load_project_config(path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/config")
async def get_config(
    project_path: str,
    type: str,
    path: str
):
    """Get config file by type and path."""
    base_path = Path(project_path)
    
    try:
        return services.load_config(base_path, type, path)
    except services.ViewerServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/workflow")
async def build_workflow(request: WorkflowRequest):
    """Build workflow model."""
    try:
        return services.build_workflow(
            request.project_path,
            request.model_name,
            request.context
        )
    except services.ViewerServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/sql")
async def get_sql_file(path: str):
    """Get SQL file content."""
    sql_path = Path(path)
    
    if not sql_path.exists():
        raise HTTPException(status_code=404, detail=f"SQL file not found: {path}")
    
    try:
        with open(sql_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"content": content, "path": str(sql_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/materializations")
async def get_materializations():
    """Get list of available materialization types."""
    return services.get_available_materializations()


class ValidateRequest(BaseModel):
    project_path: str
    model_name: str
    context: Optional[str] = None


@router.post("/api/validate")
async def validate_workflow(request: ValidateRequest):
    """Validate workflow and return validation report."""
    try:
        return services.validate_workflow(
            request.project_path,
            request.model_name,
            request.context
        )
    except services.ViewerServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
