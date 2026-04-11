# Концепция реализации для AI-агента: развитие IDE на базе нового FW payload

Дата: 11 апреля 2026

## Как пользоваться этим документом

Этот документ нужен как единая точка входа для `Codex`, который будет развивать IDE на базе нового `FW workflow payload`.

Порядок работы:
- сначала прочитать раздел "Маршрут чтения";
- затем использовать раздел "Концепция" как продуктовую рамку;
- потом идти по backlog фазами, без пересборки объема задач на лету;
- запускать нового агента по `system prompt` из этого документа;
- после завершения каждой фазы обновлять код, тесты и документацию синхронно.

## Назначение документа

Цель документа: превратить анализ нового FW payload в исполнимую программу работ для AI-агента.

Целевой исполнитель:
- `Codex`, работающий внутри этого репозитория и использующий локальный код как основной источник истины.

Базовые опорные материалы:
- [FW_WORKFLOW_STRUCTURE_UI_IMPROVEMENTS.md](</Users/IgorShabanin/dev/DQCR Studio/Docs/FW_WORKFLOW_STRUCTURE_UI_IMPROVEMENTS.md>)
- [PromptGen.md](</Users/IgorShabanin/Downloads/PromptGen.md>)

## Концепция

Текущая IDE в основном опирается на `folder lineage`, workflow cache status и ограниченный набор metadata из FW. Новый payload уже содержит существенно более богатую execution-модель: шаги, зависимости, контексты, tool-specific ветвление, SQL metadata, inline-конфиги и признаки деградации cache. Это позволяет перевести интерфейс из режима "граф папок и fallback-помощник" в режим `execution-aware IDE`.

Целевая UX-модель:
- `Execution graph`: отображение реального step-level workflow, а не только порядка папок.
- `Context/tool-aware inspector`: интерфейс понимает, что один и тот же workflow ведет себя по-разному в разных `context` и `tool`.
- `SQL intelligence`: IDE показывает не только исходный SQL, но и `prepared/rendered` версии, refs, aliases, tables и inline-конфиги.
- `CTE/ref navigation`: пользователь может переходить по `_w.*`, `_m.*`, CTE и derived table mapping.
- `Cache quality awareness`: система явно показывает, полноценные ли данные использует IDE, либо интерфейс работает в `stale/fallback` режиме.

Что уже можно реализовать на текущем payload без расширения FW:
- step-level execution graph на основе `steps[]`, `dependencies`, `step_scope`, `context`, `tools`;
- step inspector на базе `sql_model`, `param_model`, `metadata`, `cte_table_names`;
- context/tool фильтрацию и подсветку условной активации;
- улучшенный UX деградации cache на вкладках lineage/parameters/validate.

Что требует расширения backend/API или прокидывания дополнительных FW полей:
- стабильная версия контракта payload;
- lightweight API для шагов без тяжелых SQL полей;
- отдача `graph`, `template`, `sql_objects`, если они доступны в FW output;
- diagnostics endpoint для покрытия payload и причин деградации;
- отложенная загрузка тяжелых SQL-артефактов по `step_id`.

## Маршрут чтения

С чего агенту начинать исследование:

1. [FW_WORKFLOW_STRUCTURE_UI_IMPROVEMENTS.md](</Users/IgorShabanin/dev/DQCR Studio/Docs/FW_WORKFLOW_STRUCTURE_UI_IMPROVEMENTS.md>)
Причина: базовый анализ того, какие новые данные появились в FW payload и какие UI/API возможности из этого следуют.

2. [SYSTEM_REFERENCE.md](</Users/IgorShabanin/dev/DQCR Studio/Docs/SYSTEM_REFERENCE.md>)
Причина: общая карта продукта, REST API, workflow cache, файловая структура и принятые системные инварианты.

3. [SQL_EDITOR_UI_INTERFACE.md](</Users/IgorShabanin/dev/DQCR Studio/Docs/SQL_EDITOR_UI_INTERFACE.md>)
Причина: текущая модель UI SQL Editor и связанные ожидания по поведению IDE.

4. [backend/app/routers/projects.py](</Users/IgorShabanin/dev/DQCR Studio/backend/app/routers/projects.py>)
Причина: главный слой, где workflow payload преобразуется в API для lineage, autocomplete, model object, config chain и workflow status.

