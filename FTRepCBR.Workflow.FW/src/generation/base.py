"""Generation - base workflow builder."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional

from FW.models import WorkflowNewModel
from FW.generation.dependency_resolvers.dependency_resolver import DependencyResolver

class BaseWorkflowBuilder(ABC):
    """Базовый класс для построителей workflow."""
    
    def __init__(
        self,
        project_path: Path,
        tool_registry,
        macro_registry,
        function_registry=None,
        dependency_resolver: Optional[DependencyResolver] = None,
        workflow_engine: str = None,
        resolver_name: str = "naming_convention"
    ):
        self.project_path = project_path
        self.tool_registry = tool_registry
        self.macro_registry = macro_registry
        self.function_registry = function_registry
    
    @abstractmethod
    def build(self, model_name: str) -> WorkflowNewModel:
        """Построить модель workflow для указанной модели.
        
        Args:
            model_name: Имя модели (таблицы)
            
        Returns:
            WorkflowModel
        """
        pass
    
    @abstractmethod
    def build_all(self) -> Dict[str, WorkflowNewModel]:
        """Построить модели workflow для всех моделей проекта.
        
        Returns:
            Dict[model_name: WorkflowModel]
        """
        pass
