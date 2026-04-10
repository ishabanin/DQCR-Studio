import os
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass
import logging
import importlib.util
from datetime import datetime, date

from FW.logging_config import get_logger
from FW.exceptions import MacroNotFoundError
from FW.macros.env import WorkflowMacroManager, BaseMacroEnv


logger = get_logger("macros")


@dataclass
class PreHookFunction:
    """Функция, требующая выполнения в отдельном шаге workflow.

    Атрибуты:
        name: Имя функции
        func: Callable - функция-обработчик
        output_var: Имя переменной для подстановки в основной SQL
        needs_workflow: bool - требуется ли workflow/env для выполнения
    """

    name: str
    func: Callable
    output_var: str
    needs_workflow: bool = False


def _detect_needs_workflow(func: Callable) -> bool:
    """Определить нуждается ли функция в workflow/env.

    Проверяет наличие параметров 'workflow' или 'env' в сигнатуре функции.
    """
    try:
        sig = inspect.signature(func)
        params = sig.parameters
        return "workflow" in params or "env" in params
    except (ValueError, TypeError):
        return False


def prehook(output_var: Optional[str] = None) -> Callable:
    """Декоратор для функций-прехуков.

    Такие функции выполняются в отдельном шаге workflow до основного SQL.
    Результат подставляется в основной запрос через переменную.

    Все prehook функции автоматически получают workflow и env параметры.
    Если функция не использует эти параметры, они будут проигнорированы.

    Пример:
        @prehook(output_var="enum_mapping")
        def enum2str(p_enum_code):
            '''Генерирует CASE выражение для перекодировки enum.'''
            return f"CASE {p_enum_code} WHEN 1 THEN 'A' ... END"

    Пример с доступом к workflow:
        @prehook(output_var="custom_result")
        def custom_func(p_param, workflow, env):
            env.add_step(...)
            return "generated_sql"

    Args:
        output_var: Имя переменной для подстановки. По умолчанию - {func_name}_result

    Returns:
        Декоратор, возвращающий PreHookFunction
    """

    def decorator(func: Callable) -> PreHookFunction:
        needs_workflow = _detect_needs_workflow(func)
        return PreHookFunction(
            name=func.__name__,
            func=func,
            output_var=output_var or f"{func.__name__}_result",
            needs_workflow=needs_workflow,
        )

    return decorator


@dataclass
class Macro:
    """Описание макроса."""

    name: str
    path: Path
    content: str
    is_tool_specific: bool = False
    tool: Optional[str] = None
    is_python: bool = False
    callable: Optional[Callable] = None


class PythonMacroNotFoundError(Exception):
    """Исключение - Python-макрос не найден."""

    pass