5. [backend/app/services/fw_service.py](</Users/IgorShabanin/dev/DQCR Studio/backend/app/services/fw_service.py>)
Причина: точка интеграции с FW CLI, нормализация payload и контур работы с workflow build.

6. [frontend/src/api/projects.ts](</Users/IgorShabanin/dev/DQCR Studio/frontend/src/api/projects.ts>)
Причина: текущий frontend-контракт API, который придется расширять для step-level execution и diagnostics.

7. [frontend/src/features/lineage/LineageScreen.tsx](</Users/IgorShabanin/dev/DQCR Studio/frontend/src/features/lineage/LineageScreen.tsx>)
Причина: текущая реализация lineage-экрана, от которой надо эволюционировать к execution-aware UI.

8. [FTRepCBR.Workflow.FW/src/models/workflow_new.py](</Users/IgorShabanin/dev/DQCR Studio/FTRepCBR.Workflow.FW/src/models/workflow_new.py>)
Причина: целевая доменная модель workflow в FW, включая шаги, folders, contexts, tools, graph и template.

9. [FTRepCBR.Workflow.FW/src/parsing/sql_metadata.py](</Users/IgorShabanin/dev/DQCR Studio/FTRepCBR.Workflow.FW/src/parsing/sql_metadata.py>)
Причина: структура SQL metadata, которую IDE должна научиться визуализировать и использовать для navigation/intelligence.

Дополнительные файлы для адресной проверки:
- [backend/tests/test_projects_api.py](</Users/IgorShabanin/dev/DQCR Studio/backend/tests/test_projects_api.py>)
Причина: текущие ожидаемые контракты API и полезные fixture-примеры workflow payload.

- [projects/rf110new/.dqcr_workflow_cache/RF110RestTurnReg.json](</Users/IgorShabanin/dev/DQCR Studio/projects/rf110new/.dqcr_workflow_cache/RF110RestTurnReg.json>)
Причина: реальный payload, по которому можно проверять доступность step-level данных и реальную форму metadata.

- [workflow sample.json](</Users/IgorShabanin/dev/DQCR Studio/workflow sample.json>)
Причина: пример более полного payload, в котором уже видны поля, пока не доходящие до IDE API.

## Backlog реализации для AI-агента

Ниже дан decision-complete backlog. Агент не должен менять границы фаз или переставлять приоритеты без явной фиксации этого решения в документации.

### Фаза 1. Стабилизация контракта workflow payload

Статус фиксации: реализовано в backend/docs/tests 11 апреля 2026.
Что зафиксировано:
- backend нормализует legacy workflow cache до `workflow_schema_version = 1`;
- `payload_features[]` вычисляется автоматически и отдается через workflow API/meta;
- model-level workflow API и отдельный diagnostics endpoint возвращают contract diagnostics;
- backward compatibility с cache без version/features покрыта тестами.

#### Задача 1.1. Зафиксировать рабочий contract summary для IDE

Цель:
- описать минимально необходимый workflow contract, на который может опираться IDE.

Ожидаемый результат:
- в документации зафиксирован обязательный набор полей для `steps`, `sql_model`, `param_model`, `metadata`, `all_contexts`, `workflow meta`.

Затронутые подсистемы:
- docs
- backend API contract

Входные документы и файлы:
- [FW_WORKFLOW_STRUCTURE_UI_IMPROVEMENTS.md](</Users/IgorShabanin/dev/DQCR Studio/Docs/FW_WORKFLOW_STRUCTURE_UI_IMPROVEMENTS.md>)
- [SYSTEM_REFERENCE.md](</Users/IgorShabanin/dev/DQCR Studio/Docs/SYSTEM_REFERENCE.md>)
- [backend/app/services/fw_service.py](</Users/IgorShabanin/dev/DQCR Studio/backend/app/services/fw_service.py>)
- [FTRepCBR.Workflow.FW/src/models/workflow_new.py](</Users/IgorShabanin/dev/DQCR Studio/FTRepCBR.Workflow.FW/src/models/workflow_new.py>)

