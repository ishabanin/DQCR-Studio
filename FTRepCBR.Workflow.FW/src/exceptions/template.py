"""Template exceptions."""
from FW.exceptions.base import BaseFWError


class TemplateNotFoundError(BaseFWError):
    """Шаблон не найден."""
    
    def __init__(self, message: str, template_name: str = None, available: list = None):
        self.template_name = template_name
        self.available = available or []
        super().__init__(message)


class TemplateValidationError(BaseFWError):
    """Ошибка валидации шаблона."""
    
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message)
