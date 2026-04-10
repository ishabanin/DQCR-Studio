"""Project template models."""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class ModelPaths:
    """Пути для модели проекта."""

    models_root: str = "model"
    project_config: str = "project.yml"
    model_config: str = "model.yml"
    contexts: str = "contexts"
    global_params: str = "parameters"
    local_params: str = "parameters"
    sql: str = "SQL"
    target: str = "target/{model}"

    def to_dict(self) -> dict:
        return {
            "models_root": self.models_root,
            "project_config": self.project_config,
            "model_config": self.model_config,
            "contexts": self.contexts,
            "global_params": self.global_params,
            "local_params": self.local_params,
            "sql": self.sql,
            "target": self.target,
        }

    @staticmethod
    def from_dict(data: dict) -> "ModelPaths":
        return ModelPaths(
            models_root=data.get("models_root", "model"),
            project_config=data.get("project_config", "project.yml"),
            model_config=data.get("model_config", "model.yml"),
            contexts=data.get("contexts", "contexts"),
            global_params=data.get("global_params", "parameters"),
            local_params=data.get("local_params", "parameters"),
            sql=data.get("sql", "SQL"),
            target=data.get("target", "target/{model}"),
        )

    def resolve_target(self, model_name: str) -> str:
        """Подставить имя модели в target path."""
        return self.target.replace("{model}", model_name)


@dataclass
class PropertyDefinition:
    """Определение свойства в template."""

    required: bool = False
    default_value: Any = None
    domain_type: Optional[str] = None

    def to_dict(self) -> dict:
        result = {"required": self.required}
        if self.default_value is not None:
            result["default_value"] = self.default_value
        if self.domain_type is not None:
            result["domain_type"] = self.domain_type
        return result

    @staticmethod
    def from_dict(data: dict) -> "PropertyDefinition":
        if data is None:
            return PropertyDefinition()
        return PropertyDefinition(
            required=data.get("required", False),
            default_value=data.get("default_value"),
            domain_type=data.get("domain_type"),
        )


@dataclass
class ModelConfig:
    """Параметры конфигурации модели."""

    builder: Optional[str] = None
    dependency_resolver: Optional[str] = None
    workflow_engine: Optional[str] = None
    workflow_template: Optional[str] = None
    default_materialization: Optional[str] = None
    model_ref_macro: Optional[str] = None
    parameter_macro: Optional[str] = None
    properties: Dict[str, PropertyDefinition] = field(default_factory=dict)

    def to_dict(self) -> dict:
        result = {}
        if self.builder:
            result["builder"] = self.builder
        if self.dependency_resolver:
            result["dependency_resolver"] = self.dependency_resolver
        if self.workflow_engine:
            result["workflow_engine"] = self.workflow_engine
        if self.workflow_template:
            result["workflow_template"] = self.workflow_template
        if self.default_materialization:
            result["default_materialization"] = self.default_materialization
        if self.model_ref_macro:
            result["model_ref_macro"] = self.model_ref_macro
        if self.parameter_macro:
            result["parameter_macro"] = self.parameter_macro
        if self.properties:
            result["properties"] = {k: v.to_dict() for k, v in self.properties.items()}
        return result

    @staticmethod
    def from_dict(data: dict) -> "ModelConfig":
        properties = {}
        if "properties" in data:
            for k, v in data["properties"].items():
                properties[k] = PropertyDefinition.from_dict(v)

        return ModelConfig(
            builder=data.get("builder"),
            dependency_resolver=data.get("dependency_resolver"),
            workflow_engine=data.get("workflow_engine"),
            workflow_template=data.get("workflow_template"),
            default_materialization=data.get("default_materialization"),
            model_ref_macro=data.get("model_ref_macro"),
            parameter_macro=data.get("parameter_macro"),
            properties=properties,
        )

    def merge(self, override: "ModelConfig") -> "ModelConfig":
        """Слить с переопределением (override имеет больший приоритет)."""
        result = ModelConfig()
        result.builder = override.builder if override.builder else self.builder
        result.dependency_resolver = (
            override.dependency_resolver
            if override.dependency_resolver
            else self.dependency_resolver
        )
        result.workflow_engine = (
            override.workflow_engine
            if override.workflow_engine
            else self.workflow_engine
        )
        result.workflow_template = (
            override.workflow_template
            if override.workflow_template
            else self.workflow_template
        )
        result.default_materialization = (
            override.default_materialization
            if override.default_materialization
            else self.default_materialization
        )
        result.model_ref_macro = (
            override.model_ref_macro
            if override.model_ref_macro
            else self.model_ref_macro
        )
        result.parameter_macro = (
            override.parameter_macro
            if override.parameter_macro
            else self.parameter_macro
        )
        result.properties = {**self.properties, **override.properties}
        return result


