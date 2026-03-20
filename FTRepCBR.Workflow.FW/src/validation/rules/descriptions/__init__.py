"""Description validation rules."""
from FW.validation.rules.base import BaseValidationRule
from FW.validation.models import ValidationIssue, ValidationLevel

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from FW.models.workflow import WorkflowModel


class MissingWorkflowDescriptionRule(BaseValidationRule):
    """Проверка наличия описания workflow.
    
    Описание помогает понять назначение workflow.
    """
    name = "missing_workflow_description"
    category = "descriptions"
    level = ValidationLevel.WARNING
    description = "Проверка наличия описания workflow"
    
    def validate(self, workflow: "WorkflowModel") -> list[ValidationIssue]:
        issues = []
        
        if not workflow.description or not workflow.description.strip():
            issues.append(ValidationIssue(
                level=self.level,
                rule=self.name,
                category=self.category,
                message="Workflow description is missing",
                location="workflow",
                details={"model_name": workflow.model_name}
            ))
        
        return issues


class MissingStepDescriptionRule(BaseValidationRule):
    """Проверка наличия описаний у шагов.
    
    Описание шага помогает понять его назначение.
    """
    name = "missing_step_description"
    category = "descriptions"
    level = ValidationLevel.INFO
    description = "Проверка наличия описаний у шагов"
    
    def validate(self, workflow: "WorkflowModel") -> list[ValidationIssue]:
        issues = []
        
        for step in workflow.steps:
            if step.sql_model and hasattr(step.sql_model, 'metadata'):
                metadata = step.sql_model.metadata
                config = metadata.inline_query_config if metadata and hasattr(metadata, 'inline_query_config') else {}
                
                if not config or not config.get('description'):
                    issues.append(ValidationIssue(
                        level=self.level,
                        rule=self.name,
                        category=self.category,
                        message="Step description is missing",
                        location=step.full_name,
                        details={"step_type": "sql"}
                    ))
        
        return issues


class MissingTargetTableDescriptionRule(BaseValidationRule):
    """Проверка наличия описания у целевой таблицы."""
    name = "missing_target_table_description"
    category = "descriptions"
    level = ValidationLevel.WARNING
    description = "Проверка наличия описания целевой таблицы"
    
    def validate(self, workflow: "WorkflowModel") -> list[ValidationIssue]:
        issues = []
        
        target_table = workflow.target_table
        if target_table and not target_table.description:
            issues.append(ValidationIssue(
                level=self.level,
                rule=self.name,
                category=self.category,
                message="Target table description is missing",
                location=f"target_table:{target_table.name}",
                details={"table_name": target_table.name}
            ))
        
        return issues
