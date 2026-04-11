# DQCR Studio: системная документация

## 1. Назначение

DQCR Studio - это файловая студия для разработки и сопровождения DQCR-проектов. Система объединяет:

- project hub для управления набором проектов;
- рабочую IDE-область для просмотра и редактирования проекта;
- backend API для работы с файлами, метаданными, workflow cache, validation и build;
- framework `FTRepCBR.Workflow.FW`, который выполняет build/validate и строит workflow-модель.

Главный архитектурный принцип: источником истины остается файловая структура проекта, а backend и frontend строят поверх нее вычисляемые представления и UI.

---

## 2. Верхнеуровневая архитектура

```text
Projects Hub / Workbench UI (React + Vite)
                  |
                  | HTTP + WebSocket
                  v
             Backend API (FastAPI)
                  |
                  | filesystem + fw2 CLI
                  v
     projects/*  +  FTRepCBR.Workflow.FW
```

### 2.1 Подсистемы

`frontend/`

- SPA-интерфейс;
- работает в двух режимах:
  - `hub mode`, когда проект не выбран;
  - `workbench mode`, когда открыт конкретный проект.

`backend/`

- файловый API;
- project metadata API;
- build/validate API;
- workflow cache orchestration;
- websocket endpoints.

`FTRepCBR.Workflow.FW/`

- framework CLI `fw2`;
- parsing, generation, validation, macros, materialization, workflow engines.

`projects/`

- рабочее хранилище проектов;
- здесь лежат исходники проектов, workflow cache и build/validation artifacts.

`infra/docker/`

- локальная инфраструктура запуска;
- backend, frontend, nginx.

`Docs/`

- инженерная документация;
- этот файл является текущим системным reference по решению.

---

## 3. Ключевые архитектурные идеи

### 3.1 Filesystem-first

Проект хранится как набор YAML и SQL файлов. Backend не использует БД для модели проекта.

Основные файлы проекта:

- `project.yml`
- `contexts/*.yml`
- `parameters/*.yml`
- `model/<ModelId>/model.yml`
- `model/<ModelId>/workflow/**` или `model/<ModelId>/SQL/**`
- `model/<ModelId>/parameters/*.yml`

### 3.2 Производные слои

Поверх файловой структуры backend поддерживает производные слои:

- workflow cache;
- lineage graph;
- config-chain;
- autocomplete metadata;
- model object representation;
- build/validation history в памяти процесса.

### 3.3 Framework-driven computation

Framework CLI `fw2` является вычислительным движком для:

- validation;
- generation/build;
- workflow model build.

Если framework payload недоступен, часть read-операций backend может обслужить через fallback parsing напрямую из файлов.

### 3.4 Hub-first UX

Текущее приложение больше не начинается сразу с открытого проекта. Если активный проект не выбран, пользователь работает через Project Hub:

- просмотр всех проектов;
- фильтрация и сортировка;
- создание;
- импорт;
- редактирование metadata;
- удаление.

После выбора проекта приложение переключается в workbench mode.

---

## 4. Runtime-модель

### 4.1 Frontend runtime

Технологии:

- React 18
- TypeScript
- Vite
- Zustand
- TanStack Query
- Monaco Editor
- React Flow
- xterm

Frontend использует:

- `localStorage` для части UI-состояния;
- `zustand/persist` для хранения `currentProjectId`;
- React Query для загрузки и инвалидации backend данных.

### 4.2 Backend runtime

Технологии:

- FastAPI
- Pydantic Settings
- ptyprocess
- Uvicorn

Backend отвечает за:

- маршрутизацию;
- защиту файловых операций;
- project registry;
- запуск framework CLI;
- выдачу read-model данных;
- хранение runtime history в памяти процесса.

### 4.3 Инфраструктура

Локальный compose поднимает:

- `backend` на `8000`
- `frontend` на `5173`
- `nginx` на `80`

Nginx используется как единая точка входа.

---

## 5. Доменная модель

