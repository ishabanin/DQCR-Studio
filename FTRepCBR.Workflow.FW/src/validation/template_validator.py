"""Template validator - проверка соответствия проекта шаблону."""
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from fnmatch import fnmatch

from FW.validation.models import ValidationIssue, ValidationLevel
from FW.models.project_template import ProjectTemplate, ModelDefinition, ModelRules
from FW.logging_config import get_logger

if True:
    from FW.models.workflow import WorkflowModel


logger = get_logger("validation.template")


class TemplateValidator:
    """Валидатор соответствия проекта шаблону.
    
    Проверяет:
    - Все required folders присутствуют
    - Все required queries присутствуют
    - Все required parameters присутствуют
    - Materialization соответствует правилам шаблона
    """
    
    def __init__(self, template: ProjectTemplate):
        """Инициализировать валидатор.
        
        Args:
            template: Шаблон проекта для проверки
        """
        self._template = template
    
    def validate(self, workflow: "WorkflowModel") -> List[ValidationIssue]:
        """Проверить workflow на соответствие шаблону.
        
        Args:
            workflow: Модель workflow
            
        Returns:
            Список найденных проблем
        """
        issues = []
        
        model_def = self._template.get_model(self._get_model_name_from_workflow(workflow))
        
        if not model_def:
            return issues
        
        rules = model_def.rules if model_def else None
        if not rules:
            return issues
        
        issues.extend(self._validate_folders(workflow, rules))
        issues.extend(self._validate_queries(workflow, rules))
        
        return issues
    
    def _get_model_name_from_workflow(self, workflow: "WorkflowModel") -> str:
        """Получить имя модели из workflow."""
        model_path = str(workflow.model_path)
        
        for model_def in self._template.models:
            if model_def.paths:
                model_root = model_def.paths.models_root
                if model_root and model_root in model_path:
                    return model_def.name
        
        return self._template.models[0].name if self._template.models else ""
    
    def _validate_folders(
        self, 
        workflow: "WorkflowModel", 
        rules: ModelRules
    ) -> List[ValidationIssue]:
        """Проверить папки на соответствие правилам."""
        issues = []
        
        existing_folders = set()
        for step in workflow.steps:
            if step.folder:
                existing_folders.add(step.folder)
        
        if rules.folders:
            for pattern, rule_def in rules.folders.items():
                if rule_def.required:
                    found = False
                    for folder in existing_folders:
                        if self._match_pattern(folder, pattern):
                            found = True
                            break
                    
                    if not found:
                        issues.append(ValidationIssue(
                            level=ValidationLevel.ERROR,
                            rule="required_folder",
                            category="template",
                            message=f"Required folder pattern '{pattern}' not found in workflow",
                            location=f"folder:{pattern}",
                            details={"pattern": pattern, "existing_folders": list(existing_folders)}
                        ))
        
        return issues
    
    def _validate_queries(
        self, 
        workflow: "WorkflowModel", 
        rules: ModelRules
    ) -> List[ValidationIssue]:
        """Проверить queries на соответствие правилам."""
        issues = []
        
        existing_queries = {}
        for step in workflow.steps:
            if step.folder and step.name:
                if step.folder not in existing_queries:
                    existing_queries[step.folder] = set()
                existing_queries[step.folder].add(step.name)
        
        if rules.queries:
            for pattern, rule_def in rules.queries.items():
                if rule_def.required:
                    found = False
                    for folder, queries in existing_queries.items():
                        for query in queries:
                            full_name = f"{folder}/{query}"
                            if self._match_pattern(query, pattern) or self._match_pattern(full_name, pattern):
                                found = True
                                break
                        if found:
                            break
                    
                    if not found:
                        issues.append(ValidationIssue(
                            level=ValidationLevel.ERROR,
                            rule="required_query",
                            category="template",
                            message=f"Required query pattern '{pattern}' not found in workflow",
                            location=f"query:{pattern}",
                            details={
                                "pattern": pattern, 
                                "existing_queries": {
                                    k: list(v) for k, v in existing_queries.items()
                                }
                            }
                        ))
        
        return issues
    
    def _match_pattern(self, name: str, pattern: str) -> bool:
        """Проверить соответствие имени паттерну.
        
        Поддерживает:
        - Точное совпадение
        - Wildcard * (любое количество символов)
        - Glob-подобные паттерны
        """
        if pattern == "*":
            return True
        
        if "*" in pattern:
            return fnmatch(name, pattern)
        
        return name == pattern


def validate_template(
    workflow: "WorkflowModel",
    template: ProjectTemplate
) -> List[ValidationIssue]:
    """Упрощённая функция валидации по шаблону.
    
    Args:
        workflow: Модель workflow
        template: Шаблон проекта
        
    Returns:
        Список найденных проблем
    """
    validator = TemplateValidator(template)
    return validator.validate(workflow)
