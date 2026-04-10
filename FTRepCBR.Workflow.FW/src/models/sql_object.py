"""SQL Object Model - не зависит от контекста, содержит source_sql и effective config."""

from pathlib import Path
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field

from FW.parsing.sql_metadata import SQLMetadata
from FW.models.attribute import Attribute

if TYPE_CHECKING:
    from FW.models.workflow import CTEMaterializationConfig, QueryConfig, FolderConfig


@dataclass
class ConfigValue:
    """Значение конфига с информацией об источнике."""

    value: Any
    source: str
    file: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None

    def to_dict(self) -> dict:
        result = {"value": self.value, "source": self.source, "file": self.file}
        if self.conditions:
            result["conditions"] = self.conditions
        if self.reason:
            result["reason"] = self.reason
        return result

    @staticmethod
    def from_dict(data: dict) -> "ConfigValue":
        return ConfigValue(
            value=data.get("value"),
            source=data.get("source", "default"),
            file=data.get("file"),
            conditions=data.get("conditions"),
            reason=data.get("reason"),
        )


@dataclass
class SQLObjectModel:
    """SQL объект - не привязан к контексту, содержит source_sql и effective config.

    Ключ объекта = полный путь к SQL файлу.

    Attributes:
        path: полный путь как ключ
        name: имя объекта
        source_sql: исходный SQL код
        metadata: распарсенные метаданные SQL
        config: полный конфиг в разрезе контекстов {context: {property: ConfigValue}}
        compiled: скомпилированные данные {context: {tool: {field: value}}}
        generated: флаг, что объект сгенерирован (например, для материализации CTE)
    """

    path: str
    name: str
    source_sql: str
    metadata: Optional[SQLMetadata] = None
    config: Dict[str, Dict[str, ConfigValue]] = field(default_factory=dict)
    compiled: Dict[str, Dict[str, Dict[str, Any]]] = field(default_factory=dict)
    generated: bool = False

    @staticmethod
    def from_sql_query(
        path: str,
        name: str,
        source_sql: str,
        metadata: Optional[SQLMetadata] = None,
    ) -> "SQLObjectModel":
        """Создать SQLObjectModel из существующих данных."""
        return SQLObjectModel(
            path=path,
            name=name,
            source_sql=source_sql,
            metadata=metadata,
        )

    def to_dict(self) -> dict:
        """Сериализация."""

        def serialize_value(val):
            if isinstance(val, ConfigValue):
                return val.to_dict()
            elif isinstance(val, dict):
                return {k: serialize_value(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [serialize_value(item) for item in val]
            else:
                return val

        config_serialized = {}
        for ctx, props in self.config.items():
            config_serialized[ctx] = {}
            for prop_name, prop_value in props.items():
                config_serialized[ctx][prop_name] = serialize_value(prop_value)

        return {
            "path": self.path,
            "name": self.name,
            "source_sql": self.source_sql,
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "config": config_serialized,
            "compiled": self.compiled,
            "generated": self.generated,
        }

    @staticmethod
    def from_dict(data: dict) -> "SQLObjectModel":
        """Десериализация."""
        metadata = None
        if data.get("metadata"):
            from FW.parsing.sql_metadata import SQLMetadata

            metadata = SQLMetadata.from_dict(data["metadata"])

        config_data = data.get("config", {})
        config = {}
        for ctx, props in config_data.items():
            config[ctx] = {}
            for prop_name, prop_value in props.items():
                if isinstance(prop_value, dict):
                    config[ctx][prop_name] = ConfigValue.from_dict(prop_value)
                else:
                    config[ctx][prop_name] = prop_value

        return SQLObjectModel(
            path=data.get("path", ""),
            name=data.get("name", ""),
            source_sql=data.get("source_sql", ""),
            metadata=metadata,
            config=config,
            compiled=data.get("compiled", {}),
            generated=data.get("generated", False),
        )