### 5.1 Проект

В текущей версии проект описывается не только `id` и `name`, но и расширенными метаданными.

Поля project-level API:

- `id`
- `name`
- `description`
- `project_type`
- `source_type`
- `source_path`
- `availability_status`
- `visibility`
- `tags`
- `model_count`
- `folder_count`
- `sql_count`
- `modified_at`
- `cache_status`

### 5.2 Типы проектов

Поддерживаются 3 типа:

- `internal` - создан в workspace;
- `imported` - скопирован из внешнего каталога;
- `linked` - внешний каталог подключен без копирования.

### 5.3 Метаданные проекта

Для `internal` проекта metadata берется в первую очередь из `project.yml`.

Сейчас важные системные project properties хранятся в блоке `properties`:

- `dqcr_visibility`
- `dqcr_tags`
- также используются обычные `version` и `owner`

Для `imported` и `linked` проектов metadata хранится в registry.

### 5.4 Контексты

Контексты лежат в `contexts/*.yml`.

В UI для каждого контекста дополнительно читаются:

- `tools`
- `constants`
- `flags`

Если каталог контекстов отсутствует, backend возвращает `default`.

### 5.5 Модели

Модели лежат в `model/<ModelId>/`.

Backend и frontend поддерживают оба варианта размещения SQL:

- `workflow/`
- `SQL/`

Это важно для чтения проектов, подсчета объектов и fallback-логики.

На текущем состоянии системы модель можно создавать напрямую из UI без ручного создания каталогов. Backend для этого создает:

- каталог `model/<ModelId>/`
- файл `model/<ModelId>/model.yml`

с минимальным scaffold для `target_table` и `workflow`.

### 5.6 Параметры

Поддерживаются:

- global parameters: `parameters/*.yml`
- model-scoped parameters: `model/<ModelId>/parameters/*.yml`

Scope значения:

- `global`
- `model:<model_id>`

### 5.7 Workflow cache

Workflow cache находится внутри проекта:

- `.dqcr_workflow_cache/<model_id>.json`
- `.dqcr_workflow_cache/<model_id>.meta.json`

Этот слой производный и может быть rebuilt.

Начиная с Phase 1 backend нормализует cache к IDE-контракту:
- payload получает `workflow_schema_version` и `payload_features[]`;
- meta дополнительно хранит `diagnostics`;
- старые cache-файлы без этих полей читаются backward-compatible и считаются `legacy payload`.

### 5.8 Build и validation artifacts

Build artifacts:

- `<project>/.dqcr_builds/<build_id>/...`
- либо пользовательский `output_path/<build_id>/...`

Validation artifacts:

- `<project>/.dqcr_validation_runs/<run_id>/...`

---

## 6. Основные пользовательские сценарии

### 6.1 Вход в систему

Если `currentProjectId` отсутствует, frontend показывает Hub.

Если в `localStorage` есть `dqcr_last_project_id`, приложение пытается восстановить последний проект через `GET /projects/{project_id}`.

### 6.2 Работа с проектами через Hub

Hub поддерживает:

- просмотр grid/list;
- full-text search;
- фильтры по visibility/type/tag;
- сортировку;
- создание;
- импорт;
- редактирование metadata;
- удаление.

### 6.3 Открытие проекта

При выборе проекта:

- `projectStore` сохраняет `currentProjectId`;
- в `localStorage` пишется `dqcr_last_project_id`;
- активная вкладка переключается на `project`.

### 6.4 Работа в workbench

Workbench содержит вкладки:

- `project`
- `lineage`
- `model`
- `sql`
- `validate`
- `parameters`
- `build`
- `admin`

Во вкладке `lineage` поддерживаются два режима визуализации:
- `Lineage` (folder-level граф, legacy поведение);
- `Execution` (step-level граф на базе `workflow/graph` + lazy step inspector), включая scope-стили (`flags/pre/params/sql/post`) и tool overlay filter.

