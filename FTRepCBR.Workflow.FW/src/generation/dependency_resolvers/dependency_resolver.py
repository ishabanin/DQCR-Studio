"""Generation - base dependency resolver."""
from abc import ABC, abstractmethod
from typing import List, Dict

class DependencyResolver(ABC):
    """Базовый класс для определения зависимостей между шагами."""
    
    @abstractmethod
    def resolve(self, steps: List[Dict]) -> None:
        """Определить зависимости между шагами.
        
        Args:
            steps: Список шагов workflow
        """
        pass
