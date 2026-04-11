# Анализ новой структуры FW и предложения по улучшению IDE/UI

Дата: 11 апреля 2026

## 1) Цель

Разобрать, какие новые данные появились в workflow payload FW, что уже можно использовать в IDE, и какие улучшения UI/API стоит внедрить в первую очередь.

## 2) Что изучено

Фактические payload и cache:
- `projects/rf110new/.dqcr_workflow_cache/RF110RestTurnReg.json`
- `projects/rf110new/.dqcr_workflow_cache/RF110RestTurnReg__default.json`
- `projects/rf110new/.dqcr_workflow_cache/RF110RestTurnReg__vtb.json`
- `projects/rf110new/.dqcr_workflow_cache/RF110RestTurnReg.meta.json`
- `workflow sample.json`

Модели и генерация в FW:
- `FTRepCBR.Workflow.FW/src/models/workflow_new.py`
- `FTRepCBR.Workflow.FW/src/models/sql_object.py`
- `FTRepCBR.Workflow.FW/src/models/context.py`
- `FTRepCBR.Workflow.FW/src/parsing/sql_metadata.py`
- `FTRepCBR.Workflow.FW/src/generation/DefaultBuilderNew.py`
- `FTRepCBR.Workflow.FW/src/generation/dependency_resolvers/naming_convention_new.py`
- `FTRepCBR.Workflow.FW/src/macros/main/folder_macro/synch_iter.py`

Текущая утилизация в backend/frontend IDE:
- `backend/app/routers/projects.py`
- `backend/app/services/fw_service.py`
- `frontend/src/features/lineage/LineageScreen.tsx`
- `frontend/src/features/lineage/components/FallbackBanner.tsx`

## 3) Какие возможности появились в данных FW

## 3.1 Шаги workflow стали богаче и ближе к execution-модели

В `steps[]` доступны поля, которых достаточно для построения execution-aware UI:
- `step_scope`: `flags | pre | params | sql | post`
    - `dependencies`: явные зависимости между шагами
- `context`: `all | default | vtb | ...`
- `tools`: ограничение шага по tool (например CTE-steps только для `adb/postgresql`)
- `is_ephemeral`, `enabled`, `asynch`, `loop_step_ref`
- `step_type`: уже сейчас встречаются `param/sql`, а код FW поддерживает также loop/end_loop макросы

По текущему payload `RF110RestTurnReg.json`:
- всего шагов: `20`
- по scope: `flags(1), pre(1), params(6), sql(11), post(1)`
- контексты в шагах: `all, default, vtb`

## 3.2 Для SQL шага появился практически полный набор артефактов

`sql_model` содержит:
- `source_sql`
- `prepared_sql` по tool (`oracle/adb/postgresql`)
- `rendered_sql` по tool
- `materialization`, `cte_materialization`, `cte_config`
- `cte_table_names` (резолв имён временных CTE-таблиц)
- `target_table`
- `attributes`
- `metadata` с семантикой SQL

Это уже позволяет строить IDE без повторного парсинга SQL в backend/UI.

## 3.3 SQL metadata стала пригодной для “умного” UI

В `sql_model.metadata` есть:
- `parameters`
- `tables` (alias/is_variable/is_cte)
- `aliases` (alias/source/expression)
- `cte`
- `functions`
- `model_refs`
- `workflow_refs`
- `inline_query_config`
- `inline_cte_configs`
- `inline_attr_configs`

Практический эффект: можно показать происхождение колонок, ссылки `_m/_w`, inline-конфиги и влияние materialization прямо в IDE.

## 3.4 Контекстная модель стала богаче

На верхнем уровне есть:
- `all_contexts` с `flags/constants/tools/cte`
- `project_properties`
- `folders` (включая `pre/post/materialized/contexts`)
- `settings/config` для workflow

Это дает базу для контекстно-зависимой визуализации и “почему шаг включён/выключен”.

## 3.5 Поддержка разных форматов payload в backend

`FWService._normalize_workflow_payload(...)` умеет принимать:
- payload напрямую с `steps`
- payload вида `{ "<ModelId>": {...} }`
- payload с единственным объектом внутри