Execution inspector показывает heavy SQL-артефакты и metadata refs (`_w/_m`, `cte_table_names`, `inline_*`) по запросу `workflow/steps/{step_id}`.

Для всех workflow-зависимых экранов (`lineage`, `parameters`, `validate`) используется унифицированный diagnostics UX:
- общий формат отображения статуса cache;
- список причин деградации payload (`issues`);
- рекомендации по восстановлению;
- coverage-сводка полноты execution payload.

### 6.5 Создание модели

Создание модели теперь доступно из нескольких точек интерфейса:

- sidebar project tree;
- Project Info screen;
- Model Editor screen.

Во всех случаях используется единый диалог `ProjectStructureDialog`, а backend-операция выполняется через `POST /projects/{project_id}/files/model`.

### 6.6 Редактирование project.yml

Экран Project Info редактирует:

- `name`
- `description`
- `template`
- `version`
- `owner`
- custom properties

Сохранение выполняется как запись файла `project.yml` через Files API.

### 6.7 Редактирование metadata проекта

Hub-редактирование работает через отдельный metadata API:

- `PATCH /projects/{project_id}/metadata`

Для internal проекта backend синхронизирует metadata в `project.yml` и, при наличии записи registry, в registry entry.

### 6.8 SQL-автодополнение

Autocomplete для SQL больше не ограничивается параметрами и macro names. Backend возвращает:

- параметры;
- macros;
- config keys;
- objects.

`objects` включают:

- `target_table`
- `workflow_query`

и могут строиться как из workflow payload, так и из fallback model parsing.

### 6.9 Build / Validate

Build и validation по-прежнему запускаются из backend поверх framework CLI и попадают в in-memory history.

---

## 7. Backend: актуальная структура

### 7.1 `backend/app/main.py`

Назначение:

- создание FastAPI app;
- lifespan hook;
- CORS;
- request logging;
- health/readiness endpoints;
- global exception handlers;
- router registration.

### 7.2 `backend/app/core/`

`config.py`

- env configuration;
- важные переменные:
  - `API_PREFIX`
  - `PROJECTS_PATH`
  - `SECRET_KEY`
  - `FW_USE_CLI`
  - `FW_CLI_COMMAND`

`fs.py`

- `ensure_within_base`
- `resolve_project_path`

`project_registry.py`

- чтение и запись `.dqcr_projects_registry.json`;
- поддержка metadata:
  - `description`
  - `visibility`
  - `tags`

`logging.py`

- backend logging setup.

### 7.3 `backend/app/services/`

`fw_service.py`

- адаптер между backend и framework;
- load project/model;
- lineage;
- validation;
- generation;
- workflow build;
- error normalization.

`workflow_cache_service.py`

- read/write workflow cache;
- read/write meta;
- project/model workflow status aggregation.

`terminal_service.py`

- PTY sessions;
- `/bin/bash` shell for websocket terminal.

### 7.4 `backend/app/routers/`

`projects.py`

- основной доменный router;
- включает project CRUD, metadata update, contexts, workflow, parameters, lineage, config-chain, model object, build, validate, quickfix.

`files.py`

- файловый CRUD внутри проекта.

`admin.py`

- templates, rules, macros.

`ws.py`

- terminal/build/validation websocket endpoints.

---

## 8. Frontend: актуальная структура

### 8.1 Shell

`frontend/src/App.tsx`

- выбирает между двумя режимами:
  - hub mode;
  - workbench mode.

### 8.2 Project Hub

Новая отдельная feature-группа:

`frontend/src/features/hub/`

Содержит:

- `ProjectsHub.tsx`
- модальные окна:
  - `CreateProjectModal`
  - `EditProjectModal`
  - `DeleteProjectModal`
- таблицу/карточки;
- sidebar и toolbar фильтров;
- hooks:
  - `useProjects`
  - `useProjectFilters`

### 8.3 Project Info

Новая отдельная feature-группа:

`frontend/src/features/project/`

Содержит:

