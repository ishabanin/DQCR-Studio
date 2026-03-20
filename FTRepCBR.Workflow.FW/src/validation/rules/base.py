"""Base validation rule."""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional, Type

from FW.validation.models import ValidationIssue, ValidationLevel

if TYPE_CHECKING:
    from FW.models.workflow import WorkflowModel


class BaseValidationRule(ABC):
    """Базовый класс для правил валидации.
    
    Каждое правило должно:
    - Определить атрибуты name, category, level
    - Реализовать метод validate()
    
    Пример использования:
        class NoHintsRule(BaseValidationRule):
            name = "no_sql_hints"
            category = "sql"
            level = ValidationLevel.WARNING
            
            def validate(self, workflow: "WorkflowModel") -> List[ValidationIssue]:
                issues = []
                for step in workflow.steps:
                    if step.sql_model and "/*+" in step.sql_model.source_sql:
                        issues.append(ValidationIssue(...))
                return issues
    """
    
    name: str = ""
    category: str = "general"
    level: ValidationLevel = ValidationLevel.WARNING
    description: str = ""
    
    @abstractmethod
    def validate(self, workflow: "WorkflowModel") -> List[ValidationIssue]:
        """Выполнить проверку правила.
        
        Args:
            workflow: Модель workflow для проверки
            
        Returns:
            Список найденных проблем
        """
        pass
    
    def get_metadata(self) -> dict:
        """Получить метаданные правила."""
        return {
            "name": self.name,
            "category": self.category,
            "level": self.level.value,
            "description": self.description,
        }


class ValidationRuleRegistry:
    """Реестр правил валидации.
    
    Загружает и хранит все доступные правила.
    """
    
    def __init__(self):
        self._rules: List[Type[BaseValidationRule]] = []
        self._rules_by_category: dict = {}
        self._load_builtin_rules()
    
    def _load_builtin_rules(self):
        """Загрузить встроенные правила."""
        from FW.validation.rules import sql
        from FW.validation.rules import adb
        from FW.validation.rules import descriptions
        from FW.validation.rules import general
        
        for module in [sql, adb, descriptions, general]:
            for attr_name in dir(module):
                if attr_name.startswith('_'):
                    continue
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type) 
                    and issubclass(attr, BaseValidationRule) 
                    and attr is not BaseValidationRule
                ):
                    self.register(attr)
    
    def register(self, rule_class: Type[BaseValidationRule]):
        """Зарегистрировать правило."""
        if rule_class not in self._rules:
            self._rules.append(rule_class)
            
            instance = rule_class()
            category = instance.category
            if category not in self._rules_by_category:
                self._rules_by_category[category] = []
            self._rules_by_category[category].append(rule_class)
    
    def get_rules_for_categories(self, categories: List[str]) -> List[Type[BaseValidationRule]]:
        """Получить правила для указанных категорий.
        
        Args:
            categories: Список категорий ['sql', 'adb', 'descriptions', 'general']
            
        Returns:
            Список классов правил
        """
        result = []
        for category in categories:
            if category in self._rules_by_category:
                result.extend(self._rules_by_category[category])
        
        if "all" in categories or not categories:
            result = self._rules.copy()
        
        return result
    
    def get_all_categories(self) -> List[str]:
        """Получить список всех доступных категорий."""
        return list(self._rules_by_category.keys())
    
    def get_all_rules(self) -> List[Type[BaseValidationRule]]:
        """Получить все правила."""
        return self._rules.copy()


_default_registry: Optional[ValidationRuleRegistry] = None


def get_validation_rule_registry() -> ValidationRuleRegistry:
    """Получить глобальный экземпляр реестра правил."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ValidationRuleRegistry()
    return _default_registry
