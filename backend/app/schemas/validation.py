from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ValidationSummary(BaseModel):
    passed: int
    warnings: int
    errors: int


class RuleResult(BaseModel):
    rule_id: str
    name: str
    status: Literal["pass", "warning", "error"]
    message: str
    file_path: str | None = None
    line: int | None = None


class ValidationResult(BaseModel):
    run_id: str
    timestamp: datetime
    project: str
    model: str
    summary: ValidationSummary
    rules: list[RuleResult]
