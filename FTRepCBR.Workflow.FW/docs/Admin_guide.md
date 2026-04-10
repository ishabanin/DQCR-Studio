# DQCR Framework — Руководство администратора

**Версия документа:** 1.0  
**Дата:** Март 2026

---

## Содержание

1. [Введение](#1-введение)
2. [Установка и требования](#2-установка-и-требования)
3. [Архитектура фреймворка](#3-архитектура-фреймворка)
4. [Создание шаблона проекта](#4-создание-шаблона-проекта)
5. [Система валидации](#5-система-валидации)
6. [Система макросов](#6-система-макросов)
7. [Материализация](#7-материализация)
8. [Генераторы workflow](#9-генераторы-workflow)
9. [Расширение функциональности](#10-расширение-функциональности)
10. [Конфигурация и реестры](#11-конфигурация-и-реестры)
11. [Устранение неполадок](#12-устранение-неполадок)

---

## 1. Введение

### 1.1 Назначение документа

Данное руководство предназначено для **администраторов** DQCR Framework — Python-проекта для генерации SQL-процессов из структурированных SQL-файлов. Специалисты, которые управляют фреймворком, создают шаблоны проектов, настраивают правила валидации и разрабатывают макросы.

### 1.2 Что входит в обязанности администратора

- Установка и настройка фреймворка
- Создание и поддержка шаблонов проектов
- Настройка правил валидации
- Разработка и поддержка макросов
- Интеграция с целевыми системами
- Устранение неполадок

---

## 2. Установка и требования

### 2.1 Требования к системе

**Аппаратные требования:**

- Процессор: 2+ ядра
- Оперативная память: 4+ ГБ
- Диск: 10+ ГБ свободного места

**Программные требования:**

- Python 3.10+
- Git (для управления версиями)

### 2.2 Установка фреймворка

**Клонирование репозитория:**

```bash
git clone https://github.com/your-org/dqcr-framework.git
cd dqcr-framework
```

**Установка зависимостей:**

```bash
pip install -r requirements.txt
```

**Проверка установки:**

```bash
python -m FW.cli --version
```

### 2.3 Структура директорий фреймворка

```
FW/
├── cli.py                      # Точка входа CLI
├── __init__.py                 # Инициализация пакета
├── logging_config.py          # Настройка логирования
├── pattern_matcher.py        # Сопоставление шаблонов
│
├── config/                     # Конфигурация
│   ├── __init__.py            # Реестры (Tool, Engine, Template)
│   ├── tools.yml              # Инструменты (adb, oracle, postgresql)
│   ├── workflow_engines.yml   # Движки оркестрации
│   └── templates/             # Шаблоны проектов
│       ├── flx.yml
│       ├── dwh_mart.yml
│       └── dq_control.yml
│
├── exceptions/                 # Исключения
│   ├── base.py                # BaseFWError
│   ├── config.py              # ConfigValidationError
│   ├── template.py            # TemplateNotFoundError
│   └── model.py               # Ошибки моделей
│
├── generation/                 # Генерация workflow
│   ├── base.py                # Абстрактный билдер
│   ├── DefaultBuilder.py      # Основной билдер
│   ├── dependency_resolver.py # Разрешение зависимостей
│   ├── naming_convention.py   # По соглашению об именах
│   ├── graph_based.py         # Графовое разрешение
│   └── explicit.py            # Явное разрешение
│
├── macros/                     # Макросы
│   ├── __init__.py           # MacroRegistry
│   ├── env.py                # MacroEnv, WorkflowMacroEnv
│   ├── main/                 # Базовые макросы
│   │   ├── materialization/  # insert_fc, upsert_fc, stage_calcid
│   │   ├── functions/        # Функции преобразования
│   │   └── model_ref/       # Ссылки на модели
│   ├── oracle/               # Oracle-специфичные
│   ├── adb/                  # ADB-специфичные
│   ├── postgresql/           # PostgreSQL-специфичные
│   └── workflow/             # Генераторы workflow
│       ├── airflow/
│       ├── dbt/
│       ├── oracle_plsql/
│       └── dqcr/
│
├── materialization/           # Рендеринг материализации
│   └── renderer.py           # MaterializationRenderer
│
├── models/                    # Модели данных
│   ├── workflow.py           # WorkflowModel
│   ├── step.py               # WorkflowStepModel
│   ├── sql_query.py          # SQLQueryModel
│   ├── parameter.py         # ParameterModel
│   ├── target_table.py      # TargetTableModel
│   └── attribute.py         # Attribute
│
├── parsing/                   # Парсинг
│   ├── project_loader.py     # Загрузка проекта
│   ├── template_loader.py    # Загрузка шаблона
│   ├── model_config_loader.py # Загрузка model.yml
│   ├── context_loader.py    # Загрузка контекстов
│   ├── parameter_loader.py  # Загрузка параметров
│   ├── sql_metadata.py      # Парсинг SQL
│   └── inline_config_parser.py # @config() парсер
│
└── validation/                # Валидация
    ├── models.py             # ValidationIssue, Report
    ├── rule_runner.py        # Запуск правил
    ├── template_validator.py # Валидация по шаблону
    ├── html_generator.py     # Генерация HTML
    └── rules/
        ├── base.py           # BaseValidationRule
        ├── general/          # Общие правила
        ├── sql/              # SQL-правила
        ├── adb/              # ADB-правила
        └── descriptions/      # Правила описаний
```

### 2.4 Настройка переменных окружения

```bash
# Linux/macOS
export DQCR_HOME=/path/to/FW
export DQCR_LOG_LEVEL=INFO

# Windows
set DQCR_HOME=C:\path\to\FW
set DQCR_LOG_LEVEL=INFO
```

---

## 3. Архитектура фреймворка

### 3.1 Общая схема

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│   CLI       │────▶│   Builder    │────▶│   Workflow    │
│  (cli.py)   │     │ (generation) │     │    Model      │
└─────────────┘     └──────────────┘     └───────────────┘
                           │                      │
                           ▼                      ▼
                    ┌──────────────┐     ┌───────────────┐
                    │   Macros     │     │   Validation │
                    │ (materialize)│     │    Rules     │
                    └──────────────┘     └───────────────┘
                           │
                           ▼
                    ┌──────────────┐     ┌───────────────┐
                    │  Renderer     │────▶│   Target      │
                    │(materialization)    │  (SQL/JSON)   │
                    └──────────────┘     └───────────────┘
```

### 3.2 Поток обработки

1. **Загрузка** — парсинг project.yml, model.yml, contexts, parameters, SQL
2. **Построение** — создание WorkflowModel (DependencyResolver)
3. **Макросы** — применение материализации к SQL-запросам
4. **Рендеринг** — генерация SQL для каждого инструмента
5. **Валидация — проверка по правилам**
6. **Генерация** — создание workflow-файлов

### 3.3 Ключевые компоненты

| Компонент | Ответственность |
|-----------|----------------|
| CLI | Интерфейс командной строки |
| Builder | Построение workflow-модели |
| DependencyResolver | Определение зависимостей между шагами |
| MacroRegistry | Управление макросами |
| MaterializationRenderer | Рендеринг SQL с материализацией |
| RuleRunner | Выполнение правил валидации |

---

## 4. Создание шаблона проекта

### 4.1 Что такое шаблон

Шаблон (template) — это конфигурация, определяющая структуру и правила проекта. Шаблоны хранятся в `FW/config/templates/`.

### 4.2 Структура шаблона

```yaml
# FW/config/templates/my_template.yml
name: my_template
description: "Описание шаблона"

models:
  - name: marts
    paths:
      models_root: model
      project_config: project.yml
      model_config: model.yml
      contexts: contexts
      global_params: parameters
      local_params: parameters
      sql: SQL
      target: target/resources/forms/

    config:
      builder: default
      dependency_resolver: naming_convention
      workflow_engine: dqcr
      default_materialization: insert_fc
      model_ref_macro: table

    validation_categories:
      - general
      - sql
      - descriptions
      - adb

    rules:
      folders:
        root:
          pre: []
          post: []
        "*_Load*":
          required: false
          materialization: insert_fc
        "*_Update*":
          required: false
          materialization: upsert_fc

      queries:
        "*_quality_*":
          required: true

      parameters:
        "date_*":
          required: true
          domain_type: date
```

### 4.3 Поля шаблона

| Поле | Тип | Описание |
|------|-----|----------|
| `name` | string | Уникальное имя шаблона |
| `description` | string | Описание |
| `models[].name` | string | Имя модели |
| `models[].paths.*` | string | Пути к директориям |
| `models[].config.*` | string | Настройки генерации |
| `models[].validation_categories` | list | Категории валидации |
| `models[].rules.*` | dict | Правила для папок, запросов, параметров |

### 4.4 Конфигурация модели

**config:**

```yaml
config:
  builder: default                    # Билдер (default, custom)
  dependency_resolver: naming_convention  # Метод разрешения зависимостей
  workflow_engine: dqcr                # Движок по умолчанию
  default_materialization: insert_fc   # Материализация по умолчанию
  model_ref_macro: table               # Макрос для ссылок на модели
```

### 4.5 Контексты проекта

Контексты позволяют определять различные конфигурации для разных окружений или клиентов. Файлы контекстов находятся в директории `contexts/` проекта.

#### 4.5.1 Структура контекста

```yaml
# contexts/vtb.yml
project: vtb                           # Имя проекта/клиента
tools:                                 # Список tools для этого контекста
  - adb

constants:                            # Константы контекста
  schema: VTB_SCHEMA
  batch_size: 10000

flags:                                # Флаги контекста
  enable_heavy_calc: false
  debug_mode: true
  overduecalcmethod:                  # Вложенные флаги
    fifo: false
    lifo: true
```

#### 4.5.2 Доступ к flags и constants

**В Python-макросах:**

```python
# В materialization-макросе
if env.flags.get('debug_mode'):
    # добавить отладочную информацию
    pass

# Поддержка вложенных флагов через точку
if env.get_flag('overduecalcmethod.fifo'):
    # для FIFO
    pass

# Получение константы
schema = env.get_constant('schema')
```

**В Jinja2-шаблонах:**

```sql
{% if ctx.flags.debug_mode %}
-- отладочный код
{% endif %}

SELECT * FROM {{ ctx.constants.schema }}.orders
```

#### 4.5.3 Условное включение шагов (enabled.conditions)

Флаги и константы используются для условного включения папок и запросов:

```yaml
# model.yml
workflow:
  folders:
    HeavyCalc:
      enabled:
        conditions:
          enable_heavy_calc: true           # флаг = значение
    
    FastPath:
      enabled:
        conditions:
          enable_heavy_calc: false          # флаг = false исключает

  queries:
    MyQuery:
      enabled:
        contexts: [default, vtb]            # в каких контекстах включено
        conditions:                         # AND - все условия должны выполниться
          enable_feature_x: true
          any:                              # OR - хотя бы одно условие
            enable_feature_a: true
            enable_feature_b: true
```

**Доступные проверки:**
- `flag_name: value` — флаг равен значению
- `flag.nested: value` — вложенный флаг
- `const_name: value` — константа равна значению
- `any: {key: value, ...}` — хотя бы одно условие выполнено (OR)
- `contexts: [ctx1, ctx2]` — в каких контекстах включено

### 4.6 Правила (rules)

**Для папок:**

```yaml
rules:
  folders:
    "root":                            # Корневая папка
      pre: [synch_iter]                # Пре-хуки
      post: []                         # Пост-хуки
    "*_iter*":                         # Любая папка с _iter
      pre: [synch_iter]
    "*_Load*":                         # Любая папка с _Load
      required: false                  # Не обязательна
      materialization: insert_fc       # Материализация по умолчанию
    "*_Update*":
      required: false
      materialization: upsert_fc
```

**Для запросов:**

```yaml
rules:
  queries:
    "*_quality_*":                     # Запросы с _quality_
      required: true                   # Обязательны
    "*_check_*":
      enabled: false                   # Отключены по умолчанию
```

**Для параметров:**

```yaml
rules:
  parameters:
    "date_*":                          # Параметры даты
      required: true
      domain_type: date
    "*_id":
      domain_type: number
```

### 4.7 Создание нового шаблона

1. Создать файл `FW/config/templates/my_template.yml`
2. Определить структуру paths
3. Настроить config
4. Добавить validation_categories
5. Определить rules
6. Зарегистрировать шаблон (автоматически при запуске)

---

## 5. Система валидации

### 5.1 Архитектура валидации

```
┌─────────────┐
│  Workflow  │
│   Model    │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│ Template    │────▶│  Issues     │
│ Validator   │     │  (Report)   │
└─────────────┘     └─────────────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│ RuleRunner  │────▶│  Issues     │
│ (by category)    │  (Report)    │
└─────────────┘     └─────────────┘
```

### 5.2 Модели валидации

**ValidationIssue:**

```python
from FW.validation.models import ValidationIssue, ValidationLevel

issue = ValidationIssue(
    level=ValidationLevel.ERROR,      # INFO, WARNING, ERROR
    rule="sql:001_NoDelete",          # Идентификатор правила
    category="sql",                   # Категория
    message="Запрос содержит DELETE",
    location="001_Load/001_Query.sql:15",  # Место
    details={"query": "DELETE FROM..."}
)
```

**ValidationReport:**

```python
from FW.validation.models import ValidationReport

report = ValidationReport(
    project_name="MyProject",
    model_name="MyModel",
    template_name="flx",
    validation_categories=["general", "sql"],
    timestamp="2024-03-15T10:30:00",
    issues=[issue1, issue2, ...]
)

# Свойства
print(report.total_issues)  # Общее количество
print(report.error_count)   # Ошибки
print(report.warning_count)  # Предупреждения
print(report.info_count)     # Информационные
```

### 5.3 Базовый класс правила

```python
from FW.validation.rules.base import BaseValidationRule
from FW.validation.models import ValidationIssue, ValidationLevel
from FW.models.workflow import WorkflowModel
from typing import List

class MyCustomRule(BaseValidationRule):
    """Мое кастомное правило"""
    
    name = "custom:001_MyRule"           # Уникальный идентификатор
    category = "general"                # Категория (general, sql, adb, descriptions)
    level = ValidationLevel.WARNING     # Уровень по умолчанию
    description = "Проверяет что-то важное"
    
    def validate(self, workflow: WorkflowModel) -> List[ValidationIssue]:
        issues = []
        
        # Логика проверки
        if not workflow.target_table:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                rule=self.name,
                category=self.category,
                message="Target table не определена",
                location=workflow.model_name
            ))
        
        return issues
```

### 5.4 Категории правил

| Категория | Описание | Примеры |
|-----------|----------|---------|
| `general` | Общие проверки | target_table, steps, tools |
| `sql` | SQL-код | hints, DELETE, SELECT * |
| `adb` | ADB-специфичные | distribution_key, primary_key |
| `descriptions` | Описания | workflow description, folder description |

### 5.5 Реестр правил

```python
from FW.validation.rules.base import ValidationRuleRegistry

# Получение всех правил категории
registry = ValidationRuleRegistry()
rules = registry.get_by_category("sql")

# Получение конкретного правила
rule = registry.get("sql:001_NoDeleteStatement")
```

### 5.6 Создание нового правила

1. Создать файл в соответствующей категории:
   - `FW/validation/rules/general/my_rule.py`
   - `FW/validation/rules/sql/my_rule.py`

2. Определить класс правила:

```python
from FW.validation.rules.base import BaseValidationRule
from FW.validation.models import ValidationIssue, ValidationLevel

class NoTruncateRule(BaseValidationRule):
    """Запрет использования TRUNCATE"""
    
    name = "sql:003_NoTruncate"
    category = "sql"
    level = ValidationLevel.ERROR
    description = "Запрос не должен содержать TRUNCATE"
    
    def validate(self, workflow):
        issues = []
        
        for step in workflow.steps:
            if step.sql_model and step.sql_model.source_sql:
                sql = step.sql_model.source_sql.upper()
                if 'TRUNCATE' in sql:
                    issues.append(ValidationIssue(
                        level=self.level,
                        rule=self.name,
                        category=self.category,
                        message=f"Запрос {step.full_name} содержит TRUNCATE",
                        location=f"{step.folder}/{step.name}.sql"
                    ))
        
        return issues
```

3. Зарегистрировать правило в `__init__.py`:

```python
# FW/validation/rules/sql/__init__.py
from FW.validation.rules.sql.no_truncate_rule import NoTruncateRule

__all__ = [
    # ... существующие правила
    NoTruncateRule,
]
```

### 5.7 Запуск валидации программно

```python
from FW.validation.rule_runner import RuleRunner

runner = RuleRunner(categories=["general", "sql"])
issues = runner.run(workflow)

# С категорией по умолчанию из шаблона
runner = RuleRunner()  # Загрузит все категории шаблона
issues = runner.run(workflow)
```

---

## 6. Система макросов

### 6.1 Архитектура макросов

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Macro     │────▶│   MacroEnv   │────▶│   Jinja2    │
│   Registry  │     │              │     │   Template  │
└─────────────┘     └──────────────┘     └─────────────┘
       │                    │
       │                    ▼
       │            ┌──────────────┐
       │            │   Python     │
       └───────────▶│   Macro      │
                    └──────────────┘
```

### 6.2 Типы макросов

| Тип | Расположение | Назначение |
|-----|--------------|------------|
| Jinja2-шаблон | `macros/**/*.sql.j2` | Генерация SQL |
| Python-функция | `macros/**/*.py` | Логика обработки |

### 6.3 MacroRegistry

```python
from FW.macros import MacroRegistry

registry = MacroRegistry()

# Получить Jinja2-шаблон
template = registry.get_macro("materialization/insert_fc_body", "oracle")

# Проверить наличие
has_macro = registry.has_python_macro("materialization_insert_fc", "oracle")

# Получить Python-макрос
macro_func = registry.get_python_macro("materialization_insert_fc", "oracle")
```

### 6.4 MacroEnv

Контекст выполнения макросов:

```python
from FW.macros.env import MacroEnv

# Доступные атрибуты
env.workflow           # WorkflowModel
env.step               # WorkflowStepModel
env.tools              # List[str]
env.param_model        # ParameterModel
env.steps              # List[WorkflowStepModel]

# Методы
rendered = env.render_template("template_name", tool="adb", **kwargs)
env.add_step(step)                                   # Добавить шаг
found_step = env.get_step_by_name("folder/query")   # Найти шаг
folder_steps = env.get_steps_in_folder("001_Load")  # Шаги папки
```

### 6.5 Создание Python-макроса

**Пример: materialization_insert_fc**

```python
# FW/macros/main/materialization/insert_fc.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from FW.models.step import WorkflowStepModel
    from FW.models.workflow import WorkflowModel
    from FW.macros.env import MacroEnv


def materialization_insert_fc(
    step: "WorkflowStepModel",
    workflow: "WorkflowModel",
    env: "MacroEnv"
):
    """
    Применяет материализацию INSERT (full column list).
    
    Генерирует:
    INSERT INTO target_table (col1, col2, ...)
    SELECT col1, col2, ...
    FROM (prepared_sql) t
    """
    wf = env.workflow or workflow
    target_table = wf.target_table if wf and wf.target_table else None
    
    if not target_table:
        raise ValueError(f"Target table not found for step {step.full_name}")
    
    for tool in env.tools:
        prepared = step.sql_model.get_prepared_sql(tool)
        
        if not prepared:
            continue
        
        # Получение колонок
        key_attrs = target_table.get_key_attributes_for_insert(step.sql_model)
        required_attrs = target_table.get_required_attributes_not_in_query(step.sql_model)
        query_attrs = list(step.sql_model.get_attribute_names())
        
        target_columns = key_attrs + required_attrs + query_attrs
        target_columns = list(dict.fromkeys(target_columns))  # Уникальные
        
        rendered = env.render_template(
            "materialization/insert_fc_body",
            tool=tool,
            target_table=target_table.name,
            schema=target_table.schema,
            target_columns=target_columns,
            sql=prepared
        )
        
        step.sql_model.rendered_sql[tool] = rendered
```

### 6.6 Jinja2-шаблон материализации

```jinja
{# macros/main/materialization/insert_fc_body.sql.j2 #}
INSERT INTO {{ schema }}.{{ target_table }} (
{% for col in target_columns %}
    {{ col }}{% if not loop.last %},{% endif %}
{% endfor %}
)
SELECT
{% for col in target_columns %}
    {{ col }}{% if not loop.last %},{% endif %}
{% endfor %}
FROM (
{{ sql }}
) [t]
```

### 6.7 Поиск шаблонов

Порядок поиска шаблонов:

1. `<tool>/<category>/<name>` (например, `oracle/materialization/insert_fc_body`)
2. `<tool>/**/<name>` (рекурсивно в папке tool)
3. `main/<category>/<name>` (fallback)

### 6.8 WorkflowMacroEnv

Для генераторов workflow:

```python
from FW.macros.env import WorkflowMacroEnv

env = WorkflowMacroEnv(
    workflow_name="MyModel",
    target_path=Path("target/dqcr/MyModel"),
    tools=["adb", "oracle"]
)

# Методы
env.create_file("dag.py", "# DAG content")
env.create_directory("steps")
rendered = env.render_template("workflow/dqcr/dag", workflow_name="MyModel")
steps = env.get_all_steps()
```

---

## 7. Материализация

### 7.1 Типы материализации

| Тип | Описание | SQL |
|-----|----------|-----|
| `insert_fc` | INSERT всех колонок | INSERT INTO ... SELECT |
| `upsert_fc` | INSERT с обновлением | INSERT ... ON CONFLICT UPDATE |
| `stage_calcid` | Stage с ID расчета | CREATE TABLE ... WITH (version) |
| `ephemeral` | CTE (временный) | WITH ... AS |
| `param` | Параметр | SELECT value FROM dual |

### 7.2 Логика insert_fc

```
target_columns = key_attrs + required_attrs + query_attrs
select_columns = query_attrs + required_attrs (с default_value)

INSERT INTO target_table (target_columns)
SELECT select_columns
FROM (prepared_sql) t
```

### 7.3 Логика upsert_fc

```
key_columns = атрибуты с is_key: true
update_columns = все атрибуты кроме key

INSERT INTO table (key + update)
SELECT key + update
FROM (prepared_sql)
ON CONFLICT (key) DO UPDATE SET
  col1 = EXCLUDED.col1, ...
```

### 7.4 MaterializationRenderer

```python
from FW.materialization.renderer import MaterializationRenderer

renderer = MaterializationRenderer()

# Подготовка SQL (замена функций, параметров)
prepared = renderer.prepare_sql(
    sql_model=sql_model,
    tool="adb",
    param_values={"date_end": "2024-01-01"},
    workflow=workflow,
    context_name="default"
)

# Применение материализации
rendered = renderer.apply_materialization(
    sql_model=sql_model,
    prepared_sql=prepared,
    tool="adb",
    workflow=workflow,
    step=step
)

# Полный рендеринг
rendered = renderer.render_sql_query(
    sql_model=sql_model,
    tool="adb",
    param_values={"date_end": "2024-01-01"},
    workflow=workflow,
    step=step
)
```

### 7.5 Обработка параметров

Параметры обрабатываются аналогично SQL-запросам:

1. **Парсинг SQL** — при создании шага параметра SQL парсится для извлечения метаданных (функции, _m.* ссылки)
2. **prepare_sql** — замена функций, _m.* ссылок
3. **rendered_sql** — применение материализации

#### 7.5.1 Параметры с _m.* ссылками

Динамические параметры могут содержать ссылки на модели (`_m.*`). При обработке:

```python
# Пример параметра
parameter:
  name: settings_table
  domain_type: record
  values:
    all:
      type: dynamic
      value: "select strnum, account2 from _m.rf110.rf110_settings"
```

**Этапы обработки:**

1. **Этап 1: Создание шага** (`_build_param_steps`)
   - SQL парсится через `SQLMetadataParser.parse()`
   - Заполняется `param_model.metadata.model_refs`

2. **Этап 2: Разрешение ссылок** (`_resolve_workflow_refs`)
   - `prepare_param()` заменяет функции и _m.* ссылки
   - При обнаружении _m.* вызывается макрос `model_ref_macro` с env
   - Макрос создаёт шаг `get_entities` и возвращает `{{ table_module_entity }}`

3. **Этап 3: Материализация**
   - `_apply_param_materialization()` создаёт rendered_sql

#### 7.5.2 MaterializationRenderer для параметров

```python
# Подготовка SQL параметра
prepared = renderer.prepare_param(
    param_model=param_model,
    tool="adb",
    parameter_values={},
    context_name="default",
    workflow=workflow,    # для _m.* ссылок
    env=env,              # для макросов
    step=step             # текущий шаг
)

# Полный рендеринг параметра
rendered = renderer.render_all_params(
    param_model=param_model,
    tools=["adb", "oracle"],
    parameter_values={},
    workflow=workflow,
    context_name="default",
    step=step
)
```

### 7.6 Создание нового типа материализации

1. Создать Python-макрос:
   ```python
   # FW/macros/main/materialization/my_custom.py
   def materialization_my_custom(step, workflow, env):
       ...
   ```

2. Создать Jinja2-шаблон:
   ```jinja
   {# FW/macros/main/materialization/my_custom_body.sql.j2 #}
   ...
   ```

3. Зарегистрировать в `FW/macros/__init__.py`

---

## 9. Генераторы workflow

### 8.1 Доступные генераторы

| Генератор | Назначение | Директория |
|-----------|------------|------------|
| `airflow` | Airflow DAG | `macros/workflow/airflow/` |
| `dbt` | dbt models | `macros/workflow/dbt/` |
| `oracle_plsql` | Oracle PL/SQL | `macros/workflow/oracle_plsql/` |
| `dqcr` | Нативный DQCR | `macros/workflow/dqcr/` |

### 8.2 Интерфейс генератора

```python
from FW.macros.env import WorkflowMacroEnv

def generate_workflow(
    workflow: WorkflowModel,
    engine: str,
    output_path: Path,
    tools: List[str]
):
    """Генерация workflow-файлов"""
    
    env = WorkflowMacroEnv(
        workflow_name=workflow.model_name,
        target_path=output_path,
        tools=tools
    )
    
    # Создание структуры директорий
    env.create_directory("steps")
    
    # Генерация шагов
    for step in workflow.steps:
        if step.sql_model:
            for tool in tools:
                sql = step.sql_model.get_rendered_sql(tool)
                env.create_file(
                    f"steps/{step.full_name}_{tool}.sql",
                    sql
                )
    
    # Генерация DAG/оркестратора
    dag_content = env.render_template(
        f"workflow/{engine}/dag",
        workflow=workflow,
        steps=workflow.steps
    )
    env.create_file("dag.py", dag_content)
```

### 8.3 Создание генератора

1. Создать директорию `FW/macros/workflow/my_generator/`
2. Добавить шаблоны Jinja2
3. Реализовать функцию генерации
4. Зарегистрировать в `workflow_engines.yml`

---

## 10. Расширение функциональности

### 10.1 Viewer

FW Workflow Viewer — веб-приложение для визуализации и анализа проектов DQCR. Подробное руководство см. в отдельном документе `Viewer_guide.md`.

#### Структура Viewer

```
FW/viewer/
├── run_viewer.py           # Скрипт запуска
├── backend/               # FastAPI backend
│   ├── main.py
│   ├── routes.py
│   ├── services.py
│   └── config.py
└── frontend/               # React frontend
    ├── src/
    │   ├── components/    # Компоненты UI
    │   ├── api.ts         # API клиент
    │   └── types.ts       # TypeScript типы
    └── package.json
```

#### Запуск Viewer

```bash
# Автоматический запуск (backend + frontend)
python -m FW.viewer.run_viewer

# Или раздельно
# Backend
python -m uvicorn FW.viewer.backend.main:app --port 9001

# Frontend
cd FW/viewer/frontend
npm install
npm run dev
```

#### Ports

- Frontend: http://localhost:3000
- Backend: http://localhost:9001
- API Docs: http://localhost:9001/docs

### 10.2 Добавление нового инструмента

1. Добавить в `FW/config/tools.yml`:

```yaml
# tools.yml
tools:
  - name: snowflake
    description: "Snowflake"
    supported: true
```

2. Создать специфичные макросы:
   ```
   FW/macros/snowflake/
   ├── materialization/
   │   ├── insert_fc.py
   │   └── upsert_fc.py
   └── functions/
   ```

### 9.2 Добавление нового движка оркестрации

1. Добавить в `FW/config/workflow_engines.yml`:

```yaml
engines:
  - name: prefect
    description: "Prefect"
    default: false
```

2. Создать генератор в `FW/macros/workflow/prefect/`

### 9.3 Добавление функции парсинга SQL

```python
# FW/parsing/custom_parser.py
def parse_custom_function(sql: str) -> Dict:
    """Парсинг кастомных функций"""
    
    pattern = r"MY_FUNC\((.*?)\)"
    matches = re.findall(pattern, sql)
    
    return {"custom_functions": matches}
```

### 11. Конфигурация и реестры

### 10.1 ToolRegistry

```python
from FW.config import ToolRegistry

registry = ToolRegistry()

# Доступные инструменты
print(registry.tools)  # ['adb', 'oracle', 'postgresql']

# Проверка
if registry.has_tool("snowflake"):
    tool = registry.get("snowflake")
```

### 10.2 WorkflowEngineRegistry

```python
from FW.config import WorkflowEngineRegistry

registry = WorkflowEngineRegistry()

print(registry.engines)  # ['airflow', 'dbt', 'oracle_plsql', 'dqcr']
engine = registry.get("airflow")
```

### 10.3 TemplateRegistry

```python
from FW.config import TemplateRegistry

registry = TemplateRegistry()

print(registry.templates)  # ['flx', 'dwh_mart', 'dq_control']
template = registry.get("flx")
```

---

## 12. Устранение неполадок

### 11.1 Логирование

**Уровни логирования:**

- `DEBUG` — подробная отладочная информация
- `INFO` — информационные сообщения
- `WARNING` — предупреждения
- `ERROR` — ошибки

**Настройка:**

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 11.2 Частые ошибки

**Ошибка: "workflow_engine must be specified"**

```
Решение: Указать -w при генерации или задать в шаблоне
python -m FW.cli generate "Project" "Model" -w dqcr
```

**Ошибка: "Target table not found"**

```
Решение: Проверить model.yml — должен быть определен target_table
```

**Ошибка: "No key attributes found for upsert_fc"**

```
Решение: Добавить атрибуты с is_key: true в target_table
```

**Ошибка: "Template not found"**

```
Решение: Проверить имя шаблона в project.yml
Шаблоны: flx, dwh_mart, dq_control
```

### 11.3 Отладка

**Включение debug-режима:**

```bash
# Через переменную окружения
export DQCR_LOG_LEVEL=DEBUG
python -m FW.cli build "Project" "Model" -o output.json
```

**Проверка конфигурации:**

```python
from FW.parsing.project_loader import load_project

project = load_project("MyProject")
print(project.template)
print(project.models)
```

---

## Приложение В. Примеры

### А.1 Создание шаблона

```yaml
# FW/config/templates/enterprise.yml
name: enterprise
description: "Корпоративный шаблон"

models:
  - name: etl
    paths:
      models_root: model
      project_config: project.yml
      model_config: model.yml
      contexts: contexts
      global_params: parameters
      sql: SQL
      target: target/

    config:
      builder: default
      dependency_resolver: graph_based
      workflow_engine: airflow
      default_materialization: stage_calcid

    validation_categories:
      - general
      - sql
      - descriptions

    rules:
      folders:
        "001_Extract":
          required: true
          materialization: stage_calcid
        "002_Transform":
          required: true
          materialization: insert_fc
        "003_Load":
          required: true
          materialization: upsert_fc

      queries:
        "*_audit_*":
          required: true
```

### А.2 Создание валидационного правила

```python
# FW/validation/rules/general/target_table_required.py
from FW.validation.rules.base import BaseValidationRule
from FW.validation.models import ValidationIssue, ValidationLevel
from FW.models.workflow import WorkflowModel
from typing import List


class TargetTableRequiredRule(BaseValidationRule):
    """Целевая таблица должна быть определена"""
    
    name = "general:001_TargetTableRequired"
    category = "general"
    level = ValidationLevel.ERROR
    description = "Модель должна иметь определенную целевую таблицу"
    
    def validate(self, workflow: WorkflowModel) -> List[ValidationIssue]:
        issues = []
        
        if not workflow.target_table:
            issues.append(ValidationIssue(
                level=self.level,
                rule=self.name,
                category=self.category,
                message=f"Модель {workflow.model_name} не имеет target_table",
                location=workflow.model_name
            ))
        elif not workflow.target_table.name:
            issues.append(ValidationIssue(
                level=self.level,
                rule=self.name,
                category=self.category,
                message="target_table должна иметь имя",
                location=workflow.model_name
            ))
        
        return issues
```

### А.3 Создание материализации

```python
# FW/macros/main/materialization/merge.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from FW.models.step import WorkflowStepModel
    from FW.models.workflow import WorkflowModel
    from FW.macros.env import MacroEnv


def materialization_merge(
    step: "WorkflowStepModel",
    workflow: "WorkflowModel",
    env: "MacroEnv"
):
    """Materialization MERGE (для Oracle)"""
    
    wf = env.workflow or workflow
    target_table = wf.target_table
    
    for tool in env.tools:
        if tool != "oracle":
            continue
            
        prepared = step.sql_model.get_prepared_sql(tool)
        
        if not prepared:
            continue
        
        key_attrs = target_table.get_key_attributes(step.sql_model)
        
        rendered = env.render_template(
            "materialization/merge_body",
            tool=tool,
            target_table=target_table.name,
            schema=target_table.schema,
            key_attributes=key_attrs,
            sql=prepared,
            attributes=step.sql_model.get_attribute_names()
        )
        
        step.sql_model.rendered_sql[tool] = rendered
```

---

## Приложение Г. API Reference

### Б.1 CLI

| Команда | Параметры |
|---------|-----------|
| build | project, model, [-c context], [-o output], [-w engine] |
| generate | project, model, [-c context], [-o output], -w engine |
| validate | project, [model], [-c context], [-o output], [-r categories] |
| parse-sql | sql_path, -o output |
| parse-param | param_path, -o output |

### Б.2 Модели

- WorkflowModel
- WorkflowStepModel
- SQLQueryModel
- ParameterModel
- TargetTableModel
- Attribute

### Б.3 Реестры

- ToolRegistry
- WorkflowEngineRegistry
- TemplateRegistry
- ValidationRuleRegistry
- MacroRegistry

---

*Документ создан для DQCR Framework версии 1.0*