Это снижает риск поломки IDE при вариациях output FW.

## 4) Важный gap: часть данных FW не доходит до IDE API

Есть рассинхрон между «полной» моделью FW и тем, что реально хранится/используется в IDE:
- В `workflow sample.json` есть `sql_objects`, но в текущем cache `RF110RestTurnReg.json` этого поля нет.
- В `workflow_new.py` модель содержит `graph` и `template`, но в текущем cache они отсутствуют.
- В backend сейчас используются в основном `steps`, `target_table`, `all_contexts`, часть `metadata`.

Вывод: потенциал новых данных выше, чем текущая утилизация в IDE.

## 5) Что уже можно улучшить в IDE прямо сейчас (без изменений FW)

1. Execution Graph (не только folder lineage)
- Строить DAG по `steps[].dependencies` и `step_scope`, а не только по папкам.
- Отдельные ноды для `pre/flags/params/post` и SQL.

2. Context/Tool overlay
- Переключатель контекста + фильтр tool.
- Подсветка шагов, активных только в выбранном context/tool.

3. SQL Intelligence Panel
- Для выбранного шага показывать `source/prepared/rendered` SQL по tool.
- Блоки `tables`, `aliases`, `model_refs`, `workflow_refs`, `inline_*`.

4. CTE Visibility
- Показывать CTE-цепочку и `cte_table_names`.
- Маркировать tool-specific CTE шаги (`tools != null`).

5. Data lineage по колонкам (MVP)
- Использовать `aliases + tables + workflow_refs` для «откуда взялось поле».

## 6) Что стоит добавить в backend/API для раскрытия полного потенциала

P0 (высокий приоритет):
1. Версионировать контракт workflow payload
- Добавить `workflow_schema_version` и `payload_features` в cache/meta.

2. Отдать execution-данные отдельным endpoint
- `GET /projects/{id}/models/{model}/workflow/graph` с готовыми `nodes/edges` по step-level.

3. Отдать “дешёвый индекс” шагов
- Endpoint с сокращенными данными шага (без больших SQL строк), чтобы быстрый UI не тянул огромный JSON.

P1:
4. Прокинуть `graph/template/sql_objects` (если есть в FW output)
- Сейчас часть информации теряется/не используется.

5. Добавить diagnostics endpoint
- Список отсутствующих полей ожидаемого контракта + причина fallback.

P2:
6. Инкрементальная загрузка тяжелых полей
- Отдельный endpoint для `source_sql/prepared/rendered` по `step_id`.

## 7) Предложенный roadmap UI

Этап 1 (быстрый эффект):
- Step-level Execution Graph.
- Context/Tool фильтры.
- Step details панель на основе текущих `sql_model + metadata`.

Этап 2:
- CTE Explorer и workflow_ref/model_ref navigation.
- Причины enable/disable по context/flags.

Этап 3:
- Колоночная lineage-карта.
- “Что изменится при смене контекста/tool” (impact preview).

## 8) Риски и ограничения

1. Размер payload
- `rendered_sql` и metadata могут быть большими; нужен lazy-load или lightweight индекс.

2. Неполный payload при fallback/stale
- Если `meta.status=stale` и `source=fallback`, часть шагов/полей может быть неполной.

3. Нестабильность формы output между версиями FW
- Нужны schema version + feature flags.

## 9) Конкретные продуктовые улучшения (список)

1. Новая вкладка `Execution` рядом с текущей `Линейность`.
2. Переключатель вида графа: `Folder graph` / `Step graph`.
3. Карточка шага: `scope`, `context`, `tools`, `dependencies`, `materialization`, `cte_table_names`.
4. Просмотр SQL по tool: `source/prepared/rendered` с diff между tools.
5. Инспектор refs: `_m.*` и `_w.*` (кликабельная навигация).
6. Инспектор inline-конфигов (`inline_query_config`, `inline_cte_configs`, `inline_attr_configs`).
7. Подсветка причин условной активации шага (flags/contexts).
8. Алерт качества cache: отдельно показывать `stale/error/missing` и степень деградации данных.
9. Экспорт execution graph в JSON/PNG.
10. API-метрика покрытия payload: какой % шагов содержит полный `sql_model`.

