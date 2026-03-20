"""Validation models."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime


class ValidationLevel(Enum):
    """Уровень серьёзности проблемы валидации."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationIssue:
    """Проблема, найденная при валидации."""
    level: ValidationLevel
    rule: str
    category: str
    message: str
    location: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "rule": self.rule,
            "category": self.category,
            "message": self.message,
            "location": self.location,
            "details": self.details,
        }
    
    @staticmethod
    def from_dict(data: dict) -> "ValidationIssue":
        return ValidationIssue(
            level=ValidationLevel(data.get("level", "warning")),
            rule=data.get("rule", ""),
            category=data.get("category", ""),
            message=data.get("message", ""),
            location=data.get("location"),
            details=data.get("details", {}),
        )


@dataclass
class ValidationReport:
    """Отчёт о валидации проекта."""
    project_name: str
    model_name: str
    template_name: str
    validation_categories: List[str]
    timestamp: str
    issues: List[ValidationIssue] = field(default_factory=list)
    template_issues: List[ValidationIssue] = field(default_factory=list)
    
    @property
    def total_issues(self) -> int:
        return len(self.issues) + len(self.template_issues)
    
    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues + self.template_issues if i.level == ValidationLevel.ERROR)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues + self.template_issues if i.level == ValidationLevel.WARNING)
    
    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues + self.template_issues if i.level == ValidationLevel.INFO)
    
    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "model_name": self.model_name,
            "template_name": self.template_name,
            "validation_categories": self.validation_categories,
            "timestamp": self.timestamp,
            "summary": {
                "total": self.total_issues,
                "errors": self.error_count,
                "warnings": self.warning_count,
                "info": self.info_count,
            },
            "issues": [i.to_dict() for i in self.issues],
            "template_issues": [i.to_dict() for i in self.template_issues],
        }
    
    @staticmethod
    def from_dict(data: dict) -> "ValidationReport":
        issues = [ValidationIssue.from_dict(i) for i in data.get("issues", [])]
        template_issues = [ValidationIssue.from_dict(i) for i in data.get("template_issues", [])]
        
        return ValidationReport(
            project_name=data.get("project_name", ""),
            model_name=data.get("model_name", ""),
            template_name=data.get("template_name", ""),
            validation_categories=data.get("validation_categories", []),
            timestamp=data.get("timestamp", ""),
            issues=issues,
            template_issues=template_issues,
        )
