"""dbt param syntax - uses Jinja2 template syntax (same as Airflow)."""
from typing import Any, Optional

from FW.models.param_types import DomainType


def render_param(
    var_name: str, 
    value: Any = None, 
    domain_type: str = DomainType.UNDEFINED,
    tool: Optional[str] = None
) -> str:
    """Рендерит параметр в синтаксисе dbt (Jinja2).
    
    Args:
        var_name: имя переменной
        value: значение (не используется, параметр для совместимости)
        domain_type: доменный тип параметра
        tool: целевой tool
        
    Returns:
        Строка вида {{ var_name }}
    """
    return f"{{{{ {var_name} }}}}"
