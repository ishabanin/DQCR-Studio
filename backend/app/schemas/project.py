from pydantic import BaseModel


class ProjectSchema(BaseModel):
    id: str
    name: str


class ContextSchema(BaseModel):
    id: str
    name: str
