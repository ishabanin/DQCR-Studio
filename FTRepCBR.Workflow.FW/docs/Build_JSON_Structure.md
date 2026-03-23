# Структура JSON, который формирует `build`

Этот документ описывает фактическую структуру JSON, который возвращает команда `build` во фреймворке DQCR.

Основание для описания:

- сериализация `WorkflowModel.to_dict()` в [FTRepCBR.Workflow.FW/src/models/workflow.py](/Users/IgorShabanin/dev/DQCR%20Studio/FTRepCBR.Workflow.FW/src/models/workflow.py#L594)
- сериализация шагов в [FTRepCBR.Workflow.FW/src/models/step.py](/Users/IgorShabanin/dev/DQCR%20Studio/FTRepCBR.Workflow.FW/src/models/step.py#L46)
- сериализация SQL-модели в [FTRepCBR.Workflow.FW/src/models/sql_query.py](/Users/IgorShabanin/dev/DQCR%20Studio/FTRepCBR.Workflow.FW/src/models/sql_query.py#L124)
- сериализация параметров в [FTRepCBR.Workflow.FW/src/models/parameter.py](/Users/IgorShabanin/dev/DQCR%20Studio/FTRepCBR.Workflow.FW/src/models/parameter.py#L175)
- логика сборки workflow в [FTRepCBR.Workflow.FW/src/generation/DefaultBuilder.py](/Users/IgorShabanin/dev/DQCR%20Studio/FTRepCBR.Workflow.FW/src/generation/DefaultBuilder.py#L215)

## 1. Что возвращает `build`

Команда `build` работает в двух режимах:

- если указан `model_name`, на выходе один объект workflow
- если `model_name` не указан, на выходе объект вида `{ "<model_name>": <workflow>, ... }`

Это поведение задаётся в [FTRepCBR.Workflow.FW/src/cli.py](/Users/IgorShabanin/dev/DQCR%20Studio/FTRepCBR.Workflow.FW/src/cli.py#L114).

Ниже описан формат одного workflow-объекта.

## 2. Корневой объект workflow

Фактическая корневая схема:

```json
{
  "model_name": "string",
  "model_path": "string",
  "target_table": {},
  "settings": {
    "workflow_template": "string|null",
    "materialization_map": {},
    "folder_contexts": {}
  },
  "config": {},
  "steps": [],
  "tools": [],
  "project_name": "string",
  "project_properties": {},
  "context_name": "string|null",
  "all_contexts": {},
  "folders": {}
}
```

### Поля верхнего уровня

`model_name`

- Имя модели.
- Берётся из аргумента `build(..., model_name, ...)`.

`model_path`

- Абсолютный или относительный путь до директории модели в проекте.
- Сериализуется как строка из `Path`.

`target_table`

- Описание целевой таблицы модели.
- Формируется из `target_table.yml` или эквивалентной модели целевой таблицы.

`settings`

- Технический блок настроек workflow.
- В текущей реализации почти всегда присутствует, но по умолчанию содержит пустые словари.

`config`

- Эффективная workflow-конфигурация модели после мерджа `model.yml` и folder configs.
- Это не runtime-состояние, а отражение конфигурации, которая участвовала в построении.

`steps`

- Список шагов workflow в порядке, который отдаёт `WorkflowGraph`.
- Включает не только SQL-шаги, но и parameter-steps.
- Может включать дополнительные шаги для материализованных CTE.

`tools`

- Список инструментов генерации для активного контекста.
- Обычно что-то вроде `["oracle", "adb", "postgresql"]`, но зависит от context config.

`project_name`

- Имя проекта.

`project_properties`

- Словарь project properties.
- Сначала заполняется `default_value` из template properties, затем переопределяется значениями из `project.yml`.

`context_name`

- Имя активного контекста сборки.
- Если `build` вызван без `-c`, значение всё равно может быть `"default"` или текущее значение билдера, но сами шаги при этом могут быть развёрнуты по нескольким контекстам.

`all_contexts`

- Словарь всех контекстов проекта.
- Нужен для понимания того, какие contexts вообще существуют и какими flags/constants/tools они обладают.

`folders`

- Сводная карта папок workflow.
- Для каждой папки хранит контексты, materialization и folder macros `pre/post`.

## 3. Важное расхождение с документацией

В пользовательской документации JSON показан с полем `graph`, но текущий `WorkflowModel.to_dict()` поле `graph` не сериализует.

То есть:

- `graph` реально создаётся в билдере
- `steps` реально берутся из `graph`
- но в итоговый JSON сам объект графа не попадает

Это видно из:

- создание graph: [FTRepCBR.Workflow.FW/src/generation/DefaultBuilder.py](/Users/IgorShabanin/dev/DQCR%20Studio/FTRepCBR.Workflow.FW/src/generation/DefaultBuilder.py#L377)
- сериализация workflow без `graph`: [FTRepCBR.Workflow.FW/src/models/workflow.py](/Users/IgorShabanin/dev/DQCR%20Studio/FTRepCBR.Workflow.FW/src/models/workflow.py#L594)

## 4. Блок `target_table`

Схема:

```json
{
  "name": "string",
  "context": "string",
  "schema": "string|null",
  "attributes": [],
  "primary_keys": [],
  "description": "string"
}
```

### Поля

`name`

- Имя целевой таблицы.

`context`

- Контекст таблицы.
- По умолчанию `"all"`.

`schema`

- Имя схемы БД.

`attributes`

- Список атрибутов целевой таблицы.

`primary_keys`

- Список имён атрибутов, которые определены как primary key.
- Это производное поле, вычисляется из `attributes`.

`description`

- Добавляется только если непустое.

### Элемент `target_table.attributes[]`

Схема атрибута:

```json
{
  "name": "string",
  "domain_type": "string",
  "required": true,
  "is_key": false,
  "constraints": [],
  "description": "string",
  "distribution_key": 1,
  "partition_key": 1,
  "default_value": "string"
}
```

### Значение полей атрибута

`name`

- Имя колонки.

`domain_type`

- Логический тип данных, например `string`, `number`, `date`.

`required`

- Обязательность атрибута.

`is_key`

- Признак, что атрибут участвует в ключе materialization-логики.

`constraints`

- Ограничения, например `PRIMARY_KEY`, `FOREIGN_KEY`, `NOT_NULL`.

`description`

- Текстовое описание колонки.

`distribution_key`

- Номер ключа распределения для MPP-систем.

`partition_key`

- Номер ключа партиционирования.

`default_value`

- Значение по умолчанию.
- Появляется только если явно задано.

## 5. Блок `settings`

Схема:

```json
{
  "workflow_template": "string|null",
  "materialization_map": {},
  "folder_contexts": {}
}
```

### Поля

`workflow_template`

- Имя template для workflow engine.
- В обычном `build` часто равно `null`.

`materialization_map`

- Карта materialization-правил.
- В текущем коде обычно пустой объект.

`folder_contexts`

- Карта контекстов по папкам.
- В текущем коде обычно пустой объект.

## 6. Блок `config`

`config` сериализует эффективный `WorkflowConfig`, то есть именно ту конфигурацию, которая реально участвовала в сборке.

Схема:

```json
{
  "template": "string",
  "description": "string",
  "folders": {},
  "cte": {},
  "pre": [],
  "post": []
}
```

### Поля

`template`

- Имя workflow template, если задано.

`description`

- Описание workflow.

`folders`

- Конфигурации папок.

`cte`

- Глобальная конфигурация материализации CTE.

`pre`

- Макросы, выполняемые до основного содержимого workflow.

`post`

- Макросы, выполняемые после основного содержимого workflow.

### `config.folders.<folder_name>`

Схема конфигурации папки:

```json
{
  "materialized": "string",
  "enabled": {
    "contexts": [],
    "conditions": {}
  },
  "description": "string",
  "queries": {},
  "cte": {},
  "pre": [],
  "post": []
}
```

### Поля конфигурации папки

`materialized`

- Materialization по умолчанию для SQL в папке.

`enabled`

- Правило включения папки.
- Содержит:
  - `contexts`: список контекстов, в которых папка активна
  - `conditions`: условия по flags/constants

`queries`

- Переопределения для конкретных SQL-файлов внутри папки.

`cte`

- Настройки материализации CTE на уровне папки.

`pre`, `post`

- Имена folder macros, которые могут модифицировать набор шагов.

### `config.folders.<folder>.queries.<query_name>`

Схема:

```json
{
  "enabled": {
    "contexts": [],
    "conditions": {}
  },
  "materialized": "string",
  "description": "string",
  "attributes": [],
  "cte": {},
  "cte_queries": {}
}
```

### Поля query config

`enabled`

- Локальное правило включения запроса.

`materialized`

- Materialization конкретного запроса.
- Имеет приоритет над папкой.

`description`

- Текстовое описание шага.

`attributes`

- Дополнительное описание атрибутов результата SQL.

`cte`

- Общая конфигурация материализации CTE для запроса.

`cte_queries`

- Конфигурации конкретных CTE по имени.

### `cte` и `cte_queries`

Эти блоки используют один и тот же формат:

```json
{
  "cte_materialization": "string",
  "by_context": {
    "default": "string"
  },
  "by_tool": {
    "oracle": "string"
  },
  "cte_queries": {
    "cte_name": {}
  },
  "attributes": []
}
```

### Смысл полей

`cte_materialization`

- Базовый тип materialization для CTE.
- Часто `ephemeral`, `insert_fc`, `upsert_fc` и т.д.

`by_context`

- Переопределение materialization по контексту.

`by_tool`

- Переопределение materialization по tool.

`cte_queries`

- Вложенные настройки для конкретных CTE.

`attributes`

- Атрибуты результирующей CTE-таблицы, если CTE материализуется отдельно.

## 7. Блок `steps`

`steps` формируется из двух источников:

- parameter steps из `_build_param_steps(...)`
- SQL steps из `_build_sql_steps(...)`

При этом:

- шаги могут разворачиваться по контекстам
- SQL с `cte_materialization != ephemeral` может породить дополнительные CTE steps
- folder macros могут добавлять новые шаги до финального разрешения зависимостей

Схема шага:

```json
{
  "step_id": "string",
  "name": "string",
  "folder": "string",
  "full_name": "string",
  "step_type": "sql|param|sync_point|loop|end_loop",
  "step_scope": "flags|pre|params|sql|post|...",
  "sql_model": {},
  "param_model": {},
  "dependencies": [],
  "context": "string",
  "is_ephemeral": false,
  "enabled": true,
  "asynch": false,
  "loop_step_ref": "string|null",
  "tools": []
}
```

### Поля шага

`step_id`

- Технический идентификатор шага.
- Для SQL формируется примерно как `sql_<folder>_<query>[_<context>]`.
- Для parameter-step как `param_<parameter>[_<context>]`.

`name`

- Короткое имя шага.

`folder`

- Папка внутри `SQL/`.
- Для parameter-step обычно пустая строка.

`full_name`

- Полное имя шага.
- Для SQL-шагов обычно имеет вид `<folder>/<query>_<context>/sql` или `<query>_<context>`.
- Для parameter-step обычно `param_<name>[_<context>]`.

`step_type`

- Тип шага.
- В текущем build реально используются в основном:
  - `sql`
  - `param`
- Значения `sync_point`, `loop`, `end_loop` предусмотрены моделью, но не являются базовой частью стандартной сериализации SQL/param шагов.

`step_scope`

- Логическая зона шага.
- Для SQL-шагов обычно `sql`.
- Для параметров:
  - `flags`, если `domain_type == bool`
  - `params` для остальных параметров
- Дополнительные значения вроде `pre` и `post` могут появиться, если их создают folder macros.

`sql_model`

- Заполнен только у SQL-шагов.

`param_model`

- Заполнен только у parameter-step.

`dependencies`

- Список `full_name` шагов, от которых зависит текущий шаг.
- Зависимости выставляются после применения folder macros.

`context`

- Контекст конкретного шага.
- Встречаются значения `all`, `default`, `vtb` и т.д.

`is_ephemeral`

- Признак, что SQL-шаг не должен материализоваться как отдельный SQL-объект.

`enabled`

- Runtime-признак включённости шага.
- По умолчанию `true`.

`asynch`

- Признак асинхронного выполнения.
- По умолчанию `false`.

`loop_step_ref`

- Ссылка на loop-step, если шаг относится к циклу.
- Обычно `null`.

`tools`

- Ограничение tools только для этого шага.
- Если не задано, поле может быть `null`.

## 8. Блок `sql_model` внутри шага

Схема:

```json
{
  "name": "string",
  "path": "string",
  "source_sql": "string",
  "materialization": "string",
  "context": "string",
  "metadata": {},
  "prepared_sql": {},
  "rendered_sql": {},
  "attributes": [],
  "cte_materialization": "string|null",
  "cte_config": {},
  "cte_table_names": {},
  "target_table": "string",
  "description": "string"
}
```

### Поля

`name`

- Имя SQL-файла без расширения.

`path`

- Путь до исходного `.sql` файла.

`source_sql`

- Исходное содержимое SQL-файла.

`materialization`

- Итоговый тип материализации для этого SQL.
- Вычисляется каскадно: folder config -> query config -> inline config.

`context`

- Контекст, к которому относится эта SQL-модель.

`metadata`

- Результат SQL-парсинга.

`prepared_sql`

- SQL после подстановки параметров и подготовки под конкретный tool, но до финальной materialization-обвязки.
- Формат: `{ "<tool>": "<sql>" }`.

`rendered_sql`

- Финальный SQL после materialization renderer.
- Формат: `{ "<tool>": "<sql>" }`.

`attributes`

- Атрибуты результата SQL.
- Формируются из metadata aliases и обогащаются config/inline-описанием.

`cte_materialization`

- Краткое поле с дефолтной materialization для CTE.
- По сути вычисляется из `cte_config`.

`cte_config`

- Полная конфигурация CTE для данного SQL.

`cte_table_names`

- Словарь имён физических таблиц для материализованных CTE.
- Появляется, когда фреймворк создаёт отдельные CTE steps.

`target_table`

- Имя target table, если оно уже вычислено и заполнено.
- В текущем коде часто пустая строка.

`description`

- Описание SQL-шагa.
- Добавляется только если непустое.

### `sql_model.metadata`

Схема:

```json
{
  "parameters": [],
  "tables": {},
  "aliases": [],
  "cte": {},
  "functions": [],
  "model_refs": {},
  "workflow_refs": {},
  "inline_query_config": {},
  "inline_cte_configs": {},
  "inline_attr_configs": {}
}
```

### Поля metadata

`parameters`

- Список параметров, найденных в `{{ ... }}`.

`tables`

- Карта таблиц, найденных в `FROM` и `JOIN`.
- Формат элемента:

```json
{
  "table_name": {
    "alias": "string",
    "is_variable": true,
    "is_cte": false
  }
}
```

`aliases`

- Список алиасов/полей, найденных в SQL.
- Конкретная форма зависит от SQL parser.

`cte`

- Карта CTE.
- Для каждой CTE сериализуются:
  - `source_tables`
  - `source_ctes`

`functions`

- Список SQL-функций, найденных парсером.

`model_refs`

- Ссылки вида `_m.*`.

`workflow_refs`

- Ссылки вида `_w.*`.

`inline_query_config`

- Inline-конфиг запроса, извлечённый из SQL-комментариев/директив.

`inline_cte_configs`

- Inline-конфиги CTE.

`inline_attr_configs`

- Inline-конфиги атрибутов результата.

## 9. Блок `param_model` внутри шага

Схема:

```json
{
  "name": "string",
  "domain_type": "string",
  "description": "string",
  "attributes": [],
  "values": {},
  "source_sql": "string|null",
  "prepared_sql": {},
  "rendered_sql": {}
}
```

### Поля

`name`

- Имя параметра.

`domain_type`

- Тип параметра, например:
  - `bool`
  - `date`
  - `string`
  - `sql.condition`
  - `sql.identifier`
  - `record`
  - `array`

`description`

- Описание параметра.

`attributes`

- Описание структуры complex-параметров (`record`, `array`).
- Часто список объектов вида `{ "name": "...", "type": "..." }`.

`values`

- Значения параметра по контекстам.
- Формат:

```json
{
  "all": {
    "type": "static|dynamic",
    "value": "..."
  },
  "vtb": {
    "type": "static|dynamic",
    "value": "..."
  }
}
```

`source_sql`

- Исходный SQL для dynamic-параметра.
- В текущей сериализации часто `null`, даже если сам `value` является SQL.

`prepared_sql`

- Подготовленный SQL по tools.
- Для статических параметров может быть пустой строкой по каждому tool.

`rendered_sql`

- Финальный SQL по tools.
- Для статических параметров фреймворк всё равно может построить SQL вида `SELECT '<value>' as <param_name>`.

## 10. Блок `all_contexts`

Схема:

```json
{
  "default": {
    "name": "default",
    "project": "string",
    "tools": [],
    "flags": {},
    "constants": {},
    "cte": {}
  }
}
```

### Поля контекста

`name`

- Имя контекста.

`project`

- Наименование клиентского проекта для данного контекста.

`tools`

- Список tools, доступных в контексте.

`flags`

- Флаги контекста.

`constants`

- Константы контекста.

`cte`

- Контекстные настройки материализации CTE.

## 11. Блок `folders`

Этот блок строится не из файлов напрямую, а как сводка по всем папкам, обнаруженным в шагах workflow, плюс по их folder macros.

Схема:

```json
{
  "": {
    "name": "",
    "short_name": "",
    "enabled": true,
    "contexts": [],
    "materialized": "string|null",
    "pre": [],
    "post": []
  },
  "001_Load": {
    "name": "001_Load",
    "short_name": "001_Load",
    "enabled": true,
    "contexts": [],
    "materialized": "string|null",
    "pre": [],
    "post": []
  }
}
```

### Поля

`name`

- Полный путь папки внутри `SQL`.

`short_name`

- Последний сегмент пути.

`enabled`

- Включена ли папка для активного `context_name`.

`contexts`

- Контексты, для которых папка потенциально активна.

`materialized`

- Материализация по умолчанию для папки.

`pre`, `post`

- Имена folder macros.

## 12. Как появляются шаги в `steps`

### Parameter steps

Формируются из всех параметров модели:

- если у параметра нет `values`, шаг не создаётся
- если у параметра есть контекст `all`, он может развернуться в несколько контекстных шагов
- для `bool` параметров `step_scope = "flags"`
- для остальных параметров `step_scope = "params"`

Источник: [FTRepCBR.Workflow.FW/src/generation/DefaultBuilder.py](/Users/IgorShabanin/dev/DQCR%20Studio/FTRepCBR.Workflow.FW/src/generation/DefaultBuilder.py#L1284)

### SQL steps

Для каждого `*.sql`:

- определяется folder и query name
- проверяются `enabled` на уровне folder и query
- рассчитываются контексты шага
- вычисляется effective materialization
- строятся `prepared_sql` и затем `rendered_sql`
- при необходимости добавляются отдельные CTE steps

Источник: [FTRepCBR.Workflow.FW/src/generation/DefaultBuilder.py](/Users/IgorShabanin/dev/DQCR%20Studio/FTRepCBR.Workflow.FW/src/generation/DefaultBuilder.py#L932)

### CTE steps

Если для CTE материализация не `ephemeral`, билдер может создать отдельный SQL-step для каждой материализуемой CTE.

Признаки такого шага:

- `step_type = "sql"`
- `full_name` имеет вид `<folder>/<query>/cte/<cte_name>`
- основной шаг получает зависимость от этих CTE steps

## 13. Порядок и зависимости

Важно понимать:

- JSON не содержит объект `graph`
- но порядок элементов в `steps` уже отражает граф выполнения
- `dependencies` содержат явные связи между шагами через `full_name`

Следовательно, для внешнего потребителя JSON `steps + dependencies` достаточно, чтобы восстановить DAG, даже без отдельного `graph`.

## 14. Что важно учитывать при интеграции

### 1. Один и тот же SQL может появиться несколько раз

Причины:

- разворот по нескольким контекстам
- материализованные CTE

Поэтому нельзя считать, что `name` шага уникален. Надёжнее использовать `step_id` или `full_name`.

### 2. `context_name` на верхнем уровне не описывает контекст каждого шага

Если `build` вызван без `-c`, один workflow может содержать шаги сразу для нескольких контекстов.

Надо смотреть именно на `steps[].context`.

### 3. `config` и `folders` это разные уровни

`config`

- описание конфигурации, пришедшей из YAML и inline-настроек

`folders`

- runtime-сводка по папкам, которые реально попали в workflow

### 4. `prepared_sql` и `rendered_sql` не одно и то же

`prepared_sql`

- SQL после подстановки параметров/макросов, но до конечной materialization-обвязки

`rendered_sql`

- итоговый SQL для конкретного tool

### 5. Sample JSON в репозитории частично устарел

Файл `workflow sample.json` содержит поля:

- `sql_objects`
- `sql_object_key`

Но текущие `WorkflowModel.to_dict()` и `WorkflowStepModel.to_dict()` таких полей уже не сериализуют.

Поэтому ориентироваться на sample как на единственный источник схемы нельзя. Надёжнее опираться на текущий код сериализации.

## 15. Краткая практическая схема

Если вам нужен минимум для парсинга результата `build`, обычно достаточно следующей модели:

```json
{
  "model_name": "string",
  "target_table": {
    "name": "string",
    "schema": "string|null",
    "attributes": [],
    "primary_keys": []
  },
  "steps": [
    {
      "step_id": "string",
      "full_name": "string",
      "step_type": "sql|param",
      "step_scope": "string",
      "context": "string",
      "dependencies": [],
      "sql_model": {},
      "param_model": {}
    }
  ],
  "all_contexts": {},
  "folders": {}
}
```

Но если JSON используется для полноценной генерации, визуализации lineage или повторного исполнения, лучше поддерживать весь набор корневых полей.
