"""Generation - base dependency resolver."""
from abc import ABC, abstractmethod
from typing import List

from FW.models import WorkflowStepModel


class DependencyResolver(ABC):
    """Базовый класс для определения зависимостей между шагами."""
    
    @abstractmethod
    def resolve(self, steps: List[WorkflowStepModel]) -> None:
        """Определить зависимости между шагами.
        
        Args:
            steps: Список шагов workflow
        """
        pass
