"""Model exceptions."""
from FW.exceptions.base import BaseFWError


class ModelNotFoundError(BaseFWError):
    """Модель не найдена."""
    
    def __init__(self, message: str, model_name: str = None):
        self.model_name = model_name
        super().__init__(message)


class ModelConfigError(BaseFWError):
    """Ошибка конфигурации модели."""
    
    def __init__(self, message: str, model_name: str = None):
        self.model_name = model_name
        super().__init__(message)
