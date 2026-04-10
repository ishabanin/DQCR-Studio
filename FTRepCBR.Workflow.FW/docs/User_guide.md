# DQCR Framework — Руководство пользователя

**Версия документа:** 1.0  
**Дата:** Март 2026

---

## Содержание

1. [Введение](#1-введение)
2. [Архитектура фреймворка](#2-архитектура-фреймворка)
3. [Создание проекта](#3-создание-проекта)
4. [Конфигурация проекта](#4-конфигурация-проекта)
5. [Конфигурация модели](#5-конфигурация-модели)
6. [SQL-запросы и материализация](#6-sql-запросы-и-материализация)
7. [Контексты и параметры](#7-контексты-и-параметры)
8. [CLI-команды](#8-cli-команды)
9. [Валидация проекта](#9-валидация-проекта)
10. [Просмотр workflow-модели](#10-просмотр-workflow-модели)
11. [Целевая директория (target)](#11-целевая-директория-target)
12. [Настройки шаблона проекта](#12-настройки-шаблона-проекта)
13. [Приоритет настроек](#13-приоритет-настроек)
14. [Viewer — визуализация проекта](#14-viewer--визуализация-проекта)

---

## 1. Введение

### 1.1 Что такое DQCR Framework

DQCR (Data Quality & Conversion Framework) — Python-проект для генерации SQL-процессов из структурированных SQL-файлов. Фреймворк вдохновлён dbt (data build tool) и ориентирован на enterprise-проекты с поддержкой нескольких целевых СУБД (Oracle, ADB, PostgreSQL) и различных движков оркестрации (Airflow, dbt, Oracle PL/SQL).

**Основные возможности:**

- Генерация SQL-запросов для нескольких целевых систем
- Поддержка материализации: INSERT, UPSERT, stage-таблицы, CTE
- Валидация проекта по правилам
- Генерация workflow-файлов для оркестраторов
- Поддержка контекстов (default, vtb и др.)
- Параметризация запросов

### 1.2 Для кого это руководство

Данное руководство предназначено для **пользователей**, которые создают и поддерживают проекты на базе DQCR Framework. Вы научитесь:

- Создавать новые проекты
- Настраивать конфигурацию моделей
- Писать SQL-запросы с материализацией
- Использовать CLI для сборки и валидации
- Понимать настройки шаблонов

---

## 2. Архитектура фреймворка

### 2.1 Компоненты системы

```
DQCR Framework
│
├── CLI (cli.py)                 # Интерфейс командной строки
│
├── Generation                   # Генерация workflow
│   ├── DefaultBuilder           # Основной билдер
│   └── DependencyResolver       # Разрешение зависимостей
│
├── Macros                       # Макросы
│   ├── Materialization          # Шаблоны материализации
│   ├── Functions                # Функции преобразования
│   └── Workflow                  # Генераторы workflow
│
├── Parsing                      # Загрузка и парсинг
│   ├── Project Loader           # Загрузка проекта
│   ├── SQL Metadata             # Парсинг SQL
│   └── Inline Config             # Парсинг @config()
│
└── Validation                   # Валидация
    ├── Rule Runner              # Запуск правил
    └── Rules                    # Правила валидации
```

### 2.2 Структура директорий проекта

Типовой проект имеет следующую структуру:

```
MyProject/
├── project.yml                  # Конфигурация проекта
├── contexts/                    # Контексты
│   ├── default.yml
│   └── vtb.yml
├── parameters/                  # Глобальные параметры
│   └── date_end.yml
└── model/
    └── MyModel/                 # Модель (сущность)
        ├── model.yml            # Конфигурация модели
        ├── SQL/                 # SQL-запросы
        │   ├── 001_Load/
        │   │   ├── folder.yml   # Конфигурация папки (опционально)
        │   │   └── 001_Query.sql
        │   └── 002_Update/
        │       └── 001_Upsert.sql
        └── parameters/          # Локальные параметры
```

### 2.3 Типы файлов

| Тип файла | Назначение |
|-----------|------------|
| `project.yml` | Общая конфигурация проекта |
| `model.yml` | Конфигурация модели (целевая таблица, атрибуты, workflow) |
| `folder.yml` | Конфигурация папки (настройки уровня папки) |
| `contexts/*.yml` | Настройки контекста (инструменты, константы, флаги) |
| `parameters/*.yml` | Параметры запросов |
| `SQL/**/*.sql` | SQL-запросы с @config() блоками |

---

## 3. Создание проекта

### 3.1 Алгоритм создания

Создание нового проекта включает следующие шаги:

1. **Создать директорию проекта** — корневая папка с произвольным именем
2. **Добавить `project.yml`** — файл конфигурации проекта
3. **Создать контексты** — в директории `contexts/`
4. **Определить параметры** — в директории `parameters/`
5. **Создать модель** — в директории `model/<model_name>/`
6. **Настроить `model.yml`** — целевая таблица, атрибуты, workflow
7. **Написать SQL-запросы** — в папке `SQL/<folder>/`

### 3.2 Пример создания проекта

Создадим проект `MyDataMart`:

```bash
mkdir -p MyDataMart/contexts
mkdir -p MyDataMart/parameters
mkdir -p MyDataMart/model/SalesReport
mkdir -p MyDataMart/model/SalesReport/SQL/001_Load
mkdir -p MyDataMart/model/SalesReport/SQL/002_Transform
mkdir -p MyDataMart/model/SalesReport/parameters
```

### 3.3 Минимальная конфигурация project.yml

```yaml
# MyDataMart/project.yml
name: MyDataMart
description: "Продажи и отчетность"
template: flx

properties:
  repsysname: sales
  owner: analytics_team
```

**Обязательные поля:**

- `name` — имя проекта
- `template` — имя шаблона (flx, dwh_mart, dq_control)

### 3.4 Выбор шаблона

Список доступных шаблонов можно посмотреть в CLI:

```bash
python -m FW.cli --help
```

Шаблоны хранятся в `FW/config/templates/`. Каждый шаблон определяет:

- Структуру директорий проекта
- Набор правил валидации (`validation_categories`)
- Настройки по умолчанию (`config.*`)

Подробнее о шаблонах см. раздел [12. Настройки шаблона проекта](#12-настройки-шаблона-проекта).

---

## 4. Конфигурация проекта

### 4.1 Файл project.yml

Файл `project.yml` находится в корне проекта и определяет глобальные настройки:

```yaml
name: RF110
description: "Проект расчетаTurnover"
template: flx

properties:
  repsysname: f110
  version: "1.0.0"
  environment: production
```

### 4.2 Доступные поля

| Поле | Тип | Описание |
|------|-----|----------|
| `name` | string | Имя проекта |
| `description` | string | Описание |
| `template` | string | Имя шаблона (обязательно) |
| `properties` | dict | Произвольные свойства |

### 4.3 Контексты

Контексты позволяют определять разные конфигурации для одного проекта. Например, для разных окружений или версий.

**Директория:** `contexts/<context_name>.yml`

```yaml
# contexts/default.yml
project: default
tools:
  - adb
  - oracle
  - postgresql

constants:
  schema: DEFAULT_SCHEMA
  batch_size: 10000

flags:
  enable_debug: false
  enable_logging: true
```

```yaml
# contexts/vtb.yml
project: vtb
tools:
  - adb

constants:
  schema: VTB_SCHEMA
  batch_size: 50000

flags:
  enable_debug: false
  enable_logging: true
  use_vtb_optimizations: true
```

### 4.4 Структура контекста

| Поле | Тип | Описание |
|------|-----|----------|
| `project` | string | Имя контекста |
| `tools` | list | Целевые СУБД (adb, oracle, postgresql) |
| `constants` | dict | Константы, доступные в SQL |
| `flags` | dict | Логические флаги |

### 4.5 Параметры

Параметры позволяют передавать значения в SQL-запросы.

**Директория:** `parameters/<param_name>.yml`

**Domain types (типы данных):**

| Тип | Описание |
|-----|----------|
| `string` | Строковый тип |
| `number` | Числовой тип |
| `date` | Дата |
| `datetime` | Дата и время |
| `bool` | Логический тип |
| `record` | Запись (структура) |
| `array` | Массив |
| `sql.condition` | SQL-условие |
| `sql.expression` | SQL-выражение |
| `sql.identifier` | SQL-идентификатор (имя таблицы, колонки) |

**Типы значений (type):**

| Тип | Описание |
|-----|----------|
| `static` | Статическое значение |
| `dynamic` | SQL-выражение (подзапрос) |

**Пример:**

```yaml
# parameters/date_end.yml
parameter:
  name: date_end
  description: "Дата окончания расчета"
  domain_type: date

  values:
    all:
      type: static
      value: "TO_DATE('2024-01-01', 'YYYY-MM-DD')"
    
    vtb:
      type: dynamic
      value: "SELECT MAX(calc_date) FROM vtb_calc_dates"
    
    default:
      type: static
      value: "SYSDATE"
```

**Область видимости (scope):**
- `global` — глобальный параметр (в корне проекта `parameters/`)
- `model` — параметр модели (в `model/<model_name>/parameters/`)

---

## 5. Конфигурация модели

### 5.1 Структура model.yml

Файл `model.yml` находится в директории модели (`model/<model_name>/model.yml`) и определяет:

- Целевую таблицу
- Атрибуты
- Workflow (папки и запросы)
- Настройки материализации

```yaml
# model/SalesReport/model.yml
target_table:
  name: SalesReport
  schema: ANALYTICS
  attributes:
    - name: dealid
      domain_type: number
      is_key: true
      constraints: [PRIMARY_KEY]
    - name: clientid
      domain_type: number
      is_key: true
    - name: amount
      domain_type: number
      required: true
      default_value: 0
    - name: created_at
      domain_type: date

workflow:
  description: "Расчет продаж"
  
  folders:
    001_Load:
      description: "Загрузка данных"
      enabled: true
      
      queries:
        001_LoadSales:
          materialized: insert_fc
          enabled: true
    
    002_Transform:
      description: "Трансформация"
      enabled: true
      
      queries:
        001_CalculateMetrics:
          materialized: stage_calcid
```

### 5.2 Целевая таблица (target_table)

```yaml
target_table:
  name: SalesReport       # Имя таблицы
  schema: ANALYTICS       # Схема/база данных
  attributes:             # Список атрибутов
    - name: dealid
      domain_type: number
      is_key: true
      constraints: [PRIMARY_KEY]
```

### 5.3 Атрибуты

Атрибуты определяют структуру целевой таблицы:

```yaml
attributes:
  - name: clientid          # Имя атрибута
    domain_type: number     # Тип: number, string, date, timestamp
    is_key: true            # Является ключевым (для UPSERT)
    required: true          # Обязательный
    default_value: 0        # Значение по умолчанию
    constraints:            # Ограничения
      - PRIMARY_KEY
      - NOT_NULL
```

**Поля атрибута:**

| Поле | Тип | Описание |
|------|-----|----------|
| `name` | string | Имя атрибута |
| `domain_type` | string | Тип (number, string, date, timestamp) |
| `is_key` | boolean | Ключевой атрибут для UPSERT |
| `required` | boolean | Обязательный атрибут |
| `default_value` | any | Значение по умолчанию |
| `constraints` | list | Ограничения (PRIMARY_KEY, NOT_NULL, FOREIGN_KEY) |

### 5.4 Workflow (папки и запросы)

Структура workflow определяет порядок выполнения SQL-запросов:

```yaml
workflow:
  description: "Описание workflow"
  
  folders:
    001_Load:                    # Имя папки (префикс определяет порядок)
      description: "Загрузка"
      enabled: true              # Включена/отключена
      
      queries:
        001_QueryName:           # Имя запроса
          materialized: insert_fc # Тип материализации
          enabled: true          # Включен
          attributes:            # Переопределение атрибутов
            - name: amount
              is_key: false
```

**Именование папок:**

- Префикс `001_`, `002_` и т.д. определяет порядок выполнения
- Суффиксы `_Load`, `_Update`, `_Transform` влияют на правила валидации

### 5.5 Folder-level конфигурация (folder.yml)

Помимо `model.yml`, вы можете определять конфигурацию для отдельных папок в файлах `folder.yml`. Это позволяет хранить настройки папок отдельно от основного конфига модели.

#### Расположение

```
model/<model_name>/SQL/<folder_name>/folder.yml
```

#### Пример

```yaml
# model/RF110RestTurnReg/SQL/001_Load__distr/folder.yml
001_Load__distr:
  enabled:
    contexts: [default]
  queries:
    001_RF110_Reg_Acc2:
      materialized: stage_calcid
  pre:
    - synch_iter
```

#### Поддерживаемые ключи

| Ключ | Описание |
|------|----------|
| `enabled` | Включение/отключение папки для контекстов |
| `materialized` | Материализация по умолчанию для папки |
| `queries.<query_name>.*` | Настройки уровня запроса |
| `pre` | Pre-макросы для папки |
| `post` | Post-макросы для папки |
| `cte` | Конфигурация материализации CTE |
| `description` | Описание папки |

#### Приоритет

Конфиг из `folder.yml` переопределяет настройки из `model.yml`:
```
folder.yml > model.yml > defaults
```

#### Загрузка

Фреймворк загружает `folder.yml` автоматически:
1. Сначала загружается `model.yml`
2. Сканируется директория `SQL/` на наличие подпапок
3. Из каждой подпапки загружается `folder.yml`
4. Конфиги мержатся (folder.yml имеет приоритет)

#### Зачем использовать folder.yml

- Изоляция настроек — каждый folder управляется независимо
- Упрощение model.yml — меньший файл конфигурации
- Командная работа — разные команды могут работать с разными папками

---

## 6. SQL-запросы и материализация

### 6.1 Расположение SQL-файлов

SQL-файлы располагаются в директории модели:

```
model/<model_name>/SQL/<folder>/<query>.sql
```

Пример:

```
model/SalesReport/
├── model.yml
└── SQL/
    ├── 001_Load/
    │   └── 001_LoadSales.sql
    └── 002_Transform/
        └── 001_Calculate.sql
```

### 6.2 Пример SQL-запроса

```sql
-- 001_LoadSales.sql
SELECT 
    s.deal_id AS dealid,
    s.client_id AS clientid,
    s.amount,
    s.deal_date AS created_at
FROM stg_sales s
WHERE s.status = 'APPROVED'
```

### 6.3 Типы материализации

Список доступных типов материализации зависит от выбранного шаблона и определяется в `config/default_materialization`.

Посмотреть доступные материализации можно в коде макросов:
- Python-макросы: `FW/macros/main/materialization/*.py`
- Jinja2-шаблоны: `FW/macros/main/materialization/*.sql.j2`

Основные категории материализаций:

| Категория | Описание |
|-----------|----------|
| Вставка | Полная загрузка (INSERT) |
| Обновление | Инкрементальная загрузка (UPSERT) |
| Промежуточная | Stage-таблицы для промежуточных результатов |
| Ephemeral | CTE, не материализуется |

### 6.4 Настройка материализации в model.yml

```yaml
queries:
  001_LoadSales:
    materialized: insert_fc        # Тип материализации
```

### 6.5 Inline-конфигурация (@config)

Можно определять конфигурацию непосредственно в SQL-файлах с помощью блоков `@config()`:

```sql
/*
@config(
  enabled: true
  materialized: insert_fc
  attributes:
    - name: clientid
      domain_type: number
      is_key: true
)
*/
SELECT 
    client_id AS clientid,
    amount
FROM stg_sales
```

**Типы inline-конфигурации:**

1. **Query-level** — в начале файла, перед WITH/SELECT
2. **CTE-level** — внутри CTE, например: `cte_name as (/* @config */ SELECT ...)`

### 6.6 CTE materialization

Управление материализацией отдельных CTE:

```sql
with 
sales as (
/*
@config(
  cte_materialization:
    default: ephemeral
    by_context:
      vtb: stage_calcid
  by_tool:
    postgresql: stage_calcid
)
*/
SELECT * FROM stg_sales
),
agg as (
SELECT 
    clientid,
    SUM(amount) AS total_amount
FROM sales
GROUP BY clientid
)
SELECT * FROM agg
```

### 6.7 Ссылки на модели (_m.*) и workflow (_w.*)

В SQL-запросах можно ссылаться на:
- Другие модели (`_m.*`)
- Другие шаги текущего workflow (`_w.*`)

**Важно:** Ссылки `_m.*` и `_w.*` пишутся **без** скобок `{{ }}`.

#### 6.7.1 Разрешение ссылок

Разрешение ссылок выполняется специальным **model_ref-макросом**, который задаётся в шаблоне проекта:

```yaml
# FW/config/templates/flx.yml
models:
  - name: marts
    config:
      model_ref_macro: table   # Используется макрос table
```

Макрос `model_ref/table.py` преобразует ссылки в реальные имена таблиц:
- `_m.dwh.ClientChr` → `"DWH"."CLIENT_CHR"`
- `_m.RF110.RF110RestTurnReg.seq` → `"RF110"."RF110RESTTURNREG_SEQ"`

#### 6.7.2 Примеры использования

**Ссылка на другую модель:**

```sql
-- model/SalesReport/SQL/002_Transform/001_Aggregate.sql
SELECT 
    s.clientid,
    s.amount,
    c.client_name
FROM _m.SalesReport.stg_sales s
LEFT JOIN _m.Clients.client c ON s.clientid = c.clientid
```

**Ссылка на шаг в том же workflow:**

```sql
-- model/SalesReport/SQL/002_Transform/002_Calculate.sql
WITH base AS (
    SELECT * FROM _w.001_LoadSales
),
enriched AS (
    SELECT * FROM _w.001_Load.001_Aggregate
)
SELECT * FROM enriched
```

#### 6.7.3 Синтаксис ссылок

**Для моделей (`_m.*`):**
```
_m.<schema>.<entity>   -- _m.dwh.ClientChr
_m.<model>.<table>    -- _m.SalesReport.stg_sales
```

**Для workflow (`_w.*`):**
```
_w.<folder>.<query_name>           -- _w.001_Load.001_LoadSales
_w.<folder>.<subfolder>.<name>     -- _w.001_Load.district.001_Calculate
_w.<query_name>                    -- _w.get_entities (без папки)
```

**Примеры из проекта:**
```sql
from _m.dwh.client c
from _m.PSReg.PSRegister r
inner join _w.001_Load_distr.RF110_Reg_Acc2 a
```

#### 6.7.4 Типы материализации при подстановке

При разрешении `_w.*`:

- Если шаг `ephemeral` → подставляется как CTE
- Если шаг материализован (`stage_*`, `insert_fc`, `upsert_fc`) → подставляется как имя таблицы

#### 6.7.5 Настройка model_ref_macro

Тип макроса определяется в шаблоне:

| Значение | Описание | Пример результата |
|---------|----------|-------------------|
| `table` | Только имя таблицы | `"CLIENT_CHR"` |
| `schema` | Схема.таблица | `"DWH"."CLIENT_CHR"` |

```yaml
# В template config
config:
  model_ref_macro: table    # По умолчанию
  # или
  model_ref_macro: schema   # Схема.имя
```

---

## 7. Контексты и параметры

### 7.1 Использование контекстов

Контекст определяет, какая конфигурация будет использоваться при сборке. По умолчанию используется контекст `default`.

**Сборка для контекста по умолчанию:**

```bash
python -m FW.cli build "MyProject" "MyModel" -o output.json
```

**Сборка для конкретного контекста:**

```bash
python -m FW.cli build "MyProject" "MyModel" -c vtb -o output.json
```

### 7.2 Подстановка параметров в SQL

Параметры подставляются в SQL через синтаксис `{{param_name}}`:

```sql
SELECT * FROM orders
WHERE order_date >= {{date_start}}
  AND order_date <= {{date_end}}
```

**Типы параметров:**

- `static` — статическое значение
- `dynamic` — SQL-выражение (подзапрос)

### 7.3 Параметры с _m.* ссылками

Динамические параметры могут содержать ссылки на модели (`_m.*`), аналогично SQL-запросам:

```yaml
# parameters/settings_table.yml
parameter:
  name: settings_table
  description: "Таблица настроек"
  domain_type: record

  values:
    all:
      type: dynamic
      value: "select strnum, account2 from _m.rf110.rf110_settings"
```

При обработке параметра:
1. SQL парсится для извлечения метаданных (_m.* ссылки)
2. Создаётся шаг `get_entities` для динамического получения имён таблиц
3. _m.* ссылки заменяются на параметры вида `{{ table_module_entity }}`

**Пример результата:**

```sql
-- prepared_sql (после замены функций, до замены _m.*):
select strnum, account2 from _m.rf110.rf110_settings

-- rendered_sql (после замены _m.*):
select strnum, account2 from {{ table_rf110_rf110_settings }}
```

Шаг `get_entities` автоматически добавляется в начало workflow и генерирует SQL для получения имён таблиц из `md_entity2table`.

### 7.3 Константы контекста

Константы доступны как переменные в Jinja2-шаблонах:

```yaml
# contexts/default.yml
constants:
  schema: ANALYTICS
  batch_size: 10000
```

```sql
-- В SQL-шаблонах (materialization)
SELECT * FROM {{ ctx.constants.schema }}.orders
LIMIT {{ ctx.constants.batch_size }}

-- Или через префикс ctx.
SELECT * FROM {{ ctx.schema }}.orders
```

### 7.4 Flags

Флаги управляют условным включением частей SQL:

```yaml
# contexts/default.yml
flags:
  enable_debug: true
  overduecalcmethod:
    fifo: false
    lifo: true
```

**Использование в Python-макросах:**

```python
# В materialization-макросе
if env.flags.get('enable_debug'):
    # добавить отладочную информацию
    pass

# Поддержка вложенных флагов через точку
if env.get_flag('overduecalcmethod.fifo'):
    # для FIFO
    pass
```

**Использование в Jinja2-шаблонах:**

```sql
-- Через ctx.flags
{% if ctx.flags.enable_debug %}
SELECT id, debug_info, name FROM table1
{% else %}
SELECT id, name FROM table1
{% endif %}

-- Вложенные флаги
{% if ctx.flags.overduecalcmethod.fifo %}
-- FIFO логика
{% endif %}
```

### 7.5 Условное включение шагов (enabled.conditions)

Флаги и константы используются для условного включения папок и запросов:

```yaml
# model.yml
workflow:
  folders:
    HeavyCalc:
      enabled:
        conditions:
          enable_heavy_calc: true     # флаг = значение
          overduecalcmethod.fifo: true # вложенный флаг
    
    FastPath:
      enabled:
        conditions:
          enable_heavy_calc: false    # флаг = false исключает
    
    ConditionalFolder:
      enabled:
        conditions:
          ctx_name: vtb                # контекст = значение
          schema: ANALYTICS             # константа = значение

  queries:
    MyQuery:
      enabled:
        contexts: [default, vtb]        # в каких контекстах включено
        conditions:                    # AND - все условия должны выполниться
          enable_feature_x: true
          any:                         # OR - хотя бы одно условие
            enable_feature_a: true
            enable_feature_b: true
```

**Приоритет проверки:**
1. `contexts` — если указан и текущий контекст не в списке → шаг исключается
2. `conditions` — если указаны и не выполняются → шаг исключается

---

## 8. CLI-команды

### 8.1 Обзор команд

Полный список команд и их параметров:

```bash
python -m FW.cli --help
python -m FW.cli <command> --help
```

Основные команды:

| Команда | Назначение |
|---------|------------|
| `build` | Собрать workflow-модель (JSON) |
| `generate` | Сгенерировать workflow-файлы |
| `validate` | Валидировать проект |
| `parse-sql` | Парсить SQL-файл в метаданные |
| `parse-param` | Парсить параметр YAML |

### 8.2 Команда build

Собирает workflow-модель и сохраняет в JSON:

```bash
python -m FW.cli build <project_path> <model_name> [-c context] [-o output]
```

**Примеры:**

```bash
# Сборка для контекста по умолчанию
python -m FW.cli build "RF110NEW" "RF110RestTurnReg" -o output.json

# Сборка для конкретного контекста
python -m FW.cli build "RF110NEW" "RF110RestTurnReg" -c vtb -o output.json

# Сборка с указанием workflow_engine
python -m FW.cli build "RF110NEW" "RF110RestTurnReg" -w dqcr -o output.json
```

### 8.3 Команда generate

Генерирует workflow-файлы для указанного движка:

```bash
python -m FW.cli generate <project_path> <model_name> [-c context] [-o output] -w <workflow_engine>
```

**Выбор workflow_engine:**

Список доступных workflow_engine можно посмотреть:

```bash
python -m FW.cli --help
```

Движки оркестрации хранятся в `FW/config/workflow_engines.yml`.

**Workflow engine** также должен быть указан в настройках шаблона (поле `config.workflow_engine`). Подробнее см. раздел [12. Настройки шаблона проекта](#12-настройки-шаблона-проекта).

**Примеры:**

```bash
# Генерация (движок берется из шаблона)
python -m FW.cli generate "RF110NEW" "RF110RestTurnReg"

# Генерация с явным указанием движка
python -m FW.cli generate "RF110NEW" "RF110RestTurnReg" -w airflow
```

### 8.4 Команда validate

Валидирует проект по правилам шаблона:

```bash
python -m FW.cli validate <project_path> [model_name] [-c context] [-o output] [-r categories]
```

**Примеры:**

```bash
# Валидация конкретной модели
python -m FW.cli validate "RF110NEW" "RF110RestTurnReg"

# Валидация с указанием контекста
python -m FW.cli validate "RF110NEW" "RF110RestTurnReg" -c vtb

# Валидация с конкретными категориями правил
python -m FW.cli validate "RF110NEW" "RF110RestTurnReg" -r "general,sql,descriptions"

# Валидация всего проекта с сохранением отчетов
python -m FW.cli validate "RF110NEW" -o validation_reports
```

**Категории валидации:**

- `general` — общие проверки
- `sql` — проверки SQL-кода
- `adb` — проверки ADB (распределение ключей)
- `descriptions` — проверки описаний

### 8.5 Команда parse-sql

Парсит SQL-файл и извлекает метаданные:

```bash
python -m FW.cli parse-sql <sql_path> -o output.json
```

**Пример:**

```bash
python -m FW.cli parse-sql "model/MyModel/SQL/001_Load/001_Query.sql" -o metadata.json
```

### 8.6 Команда parse-param

Парсит файл параметра YAML:

```bash
python -m FW.cli parse-param <param_path> -o output.json
```

**Пример:**

```bash
python -m FW.cli parse-param "parameters/date_end.yml" -o param.json
```

---

## 9. Валидация проекта

### 9.1 Как работает валидация

Валидация проверяет проект на соответствие правилам, определенным в шаблоне. Результат — отчет с ошибками, предупреждениями и информационными сообщениями.

**Категории правил:**

| Категория | Описание | Примеры проверок |
|-----------|----------|------------------|
| `general` | Общие | Наличие target_table, steps, tools |
| `sql` | SQL-код | Запрещенные операторы, SELECT * |
| `adb` | ADB-специфичные | distribution_key, primary_key |
| `descriptions` | Описания | Описания workflow, папок |

### 9.2 Результаты валидации

После выполнения валидации выводится сводка:

```
=== Validation Report ===
Model: RF110RestTurnReg
Template: flx
Timestamp: 2024-03-15T10:30:00

Errors: 0
Warnings: 3
Info: 5

Issues:
[WARNING] sql:001_MissingPrimaryKey - Таблица RF110RestTurnReg не имеет primary_key атрибута
[WARNING] sql:002_SelectStar - Запрос 001_Load использует SELECT *
[INFO] general:001_TargetTableFound - Целевая таблица найдена
```

### 9.3 Выходные форматы

**JSON** — машинный формат:

```bash
python -m FW.cli validate "RF110NEW" "RF110RestTurnReg" -o report.json
```

**HTML** — интерактивный отчет с фильтрацией:

```bash
python -m FW.cli validate "RF110NEW" "RF110RestTurnReg" -o report.html
```

### 9.4 Типичные ошибки и их исправление

**1. Отсутствует primary_key:**

```yaml
# Ошибка
attributes:
  - name: id
    domain_type: number
    # is_key: true — отсутствует!

# Исправление
attributes:
  - name: id
    domain_type: number
    is_key: true
    constraints: [PRIMARY_KEY]
```

**2. Запрос использует SELECT *:**

```sql
-- Ошибка
SELECT * FROM table1

-- Исправление: явно указать колонки
SELECT id, name, amount FROM table1
```

**3. Папка отключена, но запросы выполняются:**

```yaml
# Проверьте enabled в model.yml
folders:
  001_Load:
    enabled: false  # Папка отключена
```

---

## 10. Просмотр workflow-модели

### 10.1 Формат JSON

После выполнения команды `build` создается JSON-файл с полным описанием workflow:

```bash
python -m FW.cli build "RF110NEW" "RF110RestTurnReg" -o output.json
```

### 10.2 Структура JSON-вывода

```json
{
  "model_name": "RF110RestTurnReg",
  "target_table": {
    "name": "RF110RestTurnReg",
    "schema": "RF110",
    "attributes": [...]
  },
  "steps": [
    {
      "step_id": "001_Load/001_LoadDeals",
      "name": "001_LoadDeals",
      "folder": "001_Load",
      "full_name": "001_Load/001_LoadDeals",
      "step_type": "SQL",
      "materialized": "insert_fc",
      "dependencies": [],
      "sql_model": {
        "prepared_sql": {...},
        "rendered_sql": {...}
      }
    }
  ],
  "graph": {
    "nodes": [...],
    "edges": [...]
  }
}
```

### 10.3 Просмотр в Python

Для удобного просмотра используйте Python:

```python
import json

with open('output.json', 'r') as f:
    workflow = json.load(f)

print(f"Model: {workflow['model_name']}")
print(f"Target: {workflow['target_table']['name']}")
print(f"Steps: {len(workflow['steps'])}")

for step in workflow['steps']:
    print(f"  - {step['full_name']} ({step['materialized']})")
```

### 10.4 Зависимости между шагами

Зависимости определяются автоматически на основе:

- Именования (соглашение об именах)
- Явных ссылок через `{{ref:step_name}}`
- Порядка папок

```json
"graph": {
  "nodes": [
    {"id": "001_Load/001_LoadDeals", "step_id": "..."},
    {"id": "002_Update/001_UpdateDeals", "step_id": "..."}
  ],
  "edges": [
    {"from": "001_Load/001_LoadDeals", "to": "002_Update/001_UpdateDeals"}
  ]
}
```

---

## 11. Целевая директория (target)

### 11.1 Структура target

После генерации workflow создаются файлы в директории `target/`:

```
target/
├── dqcr/                           # Нативный формат DQCR
│   └── <model_name>/
│       ├── workflow.json
│       └── steps/
│           ├── 001_Load.sql
│           └── 002_Update.sql
│
├── airflow/                       # Airflow DAGs
│   └── <model_name>/
│       └── dag.py
│
├── dbt/                           # dbt модели
│   └── <model_name>/
│       └── models/
│
└── oracle_plsql/                  # Oracle PL/SQL
    └── <model_name>/
        └── packages/
```

### 11.2 Генерация в target

```bash
# Генерация в целевую директорию
python -m FW.cli generate "RF110NEW" "RF110RestTurnReg" -w dqcr
```

По умолчанию файлы создаются в `target/<workflow_engine>/<model_name>/`.

### 11.3 Настройка пути

Можно указать кастомный путь вывода:

```bash
python -m FW.cli generate "RF110NEW" "RF110RestTurnReg" -w airflow -o ./custom_output
```

---

## 12. Настройки шаблона проекта

### 12.1 Зачем нужны настройки шаблона

Шаблон определяет:

- Структуру директорий проекта
- Правила валидации
- Настройки по умолчанию
- Доступные инструменты и движки

### 12.2 Просмотр настроек шаблона

Настройки шаблона хранятся в `FW/config/templates/<template_name>.yml`.

**Просмотр доступных шаблонов:**

```python
from FW.config import TemplateRegistry

registry = TemplateRegistry()
print(registry.templates)  # ['flx', 'dwh_mart', 'dq_control']
```

**Получение конкретного шаблона:**

```python
template = registry.get('flx')
print(template.name)
print(template.validation_categories)
print(template.config)
```

### 12.3 Структура шаблона

```yaml
# FW/config/templates/flx.yml
name: flx
description: "Гибкий шаблон для витрин данных"

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
        "*_iter*":
          pre: synch_iter
        "*_Load*":
          required: false
          materialization: insert_fc
        "*_Update*":
          required: false
          materialization: upsert_fc
```

### 12.4 Ключевые настройки шаблона

| Параметр | Описание |
|----------|----------|
| `config.builder` | Билдер для генерации (default) |
| `config.dependency_resolver` | Метод разрешения зависимостей |
| `config.workflow_engine` | Движок оркестрации по умолчанию |
| `config.default_materialization` | Материализация по умолчанию |
| `validation_categories` | Категории правил валидации |
| `rules.folders` | Правила для папок |
| `rules.queries` | Правила для запросов |

### 12.5 Как правила влияют на проект

**Пример правила для папок:**

```yaml
rules:
  folders:
    "*_Load*":           # Папки с суффиксом _Load
      required: false    # Не обязательны
      materialization: insert_fc  # По умолчанию
    "*_Update*":         # Папки с суффиксом _Update
      required: false
      materialization: upsert_fc
```

Это означает:

- Если папка называется `001_LoadData`, к ней автоматически применяется материализация `insert_fc`
- Валидатор не требует наличия папок `*_Load*`

### 12.6 Как посмотреть активные правила

**Программный способ:**

```python
from FW.parsing.template_loader import load_template

template = load_template('flx')
print(template.rules)
```

**Через CLI:**

```bash
# Валидация покажет активные правила
python -m FW.cli validate "MyProject" "MyModel" -r "general,sql"
```

---

## 14. Viewer — визуализация проекта

### 14.1 Что такое Viewer

**FW Workflow Viewer** — веб-приложение для визуализации и анализа проектов DQCR. Позволяет:

- Загружать и просматривать структуру проекта
- Строить и визуализировать workflow-модели
- Валидировать проекты и отображать результаты
- Просматривать SQL-запросы с подсветкой синтаксиса
- Анализировать граф зависимостей между шагами
- Просматривать конфигурационные файлы (YAML)

### 14.2 Запуск Viewer

```bash
python -m FW.viewer.run_viewer
```

После запуска:
- **Web-интерфейс:** http://localhost:3000
- **API:** http://localhost:9001

### 14.3 Основные возможности

**Загрузка проекта:**
1. Введите путь к проекту в поле Project
2. Нажмите Load

**Выбор модели и контекста:**
- Model — выберите модель из списка
- Context — выберите контекст (default, vtb, all)

**Валидация:**
- Нажмите Verify для запуска валидации
- Результаты отображаются в дереве проекта (индикаторы)

**Просмотр:**
- Клик по элементу в дереве открывает его в новой вкладке
- SQL-файлы показываются с подсветкой синтаксиса
- Граф workflow доступен через элемент Graph в дереве

**Интерфейс:**
- Темная/светлая тема (кнопка в правом верхнем углу)
- Изменяемая ширина sidebar
- Множественные вкладки

### 14.4 Подробное руководство

Полное руководство по Viewer см. в отдельном документе `Viewer_guide.md`.

---

## Приложение А. Примеры конфигураций

### А.1 Минимальный проект

```
MinimalProject/
├── project.yml
├── contexts/
│   └── default.yml
└── model/
    └── SimpleModel/
        ├── model.yml
        └── SQL/
            └── 001_Load/
                └── 001_Query.sql
```

### А.2 Полный пример model.yml

```yaml
target_table:
  name: OrdersSummary
  schema: ANALYTICS
  attributes:
    - name: order_id
      domain_type: number
      is_key: true
      constraints: [PRIMARY_KEY]
    - name: client_id
      domain_type: number
      is_key: true
    - name: order_date
      domain_type: date
    - name: total_amount
      domain_type: number
      required: true
      default_value: 0
    - name: status
      domain_type: string
      required: true
      default_value: 'NEW'

workflow:
  description: "Сводка заказов"
  
  folders:
    001_Extract:
      description: "Извлечение данных"
      enabled: true
      
      queries:
        001_OrdersRaw:
          materialized: stage_calcid
    
    002_Transform:
      description: "Трансформация"
      enabled: true
      
      queries:
        001_Aggregate:
          materialized: insert_fc
        
        002_Enrich:
          materialized: upsert_fc

cte:
  cte_materialization:
    default: ephemeral
    by_context:
      vtb: stage_calcid
```

---

## 13. Приоритет настроек

Конфигурация в DQCR имеет чёткую иерархию приоритетов. Настройки с более высоким приоритетом переопределяют более низкие.

### 13.1 Иерархия приоритетов (от низкого к высокому)

| Уровень | Источник | Описание |
|--------|----------|----------|
| 1 | Шаблон проекта (`FW/config/templates/*.yml`) | Настройки по умолчанию |
| 2 | Переопределения шаблона (`project.yml`) | Настройки проекта |
| 3 | model.yml | Настройки конкретной модели |
| 4 | folder.yml | Настройки конкретной папки (переопределяет model.yml) |
| 5 | Inline-конфигурация (`@config()` в SQL) | Настройки уровня запроса/CTE/атрибута |

### 13.2 Примеры переопределения

**1. Материализация:**

```
Шаблон: default_materialization = insert_fc
project.yml: Нет переопределения
model.yml: queries.my_query.materialized = upsert_fc
SQL: @config(materialized: stage_calcid)
→ Итог: stage_calcid (наивысший приоритет)
```

**2. Workflow engine:**

```
Шаблон: workflow_engine = dbt
project.yml: Нет переопределения
model.yml: config.workflow_engine = airflow
→ Итог: airflow
```

### 13.3 Правило merge

Для словарей (dict) применяется **merge**, а не полная замена:

```yaml
# model.yml
cte:
  cte_materialization:
    default: ephemeral

# SQL @config
@config(cte_materialization: stage_calcid)
→ Итог: merge → {default: stage_calcid}
```

### 13.4 Контекстная фильтрация

Контексты (`-c vtb`) влияют только на:
- Выбор значений параметров (`values.vtb`)
- Включение папок/запросов (`enabled.contexts`, `enabled.conditions`)
- Материализацию CTE (`cte.by_context`)

Контекст **не влияет** на:
- Выбор шаблона
- Workflow engine
- Настройки материализации запросов (кроме CTE)

---

## Приложение Б. Часто задаваемые вопросы

**В: Как добавить новый запрос?**  
О: Создайте SQL-файл в нужной папке и добавьте его в `model.yml` в раздел `queries`.

**В: Как изменить тип материализации?**  
О: Укажите `materialized` в конфигурации запроса в `model.yml` или используйте `@config()` в SQL-файле.

**В: Как запустить валидацию только для SQL-правил?**  
О: Используйте `-r sql`: `python -m FW.cli validate "Project" "Model" -r sql`

**В: Где посмотреть сгенерированные файлы?**  
О: В директории `target/<workflow_engine>/<model_name>/`

**В: Как работать с разными контекстами?**  
О: Укажите контекст через флаг `-c`: `python -m FW.cli build "Project" "Model" -c vtb`

---

*Документ создан для DQCR Framework версии 1.0*
