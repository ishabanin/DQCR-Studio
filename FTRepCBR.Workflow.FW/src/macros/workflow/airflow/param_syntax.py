"""Airflow param syntax - uses Jinja2 template syntax."""
from typing import Any, Optional

from FW.models.param_types import DomainType


def render_param(
    var_name: str, 
    value: Any = None, 
    domain_type: str = DomainType.UNDEFINED,
    tool: Optional[str] = None
) -> str:
    """Рендерит параметр в синтаксисе Airflow (Jinja2).
    
    Args:
        var_name: имя переменной
        value: значение (не используется, параметр для совместимости)
        domain_type: доменный тип параметра
        tool: целевой tool
        
    Returns:
        Строка вида get_param('var_name')
    """
    if domain_type == DomainType.STRING:
       return f"':{var_name}:'"
    if domain_type == DomainType.DATE:
       return f"to_date(':{var_name}:','yyyymmdd'"
    else:
       return f":{var_name}:"
