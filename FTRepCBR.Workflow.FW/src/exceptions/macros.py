"""Macro exceptions."""
from FW.exceptions.base import BaseFWError


class MacroNotFoundError(BaseFWError):
    """Макрос не найден."""
    
    def __init__(self, message: str, macro_name: str = None):
        self.macro_name = macro_name
        super().__init__(message)


class FunctionNotFoundError(BaseFWError):
    """Функция не найдена."""
    
    def __init__(self, message: str, function_name: str = None):
        self.function_name = function_name
        super().__init__(message)
