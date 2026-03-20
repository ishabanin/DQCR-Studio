"""Workflow engine model."""
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class WorkflowEngineModel:
    """Модель workflow engine.
    
    Атрибуты:
        name: имя движка (airflow, dbt, oracle_plsql)
        macro_path: путь к макросам движка
    """
    name: str
    macro_path: str
    
    @staticmethod
    def from_dict(name: str, data: Dict) -> "WorkflowEngineModel":
        """Создать из словаря."""
        return WorkflowEngineModel(
            name=name,
            macro_path=data.get("macro_path", f"workflow/{name}")
        )
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "macro_path": self.macro_path
        }
