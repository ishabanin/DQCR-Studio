"""Graph based resolver."""
from typing import List

from FW.models import WorkflowStepModel


class GraphBasedResolver:
    """Определение зависимостей по анализу SQL (таблицы, CTE).
    
    Анализирует FROM/JOIN для построения графа зависимостей.
    """
    
    def resolve(self, steps: List[WorkflowStepModel]) -> None:
        """Определить зависимости по анализу SQL.
        
        Args:
            steps: Список шагов workflow
        """
        if not steps:
            return
        
        for step in steps:
            if step.sql_model and step.sql_model.metadata:
                tables = step.sql_model.metadata.tables
                
                dependencies = []
                for table_name, table_info in tables.items():
                    for other_step in steps:
                        if other_step.full_name == step.full_name:
                            continue
                        if other_step.sql_model and other_step.sql_model.metadata:
                            other_tables = other_step.sql_model.metadata.tables
                            if table_name in other_tables:
                                if other_step.full_name not in dependencies:
                                    dependencies.append(other_step.full_name)
                
                step.dependencies = dependencies