Критерии готовности:
- перечислены обязательные и опциональные поля payload;
- описаны допустимые режимы деградации (`ready/stale/building/error/missing`);
- зафиксировано, какие поля IDE считает критичными для execution UI.

#### Задача 1.2. Ввести версионирование и feature flags payload

Цель:
- убрать двусмысленность между версиями FW output.

Ожидаемый результат:
- payload или meta содержит `workflow_schema_version` и `payload_features`.

Затронутые подсистемы:
- backend
- docs
- tests

Входные документы и файлы:
- [backend/app/services/fw_service.py](</Users/IgorShabanin/dev/DQCR Studio/backend/app/services/fw_service.py>)
- [backend/app/services/workflow_cache_service.py](</Users/IgorShabanin/dev/DQCR Studio/backend/app/services/workflow_cache_service.py>)
- [backend/tests/test_fw_service.py](</Users/IgorShabanin/dev/DQCR Studio/backend/tests/test_fw_service.py>)
- [backend/tests/test_projects_api.py](</Users/IgorShabanin/dev/DQCR Studio/backend/tests/test_projects_api.py>)

Критерии готовности:
- backend умеет читать payload без версии и с версией;
- IDE может определить доступность advanced features без эвристик по полям;
- тесты покрывают backward compatibility.

#### Задача 1.3. Добавить coverage/diagnostics для payload

Цель:
- сделать качество payload наблюдаемым.

Ожидаемый результат:
- backend умеет вычислять, каких полей не хватает для execution UI и почему payload degraded.

Затронутые подсистемы:
- backend
- frontend
- docs

Входные документы и файлы:
- [backend/app/routers/projects.py](</Users/IgorShabanin/dev/DQCR Studio/backend/app/routers/projects.py>)
- [projects/rf110new/.dqcr_workflow_cache/RF110RestTurnReg.meta.json](</Users/IgorShabanin/dev/DQCR Studio/projects/rf110new/.dqcr_workflow_cache/RF110RestTurnReg.meta.json>)

Критерии готовности:
- backend возвращает диагностический summary для модели;
- summary различает `fallback`, `stale`, `missing heavy fields`, `legacy payload`.

### Фаза 2. Backend/API для step-level execution

Статус фиксации: реализовано в backend/frontend API types/tests/docs 11 апреля 2026.
Что зафиксировано:
- добавлен `GET /projects/{project_id}/models/{model_id}/workflow/graph` (step-level nodes/edges/summary);
- добавлен lightweight index `GET /projects/{project_id}/models/{model_id}/workflow/steps`;
- добавлен heavy step endpoint `GET /projects/{project_id}/models/{model_id}/workflow/steps/{step_id}`;
- graph response содержит `advanced` c passthrough полями `graph/template/sql_objects`, если они есть в payload;
- тесты покрывают `flags/pre/params/sql/post` и tool-specific шаги.

#### Задача 2.1. Спроектировать и реализовать step-level execution endpoint

Цель:
- дать frontend готовые `nodes/edges` по шагам workflow.

Ожидаемый результат:
- новый endpoint `GET /projects/{project_id}/models/{model_id}/workflow/graph`.

Затронутые подсистемы:
- backend
- frontend API types
- tests

Входные документы и файлы:
- [backend/app/routers/projects.py](</Users/IgorShabanin/dev/DQCR Studio/backend/app/routers/projects.py>)
- [frontend/src/api/projects.ts](</Users/IgorShabanin/dev/DQCR Studio/frontend/src/api/projects.ts>)
- [FTRepCBR.Workflow.FW/src/models/workflow_new.py](</Users/IgorShabanin/dev/DQCR Studio/FTRepCBR.Workflow.FW/src/models/workflow_new.py>)

Критерии готовности:
- endpoint возвращает шаги, связи и summary для execution graph;
- в payload узла есть `step_id`, `step_scope`, `step_type`, `context`, `tools`, `enabled`, `dependencies`;
- тесты покрывают SQL, param, pre, post и tool-specific шаги.

#### Задача 2.2. Ввести lightweight step index

Цель:
- не перегружать UI тяжелым JSON на первом запросе.

Ожидаемый результат:
- backend возвращает легковесное представление шагов отдельно от тяжелых SQL-артефактов.

Затронутые подсистемы:
- backend
- frontend API

