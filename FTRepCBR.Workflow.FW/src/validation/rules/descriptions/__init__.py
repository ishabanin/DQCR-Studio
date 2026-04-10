"""Description validation rules."""
from FW.validation.rules.base import BaseValidationRule
from FW.validation.models import ValidationIssue, ValidationLevel

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from FW.models.workflow_new import WorkflowNewModel
    from FW.models.sql_object import SQLObjectModel


def _get_file_path(sql_object: "SQLObjectModel", workflow: "WorkflowNewModel") -> str:
    """Compute relative file path from project root."""
    project_name = workflow.project.project_name if workflow.project else ""
    model_group = workflow.models_root
    model_name = workflow.model_name
    sql_path = sql_object.path
    return f"{project_name}/{model_group}/{model_name}/{sql_path}"


class MissingStepDescriptionRule(BaseValidationRule):
    """Проверка наличия описаний у шагов.
    
    Описание шага помогает понять его назначение.
    """
    name = "missing_step_description"
    category = "descriptions"
    level = ValidationLevel.INFO
    description = "Проверка наличия описаний у шагов"
    
    def validate(self, workflow: "WorkflowNewModel") -> list[ValidationIssue]:
        issues = []
        
        model_group = workflow.models_root
        model_name = workflow.model_name
        
        if not workflow.sql_objects:
            return issues
        
        for sql_object in workflow.sql_objects.values():
            if sql_object.generated:
                continue
            
            has_description = False
            
            if sql_object.metadata and hasattr(sql_object.metadata, 'inline_query_config'):
                inline_config = sql_object.metadata.inline_query_config or {}
                if inline_config.get('description'):
                    has_description = True
            
            if not has_description:
                for ctx, ctx_config in sql_object.config.items():
                    if not isinstance(ctx_config, dict):
                        continue
                    
                    for tool, config in ctx_config.items():
                        if not isinstance(config, dict):
                            continue
                        
                        desc = config.get("description")
                        if desc is not None:
                            if hasattr(desc, 'value'):
                                if desc.value:
                                    has_description = True
                                    break
                            elif desc:
                                has_description = True
                                break
                    if has_description:
                        break
            
            if not has_description:
                file_path = _get_file_path(sql_object, workflow)
                issues.append(ValidationIssue(
                    level=self.level,
                    rule=self.name,
                    category=self.category,
                    message="Step description is missing",
                    file_path=file_path,
                    model_group=model_group,
                    model_name=model_name,
                    details={"step_type": "sql"}
                ))
        
        return issues


class MissingTargetTableDescriptionRule(BaseValidationRule):
    """Проверка наличия описания у целевой таблицы."""
    name = "missing_target_table_description"
    category = "descriptions"
    level = ValidationLevel.WARNING
    description = "Проверка наличия описания целевой таблицы"
    
    def validate(self, workflow: "WorkflowNewModel") -> list[ValidationIssue]:
        issues = []
        
        model_group = workflow.models_root
        model_name = workflow.model_name
        
        target_table = workflow.target_table
        if target_table and not target_table.description:
            project_name = workflow.project.project_name if workflow.project else ""
            file_path = f"{project_name}/{model_group}/{model_name}/model.yml"
            
            issues.append(ValidationIssue(
                level=self.level,
                rule=self.name,
                category=self.category,
                message="Target table description is missing",
                file_path=file_path,
                model_group=model_group,
                model_name=model_name,
                details={"table_name": target_table.name}
            ))
        
        return issues
