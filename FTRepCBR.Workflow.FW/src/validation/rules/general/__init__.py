"""General validation rules."""
from FW.validation.rules.base import BaseValidationRule
from FW.validation.models import ValidationIssue, ValidationLevel

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from FW.models.workflow_new import WorkflowNewModel


class TargetTableRequiredRule(BaseValidationRule):
    """Проверка наличия target table.
    
    Каждый workflow должен иметь определённую целевую таблицу.
    """
    name = "target_table_required"
    category = "general"
    level = ValidationLevel.ERROR
    description = "Проверка наличия target table"
    
    def validate(self, workflow: "WorkflowNewModel") -> list[ValidationIssue]:
        issues = []
        
        model_group = workflow.models_root
        model_name = workflow.model_name
        
        if not workflow.target_table or not workflow.target_table.name:
            project_name = workflow.project.project_name if workflow.project else ""
            file_path = f"{project_name}/{model_group}/{model_name}/model.yml"
            
            issues.append(ValidationIssue(
                level=self.level,
                rule=self.name,
                category=self.category,
                message="Target table is not defined",
                file_path=file_path,
                model_group=model_group,
                model_name=model_name,
                details={"model_name": model_name}
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
    
    def validate(self, workflow: "WorkflowNewModel") -> list[ValidationIssue]:
        issues = []
        
        model_group = workflow.models_root
        model_name = workflow.model_name
        
        step_count = 0
        if workflow.graph:
            for context_tools in workflow.graph.values():
                for tool_data in context_tools.values():
                    if "steps" in tool_data:
                        step_count += len(tool_data["steps"])
        
        if step_count == 0:
            project_name = workflow.project.project_name if workflow.project else ""
            file_path = f"{project_name}/{model_group}/{model_name}/model.yml"
            
            issues.append(ValidationIssue(
                level=self.level,
                rule=self.name,
                category=self.category,
                message="Workflow has no steps",
                file_path=file_path,
                model_group=model_group,
                model_name=model_name,
                details={"model_name": model_name}
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
    
    def validate(self, workflow: "WorkflowNewModel") -> list[ValidationIssue]:
        issues = []
        
        model_group = workflow.models_root
        model_name = workflow.model_name
        
        if not workflow.tools or len(workflow.tools) == 0:
            project_name = workflow.project.project_name if workflow.project else ""
            file_path = f"{project_name}/{model_group}/{model_name}/model.yml"
            
            issues.append(ValidationIssue(
                level=self.level,
                rule=self.name,
                category=self.category,
                message="No tools defined for workflow",
                file_path=file_path,
                model_group=model_group,
                model_name=model_name,
                details={"model_name": model_name}
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
    
    def validate(self, workflow: "WorkflowNewModel") -> list[ValidationIssue]:
        issues = []
        
        model_group = workflow.models_root
        model_name = workflow.model_name
        
        if not workflow.sql_objects:
            return issues
        
        non_ephemeral_count = 0
        total_count = len(workflow.sql_objects)
        
        for sql_object in workflow.sql_objects.values():
            if sql_object.generated:
                continue
            
            for ctx, ctx_config in sql_object.config.items():
                if not isinstance(ctx_config, dict):
                    continue
                
                for tool, config in ctx_config.items():
                    if not isinstance(config, dict):
                        continue
                    
                    materialized = config.get("materialized")
                    if materialized is not None:
                        if hasattr(materialized, 'value'):
                            mat_value = materialized.value
                        else:
                            mat_value = materialized
                        if mat_value and mat_value != "ephemeral":
                            non_ephemeral_count += 1
                            break
                if non_ephemeral_count > 0:
                    break
        
        if non_ephemeral_count == 0 and total_count > 0:
            project_name = workflow.project.project_name if workflow.project else ""
            file_path = f"{project_name}/{model_group}/{model_name}/model.yml"
            
            issues.append(ValidationIssue(
                level=self.level,
                rule=self.name,
                category=self.category,
                message="All steps are ephemeral - workflow produces no output",
                file_path=file_path,
                model_group=model_group,
                model_name=model_name,
                details={
                    "model_name": model_name,
                    "total_steps": total_count
                }
            ))
        
        return issues
