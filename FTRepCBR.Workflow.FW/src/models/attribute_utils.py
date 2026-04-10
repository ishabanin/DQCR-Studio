"""Утилиты для работы с атрибутами SQLModel и TargetTableModelNew."""
from typing import TYPE_CHECKING, List, Optional, Set, Tuple, Dict

if TYPE_CHECKING:
    from FW.models.sql_query import SQLQueryModel
    from FW.models.workflow_new import TargetTableModelNew
    from FW.models.attribute import Attribute


def get_query_attribute_names(sql_model: "SQLQueryModel") -> Set[str]:
    """Получить имена атрибутов из запроса (регистронезависимо).
    
    Объединяет:
    1. Атрибуты из sql_model.attributes (явно описанные в model.yml)
    2. Атрибуты из metadata.aliases (все алиасы в запросе)
    
    Args:
        sql_model: Модель SQL запроса
        
    Returns:
        Множество имён атрибутов в нижнем регистре
    """
    attr_names: Set[str] = set()
    
    if sql_model.attributes:
        attr_names = {a.name.lower() for a in sql_model.attributes}
    
    if sql_model.metadata and sql_model.metadata.aliases:
        for a in sql_model.metadata.aliases:
            if isinstance(a, dict):
                alias_name = a.get('alias', '')
                if alias_name:
                    attr_names.add(alias_name.lower())
    
    return attr_names


def get_key_attributes(
    sql_model: "SQLQueryModel",
    target_table: Optional["TargetTableModelNew"]
) -> List[str]:
    """Получить ключевые атрибуты для материализации.
    
    Приоритет:
    1. Атрибуты запроса с constraints: ["PRIMARY_KEY"]
    2. Primary keys целевой таблицы, которые ЕСТЬ в запросе
    
    Args:
        sql_model: Модель SQL запроса
        target_table: Модель целевой таблицы
        
    Returns:
        Список ключевых атрибутов
    """
    key_attrs: List[str] = []
    query_attrs = get_query_attribute_names(sql_model)
    
    if sql_model.attributes:
        for a in sql_model.attributes:
            if a.is_primary_key():
                key_attrs.append(a.name)
    
    if not key_attrs and target_table:
        for pk_name in target_table.primary_key_names:
            if pk_name.lower() in query_attrs:
                key_attrs.append(pk_name)
    
    return key_attrs


def get_update_attributes(
    sql_model: "SQLQueryModel",
    target_table: Optional["TargetTableModelNew"],
    key_attrs: List[str]
) -> List[str]:
    """Получить атрибуты для UPDATE (неключевые).
    
    Все атрибуты запроса, кроме ключевых.
    Если target_table содержит атрибуты - фильтруем по ним.
    
    Args:
        sql_model: Модель SQL запроса
        target_table: Модель целевой таблицы
        key_attrs: Список ключевых атрибутов
        
    Returns:
        Список имён атрибутов для SET clause
    """
    query_attrs = get_query_attribute_names(sql_model)
    key_attrs_lower = {k.lower() for k in key_attrs}
    
    result: List[str] = []
    has_target_attrs = target_table and target_table.attributes
    
    for name in query_attrs:
        if name and name.lower() not in key_attrs_lower:
            if has_target_attrs:
                if target_table and target_table.get_attribute(name):
                    result.append(name)
            else:
                result.append(name)
    
    return result


def get_required_attributes_not_in_query(
    sql_model: "SQLQueryModel",
    target_table: Optional["TargetTableModelNew"]
) -> List[Tuple[str, Optional[str]]]:
    """Получить обязательные атрибуты целевой таблицы, которых нет в запросе.
    
    Args:
        sql_model: Модель SQL запроса
        target_table: Модель целевой таблицы
        
    Returns:
        Список кортежей (имя_атрибута, default_value)
    """
    result: List[Tuple[str, Optional[str]]] = []
    query_attrs = get_query_attribute_names(sql_model)
    
    if not target_table or not target_table.attributes:
        return result
    
    for attr in target_table.attributes:
        if attr.required and attr.name.lower() not in query_attrs:
            result.append((attr.name, attr.default_value))
    
    return result


def format_attr_default_value(default_value: Optional[str], domain_type: Optional[str]) -> Optional[str]:
    """Форматировать значение по умолчанию с учётом типа.
    
    Args:
        default_value: значение по умолчанию
        domain_type: доменный тип атрибута
        
    Returns:
        Отформатированное значение
    """
    if default_value is None:
        return None
    
    domain_type_lower = domain_type.lower() if domain_type else "string"
    
    if domain_type_lower in ("string", "date", "timestamp", "datetime"):
        return f"'{default_value}'"
    
    return default_value


