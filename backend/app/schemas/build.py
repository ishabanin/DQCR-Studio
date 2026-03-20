from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class BuildResult(BaseModel):
    build_id: str
    timestamp: datetime
    project: str
    engine: Literal["dqcr", "airflow", "dbt", "oracle_plsql"]
    context: str
    output_path: str
