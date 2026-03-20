"""Naming convention resolver."""
from typing import List

from FW.models import WorkflowStepModel, StepType


SCOPE_ORDER = {
    'flags': 0,
    'pre': 1,
    'params': 2,
    'sql': 3,
    'post': 4,
}


def _get_scope_order(scope: str) -> int:
    """Получить порядковый номер для scope.
    
    Args:
        scope: значение step_scope
    
    Returns:
        порядковый номер scope
    """
    return SCOPE_ORDER.get(scope, 99)


class NamingConventionResolver:
    """Определение зависимостей по naming convention.
    
    Сортировка внутри каждой папки:
    1. step_scope: flags -> pre -> params -> sql -> post
    2. full_name
    
    Зависимость: каждый шаг зависит от предыдущего в последовательности внутри папки.
    """
    
    def resolve(self, steps: List[WorkflowStepModel]) -> None:
        """Определить зависимости по naming convention.
        
        Сортируем: folder → scope → full_name
        Каждый шаг зависит от предыдущего в отсортированном списке.
        Если у шага уже есть dependencies - сохраняем.
        
        Args:
            steps: Список шагов workflow
        """
        if not steps:
            return
        
        sl = []
        for s in steps:
            sl.append({"scope" : s.step_scope if s.folder == "" else "sql",
                       "s" : s})  
                    
        sl_sorted = sorted(sl, key=self._get_sort_key__)
        #sorted_steps = sorted(steps, key=self._get_sort_key)

        for i, step in enumerate(sl_sorted):
            if i == 0:
                step["s"].dependencies = []
            else:    
                step["s"].dependencies = [sl_sorted[i-1]["s"].full_name]
            print("folder: {}, full_name: {}, scope: {}, dependencies: {}".format(step["s"].folder, step["s"].full_name, step["s"].step_scope, step["s"].dependencies))
    def _get_sort_key__(self, step: dict) -> tuple:
        return (_get_scope_order(step["scope"]), 
                 step["s"].folder, 
                 _get_scope_order(step["s"].step_scope), 
                 step["s"].full_name)
    
    def _get_sort_key(self, step: WorkflowStepModel) -> tuple:
        """Получить ключ сортировки для шага.
        
        Сортировка по:
        1. folder
        2. step_scope (flags, pre, params, sql, post)
        3. full_name
        """
        scope_order = _get_scope_order(step.step_scope)
        
        return (step.folder, scope_order, step.full_name)
