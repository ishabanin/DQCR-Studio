"""Parameter domain types."""
from enum import Enum


class DomainType(str, Enum):
    """Типы данных параметров."""
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    DATETIME = "datetime"
    BOOL = "bool"
    RECORD = "record"
    ARRAY = "array"
    SQL_CONDITION = "sql.condition"
    SQL_EXPRESSION = "sql.expression"
    SQL_EXPRESSION_WHEN_LIST = "sql.expression.when.list"
    SQL_IDENTIFIER = "sql.identifier"
    UNDEFINED = "undefined"


class ParamType(str, Enum):
    """Типы получения значения параметра."""
    STATIC = "static"
    DYNAMIC = "dynamic"
