from pydantic import BaseModel


class ProjectSchema(BaseModel):
    id: str
    name: str
    source_type: str = "internal"
    source_path: str | None = None
    availability_status: str = "available"


class ContextSchema(BaseModel):
    id: str
    name: str