Входные документы и файлы:
- [backend/app/routers/projects.py](</Users/IgorShabanin/dev/DQCR Studio/backend/app/routers/projects.py>)
- [frontend/src/api/projects.ts](</Users/IgorShabanin/dev/DQCR Studio/frontend/src/api/projects.ts>)

Критерии готовности:
- первый экран execution graph строится без загрузки `source_sql/prepared_sql/rendered_sql`;
- heavy payload запрашивается только при открытии step inspector.

#### Задача 2.3. Прокинуть недостающие advanced-поля из FW payload

Цель:
- приблизить IDE API к полной модели `workflow_new`.

Ожидаемый результат:
- backend начинает возвращать `graph`, `template`, `sql_objects` или их нормализованные производные, если они доступны во входном payload.

Затронутые подсистемы:
- backend
- docs
- tests

Входные документы и файлы:
- [FTRepCBR.Workflow.FW/src/models/workflow_new.py](</Users/IgorShabanin/dev/DQCR Studio/FTRepCBR.Workflow.FW/src/models/workflow_new.py>)
- [workflow sample.json](</Users/IgorShabanin/dev/DQCR Studio/workflow sample.json>)
- [backend/app/services/fw_service.py](</Users/IgorShabanin/dev/DQCR Studio/backend/app/services/fw_service.py>)

Критерии готовности:
- backend не теряет уже пришедшие advanced-поля;
- docs фиксирует, какие поля транслируются напрямую, а какие нормализуются.

### Фаза 3. Frontend execution UI

Статус фиксации: baseline реализации выполнен 11 апреля 2026.
Что внедрено:
- в lineage screen добавлен переключатель режима `Lineage / Execution` без удаления legacy folder-графа;
- execution режим использует `workflow/graph` как основной источник nodes/edges;
- detail panel для execution шага использует lazy-load heavy payload через `workflow/steps/{step_id}`;
- fallback banner адаптирован для execution payload fallback;
- execution graph получил scope-based styling (`flags/pre/params/sql/post`);
- добавлен tool overlay filter в execution toolbar (сохранение выбранного tool в localStorage);
- frontend API types расширены для `workflow/graph`, `workflow/steps`, `workflow/steps/{step_id}`.

#### Задача 3.1. Добавить новый режим или вкладку `Execution`

Цель:
- вывести step-level execution в отдельную пользовательскую поверхность.

Ожидаемый результат:
- в UI появляется режим `Execution`, не ломающий текущую вкладку `Линейность`.

Затронутые подсистемы:
- frontend navigation
- state management
- docs

Входные документы и файлы:
- [frontend/src/features/lineage/LineageScreen.tsx](</Users/IgorShabanin/dev/DQCR Studio/frontend/src/features/lineage/LineageScreen.tsx>)
- [SQL_EDITOR_UI_INTERFACE.md](</Users/IgorShabanin/dev/DQCR Studio/Docs/SQL_EDITOR_UI_INTERFACE.md>)

Критерии готовности:
- пользователь может открыть execution-представление отдельно от folder lineage;
- fallback-сценарии корректно обработаны;
- старое поведение lineage не регрессирует.

#### Задача 3.2. Построить execution graph

Цель:
- визуализировать шаги workflow, а не папки.

Ожидаемый результат:
- граф показывает `flags/pre/params/sql/post`, зависимости и status styling.

Затронутые подсистемы:
- frontend graph rendering
- UX

Входные документы и файлы:
- [frontend/src/features/lineage/LineageScreen.tsx](</Users/IgorShabanin/dev/DQCR Studio/frontend/src/features/lineage/LineageScreen.tsx>)
- [frontend/src/features/lineage/dagLayout.ts](</Users/IgorShabanin/dev/DQCR Studio/frontend/src/features/lineage/dagLayout.ts>)

Критерии готовности:
- шаги группируются и окрашиваются по scope;
- видны dependencies;
- tool-specific ветви и context-specific шаги не теряются.

#### Задача 3.3. Добавить context/tool overlays

Цель:
- сделать execution UI чувствительным к operational variation.

Ожидаемый результат:
- пользователь может фильтровать или сравнивать execution graph по `context` и `tool`.

Затронутые подсистемы:
- frontend controls
- graph filtering

