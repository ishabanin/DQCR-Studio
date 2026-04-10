"""Parameter materialization macro.

Генерирует SQL для параметра на основе его типа и значения.

Примеры:
    - static number: SELECT '123' as param_name FROM DUAL (oracle)
    - static string: SELECT 'value' as param_name FROM DUAL
    - static array: SELECT 'val_0' as val_0 FROM DUAL UNION ALL ...
    - dynamic: возвращает prepared_sql напрямую

Работает с WorkflowNewModel через MacroEnv.
"""
from typing import Optional, TYPE_CHECKING, List, Dict, Any

from FW.logging_config import get_logger as _get_logger

if TYPE_CHECKING:
    from FW.models.workflow_new import WorkflowNewModel
    from FW.macros.env import BaseMacroEnv
    from FW.models.parameter import ParameterModel

logger = _get_logger("parameter.param")


DOMAIN_TYPE_MAP = {
    'date': 'date',
    'number': 'numeric',
    'numeric': 'numeric',
    'integer': 'integer',
    'int': 'integer',
}


def _get_param_value_for_context(
    param_model: "ParameterModel",
    context: str,
    all_contexts: List[str]
) -> Optional[Any]:
    """Получить значение параметра для конкретного контекста.
    
    Args:
        param_model: Модель параметра
        context: Имя контекста
        all_contexts: Все доступные контексты
        
    Returns:
        ParameterValue или None
    """
    if context in param_model.values:
        return param_model.values[context]
    
    if "all" in param_model.values:
        return param_model.values["all"]
    
    return None


def _generate_static_sql(
    param_model: "ParameterModel",
    param_value: Any,
    tool: str,
    context: str
) -> str:
    """Сгенерировать SQL для статического параметра.
    
    Args:
        param_model: Модель параметра
        param_value: Значение параметра
        tool: Целевой tool
        context: Имя контекста
        
    Returns:
        SQL для параметра
    """
    p_domain = param_model.domain_type
    p_name = param_model.name
    ptype = DOMAIN_TYPE_MAP.get(p_domain, 'text')
    
    val = param_value.value if param_value else ''
    if val is None:
        val = ''
    
    if isinstance(val, str):
        val = val.replace("'", "''") if val else ''
    elif val is not None:
        val = str(val).replace("'", "''")
    
    if isinstance(val, (list, tuple)):
        parts = []
        for i, row in enumerate(val):
            if isinstance(row, str):
                row = row.replace("'", "''")
            else:
                row = str(row).replace("'", "''")
            
            if tool == 'oracle':
                parts.append(f"SELECT '{row}' as val_{i} FROM DUAL")
            elif tool == 'postgresql':
                parts.append(f"SELECT '{row}'::{ptype} as val_{i}")
            else:
                parts.append(f"SELECT '{row}' as val_{i}")
        
        return ' UNION ALL '.join(parts)
    
    if tool == 'oracle':
        return f"SELECT '{val}' as {p_name} FROM DUAL"
    elif tool == 'postgresql':
        return f"SELECT '{val}'::{ptype} as {p_name}"
    else:
        return f"SELECT '{val}' as {p_name}"


def materialization_param(
    param_model: "Optional[ParameterModel]" = None,
    tool: Optional[str] = None,
    context: Optional[str] = None,
    workflow_new: "Optional[WorkflowNewModel]" = None,
    env: "Optional[BaseMacroEnv]" = None,
) -> str:
    """Сгенерировать SQL для параметра.
    
    Логика:
    1. Для dynamic параметров - возвращает prepared_sql напрямую (без обертки)
    2. Для static параметров - генерирует SELECT wrapper
    
    Args:
        param_model: Модель параметра
        tool: Целевой tool (oracle, adb, postgresql)
        context: Имя контекста
        workflow_new: WorkflowNewModel
        env: Окружение макроса
        
    Returns:
        SQL для параметра
    """
    if param_model is None:
        logger.warning("materialization_param called with no param_model")
        return ""
    
    if env is None or workflow_new is None:
        logger.warning("materialization_param called without env or workflow_new")
        return ""
    
    all_contexts = list(workflow_new.contexts.keys()) if workflow_new.contexts else ["all"]
    
    param_value = _get_param_value_for_context(param_model, context, all_contexts)
    
    if param_value is None:
        logger.debug(f"Parameter {param_model.name}: no value for context {context}")
        return ""
    
    is_dynamic = param_value.type == "dynamic"
    
    if is_dynamic:
        prepared_sql = param_value.value if param_value.value else ""
        logger.debug(f"Parameter {param_model.name}: dynamic SQL ({len(prepared_sql)} chars)")
        return prepared_sql
    
    static_sql = _generate_static_sql(param_model, param_value, tool, context)
    logger.debug(f"Parameter {param_model.name}: static SQL ({len(static_sql)} chars)")
    return static_sql


def resolve_parameter_macro(
    param_name: str,
    tool: str,
    context: str,
    workflow_new: "WorkflowNewModel",
    env: "BaseMacroEnv"
) -> str:
    """Получить значение параметра для подстановки в SQL.
    
    Вызывается при подстановке {{param_name}} в prepared_sql.
    
    Args:
        param_name: Имя параметра
        tool: Целевой tool
        context: Имя контекста
        workflow_new: WorkflowNewModel
        env: Окружение макроса
        
    Returns:
        Значение параметра для подстановки
    """
    param = env.get_parameter(param_name)
    
    if not param:
        logger.warning(f"Parameter '{param_name}' not found in workflow")
        return f"{{{{{param_name}}}}}"
    
    param_value = _get_param_value_for_context(param, context, list(workflow_new.contexts.keys()))
    
    if param_value is None:
        logger.warning(f"Parameter '{param_name}': no value for context {context}")
        return f"{{{{{param_name}}}}}"
    
    if param_value.type == "dynamic":
        compiled = env.get_compiled("parameter", param_name, context, tool)
        if compiled and compiled.get("prepared_sql"):
            return compiled.get("prepared_sql")
        
        if param_value.value:
            return param_value.value
    
    is_dynamic = param_value.type == "dynamic"
    
    if is_dynamic:
        return param_value.value if param_value.value else ""
    
    val = param_value.value if param_value.value else ''
    if val is None:
        val = ''
    if isinstance(val, str):
        return val
    
    return str(val)
