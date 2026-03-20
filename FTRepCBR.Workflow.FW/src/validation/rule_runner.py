"""Validation rule runner."""
from typing import List, Optional, Type
import logging

from FW.validation.models import ValidationIssue, ValidationReport, ValidationLevel
from FW.validation.rules.base import BaseValidationRule, get_validation_rule_registry

from FW.logging_config import get_logger

if True:
    from FW.models.workflow import WorkflowModel


logger = get_logger("validation.runner")


class RuleRunner:
    """Исполнитель правил валидации.
    
    Загружает правила по категориям и выполняет их для переданной модели.
    """
    
    def __init__(self, categories: Optional[List[str]] = None):
        """Инициализировать runner.
        
        Args:
            categories: Список категорий правил для выполнения.
                       Если None - будут использованы все доступные правила.
        """
        self._registry = get_validation_rule_registry()
        self._categories = categories or []
    
    def run(self, workflow: "WorkflowModel") -> List[ValidationIssue]:
        """Выполнить все правила для workflow.
        
        Args:
            workflow: Модель workflow для проверки
            
        Returns:
            Список найденных проблем
        """
        issues = []
        
        categories = self._get_effective_categories()
        
        rule_classes = self._registry.get_rules_for_categories(categories)
        
        logger.info(f"Running {len(rule_classes)} validation rules for categories: {categories}")
        
        for rule_class in rule_classes:
            try:
                rule = rule_class()
                rule_issues = rule.validate(workflow)
                if rule_issues:
                    issues.extend(rule_issues)
                    logger.debug(f"Rule '{rule.name}' found {len(rule_issues)} issues")
            except Exception as e:
                logger.error(f"Error running rule {rule_class.__name__}: {e}")
        
        return issues
    
    def _get_effective_categories(self) -> List[str]:
        """Получить эффективный список категорий."""
        if self._categories:
            return self._categories
        
        available = self._registry.get_all_categories()
        return available if available else ["general"]
    
    def get_available_categories(self) -> List[str]:
        """Получить список доступных категорий."""
        return self._registry.get_all_categories()


def run_validation(
    workflow: "WorkflowModel",
    categories: Optional[List[str]] = None
) -> ValidationReport:
    """Выполнить валидацию workflow.
    
    Args:
        workflow: Модель workflow
        categories: Список категорий правил
        
    Returns:
        ValidationReport с результатами
    """
    runner = RuleRunner(categories)
    issues = runner.run(workflow)
    
    return issues


def validate_workflow(
    workflow: "WorkflowModel",
    categories: Optional[List[str]] = None
) -> ValidationReport:
    """Выполнить валидацию workflow и создать отчёт.
    
    Args:
        workflow: Модель workflow
        categories: Список категорий правил
        
    Returns:
        ValidationReport с результатами
    """
    runner = RuleRunner(categories)
    issues = runner.run(workflow)
    
    report = ValidationReport(
        project_name=workflow.project_name,
        model_name=workflow.model_name,
        template_name=getattr(workflow, "template_name", ""),
        validation_categories=categories or runner.get_available_categories(),
        timestamp=workflow.__dict__.get("_validation_timestamp", ""),
        issues=issues,
        template_issues=[]
    )
    
    return report
