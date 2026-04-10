"""Exceptions package."""
from FW.exceptions.base import BaseFWError
from FW.exceptions.template import TemplateNotFoundError, TemplateValidationError
from FW.exceptions.model import ModelNotFoundError, ModelConfigError
from FW.exceptions.macros import MacroNotFoundError, FunctionNotFoundError
from FW.exceptions.config import ConfigValidationError


__all__ = [
    'BaseFWError',
    'TemplateNotFoundError',
    'TemplateValidationError',
    'ModelNotFoundError',
    'ModelConfigError',
    'MacroNotFoundError',
    'FunctionNotFoundError',
    'ConfigValidationError',
]
