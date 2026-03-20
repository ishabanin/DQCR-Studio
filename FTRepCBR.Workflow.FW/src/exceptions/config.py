"""Config exceptions."""
from FW.exceptions.base import BaseFWError


class ConfigValidationError(BaseFWError):
    """Ошибка валидации конфигурации."""
    
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message)