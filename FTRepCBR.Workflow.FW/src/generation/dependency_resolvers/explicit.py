"""Explicit dependency resolver."""
from typing import List, Dict

class ExplicitDependencyResolver:
    """Явное указание зависимостей в конфигурации.
    
    Зависимости указываются напрямую в step.dependencies при создании.
    Этот resolver не меняет зависимости - они уже установлены.
    """
    
    def resolve(self, steps: List[Dict]) -> None:
        """Не делаем ничего - зависимости уже установлены явно.
        
        Args:
            steps: Список шагов workflow
        """
        pass