def enrich_attributes_with_config(
    metadata_aliases: List[Dict],
    config_attributes: List["Attribute"],
    inline_attr_configs: Optional[Dict[str, Dict]] = None,
    default_source: str = "model"
) -> List["Attribute"]:
    """Обогатить атрибуты из SQL метаданных свойствами из YAML конфига.
    
    Args:
        metadata_aliases: Список алиасов из SQLMetadata.aliases
        config_attributes: Список атрибутов из YAML конфига
        inline_attr_configs: Словарь inline конфигов атрибутов {alias: config}
        default_source: Источник по умолчанию (model, folder) - не используется
        
    Returns:
        Обогащенный список атрибутов
    """
    from FW.models.attribute import Attribute
    
    if not metadata_aliases and not config_attributes and not inline_attr_configs:
        return []
    
    inline_attr_configs = inline_attr_configs or {}
    
    config_attrs_map: Dict[str, "Attribute"] = {
        attr.name.lower(): attr for attr in config_attributes
    }
    
    result: List[Attribute] = []
    sql_names_lower: Set[str] = set()
    
    for alias_info in metadata_aliases:
        alias_name = alias_info.get('alias', '')
        if not alias_name:
            continue
            
        alias_lower = alias_name.lower()
        sql_names_lower.add(alias_lower)
        
        attr = Attribute(name=alias_name)
        
        if alias_lower in config_attrs_map:
            cfg_attr = config_attrs_map[alias_lower]
            
            attr.distribution_key = cfg_attr.distribution_key
            attr.partition_key = cfg_attr.partition_key
            attr.required = cfg_attr.required
            attr.constraints = cfg_attr.constraints
            attr.default_value = cfg_attr.default_value
            attr.domain_type = cfg_attr.domain_type
        
        if alias_lower in inline_attr_configs:
            inline_cfg = inline_attr_configs[alias_lower]
            
            if inline_cfg.get('domain_type'):
                attr.domain_type = inline_cfg['domain_type']
            if 'required' in inline_cfg:
                attr.required = inline_cfg['required']
            if inline_cfg.get('constraints'):
                attr.constraints = inline_cfg['constraints']
            if 'distribution_key' in inline_cfg:
                dk_val = inline_cfg['distribution_key']
                try:
                    attr.distribution_key = int(str(dk_val).rstrip(','))
                except (ValueError, TypeError):
                    pass
            if 'partition_key' in inline_cfg:
                pk_val = inline_cfg['partition_key']
                try:
                    attr.partition_key = int(str(pk_val).rstrip(','))
                except (ValueError, TypeError):
                    pass
            if inline_cfg.get('default_value') is not None:
                attr.default_value = inline_cfg['default_value']
            if inline_cfg.get('description'):
                attr.description = inline_cfg['description']
        
        result.append(attr)
    
    for cfg_attr in config_attributes:
        if cfg_attr.name.lower() not in sql_names_lower:
            result.append(cfg_attr)
    
    for inline_attr_name, inline_cfg in inline_attr_configs.items():
        if inline_attr_name not in sql_names_lower and inline_attr_name in config_attrs_map:
            for attr in result:
                if attr.name.lower() == inline_attr_name:
                    if inline_cfg.get('domain_type'):
                        attr.domain_type = inline_cfg['domain_type']
                    if 'required' in inline_cfg:
                        attr.required = inline_cfg['required']
                    if inline_cfg.get('constraints'):
                        attr.constraints = inline_cfg['constraints']
                    if 'distribution_key' in inline_cfg:
                        dk_val = inline_cfg['distribution_key']
                        try:
                            attr.distribution_key = int(str(dk_val).rstrip(','))
                        except (ValueError, TypeError):
                            pass
                    if 'partition_key' in inline_cfg:
                        pk_val = inline_cfg['partition_key']
                        try:
                            attr.partition_key = int(str(pk_val).rstrip(','))
                        except (ValueError, TypeError):
                            pass
                    if inline_cfg.get('default_value') is not None:
                        attr.default_value = inline_cfg['default_value']
                    if inline_cfg.get('description'):
                        attr.description = inline_cfg['description']
                    break
    
    return result