Входные документы и файлы:
- [frontend/src/api/projects.ts](</Users/IgorShabanin/dev/DQCR Studio/frontend/src/api/projects.ts>)
- [projects/rf110new/.dqcr_workflow_cache/RF110RestTurnReg.json](</Users/IgorShabanin/dev/DQCR Studio/projects/rf110new/.dqcr_workflow_cache/RF110RestTurnReg.json>)

Критерии готовности:
- пользователь видит, какие шаги активны для выбранного context/tool;
- скрытые и disabled шаги не исчезают бесследно, а отображаются осознанно.

### Фаза 4. SQL / CTE / ref intelligence

Статус фиксации: baseline реализации выполнен 11 апреля 2026.
Что внедрено:
- execution step inspector отображает `source_sql`, `prepared_sql`, `rendered_sql`, `attributes`, `target_table`, `materialization`, `cte_materialization`;
- inspector показывает metadata-блоки `workflow_refs`, `model_refs`, `cte_table_names`, `inline_query_config`, `inline_cte_configs`, `inline_attr_configs`;
- lazy heavy loading сохранён через `workflow/steps/{step_id}`;
- добавлена базовая ref navigation: `_w.*` переводит к соответствующему step node в execution graph, `_m.*` переключает в Model Editor;
- unresolved refs не ломают UI и показываются через info toast.

#### Задача 4.1. Реализовать step inspector

Цель:
- показать полную техническую информацию по шагу без открытия сырого JSON.

Ожидаемый результат:
- inspector отображает `source_sql`, `prepared_sql`, `rendered_sql`, `attributes`, `target_table`, `materialization`.

Затронутые подсистемы:
- frontend detail panel
- backend heavy payload access

Входные документы и файлы:
- [frontend/src/api/projects.ts](</Users/IgorShabanin/dev/DQCR Studio/frontend/src/api/projects.ts>)
- [FTRepCBR.Workflow.FW/src/models/workflow_new.py](</Users/IgorShabanin/dev/DQCR Studio/FTRepCBR.Workflow.FW/src/models/workflow_new.py>)

Критерии готовности:
- inspector умеет работать для SQL и param шагов;
- heavy SQL загружается лениво;
- данные читаемы и структурированы по tool.

#### Задача 4.2. Реализовать ref navigation

Цель:
- сделать `_w.*`, `_m.*`, CTE и aliases навигационными объектами.

Ожидаемый результат:
- пользователь может перейти от шага к workflow query, target table, CTE или связанному SQL объекту.

Затронутые подсистемы:
- frontend navigation
- metadata rendering
- backend lookup helpers

Входные документы и файлы:
- [FTRepCBR.Workflow.FW/src/parsing/sql_metadata.py](</Users/IgorShabanin/dev/DQCR Studio/FTRepCBR.Workflow.FW/src/parsing/sql_metadata.py>)
- [backend/app/routers/projects.py](</Users/IgorShabanin/dev/DQCR Studio/backend/app/routers/projects.py>)

Критерии готовности:
- refs визуально различимы;
- клики переводят пользователя к релевантному объекту;
- broken refs не ломают UI и отображаются как unresolved.

#### Задача 4.3. Реализовать CTE and inline config explorer

Цель:
- сделать видимыми intermediate-конфигурации, которые раньше были скрыты в SQL metadata.

Ожидаемый результат:
- UI показывает `cte_table_names`, `inline_query_config`, `inline_cte_configs`, `inline_attr_configs`.

Затронутые подсистемы:
- frontend inspector
- UX

Входные документы и файлы:
- [FTRepCBR.Workflow.FW/src/parsing/sql_metadata.py](</Users/IgorShabanin/dev/DQCR Studio/FTRepCBR.Workflow.FW/src/parsing/sql_metadata.py>)
- [projects/rf110new/.dqcr_workflow_cache/RF110RestTurnReg.json](</Users/IgorShabanin/dev/DQCR Studio/projects/rf110new/.dqcr_workflow_cache/RF110RestTurnReg.json>)

Критерии готовности:
- tool-specific CTE materialization видна пользователю;
- inline configs отделены от базового model/folder config и явно маркированы как inline.

### Фаза 5. Cache diagnostics и деградация UX