- `ProjectInfoScreen.tsx`
- cards и summary-компоненты;
- `useProjectInfo`
- проектные стили `project-info.css`

Этот экран агрегирует:

- `project.yml`
- tree проекта;
- contexts;
- parameters;
- workflow status

и строит обзорную страницу проекта.

### 8.4 Workbench features

`features/lineage/`

- lineage screen;
- dag layout;
- отдельные styles и helpers.

`features/model/`

- model editor;
- sync engine;
- YAML sync.

`features/sql/`

- SQL editor;
- autocomplete;
- object-aware autocomplete для target tables и workflow queries;
- preview build output;
- validation integration.

`features/parameters/`

- parameter management.

`features/build/`

- build execution and artifacts browsing.

`features/validate/`

- validation UI;
- quick fix;
- quick fix preview modal.

`features/admin/`

- admin UI.

### 8.5 Shared project structure actions

Появился общий компонент:

`frontend/src/shared/components/ProjectStructureDialog.tsx`

Он используется для операций:

- `rename`
- `delete`
- `new-file`
- `new-folder`
- `new-model`

### 8.6 Shared stores

`projectStore`

- хранит `currentProjectId`;
- persist middleware;
- при открытии проекта переключает активную вкладку на `project`.

`editorStore`

- активная вкладка;
- открытые файлы;
- dirty state;
- cursor state;
- navigation targets.

`uiStore`

- sidebar and bottom panel state;
- toast system;
- user role;
- user email;
- workflow cache status;
- last saved timestamp;
- initial model/parameter hints;
- dismissed warning flags.

`contextStore`

- active context;
- multi-context mode.

`validationStore`

- latest validation result.

---

## 9. Framework: роль в системе

### 9.1 Framework зоны

`FTRepCBR.Workflow.FW/src/parsing/`

- project/model/sql/parameter/context loading.

`FTRepCBR.Workflow.FW/src/models/`

- framework domain models.

`FTRepCBR.Workflow.FW/src/generation/`

- workflow build and generation logic.

`FTRepCBR.Workflow.FW/src/validation/`

- validation subsystem and report generation.

`FTRepCBR.Workflow.FW/src/macros/`

- macros, functions, materialization, engine-specific templates.

`FTRepCBR.Workflow.FW/src/config/`

- templates, tools, workflow engines registries.

### 9.2 CLI, которые важны для Studio

Ключевые вызовы:

- `fw2 validate <project_path> <model_id> -o <output_dir>`
- `fw2 generate <project_path> <model_id> -c <context> -w <engine> -o <output_dir>`

Поддерживаемые engine в backend:

- `dqcr`
- `airflow`
- `dbt`
- `oracle_plsql`

---

## 10. Проектная файловая структура

Типовая структура проекта:

```text
<project_id>/
  project.yml
  contexts/
    default.yml
    <context>.yml
  parameters/
    <global_param>.yml
  model/
    <ModelId>/
      model.yml
      parameters/
        <model_param>.yml
      workflow/
        01_stage/
          folder.yml
          001_main.sql
      SQL/
        01_stage/
          folder.yml
          001_main.sql
  .dqcr_workflow_cache/
    <ModelId>.json
    <ModelId>.meta.json
  .dqcr_builds/
    <build_id>/
  .dqcr_validation_runs/
    <run_id>/
```

### 10.1 Служебные каталоги

`.dqcr_workflow_cache/`

- кеш workflow payload и meta.
- обычно содержит:
  - `<ModelId>.json` или `<ModelId>__<context>.json` - вычисленный workflow payload, нормализованный до IDE contract (`workflow_schema_version`, `payload_features`);
  - `<ModelId>.meta.json` - статус (`ready/stale/building/error/missing`), `updated_at`, `error`, `source`, `workflow_schema_version`, `payload_features`, `diagnostics`.

`.dqcr_builds/`

- generated output.
- обычно содержит:
  - `<build_id>/...` - файлы результата generate/build;
  - `history.json` - история build-операций по проекту.

