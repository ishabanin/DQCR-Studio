"""SQL validation rules."""
from FW.validation.rules.base import BaseValidationRule
from FW.validation.models import ValidationIssue, ValidationLevel

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from FW.models.workflow import WorkflowModel


class NoHintsRule(BaseValidationRule):
    """Проверка отсутствия SQL hints в запросах.
    
    Hints могут негативно влиять на производительность и переносимость.
    """
    name = "no_sql_hints"
    category = "sql"
    level = ValidationLevel.WARNING
    description = "Проверка отсутствия SQL hints"
    
    def validate(self, workflow: "WorkflowModel") -> list[ValidationIssue]:
        issues = []
        for step in workflow.steps:
            if step.sql_model and step.sql_model.source_sql:
                source = step.sql_model.source_sql.upper()
                if "/*+" in source or "/*+" in source:
                    issues.append(ValidationIssue(
                        level=self.level,
                        rule=self.name,
                        category=self.category,
                        message="SQL hints found in query (/*+ ... */)",
                        location=step.full_name,
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
    
    def validate(self, workflow: "WorkflowModel") -> list[ValidationIssue]:
        issues = []
        for step in workflow.steps:
            if step.sql_model and step.sql_model.source_sql:
                source_upper = step.sql_model.source_sql.upper()
                if "DELETE" in source_upper and "FROM" in source_upper:
                    issues.append(ValidationIssue(
                        level=self.level,
                        rule=self.name,
                        category=self.category,
                        message="DELETE statement found in query",
                        location=step.full_name,
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
    
    def validate(self, workflow: "WorkflowModel") -> list[ValidationIssue]:
        issues = []
        for step in workflow.steps:
            if step.sql_model and step.sql_model.source_sql:
                source_upper = step.sql_model.source_sql.upper()
                if "TRUNCATE" in source_upper:
                    issues.append(ValidationIssue(
                        level=self.level,
                        rule=self.name,
                        category=self.category,
                        message="TRUNCATE statement found - extremely dangerous operation",
                        location=step.full_name,
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
    
    def validate(self, workflow: "WorkflowModel") -> list[ValidationIssue]:
        import re
        issues = []
        for step in workflow.steps:
            if step.sql_model and step.sql_model.source_sql:
                source = step.sql_model.source_sql.upper()
                select_star_pattern = r'SELECT\s+\*\s+FROM'
                if re.search(select_star_pattern, source):
                    issues.append(ValidationIssue(
                        level=self.level,
                        rule=self.name,
                        category=self.category,
                        message="SELECT * found in query - avoid for better maintainability",
                        location=step.full_name,
                        details={"select_star_detected": True}
                    ))
        return issues