Статус фиксации: baseline реализации выполнен 11 апреля 2026.
Что внедрено:
- workflow cache состояния (`ready/stale/building/error/missing`) унифицированы в UX для `lineage`, `parameters`, `validate` через единый diagnostics panel;
- на frontend добавлен reusable `WorkflowDiagnosticsPanel` с причинами деградации и recovery hints по issue codes;
- `LineageScreen` использует model-level diagnostics endpoint (`workflow/diagnostics`);
- `ParametersScreen` и `ValidateScreen` показывают diagnostics по degraded моделям из project workflow status;
- diagnostics panel содержит coverage-сводку (steps/sql metadata/heavy SQL), чтобы пользователь видел степень деградации данных.

#### Задача 5.1. Унифицировать UX состояний cache

Цель:
- чтобы все workflow-зависимые экраны одинаково и честно объясняли качество данных.

Ожидаемый результат:
- общий UX-подход для `ready/stale/building/error/missing`.

Затронутые подсистемы:
- frontend lineage
- parameters
- validate
- shared UI

Входные документы и файлы:
- [frontend/src/features/lineage/LineageScreen.tsx](</Users/IgorShabanin/dev/DQCR Studio/frontend/src/features/lineage/LineageScreen.tsx>)
- [frontend/src/features/parameters/ParametersScreen.tsx](</Users/IgorShabanin/dev/DQCR Studio/frontend/src/features/parameters/ParametersScreen.tsx>)
- [frontend/src/features/validate/ValidateScreen.tsx](</Users/IgorShabanin/dev/DQCR Studio/frontend/src/features/validate/ValidateScreen.tsx>)

Критерии готовности:
- предупреждения не противоречат друг другу между вкладками;
- rebuilding и fallback-сценарии визуально согласованы;
- пользователю ясно, насколько trustworthy текущие данные.

#### Задача 5.2. Добавить diagnostics UI

Цель:
- сделать деградацию объяснимой, а не просто предупреждающей.

Ожидаемый результат:
- экран или panel с причинами degraded payload и советами по восстановлению.

Затронутые подсистемы:
- backend diagnostics endpoint
- frontend diagnostics panel

Входные документы и файлы:
- [backend/app/routers/projects.py](</Users/IgorShabanin/dev/DQCR Studio/backend/app/routers/projects.py>)
- [projects/rf110new/.dqcr_workflow_cache/RF110RestTurnReg.meta.json](</Users/IgorShabanin/dev/DQCR Studio/projects/rf110new/.dqcr_workflow_cache/RF110RestTurnReg.meta.json>)

Критерии готовности:
- UI показывает причину fallback;
- отображает, каких полей не хватает для advanced features;
- дает пользователю понятный next action, например `Rebuild cache`.

## Критерии приемки всего направления

Документ считается пригодным как стартовый артефакт для нового AI-агента, если по нему без чтения переписки понятно:
- что именно строим;
- почему execution-aware IDE важнее текущего folder lineage-only подхода;
- в каком порядке надо внедрять изменения;
- где лежат основные документы, API и кодовые entrypoints;
- какой prompt использовать для запуска агента;
- как определять завершенность по каждой фазе.

## System Prompt для запуска Codex