`.dqcr_validation_runs/`

- validation reports and artifacts.
- обычно содержит:
  - `<run_id>/<ModelId>_validation.json`
  - `<run_id>/<ModelId>_validation.html`

### 10.1.1 Когда эти каталоги наполняются

`.dqcr_workflow_cache/` обновляется при:

- создании/импорте/подключении проекта;
- изменении внутренних metadata проекта;
- изменении файлов проекта (save/create/rename/delete);
- изменении параметров проекта/модели (create/update/delete);
- сохранении model object (`PUT /projects/{project_id}/models/{model_id}`);
- явном rebuild (`POST /projects/{project_id}/models/{model_id}/workflow/rebuild`);
- ленивом автопостроении, когда cache отсутствует (например при `GET /projects/{project_id}/files/tree` и ряде workflow/autocomplete чтений).

`.dqcr_builds/` обновляется при:

- запуске build/generate (`POST /projects/{project_id}/build` и связанные use-cases),
- записи/обновлении `history.json` после завершения build.

`.dqcr_validation_runs/` обновляется при:

- запуске validation, когда backend вызывает framework CLI (`fw2 validate`) и сохраняет артефакты run в новый `<run_id>`.

### 10.2 Реестр проектов

В корне `PROJECTS_PATH` backend хранит:

```text
.dqcr_projects_registry.json
```

Он нужен для imported/linked metadata и availability.

### 10.3 Актуальные рабочие проекты в репозитории

На текущем состоянии репозитория присутствуют:

- `projects/rf110`
- `projects/rf110new_manual`
- `projects/sample`

Это важно, потому что ранее временные demo/new-project каталоги уже не являются актуальной базой документации.

---

## 11. REST API

Все backend HTTP routes публикуются под:

```text
/api/v1
```

### 11.1 Service endpoints

`GET /health`

- liveness.

`GET /ready`

- readiness.

### 11.2 Projects API

`GET /api/v1/projects`

- список проектов;
- возвращает расширенную summary-модель проекта.

`GET /api/v1/projects/{project_id}`

- получить один проект по id.

`PATCH /api/v1/projects/{project_id}/metadata`

- обновление metadata проекта.

Payload:

```json
{
  "name": "RF110",
  "description": "Main regulatory project",
  "visibility": "private",
  "tags": ["regulatory", "bank"]
}
```

`DELETE /api/v1/projects/{project_id}`

- удаляет проект;
- для `internal` и `imported` удаляет локальный каталог;
- для `linked` убирает запись из registry, не трогая внешний каталог.

`POST /api/v1/projects`

- создание/импорт/подключение проекта;
- режимы:
  - `create`
  - `import`
  - `connect`

`POST /api/v1/projects/import-upload`

- multipart upload проекта.

`GET /api/v1/projects/{project_id}/contexts`

- список контекстов.

### 11.3 Workflow API

`GET /api/v1/projects/{project_id}/workflow/status`

- агрегированный статус workflow проекта.

`GET /api/v1/projects/{project_id}/models/{model_id}/workflow`

- workflow payload модели и статус.

`POST /api/v1/projects/{project_id}/models/{model_id}/workflow/rebuild`

- принудительный rebuild workflow cache модели.

### 11.4 Files API

`GET /api/v1/projects/{project_id}/files/tree`

- дерево проекта.

`GET /api/v1/projects/{project_id}/files/content?path=...`

- содержимое файла;
- если файла нет, backend возвращает пустой `content`.

`PUT /api/v1/projects/{project_id}/files/content`

- сохранить файл.

`POST /api/v1/projects/{project_id}/files/folder`

- создать папку.

`POST /api/v1/projects/{project_id}/files/model`

- создать новую модель;
- backend валидирует `model_id`;
- создает `model/<ModelId>/model.yml`.

Payload:

```json
{
  "model_id": "NewModel"
}
```

