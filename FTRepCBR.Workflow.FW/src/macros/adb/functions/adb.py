"""Tool-specific функции для ADB (ADB Data Warehouse).

Переопределяют базовые функции из base.py там, где синтаксис отличается.

Каждая функция имеет последними параметрами:
- workflow: WorkflowNewModel - модель workflow
- obj_type: str - тип объекта ("sql_object" или "parameter")
- obj_key: str - ключ объекта
"""

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from FW.models.workflow_new import WorkflowNewModel
    from FW.macros.env import BaseMacroEnv


def date_trunc(part, value, workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """ADB DATE_TRUNC."""
    return f"DATE_TRUNC('{part}', {value})"


def date_add(part, value, interval, workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """ADB DATE_ADD."""
    return f"DATE_ADD({value}, INTERVAL {interval} {part})"


def date_sub(part, value, interval, workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """ADB DATE_SUB."""
    return f"DATE_SUB({value}, INTERVAL {interval} {part})"


def string_agg(column, delimiter=',', workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """ADB STRING_AGG."""
    return f"STRING_AGG({column}, '{delimiter}')"


def enum2str(p_enum_code, workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """ADB: Перекодировка enum кода в наименование.
    
    Специфичная реализация для ADB.
    """
    return f"/* TODO: enum2str ADB({p_enum_code}) */"
