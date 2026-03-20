"""Workflow step model."""
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass, field

from FW.models.sql_query import SQLQueryModel
from FW.models.parameter import ParameterModel


class StepType(Enum):
    """Тип шага workflow."""
    SQL = "sql"
    PARAM = "param"
    SYNC_POINT = "sync_point"
    LOOP = "loop"
    END_LOOP = "end_loop"


@dataclass
class WorkflowStepModel:
    """Модель шага workflow."""
    step_id: str
    name: str
    folder: str
    full_name: str
    step_type: StepType
    step_scope: str = ""  # flags, pre, params, sql, post
    sql_model: Optional[SQLQueryModel] = None
    param_model: Optional[ParameterModel] = None
    dependencies: List[str] = field(default_factory=list)
    context: str = "all"
    is_ephemeral: bool = False
    enabled: bool = True
    asynch: bool = False
    loop_step_ref: Optional[str] = None
    tools: Optional[List[str]] = None
    
    def is_sql_step(self) -> bool:
        """Является ли шаг SQL."""
        return self.step_type == StepType.SQL
    
    def is_param_step(self) -> bool:
        """Является ли шаг параметром."""
        return self.step_type == StepType.PARAM
    
    def to_dict(self) -> dict:
        """Сериализация."""
        return {
            'step_id': self.step_id,
            'name': self.name,
            'folder': self.folder,
            'full_name': self.full_name,
            'step_type': self.step_type.value,
            'step_scope': self.step_scope,
            'sql_model': self.sql_model.to_dict() if self.sql_model else None,
            'param_model': self.param_model.to_dict() if self.param_model else None,
            'dependencies': self.dependencies,
            'context': self.context,
            'is_ephemeral': self.is_ephemeral,
            'enabled': self.enabled,
            'asynch': self.asynch,
            'loop_step_ref': self.loop_step_ref,
            'tools': self.tools,
        }