@dataclass
class RuleDefinition:
    """Определение правила для объекта."""

    required: bool = True
    enabled: bool = True
    materialized: Optional[str] = None
    domain_type: Optional[str] = None
    pre: List[str] = field(default_factory=list)
    post: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        result = {"required": self.required, "enabled": self.enabled}
        if self.materialized:
            result["materialized"] = self.materialized
        if self.domain_type:
            result["domain_type"] = self.domain_type
        if self.pre:
            result["pre"] = self.pre
        if self.post:
            result["post"] = self.post
        return result

    @staticmethod
    def from_dict(data: dict) -> "RuleDefinition":
        pre = data.get("pre", [])
        if isinstance(pre, str):
            pre = [pre]
        post = data.get("post", [])
        if isinstance(post, str):
            post = [post]
        return RuleDefinition(
            required=data.get("required", True),
            enabled=data.get("enabled", True),
            materialized=data.get("materialized") or data.get("materialization"),
            domain_type=data.get("domain_type"),
            pre=pre,
            post=post,
        )


@dataclass
class ModelRules:
    """Правила для объектов модели."""

    folders: Dict[str, RuleDefinition] = field(default_factory=dict)
    queries: Dict[str, RuleDefinition] = field(default_factory=dict)
    parameters: Dict[str, RuleDefinition] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "folders": {k: v.to_dict() for k, v in self.folders.items()},
            "queries": {k: v.to_dict() for k, v in self.queries.items()},
            "parameters": {k: v.to_dict() for k, v in self.parameters.items()},
        }

    @staticmethod
    def from_dict(data: dict) -> "ModelRules":
        folders = {}
        queries = {}
        parameters = {}

        if "folders" in data:
            for k, v in data["folders"].items():
                folders[k] = RuleDefinition.from_dict(v)

        if "queries" in data:
            for k, v in data["queries"].items():
                queries[k] = RuleDefinition.from_dict(v)

        if "parameters" in data:
            for k, v in data["parameters"].items():
                parameters[k] = RuleDefinition.from_dict(v)

        return ModelRules(folders=folders, queries=queries, parameters=parameters)

    def merge(self, override: "ModelRules") -> "ModelRules":
        """Слить правила с переопределением."""
        result = ModelRules()

        result.folders = {**self.folders, **override.folders}
        result.queries = {**self.queries, **override.queries}
        result.parameters = {**self.parameters, **override.parameters}

        return result


@dataclass
class ModelDefinition:
    """Определение модели в шаблоне."""

    name: str
    paths: ModelPaths
    config: ModelConfig
    rules: ModelRules
    validation_categories: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "paths": self.paths.to_dict(),
            "config": self.config.to_dict(),
            "rules": self.rules.to_dict(),
            "validation_categories": self.validation_categories,
        }

    @staticmethod
    def from_dict(data: dict) -> "ModelDefinition":
        return ModelDefinition(
            name=data.get("name", ""),
            paths=ModelPaths.from_dict(data.get("paths", {})),
            config=ModelConfig.from_dict(data.get("config", {})),
            rules=ModelRules.from_dict(data.get("rules", {})),
            validation_categories=data.get("validation_categories", []),
        )


@dataclass
class ProjectTemplate:
    """Шаблон проекта."""

    name: str
    description: str = ""
    models: List[ModelDefinition] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "models": [m.to_dict() for m in self.models],
        }

    @staticmethod
    def from_dict(data: dict) -> "ProjectTemplate":
        models = []
        for m in data.get("models", []):
            models.append(ModelDefinition.from_dict(m))

        return ProjectTemplate(
            name=data.get("name", ""),
            description=data.get("description", ""),
            models=models,
        )

    def get_model(self, name: str) -> Optional[ModelDefinition]:
        """Получить модель по имени."""
        for m in self.models:
            if m.name == name:
                return m
        return None


@dataclass
class ProjectConfig:
    """Конфигурация проекта (из project.yml)."""

    name: str
    template: str = ""
    config: Optional[ModelConfig] = None
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        result = {
            "name": self.name,
            "template": self.template,
        }
        if self.config:
            result["config"] = self.config.to_dict()
        if self.properties:
            result["properties"] = self.properties
        return result

    @staticmethod
    def from_dict(data: dict) -> "ProjectConfig":
        config = None
        if "config" in data:
            config = ModelConfig.from_dict(data["config"])

        return ProjectConfig(
            name=data.get("name", ""),
            template=data.get("template", ""),
            config=config,
            properties=data.get("properties", {}),
        )
