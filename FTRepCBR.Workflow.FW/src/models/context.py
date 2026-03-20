"""Context model for project contexts."""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from FW.models.workflow import CTEMaterializationConfig


@dataclass
class ContextFlags:
    """Флаги контекста.
    
    Поддерживает вложенные структуры:
        flags:
            overduecalcmethod:
                fifo: false
                lifo: true
    """
    _flags: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение флага по ключу (поддержка вложенных через точку)."""
        parts = key.split(".")
        value = self._flags
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация."""
        return self._flags
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ContextFlags":
        """Создать из словаря."""
        return ContextFlags(_flags=data or {})


@dataclass
class ContextConstants:
    """Константы контекста."""
    _constants: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение константы."""
        return self._constants.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализация."""
        return self._constants
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ContextConstants":
        """Создать из словаря."""
        return ContextConstants(_constants=data or {})


@dataclass
class ContextModel:
    """Модель контекста.
    
    Атрибуты:
        name: имя контекста (имя файла без .yml)
        project: наименование клиентского проекта
        tools: список tools для этого контекста
        flags: флаги контекста
        constants: константы контекста
        cte: конфигурация материализации CTE
    """
    name: str
    project: str = ""
    tools: List[str] = field(default_factory=list)
    flags: ContextFlags = field(default_factory=ContextFlags)
    constants: ContextConstants = field(default_factory=ContextConstants)
    cte: CTEMaterializationConfig = field(default_factory=CTEMaterializationConfig)
    
    def get_tool(self, tool: str) -> bool:
        """Проверить, доступен ли tool в этом контексте."""
        return tool in self.tools
    
    def get_flag(self, key: str, default: Any = None) -> Any:
        """Получить флаг."""
        return self.flags.get(key, default)
    
    def get_constant(self, key: str, default: Any = None) -> Any:
        """Получить константу."""
        return self.constants.get(key, default)
    
    def to_dict(self) -> dict:
        """Сериализация."""
        return {
            "name": self.name,
            "project": self.project,
            "tools": self.tools,
            "flags": self.flags.to_dict(),
            "constants": self.constants.to_dict(),
            "cte": self.cte.to_dict(),
        }
    
    @staticmethod
    def from_dict(name: str, data: Dict[str, Any]) -> "ContextModel":
        """Создать из словаря (YAML)."""
        project = data.get("project", "")
        tools = data.get("tools", [])
        
        flags_data = data.get("flags", {})
        flags = ContextFlags.from_dict(flags_data)
        
        constants_data = data.get("constants", {})
        constants = ContextConstants.from_dict(constants_data)
        
        cte_data = data.get("cte")
        cte = CTEMaterializationConfig.from_dict(cte_data)
        
        return ContextModel(
            name=name,
            project=project,
            tools=tools,
            flags=flags,
            constants=constants,
            cte=cte,
        )


@dataclass
class ContextCollection:
    """Коллекция контекстов проекта."""
    _contexts: Dict[str, ContextModel] = field(default_factory=dict)
    default_context: str = "default"
    
    def add(self, context: ContextModel) -> None:
        """Добавить контекст."""
        self._contexts[context.name] = context
    
    def get(self, name: str) -> Optional[ContextModel]:
        """Получить контекст по имени."""
        return self._contexts.get(name)
    
    def get_default(self) -> Optional[ContextModel]:
        """Получить контекст по умолчанию."""
        return self._contexts.get(self.default_context)
    
    def list_names(self) -> List[str]:
        """Список имен контекстов."""
        return list(self._contexts.keys())
    
    def get_contexts(self) -> Dict[str, "ContextModel"]:
        """Получить словарь всех контекстов."""
        return self._contexts
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Сериализация коллекции контекстов."""
        return {name: ctx.to_dict() for name, ctx in self._contexts.items()}
    
    def __len__(self) -> int:
        return len(self._contexts)
    
    def __getitem__(self, key: str) -> ContextModel:
        return self._contexts[key]
    
    def __contains__(self, key: str) -> bool:
        return key in self._contexts