class MacroRegistry:
    """Реестр макросов для DQCR Framework.

    Структура директорий:
    - main/           - Базовые макросы (обязательно)
    - oracle/         - Oracle-specific реализации
    - adb/            - ADB-specific реализации
    - postgresql/     - PostgreSQL-specific реализации

    Логика поиска макроса:
    1. <tool>/<name> (e.g., oracle/materialization/insert_fc)
    2. <tool>/**/<name> (рекурсивно во вложенных папках)
    3. main/<name> (базовый макрос)
    4. Error - если не найден
    """

    def __init__(
        self,
        macros_path: Optional[Path] = None,
        custom_macros_path: Optional[Path] = None,
    ):
        self._macros: Dict[str, Macro] = {}
        self._python_macros: Dict[str, Callable] = {}
        self._tools_path = macros_path or self._get_default_macros_path()
        self._custom_path = custom_macros_path
        self._tools = ["oracle", "adb", "postgresql"]
        self._workflow_engines = ["airflow", "dbt", "oracle_plsql", "dqcr"]
        self._workflow_templates: Dict[str, Callable] = {}
        self._load()

    def _get_default_macros_path(self) -> Path:
        """Получить путь к макросам по умолчанию."""
        fw_dir = Path(__file__).parent.parent
        return fw_dir / "macros"

    def _load(self):
        """Загрузить все макросы."""
        # Загрузка базовых макросов из main/
        main_dir = self._tools_path / "main"
        if main_dir.exists():
            self._load_macros_from_dir(main_dir, tool=None, base_path="main")

        # Загрузка tool-specific макросов
        for tool_name in self._tools:
            tool_dir = self._tools_path / tool_name
            if tool_dir.exists():
                self._load_macros_from_dir(
                    tool_dir, tool=tool_name, base_path=tool_name
                )

        # Загрузка workflow engine макросов
        for engine_name in self._workflow_engines:
            engine_dir = self._tools_path / "workflow" / engine_name
            if engine_dir.exists():
                self._load_macros_from_dir(
                    engine_dir, tool=engine_name, base_path=f"workflow/{engine_name}"
                )

        # Загрузка кастомных макросов (override)
        if self._custom_path and self._custom_path.exists():
            # main
            custom_main = self._custom_path / "main"
            if custom_main.exists():
                self._load_macros_from_dir(
                    custom_main, tool=None, base_path="main", override=True
                )

            # tools
            for tool_name in self._tools:
                custom_tool = self._custom_path / tool_name
                if custom_tool.exists():
                    self._load_macros_from_dir(
                        custom_tool, tool=tool_name, base_path=tool_name, override=True
                    )

            # workflow engines
            for engine_name in self._workflow_engines:
                custom_engine = self._custom_path / "workflow" / engine_name
                if custom_engine.exists():
                    self._load_macros_from_dir(
                        custom_engine,
                        tool=engine_name,
                        base_path=f"workflow/{engine_name}",
                        override=True,
                    )

        # Загрузка workflow engine шаблонов из templates/
        self._load_workflow_templates()

        # Загрузка Python-макросов
        self._load_python_macros()

        logger.info(
            f"Loaded {len(self._macros)} macros, {len(self._python_macros)} python macros"
        )

    def _load_python_macros(self):
        """Загрузить Python-макросы из всех директорий."""

        def load_from_dir(
            directory: Path, tool: Optional[str] = None, override: bool = False
        ):
            if not directory.exists():
                return

            for py_file in directory.rglob("*.py"):
                if py_file.stem == "__init__":
                    continue

                macro_name = self._get_python_macro_name(py_file, directory, tool)

                try:
                    spec = importlib.util.spec_from_file_location(
                        f"macro_{py_file.stem}", py_file
                    )
                    if spec is None or spec.loader is None:
                        continue

                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    func = None
                    for name in dir(module):
                        if not name.startswith("materialization_"):
                            continue
                        attr = getattr(module, name)
                        if callable(attr):
                            func = attr
                            break

                    if not func:
                        for name in dir(module):
                            if name.startswith("_") or name == "get_logger":
                                continue
                            attr = getattr(module, name)

                            attr_module = getattr(attr, "__module__", None)
                            if attr_module and attr_module.startswith("typing"):
                                continue

                            if callable(attr) and not isinstance(attr, type):
                                func = attr
                                break

                    if func:
                        key = f"{tool}/{macro_name}" if tool else f"main/{macro_name}"
                        if override or key not in self._python_macros:
                            self._python_macros[key] = func
                            action = (
                                "Overridden" if key in self._python_macros else "Loaded"
                            )
                            logger.debug(f"{action} python macro: {key}")

                except Exception as e:
                    logger.warning(f"Error loading python macro from {py_file}: {e}")

        def load_workflow_macro(
            engine_dir: Path, engine_name: str, override: bool = False
        ):
            """Загрузить Python-макрос workflow из __init__.py"""
            init_file = engine_dir / "__init__.py"
            if not init_file.exists():
                return

            try:
                spec = importlib.util.spec_from_file_location(
                    f"workflow_{engine_name}", init_file
                )
                if spec is None or spec.loader is None:
                    return

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                func = None
                for name in dir(module):
                    if name.startswith("_"):
                        continue
                    attr = getattr(module, name)
                    if isinstance(attr, type(lambda: None)):
                        func = attr
                        break

                if func:
                    key = f"{engine_name}/workflow"
                    if override or key not in self._python_macros:
                        self._python_macros[key] = func
                        action = (
                            "Overridden" if key in self._python_macros else "Loaded"
                        )
                        logger.debug(f"{action} workflow macro: {key}")

            except Exception as e:
                logger.warning(f"Error loading workflow macro from {init_file}: {e}")

        # Загрузка из main/
        main_dir = self._tools_path / "main"
        load_from_dir(main_dir, tool=None)

        # Загрузка из tool-директорий
        for tool_name in self._tools:
            tool_dir = self._tools_path / tool_name
            load_from_dir(tool_dir, tool=tool_name)

        # Загрузка workflow макросов (из __init__.py)
        for engine_name in self._workflow_engines:
            engine_dir = self._tools_path / "workflow" / engine_name
            load_workflow_macro(engine_dir, engine_name)

        # Загрузка из workflow engine директорий (не-__init__.py файлы)
        for engine_name in self._workflow_engines:
            engine_dir = self._tools_path / "workflow" / engine_name
            load_from_dir(engine_dir, tool=engine_name)

        # Кастомные макросы (override)
        if self._custom_path and self._custom_path.exists():
            custom_main = self._custom_path / "main"
            load_from_dir(custom_main, tool=None, override=True)

            for tool_name in self._tools:
                custom_tool = self._custom_path / tool_name
                load_from_dir(custom_tool, tool=tool_name, override=True)

            for engine_name in self._workflow_engines:
                custom_engine = self._custom_path / "workflow" / engine_name
                load_workflow_macro(custom_engine, engine_name, override=True)
                load_from_dir(custom_engine, tool=engine_name, override=True)

    def _get_python_macro_name(
        self, py_file: Path, base_dir: Path, tool: Optional[str]
    ) -> str:
        """Получить имя Python-макроса из пути к файлу."""
        try:
            rel_path = py_file.relative_to(base_dir)
        except ValueError:
            return py_file.stem

        parts = list(rel_path.parts)
        if parts[-1] == "__init__.py":
            return ""

        parts[-1] = parts[-1].replace(".py", "")
        parts = [p for p in parts if p]

        return "/".join(parts)

    def _load_macros_from_dir(
        self,
        directory: Path,
        tool: Optional[str] = None,
        base_path: str = "",
        override: bool = False,
    ):
        """Загрузить макросы из директории."""
        if not directory.exists():
            return

        for item in directory.rglob("*.sql.j2"):
            try:
                rel_path = item.relative_to(directory)
            except ValueError:
                continue

            # Формируем имя макроса
            parts = list(rel_path.parts)
            if parts[-1] == "__interface__.sql.j2":
                parts = parts[:-1]
            parts[-1] = parts[-1].replace(".sql.j2", "")

            macro_name = "/".join(parts)

            # Добавляем префикс tool (oracle/, adb/) или main/
            if tool:
                macro_name = f"{tool}/{macro_name}"
            else:
                macro_name = f"main/{macro_name}"

            # Читаем содержимое
            try:
                with open(item, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                logger.warning(f"Error reading macro {item}: {e}")
                continue

            macro = Macro(
                name=macro_name,
                path=item,
                content=content,
                is_tool_specific=tool is not None,
                tool=tool,
            )

            # Override или добавление
            if override or macro_name not in self._macros:
                self._macros[macro_name] = macro
                action = "Overridden" if macro_name in self._macros else "Loaded"
                logger.debug(f"{action} macro: {macro_name} (tool: {tool})")

    def _load_workflow_templates(self):
        """Загрузить шаблоны workflow engine из templates/ директорий."""
        for engine_name in self._workflow_engines:
            engine_dir = self._tools_path / "workflow" / engine_name / "templates"
            if not engine_dir.exists():
                continue

            for item in engine_dir.rglob("*.sql.j2"):
                try:
                    rel_path = item.relative_to(engine_dir)
                except ValueError:
                    continue

                parts = list(rel_path.parts)
                parts[-1] = parts[-1].replace(".sql.j2", "")
                macro_name = "/".join(parts)
                full_name = f"workflow/{engine_name}/templates/{macro_name}"

                try:
                    with open(item, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception as e:
                    logger.warning(f"Error reading template {item}: {e}")
                    continue

                macro = Macro(
                    name=full_name,
                    path=item,
                    content=content,
                    is_tool_specific=True,
                    tool=engine_name,
                )

                if full_name not in self._macros:
                    self._macros[full_name] = macro
                    logger.debug(f"Loaded workflow template: {full_name}")

        if self._custom_path and self._custom_path.exists():
            for engine_name in self._workflow_engines:
                custom_templates = (
                    self._custom_path / "workflow" / engine_name / "templates"
                )
                if not custom_templates.exists():
                    continue

                for item in custom_templates.rglob("*.sql.j2"):
                    try:
                        rel_path = item.relative_to(custom_templates)
                    except ValueError:
                        continue

                    parts = list(rel_path.parts)
                    parts[-1] = parts[-1].replace(".sql.j2", "")
                    macro_name = "/".join(parts)
                    full_name = f"workflow/{engine_name}/templates/{macro_name}"

                    try:
                        with open(item, "r", encoding="utf-8") as f:
                            content = f.read()
                    except Exception as e:
                        logger.warning(f"Error reading template {item}: {e}")
                        continue

                    macro = Macro(
                        name=full_name,
                        path=item,
                        content=content,
                        is_tool_specific=True,
                        tool=engine_name,
                    )

                    self._macros[full_name] = macro
                    logger.debug(f"Overridden workflow template: {full_name}")

        self._load_workflow_templates_python()

    def _load_workflow_templates_python(self):
        """Загрузить Python шаблоны workflow из templates/ директорий."""
        for engine_name in self._workflow_engines:
            templates_dir = self._tools_path / "workflow" / engine_name / "templates"
            if not templates_dir.exists():
                continue

            for py_file in templates_dir.glob("*.py"):
                if py_file.stem == "__init__":
                    continue

                try:
                    spec = importlib.util.spec_from_file_location(
                        f"wf_template_{engine_name}_{py_file.stem}", py_file
                    )
                    if spec is None or spec.loader is None:
                        continue

                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    func = None
                    if hasattr(module, "generate_workflow"):
                        func = module.generate_workflow

                    if func:
                        key = f"{engine_name}/{py_file.stem}"
                        self._workflow_templates[key] = func
                        logger.debug(f"Loaded workflow template: {key}")

                except Exception as e:
                    logger.warning(
                        f"Error loading workflow template from {py_file}: {e}"
                    )

        if self._custom_path and self._custom_path.exists():
            for engine_name in self._workflow_engines:
                custom_templates = (
                    self._custom_path / "workflow" / engine_name / "templates"
                )
                if not custom_templates.exists():
                    continue

                for py_file in custom_templates.glob("*.py"):
                    if py_file.stem == "__init__":
                        continue

                    try:
                        spec = importlib.util.spec_from_file_location(
                            f"wf_template_{engine_name}_{py_file.stem}", py_file
                        )
                        if spec is None or spec.loader is None:
                            continue

                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        func = None
                        if hasattr(module, "generate_workflow"):
                            func = module.generate_workflow

                        if func:
                            key = f"{engine_name}/{py_file.stem}"
                            self._workflow_templates[key] = func
                            logger.debug(f"Overridden workflow template: {key}")

                    except Exception as e:
                        logger.warning(
                            f"Error loading custom workflow template from {py_file}: {e}"
                        )

    def get_macro(self, name: str, tool: Optional[str] = None) -> Macro:
        """Получить макрос.

        Логика поиска:
        1. <tool>/<name> (tool-specific)
        2. <tool>/**/<name> (рекурсивно во вложенных папках)
        3. workflow/<engine>/templates/<name> (для workflow engines)
        4. workflow/<engine>/<name>
        5. main/<name> (базовый fallback)

        Args:
            name: Имя макроса (может включать подпапку, напр. materialization/insert_fc)
            tool: Tool (oracle/adb/postgresql) или workflow engine (airflow/dbt)

        Returns:
            Macro объект

        Raises:
            MacroNotFoundError: Если макрос не найден
        """
        # 1. Tool-specific поиск
        if tool:
            tool_path = f"{tool}/{name}"
            if tool_path in self._macros:
                return self._macros[tool_path]

            # Рекурсивный поиск во вложенных папках tools/<tool>/
            tool_dir = self._tools_path / tool
            if tool_dir.exists():
                for item in tool_dir.rglob(f"*.sql.j2"):
                    rel_path = item.relative_to(tool_dir)
                    parts = list(rel_path.parts)
                    parts[-1] = parts[-1].replace(".sql.j2", "")
                    found_name = "/".join(parts)
                    if found_name == name or found_name.endswith(f"/{name}"):
                        full_name = f"{tool}/{found_name}"
                        if full_name in self._macros:
                            return self._macros[full_name]

        # 2. Workflow engine поиск (templates/)
        if tool and tool in self._workflow_engines:
            templates_dir = self._tools_path / "workflow" / tool / "templates"
            if templates_dir.exists():
                for item in templates_dir.rglob(f"*.sql.j2"):
                    rel_path = item.relative_to(templates_dir)
                    parts = list(rel_path.parts)
                    parts[-1] = parts[-1].replace(".sql.j2", "")
                    found_name = "/".join(parts)
                    if found_name == name or found_name.endswith(f"/{name}"):
                        full_name = f"workflow/{tool}/templates/{found_name}"
                        if full_name in self._macros:
                            return self._macros[full_name]

        # 3. Поиск в main/
        main_path = f"main/{name}"
        if main_path in self._macros:
            return self._macros[main_path]

        # 4. Рекурсивный поиск в main/
        main_dir = self._tools_path / "main"
        if main_dir.exists():
            for item in main_dir.rglob("*.sql.j2"):
                rel_path = item.relative_to(main_dir)
                parts = list(rel_path.parts)
                parts[-1] = parts[-1].replace(".sql.j2", "")
                found_name = "/".join(parts)
                if found_name == name or found_name.endswith(f"/{name}"):
                    full_name = f"main/{found_name}"
                    if full_name in self._macros:
                        return self._macros[full_name]

        # 5. Error
        raise MacroNotFoundError(
            f"Macro '{name}' not found for tool '{tool}'. "
            f"Available: {list(self._macros.keys())}"
        )

    def get_macro_content(self, name: str, tool: Optional[str] = None) -> str:
        """Получить содержимое макроса (shortcut)."""
        return self.get_macro(name, tool).content

    def list_macros(self, tool: Optional[str] = None) -> List[str]:
        """Список доступных макросов."""
        if tool:
            prefix = f"{tool}/"
            return [k for k in self._macros.keys() if k.startswith(prefix)]
        return list(self._macros.keys())

    def list_tools(self) -> List[str]:
        """Список доступных tools."""
        return self._tools.copy()

    def has_macro(self, name: str, tool: Optional[str] = None) -> bool:
        """Проверить существование макроса."""
        direct_key = f"{tool}/{name}" if tool else name
        if direct_key in self._macros:
            return True

        try:
            self.get_macro(name, tool)
            return True
        except MacroNotFoundError:
            return False

    def get_available_tools_for_macro(self, name: str) -> List[str]:
        """Получить список tools, для которых есть макрос."""
        available = []

        # Check main
        if self.has_macro(name, None):
            available.append("main")

        # Check each tool
        for tool in self._tools:
            if self.has_macro(name, tool):
                available.append(tool)

        return available

    def has_python_macro(self, name: str, tool: Optional[str] = None) -> bool:
        """Проверить существование Python-макроса.

        Логика поиска:
        1. <tool>/<name>
        2. main/<name>

        Args:
            name: Имя макроса (напр. materialization/insert_fc)
            tool: Tool (oracle/adb/postgresql)

        Returns:
            True если макрос найден
        """
        if tool:
            key = f"{tool}/{name}"
            if key in self._python_macros:
                return True

        main_key = f"main/{name}"
        return main_key in self._python_macros

    def has_model_ref_macro(self, name: str, tool: Optional[str] = None) -> bool:
        """Проверить существование model_ref макроса.

        Логика поиска:
        1. <tool>/model_ref/<name>
        2. main/model_ref/<name>

        Args:
            name: Имя макроса (напр. table)
            tool: Tool (oracle/adb/postgresql)

        Returns:
            True если макрос найден
        """
        return self.has_python_macro(f"model_ref/{name}", tool)

    def get_model_ref_macro(self, name: str, tool: Optional[str] = None) -> Callable:
        """Получить model_ref макрос.

        Логика поиска:
        1. <tool>/model_ref/<name>
        2. main/model_ref/<name>

        Args:
            name: Имя макроса (напр. table)
            tool: Tool (oracle/adb/postgresql)

        Returns:
            Callable - функция макроса

        Raises:
            PythonMacroNotFoundError: Если макрос не найден
        """
        return self.get_python_macro(f"model_ref/{name}", tool)

    def has_parameter_macro(self, name: str, tool: Optional[str] = None) -> bool:
        """Проверить существование parameter макроса.

        Логика поиска:
        1. <tool>/parameter/<name>
        2. main/parameter/<name>

        Args:
            name: Имя макроса (напр. param)
            tool: Tool (oracle/adb/postgresql)

        Returns:
            True если макрос найден
        """
        return self.has_python_macro(f"parameter/{name}", tool)

    def get_parameter_macro(self, name: str, tool: Optional[str] = None) -> Callable:
        """Получить parameter макрос.

        Логика поиска:
        1. <tool>/parameter/<name>
        2. main/parameter/<name>

        Args:
            name: Имя макроса (напр. param)
            tool: Tool (oracle/adb/postgresql)

        Returns:
            Callable - функция макроса

        Raises:
            PythonMacroNotFoundError: Если макрос не найден
        """
        return self.get_python_macro(f"parameter/{name}", tool)

    def has_materialization_macro(self, name: str, tool: Optional[str] = None) -> bool:
        """Проверить существование materialization макроса.

        Логика поиска:
        1. <tool>/materialization/<name>
        2. main/materialization/<name>

        Args:
            name: Имя макроса (напр. insert_fc, upsert_fc, stage_calcid)
            tool: Tool (oracle/adb/postgresql)

        Returns:
            True если макрос найден
        """
        return self.has_python_macro(f"materialization/{name}", tool)

    def get_materialization_macro(
        self, name: str, tool: Optional[str] = None
    ) -> Callable:
        """Получить materialization макрос.

        Логика поиска:
        1. <tool>/materialization/<name>
        2. main/materialization/<name>

        Args:
            name: Имя макроса (напр. insert_fc, upsert_fc, stage_calcid)
            tool: Tool (oracle/adb/postgresql)

        Returns:
            Callable - функция макроса

        Raises:
            PythonMacroNotFoundError: Если макрос не найден
        """
        return self.get_python_macro(f"materialization/{name}", tool)

    def has_function_macro(self, name: str, tool: Optional[str] = None) -> bool:
        """Проверить существование function макроса.

        Использует FunctionRegistry для поиска функций.

        Args:
            name: Имя функции (напр. to_char, coalesce)
            tool: Tool (oracle/adb/postgresql)

        Returns:
            True если макрос найден
        """
        from FW.macros import get_function_registry

        func_registry = get_function_registry(tools=self._tools)

        if tool and tool in self._tools:
            tool_funcs = func_registry.get_tool_functions(tool)
            if name in tool_funcs:
                return True

        base_funcs = func_registry.get_base_functions()
        return name in base_funcs

    def get_function_macro(self, name: str, tool: Optional[str] = None) -> Callable:
        """Получить function макрос.

        Использует FunctionRegistry для поиска функций.
        Приоритет: tool-specific -> base

        Args:
            name: Имя функции (напр. to_char, coalesce)
            tool: Tool (oracle/adb/postgresql)

        Returns:
            Callable - функция макроса

        Raises:
            PythonMacroNotFoundError: Если макрос не найден
        """
        from FW.macros import get_function_registry

        func_registry = get_function_registry(tools=self._tools)

        if tool and tool in self._tools:
            tool_funcs = func_registry.get_tool_functions(tool)
            if name in tool_funcs:
                return tool_funcs[name]

        base_funcs = func_registry.get_base_functions()
        if name in base_funcs:
            return base_funcs[name]

        raise PythonMacroNotFoundError(
            f"Function macro '{name}' not found for tool '{tool}'. "
            f"Available base functions: {list(base_funcs.keys())}"
        )

    def get_python_macro(self, name: str, tool: Optional[str] = None) -> Callable:
        """Получить Python-макрос.

        Логика поиска:
        1. <tool>/<name> (tool-specific)
        2. main/<name> (fallback)

        Args:
            name: Имя макроса
            tool: Tool (oracle/adb/postgresql)

        Returns:
            Callable - функция макроса

        Raises:
            PythonMacroNotFoundError: Если макрос не найден
        """
        # 1. Tool-specific
        if tool:
            key = f"{tool}/{name}"
            if key in self._python_macros:
                return self._python_macros[key]

        # 2. Main fallback
        main_key = f"main/{name}"
        if main_key in self._python_macros:
            return self._python_macros[main_key]

        raise PythonMacroNotFoundError(
            f"Python macro '{name}' not found for tool '{tool}'. "
            f"Available: {list(self._python_macros.keys())}"
        )

    def has_workflow_template(self, workflow_engine: str, template_name: str) -> bool:
        """Проверить существование workflow template.

        Args:
            workflow_engine: имя workflow engine (dqcr, airflow, etc)
            template_name: имя шаблона (default, basic, etc)

        Returns:
            True если шаблон найден
        """
        key = f"{workflow_engine}/{template_name}"
        return key in self._workflow_templates

    def get_workflow_template(
        self, workflow_engine: str, template_name: str
    ) -> Callable:
        """Получить workflow template.

        Args:
            workflow_engine: имя workflow engine (dqcr, airflow, etc)
            template_name: имя шаблона (default, basic, etc)

        Returns:
            Callable - функция шаблона

        Raises:
            PythonMacroNotFoundError: Если шаблон не найден
        """
        key = f"{workflow_engine}/{template_name}"
        if key in self._workflow_templates:
            return self._workflow_templates[key]

        raise PythonMacroNotFoundError(
            f"Workflow template '{template_name}' not found for engine '{workflow_engine}'. "
            f"Available: {list(self._workflow_templates.keys())}"
        )


# Глобальный экземпляр
_default_registry: Optional[MacroRegistry] = None


def get_macro_registry(
    macros_path: Optional[Path] = None, custom_macros_path: Optional[Path] = None
) -> MacroRegistry:
    """Получить глобальный экземпляр MacroRegistry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = MacroRegistry(macros_path, custom_macros_path)
    return _default_registry


# =============================================================================
# FunctionRegistry - загружается из macros/<tool>/functions/
# =============================================================================


class FunctionRegistry:
    """Реестр функций для Jinja2.

    Функции загружаются из macros/<tool>/functions/*.py
    Поддерживается:
    - Базовые функции (main/functions/)
    - Tool-specific функции (oracle/functions/, postgresql/functions/)
    - Prehook функции (с декоратором @prehook)
    """

    def __init__(
        self, tools: Optional[List[str]] = None, macros_path: Optional[Path] = None
    ):
        self._tools = tools or ["oracle", "adb", "postgresql"]
        self._macros_path = macros_path or self._get_default_macros_path()

        self._base_functions: Dict[str, Callable] = {}
        self._tool_functions: Dict[str, Dict[str, Callable]] = {}
        self._prehook_functions: Dict[str, PreHookFunction] = {}

        self._register_all_functions()

    def _get_default_macros_path(self) -> Path:
        fw_dir = Path(__file__).parent.parent
        return fw_dir / "macros"

    def _load_functions_from_file(
        self, file_path: Path, tool: Optional[str] = None
    ) -> Dict[str, Callable]:
        """Загрузить функции из Python файла."""
        functions = {}

        if not file_path.exists():
            return functions

        try:
            spec = importlib.util.spec_from_file_location(
                f"func_{file_path.stem}", file_path
            )
            if spec is None or spec.loader is None:
                return functions

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for name in dir(module):
                if name.startswith("_"):
                    continue

                attr = getattr(module, name)

                if isinstance(attr, PreHookFunction):
                    self._prehook_functions[attr.name] = attr
                    functions[attr.name] = attr.func
                elif callable(attr):
                    functions[name] = attr

        except Exception as e:
            logger.warning(f"Error loading functions from {file_path}: {e}")

        return functions

    def _register_all_functions(self):
        """Загрузить все функции из всех директорий."""
        funcs_dir = self._macros_path / "main" / "functions"
        if funcs_dir.exists():
            for py_file in funcs_dir.glob("*.py"):
                if py_file.stem == "__init__":
                    continue
                self._base_functions.update(
                    self._load_functions_from_file(py_file, tool=None)
                )

        for tool in self._tools:
            tool_funcs_dir = self._macros_path / tool / "functions"
            if tool_funcs_dir.exists():
                self._tool_functions[tool] = {}
                for py_file in tool_funcs_dir.glob("*.py"):
                    if py_file.stem == "__init__":
                        continue
                    self._tool_functions[tool].update(
                        self._load_functions_from_file(py_file, tool=tool)
                    )

        self._base_functions.update(
            {
                "upper": str.upper,
                "lower": str.lower,
                "trim": str.strip,
                "replace": lambda s, old, new: s.replace(old, new),
                "substring": lambda s, start, end: s[start:end],
                "length": len,
                "now": lambda: datetime.now(),
                "today": lambda: date.today(),
                "date_add": lambda d, days: d,
                "date_sub": lambda d, days: d,
                "to_string": str,
                "to_int": int,
                "to_float": float,
                "to_bool": lambda x: bool(x),
                # coalesce intentionally removed - use from base.py instead
                "ifnull": lambda val, default: val if val is not None else default,
                "iff": lambda cond, true_val, false_val: (
                    true_val if cond else false_val
                ),
                "escape_sql": lambda s: "NULL" if s is None else s.replace("'", "''"),
                "quote": lambda s: f"'{s}'" if s else "NULL",
                "join": lambda seq, delim: delim.join(seq),
                "split": lambda s, delim: s.split(delim),
                "uniq": lambda seq: list(dict.fromkeys(seq)),
                "print": lambda x: x,
            }
        )

        logger.debug(
            f"Loaded {len(self._base_functions)} base functions, "
            f"{sum(len(f) for f in self._tool_functions.values())} tool functions, "
            f"{len(self._prehook_functions)} prehook functions"
        )

    def get_all_functions(self, tool: Optional[str] = None) -> Dict[str, Callable]:
        """Получить все функции для указанного tool.

        Порядок приоритета: tool-specific -> base
        """
        result = self._base_functions.copy()
        if tool and tool in self._tool_functions:
            result.update(self._tool_functions[tool])
        return result

    def get_base_functions(self) -> Dict[str, Callable]:
        """Получить базовые функции."""
        return self._base_functions.copy()

    def get_tool_functions(self, tool: str) -> Dict[str, Callable]:
        """Получить функции для конкретного tool."""
        return self._tool_functions.get(tool, {}).copy()

    def get_prehook_functions(self) -> Dict[str, PreHookFunction]:
        """Получить все prehook функции."""
        return self._prehook_functions.copy()

    def is_prehook_function(self, name: str) -> bool:
        """Проверить является ли функция prehook."""
        return name in self._prehook_functions

    def get_prehook(self, name: str) -> Optional[PreHookFunction]:
        """Получить prehook функцию по имени."""
        return self._prehook_functions.get(name)


_default_function_registry: Optional[FunctionRegistry] = None


def get_function_registry(
    tools: Optional[List[str]] = None, macros_path: Optional[Path] = None
) -> FunctionRegistry:
    global _default_function_registry
    if _default_function_registry is None:
        _default_function_registry = FunctionRegistry(tools, macros_path)
    return _default_function_registry
