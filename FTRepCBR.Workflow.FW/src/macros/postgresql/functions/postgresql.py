"""Tool-specific функции для PostgreSQL.

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


def to_timestamp(value, format_mask=None, workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """PostgreSQL TO_TIMESTAMP."""
    if format_mask:
        return f"TO_TIMESTAMP({value}, '{format_mask}')"
    return f"TO_TIMESTAMP({value})"


def age(date1, date2=None, workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """PostgreSQL AGE."""
    if date2:
        return f"AGE({date1}, {date2})"
    return f"AGE({date1})"


def extract(part, value, workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """PostgreSQL EXTRACT."""
    return f"EXTRACT({part} FROM {value})"


def array_agg(column, workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """PostgreSQL ARRAY_AGG."""
    return f"ARRAY_AGG({column})"


def unnest(array, workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """PostgreSQL UNNEST."""
    return f"UNNEST({array})"


def merge_into(target, source, on, matched_update=None, not_matched_insert=None, workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """PostgreSQL MERGE (not directly supported)."""
    return f"/* MERGE not directly supported in PostgreSQL */"


def enum2str(p_enum_code, workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """PostgreSQL: Перекодировка enum кода в наименование.
    
    Специфичная реализация для PostgreSQL.
    """
    return f"/* TODO: enum2str PostgreSQL({p_enum_code}) */"


def nvl(value, default, workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """NVL - базовая реализация."""
    return f"COALESCE({value}, {default})"
