"""Default workflow builder - main implementation."""
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from copy import deepcopy

from FW.logging_config import get_logger
from FW.models import (
    WorkflowModel, WorkflowSettings, WorkflowGraph, WorkflowStepModel, StepType,
    SQLQueryModel, SQLMetadataParser, ParameterModel, TargetTableModel,
    ContextModel, EnabledRule, WorkflowConfig, FolderConfig, FolderModel, QueryConfig,
    ProjectTemplate, ModelDefinition, ModelPaths, ModelConfig, ModelRules
)
from FW.models.param_types import DomainType
from FW.models.workflow import CTEMaterializationConfig
from FW.generation.base import BaseWorkflowBuilder
from FW.materialization.renderer import MaterializationRenderer
from FW.parsing import (
    load_project, load_project_config, load_contexts, load_parameters as load_params,
    load_model_config, load_target_table, load_folder_configs, merge_workflow_configs
)
from FW.pattern_matcher import find_matching_rule
from FW.exceptions import TemplateNotFoundError, ConfigValidationError


logger = get_logger("builder")


class DefaultBuilder(BaseWorkflowBuilder):
    """Построитель workflow - основная реализация."""
    
    def __init__(
        self,
        *args,
        context_name: str = "default",
        workflow_engine: str = None,
        template: Optional[ProjectTemplate] = None,
        model_definition: Optional[ModelDefinition] = None,
        **kwargs
    ):
        resolver_name = "naming_convention"
        
        if template and model_definition:
            template_model = template.get_model(model_definition.name)
            if template_model and template_model.config and template_model.config.dependency_resolver:
                resolver_name = template_model.config.dependency_resolver
            elif model_definition.config and model_definition.config.dependency_resolver:
                resolver_name = model_definition.config.dependency_resolver
        
        super().__init__(*args, workflow_engine=workflow_engine, resolver_name=resolver_name, **kwargs)
        self.sql_parser = SQLMetadataParser()
        self.materialization_renderer = MaterializationRenderer(
            self.macro_registry,
            self.function_registry,
            workflow_engine=workflow_engine
        )
        self._context_name = context_name
        self._context: Optional[ContextModel] = None
        self._params: Dict[str, ParameterModel] = {}
        self._config: Optional[WorkflowConfig] = None
        self._all_model_contexts: List[str] = []
        self._tools: List[str] = []
        self._model_name: str = ""
        
        self._template = template
        self._model_definition = model_definition
        self._effective_config: Optional[ModelConfig] = None
        self._effective_rules: Optional[ModelRules] = None
        self._effective_paths: Optional[ModelPaths] = None
    
    def _init_template_config(self):
        """Инициализировать конфигурацию из шаблона."""
        if not self._template or not self._model_definition:
            raise TemplateNotFoundError(
                "Template and model_definition are required. "
                "Please specify template in project.yml"
            )
        
        template_model = self._template.get_model(self._model_definition.name)
        if template_model:
            self._effective_config = template_model.config
            self._effective_rules = template_model.rules
            self._effective_paths = template_model.paths
        else:
            self._effective_config = self._model_definition.config
            self._effective_rules = self._model_definition.rules
            self._effective_paths = self._model_definition.paths
        
        if self._model_definition.config:
            for key in ['builder', 'dependency_resolver', 'workflow_engine', 'default_materialization']:
                template_val = getattr(self._effective_config, key)
                model_val = getattr(self._model_definition.config, key)
                if model_val and model_val != getattr(ModelConfig(), key):
                    setattr(self._effective_config, key, model_val)
        
        if self._model_definition.rules and self._effective_rules:
            self._effective_rules.folders = {**self._effective_rules.folders, **self._model_definition.rules.folders}
            self._effective_rules.queries = {**self._effective_rules.queries, **self._model_definition.rules.queries}
            self._effective_rules.parameters = {**self._effective_rules.parameters, **self._model_definition.rules.parameters}
        
        if self._model_definition.paths:
            for key in self._effective_paths.__dict__:
                model_val = getattr(self._model_definition.paths, key, None)
                if model_val:
                    setattr(self._effective_paths, key, model_val)
    
    def _get_model_paths(self) -> ModelPaths:
        """Получить пути модели."""
        return self._effective_paths or ModelPaths()
    
    def _get_model_contexts(self) -> List[str]:
        """Получить все контексты проекта из папки contexts/.
        
        Returns:
            Список имён контекстов ['default', 'vtb', ...]
        """
        if self._all_model_contexts:
            return self._all_model_contexts
        
        paths = self._get_model_paths()
        contexts_path = self.project_path / paths.contexts
        contexts = load_contexts(contexts_path if contexts_path.exists() else self.project_path)
        self._all_model_contexts = contexts.list_names()
        
        if not self._all_model_contexts:
            self._all_model_contexts = ['default']
            logger.warning("No contexts found, using ['default']")
        
        return self._all_model_contexts
    
    def _get_folder_step_contexts(self, folder: str) -> List[str]:
        """Получить контексты для шага папки.
        
        - enabled.contexts: [default, vtb] -> ['default', 'vtb']
        - enabled: true (без contexts) -> ['all'] (all = для всех)
        
        Args:
            folder: имя папки
            
        Returns:
            Список контекстов. Элемент 'all' означает "для всех контекстов"
        """
        folder_config = self._get_effective_folder_config(folder)
        
        if not folder_config or not folder_config.enabled:
            return ['all']
        
        if folder_config.enabled.contexts:
            return folder_config.enabled.contexts
        
        return ['all']
    
    def _get_query_step_contexts(self, folder: str, query_name: str) -> List[str]:
        """Получить контексты для SQL запроса.
        
        Наследует от папки, если не указано явно.
        
        Args:
            folder: имя папки
            query_name: имя запроса
            
        Returns:
            Список контекстов. Элемент 'all' означает "для всех контекстов проекта"
        """
        folder_contexts = self._get_folder_step_contexts(folder)
        
        # Контекст ['all'] = "для всех" - НЕ разворачиваем в _all_model_contexts
        if folder_contexts == ['all']:
            return ['all']
        
        query_config = self._get_query_config(folder, query_name)
        
        if query_config and query_config.enabled:
            if query_config.enabled.contexts:
                return [c for c in query_config.enabled.contexts if c in folder_contexts]
        
        return folder_contexts
    
    def _get_param_contexts_expanded(self, param_model: ParameterModel) -> List[str]:
        """Получить контексты для параметра с разворотом 'all'.
        
        Примеры:
            values: { all: "x" }
            проекты: [default, vtb]
            -> ['all']  (только all, не разворачиваем)
            
            values: { all: "x", vtb: "y" }
            проекты: [default, vtb]
            -> ['default', 'vtb']  (all разворачивается в default)
        
        Args:
            param_model: модель параметра
            
        Returns:
            Список контекстов
        """
        values_keys = list(param_model.values.keys())
        
        if 'all' in values_keys:
            # Только 'all' без явных переопределений - НЕ разворачиваем
            if len(values_keys) == 1:
                return ['all']
            
            # 'all' + явные контексты - разворачиваем all в остальные контексты проекта
            explicit_contexts = [c for c in values_keys if c != 'all']
            all_project_contexts = list(self._all_model_contexts)
            
            # all разворачивается во все контексты проекта, КРОМЕ явно указанных
            expanded = [c for c in all_project_contexts if c not in explicit_contexts]
            
            # Добавляем явные контексты
            return expanded + explicit_contexts
        
        return values_keys
    
    def build(self, model_name: str, context_name: Optional[str] = None) -> WorkflowModel:
        """Построить модель workflow для указанной модели.
        
        Args:
            model_name: имя модели
            context_name: имя контекста (опционально, переопределяет умолчание)
        """
        self._init_template_config()
        
        model_ref_macro_name = None
        if self._effective_config:
            model_ref_macro_name = self._effective_config.model_ref_macro
        if model_ref_macro_name:
            self.materialization_renderer.set_model_ref_config(model_ref_macro_name)
        
        if context_name:
            self._context_name = context_name
        
        paths = self._get_model_paths()
        model_path = self.project_path / paths.models_root / model_name
        
        if not model_path.exists():
            raise ValueError(f"Model not found: {model_name}")
        
        project = load_project(self.project_path)
        
        contexts = load_contexts(self.project_path)
        
        # Загружаем все контексты проекта
        self._all_model_contexts = contexts.list_names()
        if not self._all_model_contexts:
            self._all_model_contexts = ['default']
        
        # Определяем какой контекст использовать для текущего выполнения
        if context_name:
            # Явно указан контекст - используем его
            self._context = contexts.get(context_name) or contexts.get_default()
        elif context_name is None and self._context_name is None:
            # None означает "полная модель без фильтрации" - не используем конкретный контекст
            self._context = None
        else:
            self._context = contexts.get(self._context_name) or contexts.get_default()
        
        if not self._context:
            logger.warning(f"Context '{self._context_name}' not found, using empty context")
            self._context = ContextModel(name=self._context_name)
        
        # Сохраняем все tools для каждого контекста проекта
        self._tools_by_context = {}
        for ctx_name in self._all_model_contexts:
            ctx_obj = contexts.get(ctx_name)
            if ctx_obj and ctx_obj.tools:
                self._tools_by_context[ctx_name] = ctx_obj.tools
            else:
                self._tools_by_context[ctx_name] = self.tool_registry.tools
        
        # Tools для активного контекста (или все tools если не задан)
        tools_for_context = self._context.tools if self._context.tools else self.tool_registry.tools
        self._tools = tools_for_context
        
        self._params = load_params(self.project_path, model_name)
        self.materialization_renderer.set_parameters(self._params)
        
        if self._context:
            self.materialization_renderer.set_context_info(
                context_name=self._context_name,
                flags=self._context.flags._flags,
                constants=self._context.constants._constants
            )
        
        self._model_name = model_name
        
        self._config = load_model_config(model_path)
        
        folder_configs = load_folder_configs(model_path)
        self._config = merge_workflow_configs(self._config, folder_configs)
        
        target_table = load_target_table(model_path, model_name)
        
        # Строим шаги
        all_steps = []
        
        # Передаем None если контекст не задан явно
        active_context = context_name if context_name else None
        
        # Параметры (с учётом активного контекста)
        param_steps = self._build_param_steps(active_context)
        all_steps.extend(param_steps)
        
        # SQL шаги (с учётом активного контекста)
        sql_steps = self._build_sql_steps(model_path, target_table, active_context)
        all_steps.extend(sql_steps)
        
        # Загружаем project_config для получения properties
        project_config = load_project_config(self.project_path)
        
        # Вычисляем project_properties: сливаем из template (определения) и project (значения)
        project_properties: Dict[str, Any] = {}
        
        # Сначала применяем default_value из template properties
        if self._effective_config and self._effective_config.properties:
            for prop_name, prop_def in self._effective_config.properties.items():
                if prop_def.default_value is not None:
                    project_properties[prop_name] = prop_def.default_value
        
        # Переопределяем значениями из project.yml
        if project_config and project_config.properties:
            project_properties.update(project_config.properties)
        
        # Создаём workflow (пока без graph - он создаётся в конце)
        workflow = WorkflowModel(
            model_name=model_name,
            model_path=model_path,
            target_table=target_table,
            settings=WorkflowSettings(),
            graph=None,  # Graph создаётся после макросов
            tools=tools_for_context,
            project_name=project.name if project else "",
            project_properties=project_properties,
            context_name=self._context_name,
            context=self._context,
            config=self._config
        )
        
        # Разрешение _w.* ссылок рекурсивно, один проход по шагам
        all_steps = self._resolve_workflow_refs(all_steps, workflow)
        
        # Финальная подстановка переменных для всех шагов после resolution
        # Это нужно потому что render_all вызывается ДО _resolve_all_model_refs
        if self.materialization_renderer.workflow_engine:
            for step in all_steps:
                if step.sql_model and step.sql_model.rendered_sql:
                    for tool, rendered in step.sql_model.rendered_sql.items():
                        if rendered:
                            import re
                            var_pattern = re.compile(r'\{\{\s*([^}]+?)\s*\}\}')
                            found_vars = set(var_pattern.findall(rendered))
                            if found_vars:
                                vars_dict = {v: v for v in found_vars}
                                rendered = self.materialization_renderer._substitute_params(rendered, vars_dict, tool)
                                step.sql_model.rendered_sql[tool] = rendered
                
                if step.param_model and step.param_model.rendered_sql:
                    for tool, rendered in step.param_model.rendered_sql.items():
                        if rendered:
                            import re
                            var_pattern = re.compile(r'\{\{\s*([^}]+?)\s*\}\}')
                            found_vars = set(var_pattern.findall(rendered))
                            if found_vars:
                                vars_dict = {v: v for v in found_vars}
                                rendered = self.materialization_renderer._substitute_params(rendered, vars_dict, tool)
                                step.param_model.rendered_sql[tool] = rendered
        
        # Сохраняем все шаги ДО применения folder macros (needed for macro access)
        workflow._all_steps = all_steps
        
        # Folder macros могут добавлять новые шаги (pre/post), поэтому вызываем ДО dependency resolver
        self._apply_folder_macros(workflow, all_steps)
        
        # Dependency resolver - устанавливает dependencies между шагами ПОСЛЕ всех добавлений
        self.dependency_resolver.resolve(all_steps)
        
        # Создаём graph ОДИН РАЗ из отсортированных шагов
        graph = WorkflowGraph()
        for step in all_steps:
            graph.add_node(step)
        workflow.graph = graph
        
        # Сохраняем все контексты проекта
        workflow.all_contexts = contexts.get_contexts()
        
        return workflow
    
    def build_all(self, context_name: Optional[str] = None) -> Dict[str, WorkflowModel]:
        """Построить модели workflow для всех моделей проекта.
        
        Args:
            context_name: имя контекста
        """
        if context_name:
            self._context_name = context_name
        
        model_dir = self.project_path / "model"
        
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
    
    def _get_effective_folder_config(self, folder: str) -> Optional[FolderConfig]:
        """Получить эффективную конфигурацию папки с каскадным наследованием.
        
        Обходит путь от корня к листу и накапливает настройки.
        Наследуются только enabled и materialized.
        
        Args:
            folder: имя папки (может содержать / для вложенных папок)
            
        Returns:
            FolderConfig с эффективными настройками
        """
        if not folder:
            return self._config.get_folder_config("") if self._config else None
        
        result = FolderConfig()
        
        parts = folder.split("/")
        
        # Накапливаем от корня к листу
        for i in range(len(parts)):
            current_path = "/".join(parts[:i+1])
            current_config = self._config.get_folder_config(current_path) if self._config else None
            
            if current_config:
                # Переопределяем только если значение явно задано
                if current_config.enabled is not None:
                    result.enabled = current_config.enabled
                if current_config.materialized is not None:
                    result.materialized = current_config.materialized
        
        return result
    
    def _is_folder_enabled(self, folder: str) -> bool:
        """Проверить, включена ли папка для текущего контекста."""
        folder_config = self._get_effective_folder_config(folder)
        
        if folder_config is None:
            return True
        
        if folder_config.enabled is None:
            return True
        
        # При построении без активного контекста (build для всех контекстов)
        # включаем все папки - контекстная фильтрация происходит позже
        if self._context_name is None:
            return True
        
        return folder_config.enabled.evaluate(
            self._context_name,
            self._context.flags._flags if self._context else {},
            self._context.constants._constants if self._context else {}
        )
    
    def _is_query_enabled(self, folder: str, query_name: str) -> bool:
        """Проверить, включен ли запрос для текущего контекста."""
        # Сначала проверяем есть ли enabled на уровне запроса в конфиге
        folder_config_exact = self._config.get_folder_config(folder) if self._config else None
        
        query_enabled = None
        if folder_config_exact:
            query_config = folder_config_exact.get_query_config(query_name)
            if query_config and query_config.enabled is not None:
                query_enabled = query_config.enabled
        
        # Если на уровне запроса не задан, используем inherited от папки
        if query_enabled is None:
            folder_config = self._get_effective_folder_config(folder)
            if folder_config is None:
                return True
            if folder_config.enabled is None:
                return True
            
            # При построении без активного контекста (build для всех контекстов)
            # включаем все запросы - контекстная фильтрация происходит позже
            if self._context_name is None:
                return True
            
            return folder_config.enabled.evaluate(
                self._context_name,
                self._context.flags._flags if self._context else {},
                self._context.constants._constants if self._context else {}
            )
        
        return query_enabled.evaluate(
            self._context_name,
            self._context.flags._flags if self._context else {},
            self._context.constants._constants if self._context else {}
        )
    
    def _get_materialization(self, folder: str) -> str:
        """Получить тип материализации для папки."""
        folder_config = self._get_effective_folder_config(folder)
        
        if folder_config and folder_config.materialized:
            return folder_config.materialized
        
        if self._effective_rules and self._effective_rules.folders:
            rule = find_matching_rule(folder, self._effective_rules.folders)
            if rule and hasattr(rule, 'materialized') and rule.materialized:
                return rule.materialized
        
        if self._effective_config.default_materialization is None:
            raise ConfigValidationError(
                "default_materialization must be specified in template or model config",
                field="default_materialization"
            )
        return self._effective_config.default_materialization
    
    def _get_folder_prepost_macros(self, folder: str) -> Tuple[List[str], List[str]]:
        """Получить списки pre/post макросов для папки.
        
        Приоритет: 
        1. model.yml folder config -> 2. model.yml root (workflow.pre/post) -> 3. template rules
        
        Args:
            folder: имя папки
            
        Returns:
            Tuple(pre_macros, post_macros)
        """
        pre_macros: List[str] = []
        post_macros: List[str] = []
        
        folder_config = self._config.get_folder_config(folder) if self._config else None
        if folder_config:
            pre_macros = list(folder_config.pre) if folder_config.pre else []
            post_macros = list(folder_config.post) if folder_config.post else []
        
        if not pre_macros and not post_macros:
            if self._config:
                if folder == "":
                    pre_macros = list(self._config.pre) if self._config.pre else []
                    post_macros = list(self._config.post) if self._config.post else []
        
        if not pre_macros and not post_macros:
            if self._effective_rules and self._effective_rules.folders:
                rule = find_matching_rule(folder, self._effective_rules.folders)
                if rule:
                    pre_macros = list(getattr(rule, 'pre', []) or [])
                    post_macros = list(getattr(rule, 'post', []) or [])
        
        if not pre_macros and not post_macros and folder == "":
            if self._effective_rules and self._effective_rules.folders:
                root_rule = self._effective_rules.folders.get("root")
                if root_rule:
                    pre_macros = list(getattr(root_rule, 'pre', []) or [])
                    post_macros = list(getattr(root_rule, 'post', []) or [])
        
        return pre_macros, post_macros
    
    def _get_folder_steps_recursive(
        self,
        folder: str,
        all_steps: List["WorkflowStepModel"]
    ) -> List["WorkflowStepModel"]:
        """Получить все шаги папки включая вложенные папки.
        
        Args:
            folder: путь к папке
            all_steps: все шаги workflow
            
        Returns:
            Список шагов в папке и вложенных папках
        """
        if folder == "":
            root_steps = []
            for step in all_steps:
                if not step.folder or '/' not in step.folder:
                    root_steps.append(step)
            root_steps.sort(key=lambda x: x.full_name)
            return root_steps
        
        folder_steps = []
        
        for step in all_steps:
            if step.folder == folder or step.folder.startswith(f"{folder}/"):
                folder_steps.append(step)
        
        folder_steps.sort(key=lambda x: x.full_name)
        return folder_steps
    
    def _apply_folder_macros(
        self,
        workflow: "WorkflowModel",
        all_steps: List["WorkflowStepModel"]
    ) -> None:
        """Применить макросы папок (pre/post).
        
        Вызывается после построения всех шагов workflow.
        
        Args:
            workflow: Модель workflow
            all_steps: Все шаги workflow
        """
        if not all_steps:
            return
        
        # Собрать уникальные папки в топологическом порядке (родители раньше детей)
        folder_paths_set = set()
        for step in all_steps:
            if step.folder:
                parts = step.folder.split('/')
                for i in range(len(parts)):
                    folder_path = '/'.join(parts[:i+1])
                    folder_paths_set.add(folder_path)
        
        folder_paths_set.add("")
        
        # Создать FolderModel для каждой папки (топологический порядок обеспечен через sorted)
        folders: Dict[str, FolderModel] = {}
        for folder_path in sorted(folder_paths_set):
            contexts = self._get_folder_step_contexts(folder_path)
            materialized = self._get_materialization(folder_path)
            pre, post = self._get_folder_prepost_macros(folder_path)
            
            enabled = True
            if self._context_name and contexts != ['all']:
                enabled = self._context_name in contexts
            
            folder_model = FolderModel(
                name=folder_path,
                short_name=folder_path.split('/')[-1] if folder_path else "",
                enabled=enabled,
                contexts=contexts,
                materialized=materialized,
                pre=pre,
                post=post
            )
            folders[folder_path] = folder_model
        
        # Сохранить в workflow
        workflow.folders = folders
        
        # Применить макросы для каждой папки
        for folder in sorted(folder_paths_set):
            folder_model = folders.get(folder)
            pre_macros, post_macros = self._get_folder_prepost_macros(folder)
            
            if not pre_macros and not post_macros:
                continue
            
            folder_steps = self._get_folder_steps_recursive(folder, all_steps)
            
            if not folder_steps:
                continue
            
            tool = self._tools[0] if self._tools else 'oracle'
            
            for macro_name in pre_macros:
                try:
                    self.materialization_renderer.apply_folder_macro(
                        macro_name=macro_name,
                        folder_path=folder,
                        folder_steps=folder_steps,
                        tool=tool,
                        workflow=workflow,
                        all_steps=all_steps,
                        folder=folder_model
                    )
                    logger.info(f"Applied pre macro '{macro_name}' to folder '{folder}'")
                except Exception as e:
                    logger.error(f"Error applying pre macro '{macro_name}' to folder '{folder}': {e}")
            
            for macro_name in post_macros:
                try:
                    self.materialization_renderer.apply_folder_macro(
                        macro_name=macro_name,
                        folder_path=folder,
                        folder_steps=folder_steps,
                        tool=tool,
                        workflow=workflow,
                        all_steps=all_steps,
                        folder=folder_model
                    )
                    logger.info(f"Applied post macro '{macro_name}' to folder '{folder}'")
                except Exception as e:
                    logger.error(f"Error applying post macro '{macro_name}' to folder '{folder}': {e}")
    
    def _get_query_config(self, folder: str, query_name: str) -> Optional[QueryConfig]:
        """Получить конфиг запроса."""
        folder_config = self._config.get_folder_config(folder) if self._config else None
        
        if folder_config:
            return folder_config.get_query_config(query_name)
        
        return None
    
    def _is_query_ephemeral(self, folder: str, query_name: str) -> bool:
        """Проверить, является ли запрос эфемерным."""
        query_config = self._get_query_config(folder, query_name)
        
        if query_config and query_config.materialized:
            return query_config.materialized == "ephemeral"
        
        return False
    
    def _get_cte_config_for_query(self, folder: str, query_name: str) -> CTEMaterializationConfig:
        """Получить конфигурацию CTE для запроса с учетом иерархии."""
        config = CTEMaterializationConfig()
        
        default_cte_mat = "ephemeral"
        
        folder_config = self._config.get_folder_config(folder) if self._config else None
        if not folder_config or not folder_config.queries:
            return config
        
        # Ищем точное совпадение или query_name содержит ключ конфига
        matched_query_name = None
        # Также пробуем убрать префикс модели из query_name
        normalized_query_name = query_name
        for prefix in [self._model_name + '_', self._model_name]:
            if query_name.startswith(prefix):
                normalized_query_name = query_name[len(prefix):]
                break
        
        for qn in folder_config.queries.keys():
            if qn == query_name or qn == normalized_query_name:
                matched_query_name = qn
                break
            if query_name.find(qn) >= 0 or normalized_query_name.find(qn) >= 0:
                matched_query_name = qn
                break
        
        if matched_query_name:
            qc = folder_config.queries[matched_query_name]
            if qc.cte and qc.cte.cte_queries:
                for cte_name, cte_cfg in qc.cte.cte_queries.items():
                    config.cte_queries[cte_name] = cte_cfg
        
        config.cte_materialization = default_cte_mat
        
        return config
    
    def _get_cte_materialization(
        self,
        cte_name: str,
        cte_config: CTEMaterializationConfig,
        tool: str
    ) -> str:
        """Получить материализацию для конкретного CTE."""
        return cte_config.get_cte_materialization(
            cte_name=cte_name,
            context_name=self._context_name,
            tool=tool,
            default="ephemeral"
        )
    
    def _create_cte_materialization_steps(
        self,
        content: str,
        metadata,
        cte_config,
        param_values: Dict[str, Any],
        folder: str,
        query_name: str,
        context: str = '',
        tools: Optional[List[str]] = None
    ) -> Tuple[Dict[str, str], List[WorkflowStepModel]]:
        """Создать шаги материализации CTE.
        
        Returns:
            Tuple of (dict with table names, list of created steps)
        """
        result = {}
        cte_steps = []
        
        if not metadata or not metadata.cte or not cte_config:
            return result, cte_steps
        
        tools_to_use = tools if tools else self.tool_registry.tools
        
        materialized_ctes = []
        for cte_name, cte_info in metadata.cte.items():
            cte_specific = cte_config.cte_queries.get(cte_name) if cte_config else None
            
            if cte_specific and cte_specific.by_context:
                if context in cte_specific.by_context:
                    mat = cte_specific.by_context.get(context, "ephemeral")
                    if mat != "ephemeral":
                        materialized_ctes.append({
                            'name': cte_name,
                            'context_for_materialization': context,
                            'source_ctes': list(cte_info.get('source_ctes', []))
                        })
            else:
                needs_materialization = any(
                    cte_config.get_cte_materialization(
                        cte_name=cte_name,
                        context_name=context,
                        tool=tool,
                        default="ephemeral"
                    ) != "ephemeral"
                    for tool in tools_to_use
                )
                
                if needs_materialization:
                    materialized_ctes.append({
                        'name': cte_name,
                        'context_for_materialization': context,
                        'source_ctes': list(cte_info.get('source_ctes', []))
                    })
        
        if not materialized_ctes:
            return result, cte_steps
        
        materialized_ctes_sorted = self._sort_ctes_by_dependency(materialized_ctes)
        
        folder_normalized = folder.replace("__", "_")
        
        for cte_data in materialized_ctes_sorted:
            cte_name = cte_data['name']
            
            cte_sql = self.sql_parser.extract_cte_query(content, cte_name)
            if not cte_sql:
                continue
            
            cte_metadata = self.sql_parser.parse(cte_sql)
            
            ctx_for_step = context if context else 'default'
            
            cte_specific = cte_config.cte_queries.get(cte_name) if cte_config else None
            
            materialization = "ephemeral"
            if cte_specific:
                materialization = cte_config.get_cte_materialization(
                    cte_name=cte_name,
                    context_name=context,
                    tool=tools_to_use[0] if tools_to_use else None,
                    default="ephemeral"
                )
            
            if materialization == "ephemeral":
                for tool in tools_to_use:
                    mat = cte_config.get_cte_materialization(
                        cte_name=cte_name,
                        context_name=context,
                        tool=tool,
                        default="ephemeral"
                    )
                    if mat != "ephemeral":
                        materialization = mat
                        break
            
            cte_step_id = f"sql_{folder_normalized}_{query_name}_{cte_name}_{context}"
            
            cte_config_attrs = []
            if cte_config and cte_name in cte_config.cte_queries:
                cte_config_attrs = cte_config.cte_queries[cte_name].attributes
            
            inline_cte_attr_configs = cte_metadata.inline_attr_configs if cte_metadata else {}
            
            from FW.models.attribute_utils import enrich_attributes_with_config
            cte_attributes = enrich_attributes_with_config(
                cte_metadata.aliases if cte_metadata else [],
                cte_config_attrs,
                inline_cte_attr_configs
            )
            
            cte_sql_model = SQLQueryModel(
                name=cte_step_id,
                path=Path(""),
                source_sql=cte_sql,
                metadata=cte_metadata,
                materialization=materialization,
                context=context,
                rendered_sql={},
                attributes=cte_attributes,
                cte_config=None
            )
            
            materialized_tools = [
                tool for tool in tools_to_use
                if cte_config.get_cte_materialization(
                    cte_name=cte_name,
                    context_name=context,
                    tool=tool,
                    default="ephemeral"
                ) != "ephemeral"
            ]
            
            cte_folder = f"{folder}"
            cte_full_name = f"{folder}/{query_name}_{context}/cte/{cte_name}"
            
            cte_step = WorkflowStepModel(
                step_id=cte_step_id,
                name=cte_step_id,
                folder=cte_folder,
                full_name=cte_full_name,
                step_type=StepType.SQL,
                step_scope="sql",
                sql_model=cte_sql_model,
                context=context,
                dependencies=[],
                is_ephemeral=not materialized_tools,
                tools=materialized_tools
            )
            
            rendered = self.materialization_renderer.render_all(
                cte_sql_model,
                materialized_tools,
                param_values,
                None,
                step=cte_step
            )
            cte_sql_model.rendered_sql = rendered
            
            target_table = cte_sql_model.target_table
            
            result[cte_name] = target_table
            result[f"{cte_name}_{context}"] = target_table
            
            cte_steps.append(cte_step)
        
        return result, cte_steps
    
    def _build_sql_steps(self, model_path: Path, target_table: TargetTableModel, active_context: str = None) -> List[WorkflowStepModel]:
        """Построить SQL шаги из файлов с учётом контекстов.
        
        Args:
            model_path: путь к модели
            target_table: целевая таблица
            active_context: активный контекст (если задан через -c)
        """
        paths = self._get_model_paths()
        sql_dir = model_path / paths.sql
        
        if not sql_dir.exists():
            return []
        
        steps = []
        
        for sql_file in sorted(sql_dir.rglob("*.sql")):
            rel_path = sql_file.relative_to(sql_dir)
            
            parent_folder = str(rel_path.parent).replace("\\", "/")
            if parent_folder == ".":
                folder = ""
            else:
                folder = parent_folder
            
            query_name = sql_file.stem
            
            # Проверяем enabled на уровне папки
            if not self._is_folder_enabled(folder):
                logger.info(f"Skipping folder {folder} - not enabled")
                continue
            
            # Проверяем enabled на уровне запроса
            if not self._is_query_enabled(folder, query_name):
                logger.info(f"Skipping query {query_name} - not enabled")
                continue
            
            # Получаем контексты для этого запроса
            query_contexts = self._get_query_step_contexts(folder, query_name)
            
            # Проверяем, есть ли by_context в cte_config
            cte_config = self._get_cte_config_for_query(folder, query_name)
            has_by_context = False
            
            if cte_config and cte_config.cte_queries:
                for cte_name, cte_cfg in cte_config.cte_queries.items():
                    if cte_cfg.by_context:
                        has_by_context = True
                        break
            
            # Если есть by_context - работаем в режиме "по контекстам проекта"
            if has_by_context:
                # Заменяем 'all' на все контексты проекта
                if 'all' in query_contexts:
                    query_contexts.remove('all')
                # Добавляем все контексты проекта
                all_project_contexts = self._get_model_contexts()
                for ctx in all_project_contexts:
                    if ctx not in query_contexts:
                        query_contexts.append(ctx)
            
            # Фильтруем по активному контексту (без active_context - все контексты проекта)
            if active_context is not None:
                # Контекст ['all'] означает "для всех" - включаем с active_context tools
                if query_contexts == ['all']:
                    query_contexts = [active_context]
                elif active_context in query_contexts:
                    query_contexts = [active_context]
                else:
                    query_contexts = []
            else:
                # active_context is None - разворачиваем все контексты проекта
                # Если query_contexts содержит 'all', заменяем на все контексты проекта
                if 'all' in query_contexts:
                    all_project_contexts = self._get_model_contexts()
                    query_contexts = all_project_contexts
            
            # Создаем шаг с флагом is_ephemeral
            is_ephemeral = self._is_query_ephemeral(folder, query_name)
            if is_ephemeral:
                logger.info(f"Creating step for ephemeral query {query_name}")
            
            try:
                with open(sql_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                logger.warning(f"Error reading {sql_file}: {e}")
                continue
            
            metadata = self.sql_parser.parse(content)
            
            # Обрабатываем каждый контекст
            for ctx in query_contexts:
                # Определяем контекстную модель для этого шага
                ctx_for_step = ctx if ctx else 'default'
                
                materialization = self._get_materialization(folder)
                
                query_config = self._get_query_config(folder, query_name)
                if query_config is None:
                    query_config = QueryConfig()
                query_config = query_config.enrich_with_inline(content)
                
                config_attrs = query_config.attributes if query_config else []
                
                inline_attr_cfg = metadata.inline_attr_configs if metadata else {}
                
                if query_config and query_config.materialized:
                    materialization = query_config.materialized
                
                from FW.models.attribute_utils import enrich_attributes_with_config
                attributes = enrich_attributes_with_config(
                    metadata.aliases if metadata else [],
                    config_attrs,
                    inline_attr_cfg
                )
                
                # Получаем значения параметров для конкретного контекста
                param_values = self._collect_param_values(metadata.parameters, ctx)
                
                # Определяем tools для этого контекста
                if ctx == 'all':
                    tools_for_step = self.tool_registry.tools
                else:
                    tools_for_step = self._tools_by_context.get(ctx, self.tool_registry.tools)
                
                cte_config = query_config.cte
                
                cte_table_names, cte_steps_to_add = self._create_cte_materialization_steps(
                    content, metadata, cte_config, param_values, folder, query_name, ctx, tools_for_step
                )
                
                sql_model = SQLQueryModel(
                    name=query_name,
                    path=sql_file,
                    source_sql=content,
                    metadata=metadata,
                    materialization=materialization,
                    context=ctx_for_step,
                    description=query_config.description if query_config else "",
                    attributes=attributes,
                    cte_config=cte_config,
                    cte_table_names=cte_table_names
                )
                
                # Создаём шаг ДО рендеринга (нужно для Python-макросов)
                folder_normalized = folder.replace("__", "_")
                step_id_suffix = f"_{ctx}" if ctx and ctx != 'all' else ""
                
                step = WorkflowStepModel(
                    step_id=f"sql_{folder_normalized}_{query_name}{step_id_suffix}",
                    name=query_name,
                    folder=folder,
                    full_name=f"{folder}/{query_name}{step_id_suffix}/sql" if folder else f"{query_name}{step_id_suffix}",
                    step_type=StepType.SQL,
                    step_scope="sql",
                    sql_model=sql_model,
                    context=ctx if ctx else 'all',
                    is_ephemeral=is_ephemeral
                )
                
                # Рендеринг будет выполнен в _resolve_workflow_refs (один проход с разрешением _w.* ссылок)
                # Пока только подготовим tools для шага
                if is_ephemeral:
                    if ctx == 'all':
                        tools_for_step = self.tool_registry.tools
                    else:
                        tools_for_step = self._tools_by_context.get(ctx, self.tool_registry.tools)
                    
                    for tool in tools_for_step:
                        prepared = self.materialization_renderer.prepare_sql(
                            sql_model,
                            tool,
                            param_values,
                            None,
                            ctx if ctx else 'all'
                        )
                        sql_model.prepared_sql[tool] = prepared
                
                # Сначала добавляем CTE шаги
                if cte_steps_to_add:
                    steps.extend(cte_steps_to_add)
                
                if cte_steps_to_add:
                    cte_step_names = [s.full_name for s in cte_steps_to_add]
                    step.dependencies = cte_step_names
                
                steps.append(step)
        
        return steps
    
    def _add_cte_materialization_steps(
        self,
        steps: List[WorkflowStepModel],
        sql_model: SQLQueryModel,
        folder: str,
        query_name: str,
        param_values: Dict[str, Any]
    ) -> None:
        """Добавить отдельные шаги для материализованных CTE."""
        if not sql_model.metadata or not sql_model.metadata.cte:
            return
        
        cte_config = sql_model.cte_config
        if not cte_config:
            return
        
        materialized_ctes = []
        for cte_name, cte_info in sql_model.metadata.cte.items():
            needs_materialization = any(
                cte_config.get_cte_materialization(
                    cte_name=cte_name,
                    context_name=self._context_name,
                    tool=tool,
                    default="ephemeral"
                ) != "ephemeral"
                for tool in self.tool_registry.tools
            )
            
            if needs_materialization:
                materialized_ctes.append({
                    'name': cte_name,
                    'source_ctes': list(cte_info.get('source_ctes', []))
                })
        
        if not materialized_ctes:
            return
        
        materialized_ctes_sorted = self._sort_ctes_by_dependency(materialized_ctes)
        
        folder_normalized = folder.replace("__", "_")
        
        main_step_id = f"sql_{folder_normalized}_{query_name}"
        
        cte_steps = []
        for cte_data in materialized_ctes_sorted:
            cte_name = cte_data['name']
            materialization = cte_data['materialization']
            
            cte_sql = self.sql_parser.extract_cte_query(sql_model.source_sql, cte_name)
            if not cte_sql:
                logger.warning(f"Could not extract CTE query for {cte_name}")
                continue
            
            cte_metadata = self.sql_parser.parse(cte_sql)
            
            cte_sql_model = SQLQueryModel(
                name=cte_name,
                path=sql_model.path,
                source_sql=cte_sql,
                metadata=cte_metadata,
                materialization=materialization,
                context=self._context_name,
                rendered_sql={},
                attributes=[],
                cte_config=None
            )
            
            cte_step_id = f"sql_{folder_normalized}_{query_name}_{cte_name}"
            cte_full_name = f"{folder}/{query_name}/cte/{cte_name}"
            
            cte_step = WorkflowStepModel(
                step_id=cte_step_id,
                name=cte_name,
                folder=folder,
                full_name=cte_full_name,
                step_type=StepType.SQL,
                step_scope="sql",
                sql_model=cte_sql_model,
                context=self._context_name,
                dependencies=[]
            )
            
            rendered = self.materialization_renderer.render_all(
                cte_sql_model,
                self.tool_registry.tools,
                param_values,
                None,
                step=cte_step
            )
            cte_sql_model.rendered_sql = rendered
            
            cte_steps.append(cte_step)
        
        if not cte_steps:
            return
        
        main_step = None
        for step in steps:
            if step.step_id == main_step_id:
                main_step = step
                break
        
        cte_step_names = [step.full_name for step in cte_steps]
        
        for step in steps:
            if step.step_id == main_step_id:
                existing_deps = step.dependencies or []
                step.dependencies = cte_step_names + existing_deps
                break
        
        insert_idx = 0
        for idx, step in enumerate(steps):
            if step.step_id == main_step_id:
                insert_idx = idx
                break
        
        for cte_step in cte_steps:
            steps.insert(insert_idx, cte_step)
            insert_idx += 1
        
        logger.info(f"Created {len(cte_steps)} materialized CTE steps for {query_name}")
    
    def _sort_ctes_by_dependency(self, ctes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Топологическая сортировка CTE по зависимостям.
        
        CTE, которые используют другие CTE, должны выполняться позже.
        """
        if not ctes:
            return ctes
        
        cte_names = {cte['name'] for cte in ctes}
        
        in_degree = {cte['name']: 0 for cte in ctes}
        graph = {cte['name']: [] for cte in ctes}
        
        for cte in ctes:
            for source_cte in cte.get('source_ctes', []):
                if source_cte in cte_names:
                    graph[source_cte].append(cte['name'])
                    in_degree[cte['name']] += 1
        
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            for cte in ctes:
                if cte['name'] == current:
                    result.append(cte)
                    break
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        remaining = [cte for cte in ctes if cte not in result]
        result.extend(remaining)
        
        return result
    
    def _build_param_steps(self, active_context: str = None) -> List[WorkflowStepModel]:
        """Построить шаги параметров с учётом контекстов и tools.
        
        Args:
            active_context: активный контекст (если задан через -c)
        """
        steps = []
        
        for param_name, param_model in self._params.items():
            if not param_model.values:
                continue
            
            # Получаем контексты для этого параметра с разворотом 'all'
            param_contexts = self._get_param_contexts_expanded(param_model)
            
            for ctx in param_contexts:
                # Фильтруем по активному контексту
                if active_context is not None and ctx != active_context:
                    continue
                
                # Создаём копию параметра для каждого контекста
                param_model_copy = deepcopy(param_model)
                param_model_copy.prepared_sql = {}
                param_model_copy.rendered_sql = {}
                
                # Парсим SQL для динамических параметров (тот же метод что для SQL шагов)
                if param_model_copy.is_dynamic(ctx):
                    sql_value = param_model_copy.get_value(ctx) or ""
                    if sql_value:
                        param_model_copy.metadata = self.sql_parser.parse(sql_value)
                        logger.debug(f"Parsed SQL for param {param_name}: {len(param_model_copy.metadata.model_refs)} model_refs")
                
                # Формируем step_id и full_name с учётом контекста
                step_id_suffix = f"_{ctx}" if ctx and ctx != 'all' else ""
                
                # Определяем step_scope на основе domain_type
                step_scope = "flags" if param_model_copy.domain_type == DomainType.BOOL else "params"
                
                step = WorkflowStepModel(
                    step_id=f"param_{param_name}{step_id_suffix}",
                    name=f"param_{param_name}",
                    folder="",
                    full_name=f"param_{param_name}{step_id_suffix}",
                    step_type=StepType.PARAM,
                    step_scope=step_scope,
                    param_model=param_model_copy,
                    context=ctx if ctx else 'all'
                )
                
                steps.append(step)
        
        return steps
    
    def _collect_param_values(self, required_params: Set[str], context: str = None) -> Dict[str, Any]:
        """Собрать значения параметров для подстановки.
        
        Args:
            required_params: набор имён параметров, используемых в SQL
            context: контекст для получения значений ('', 'default', 'vtb', ...)
                     для пустого контекста используется ключ 'all'
        
        Returns:
            Словарь значений параметров
        """
        result = {}
        
        for param_name in required_params:
            if param_name in self._params:
                param_model = self._params[param_name]
                
                # Определяем какой ключ использовать для получения значения
                value_ctx = 'all' if (context == '' or context is None) else context
                
                value = param_model.get_value(value_ctx)
                
                if value is None:
                    value = param_model.get_value("all")
                
                if value is not None:
                    result[param_name] = value
        
        return result
    
    def _resolve_workflow_refs(
        self,
        steps: List[WorkflowStepModel],
        workflow: "WorkflowModel"
    ) -> List[WorkflowStepModel]:
        """Разрешить _w.* ссылки рекурсивно, один проход по шагам.
        
        Каждый шаг обрабатывается целиком: prepare → resolve refs → render.
        
        Также разрешает _m.* ссылки для параметров.
        
        Args:
            steps: Список шагов workflow
            workflow: Модель workflow
            
        Returns:
            Обновленный список шагов
        """
        if not steps:
            return steps
        
        sql_steps = [s for s in steps if s.step_type == StepType.SQL and s.sql_model]
        param_steps = [s for s in steps if s.step_type == StepType.PARAM and s.param_model]
        
        if not sql_steps and not param_steps:
            return steps
        
        model_ref_macro_name = None
        if self._template and self._model_definition:
            template_model = self._template.get_model(self._model_definition.name)
            if template_model:
                model_ref_macro_name = template_model.config.model_ref_macro
        
        tools = self._tools if self._tools else ['oracle']
        
        from FW.macros.env import MacroEnv
        
        env = MacroEnv(
            renderer=self.materialization_renderer,
            macro_registry=self.macro_registry,
            workflow=workflow,
            tools=tools,
            step=None,
            param_model=None,
            steps=steps,
            context_name=self._context_name,
            flags=self._context.flags._flags if self._context else {},
            constants=self._context.constants._constants if self._context else {}
        )
        
        if param_steps:
            logger.info(f"_resolve_workflow_refs: processing {len(param_steps)} param steps")
            for param_step in param_steps:
                self._resolve_single_param(param_step, workflow, env, tools, model_ref_macro_name)
        
        if not sql_steps:
            return steps
        
        logger.info(f"_resolve_workflow_refs: processing {len(sql_steps)} SQL steps")
        
        step_by_full_name = {step.full_name: step for step in sql_steps}
        
        from FW.macros.env import MacroEnv
        from FW.models.workflow import WorkflowModel as WFModel
        
        tools = self._tools if self._tools else ['oracle']
        
        env = MacroEnv(
            renderer=self.materialization_renderer,
            macro_registry=self.macro_registry,
            workflow=workflow,
            tools=tools,
            step=None,
            param_model=None,
            steps=steps,
            context_name=self._context_name,
            flags=self._context.flags._flags if self._context else {},
            constants=self._context.constants._constants if self._context else {}
        )
        
        processed_steps: set = set()
        
        def resolve_step(step: WorkflowStepModel):
            """Обработать шаг."""
            if step.step_id in processed_steps:
                return
            
            if not step.sql_model or not step.sql_model.source_sql:
                processed_steps.add(step.step_id)
                return
            
            metadata = step.sql_model.metadata
            if not metadata:
                processed_steps.add(step.step_id)
                return
            
            # Сначала рендерим зависимые шаги (_w.* ссылки) чтобы заполнился target_table
            if metadata.workflow_refs:
                for ref_full, ref_info in metadata.workflow_refs.items():
                    target_step = self._find_target_step(ref_info, sql_steps, step_by_full_name)
                    if target_step and not target_step.is_ephemeral:
                        # Рендерим зависимый шаг чтобы заполнился target_table
                        self._render_step(target_step, workflow)
            
            # Подготавливаем prepared_sql для не-ephemeral шагов
            if not step.is_ephemeral:
                ctx = step.context if step.context else 'all'
                if step.tools:
                    tools_for_step = step.tools
                elif ctx == 'all':
                    tools_for_step = self.tool_registry.tools
                else:
                    tools_for_step = self._tools_by_context.get(ctx, self.tool_registry.tools)
                
                param_values = self._collect_param_values(
                    step.sql_model.metadata.parameters if step.sql_model.metadata else [],
                    ctx
                )
                
                for tool in tools_for_step:
                    prepared = self.materialization_renderer.prepare_sql(
                        step.sql_model,
                        tool,
                        param_values,
                        None,
                        ctx
                    )
                    step.sql_model.prepared_sql[tool] = prepared
            
            # Разрешаем _m.* и _w.* ссылки в prepared_sql
            self._resolve_model_refs(step, workflow, env, model_ref_macro_name, tools)
            self._resolve_step_workflow_refs(step, sql_steps, step_by_full_name)
            
            # Рендерим текущий шаг (использует prepared_sql с заменами)
            if not step.is_ephemeral:
                self._render_step(step, workflow)
            
            processed_steps.add(step.step_id)
        
        # Обрабатываем все SQL шаги
        for step in sql_steps:
            resolve_step(step)
        
        return steps
    
    def _find_target_step(
        self,
        ref_info: dict,
        sql_steps: List[WorkflowStepModel],
        step_by_full_name: dict
    ) -> Optional[WorkflowStepModel]:
        """Найти целевой шаг по информации о ссылке."""
        query_name = ref_info['query_name']
        folder = ref_info['folder']
        
        folder_normalized = folder.replace('_', '__')
        
        target_step = step_by_full_name.get(f"{folder_normalized}/{query_name}_default")
        
        if not target_step:
            for s in sql_steps:
                step_folder_normalized = s.folder.replace('__', '_')
                if s.name == query_name and step_folder_normalized.endswith(folder):
                    target_step = s
                    break
        
        if not target_step:
            for s in sql_steps:
                if query_name in s.name and s.is_ephemeral:
                    target_step = s
                    break
        
        if not target_step:
            for s in sql_steps:
                if query_name in s.name:
                    target_step = s
                    break
        
        return target_step
    
    def _resolve_model_refs(
        self,
        step: WorkflowStepModel,
        workflow: "WorkflowModel",
        env: "MacroEnv",
        model_ref_macro_name: Optional[str],
        tools: List[str]
    ) -> dict:
        """Разрешить _m.* ссылки в шаге."""
        ref_map = {}
        
        if not step.sql_model or not step.sql_model.source_sql:
            return ref_map
        
        metadata = step.sql_model.metadata
        if not metadata or not metadata.model_refs:
            return ref_map
        
        if not model_ref_macro_name:
            logger.warning(f"Step {step.name}: model_ref_macro_name is None")
            return ref_map
        
        content = step.sql_model.source_sql
        
        for ref_full, ref_info in metadata.model_refs.items():
            try:
                tool = tools[0] if tools else 'oracle'
                macro = self.macro_registry.get_model_ref_macro(model_ref_macro_name, tool)
                path = ref_info['path']
                context = step.context if step.context else None
                replacement = macro(path, tool, context, workflow, env, step)
                ref_map[ref_full] = replacement
                logger.info(f"Step {step.name}: Replaced {ref_full} -> {replacement}")
            except Exception as e:
                logger.error(f"Step {step.name}: Error resolving model ref {ref_full}: {e}")
        
        # Применяем замены к prepared_sql
        if ref_map and step.sql_model.prepared_sql:
            for tool in step.sql_model.prepared_sql:
                prepared = step.sql_model.prepared_sql[tool]
                for ref_full, replacement in ref_map.items():
                    if ref_full in prepared:
                        prepared = prepared.replace(ref_full, replacement)
                        step.sql_model.prepared_sql[tool] = prepared
        
        return ref_map
    
    def _resolve_single_param(
        self,
        step: WorkflowStepModel,
        workflow: "WorkflowModel",
        env: "MacroEnv",
        tools: List[str],
        model_ref_macro_name: str = None
    ):
        """Разрешить ссылки для одного параметра (аналогично SQL шагам).
        
        1. prepare_sql - замена функций
        2. rendered_sql - материализация
        
        Args:
            step: Шаг параметра
            workflow: WorkflowModel
            env: MacroEnv
            tools: Список tools
            model_ref_macro_name: Имя макроса для model refs
        """
        param_model = step.param_model
        if not param_model:
            return
        
        context = step.context if step.context else 'all'
        
        step_tools = tools
        if context and context != 'all':
            step_tools = self._tools_by_context.get(context, tools)
        
        for tool in step_tools:
            prepared = self.materialization_renderer.prepare_param(
                param_model,
                tool,
                {},
                context,
                workflow,
                env,
                step
            )
            param_model.prepared_sql[tool] = prepared
        
        rendered = self.materialization_renderer._apply_param_materialization(
            param_model,
            param_model.prepared_sql.get(step_tools[0], "") if step_tools else "",
            step_tools[0] if step_tools else 'oracle',
            workflow,
            step
        )
        for tool in step_tools:
            param_model.rendered_sql[tool] = rendered
        
        logger.info(f"Param {step.name}: resolved prepared_sql and rendered_sql")
    
    def _resolve_step_workflow_refs(
        self,
        step: WorkflowStepModel,
        sql_steps: List[WorkflowStepModel],
        step_by_full_name: dict
    ):
        """Разрешить _w.* ссылки для одного шага."""
        if not step.sql_model or not step.sql_model.source_sql:
            return
        
        metadata = step.sql_model.metadata
        if not metadata or not metadata.workflow_refs:
            return
        
        workflow_ref_map = {}
        
        for ref_full, ref_info in metadata.workflow_refs.items():
            target_step = self._find_target_step(ref_info, sql_steps, step_by_full_name)
            
            if not target_step:
                logger.warning(f"Workflow step not found for {ref_full}")
                continue
            
            step_materialization = target_step.sql_model.materialization if target_step.sql_model else "insert_fc"
            
            # Эфемерный CTE - подставляем SQL
            if target_step.is_ephemeral or step_materialization == "ephemeral":
                if target_step.sql_model and target_step.sql_model.source_sql:
                    cte_name = target_step.sql_model.name
                    cte_sql = target_step.sql_model.source_sql
                    workflow_ref_map[ref_full] = (cte_name, cte_sql, True)
                    logger.info(f"Step {step.name}: Will add ephemeral CTE: {cte_name}")
            else:
                # Материализованный - используем target_table (уже заполнен макросом)
                target_table = target_step.sql_model.target_table if target_step.sql_model and target_step.sql_model.target_table else (target_step.sql_model.name if target_step.sql_model else target_step.name)
                workflow_ref_map[ref_full] = (target_table, None, False)
                logger.info(f"Step {step.name}: Replaced {ref_full} -> {target_table}")
        
        if not workflow_ref_map:
            return
        
        # Обрабатываем эфемерные CTE
        ephemeral_steps = []
        for ref_full, (cte_name, cte_sql, is_eph) in workflow_ref_map.items():
            if is_eph and cte_sql:
                for s in sql_steps:
                    if s.name == cte_name:
                        ephemeral_steps.append(s)
                        break
        
        if len(ephemeral_steps) > 1:
            temp_resolver = self.dependency_resolver.__class__()
            temp_resolver.resolve(ephemeral_steps)
            from FW.models.workflow import WorkflowGraph
            temp_graph = WorkflowGraph()
            for s in ephemeral_steps:
                temp_graph.add_node(s)
            ephemeral_ordered = list(temp_graph.topological_sort())
            ephemeral_ctes = [(s.name, s.sql_model.source_sql) for s in ephemeral_ordered if s.sql_model and s.sql_model.source_sql]
        else:
            ephemeral_ctes = [(name, sql) for ref_full, (name, sql, is_eph) in workflow_ref_map.items() if is_eph and sql]
        
        if ephemeral_ctes:
            cte_parts = [f"{name} as (\n{sql}\n)" for name, sql in ephemeral_ctes]
            cte_block = ",\n".join(cte_parts)
            
            for tool in step.sql_model.prepared_sql:
                prepared = step.sql_model.prepared_sql[tool]
                for ref_full, (cte_name, sql, is_eph) in workflow_ref_map.items():
                    if is_eph:
                        prepared = prepared.replace(ref_full, cte_name)
                prepared_upper = prepared.upper()
                with_pos = prepared_upper.find('WITH')
                if with_pos >= 0:
                    insert_pos = with_pos + 5
                    prepared = prepared[:insert_pos] + f" {cte_block},\n" + prepared[insert_pos:]
                else:
                    prepared = f"WITH {cte_block}\n{prepared}"
                step.sql_model.prepared_sql[tool] = prepared
            
            logger.info(f"Step {step.name}: Added {len(ephemeral_ctes)} ephemeral CTEs")
        
        # Заменяем материализованные ссылки в prepared_sql
        for ref_full, (target_table, _, is_eph) in workflow_ref_map.items():
            if not is_eph and target_table:
                for tool in step.sql_model.prepared_sql:
                    prepared = step.sql_model.prepared_sql[tool]
                    if ref_full in prepared:
                        step.sql_model.prepared_sql[tool] = prepared.replace(ref_full, target_table)
    
    def _render_step(self, step: WorkflowStepModel, workflow: "WorkflowModel"):
        """Отрендерить шаг (заполнить rendered_sql и target_table).
        
        Использует уже подготовленный prepared_sql с заменёнными _m.* и _w.* ссылками.
        """
        if not step.sql_model or step.is_ephemeral:
            return
        
        from FW.models.workflow import WorkflowModel
        
        ctx = step.context if step.context else 'all'
        
        if ctx == 'all':
            tools_for_step = self.tool_registry.tools
        else:
            tools_for_step = self._tools_by_context.get(ctx, self.tool_registry.tools)
        
        temp_workflow = WorkflowModel(
            model_name="",
            model_path=workflow.model_path,
            target_table=workflow.target_table,
            settings=WorkflowSettings(),
            graph=None,
            tools=tools_for_step,
        )
        
        # Получаем параметры для шага
        param_values = self._collect_param_values(
            step.sql_model.metadata.parameters if step.sql_model.metadata else [],
            ctx
        )
        
        # Подготавливаем prepared_sql только если его нет
        if not step.sql_model.prepared_sql:
            for tool in tools_for_step:
                prepared = self.materialization_renderer.prepare_sql(
                    step.sql_model,
                    tool,
                    param_values,
                    temp_workflow,
                    ctx
                )
                step.sql_model.prepared_sql[tool] = prepared
        
        # Применяем материализацию для каждого tool
        for tool in tools_for_step:
            prepared = step.sql_model.prepared_sql.get(tool)
            if not prepared:
                continue
            
            rendered = self.materialization_renderer.apply_materialization(
                step.sql_model,
                prepared,
                tool,
                temp_workflow,
                step
            )
            
            # Используем результат из sql_model.rendered_sql (заполняется Python-макросом)
            step.sql_model.rendered_sql[tool] = step.sql_model.rendered_sql.get(tool, rendered)
        
        # source_sql не меняем
