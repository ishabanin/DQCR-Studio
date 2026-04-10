"""Tool-specific функции для Oracle.

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


def nvl2(value, not_null, null, workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """Oracle NVL2."""
    return f"NVL2({value}, {not_null}, {null})"


def decode(*args, workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """Oracle DECODE."""
    args_list = list(args)
    sql_args = args_list[:-4] if len(args_list) > 4 else args_list
    if not sql_args or len(sql_args) < 3:
        return str(sql_args[0]) if sql_args else ""
    return f"DECODE({', '.join(str(a) for a in sql_args)})"


def trunc_date(date_val, format_mask='DD', workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """Oracle TRUNC for dates."""
    return f"TRUNC({date_val}, '{format_mask}')"


def add_months(date_val, months, workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """Oracle ADD_MONTHS."""
    return f"ADD_MONTHS({date_val}, {months})"


def months_between(date1, date2, workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """Oracle MONTHS_BETWEEN."""
    return f"MONTHS_BETWEEN({date1}, {date2})"


def listagg(column, delimiter=',', order_by=None, workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """Oracle LISTAGG."""
    order_by_str = f" ORDER BY {order_by}" if order_by else ""
    return f"LISTAGG({column}, '{delimiter}'){order_by_str} WITHIN GROUP()"


def enum2str(p_enum_code, workflow: "Optional[Any]" = None, env: "Optional[Any]" = None, obj_type: "Optional[str]" = None, obj_key: "Optional[str]" = None):
    """Oracle: Перекодировка enum кода в наименование.
    
    Специфичная реализация для Oracle.
    """
    return f"/* TODO: enum2str Oracle({p_enum_code}) */"
