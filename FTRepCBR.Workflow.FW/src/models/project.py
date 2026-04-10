"""Project model."""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class ProjectModel:
    """Модель проекта.

    Атрибуты:
        name: имя проекта
        description: описание
        constants: константы проекта {name: {domain_type, value}}
        flags: флаги проекта
    """

    name: str
    description: str = ""
    constants: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    flags: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Сериализация."""
        return {
            "name": self.name,
            "description": self.description,
            "constants": self.constants,
            "flags": self.flags,
        }

    @staticmethod
    def from_dict(data: dict) -> "ProjectModel":
        """Создать из словаря (YAML)."""
        constants = data.get("constants", {})
        flags = data.get("flags", {})

        return ProjectModel(
            name=data.get("name", ""),
            description=data.get("description", ""),
            constants=constants,
            flags=flags,
        )
