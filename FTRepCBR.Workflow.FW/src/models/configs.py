"""Классы файлов конфигураций"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

from FW.models.attribute import Attribute
from FW.models.enabled import EnabledRule

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
class WorkflowConfig:
    """Конфигурация workflow в model.yml."""
    template: Optional[str] = None
    description: str = ""
    folders: Dict[str, FolderConfig] = field(default_factory=dict)
    cte: Optional[CTEMaterializationConfig] = None
    pre: List[str] = field(default_factory=list)
    post: List[str] = field(default_factory=list)
    
    @staticmethod
    def from_dict(data: Optional[Dict[str, Any]]) -> "WorkflowConfig":
        if data is None:
            return WorkflowConfig()
        
        template = data.get("template")
        description = data.get("description", "")
        
        folders = {}
        for f_name, f_data in data.get("folders", {}).items():
            folders[f_name] = FolderConfig.from_dict(f_data)
        
        cte_data = data.get("cte")
        cte = CTEMaterializationConfig.from_dict(cte_data)
        
        pre = data.get("pre", [])
        if isinstance(pre, str):
            pre = [pre]
        post = data.get("post", [])
        if isinstance(post, str):
            post = [post]
        
        return WorkflowConfig(
            template=template,
            description=description,
            folders=folders,
            cte=cte,
            pre=pre,
            post=post,
        )
    
    def get_folder_config(self, folder_name: str) -> Optional[FolderConfig]:
        """Получить конфиг папки."""
        return self.folders.get(folder_name)
    
    def to_dict(self) -> dict:
        result = {}
        if self.template:
            result["template"] = self.template
        if self.description:
            result["description"] = self.description
        if self.folders:
            result["folders"] = {k: v.to_dict() for k, v in self.folders.items()}
        if self.cte:
            result["cte"] = self.cte.to_dict()
        if self.pre:
            result["pre"] = self.pre
        if self.post:
            result["post"] = self.post
        return result
