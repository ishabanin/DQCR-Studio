"""Облегченная модель workflow - только базовые поля."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List, TYPE_CHECKING

from FW.models.enabled import EnabledRule
from FW.models.attribute import Attribute
from FW.models.sql_object import SQLObjectModel, ConfigValue
from FW.models.parameter import ParameterModel
from FW.models.context import ContextModel

@dataclass
class CTEMaterializationConfig:
    """Конфигурация материализации CTE.
    
    Структура:
        cte:
          cte_materialization:
            default: ephemeral | insert_fc | upsert_fc | ...
            by_context:
              vtb: insert_fc
            by_tool:
              oracle: upsert_fc
              adb: insert_fc
          
          cte_queries:
            <cte_name>:
              cte_materialization: upsert_fc
              attributes:
                - name: dealid
                  distribution_key: 1
    """
    cte_materialization: Optional[str] = None
    by_context: Dict[str, str] = field(default_factory=dict)
    by_tool: Dict[str, str] = field(default_factory=dict)
    cte_queries: Dict[str, "CTEMaterializationConfig"] = field(default_factory=dict)
    attributes: List[Attribute] = field(default_factory=list)
    
    def get_cte_materialization(
        self,
        cte_name: str,
        context_name: str,
        tool: str,
        default: str = "ephemeral"
    ) -> str:
        """Получить материализацию для конкретного CTE.
        
        Приоритет:
        1. cte_queries[cte_name].by_tool[tool]
        2. cte_queries[cte_name].cte_materialization
        3. by_tool[tool]
        4. by_context[context_name]
        5. cte_materialization
        6. default
        
        Args:
            cte_name: имя CTE (если есть в cte_queries)
            context_name: имя контекста
            tool: целевой tool
            default: значение по умолчанию
            
        Returns:
            Тип материализации
        """
        if cte_name and cte_name in self.cte_queries:
            specific = self.cte_queries[cte_name]
            if tool and specific.by_tool and tool in specific.by_tool:
                return specific.by_tool[tool]
            if context_name and specific.by_context and context_name in specific.by_context:
                return specific.by_context[context_name]
            if specific.cte_materialization is not None:
                return specific.cte_materialization
        
        if tool and tool in self.by_tool:
            return self.by_tool[tool]
        
        if context_name and context_name in self.by_context:
            return self.by_context[context_name]
        
        if self.cte_materialization is not None:
            return self.cte_materialization
        
        return default
    
    def to_dict(self) -> dict:
        result = {}
        if self.cte_materialization:
            result["cte_materialization"] = self.cte_materialization
        if self.by_context:
            result["by_context"] = self.by_context
        if self.by_tool:
            result["by_tool"] = self.by_tool
        if self.cte_queries:
            result["cte_queries"] = {k: v.to_dict() for k, v in self.cte_queries.items()}
        if self.attributes:
            result["attributes"] = [a.to_dict() for a in self.attributes]
        return result
    
    @staticmethod
    def from_dict(data) -> "CTEMaterializationConfig":
        if not data:
            return CTEMaterializationConfig()
        
        if isinstance(data, str):
            return CTEMaterializationConfig(cte_materialization=data)
        
        if isinstance(data, CTEMaterializationConfig):
            return data
        
        if not isinstance(data, dict):
            return CTEMaterializationConfig()
        
        cte_mat = data.get("cte_materialization")
        by_context = data.get("by_context", {})
        by_tool = data.get("by_tool", {})
        
        attrs_data = data.get("attributes", [])
        attributes = [Attribute.from_dict(a) for a in attrs_data]
        
        cte_queries = {}
        for cte_name, cte_data in data.get("cte_queries", {}).items():
            if isinstance(cte_data, CTEMaterializationConfig):
                cte_queries[cte_name] = cte_data
            else:
                cte_queries[cte_name] = CTEMaterializationConfig.from_dict(cte_data)
        
        return CTEMaterializationConfig(
            cte_materialization=cte_mat,
            by_context=by_context,
            by_tool=by_tool,
            cte_queries=cte_queries,
            attributes=attributes,
        )
@dataclass
class QueryConfig:
    """Конфигурация конкретного SQL запроса."""
    enabled: Optional[EnabledRule] = None
    materialized: Optional[str] = None
    description: str = ""
    attributes: List[Attribute] = field(default_factory=list)
    cte: Optional[CTEMaterializationConfig] = None
    
    @staticmethod
    def from_dict(data: Optional[Dict[str, Any]]) -> "QueryConfig":
        if data is None:
            return QueryConfig()
        
        enabled_data = data.get("enabled")
        enabled = EnabledRule.from_dict(enabled_data)
        
        materialized = data.get("materialized")
        description = data.get("description", "")
        
        attrs_data = data.get("attributes", [])
        attributes = [Attribute.from_dict(a) for a in attrs_data]
        
        cte_queries_raw = data.get("cte_queries", {})
        
        cte_queries = {}
        
        for cte_name, cte_info in cte_queries_raw.items():
            if isinstance(cte_info, dict):
                if "cte_materialization" in cte_info:
                    mat = cte_info["cte_materialization"]
                    attrs_data = cte_info.get("attributes", [])
                    cte_attrs = [Attribute.from_dict(a) for a in attrs_data]
                    if isinstance(mat, str):
                        cte_queries[cte_name] = CTEMaterializationConfig(
                            cte_materialization=mat,
                            attributes=cte_attrs
                        )
                    elif isinstance(mat, dict):
                        cte_queries[cte_name] = CTEMaterializationConfig(
                            cte_materialization=mat.get("default"),
                            by_context=mat.get("by_context", {}),
                            by_tool=mat.get("by_tool", {}),
                            attributes=cte_attrs
                        )
                    else:
                        cte_queries[cte_name] = CTEMaterializationConfig(
                            cte_materialization=None,
                            attributes=cte_attrs
                        )
                else:
                    cte_queries[cte_name] = CTEMaterializationConfig.from_dict(cte_info)
            else:
                cte_queries[cte_name] = CTEMaterializationConfig(cte_materialization=cte_info)
        
        cte_data = data.get("cte") or {}
        if cte_queries:
            cte_data = {"cte_queries": cte_queries, **cte_data}
        
        cte = CTEMaterializationConfig.from_dict(cte_data)
        
        return QueryConfig(
            enabled=enabled,
            materialized=materialized,
            description=description,
            attributes=attributes,
            cte=cte,
        )
    
    def to_dict(self) -> dict:
        result = {}
        if self.enabled:
            result["enabled"] = self.enabled.to_dict()
        if self.materialized:
            result["materialized"] = self.materialized
        if self.description:
            result["description"] = self.description
        if self.attributes:
            result["attributes"] = [a.to_dict() for a in self.attributes]
        if self.cte:
            cte_dict = self.cte.to_dict()
            if "cte_queries" in cte_dict:
                result["cte_queries"] = cte_dict["cte_queries"]
            else:
                result["cte"] = cte_dict
        return result
    
    def enrich_with_inline(self, sql_content: str) -> "QueryConfig":
        """Обогатить конфиг inline-конфигом из SQL.
        
        Inline конфиг имеет наивысший приоритет и мержится каскадно.
        """
        from FW.parsing.inline_config_parser import parse_inline_configs
        
        inline_result = parse_inline_configs(sql_content)
        
        if not inline_result.query_config and not inline_result.cte_configs:
            return self
        
        if inline_result.query_config:
            if inline_result.query_config.get('enabled'):
                from FW.models.enabled import EnabledRule
                enabled_data = inline_result.query_config['enabled']
                self.enabled = EnabledRule.from_dict(enabled_data)
            
            if inline_result.query_config.get('materialized'):
                self.materialized = inline_result.query_config['materialized']
            
            if inline_result.query_config.get('description'):
                self.description = inline_result.query_config['description']
            
            if inline_result.query_config.get('attributes'):
                inline_attrs = [
                    Attribute.from_dict(a) 
                    for a in inline_result.query_config['attributes']
                ]
                self.attributes = self.attributes + inline_attrs
        
        if self.cte is None:
            self.cte = CTEMaterializationConfig()
        
        if inline_result.cte_configs:
            for cte_name, cte_inline in inline_result.cte_configs.items():
                if cte_name not in self.cte.cte_queries:
                    self.cte.cte_queries[cte_name] = CTEMaterializationConfig()
                
                cte_cfg = self.cte.cte_queries[cte_name]
                
                inline_mat = cte_inline.get('cte_materialization')
                if inline_mat:
                    if isinstance(inline_mat, str):
                        cte_cfg.cte_materialization = inline_mat
                    elif isinstance(inline_mat, dict):
                        cte_cfg.cte_materialization = inline_mat.get('default')
                        if inline_mat.get('by_context'):
                            cte_cfg.by_context = inline_mat['by_context']
                        if inline_mat.get('by_tool'):
                            cte_cfg.by_tool = inline_mat['by_tool']
                
                if cte_inline.get('attributes'):
                    cte_attrs = [Attribute.from_dict(a) for a in cte_inline['attributes']]
                    cte_cfg.attributes = cte_attrs
        
        return self
        
@dataclass
class FolderModel:
    """Модель папки в workflow."""
    name: str = ""
    short_name: str = ""
    enabled: bool = True
    contexts: List[str] = field(default_factory=list)
    materialized: Optional[str] = None
    pre: List[str] = field(default_factory=list)
    post: List[str] = field(default_factory=list)
    config: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        def serialize_value(val):
            if hasattr(val, 'to_dict'):
                return val.to_dict()
            elif isinstance(val, dict):
                return {k: serialize_value(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [serialize_value(item) for item in val]
            else:
                return val
        
        return {
            "name": self.name,
            "short_name": self.short_name,
            "enabled": self.enabled,
            "contexts": self.contexts,
            "materialized": self.materialized,
            "pre": self.pre,
            "post": self.post,
            "config": {k: serialize_value(v) for k, v in self.config.items()},
        }

@dataclass
class ProjectInfo:
    """Модель проекта для WorkflowNewModel."""

    project_name: str
    project_properties: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "project_properties": self.project_properties,
        }

@dataclass
class FolderConfig:
    """Конфигурация папки в workflow."""
    materialized: Optional[str] = None
    enabled: Optional[EnabledRule] = None
    description: str = ""
    queries: Dict[str, QueryConfig] = field(default_factory=dict)
    cte: Optional[CTEMaterializationConfig] = None
    pre: List[str] = field(default_factory=list)
    post: List[str] = field(default_factory=list)
    
    @staticmethod
    def from_dict(data: Optional[Dict[str, Any]]) -> "FolderConfig":
        if data is None:
            return FolderConfig()
        
        materialized = data.get("materialized")
        
        enabled_data = data.get("enabled")
        enabled = EnabledRule.from_dict(enabled_data)
        
        description = data.get("description", "")
        
        queries = {}
        for q_name, q_data in data.get("queries", {}).items():
            queries[q_name] = QueryConfig.from_dict(q_data)
        
        cte_data = data.get("cte")
        cte = CTEMaterializationConfig.from_dict(cte_data)
        
        pre = data.get("pre", [])
        if isinstance(pre, str):
            pre = [pre]
        post = data.get("post", [])
        if isinstance(post, str):
            post = [post]
        
        return FolderConfig(
            materialized=materialized,
            enabled=enabled,
            description=description,
            queries=queries,
            cte=cte,
            pre=pre,
            post=post,
        )
    
    def get_query_config(self, query_name: str) -> Optional[QueryConfig]:
        """Получить конфиг конкретного запроса."""
        return self.queries.get(query_name)
    
    def to_dict(self) -> dict:
        result = {}
        if self.materialized:
            result["materialized"] = self.materialized
        if self.enabled:
            result["enabled"] = self.enabled.to_dict()
        if self.description:
            result["description"] = self.description
        if self.queries:
            result["queries"] = {k: v.to_dict() for k, v in self.queries.items()}
        if self.cte:
            result["cte"] = self.cte.to_dict()
        if self.pre:
            result["pre"] = self.pre
        if self.post:
            result["post"] = self.post
        return result


@dataclass
class TargetTableModelNew:
    """Облегченная модель целевой таблицы.

    Отличается от TargetTableModel отсутствием:
    - primary_keys (вычисляемое свойство)
    - config_sources
    """

    name: str
    schema: Optional[str] = None
    description: str = ""
    context: str = "all"
    attributes: List[Attribute] = field(default_factory=list)

    def get_attribute(self, name: str) -> Optional[Attribute]:
        """Получить атрибут по имени."""
        for attr in self.attributes:
            if attr.name.lower() == name.lower():
                return attr
        return None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "schema": self.schema,
            "description": self.description,
            "context": self.context,
            "attributes": [attr.to_dict() for attr in self.attributes],
        }

    @staticmethod
    def from_dict(data: dict) -> "TargetTableModelNew":
        attrs = [Attribute.from_dict(a) for a in data.get("attributes", [])]
        return TargetTableModelNew(
            name=data.get("name", ""),
            schema=data.get("schema"),
            description=data.get("description", ""),
            context=data.get("context", "all"),
            attributes=attrs,
        )


@dataclass
class WorkflowNewModel:
    """Облегченная модель workflow.

    Поля:
    - model_name: имя модели
    - model_path: путь к модели
    - target_table: целевая таблица (без primary_keys, config_sources)
    - sql_objects: SQL объекты (полная версия с config, config_sources)
    - parameters: параметры
    - tools: список tools
    - folders: папки (текущий FolderModel)
    - contexts: контексты проекта (полный ContextModel, переименовано из all_contexts)
    - project: проект с именем и properties
    - graph: граф workflow {context: {tool: {steps, edges}}}
    - template: workflow_template с информацией об источнике
    """

    model_name: str
    model_path: Path
    target_table: TargetTableModelNew
    models_root: str = ""
    sql_objects: Dict[str, SQLObjectModel] = field(default_factory=dict)
    parameters: Dict[str, ParameterModel] = field(default_factory=dict)
    tools: List[str] = field(default_factory=list)
    folders: Dict[str, FolderModel] = field(default_factory=dict)
    contexts: Dict[str, ContextModel] = field(default_factory=dict)
    project: Optional[ProjectInfo] = None
    graph: Dict[str, Dict[str, Dict[str, Any]]] = field(default_factory=dict)
    template: Optional[ConfigValue] = None

    def get_sql_object(self, key: str) -> Optional[SQLObjectModel]:
        """Получить SQL объект по ключу."""
        return self.sql_objects.get(key)

    def get_parameter(self, name: str) -> Optional[ParameterModel]:
        """Получить параметр по имени."""
        return self.parameters.get(name)

    def get_folder(self, folder_name: str) -> Optional[FolderModel]:
        """Получить папку по имени."""
        return self.folders.get(folder_name)

    @property
    def target_table_name(self) -> str:
        """Имя целевой таблицы."""
        return self.target_table.name

    @property
    def steps(self) -> List[Dict]:
        """Получить список шагов из графа."""
        if not self.graph:
            return []
        steps = []
        for context_tools in self.graph.values():
            for tool_data in context_tools.values():
                if "steps" in tool_data:
                    steps.extend(tool_data["steps"].values())
        return steps

    @property
    def project_properties(self) -> Dict[str, Any]:
        """Получить свойства проекта."""
        if self.project and self.project.project_properties:
            return self.project.project_properties
        return {}

    @property
    def all_contexts(self) -> Dict[str, "ContextModel"]:
        """Получить все контексты."""
        return self.contexts

    @property
    def context_name(self) -> str:
        """Получить имя контекста."""
        return "default"

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "model_path": str(self.model_path),
            "models_root": self.models_root,
            "target_table": self.target_table.to_dict(),
            "sql_objects": {
                key: obj.to_dict() for key, obj in self.sql_objects.items()
            },
            "parameters": {
                key: param.to_dict() for key, param in self.parameters.items()
            },
            "tools": self.tools,
            "folders": {
                name: folder.to_dict() for name, folder in self.folders.items()
            },
            "contexts": {name: ctx.to_dict() for name, ctx in self.contexts.items()},
            "project": self.project.to_dict() if self.project else None,
            "graph": self.graph,
            "template": self.template.to_dict() if self.template else None,
        }
