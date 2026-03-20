"""ADB validation rules."""
from FW.validation.rules.base import BaseValidationRule
from FW.validation.models import ValidationIssue, ValidationLevel

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from FW.models.workflow import WorkflowModel


class DistributionKeyRule(BaseValidationRule):
    """Проверка наличия ключа распределения для ADB.
    
    Для материализации insert_fc в ADB требуется ключ распределения.
    """
    name = "adb_distribution_key"
    category = "adb"
    level = ValidationLevel.ERROR
    description = "Проверка наличия ключа распределения для ADB"
    
    def validate(self, workflow: "WorkflowModel") -> list[ValidationIssue]:
        issues = []
        
        if "adb" not in workflow.tools:
            return issues
            
        for step in workflow.steps:
            if step.sql_model and step.sql_model.materialization == "insert_fc":
                has_dist_key = any(
                    attr.distribution_key is not None 
                    for attr in step.sql_model.attributes
                )
                
                if not has_dist_key:
                    issues.append(ValidationIssue(
                        level=self.level,
                        rule=self.name,
                        category=self.category,
                        message="No distribution_key defined for ADB insert_fc materialization",
                        location=step.full_name,
                        details={
                            "materialization": step.sql_model.materialization,
                            "tool": "adb"
                        }
                    ))
        
        return issues


class AdbPrimaryKeyRule(BaseValidationRule):
    """Проверка наличия PRIMARY KEY для ADB.
    
    ADB требует primary key для материализации insert_fc.
    """
    name = "adb_primary_key"
    category = "adb"
    level = ValidationLevel.ERROR
    description = "Проверка наличия PRIMARY KEY для ADB"
    
    def validate(self, workflow: "WorkflowModel") -> list[ValidationIssue]:
        issues = []
        
        if "adb" not in workflow.tools:
            return issues
        
        target_table = workflow.target_table
        if not target_table:
            return issues
            
        has_primary_key = any(
            attr.is_key or "PRIMARY_KEY" in (attr.constraints or [])
            for attr in target_table.attributes
        )
        
        if not has_primary_key:
            issues.append(ValidationIssue(
                level=self.level,
                rule=self.name,
                category=self.category,
                message="No primary key defined in target table for ADB",
                location="target_table",
                details={
                    "target_table": target_table.name,
                    "tool": "adb"
                }
            ))
        
        return issues