## 10) Резюме

FW payload действительно стал значительно богаче и уже содержит данные, достаточные для заметного скачка UX IDE: от "графа папок" к полноценному execution-aware интерфейсу.

Ключевой следующий шаг: поднять утилизацию уже доступных полей `steps/sql_model/metadata`, параллельно зафиксировать стабильный контракт (`schema_version`) и прокинуть недостающие части модели (`graph/template/sql_objects`) через API.

## 11) Contract summary для IDE (Phase 1 baseline)

Начиная с фазы 1 backend DQCR Studio нормализует workflow payload до единого IDE-контракта, даже если исходный cache был записан старой версией FW/backend.

### 11.1 Обязательные поля для execution-aware IDE

Верхний уровень payload:
- `workflow_schema_version`
- `payload_features[]`
- `steps[]`

Обязательный минимум для каждого `step`:
- `step_id`
- `step_scope`
- `step_type`
- `context`
- `enabled`
- `dependencies`

Для SQL-шага (`step_type=sql`) критичны:
- `sql_model`
- `sql_model.source_sql`
- `sql_model.prepared_sql`
- `sql_model.rendered_sql`
- `sql_model.metadata`

Для parameter-шага (`step_type=param`) критичен:
- `param_model`

### 11.2 Важные, но опциональные поля

Backend сохраняет и прокидывает как optional:
- `all_contexts`
- `folders`
- `project_properties`
- `target_table`
- `config`
- `settings`
- `graph`
- `template`
- `sql_objects`
- `sql_model.cte_table_names`
- `step.tools`

Отсутствие optional-полей не ломает базовый execution UI, но снижает качество инспекторов и навигации.

### 11.3 Версия и feature flags

Зафиксирован baseline:
- `workflow_schema_version = 1`

`payload_features[]` вычисляется backend автоматически и используется как capability-map вместо эвристик по отдельным полям. Среди поддерживаемых feature flags:
- `steps`
- `step_dependencies`
- `step_context`
- `step_tools`
- `param_model`
- `sql_model`
- `sql_source`
- `sql_prepared`
- `sql_rendered`
- `sql_metadata`
- `cte_table_names`
- `all_contexts`
- `folders`
- `project_properties`
- `graph`
- `template`
- `sql_objects`

### 11.4 Режимы деградации и diagnostics

IDE различает:
- `ready` — payload доступен и cache считается актуальным
- `stale` — используется сохранённый cache после неудачного rebuild
- `building` — rebuild в процессе
- `error` — cache недоступен и rebuild завершился ошибкой
- `missing` — cache ещё не существует

Model-level diagnostics теперь отдельно отмечает:
- `fallback_source`
- `stale_payload`
- `legacy_payload`
- `missing_heavy_fields`
- `contract_gaps`
- `workflow_missing`
- `workflow_error`

### 11.5 Новая backend surface

Помимо существующего `GET /projects/{project_id}/models/{model_id}/workflow`, backend теперь отдаёт отдельный summary:
- `GET /projects/{project_id}/models/{model_id}/workflow/diagnostics`

Оба endpoint возвращают:
- `workflow_schema_version`
- `payload_features`
- `diagnostics`

## 12) Step-level API (Phase 2)

Для execution-aware UI добавлены backend endpoint-ы, которые разделяют lightweight graph и heavy SQL payload:

- `GET /projects/{project_id}/models/{model_id}/workflow/graph`
  - возвращает `nodes/edges/summary` по шагам workflow;
  - каждый node содержит `step_id`, `step_scope`, `step_type`, `context`, `tools`, `enabled`, `dependencies`;
  - heavy SQL строки (`source/prepared/rendered`) не включаются;
  - дополнительно возвращается `advanced` с passthrough-полями `graph/template/sql_objects`, если они были в FW payload.

- `GET /projects/{project_id}/models/{model_id}/workflow/steps`
  - lightweight index шагов для быстрого открытия execution screen.

- `GET /projects/{project_id}/models/{model_id}/workflow/steps/{step_id}`
  - heavy details для step inspector;
  - содержит `sql_model.source_sql/prepared_sql/rendered_sql/metadata` и `param_model`, если применимо.
