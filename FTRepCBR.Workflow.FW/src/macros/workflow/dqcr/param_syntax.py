"""dqcr param syntax - uses :var_name: template syntax."""
from typing import Any, Optional

from FW.models.param_types import DomainType


def render_param(
    var_name: str, 
    value: Any = None, 
    domain_type: str = DomainType.UNDEFINED,
    tool: Optional[str] = None
) -> str:
    """Рендерит параметр в синтаксисе dqcr (:var_name:).
    
    Args:
        var_name: имя переменной
        value: значение (не используется, параметр для совместимости)
        domain_type: доменный тип параметра
        tool: целевой tool
        
    Returns:
        Строка вида :var_name:
    """
    if domain_type == DomainType.DATE:       
       return f"to_date(':{var_name}:','yyyymmdd')"
    if domain_type == DomainType.STRING:
       if tool in ("adb","postgresql"):
          return f"$$:{var_name}:$$"   
       if tool == "oracle":
          return f"q'[:{var_name}:]'"
       return f"':{var_name}:'"
    return f":{var_name}:"