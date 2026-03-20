"""Parameter model."""
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from dataclasses import dataclass, field

from FW.models.param_types import DomainType

if TYPE_CHECKING:
    from FW.parsing.sql_metadata import SQLMetadata


@dataclass
class ParameterValue:
    """Значение параметра для конкретного контекста.
    
    Атрибуты:
        type: тип получения значения (static, dynamic)
        value: значение или SQL запрос
    """
    type: str = "static"
    value: Any = None
    
    @staticmethod
    def from_dict(data: Any) -> "ParameterValue":
        """Создать из словаря или простого значения.
        
        Formats:
            - "value" -> { type: "static", value: "value" }
            - { type: "static", value: "value" }
            - { type: "dynamic", value: "SELECT..." }
        """
        if data is None:
            return ParameterValue(type="static", value=None)
        
        if isinstance(data, str):
            return ParameterValue(type="static", value=data)
        
        if isinstance(data, dict):
            return ParameterValue(
                type=data.get("type", "static"),
                value=data.get("value")
            )
        
        return ParameterValue(type="static", value=data)
    
    def to_dict(self) -> dict:
        """Сериализация."""
        return {
            "type": self.type,
            "value": self.value
        }


@dataclass
class ParameterModel:
    """Модель параметра.
    
    Атрибуты:
        name: имя параметра
        description: описание
        domain_type: тип данных (date, string, number, bool, sql.condition, sql.identifier, sql.expression, array, record)
        attributes: атрибуты с типами данных для complex types (array/record)
        values: словарь значений по контексту {context: ParameterValue}
        source_sql: исходный SQL для динамических параметров
        prepared_sql: подготовленный SQL для каждого tool (после подстановки параметров и функций)
        metadata: метаданные из парсинга SQL
        rendered_sql: материализованный SQL для каждого tool
    """
    name: str
    domain_type: str = DomainType.UNDEFINED
    description: str = ""
    attributes: List[Dict[str, str]] = field(default_factory=list)
    values: Dict[str, ParameterValue] = field(default_factory=dict)
    source_sql: Optional[str] = None
    prepared_sql: Dict[str, str] = field(default_factory=dict)
    metadata: Optional["SQLMetadata"] = None
    rendered_sql: Dict[str, str] = field(default_factory=dict)
    
    def get_value(self, context: str = "default") -> Any:
        """Получить значение параметра для указанного контекста.
        
        Args:
            context: имя контекста
            
        Returns:
            Значение параметра
        """
        if context in self.values:
            return self.values[context].value
        
        if "all" in self.values:
            return self.values["all"].value
        
        if self.values:
            return list(self.values.values())[0].value
        
        return None
    
    def get_param_type(self, context: str = "default") -> str:
        """Получить тип параметра для указанного контекста."""
        if context in self.values:
            return self.values[context].type
        
        if "all" in self.values:
            return self.values["all"].type
        
        return "static"
    
    def is_dynamic(self, context: str = "default") -> bool:
        """Проверить, является ли параметр динамическим для контекста."""
        return self.get_param_type(context) == "dynamic"
    
    def get_prepared_sql(self, tool: str) -> str:
        """Получить подготовленный SQL для tool (после подстановки параметров и функций).
        
        Args:
            tool: целевой tool (oracle/adb/postgresql)
            
        Returns:
            Подготовленный SQL или пустая строка
        """
        return self.prepared_sql.get(tool, "")
    
    def get_rendered_sql(self, tool: str) -> str:
        """Получить уже отрендеренный SQL для tool.
        
        Args:
            tool: целевой tool (oracle/adb/postgresql)
            
        Returns:
            Отрендеренный SQL или prepared_sql, если не найден
        """
        if tool in self.rendered_sql:
            return self.rendered_sql[tool]
        if tool in self.prepared_sql:
            return self.prepared_sql[tool]
        return ""
    
    @staticmethod
    def from_dict(name: str, data: Dict[str, Any]) -> "ParameterModel":
        """Создать ParameterModel из словаря (YAML).
        
        Expected format:
            parameter:
                name: date_end
                description: "Дата"
                domain_type: date
                attributes: [...]
                values:
                    all:
                        type: static
                        value: ":DATE_END:"
                    vtb:
                        type: dynamic
                        value: "SELECT..."
        """
        param_data = data.get("parameter", data)
        
        domain_type = param_data.get("domain_type", "string")
        description = param_data.get("description", "")
        attributes = param_data.get("attributes", [])
        
        values_raw = param_data.get("values", {})
        values = {}
        for ctx, val in values_raw.items():
            values[ctx] = ParameterValue.from_dict(val)
        
        return ParameterModel(
            name=name,
            domain_type=domain_type,
            description=description,
            attributes=attributes,
            values=values,
        )
    
    def to_dict(self) -> dict:
        """Сериализация."""
        return {
            'name': self.name,
            'domain_type': self.domain_type,
            'description': self.description,
            'attributes': self.attributes,
            'values': {k: v.to_dict() for k, v in self.values.items()},
            'source_sql': self.source_sql,
            'prepared_sql': self.prepared_sql,
            'rendered_sql': self.rendered_sql,
        }
