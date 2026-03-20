"""Enabled rule model for workflow steps."""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class EnabledRule:
    """Правило включения шага/папки в workflow.
    
    Структура:
        enabled:
            contexts: [default, vtb]      # OR - любой из контекстов
            conditions:                   # AND - все условия должны выполниться
                sometype: TEST            # константа = значение
                heavy_calc: true          # флаг = true
                any:                      # OR - хотя бы одно из
                    overduecalcmethod.fifo: true
                    overduecalcmethod.lifo: true
    """
    contexts: Optional[List[str]] = None
    conditions: Optional[Dict[str, Any]] = None
    
    def evaluate(self, context_name: str, context_flags: Dict[str, Any], 
                 context_constants: Dict[str, Any]) -> bool:
        """Проверить, должен ли быть шаг включен.
        
        Args:
            context_name: имя текущего контекста
            context_flags: флаги контекста {flag_name: value}
            context_constants: константы контекста {const_name: value}
            
        Returns:
            True если шаг должен быть включен
        """
        if self.contexts and context_name not in self.contexts:
            return False
        
        if self.conditions is None:
            return True
        
        for key, expected_value in self.conditions.items():
            if key == "any":
                if not self._evaluate_any(expected_value, context_flags, context_constants):
                    return False
            else:
                actual_value = self._get_value(key, context_flags, context_constants)
                if actual_value != expected_value:
                    return False
        
        return True
    
    def _get_value(self, key: str, flags: Dict, constants: Dict) -> Any:
        """Получить значение по ключу (поддержка вложенных через точку)."""
        parts = key.split(".")
        
        if parts[0] in constants:
            value = constants[parts[0]]
            if len(parts) > 1 and isinstance(value, dict):
                for p in parts[1:]:
                    value = value.get(p)
            return value
        
        if parts[0] in flags:
            value = flags[parts[0]]
            if len(parts) > 1 and isinstance(value, dict):
                for p in parts[1:]:
                    value = value.get(p)
            return value
        
        return None
    
    def _evaluate_any(self, any_conditions: Dict[str, Any], 
                      flags: Dict, constants: Dict) -> bool:
        """Проверить блок any - хотя бы одно условие должно выполниться."""
        for key, expected_value in any_conditions.items():
            actual_value = self._get_value(key, flags, constants)
            if actual_value == expected_value:
                return True
        return False
    
    @staticmethod
    def from_dict(data: Any) -> Optional["EnabledRule"]:
        """Создать EnabledRule из словаря."""
        if data is None or data is True:
            return EnabledRule()
        if data is False:
            return EnabledRule(contexts=[], conditions={})
        
        if isinstance(data, dict):
            contexts = data.get("contexts")
            conditions = data.get("conditions")
            return EnabledRule(contexts=contexts, conditions=conditions)
        
        return None
    
    def to_dict(self) -> dict:
        """Сериализация."""
        result = {}
        if self.contexts:
            result["contexts"] = self.contexts
        if self.conditions:
            result["conditions"] = self.conditions
        return result


def parse_enabled(data: Any) -> Optional[EnabledRule]:
    """Упрощенная функция парсинга enabled."""
    return EnabledRule.from_dict(data)
