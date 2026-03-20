"""Project model."""
from typing import Optional
from dataclasses import dataclass


@dataclass
class ProjectModel:
    """Модель проекта.
    
    Атрибуты:
        name: имя проекта
        description: описание
    """
    name: str
    description: str = ""
    
    def to_dict(self) -> dict:
        """Сериализация."""
        return {
            "name": self.name,
            "description": self.description,
        }
    
    @staticmethod
    def from_dict(data: dict) -> "ProjectModel":
        """Создать из словаря (YAML)."""
        return ProjectModel(
            name=data.get("name", ""),
            description=data.get("description", ""),
        )
