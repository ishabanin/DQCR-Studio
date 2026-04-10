"""Облегченный workflow builder - только базовые поля без рендеринга."""

from pathlib import Path
from typing import Dict, Any, List, Optional

from FW.logging_config import get_logger
from FW.models import ProjectTemplate, ModelDefinition, ModelPaths, ModelConfig
from FW.models.sql_object import SQLObjectModel, ConfigValue
from FW.models.parameter import ParameterModel
from FW.models.param_types import DomainType
from FW.models.configs import FolderModel, FolderConfig
from FW.models.workflow_new import WorkflowNewModel, TargetTableModelNew, ProjectInfo
from FW.models.context import ContextModel, ContextCollection
from FW.parsing.sql_metadata import SQLMetadataParser, SQLMetadata
from FW.parsing import (
    load_project,
    load_project_config,
    load_contexts,
    load_parameters as load_params,
    load_model_config,
    load_folder_configs,
    merge_workflow_configs,
)
from FW.generation.sql_object_config import (
    build_sql_object_config,
    build_compiled_sql_object,
)
from FW.generation.build_folder_config import build_folder_config
from FW.generation.cte_materialization import process_cte_materialization
from FW.generation.base import BaseWorkflowBuilder
from FW.generation.dependency_resolvers.resolver_factory import create_resolver_for_workflow_new
from FW.exceptions import TemplateNotFoundError
from FW.macros import WorkflowMacroManager
from FW.macros.main.materialization.materialization_macro import (
    MaterializationMacroManager,
)


logger = logger = get_logger("builder_new")