`POST /api/v1/projects/{project_id}/files/rename`

- rename файла или папки.

`DELETE /api/v1/projects/{project_id}/files?path=...`

- удалить файл или папку.

### 11.5 Metadata/read-model API

`GET /api/v1/projects/{project_id}/autocomplete`

- параметры;
- builtin macros;
- config keys;
- objects;
- all contexts;
- workflow/fallback source flag.

Поддерживает query parameter:

- `model_id` - сузить autocomplete objects до конкретной модели.

`objects` в autocomplete сейчас имеют собственную модель:

- `kind: target_table | workflow_query`
- `source: project_workflow | project_model_fallback`
- `lookup_keys`
- `columns`

`GET /api/v1/projects/{project_id}/parameters`

- список параметров.

`POST /api/v1/projects/{project_id}/parameters`

- создать параметр.

`PUT /api/v1/projects/{project_id}/parameters/{parameter_id}`

- обновить параметр.

`DELETE /api/v1/projects/{project_id}/parameters/{parameter_id}`

- удалить параметр.

`POST /api/v1/projects/{project_id}/parameters/{parameter_id}/test`

- тест разрешения значения параметра.

### 11.6 Model API

`GET /api/v1/projects/{project_id}/models/{model_id}/lineage`

- lineage graph.

`GET /api/v1/projects/{project_id}/models/{model_id}/config-chain`

- config priority chain;
- resolved values;
- cte settings;
- generated outputs;
- sql metadata.

`GET /api/v1/projects/schema/model-yml`

- схема `model.yml`.

`GET /api/v1/projects/{project_id}/models/{model_id}`

- object representation модели.

`PUT /api/v1/projects/{project_id}/models/{model_id}`

- сохранить object representation обратно в YAML и файловую структуру.

### 11.7 Build API

`POST /api/v1/projects/{project_id}/build`

- выполнить build.

`GET /api/v1/projects/{project_id}/build/history`

- build history из памяти процесса.

`GET /api/v1/projects/{project_id}/build/{build_id}/files`

- дерево и список generated files.

`GET /api/v1/projects/{project_id}/build/{build_id}/download`

- скачать весь build.

`GET /api/v1/projects/{project_id}/build/{build_id}/download?path=...`

- скачать один файл.

`GET /api/v1/projects/{project_id}/build/{build_id}/files/content`

- получить текст артефакта.

`POST /api/v1/projects/{project_id}/build/{engine}/preview`

- preview SQL под конкретный engine.

Примечание:

- path-segment называется `build_id`, но фактически используется как engine id.

### 11.8 Validation API

`POST /api/v1/projects/{project_id}/validate`

- выполнить validation.

`GET /api/v1/projects/{project_id}/validate/history`

- validation history из памяти процесса.

`POST /api/v1/projects/{project_id}/validate/quickfix`

- quick fix.

Поддерживаемые типы:

- `add_field`
- `rename_folder`

---

## 12. WebSocket API

### 12.1 `WS /ws/terminal/{session_id}`

- backend поднимает PTY shell;
- cwd = `PROJECTS_PATH`;
- при disconnect session закрывается.

### 12.2 `WS /ws/validation/{project_id}`

- клиент отправляет входной payload;
- сервер стримит:
  - `progress`
  - `done`
  - `error`

### 12.3 `WS /ws/build/{project_id}`

- клиент отправляет build request;
- сервер стримит progress и final result.

---

## 13. Workflow cache

### 13.1 Статусы

Используются значения:

- `ready`
- `stale`
- `building`
- `error`
- `missing`

### 13.2 Источники workflow данных

- `framework_cli`
- `fallback`

### 13.3 Важный нюанс API

Project summary (`GET /projects`) возвращает `cache_status`.

Model/workflow endpoints возвращают более детализированное состояние через model-level payload.

С Phase 1 model-level workflow API возвращает:
- `workflow_schema_version`
- `payload_features`
- `diagnostics`

