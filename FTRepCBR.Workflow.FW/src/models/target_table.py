"""Target table model."""
from typing import TYPE_CHECKING, Optional, List, Set
from dataclasses import dataclass, field

from FW.models.attribute import Attribute, ConstraintType

if TYPE_CHECKING:
    from FW.models.sql_query import SQLQueryModel


@dataclass
class TargetTableModel:
    """Модель целевой таблицы."""
    name: str
    context: str = "all"
    schema: Optional[str] = None
    description: str = ""
    attributes: List[Attribute] = field(default_factory=list)
    
    @property
    def primary_keys(self) -> List[Attribute]:
        """Получить атрибуты первичного ключа."""
        return [attr for attr in self.attributes if attr.is_primary_key()]
    
    @property
    def primary_key_names(self) -> List[str]:
        """Получить имена атрибутов первичного ключа."""
        return [attr.name for attr in self.primary_keys]
    
    @property
    def foreign_keys(self) -> List[Attribute]:
        """Получить атрибуты внешнего ключа."""
        return [attr for attr in self.attributes if attr.is_foreign_key()]
    
    def get_attribute(self, name: str) -> Optional[Attribute]:
        """Получить атрибут по имени."""
        for attr in self.attributes:
            if attr.name.lower() == name.lower():
                return attr
        return None
    
    def get_columns_by_domain(self, domain_type: str) -> List[Attribute]:
        """Получить колонки по доменному типу."""
        return [attr for attr in self.attributes if attr.domain_type == domain_type]
    
    def find_attributes_in_query(self, sql_model: "SQLQueryModel") -> List[Attribute]:
        """Найти атрибуты таблицы, присутствующие в запросе (регистронезависимо).
        
        Args:
            sql_model: Модель SQL запроса
            
        Returns:
            Список атрибутов таблицы, присутствующих в запросе
        """
        from FW.models.attribute_utils import get_query_attribute_names
        
        query_attrs = get_query_attribute_names(sql_model)
        return [a for a in self.attributes if a.name.lower() in query_attrs]
    
    def get_key_attributes_for_insert(self, sql_model: "SQLQueryModel") -> List[str]:
        """Получить ключевые атрибуты для INSERT.
        
        Args:
            sql_model: Модель SQL запроса
            
        Returns:
            Список ключевых атрибутов
        """
        from FW.models.attribute_utils import get_key_attributes
        
        return get_key_attributes(sql_model, self)
    
    def get_required_attributes_not_in_query(self, sql_model: "SQLQueryModel") -> List[tuple]:
        """Получить обязательные атрибуты, отсутствующие в запросе.
        
        Args:
            sql_model: Модель SQL запроса
            
        Returns:
            Список кортежей (имя_атрибута, default_value)
        """
        from FW.models.attribute_utils import get_required_attributes_not_in_query
        
        return get_required_attributes_not_in_query(sql_model, self)
    
    def to_dict(self) -> dict:
        """Сериализация."""
        result = {
            'name': self.name,
            'context': self.context,
            'schema': self.schema,
            'attributes': [attr.to_dict() for attr in self.attributes],
            'primary_keys': self.primary_key_names,
        }
        if self.description:
            result['description'] = self.description
        return result