def load_target_table_new(
    model_path: Path, default_name: str = "", model_config: str = "model.yml"
) -> TargetTableModelNew:
    """Загрузить конфигурацию целевой таблицы (облегченная версия).

    Args:
        model_path: путь к директории модели
        default_name: имя по умолчанию
        model_config: имя файла конфигурации модели

    Returns:
        TargetTableModelNew (без config_sources)
    """
    import yaml

    model_yml = model_path / model_config

    if not model_yml.exists():
        return TargetTableModelNew(name=default_name)

    try:
        with open(model_yml, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        target_data = data.get("target_table", {})

        table_name = target_data.get("name", default_name)
        schema = target_data.get("schema")
        description = target_data.get("description", "")

        attrs_data = target_data.get("attributes", [])
        from FW.models.attribute import Attribute

        attributes = [Attribute.from_dict(a) for a in attrs_data]

        return TargetTableModelNew(
            name=table_name,
            schema=schema,
            description=description,
            attributes=attributes,
        )

    except Exception as e:
        logger.error(f"Error loading target table from model.yml: {e}")
        return TargetTableModelNew(name=default_name)


class DefaultBuilderNew(BaseWorkflowBuilder):
    """Облегченный построитель workflow.

    Заполняет только базовые поля модели без:
    - dependency resolution
    - materialization rendering
    - folder pre/post macros
    """

    def __init__(
        self,
        *args,
        context_name: str = "default",
        template: Optional[ProjectTemplate] = None,
        model_definition: Optional[ModelDefinition] = None,
        workflow_engine: Optional[str] = None,
        **kwargs,
    ):
        resolver_name = "naming_convention"

        if template and model_definition:
            template_model = template.get_model(model_definition.name)
            if (
                template_model
                and template_model.config
                and template_model.config.dependency_resolver
            ):
                resolver_name = template_model.config.dependency_resolver
            elif (
                model_definition.config and model_definition.config.dependency_resolver
            ):
                resolver_name = model_definition.config.dependency_resolver

        super().__init__(
            *args,
            workflow_engine=workflow_engine,
            resolver_name=resolver_name,
            **kwargs,
        )

        self._context_name = context_name
        self._context: Optional[ContextModel] = None
        self._params: Dict[str, ParameterModel] = {}
        self._config = None
        self._all_model_contexts: List[str] = []
        self._tools: List[str] = []
        self._model_name: str = ""

        self._template = template
        self._model_definition = model_definition
        self._effective_config: Optional[ModelConfig] = None
        self._effective_paths: Optional[ModelPaths] = None
        self._template_name: Optional[str] = None
        self._folder_rules: Dict[str, Any] = {}

    def _init_template_config(self):
        """Инициализировать конфигурацию из шаблона."""
        if not self._template or not self._model_definition:
            raise TemplateNotFoundError(
                "Template and model_definition are required. "
                "Please specify template in project.yml"
            )

        self._template_name = self._template.name

        template_model = self._template.get_model(self._model_definition.name)
        if template_model:
            self._effective_config = template_model.config
            self._effective_paths = template_model.paths
            self._folder_rules = (
                template_model.rules.folders if template_model.rules else {}
            )
        else:
            self._effective_config = self._model_definition.config
            self._effective_paths = self._model_definition.paths
            self._folder_rules = (
                self._model_definition.rules.folders
                if self._model_definition.rules
                else {}
            )

        if self._model_definition.config:
            for key in [
                "builder",
                "dependency_resolver",
                "workflow_engine",
                "default_materialization",
                "parameter_macro",
                "model_ref_macro",
            ]:
                template_val = getattr(self._effective_config, key)
                model_val = getattr(self._model_definition.config, key)
                if model_val and model_val != getattr(ModelConfig(), key):
                    setattr(self._effective_config, key, model_val)

        if self._model_definition.paths:
            for key in self._effective_paths.__dict__:
                model_val = getattr(self._model_definition.paths, key, None)
                if model_val:
                    setattr(self._effective_paths, key, model_val)

    def _get_model_paths(self) -> ModelPaths:
        """Получить пути модели."""
        return self._effective_paths or ModelPaths()

    def _get_model_contexts(self) -> List[str]:
        """Получить все контексты проекта."""
        if self._all_model_contexts:
            return self._all_model_contexts

        paths = self._get_model_paths()
        contexts_path = self.project_path / paths.contexts
        contexts = load_contexts(
            contexts_path if contexts_path.exists() else self.project_path
        )
        self._all_model_contexts = contexts.list_names()

        if not self._all_model_contexts:
            self._all_model_contexts = ["default"]
            logger.warning("No contexts found, using ['default']")

        return self._all_model_contexts

    def build(
        self, model_name: str, context_name: Optional[str] = None
    ) -> WorkflowNewModel:
        """Построить облегченную модель workflow.

        Args:
            model_name: имя модели
            context_name: имя контекста (опционально)
        """
        self._init_template_config()

        if context_name:
            self._context_name = context_name

        paths = self._get_model_paths()
        model_path = self.project_path / paths.models_root / model_name

        if not model_path.exists():
            raise ValueError(f"Model not found: {model_name}")

        project = load_project(self.project_path)

        contexts = load_contexts(self.project_path)

        self._all_model_contexts = contexts.list_names()
        if not self._all_model_contexts:
            self._all_model_contexts = ["default"]

        if context_name:
            self._context = contexts.get(context_name) or contexts.get_default()
        else:
            self._context = contexts.get(self._context_name) or contexts.get_default()

        if not self._context:
            logger.warning(
                f"Context '{self._context_name}' not found, using empty context"
            )
            self._context = ContextModel(name=self._context_name)

        self._tools_by_context = {}
        for ctx_name in self._all_model_contexts:
            ctx_obj = contexts.get(ctx_name)
            if ctx_obj and ctx_obj.tools:
                self._tools_by_context[ctx_name] = ctx_obj.tools
            else:
                self._tools_by_context[ctx_name] = self.tool_registry.tools

        tools_for_context = (
            self._context.tools if self._context.tools else self.tool_registry.tools
        )
        self._tools = tools_for_context

        self._params = load_params(
            self.project_path,
            model_path,
            self._effective_paths.local_params,
            self._effective_paths.global_params,
        )

        self._build_parameter_metadata(self._params)

        self._model_name = model_name

        self._config = load_model_config(model_path)

        folder_configs = load_folder_configs(model_path)
        self._config = merge_workflow_configs(self._config, folder_configs)

        paths = self._get_model_paths()
        target_table = load_target_table_new(model_path, model_name, paths.model_config)

        context_flags: Dict[str, Dict[str, Any]] = {}
        context_constants: Dict[str, Dict[str, Any]] = {}
        for ctx_name in self._get_model_contexts():
            ctx_obj = contexts.get(ctx_name)
            if ctx_obj:
                context_flags[ctx_name] = (
                    ctx_obj.flags.to_dict() if ctx_obj.flags else {}
                )
                context_constants[ctx_name] = (
                    ctx_obj.constants.to_dict() if ctx_obj.constants else {}
                )

        sql_objects = self._build_sql_objects(
            model_path, context_flags, context_constants
        )

        default_mat = (
            self._effective_config.default_materialization
            if self._effective_config and self._effective_config.default_materialization
            else "insert_fc"
        )

        cte_sql_objects = process_cte_materialization(
            sql_objects=sql_objects,
            config=self._config,
            model_contexts=self._all_model_contexts,
            tools_by_context=self._tools_by_context,
            default_materialization=default_mat,
        )
        sql_objects.update(cte_sql_objects)

        self._build_compiled_parameters(self._params)

        self._build_folders(model_path, context_flags, context_constants)

        project_config = load_project_config(self.project_path)

        project_properties: Dict[str, Dict[str, Any]] = {}

        if self._effective_config and self._effective_config.properties:
            for prop_name, prop_def in self._effective_config.properties.items():
                project_properties[prop_name] = {
                    "value": prop_def.default_value,
                    "domain_type": prop_def.domain_type,
                }

        if project_config and project_config.properties:
            for prop_name, prop_value in project_config.properties.items():
                if prop_name in project_properties:
                    project_properties[prop_name]["value"] = prop_value
                else:
                    project_properties[prop_name] = {
                        "value": prop_value,
                        "domain_type": None,
                    }

        project_model = ProjectInfo(
            project_name=project.name if project else "",
            project_properties=project_properties,
        )

        # Create workflow_for_macro BEFORE substitution
        macro_manager = WorkflowMacroManager(macro_registry=self.macro_registry)
        workflow_for_macro = WorkflowNewModel(
            model_name=model_name,
            model_path=model_path,
            models_root=self._effective_paths.models_root if self._effective_paths else "",
            target_table=target_table,
            sql_objects=sql_objects,
            parameters=self._params,
            tools=self._tools,
            folders=self._folders,
            contexts=contexts.get_contexts(),
            project=project_model,
            graph=None,  # graph will be set later
        )

        # Build graph FIRST - needed for model_ref macro (uses env.has_step_in_graph)
        graph = self._build_graph(sql_objects, self._params)
        workflow_for_macro.graph = graph

        # Run parameter_macro - regenerates prepared_sql from param values
        if self._effective_config and self._effective_config.parameter_macro:
            macro_manager.run_parameter_macro(
                workflow_for_macro, self._effective_config.parameter_macro
            )
            self._params = workflow_for_macro.parameters

        # Run model_ref_macro - now graph is set, so no errors
        if self._effective_config and self._effective_config.model_ref_macro:
            macro_manager.run_model_ref(
                workflow_for_macro, self._effective_config.model_ref_macro
            )
            sql_objects = workflow_for_macro.sql_objects
            self._params = workflow_for_macro.parameters

        macro_manager.run_functions_macro(workflow_for_macro)
        sql_objects = workflow_for_macro.sql_objects
        self._params = workflow_for_macro.parameters

        # Substitute project context refs BEFORE materialization
        # so both prepared_sql and rendered_sql have the same values
        self._substitute_project_context_refs(sql_objects, self._params, contexts)

        materialization_mgr = MaterializationMacroManager(
            macro_registry=self.macro_registry
        )
        default_mat = (
            self._effective_config.default_materialization
            if self._effective_config and self._effective_config.default_materialization
            else "insert_fc"
        )
        materialization_mgr.run_materialization(workflow_for_macro, default_mat)
        sql_objects = workflow_for_macro.sql_objects
        self._params = workflow_for_macro.parameters

        # Resolve workflow refs (_w.* references)
        self._resolve_workflow_refs(sql_objects, self._params)

        # Run dependency resolver in the end
        resolver = create_resolver_for_workflow_new(
            self._template, self._model_definition
        )

        for context in self._all_model_contexts:
            tools = self._tools_by_context.get(context, self.tool_registry.tools)
            for tool in tools:
                resolver.resolve(graph[context][tool])

        workflow = WorkflowNewModel(
            model_name=model_name,
            model_path=model_path,
            models_root=self._effective_paths.models_root if self._effective_paths else "",
            target_table=target_table,
            sql_objects=sql_objects,
            parameters=self._params,
            tools=self._tools,
            folders=self._folders,
            contexts=contexts.get_contexts(),
            project=project_model,
            graph=graph,
        )

        if self._effective_config and self._effective_config.workflow_template:
            from FW.models.sql_object import ConfigValue

            workflow.template = ConfigValue(
                value=self._effective_config.workflow_template,
                source="model_config",
                file="model.yml",
            )

        return workflow

    def _build_graph(
        self,
        sql_objects: Dict[str, SQLObjectModel],
        parameters: Dict[str, ParameterModel],
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Построить граф workflow.

        Args:
            sql_objects: SQL объекты модели
            parameters: параметры модели

        Returns:
            Graph: {context: {tool: {steps: {}, edges: []}}}
        """
        graph: Dict[str, Dict[str, Dict[str, Any]]] = {}

        for context in self._all_model_contexts:
            tools = self._tools_by_context.get(context, self.tool_registry.tools)
            graph[context] = {}

            for tool in tools:
                graph[context][tool] = {
                    "steps": {},
                    "edges": [],
                }
                steps = graph[context][tool]["steps"]

                for sql_key, sql_obj in sql_objects.items():
                    ctx_config = sql_obj.config.get(context, {})
                    enabled = ctx_config.get("enabled")

                    is_enabled = True
                    if enabled is not None:
                        if hasattr(enabled, "value"):
                            is_enabled = enabled.value
                        else:
                            is_enabled = enabled

                    if not is_enabled:
                        continue

                    sql_tools = ctx_config.get("tools", [])
                    if tool not in sql_tools:
                        continue

                    steps[sql_key] = {
                        "step_key": sql_key,
                        "context": context,
                        "tool": tool,
                        "step_type": "sql",
                        "step_scope": "sql",
                        "object_id": sql_key,
                        "asynch": False,
                    }

                for param_name, param in parameters.items():
                    param_value = param.values.get(context)
                    if param_value is None and "all" in param.values:
                        param_value = param.values.get("all")

                    if param_value is None:
                        continue

                    domain_type = param.domain_type or DomainType.UNDEFINED
                    step_scope = "flag" if domain_type == DomainType.BOOL else "param"

                    steps[param_name] = {
                        "step_key": param_name,
                        "context": context,
                        "tool": tool,
                        "step_type": "param",
                        "step_scope": step_scope,
                        "object_id": param_name,
                        "asynch": False,
                    }
        return graph

    def build_all(
        self, context_name: Optional[str] = None
    ) -> Dict[str, WorkflowNewModel]:
        """Построить модели workflow для всех моделей проекта."""
        self._init_template_config()

        if context_name:
            self._context_name = context_name

        paths = self._get_model_paths()
        model_dir = self.project_path / paths.models_root

        if not model_dir.exists():
            logger.warning(f"Model directory not found: {model_dir}")
            return {}

        result = {}
        for model_folder in model_dir.iterdir():
            if not model_folder.is_dir():
                continue

            model_name = model_folder.name
            try:
                result[model_name] = self.build(model_name, context_name)
            except Exception as e:
                logger.error(f"Error building model {model_name}: {e}")

        return result

    def _build_sql_objects(
        self,
        model_path: Path,
        context_flags: Dict[str, Dict[str, Any]],
        context_constants: Dict[str, Dict[str, Any]],
    ) -> Dict[str, SQLObjectModel]:
        """Построить SQL объекты из SQL файлов.

        Returns:
            Dict[path: SQLObjectModel]
        """
        paths = self._get_model_paths()
        sql_dir = model_path / paths.sql

        if not sql_dir.exists():
            return {}

        sql_objects: Dict[str, SQLObjectModel] = {}
        sql_parser = SQLMetadataParser()

        for sql_file in sorted(sql_dir.rglob("*.sql")):
            rel_path = sql_file.relative_to(sql_dir)

            parent_folder = str(rel_path.parent).replace("\\", "/")
            if parent_folder == ".":
                folder = ""
            elif parent_folder.startswith("SQL/"):
                folder = parent_folder[4:]
            else:
                folder = parent_folder

            query_name = sql_file.stem

            folder_config, folder_with_config = self._get_folder_config_hierarchical(
                folder
            )
            query_config = None
            if folder_config and folder_config.queries:
                query_config = folder_config.queries.get(query_name)

            folder_yml_path = None
            if folder_with_config is not None:
                sql_dir = model_path / self._get_model_paths().sql
                folder_yml_path = str(sql_dir / folder_with_config / "folder.yml")

            try:
                with open(sql_file, "r", encoding="utf-8") as f:
                    content = f.read()

                metadata = sql_parser.parse(content)

                sql_object_key = str(sql_file.relative_to(model_path)).replace(
                    "\\", "/"
                )

                sql_object = SQLObjectModel(
                    path=sql_object_key,
                    name=query_name,
                    source_sql=content,
                    metadata=metadata,
                )

                query_contexts = self._get_query_step_contexts(folder, query_name)

                sql_object.config = build_sql_object_config(
                    folder=folder,
                    query_name=query_name,
                    query_config=query_config,
                    folder_config=folder_config,
                    metadata=metadata,
                    sql_file_path=sql_object_key,
                    contexts=query_contexts,
                    all_contexts=self._get_model_contexts(),
                    default_materialization=self._effective_config.default_materialization
                    if self._effective_config
                    else "insert_fc",
                    folder_path=str(model_path / paths.sql),
                    get_parent_folder_config=lambda f: (
                        self._config.get_folder_config(f) if self._config else None
                    ),
                    template_name=self._template_name,
                    folder_rules=self._folder_rules,
                    context_flags=context_flags,
                    context_constants=context_constants,
                    folder_yml_path=folder_yml_path.replace("\\", "/")
                    if folder_yml_path
                    else None,
                    tools_by_context=self._tools_by_context,
                )

                build_compiled_sql_object(
                    sql_object=sql_object,
                    metadata=metadata,
                    all_contexts=self._get_model_contexts(),
                    tools_by_context=self._tools_by_context,
                    all_tools=self.tool_registry.tools,
                )

                sql_objects[sql_object_key] = sql_object

            except Exception as e:
                logger.error(f"Error processing SQL file {sql_file}: {e}")

        return sql_objects

    def _build_compiled_parameters(
        self,
        parameters: Dict[str, ParameterModel],
    ) -> None:
        """Заполнить compiled и config для параметров.

        Заполняется только для контекстов где есть values и их tools.
        """
        all_contexts = self._get_model_contexts()
        all_tools = self.tool_registry.tools

        for param_name, param in parameters.items():
            compiled: Dict[str, Dict[str, Dict[str, Any]]] = {}

            param_value_keys = list(param.values.keys()) if param.values else []

            if "all" in param_value_keys:
                target_contexts = all_contexts
            else:
                target_contexts = [
                    ctx for ctx in param_value_keys if ctx in all_contexts
                ]

            for ctx in target_contexts:
                tools = self._tools_by_context.get(ctx, all_tools)

                param.config[ctx] = {"tools": tools}

                compiled[ctx] = {}
                for tool in tools:
                    param_value = param.values.get(ctx)
                    if param_value is None and "all" in param_value_keys:
                        param_value = param.values.get("all")

                    is_dynamic = param_value and param_value.type == "dynamic"

                    source_sql = ""
                    if is_dynamic and param_value and param_value.value:
                        source_sql = param_value.value

                    workflow_refs = (
                        {ref: "" for ref in param.metadata.workflow_refs.keys()}
                        if param.metadata and param.metadata.workflow_refs
                        else {}
                    )
                    model_refs = (
                        {ref: "" for ref in param.metadata.model_refs.keys()}
                        if param.metadata and param.metadata.model_refs
                        else {}
                    )

                    compiled[ctx][tool] = {
                        "target_table": "",
                        "workflow_refs": workflow_refs,
                        "model_refs": model_refs,
                        "parameters": [],
                        "prepared_sql": source_sql,
                        "rendered_sql": "",
                    }

            param.compiled = compiled

    def _build_parameter_metadata(
        self,
        parameters: Dict[str, ParameterModel],
    ) -> None:
        """Построить metadata для параметров - парсить SQL для извлечения ссылок.

        Для каждого параметра с динамическим SQL значением:
        1. Получить SQL из values
        2. Парсить с помощью SQLMetadataParser
        3. Присвоить metadata в param.metadata
        """
        sql_parser = SQLMetadataParser()

        for param_name, param in parameters.items():
            if not param.values:
                continue

            all_sql = []
            for ctx, param_value in param.values.items():
                if param_value and param_value.value:
                    all_sql.append(param_value.value)

            if not all_sql:
                continue

            combined_sql = "\n".join(all_sql)

            metadata = sql_parser.parse(combined_sql)
            param.metadata = metadata

    def _get_folder_config_hierarchical(
        self, folder: str
    ) -> tuple[Optional["FolderConfig"], Optional[str]]:
        """Получить конфиг папки с учетом иерархии.

        Ищет конфиг в текущей папке и всех родителях.
        Returns: (folder_config, folder_with_config)
        """
        current_folder = folder

        while current_folder is not None:
            folder_config = (
                self._config.get_folder_config(current_folder) if self._config else None
            )

            if folder_config:
                return folder_config, current_folder

            if current_folder == "" or current_folder is None:
                break

            parent_parts = current_folder.rsplit("/", 1)
            current_folder = parent_parts[0] if len(parent_parts) > 1 else ""

        return None, None

    def _get_query_step_contexts(self, folder: str, query_name: str) -> List[str]:
        """Получить контексты для SQL запроса с учетом иерархии папок.

        Ищет конфиг в текущей папке и всех родителях.
        """
        all_contexts = self._get_model_contexts()

        current_folder = folder
        while current_folder is not None:
            folder_config = (
                self._config.get_folder_config(current_folder) if self._config else None
            )

            if (
                folder_config
                and folder_config.enabled
                and folder_config.enabled.contexts
            ):
                return folder_config.enabled.contexts

            if current_folder == "" or current_folder is None:
                break

            parent_parts = current_folder.rsplit("/", 1)
            current_folder = parent_parts[0] if len(parent_parts) > 1 else ""

        return all_contexts

    def _get_folder_step_contexts(self, folder: str) -> List[str]:
        """Получить контексты для папки с учетом иерархии.

        Ищет конфиг в текущей папке и всех родителях.
        """
        all_contexts = self._get_model_contexts()

        current_folder = folder
        while current_folder is not None:
            folder_config = (
                self._config.get_folder_config(current_folder) if self._config else None
            )

            if (
                folder_config
                and folder_config.enabled
                and folder_config.enabled.contexts
            ):
                return folder_config.enabled.contexts

            if current_folder == "" or current_folder is None:
                break

            parent_parts = current_folder.rsplit("/", 1)
            current_folder = parent_parts[0] if len(parent_parts) > 1 else ""

        return all_contexts

    def _build_folders(
        self,
        model_path: Path,
        context_flags: Dict[str, Dict[str, Any]],
        context_constants: Dict[str, Dict[str, Any]],
    ) -> None:
        """Построить модели папок."""
        paths = self._get_model_paths()
        sql_dir = model_path / paths.sql

        if not sql_dir.exists():
            self._folders = {}
            return

        folder_paths_set = set()
        for sql_file in sql_dir.rglob("*.sql"):
            rel_path = sql_file.relative_to(sql_dir)
            parent_folder = str(rel_path.parent).replace("\\", "/")
            if parent_folder != ".":
                parts = parent_folder.split("/")
                for i in range(len(parts)):
                    folder_path = "/".join(parts[: i + 1])
                    folder_paths_set.add(folder_path)

        folder_paths_set.add("")

        folders: Dict[str, FolderModel] = {}

        for folder_path in sorted(folder_paths_set):
            contexts = self._get_folder_step_contexts(folder_path)

            materialized = None
            if (
                self._effective_config
                and self._effective_config.default_materialization
            ):
                materialized = self._effective_config.default_materialization

            folder_sql_path = (
                model_path / paths.sql / folder_path
                if folder_path
                else model_path / paths.sql
            )

            effective_folder_config = (
                self._config.get_folder_config(folder_path) if self._config else None
            )

            folder_cfg = build_folder_config(
                folder=folder_path,
                folder_path=folder_sql_path,
                folder_config=effective_folder_config,
                workflow_config=effective_folder_config,
                all_contexts=self._get_model_contexts(),
                default_materialization=self._effective_config.default_materialization
                if self._effective_config
                else None,
                get_parent_folder_config=lambda f: (
                    self._config.get_folder_config(f) if self._config else None
                ),
                template_name=self._template_name,
                folder_rules=self._folder_rules,
                context_flags=context_flags,
                context_constants=context_constants,
            )

            enabled = True

            ctx_key = self._context_name if self._context_name else "default"
            pre_values = []
            post_values = []
            if folder_cfg and ctx_key in folder_cfg:
                pre_cfg = folder_cfg[ctx_key].get("pre", [])
                post_cfg = folder_cfg[ctx_key].get("post", [])
                pre_values = [v.value if hasattr(v, "value") else v for v in pre_cfg]
                post_values = [v.value if hasattr(v, "value") else v for v in post_cfg]

            folder_model = FolderModel(
                name=folder_path,
                short_name=folder_path.split("/")[-1] if folder_path else "",
                enabled=enabled,
                contexts=contexts,
                materialized=materialized,
                pre=pre_values,
                post=post_values,
                config=folder_cfg,
            )
            folders[folder_path] = folder_model

        self._folders = folders

    def _substitute_project_context_refs(
        self,
        sql_objects: Dict[str, SQLObjectModel],
        parameters: Dict[str, ParameterModel],
        contexts: "ContextCollection",
    ) -> None:
        """Подставить значения _p.props, _ctx.flags, _ctx.const в SQL.

        Для каждого объекта:
        1. Получить ссылки из metadata (project_props, context_flags, context_constants)
        2. Подставить фактические значения из project properties, context flags/const
        3. Обновить prepared_sql в compiled
        """
        project_props = {}
        if self._effective_config and self._effective_config.properties:
            for prop_name, prop_def in self._effective_config.properties.items():
                project_props[prop_name] = {
                    "value": prop_def.default_value,
                    "domain_type": prop_def.domain_type,
                }

        project_config = load_project_config(self.project_path)
        if project_config and project_config.properties:
            for prop_name, prop_value in project_config.properties.items():
                if prop_name in project_props:
                    project_props[prop_name]["value"] = prop_value
                else:
                    project_props[prop_name] = {
                        "value": prop_value,
                        "domain_type": None,
                    }

        def get_value_for_ref(ref_info: dict, ref_type: str) -> str:
            """Получить значение для подстановки."""
            name = ref_info.get("name") or ref_info.get("path", "")
            full_ref = ref_info.get("full_ref", "")

            if ref_type == "project_prop":
                prop_info = project_props.get(name, {})
                value = prop_info.get("value")
                domain_type = prop_info.get("domain_type")
            elif ref_type == "context_flag":
                parts = name.split(".") if "." in name else [name]
                value = None
                domain_type = None
                for ctx_name in self._all_model_contexts:
                    ctx_obj = contexts.get(ctx_name)
                    if ctx_obj:
                        value = ctx_obj.flags.get(name)
                        if value is None and len(parts) > 1:
                            current = ctx_obj.flags._flags
                            for part in parts:
                                if isinstance(current, dict):
                                    current = current.get(part)
                                else:
                                    current = None
                                    break
                            value = current
                        if value is not None:
                            break
            elif ref_type == "context_const":
                value = None
                domain_type = None
                for ctx_name in self._all_model_contexts:
                    ctx_obj = contexts.get(ctx_name)
                    if ctx_obj:
                        const_info = ctx_obj.constants._constants.get(name)
                        if const_info:
                            value = (
                                const_info.get("value")
                                if isinstance(const_info, dict)
                                else const_info
                            )
                            domain_type = (
                                const_info.get("domain_type")
                                if isinstance(const_info, dict)
                                else None
                            )
                        if value is not None:
                            break
            else:
                value = None
                domain_type = None

            if value is None:
                return full_ref

            if domain_type == "string":
                return f"'{value}'"
            elif domain_type == "number":
                return str(value)
            elif domain_type == "boolean":
                return "TRUE" if value else "FALSE"
            elif domain_type == "date":
                return f"DATE '{value}'"
            else:
                return str(value)

        for sql_key, sql_obj in sql_objects.items():
            if not sql_obj.metadata:
                continue

            metadata = sql_obj.metadata

            all_refs = {}
            if metadata.project_props:
                for name, info in metadata.project_props.items():
                    all_refs[info.get("full_ref", f"_p.props.{name}")] = (
                        "project_prop",
                        info,
                    )
            if metadata.context_flags:
                for path, info in metadata.context_flags.items():
                    all_refs[info.get("full_ref", f"_ctx.flags.{path}")] = (
                        "context_flag",
                        info,
                    )
            if metadata.context_constants:
                for name, info in metadata.context_constants.items():
                    all_refs[info.get("full_ref", f"_ctx.const.{name}")] = (
                        "context_const",
                        info,
                    )

            if not all_refs:
                continue

            for ctx, tool_compiled in sql_obj.compiled.items():
                for tool, compiled in tool_compiled.items():
                    prepared = compiled.get("prepared_sql", "")
                    if not prepared:
                        continue

                    updated = False
                    for full_ref, (ref_type, ref_info) in all_refs.items():
                        if full_ref in prepared:
                            replacement = get_value_for_ref(ref_info, ref_type)
                            prepared = prepared.replace(full_ref, replacement)
                            updated = True

                    if updated:
                        sql_obj.compiled[ctx][tool]["prepared_sql"] = prepared

        for param_name, param in parameters.items():
            if not param.metadata:
                continue

            metadata = param.metadata

            all_refs = {}
            if metadata.project_props:
                for name, info in metadata.project_props.items():
                    all_refs[info.get("full_ref", f"_p.props.{name}")] = (
                        "project_prop",
                        info,
                    )
            if metadata.context_flags:
                for path, info in metadata.context_flags.items():
                    all_refs[info.get("full_ref", f"_ctx.flags.{path}")] = (
                        "context_flag",
                        info,
                    )
            if metadata.context_constants:
                for name, info in metadata.context_constants.items():
                    all_refs[info.get("full_ref", f"_ctx.const.{name}")] = (
                        "context_const",
                        info,
                    )

            if not all_refs:
                continue

            for ctx, tool_compiled in param.compiled.items():
                for tool, compiled in tool_compiled.items():
                    prepared = compiled.get("prepared_sql", "")
                    if not prepared:
                        continue

                    updated = False
                    for full_ref, (ref_type, ref_info) in all_refs.items():
                        if full_ref in prepared:
                            replacement = get_value_for_ref(ref_info, ref_type)
                            prepared = prepared.replace(full_ref, replacement)
                            updated = True

                    if updated:
                        param.compiled[ctx][tool]["prepared_sql"] = prepared

    def _resolve_workflow_refs(
        self,
        sql_objects: Dict[str, SQLObjectModel],
        parameters: Dict[str, ParameterModel],
    ) -> None:
        """Заменить _w.* ссылки на target_table после материализации.

        Для каждого объекта:
        1. Найти целевой объект по workflow_refs
        2. Получить target_table из compiled[context][tool]
        3. Заменить _w.* в prepared_sql, rendered_sql и workflow_refs
        """
        all_objects: Dict[str, tuple] = {}

        for key, obj in sql_objects.items():
            obj_path = key.replace("SQL/", "").replace("\\", "/")
            if obj_path.endswith(".sql"):
                obj_path = obj_path[:-4]
            all_objects[obj_path] = ("sql_object", obj)

        for name, param in parameters.items():
            all_objects[name] = ("parameter", param)

        def normalize_folder(folder: str) -> str:
            result = folder
            result = result.replace("_distr", "__distr")
            result = result.replace("_vtb", "__vtb")
            result = result.replace("_Update", "__Update")
            return result

        def try_find_target(ref_path: str) -> Optional[tuple]:
            parts = ref_path.split(".")
            if len(parts) < 2:
                return None

            cte_idx = -1
            for i, part in enumerate(parts):
                if part == "cte":
                    cte_idx = i
                    break

            if cte_idx > 1:
                folder_parts = parts[: cte_idx - 2]
                query_name = parts[cte_idx - 2]
                cte_index = parts[cte_idx - 1]
                cte_name = parts[cte_idx + 1] if cte_idx + 1 < len(parts) else ""

                folder = "/".join(folder_parts)
                lookup = (
                    f"{folder}/{query_name}.{cte_index}.cte.{cte_name}"
                    if folder
                    else f"{query_name}.{cte_index}.cte.{cte_name}"
                )
            else:
                query_name = parts[-1]
                folder = "/".join(parts[:-1])
                lookup = f"{folder}/{query_name}" if folder else query_name

            if lookup in all_objects:
                return all_objects[lookup]

            folder_norm = normalize_folder(folder)
            lookup_norm = f"{folder_norm}/{query_name}" if folder_norm else query_name
            if lookup_norm in all_objects:
                return all_objects[lookup_norm]

            if folder:
                for k, v in all_objects.items():
                    k_name = k.split("/")[-1]
                    if k_name == query_name:
                        return v

            if folder:
                folder_norm = normalize_folder(folder)
                for k, v in all_objects.items():
                    k_folder = "/".join(k.split("/")[:-1])
                    if k_folder == folder_norm:
                        return v

            for k, v in all_objects.items():
                if k.endswith(f"/{query_name}"):
                    return v

            return None

        for obj_key, (obj_type, obj) in all_objects.items():
            for ctx, tool_compiled in obj.compiled.items():
                for tool, compiled in tool_compiled.items():
                    workflow_refs = compiled.get("workflow_refs", {})

                    metadata = getattr(obj, "metadata", None)
                    if metadata and metadata.workflow_refs:
                        for ref_full, ref_info in metadata.workflow_refs.items():
                            if ref_full not in workflow_refs:
                                workflow_refs[ref_full] = ""

                    if not workflow_refs:
                        continue

                    for ref_full, ref_value in workflow_refs.items():
                        ref_path = ref_full[3:]

                        target_obj = try_find_target(ref_path)

                        if not target_obj:
                            ref_path_slash = ref_path.replace(".", "/")
                            for k, v in all_objects.items():
                                if (
                                    ref_path_slash in k
                                    or normalize_folder(ref_path_slash) in k
                                ):
                                    target_obj = v
                                    break

                        if not target_obj:
                            continue

                        target_type, target_obj_val = target_obj
                        target_compiled = target_obj_val.compiled.get(ctx, {}).get(
                            tool, {}
                        )
                        target_table = target_compiled.get("target_table", "")

                        if not target_table:
                            continue

                        prepared = compiled.get("prepared_sql", "")
                        rendered = compiled.get("rendered_sql", "")

                        if ref_full in prepared:
                            compiled["prepared_sql"] = prepared.replace(
                                ref_full, target_table
                            )
                        if ref_full in rendered:
                            compiled["rendered_sql"] = rendered.replace(
                                ref_full, target_table
                            )

                        workflow_refs[ref_full] = target_table
