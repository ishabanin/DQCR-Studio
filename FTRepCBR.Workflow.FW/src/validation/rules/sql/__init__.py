"""SQL validation rules."""
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


class NoHintsRule(BaseValidationRule):
    """Проверка отсутствия SQL hints в запросах.
    
    Hints могут негативно влиять на производительность и переносимость.
    """
    name = "no_sql_hints"
    category = "sql"
    level = ValidationLevel.WARNING
    description = "Проверка отсутствия SQL hints"
    
    def validate(self, workflow: "WorkflowNewModel") -> list[ValidationIssue]:
        issues = []
        
        model_group = workflow.models_root
        model_name = workflow.model_name
        
        if not workflow.sql_objects:
            return issues
        
        for sql_object in workflow.sql_objects.values():
            if sql_object.generated:
                continue
            
            if sql_object.source_sql:
                source = sql_object.source_sql.upper()
                if "/*+" in source:
                    file_path = _get_file_path(sql_object, workflow)
                    issues.append(ValidationIssue(
                        level=self.level,
                        rule=self.name,
                        category=self.category,
                        message="SQL hints found in query (/*+ ... */)",
                        file_path=file_path,
                        model_group=model_group,
                        model_name=model_name,
                        details={"hint_detected": True}
                    ))
        
        return issues


class NoDeleteStatementRule(BaseValidationRule):
    """Проверка отсутствия DELETE операторов в запросах.
    
    DELETE операторы потенциально опасны для данных.
    """
    name = "no_delete_statement"
    category = "sql"
    level = ValidationLevel.WARNING
    description = "Проверка отсутствия DELETE операторов"
    
    def validate(self, workflow: "WorkflowNewModel") -> list[ValidationIssue]:
        issues = []
        
        model_group = workflow.models_root
        model_name = workflow.model_name
        
        if not workflow.sql_objects:
            return issues
        
        for sql_object in workflow.sql_objects.values():
            if sql_object.generated:
                continue
            
            if sql_object.source_sql:
                source_upper = sql_object.source_sql.upper()
                if "DELETE" in source_upper and "FROM" in source_upper:
                    file_path = _get_file_path(sql_object, workflow)
                    issues.append(ValidationIssue(
                        level=self.level,
                        rule=self.name,
                        category=self.category,
                        message="DELETE statement found in query",
                        file_path=file_path,
                        model_group=model_group,
                        model_name=model_name,
                        details={"delete_detected": True}
                    ))
        
        return issues


class NoTruncateRule(BaseValidationRule):
    """Проверка отсутствия TRUNCATE операторов.
    
    TRUNCATE очень опасен - не логируется и не откатывается.
    """
    name = "no_truncate_statement"
    category = "sql"
    level = ValidationLevel.ERROR
    description = "Проверка отсутствия TRUNCATE операторов"
    
    def validate(self, workflow: "WorkflowNewModel") -> list[ValidationIssue]:
        issues = []
        
        model_group = workflow.models_root
        model_name = workflow.model_name
        
        if not workflow.sql_objects:
            return issues
        
        for sql_object in workflow.sql_objects.values():
            if sql_object.generated:
                continue
            
            if sql_object.source_sql:
                source_upper = sql_object.source_sql.upper()
                if "TRUNCATE" in source_upper:
                    file_path = _get_file_path(sql_object, workflow)
                    issues.append(ValidationIssue(
                        level=self.level,
                        rule=self.name,
                        category=self.category,
                        message="TRUNCATE statement found - extremely dangerous operation",
                        file_path=file_path,
                        model_group=model_group,
                        model_name=model_name,
                        details={"truncate_detected": True}
                    ))
        
        return issues


class NoSelectStarRule(BaseValidationRule):
    """Проверка использования SELECT * в запросах.
    
    SELECT * может привести к непредсказуемым результатам при изменении схемы.
    """
    name = "no_select_star"
    category = "sql"
    level = ValidationLevel.INFO
    description = "Проверка отсутствия SELECT *"
    
    def validate(self, workflow: "WorkflowNewModel") -> list[ValidationIssue]:
        import re
        issues = []
        
        model_group = workflow.models_root
        model_name = workflow.model_name
        
        if not workflow.sql_objects:
            return issues
        
        for sql_object in workflow.sql_objects.values():
            if sql_object.generated:
                continue
            
            if sql_object.source_sql:
                source = sql_object.source_sql.upper()
                select_star_pattern = r'SELECT\s+\*\s+FROM'
                if re.search(select_star_pattern, source):
                    file_path = _get_file_path(sql_object, workflow)
                    issues.append(ValidationIssue(
                        level=self.level,
                        rule=self.name,
                        category=self.category,
                        message="SELECT * found in query - avoid for better maintainability",
                        file_path=file_path,
                        model_group=model_group,
                        model_name=model_name,
                        details={"select_star_detected": True}
                    ))
        
        return issues
