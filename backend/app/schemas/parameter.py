from pydantic import BaseModel


class ParameterSchema(BaseModel):
    name: str
    scope: str
    domain_type: str
