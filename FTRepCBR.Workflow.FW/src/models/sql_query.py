"""SQL query model."""
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional, List, Set
from dataclasses import dataclass, field

from FW.parsing.sql_metadata import SQLMetadata
from FW.models.attribute import Attribute

if TYPE_CHECKING:
    from FW.models.workflow_new import CTEMaterializationConfig, TargetTableModelNew


@dataclass
class SQLQueryModel:
    """Модель SQL-запроса."""
    name: str
    path: Path
    source_sql: str
    metadata: SQLMetadata
    materialization: str
    context: str = "all"
    description: str = ""
    prepared_sql: Dict[str, str] = field(default_factory=dict)
    rendered_sql: Dict[str, str] = field(default_factory=dict)
    attributes: List[Attribute] = field(default_factory=list)
    cte_config: Optional["CTEMaterializationConfig"] = None
    target_table: str = ""
    cte_table_names: Optional[Dict[str, str]] = None
    
    @property
    def cte_materialization(self) -> Optional[str]:
        """Получить дефолтную материализацию CTE."""
        if self.cte_config:
            return self.cte_config.cte_materialization
        return None
    
    @property
    def full_name(self) -> str:
        """Полное имя."""
        return f"{self.path.parent.name}/{self.name}" if self.path.parent.name != "SQL" else self.name
    
    def get_prepared_sql(self, tool: str) -> str:
        """Получить подготовленный SQL для tool (после подстановки параметров и функций).
        
        Args:
            tool: целевой tool (oracle/adb/postgresql)
            
        Returns:
            Подготовленный SQL или исходный source_sql, если не найден
        """
        return self.prepared_sql.get(tool, self.source_sql)
    
    def get_prepared_sql_for_render(self, tool: str) -> str:
        """Получить prepared_sql для использования в шаблоне материализации.
        
        В отличие от get_prepared_sql, не делает fallback на source_sql.
        Это нужно для шаблонов материализации, чтобы избежать двойного рендеринга.
        
        Args:
            tool: целевой tool (oracle/adb/postgresql)
            
        Returns:
            Prepared SQL или пустая строка, если не найден
        """
        return self.prepared_sql.get(tool, "")
    
    def get_rendered_sql(self, tool: str) -> str:
        """Получить уже отрендеренный SQL для tool (после материализации).
        
        Args:
            tool: целевой tool (oracle/adb/postgresql)
            
        Returns:
            Отрендеренный SQL или prepared_sql/source_sql, если не найден
        """
        if tool in self.rendered_sql:
            return self.rendered_sql[tool]
        if tool in self.prepared_sql:
            return self.prepared_sql[tool]
        return self.source_sql
    
    def get_attribute_names(self) -> Set[str]:
        """Получить имена атрибутов из запроса (регистронезависимо).
        
        Returns:
            Множество имён атрибутов в нижнем регистре
        """
        from FW.models.attribute_utils import get_query_attribute_names
        
        return get_query_attribute_names(self)
    
    def get_key_attributes(self, target_table: Optional["TargetTableModelNew"]) -> List[str]:
        """Получить ключевые атрибуты для материализации.
        
        Args:
            target_table: Модель целевой таблицы
            
        Returns:
            Список ключевых атрибутов
        """
        from FW.models.attribute_utils import get_key_attributes
        
        return get_key_attributes(self, target_table)
    
    def get_update_attributes(
        self,
        target_table: Optional["TargetTableModelNew"],
        key_attrs: List[str]
    ) -> List[str]:
        """Получить атрибуты для UPDATE (неключевые).
        
        Args:
            target_table: Модель целевой таблицы
            key_attrs: Список ключевых атрибутов
            
        Returns:
            Список имён атрибутов для SET clause
        """
        from FW.models.attribute_utils import get_update_attributes
        
        return get_update_attributes(self, target_table, key_attrs)
    
    def to_dict(self) -> dict:
        """Сериализация."""
        result = {
            'name': self.name,
            'path': str(self.path),
            'source_sql': self.source_sql,
            'materialization': self.materialization,
            'context': self.context,
            'metadata': self.metadata.to_dict() if self.metadata else None,
            'prepared_sql': self.prepared_sql,
            'rendered_sql': self.rendered_sql,
            'attributes': [attr.to_dict() for attr in self.attributes],
            'cte_materialization': self.cte_materialization,
            'cte_config': self.cte_config.to_dict() if self.cte_config else None,
            'cte_table_names': self.cte_table_names,
            'target_table': self.target_table,
        }
        if self.description:
            result['description'] = self.description
        return result
