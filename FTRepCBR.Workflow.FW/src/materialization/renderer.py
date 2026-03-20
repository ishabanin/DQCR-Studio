"""Materialization renderer."""
import re
from pathlib import Path
from typing import Dict, Optional, Any, List, TYPE_CHECKING
from jinja2 import Template

from FW.logging_config import get_logger
from FW.models import SQLQueryModel, ParameterModel
from FW.models.param_types import DomainType
from FW.parsing.inline_config_parser import remove_inline_configs

if TYPE_CHECKING:
    from FW.macros.env import MacroEnv
    from FW.models.step import WorkflowStepModel
    from FW.models.workflow import WorkflowModel, FolderModel


logger = get_logger("materialization")

class MaterializationRenderer:
    """Рендерер материализации.
    
    Применяет материализацию к SQLQueryModel или ParameterModel.
    Включает общий механизм замены функций.
    """
    
    def __init__(self, macro_registry, function_registry=None, workflow_engine: str = None, model_ref_macro_name: str = None):
        self.macro_registry = macro_registry
        self.function_registry = function_registry
        self.workflow_engine = workflow_engine
        self.model_ref_macro_name = model_ref_macro_name
        self._parameters: Dict[str, ParameterModel] = {}
        self._context_flags: Dict[str, Any] = {}
        self._context_constants: Dict[str, Any] = {}
        self._context_name: str = None
        if workflow_engine:
            self._param_syntax_func = self._load_param_syntax(workflow_engine)
        else:
            self._param_syntax_func = None
    
    def set_context_info(
        self,
        context_name: str = None,
        flags: Dict[str, Any] = None,
        constants: Dict[str, Any] = None
    ) -> None:
        """Установить информацию о контексте для использования в макросах.
        
        Args:
            context_name: Имя контекста
            flags: Флаги контекста
            constants: Константы контекста
        """
        self._context_name = context_name
        self._context_flags = flags or {}
        self._context_constants = constants or {}
    
    def set_model_ref_config(self, model_ref_macro_name: str) -> None:
        """Установить имя macro для разрешения model refs.
        
        Args:
            model_ref_macro_name: Имя макроса для _m.* ссылок
        """
        self.model_ref_macro_name = model_ref_macro_name
    
    def _parse_param_metadata(self, sql_content: str):
        """Парсить metadata из SQL параметра.
        
        Args:
            sql_content: SQL текст параметра
            
        Returns:
            SQLMetadata с model_refs и workflow_refs
        """
        from FW.parsing.sql_metadata import SQLMetadataParser
        
        parser = SQLMetadataParser()
        return parser.parse(sql_content)
    
    def _replace_model_refs(
        self,
        sql: str,
        metadata,
        tool: str,
        context_name: str = None,
        workflow: "WorkflowModel" = None,
        env: "MacroEnv" = None,
        step: "WorkflowStepModel" = None
    ) -> str:
        """Заменить _m.* ссылки в SQL.
        
        Args:
            sql: SQL с _m.* ссылками
            metadata: SQLMetadata с model_refs
            tool: целевой tool
            context_name: имя контекста
            workflow: WorkflowModel для макроса
            env: MacroEnv для макроса
            step: WorkflowStepModel для макроса
            
        Returns:
            SQL с замененными _m.* ссылками
        """
        if not metadata or not metadata.model_refs:
            return sql
        
        if not self.model_ref_macro_name:
            logger.warning("model_ref_macro_name not set, skipping _m.* replacement")
            return sql
        
        result = sql
        
        for ref_full, ref_info in metadata.model_refs.items():
            try:
                macro = self.macro_registry.get_model_ref_macro(self.model_ref_macro_name, tool)
                path = ref_info['path']
                context = context_name if context_name else None
                replacement = macro(path, tool, context, workflow, env, step)
                result = result.replace(ref_full, replacement)
                logger.info(f"Parameter: Replaced {ref_full} -> {replacement}")
            except Exception as e:
                logger.error(f"Parameter: Error resolving model ref {ref_full}: {e}")
        
        return result
    
    def _load_param_syntax(self, engine: str):
        """Загрузить функцию подмены параметров для workflow engine."""
        if engine is None:
            return None
            
        try:
            from pathlib import Path
            import importlib.util
            
            macros_path = Path(__file__).parent.parent / "macros" / "workflow" / engine / "param_syntax.py"
            
            if not macros_path.exists():
                logger.warning(f"Param syntax not found for engine {engine}, using default")
                return self._default_param_syntax
            
            spec = importlib.util.spec_from_file_location(f"param_syntax_{engine}", macros_path)
            if spec is None or spec.loader is None:
                return self._default_param_syntax
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, 'render_param'):
                return module.render_param
            
            logger.warning(f"render_param not found in {macros_path}, using default")
            return self._default_param_syntax
            
        except Exception as e:
            logger.warning(f"Error loading param syntax for {engine}: {e}, using default")
            return self._default_param_syntax
    
    def _default_param_syntax(
        self, 
        var_name: str, 
        value: Any = None,
        domain_type: str = DomainType.UNDEFINED,
        tool: Optional[str] = None
    ) -> str:
        """Default - возвращает {{ var_name }}."""
        return f"{{{{ {var_name} }}}}"
    
    def render_param(
        self, 
        var_name: str, 
        value: Any = None,
        domain_type: str = DomainType.UNDEFINED,
        tool: Optional[str] = None
    ) -> str:
        """Рендерит параметр в синтаксисе текущего workflow engine.
        
        Args:
            var_name: имя переменной
            value: значение параметра
            domain_type: доменный тип параметра
            tool: целевой tool (oracle, adb, postgresql)
        """
        if self._param_syntax_func is None:
            return f"{{{{ {var_name} }}}}"
        return self._param_syntax_func(var_name, value, domain_type, tool)
    
    def _get_param_domain_type(self, param_name: str) -> str:
        """Получить domain_type параметра.
        
        Args:
            param_name: имя параметра
            
        Returns:
            domain_type параметра или UNDEFINED если не найден
        """
        if param_name in self._parameters:
            return self._parameters[param_name].domain_type
        return DomainType.UNDEFINED
    
    def set_parameters(self, parameters: Dict[str, ParameterModel]) -> None:
        """Установить словарь параметров для доступа к их типам.
        
        Args:
            parameters: словарь {name: ParameterModel}
        """
        self._parameters = parameters
    
    def prepare_sql(
        self,
        sql_model: SQLQueryModel,
        tool: str,
        parameter_values: Dict[str, Any] = None,
        workflow = None,
        context_name: str = None
    ) -> str:
        """Подготовить SQL: подстановка параметров, функций, CTE-замены.
        
        Args:
            sql_model: Модель SQL запроса
            tool: Целевой tool (oracle, adb, postgresql)
            parameter_values: Значения параметров для подстановки
            workflow: Модель workflow (опционально)
            context_name: Имя контекста для подстановки значений параметров
            
        Returns:
            Подготовленный SQL для указанного tool
        """
        content = remove_inline_configs(sql_model.source_sql)
        
        content = self._replace_functions(content, sql_model.metadata, tool)
        
        cte_config = getattr(sql_model, 'cte_config', None)
        cte_table_names = getattr(sql_model, 'cte_table_names', {})
        
        if cte_config:
            ctx_name = context_name or ""
            
            cte_table_names = getattr(sql_model, 'cte_table_names', None)
            content = self._replace_cte_with_table(content, sql_model.metadata, tool, cte_config, ctx_name, cte_table_names)
        
        return content
    
    def apply_materialization(
        self,
        sql_model: SQLQueryModel,
        prepared_sql: str,
        tool: str,
        workflow: "WorkflowModel" = None,
        step: "WorkflowStepModel" = None
    ) -> str:
        """Применить шаблон материализации.
        
        Args:
            sql_model: Модель SQL запроса
            prepared_sql: Подготовленный SQL
            tool: Целевой tool
            workflow: Модель workflow (опционально)
            step: Шаг workflow (опционально, для Python-макросов)
            
        Returns:
            Материализованный SQL
        """
        return self._apply_materialization(sql_model, prepared_sql, tool, workflow, step)
    
    def render_sql_query(
        self,
        sql_model: SQLQueryModel,
        tool: str,
        parameter_values: Dict[str, Any] = None,
        workflow: "WorkflowModel" = None,
        step: "WorkflowStepModel" = None
    ) -> str:
        """Применить материализацию к SQLQueryModel.
        
        Процесс:
        1. Подготовка SQL (подстановка параметров, функций, CTE-замены)
        2. Применение шаблона материализации
        
        Args:
            sql_model: Модель SQL запроса
            tool: Целевой tool (oracle, adb, postgresql)
            parameter_values: Значения параметров для подстановки
            workflow: Модель workflow (опционально, для доступа к target_table)
            step: Шаг workflow (опционально)
            
        Returns:
            Материализованный SQL для указанного tool
        """
        prepared = self.prepare_sql(sql_model, tool, parameter_values, workflow)
        rendered = self.apply_materialization(sql_model, prepared, tool, workflow, step)
        return rendered
    
    def prepare_param(
        self,
        param_model: ParameterModel,
        tool: str,
        parameter_values: Dict = None,
        context_name: str = "default",
        workflow: "WorkflowModel" = None,
        env: "MacroEnv" = None,
        step: "WorkflowStepModel" = None
    ) -> str:
        """Подготовить SQL параметра: подстановка параметров, замена функций, _m.* замены.
        
        Args:
            param_model: Модель параметра
            tool: Целевой tool
            parameter_values: Значения параметров для подстановки
            context_name: Имя контекста
            workflow: WorkflowModel для макросов
            env: MacroEnv для макросов
            step: WorkflowStepModel для макросов
            
        Returns:
            Подготовленный SQL для параметра
        """
        if not param_model.is_dynamic(context_name):
            return ""
        
        sql = remove_inline_configs(param_model.get_value(context_name) or "")
        
        sql = self._replace_functions_from_sql(sql, tool)
        
        if not param_model.metadata:
            param_model.metadata = self._parse_param_metadata(sql)
        
        if param_model.metadata and param_model.metadata.model_refs:
            sql = self._replace_model_refs(
                sql,
                param_model.metadata,
                tool,
                context_name,
                workflow,
                env,
                step
            )
        
        return sql
    
    def render_parameter(
        self,
        param_model: ParameterModel,
        tool: str,
        parameter_values: Dict = None,
        workflow: "WorkflowModel" = None,
        context_name: str = "default",
        step: "WorkflowStepModel" = None
    ) -> str:
        """Применить материализацию к ParameterModel.
        
        Процесс:
        1. Подготовка SQL (подстановка параметров, замена функций)
        2. Применение шаблона материализации
        
        Args:
            param_model: Модель параметра
            tool: Целевой tool
            parameter_values: Значения параметров
            workflow: Модель workflow
            context_name: Имя контекста
            step: Шаг workflow
            
        Returns:
            Материализованный SQL для параметра
        """
        prepared = self.prepare_param(param_model, tool, parameter_values, context_name)
        rendered = self._apply_param_materialization(param_model, prepared, tool, workflow, step)
        return rendered
    
    def render_all(
        self,
        sql_model: SQLQueryModel,
        tools: list,
        parameter_values: Dict[str, Any] = None,
        workflow: "WorkflowModel" = None,
        context_name: str = None,
        step: "WorkflowStepModel" = None
    ) -> Dict[str, str]:
        """Применить материализацию для всех tools.
        
        Заполняет sql_model.prepared_sql и sql_model.rendered_sql.
        
        Args:
            sql_model: Модель SQL
            tools: Список tools
            parameter_values: Значения параметров
            workflow: Модель workflow
            context_name: Имя контекста для подстановки значений параметров
            step: Шаг workflow
            
        Returns:
            Dict[tool: rendered_sql]
        """
        result = {}
        for tool in tools:
            prepared = self.prepare_sql(sql_model, tool, parameter_values, workflow, context_name)
            sql_model.prepared_sql[tool] = prepared
            rendered = self.apply_materialization(sql_model, prepared, tool, workflow, step)
            
            # Используем результат из sql_model.rendered_sql (заполняется Python-макросом)
            rendered = sql_model.rendered_sql.get(tool, rendered)
            
            # Финальная подстановка: все {{ var }} → синтаксис workflow engine
            if rendered and self.workflow_engine:
                var_pattern = re.compile(r'\{\{\s*([^}]+?)\s*\}\}')
                found_vars = set(var_pattern.findall(rendered))
                if found_vars:
                    vars_dict = {v: v for v in found_vars}
                    rendered = self._substitute_params(rendered, vars_dict, tool)
            
            sql_model.rendered_sql[tool] = rendered
            
            result[tool] = rendered
        return result
    
    def render_all_params(
        self,
        param_model: ParameterModel,
        tools: list,
        parameter_values: Dict[str, Any] = None,
        workflow: "WorkflowModel" = None,
        context_name: str = "default",
        step: "WorkflowStepModel" = None
    ) -> Dict[str, str]:
        """Применить материализацию для всех tools к параметру.
        
        Заполняет param_model.source_sql, param_model.prepared_sql и param_model.rendered_sql.
        
        Args:
            param_model: Модель параметра
            tools: Список tools
            parameter_values: Значения параметров для подстановки
            workflow: Модель workflow
            context_name: Имя контекста
            step: Шаг workflow
            
        Returns:
            Dict[tool: rendered_sql]
        """
        is_dynamic = param_model.is_dynamic(context_name)
        
        if is_dynamic:
            sql_value = param_model.get_value(context_name) or ""
            param_model.source_sql = sql_value
        else:
            param_model.source_sql = None
        
        # Сохраняем текущий контекст для использования в шаблоне
        param_model._current_context = context_name
        
        # Для не-динамических параметров, подставляем значение для текущего контекста
        # Сохраняем оригинальные values для восстановления
        original_values = param_model.values
        
        if not is_dynamic:
            # Находим значение для контекста
            if context_name in param_model.values:
                # Используем значение для конкретного контекста
                param_model.values = {context_name: param_model.values[context_name]}
            elif 'all' in param_model.values:
                # Fallback на 'all'
                param_model.values = {'all': param_model.values['all']}
        
        result = {}
        for tool in tools:
            prepared = ""
            rendered = ""
            
            if is_dynamic:
                env = None
                prepared = self.prepare_param(param_model, tool, parameter_values, context_name, workflow, env, step)
                rendered = self._apply_param_materialization(param_model, prepared, tool, workflow, step)
            else:
                rendered = self._apply_param_materialization(param_model, prepared, tool, workflow, step)
            
            param_model.prepared_sql[tool] = prepared
            
            # Финальная подстановка для динамических параметров
            if rendered and self.workflow_engine:
                var_pattern = re.compile(r'\{\{\s*([^}]+?)\s*\}\}')
                found_vars = set(var_pattern.findall(rendered))
                if found_vars:
                    vars_dict = {v: v for v in found_vars}
                    rendered = self._substitute_params(rendered, vars_dict, tool)
            
            param_model.rendered_sql[tool] = rendered
            result[tool] = rendered
        
        # Восстанавливаем оригинальные values
        param_model.values = original_values
        if hasattr(param_model, '_current_context'):
            delattr(param_model, '_current_context')
        
        return result
    
    def _substitute_params(
        self,
        sql_content: str,
        parameter_values: Dict[str, Any],
        tool: Optional[str] = None
    ) -> str:
        """Подставить параметры в SQL с учётом синтаксиса workflow engine.
        
        Заменяет {{ var_name }} или {{var_name}} на синтаксис конкретного workflow engine:
        - Airflow/dbt: {{ var_name }}
        - Oracle PL/SQL: :VAR_NAME
        
        Args:
            sql_content: SQL с параметрами
            parameter_values: словарь значений параметров
            tool: целевой tool (oracle, adb, postgresql)
        """
        result = sql_content
        if parameter_values:
            for var, value in parameter_values.items():
                domain_type = self._get_param_domain_type(var)
                placeholder = self.render_param(var, value, domain_type, tool)
                # Все варианты с пробелами и без
                result = result.replace(f'{{{{ {var} }}}}', placeholder)
                result = result.replace(f'{{{{{var}}}}}', placeholder)
                result = result.replace(f'{{{{ {var}}}}}', placeholder)
                result = result.replace(f'{{{{{var} }}}}', placeholder)
                # Дополнительные варианты
                result = result.replace(f'{{{{ {var.upper()} }}}}', placeholder)
                result = result.replace(f'{{{{{var.upper()}}}}}', placeholder)
        return result
    
    def _replace_functions(
        self,
        sql_content: str,
        metadata,
        tool: str
    ) -> str:
        """Заменить вызовы функций на результат макроса.
        
        Общий механизм для SQL и параметров.
        
        Args:
            sql_content: SQL с функциями
            metadata: SQLMetadata с извлеченными функциями
            tool: целевой tool
            
        Returns:
            SQL с замененными функциями
        """
        result = sql_content
        
        if not metadata or not metadata.functions:
            return result
        
        for func_call in metadata.functions:
            func_name = func_call['name'].lower()
            params = func_call['params']
            
            original_call = f"{func_name}({','.join(params)})"
            
            replacement = self._get_function_replacement(func_name, params, tool)
            
            if replacement is not None:
                result = re.sub(re.escape(original_call), replacement, result, flags=re.IGNORECASE)
        
        return result
    
    def _replace_cte_with_table(
        self,
        sql_content: str,
        metadata,
        tool: str,
        cte_config,
        context_name: str = "",
        cte_table_names: Dict[str, str] = None
    ) -> str:
        """Заменить ссылки на CTE на таблицы, если CTE материализуется.
        
        Также удаляет определения материализованных CTE из WITH-секции.
        """
        if cte_table_names is None:
            cte_table_names = {}
        
        if not metadata or not metadata.cte or not cte_config:
            return sql_content
        
        materialized_ctes = []
        for cte_name, cte_info in metadata.cte.items():
            materialization = cte_config.get_cte_materialization(
                cte_name=cte_name,
                context_name=context_name,
                tool=tool,
                default="ephemeral"
            )
            
            if materialization != "ephemeral":
                materialized_ctes.append(cte_name)
        
        if not materialized_ctes:
            return sql_content
        
        result = sql_content
        
        for cte_name in materialized_ctes:
            table_name = cte_table_names.get(cte_name) if cte_table_names else None
            if not table_name:
                table_name = cte_table_names.get(f"{cte_name}_{context_name}") if cte_table_names else None
            if not table_name:
                table_name = f"{cte_name}_materialized"
            
            pattern = r'\bFROM\s+' + cte_name + r'(?=\b|[^\w])'
            result = re.sub(pattern, f"FROM {table_name}", result, flags=re.IGNORECASE)
            
            pattern = r'\bJOIN\s+' + cte_name + r'(?=\b|[^\w])'
            result = re.sub(pattern, f"JOIN {table_name}", result, flags=re.IGNORECASE)
        
        result = self._remove_cte_from_with(result, materialized_ctes)
        
        for cte_name in materialized_ctes:
            table_name = cte_table_names.get(cte_name) if cte_table_names else None
            if not table_name:
                table_name = cte_table_names.get(f"{cte_name}_{context_name}") if cte_table_names else None
            if not table_name:
                table_name = f"{cte_name}_materialized"
            
            pattern = r'\bFROM\s+' + cte_name + r'(?=\b|[^\w])'
            result = re.sub(pattern, f"FROM {table_name}", result, flags=re.IGNORECASE)
            
            pattern = r'\bJOIN\s+' + cte_name + r'(?=\b|[^\w])'
            result = re.sub(pattern, f"JOIN {table_name}", result, flags=re.IGNORECASE)
        
        return result
    
    def _remove_cte_from_with(self, sql_content: str, cte_names: List[str]) -> str:
        """Удалить определения CTE из WITH-секции.
        
        Args:
            sql_content: SQL с WITH
            cte_names: Список имён CTE для удаления
            
        Returns:
            SQL с удалёнными CTE определениями
        """
        cte_with_pattern = re.compile(r'\bWITH\s+', re.IGNORECASE)
        cte_def_pattern = re.compile(r'\b([a-zA-Z0-9_]+)\s+as\s*\(', re.IGNORECASE)
        
        match = cte_with_pattern.search(sql_content)
        if not match:
            return sql_content
        
        with_start = match.start()
        content_after_with = sql_content[match.end():]
        
        cte_def_matches = list(cte_def_pattern.finditer(content_after_with))
        
        if not cte_def_matches:
            return sql_content
        
        cte_names_lower = {name.lower() for name in cte_names}
        
        cte_boundaries = []
        
        for def_match in cte_def_matches:
            cte_name = def_match.group(1)
            
            start_pos = def_match.end() - 1
            paren_depth = 0
            end_pos = -1
            
            for j, char in enumerate(content_after_with[start_pos:]):
                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1
                    if paren_depth == 0:
                        end_pos = start_pos + j + 1
                        break
            
            if end_pos == -1:
                return sql_content
            
            cte_boundaries.append({
                'name': cte_name,
                'start': def_match.start(),
                'end': end_pos,
                'removed': cte_name.lower() in cte_names_lower
            })
        
        kept_ctes = [c for c in cte_boundaries if not c['removed']]
        
        if not kept_ctes:
            last_cte_end = max(c['end'] for c in cte_boundaries)
            rest_of_content = content_after_with[last_cte_end:]
            
            select_match = re.search(r'\bSELECT\b', rest_of_content, re.IGNORECASE)
            if select_match:
                select_start_in_rest = select_match.start()
                actual_select_start = last_cte_end + select_start_in_rest
                
                while actual_select_start < len(content_after_with):
                    if content_after_with[actual_select_start] not in ' \t\n\r':
                        break
                    actual_select_start += 1
                
                return sql_content[:with_start] + content_after_with[actual_select_start:]
            
            return sql_content
        
        kept_parts = []
        for cte in kept_ctes:
            kept_parts.append(content_after_with[cte['start']:cte['end']])

        remaining_ctes = ', '.join(kept_parts)

        last_cte_end = max(c['end'] for c in kept_ctes)
        
        return sql_content[:with_start] + 'WITH ' + remaining_ctes + content_after_with[last_cte_end:]
    
    def _replace_functions_from_sql(
        self,
        sql_content: str,
        tool: str
    ) -> str:
        """Заменить функции в SQL без metadata.
        
        Используется для ParameterModel, где нет metadata.
        Парсит функции из SQL напрямую.
        
        Args:
            sql_content: SQL с функциями
            tool: целевой tool
            
        Returns:
            SQL с замененными функциями
        """
        import re
        
        result = sql_content
        
        func_pattern = re.compile(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)')
        
        def replace_match(match):
            func_name = match.group(1).lower()
            params_str = match.group(2)
            
            params = self._split_params(params_str)
            
            replacement = self._get_function_replacement(func_name, params, tool)
            
            if replacement is not None:
                return replacement
            
            return match.group(0)
        
        result = func_pattern.sub(replace_match, result)
        
        return result
    
    def _split_params(self, params_str: str) -> List[str]:
        """Разделить параметры по запятым с учетом вложенности."""
        params = []
        current = ""
        depth = 0
        
        for char in params_str:
            if char == '(':
                depth += 1
                current += char
            elif char == ')':
                depth -= 1
                current += char
            elif char == ',' and depth == 0:
                if current.strip():
                    params.append(current.strip())
                current = ""
            else:
                current += char
        
        if current.strip():
            params.append(current.strip())
        
        return params
    
    def _get_function_replacement(
        self,
        func_name: str,
        params: List[str],
        tool: str
    ) -> Optional[str]:
        """Получить замену для функции.
        
        Ищет: tool-specific -> base
        
        Args:
            func_name: имя функции
            params: параметры вызова
            tool: целевой tool
            
        Returns:
            Заменяющий SQL или None если функция не найдена или не требует замены
            
        Raises:
            ValueError: Если функция не найдена для указанного tool
        """
        import types
        
        if not self.function_registry:
            return None
        
        if self.function_registry.is_prehook_function(func_name):
            return None
        
        tool_funcs = self.function_registry.get_tool_functions(tool)
        base_funcs = self.function_registry.get_base_functions()
        
        if func_name in tool_funcs:
            func_impl = tool_funcs[func_name]
        elif func_name in base_funcs:
            func_impl = base_funcs[func_name]
        else:
            # Функция не найдена - оставить без изменений
            return None
        
        # Не заменять:
        # 1. Python встроенные методы (lower, upper, trim, length и т.д.)
        #    Они являются стандартными SQL функциями и не требуют замены
        # 2. Python lambdas (coalesce, decode, ifnull и т.д.)
        #    Они возвращают значения аргументов, а не SQL строки
        if isinstance(func_impl, (types.BuiltinMethodType, types.MethodDescriptorType, types.BuiltinFunctionType)):
            return None
        
        # Проверить является ли lambda - они тоже возвращают аргументы, а не SQL
        if hasattr(func_impl, '__name__') and func_impl.__name__ == '<lambda>':
            return None
        
        try:
            return func_impl(*params)
        except Exception as e:
            raise ValueError(
                f"Error calling function '{func_name}' with params {params}: {e}"
            )
    
    def _apply_materialization(
        self,
        sql_model: SQLQueryModel,
        content: str,
        tool: str,
        workflow: "WorkflowModel" = None,
        step: "WorkflowStepModel" = None
    ) -> str:
        """Применить шаблон материализации к SQL.
        
        Args:
            sql_model: Модель SQL
            content: SQL после замены функций и CTE
            tool: целевой tool
            workflow: Модель workflow (опционально)
            step: Шаг workflow (опционально)
            
        Returns:
            Материализованный SQL
        """
        materialization = sql_model.materialization
        macro_name = f"materialization/{materialization}"
        
        print(f"[DEBUG] _apply_materialization: materialization={materialization}, tool={tool}, has_python={self.macro_registry.has_python_macro(macro_name, tool)}")
        
        # Проверяем Python-макрос
        if self.macro_registry.has_python_macro(macro_name, tool):
            try:
                from FW.macros.env import MacroEnv
                
                logger.debug(f"Using Python macro for '{macro_name}' tool={tool}")
                
                env = MacroEnv(
                    renderer=self,
                    macro_registry=self.macro_registry,
                    workflow=workflow,
                    tools=[tool],
                    step=step,
                    param_model=None,
                    context_name=self._context_name,
                    flags=self._context_flags,
                    constants=self._context_constants
                )
                
                python_macro = self.macro_registry.get_python_macro(macro_name, tool)
                python_macro(step=step, workflow=workflow, env=env)
                
                result = sql_model.rendered_sql.get(tool, content)
                logger.debug(f"After macro: rendered_sql[{tool}]={len(result) if result else 'empty'} chars")
                return result
                
            except Exception as e:
                logger.error(f"Error applying Python materialization '{materialization}': {e}")
                return content
        
        from FW.macros.exceptions import MacroNotFoundError
        raise MacroNotFoundError(f"Python macro '{macro_name}' not found for tool '{tool}'")
    
    def _apply_param_materialization(
        self,
        param_model: ParameterModel,
        sql: str,
        tool: str,
        workflow: "WorkflowModel" = None,
        step: "WorkflowStepModel" = None
    ) -> str:
        """Применить шаблон материализации к параметру.
        
        Args:
            param_model: Модель параметра
            sql: SQL после замены функций
            tool: целевой tool
            workflow: Модель workflow (опционально)
            step: Шаг workflow (опционально)
            
        Returns:
            Материализованный SQL для параметра
        """
        macro_name = "materialization/param"
        
        # Проверяем Python-макрос
        if self.macro_registry.has_python_macro(macro_name, tool):
            try:
                from FW.macros.env import MacroEnv
                
                env = MacroEnv(
                    renderer=self,
                    macro_registry=self.macro_registry,
                    workflow=workflow,
                    tools=[tool],
                    step=step,
                    param_model=param_model,
                    context_name=self._context_name,
                    flags=self._context_flags,
                    constants=self._context_constants
                )
                
                python_macro = self.macro_registry.get_python_macro(macro_name, tool)
                python_macro(step=step, workflow=workflow, env=env)
                
                return param_model.rendered_sql.get(tool, sql)
                
            except Exception as e:
                logger.error(f"Error applying Python param materialization: {e}")
                return sql
        
        from FW.macros.exceptions import MacroNotFoundError
        raise MacroNotFoundError(f"Python macro '{macro_name}' not found for tool '{tool}'")
    
    def apply_folder_macro(
        self,
        macro_name: str,
        folder_path: str,
        folder_steps: List["WorkflowStepModel"],
        tool: str,
        workflow: "WorkflowModel",
        all_steps: Optional[List["WorkflowStepModel"]] = None,
        folder: Optional["FolderModel"] = None
    ) -> None:
        """Применить макрос папки (pre/post).
        
        Макрос вызывается для добавления дополнительных шагов
        в начало или конец содержимого папки.
        
        Args:
            macro_name: Имя макроса папки
            folder_path: Путь к папке относительно корня workflow
            folder_steps: Список шагов в папке (включая вложенные)
            tool: Целевой tool
            workflow: Модель workflow
            all_steps: Список всех шагов workflow (для добавления новых шагов)
            folder: Модель папки с наследуемыми свойствами
        """
        macro_path = f"folder_macro/{macro_name}"
        
        if not self.macro_registry.has_python_macro(macro_path, tool):
            from FW.macros.exceptions import MacroNotFoundError
            raise MacroNotFoundError(f"Folder macro '{macro_name}' not found for tool '{tool}'")
        
        try:
            from FW.macros.env import MacroEnv
            
            env = MacroEnv(
                renderer=self,
                macro_registry=self.macro_registry,
                workflow=workflow,
                tools=[tool],
                step=None,
                param_model=None,
                folder_path=folder_path,
                folder_steps=folder_steps,
                steps=all_steps,
                context_name=self._context_name,
                flags=self._context_flags,
                constants=self._context_constants,
                folder=folder
            )
            
            python_macro = self.macro_registry.get_python_macro(macro_path, tool)
            python_macro(step=None, workflow=workflow, env=env)
            
            logger.debug(f"Applied folder macro '{macro_name}' to folder '{folder_path}'")
            
        except Exception as e:
            logger.error(f"Error applying folder macro '{macro_name}': {e}")
            raise
