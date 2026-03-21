from pydantic import BaseModel


class ProjectSchema(BaseModel):
    id: str
    name: str
    description: str | None = None
    project_type: str = "internal"
    source_type: str = "internal"
    source_path: str | None = None
    availability_status: str = "available"
    visibility: str = "private"
    tags: list[str] = []
    model_count: int = 0
    folder_count: int = 0
    sql_count: int = 0
    modified_at: str
    cache_status: str = "missing"


class ContextSchema(BaseModel):
    id: str
    name: str