Отдельный diagnostics endpoint:
- `GET /api/v1/projects/{project_id}/models/{model_id}/workflow/diagnostics`

Phase 2 execution endpoints:
- `GET /api/v1/projects/{project_id}/models/{model_id}/workflow/graph` - step-level execution DAG (`nodes/edges/summary`) без heavy SQL строк;
- `GET /api/v1/projects/{project_id}/models/{model_id}/workflow/steps` - lightweight index шагов;
- `GET /api/v1/projects/{project_id}/models/{model_id}/workflow/steps/{step_id}` - heavy step payload для inspector (`source/prepared/rendered SQL`, metadata, param_model).

Diagnostics summary описывает:
- legacy ли payload;
- готов ли payload для execution-aware UI;
- какие contract-поля отсутствуют;
- насколько покрыты heavy SQL artifacts (`source/prepared/rendered/metadata`);
- почему IDE работает в degraded/fallback режиме.

### 13.4 Триггеры rebuild workflow cache

Основной orchestrator: `trigger_workflow_rebuild(project_id, changed_paths)`.

Ключевые источники вызова:

- `POST /api/v1/projects` (`create|import|connect`);
- `POST /api/v1/projects/import-upload`;
- `PATCH /api/v1/projects/{project_id}/metadata` (для internal проектов);
- файловые endpoints:
  - `PUT /api/v1/projects/{project_id}/files/content`
  - `POST /api/v1/projects/{project_id}/files/folder`
  - `POST /api/v1/projects/{project_id}/files/model`
  - `POST /api/v1/projects/{project_id}/files/rename`
  - `DELETE /api/v1/projects/{project_id}/files`
- параметры:
  - `POST /api/v1/projects/{project_id}/parameters`
  - `PUT /api/v1/projects/{project_id}/parameters/{parameter_id}`
  - `DELETE /api/v1/projects/{project_id}/parameters/{parameter_id}`
- `PUT /api/v1/projects/{project_id}/models/{model_id}`;
- `POST /api/v1/projects/{project_id}/models/{model_id}/workflow/rebuild`.

Ленивая инициализация cache:

- `ensure_project_workflow_cache(...)` вызывается при `GET /api/v1/projects/{project_id}/files/tree` и достраивает отсутствующие cache-файлы.

---

## 14. Безопасность и ограничения

### 14.1 Path traversal

Все файловые операции должны проходить через `ensure_within_base(...)`.

### 14.2 Linked projects

Backend не владеет содержимым linked каталога. Для linked проекта:

- проверяется `availability_status`;
- удаление проекта удаляет только registry entry.

### 14.3 Auth

Полноценная серверная auth/authorization схема не реализована.

Frontend хранит role в localStorage и отправляет `Authorization` header, но backend его не валидирует.

### 14.4 Runtime persistence

Не персистятся между рестартами:

- build history;
- validation history;
- admin runtime state;
- terminal sessions.

---

## 15. Конфигурация

Backend settings:

- `APP_NAME`
- `API_PREFIX`
- `PROJECTS_PATH`
- `CORS_ORIGINS`
- `SECRET_KEY`
- `LOG_LEVEL`
- `FW_USE_CLI`
- `FW_CLI_COMMAND`

Стандартный docker runtime:

- `PROJECTS_PATH=/app/projects`
- `FW_USE_CLI=true`
- `FW_CLI_COMMAND=fw2`

---

## 16. Тесты

### 16.1 Backend

`backend/tests/test_projects_api.py`

- projects API;
- import/connect/upload;
- files API;
- workflow API;
- validate/build history;
- часть model/lineage поведения.

`backend/tests/test_fw_service.py`

- error mapping;
- CLI/fallback behavior;
- workflow build behavior.

### 16.2 Frontend

`frontend/tests/e2e/critical-path.spec.ts`

- критические UI-сценарии.

Следует учитывать, что часть UI уже существенно изменилась, поэтому системная документация должна считаться более актуальным описанием архитектуры, чем старые e2e допущения.

