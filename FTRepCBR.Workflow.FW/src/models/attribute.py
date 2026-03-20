"""Universal attribute model for tables and queries."""
from typing import Optional, List
from dataclasses import dataclass, field
from enum import Enum


class ConstraintType(str, Enum):
    """Типы ограничений."""
    PRIMARY_KEY = "PRIMARY_KEY"
    FOREIGN_KEY = "FOREIGN_KEY"
    UNIQUE = "UNIQUE"
    NOT_NULL = "NOT_NULL"
    CHECK = "CHECK"
    DEFAULT = "DEFAULT"


@dataclass
class Attribute:
    """Универсальный атрибут (для таблицы и запроса).
    
    Attributes:
        name: имя атрибута
        domain_type: доменный тип (string, number, date, etc)
        required: обязательный атрибут
        is_key: ключевой атрибут (для upsert ключа)
        constraints: список ограничений
        description: описание
        distribution_key: номер для распределения (MPP системы, GreenPlum)
        partition_key: номер для партиционирования
        default_value: значение по умолчанию для подстановки при insert
    """
    name: str
    domain_type: str = "string"
    required: bool = False
    is_key: bool = False
    constraints: List[str] = field(default_factory=list)
    description: str = ""
    distribution_key: Optional[int] = None
    partition_key: Optional[int] = None
    default_value: Optional[str] = None
    
    def is_primary_key(self) -> bool:
        return ConstraintType.PRIMARY_KEY in self.constraints
    
    def is_foreign_key(self) -> bool:
        return ConstraintType.FOREIGN_KEY in self.constraints
    
    def is_not_null(self) -> bool:
        return self.required or ConstraintType.NOT_NULL in self.constraints
    
    def to_dict(self) -> dict:
        result = {
            "name": self.name,
            "domain_type": self.domain_type,
            "required": self.required,
            "is_key": self.is_key,
            "constraints": self.constraints,
            "description": self.description,
            "distribution_key": self.distribution_key,
            "partition_key": self.partition_key,
        }
        if self.default_value is not None:
            result["default_value"] = self.default_value
        return result
    
    @staticmethod
    def from_dict(data: dict) -> "Attribute":
        return Attribute(
            name=data.get("name", ""),
            domain_type=data.get("domain_type", "string"),
            required=data.get("required", False),
            is_key=data.get("is_key", False),
            constraints=data.get("constraints", []),
            description=data.get("description", ""),
            distribution_key=data.get("distribution_key"),
            partition_key=data.get("partition_key"),
            default_value=data.get("default_value"),
        )
