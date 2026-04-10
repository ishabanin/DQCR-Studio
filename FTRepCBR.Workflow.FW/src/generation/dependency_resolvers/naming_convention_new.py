"""Naming Convention Resolver для workflow_new."""

from typing import Dict, Any, List
from FW.logging_config import get_logger

logger = get_logger("naming_convention_new")


SCOPE_ORDER = {
    "flags": 0,
    "pre": 1,
    "params": 2,
    "sql": 3,
    "flag": 2,
    "param": 2,
    "post": 4,
}


def _get_scope_order(scope: str) -> int:
    return SCOPE_ORDER.get(scope, 99)


class NamingConventionResolverNew:
    """Resolver для workflow_new на основе naming convention.
    
    Сортировка:
    1. folder (папка)
    2. step_scope (flags -> pre -> params -> sql -> post)
    3. full_name
    
    Зависимости: каждый шаг зависит от предыдущего в отсортированном списке.
    """
    
    def resolve(
        self, 
        graph_context_tool: Dict[str, Dict[str, Any]]
    ) -> None:
        """Заполнить edges для графа конкретного context/tool.
        
        Args:
            graph_context_tool: {
                "steps": {
                    "object_id": {
                        "context": "...",
                        "tool": "...",
                        "step_type": "sql"|"param",
                        "step_scope": "...",
                        "object_id": "...",
                        "asynch": bool
                    }
                },
                "edges": []  # заполняется этим методом
            }
        """
        steps = graph_context_tool.get("steps", {})
        if not steps:
            graph_context_tool["edges"] = []
            return
        
        sorted_steps = self._sort_steps(steps)
        
        edges = []
        for i, step in enumerate(sorted_steps):
            if i == 0:
                edges.append({
                    "from": "START",
                    "to": step["step_key"],
                })
            else:
                prev_step = sorted_steps[i - 1]
                edges.append({
                    "from": prev_step["step_key"],
                    "to": step["step_key"],
                })
        
        last_step = sorted_steps[-1] if sorted_steps else None
        if last_step:
            edges.append({
                "from": last_step["step_key"],
                "to": "FINISH",
            })
        
        graph_context_tool["edges"] = edges
        
        logger.debug(f"Resolved {len(edges)} edges for context/tool")
    
    def _sort_steps(self, steps: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Отсортировать шаги по folder -> scope -> object_id.
        
        Args:
            steps: словарь шагов {step_key: step_data}
        
        Returns:
            Отсортированный список шагов с добавленными полями folder, object_id, step_key
        """
        step_list = []
        
        for step_key, step_data in steps.items():
            object_id = step_data.get("object_id", step_key)
            folder, full_name = self._extract_folder_and_name(object_id, step_data)
            
            step_scope = step_data.get("step_scope", "sql")
            effective_scope = step_scope if folder == "" else "sql"
            
            step_with_meta = {
                **step_data,
                "step_key": step_key,
                "object_id": object_id,
                "folder": folder,
                "full_name": full_name,
                "effective_scope": effective_scope,
            }
            step_list.append(step_with_meta)
        
        def sort_key(s):
            folder = s["folder"]
            scope = _get_scope_order(s["effective_scope"])
            obj_id = s["object_id"]
            
            is_cte = ".cte." in obj_id
            sort_id = obj_id if not is_cte else obj_id.replace(".cte.", ".z_cte.")
            
            return (folder, scope, sort_id)
        
        sorted_steps = sorted(step_list, key=sort_key)
        
        return sorted_steps
    
    def _extract_folder_and_name(
        self, 
        object_id: str, 
        step_data: Dict[str, Any]
    ) -> tuple[str, str]:
        """Извлечь folder и full_name из object_id.
        
        Args:
            object_id: идентификатор объекта (путь к файлу или имя параметра)
            step_data: данные шага
        
        Returns:
            (folder, full_name)
        """
        step_type = step_data.get("step_type", "sql")
        
        if step_type == "param":
            return ("", object_id)
        
        normalized_id = object_id
        if normalized_id.startswith("SQL/"):
            normalized_id = normalized_id[4:]
        
        if "/" in normalized_id:
            parts = normalized_id.rsplit("/", 1)
            folder = parts[0] if parts[0] else ""
            name = parts[1] if len(parts) > 1 else normalized_id
        else:
            folder = ""
            name = normalized_id
        
        if "." in name:
            name = name.rsplit(".", 1)[0]
        
        full_name = f"{folder}/{name}" if folder else name
        
        return (folder, full_name)