### 16.3 Запуск

```bash
make test
uv run --directory backend pytest
pnpm --dir frontend test
pnpm --dir frontend test:e2e
```

---

## 17. Карта каталогов репозитория

### 17.1 Корень

`README.md`

- краткая входная точка.

`Docs/`

- проектная документация.

`backend/`

- FastAPI backend.

`frontend/`

- React frontend.

`infra/docker/`

- compose и nginx.

`projects/`

- текущие workspace projects.

`FTRepCBR.Workflow.FW/`

- framework package.

### 17.2 `frontend/src/`

`api/`

- HTTP client и DTO.

`app/providers/`

- providers приложения.

`app/store/`

- zustand stores.

`features/hub/`

- project hub.

`features/project/`

- project overview page.

`features/layout/`

- workbench layout selection.

`features/lineage/`

- lineage feature.

`features/model/`

- model editing feature.

`features/sql/`

- SQL editor feature.

`features/parameters/`

- parameters feature.

`features/build/`

- build feature.

`features/validate/`

- validate feature.

`features/admin/`

- admin feature.

`shared/components/`

- shell and reusable UI components.

### 17.3 `backend/app/`

`core/`

- config, fs, logging, registry.

`routers/`

- HTTP/WS endpoints.

`services/`

- framework integration, workflow cache, terminal.

`schemas/`

- Pydantic schemas.

### 17.4 `FTRepCBR.Workflow.FW/`

`src/cli.py`

- CLI entrypoint.

`src/parsing/`

- parsing layer.

`src/models/`

- domain models.

`src/generation/`

- build/generation logic.

`src/validation/`

- validation subsystem.

`src/macros/`

- macros/functions/materialization/workflow engine templates.

`src/config/`

- registries and templates.

---

## 18. Что изменилось относительно прошлой версии документации

В актуальном проекте нужно учитывать следующие изменения:

1. Появился отдельный Project Hub как основной стартовый экран.
2. Появился Project Info screen как отдельная вкладка workbench.
3. Project API расширен:
   - `GET /projects/{project_id}`
   - `PATCH /projects/{project_id}/metadata`
   - `DELETE /projects/{project_id}`
4. Files API расширен:
   - `POST /projects/{project_id}/files/model`
5. Autocomplete API расширен объектами проекта и поддержкой `model_id`.
6. Project summary теперь возвращает analytics и metadata поля:
   - `visibility`
   - `tags`
   - `model_count`
   - `folder_count`
   - `sql_count`
   - `modified_at`
   - `cache_status`
7. Internal project metadata теперь частично синхронизируется через `project.yml`.
8. Появился общий `ProjectStructureDialog`, переиспользуемый в нескольких экранах.
9. Текущая структура frontend feature-модулей заметно богаче, чем в исходной scaffold-версии.
10. Набор реальных проектов в `projects/` изменился; старые временные demo-проекты больше не должны считаться канонической основой документации.

---

## 19. Рекомендации для дальнейшей разработки и QA

### 19.1 Для backend

- любое изменение project/model/parameter/files должно учитывать workflow cache invalidation;
- новые project-level поля нужно синхронизировать одновременно в API schema, registry и internal `project.yml` logic;
- linked projects нужно тестировать отдельно от internal/imported.

### 19.2 Для frontend

- новые feature-модули лучше добавлять отдельными domain-папками;
- при изменении project lifecycle надо проверять оба режима приложения:
  - hub mode;
  - workbench mode;
- persisted stores и localStorage поведение нужно учитывать в e2e.

### 19.3 Для QA

- отдельно тестировать:
  - project creation
  - import upload
  - linked project
  - metadata patch
  - delete semantics
  - workflow cache status transitions
  - build/validate history after restart
- проверять read-model ответы как в `workflow`, так и в `fallback` режимах.

Этот документ должен использоваться как актуальная базовая карта системы для разработки, тестирования и дальнейшего уточнения API-контрактов.
