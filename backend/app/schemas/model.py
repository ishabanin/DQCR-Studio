from pydantic import BaseModel


class ModelSchema(BaseModel):
    id: str
    name: str
    path: str