```md
## Role
Ты — Codex, AI-агент реализации внутри репозитория DQCR Studio. Ты выступаешь как инженер-исполнитель, который развивает IDE на базе нового FW workflow payload. Ты не пересобираешь продуктовую концепцию с нуля, а реализуешь уже зафиксированную программу работ.

## Context
Твоя задача — поэтапно превратить текущую IDE из folder-lineage интерфейса в execution-aware IDE. Основная опора — реальные данные FW payload, текущий backend/frontend код и существующая документация.

Перед началом работы обязательно прочитай:
- [FW_WORKFLOW_STRUCTURE_UI_IMPROVEMENTS.md](</Users/IgorShabanin/dev/DQCR Studio/Docs/FW_WORKFLOW_STRUCTURE_UI_IMPROVEMENTS.md>)
- [AI_AGENT_EXECUTION_CONCEPT.md](</Users/IgorShabanin/dev/DQCR Studio/Docs/AI_AGENT_EXECUTION_CONCEPT.md>)
- [SYSTEM_REFERENCE.md](</Users/IgorShabanin/dev/DQCR Studio/Docs/SYSTEM_REFERENCE.md>)
- [SQL_EDITOR_UI_INTERFACE.md](</Users/IgorShabanin/dev/DQCR Studio/Docs/SQL_EDITOR_UI_INTERFACE.md>)
- [backend/app/routers/projects.py](</Users/IgorShabanin/dev/DQCR Studio/backend/app/routers/projects.py>)
- [backend/app/services/fw_service.py](</Users/IgorShabanin/dev/DQCR Studio/backend/app/services/fw_service.py>)
- [frontend/src/api/projects.ts](</Users/IgorShabanin/dev/DQCR Studio/frontend/src/api/projects.ts>)
- [frontend/src/features/lineage/LineageScreen.tsx](</Users/IgorShabanin/dev/DQCR Studio/frontend/src/features/lineage/LineageScreen.tsx>)
- [FTRepCBR.Workflow.FW/src/models/workflow_new.py](</Users/IgorShabanin/dev/DQCR Studio/FTRepCBR.Workflow.FW/src/models/workflow_new.py>)
- [FTRepCBR.Workflow.FW/src/parsing/sql_metadata.py](</Users/IgorShabanin/dev/DQCR Studio/FTRepCBR.Workflow.FW/src/parsing/sql_metadata.py>)

## Task
Реализуй backlog из `AI_AGENT_EXECUTION_CONCEPT.md` строго фазами.

Порядок работы:
1. Сначала исследуй релевантный код и данные для выбранной фазы.
2. Затем зафиксируй, какие изменения нужны в backend, frontend, tests и docs.
3. После этого внеси изменения.
4. По завершении каждой фазы обнови документацию и тесты.

Приоритет фаз:
1. Стабилизация контракта workflow payload
2. Backend/API для step-level execution
3. Frontend execution UI
4. SQL/CTE/ref intelligence
5. Cache diagnostics и деградация UX

## Constraints
- Не меняй контракт workflow payload без явной фиксации этого изменения в документации.
- Не пропускай обновление тестов, если меняется API или пользовательское поведение.
- Не объединяй несколько фаз в одну без явного обоснования в документации.
- При неопределенности сначала исследуй репозиторий и текущий код, потом предлагай изменения.
- Если обнаружишь несовпадение между документацией и кодом, зафиксируй это и синхронизируй документы с фактическим поведением.
- Используй существующие patterns проекта, если нет достаточного основания для нового слоя абстракции.

## Format
В каждой рабочей сессии:
- сначала коротко опиши, какую фазу и какую задачу выполняешь;
- затем перечисли затронутые подсистемы;
- после реализации кратко опиши результат;
- явно укажи, какие тесты выполнены;
- отдельно зафиксируй обновленные документы.

Если задача не может быть завершена целиком:
- опиши blocker;
- перечисли, какие факты уже подтверждены;
- предложи минимальный следующий шаг.

## Self-check
Перед завершением каждой задачи проверь:
- соответствует ли изменение целевой execution-aware концепции;
- не сломан ли текущий lineage/fallback UX;
- обновлены ли tests и docs;
- не появились ли незафиксированные решения по контракту payload;
- достаточно ли информации, чтобы следующий агент мог продолжить работу без чтения переписки.
```

## Проверка документа после создания

Проверить обязательно:
1. Все ссылки кликабельны и ведут в существующие файлы.
2. Backlog покрывает backend, frontend, docs и tests.
3. `system prompt` не противоречит ограничениям репозитория и процессу работы агента.
4. Документ можно отдать новому агенту как единственный стартовый артефакт.

## Принятые допущения

- Целевой исполнитель этого документа: `Codex`.
- Документ должен быть самостоятельным и не зависеть от чтения переписки.
- В документ включен не только backlog, но и готовый `system prompt`.
- Новый документ является отдельным артефактом и не заменяет [FW_WORKFLOW_STRUCTURE_UI_IMPROVEMENTS.md](</Users/IgorShabanin/dev/DQCR Studio/Docs/FW_WORKFLOW_STRUCTURE_UI_IMPROVEMENTS.md>), а дополняет его как execution-oriented guide.
