"""Oracle PL/SQL param syntax - uses bind variables."""
from typing import Any, Optional

from FW.models.param_types import DomainType


def render_param(
    var_name: str, 
    value: Any = None, 
    domain_type: str = DomainType.UNDEFINED,
    tool: Optional[str] = None
) -> str:
    """Рендерит параметр в синтаксисе Oracle PL/SQL (bind variables).
    
    Args:
        var_name: имя переменной
        value: значение (не используется, параметр для совместимости)
        domain_type: доменный тип параметра
        tool: целевой tool
        
    Returns:
        Строка вида :VAR_NAME или to_date(:VAR_NAME, 'yyyy-mm-dd') для дат
    """
    var_upper = var_name.upper()
    
    if domain_type == DomainType.DATE and tool == "oracle":
        return f"to_date(:{var_upper}, 'yyyy-mm-dd')"
    
    if domain_type == DomainType.NUMBER and tool == "oracle":
        return f"to_number(:{var_upper})"
    
    return f":{var_upper}"
