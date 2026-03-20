"""General validation rules."""
from FW.validation.rules.base import BaseValidationRule
from FW.validation.models import ValidationIssue, ValidationLevel

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from FW.models.workflow import WorkflowModel


class TargetTableRequiredRule(BaseValidationRule):
    """Проверка наличия target table.
    
    Каждый workflow должен иметь определённую целевую таблицу.
    """
    name = "target_table_required"
    category = "general"
    level = ValidationLevel.ERROR
    description = "Проверка наличия target table"
    
    def validate(self, workflow: "WorkflowModel") -> list[ValidationIssue]:
        issues = []
        
        if not workflow.target_table:
            issues.append(ValidationIssue(
                level=self.level,
                rule=self.name,
                category=self.category,
                message="Target table is not defined",
                location="workflow",
                details={"model_name": workflow.model_name}
            ))
        
        return issues


class NoStepsRule(BaseValidationRule):
    """Проверка наличия шагов в workflow.
    
    Workflow без шагов не имеет смысла.
    """
    name = "no_steps"
    category = "general"
    level = ValidationLevel.WARNING
    description = "Проверка наличия шагов в workflow"
    
    def validate(self, workflow: "WorkflowModel") -> list[ValidationIssue]:
        issues = []
        
        if not workflow.steps or len(workflow.steps) == 0:
            issues.append(ValidationIssue(
                level=self.level,
                rule=self.name,
                category=self.category,
                message="Workflow has no steps",
                location="workflow",
                details={"model_name": workflow.model_name}
            ))
        
        return issues


class ToolsDefinedRule(BaseValidationRule):
    """Проверка определения tools для workflow.
    
    Workflow должен знать целевые инструменты для генерации.
    """
    name = "tools_defined"
    category = "general"
    level = ValidationLevel.WARNING
    description = "Проверка определения tools"
    
    def validate(self, workflow: "WorkflowModel") -> list[ValidationIssue]:
        issues = []
        
        if not workflow.tools or len(workflow.tools) == 0:
            issues.append(ValidationIssue(
                level=self.level,
                rule=self.name,
                category=self.category,
                message="No tools defined for workflow",
                location="workflow",
                details={"model_name": workflow.model_name}
            ))
        
        return issues


class NoEphemeralOnlyRule(BaseValidationRule):
    """Проверка: не все шаги должны быть ephemeral.
    
    Если все шаги ephemeral - результат workflow пустой.
    """
    name = "not_all_ephemeral"
    category = "general"
    level = ValidationLevel.WARNING
    description = "Проверка что не все шаги ephemeral"
    
    def validate(self, workflow: "WorkflowModel") -> list[ValidationIssue]:
        issues = []
        
        if not workflow.steps:
            return issues
            
        non_ephemeral_count = sum(
            1 for step in workflow.steps 
            if step.sql_model and step.sql_model.materialization != "ephemeral"
        )
        
        if non_ephemeral_count == 0:
            issues.append(ValidationIssue(
                level=self.level,
                rule=self.name,
                category=self.category,
                message="All steps are ephemeral - workflow produces no output",
                location="workflow",
                details={
                    "model_name": workflow.model_name,
                    "total_steps": len(workflow.steps)
                }
            ))
        
        return issues
