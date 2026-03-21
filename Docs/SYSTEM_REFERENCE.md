# DQCR Studio: системная документация

## 1. Назначение решения

DQCR Studio - это локальная IDE/студия для работы с файловыми DQCR-проектами. Решение объединяет:

- визуальную рабочую область для аналитика/разработчика;
- backend API для работы с проектами, файлами, параметрами, validation и build;
- встроенную интеграцию с `FTRepCBR.Workflow.FW`, который строит workflow-модель, валидирует проект и генерирует артефакты;
- файловое хранилище проектов, которое является основным источником истины.

Ключевой архитектурный принцип: UI и API работают поверх структуры каталогов проекта, а framework CLI используется как движок вычисления workflow, генерации и валидации.

---

## 2. Состав решения

### 2.1 Верхнеуровневая схема

```text
Frontend (React/Vite)
        |
        | HTTP / WebSocket
        v
Backend (FastAPI)
        |
        | file system + fw2 CLI
        v
Projects directory + FTRepCBR.Workflow.FW
```

### 2.2 Подсистемы

1. `frontend/`
   SPA-интерфейс студии: редактор SQL, модель, lineage, параметры, validate, build, admin.

2. `backend/`
   HTTP/WebSocket API. Управляет проектами, файлами, workflow cache, build/validate, quick-fix и terminal session.

3. `FTRepCBR.Workflow.FW/`
   Framework-пакет с CLI `fw2`, парсингом проекта, генерацией workflow, materialization, rules validation и шаблонами workflow engine.

4. `projects/`
   Рабочие проекты студии. Каждый проект хранится как набор YAML/SQL-файлов.

5. `infra/docker/`
   Docker Compose и Nginx для локального запуска всей системы.

6. `Docs/`
   Продуктовая и инженерная документация. Этот документ является опорным системным reference.

---

## 3. Архитектурные принципы

### 3.1 Файловая модель как source of truth

Основное состояние проекта хранится в каталоге проекта:

- `project.yml`
- `contexts/*.yml`
- `parameters/*.yml`
- `model/<ModelId>/model.yml`
- `model/<ModelId>/workflow/**`
- `model/<ModelId>/parameters/*.yml`

Backend не использует базу данных. Все операции изменяют файлы напрямую.

### 3.2 Workflow cache как ускоряющий слой

Для вычисляемых представлений модели backend использует кэш workflow:

- `.dqcr_workflow_cache/<model_id>.json`
- `.dqcr_workflow_cache/<model_id>.meta.json`

Кэш нужен для:

- lineage;
- autocomplete;
- config-chain;
- model object;
- статуса workflow.

Если workflow cache отсутствует или невалиден, backend может перейти на fallback-логику, построенную на прямом чтении файлов.

### 3.3 Framework как вычислительный движок

Backend вызывает framework CLI `fw2` для:

- `validate`;
- `generate`;
- build workflow модели.

Если CLI недоступен для некоторых сценариев, `FWService` использует локальные fallback builders там, где они предусмотрены.

### 3.4 Stateless API + in-memory runtime state

Backend в целом stateless относительно HTTP-запросов, но есть несколько in-memory структур runtime-состояния:

- `_VALIDATION_HISTORY`
- `_BUILD_HISTORY`
- terminal sessions в `TerminalService`
- admin templates/rules/macros в памяти процесса

Это значит:

- история build/validate не переживает рестарт backend;
- admin-изменения сейчас не персистятся в отдельное хранилище;
- terminal sessions живут только в памяти backend-процесса.

---

## 4. Runtime-архитектура

### 4.1 Frontend

Технологии:

- React 18
- TypeScript
- Vite
- Zustand
- TanStack Query
- Monaco Editor
- React Flow
- xterm

Frontend общается только с backend API, прямого доступа к framework или файловой системе у него нет.

### 4.2 Backend

Технологии:

- FastAPI
- Pydantic Settings
- ptyprocess
- Uvicorn

Ключевые маршрутизаторы:

- `projects.py` - основной домен системы;
- `files.py` - файловый CRUD внутри проекта;
- `admin.py` - шаблоны, rules, macros;
- `ws.py` - terminal/build/validation streaming.

### 4.3 Framework

`FTRepCBR.Workflow.FW` содержит:

- CLI `fw2`;
- парсеры project/model/sql/parameter/context;
- генераторы workflow;
- materialization templates;
- validation rules;
- registries для workflow engines, tools и macros.

### 4.4 Инфраструктура запуска

`infra/docker/docker-compose.yml` поднимает:

- `backend` на `8000`
- `frontend` на `5173`
- `nginx` на `80`

Nginx выступает как единая точка входа.

---

## 5. Логическая модель данных

### 5.1 Проект

Проект идентифицируется `project_id` и физически находится в `PROJECTS_PATH`.

Поддерживаются типы источника проекта:

- `internal` - создан внутри workspace;
- `imported` - скопирован из внешней папки;
- `linked` - подключен как внешняя директория без копирования.

Метаданные linked/imported проектов частично хранятся в реестре:

- `.dqcr_projects_registry.json`

### 5.2 Контексты

Контексты лежат в `contexts/*.yml`. Если каталог отсутствует, backend считает, что доступен `default`.

### 5.3 Модели

Модель живет в `model/<model_id>/` и обычно содержит:

- `model.yml`
- `workflow/<folder>/folder.yml`
- SQL-файлы внутри `workflow`
- model-scoped parameters

### 5.4 Параметры

Параметры бывают:

- global: `parameters/*.yml`
- model-scoped: `model/<model_id>/parameters/*.yml`

Поддерживаемые scope:

- `global`
- `model:<model_id>`

Backend хранит значение параметра по контекстам, где `type` может быть:

- `static`
- `dynamic`

### 5.5 Build artifacts

Результаты build пишутся в:

- `<project>/.dqcr_builds/<build_id>/...`
- либо в указанный `output_path/<build_id>/...`

### 5.6 Validation artifacts

Результаты validation CLI пишутся в:

- `<project>/.dqcr_validation_runs/<run_id>/...`

---

## 6. Основные пользовательские сценарии

### 6.1 Создание проекта

Frontend wizard отправляет `POST /api/v1/projects`.
Backend:

1. создает структуру каталогов;
2. пишет `project.yml`, contexts, model, workflow;
3. добавляет запись в registry;
4. инициирует rebuild workflow cache.

### 6.2 Импорт проекта

Варианты:

- `mode=import` с `source_path`
- `POST /api/v1/projects/import-upload` с загрузкой файлов

Импорт создает локальную копию проекта в workspace.

### 6.3 Подключение внешней папки

`mode=connect` регистрирует внешний каталог как `linked` проект. Backend хранит `source_path` и проверяет `availability_status`.

### 6.4 Редактирование файлов

Файловые операции идут через `/files/*`. После любого изменения backend вызывает `trigger_workflow_rebuild(...)`, чтобы пометить workflow как требующий пересборки.

### 6.5 Получение lineage/config/autocomplete/model object

Backend сначала пытается использовать workflow cache. Если данных нет, используется fallback по файловой структуре.

### 6.6 Validation

`POST /validate` запускает framework validation и сохраняет результат в in-memory history.

### 6.7 Build

`POST /build` запускает framework generation и сохраняет:

- метаданные build в памяти;
- физические файлы в output directory.

### 6.8 Quick fix

`POST /validate/quickfix` выполняет исправления в файлах проекта, затем по умолчанию повторно запускает validation.

---

## 7. Backend: модульная структура

### 7.1 `backend/app/main.py`

Точка входа FastAPI.

Отвечает за:

- создание приложения;
- CORS;
- middleware request logging;
- health/readiness endpoints;
- подключение router-ов;
- global exception handlers.

### 7.2 `backend/app/core/`

`config.py`

- настройки приложения через env vars;
- `PROJECTS_PATH`, `FW_USE_CLI`, `FW_CLI_COMMAND`, `SECRET_KEY`.

`fs.py`

- защита от path traversal;
- разрешение project path, включая linked projects.

`project_registry.py`

- чтение/запись `.dqcr_projects_registry.json`;
- учет типа проекта и доступности linked path.

`logging.py`

- структурированная настройка логирования backend.

### 7.3 `backend/app/services/`

`fw_service.py`

- адаптер между FastAPI и framework;
- load project/model;
- build lineage;
- run validation;
- run generation;
- run workflow build;
- normalize errors CLI/fallback.

`workflow_cache_service.py`

- чтение/запись `.dqcr_workflow_cache`;
- управление статусами:
  - `ready`
  - `stale`
  - `building`
  - `error`
  - `missing`

`terminal_service.py`

- управление pseudo-terminal session;
- shell-сессии на базе `ptyprocess`.

### 7.4 `backend/app/routers/`

`projects.py`

- главный доменный router;
- создание/import/connect projects;
- contexts;
- workflow status;
- autocomplete;
- parameters CRUD;
- lineage;
- config-chain;
- model object;
- build;
- validate;
- quickfix;
- истории build/validate.

`files.py`

- дерево файлов;
- чтение/запись файлов;
- create folder;
- rename;
- delete.

`admin.py`

- шаблоны;
- набор правил;
- macro registry для UI.

`ws.py`

- terminal websocket;
- validation websocket;
- build websocket.

---

## 8. Frontend: модульная структура

### 8.1 Shell и layout

`frontend/src/App.tsx`

- каркас приложения:
  - `TopBar`
  - `Sidebar`
  - `TabBar`
  - `Workbench`
  - `BottomPanel`
  - `StatusBar`
  - `ToastViewport`
  - `ProjectWizardModal`

`frontend/src/features/layout/Workbench.tsx`

- переключает рабочие экраны:
  - lineage
  - model
  - sql
  - validate
  - parameters
  - build
  - admin

### 8.2 API слой

`frontend/src/api/client.ts`

- общий `axios` client;
- проставляет `Authorization` из localStorage;
- пишет API log в UI store.

`frontend/src/api/projects.ts`

- типы запросов/ответов;
- все вызовы backend API.

### 8.3 State management

`frontend/src/app/store/projectStore.ts`

- текущий активный проект.

`frontend/src/app/store/contextStore.ts`

- активный контекст;
- multi-context режим.

`frontend/src/app/store/editorStore.ts`

- активная вкладка;
- список открытых файлов;
- dirty state;
- навигация к строке.

`frontend/src/app/store/uiStore.ts`

- состояние shell/UI;
- bottom panel;
- toasts;
- api logs;
- project wizard;
- role;
- validation autorun.

`frontend/src/app/store/validationStore.ts`

- последний validation result.

### 8.4 Feature-модули

`features/sql/`

- SQL editor;
- Monaco integration;
- autocomplete;
- preview build output;
- запуск validation;
- конфигурационный inspector.

`features/model/`

- model editor;
- синхронизация YAML <-> object representation.

`features/lineage/`

- граф lineage;
- layout через `dagre`;
- визуализация через `reactflow`.

`features/parameters/`

- CRUD параметров;
- тестирование параметра;
- интеграция с workflow/autocomplete/config-chain.

`features/build/`

- запуск build;
- просмотр истории;
- дерево build artifacts;
- просмотр generated files;
- скачивание результата.

`features/validate/`

- запуск validation;
- история validation;
- фильтры по severity/category;
- quick-fix интеграция.

`features/admin/`

- templates;
- rules;
- macros.

`features/wizard/`

- мастер создания/импорта проекта.

---

## 9. Framework: внутреннее устройство

### 9.1 Основные зоны

`FTRepCBR.Workflow.FW/src/parsing/`

- загрузка `project.yml`, `model.yml`, parameters, contexts, templates;
- SQL metadata parsing.

`FTRepCBR.Workflow.FW/src/models/`

- модели домена framework:
  - project
  - workflow
  - step
  - parameter
  - context
  - target table
  - sql query

`FTRepCBR.Workflow.FW/src/generation/`

- builders и resolvers workflow;
- построение workflow model и generation result.

`FTRepCBR.Workflow.FW/src/validation/`

- rule runner;
- template validation;
- HTML/JSON reports.

`FTRepCBR.Workflow.FW/src/macros/`

- builtin macros;
- materialization;
- workflow-engine specific macros/functions.

`FTRepCBR.Workflow.FW/src/config/`

- registry workflow engines;
- tools;
- templates.

### 9.2 CLI-команды

По `src/cli.py` framework поддерживает как минимум:

- SQL parsing;
- parameter parsing;
- workflow build;
- `generate`;
- `validate`.

Для студии критичны команды:

- `fw2 validate <project_path> <model_id> -o <output_dir>`
- `fw2 generate <project_path> <model_id> -c <context> -w <engine> -o <output_dir>`

### 9.3 Поддерживаемые workflow engines

В backend явно поддерживаются:

- `dqcr`
- `airflow`
- `dbt`
- `oracle_plsql`

---

## 10. Проектная структура на файловой системе

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
        02_transform/
          folder.yml
          001_step.sql
  .dqcr_workflow_cache/
    <ModelId>.json
    <ModelId>.meta.json
  .dqcr_builds/
    <build_id>/
  .dqcr_validation_runs/
    <run_id>/
```

### 10.1 Служебные файлы/каталоги проекта

`.dqcr_workflow_cache/`

- внутренний кэш backend;
- можно пересоздать;
- не должен быть основным источником истины.

`.dqcr_builds/`

- generated output;
- может очищаться отдельно от исходников проекта.

`.dqcr_validation_runs/`

- validation artifacts от framework CLI.

### 10.2 Реестр проектов

В корне `PROJECTS_PATH` backend может хранить:

```text
.dqcr_projects_registry.json
```

Он нужен для imported/linked metadata и availability linked проектов.

---

## 11. REST API

Все HTTP endpoints публикуются под префиксом:

```text
/api/v1
```

### 11.1 Service endpoints

`GET /health`

- liveness probe;
- ответ: `{"status":"ok"}`.

`GET /ready`

- readiness probe;
- ответ зависит от `app.state.fw_ready`.

### 11.2 Projects API

`GET /api/v1/projects`

- список всех проектов из filesystem + registry.

`POST /api/v1/projects`

- создание/импорт/подключение проекта;
- режимы:
  - `create`
  - `import`
  - `connect`

Примеры payload:

```json
{
  "mode": "create",
  "project_id": "newproj",
  "name": "New Project",
  "description": "from wizard",
  "template": "flx",
  "contexts": ["default", "dev"],
  "properties": {"owner": "qa"},
  "model": {
    "name": "SampleModel",
    "first_folder": "01_stage",
    "attributes": [{"name": "id", "domain_type": "number", "is_key": true}]
  }
}
```

```json
{
  "mode": "import",
  "source_path": "/path/to/project",
  "project_id": "imported_proj",
  "name": "Imported Project"
}
```

```json
{
  "mode": "connect",
  "source_path": "/path/to/project",
  "project_id": "linked_proj",
  "name": "Linked Project"
}
```

`POST /api/v1/projects/import-upload`

- multipart upload проекта папкой;
- поля:
  - `files[]`
  - `relative_paths[]`
  - `project_id?`
  - `name?`
  - `description?`

`GET /api/v1/projects/{project_id}/contexts`

- список contexts.

### 11.3 Workflow API

`GET /api/v1/projects/{project_id}/workflow/status`

- агрегированный статус workflow cache по всем моделям проекта.

`GET /api/v1/projects/{project_id}/models/{model_id}/workflow`

- workflow payload модели + meta status.

`POST /api/v1/projects/{project_id}/models/{model_id}/workflow/rebuild`

- принудительный rebuild workflow cache для модели.

Ответы используют статусы:

- `ready`
- `stale`
- `building`
- `error`
- `missing`

### 11.4 Files API

`GET /api/v1/projects/{project_id}/files/tree`

- дерево файлов проекта.

`GET /api/v1/projects/{project_id}/files/content?path=...`

- содержимое файла;
- если файл отсутствует, backend возвращает пустой `content`, а не 404.

`PUT /api/v1/projects/{project_id}/files/content`

```json
{
  "path": "model/SampleModel/workflow/01_stage/001_main.sql",
  "content": "SELECT 1"
}
```

`POST /api/v1/projects/{project_id}/files/folder`

```json
{
  "path": "model/SampleModel/workflow/02_new"
}
```

`POST /api/v1/projects/{project_id}/files/rename`

```json
{
  "path": "old/name.sql",
  "new_name": "new_name.sql"
}
```

`DELETE /api/v1/projects/{project_id}/files?path=...`

- удаление файла или каталога.

### 11.5 Autocomplete и параметры

`GET /api/v1/projects/{project_id}/autocomplete`

- параметры;
- builtin macros;
- config keys;
- all contexts;
- признак `fallback`.

`GET /api/v1/projects/{project_id}/parameters`

- список всех параметров проекта.

`POST /api/v1/projects/{project_id}/parameters`

- создание параметра.

`PUT /api/v1/projects/{project_id}/parameters/{parameter_id}?scope=...`

- обновление параметра.

`DELETE /api/v1/projects/{project_id}/parameters/{parameter_id}?scope=...`

- удаление параметра.

`POST /api/v1/projects/{project_id}/parameters/{parameter_id}/test?scope=...`

- тест разрешения значения параметра;
- для `dynamic` backend сейчас возвращает simulated result.

### 11.6 Model API

`GET /api/v1/projects/{project_id}/models/{model_id}/lineage`

- lineage graph и summary.

`GET /api/v1/projects/{project_id}/models/{model_id}/config-chain?sql_path=...`

- цепочка приоритетов `@config`;
- resolved values;
- cte settings;
- generated outputs;
- sql metadata.

`GET /api/v1/projects/schema/model-yml`

- схема `model.yml` для UI.

`GET /api/v1/projects/{project_id}/models/{model_id}`

- модель как object representation;
- источник:
  - `workflow`
  - `fallback`

`PUT /api/v1/projects/{project_id}/models/{model_id}`

- сохранение model object обратно в `model.yml`;
- синхронизация workflow folders на файловую систему.

### 11.7 Build API

`POST /api/v1/projects/{project_id}/build`

Payload:

```json
{
  "model_id": "SampleModel",
  "engine": "dqcr",
  "context": "default",
  "dry_run": false,
  "output_path": ".custom_output"
}
```

`GET /api/v1/projects/{project_id}/build/history`

- до 10 последних build из памяти процесса.

`GET /api/v1/projects/{project_id}/build/{build_id}/files`

- список и дерево generated files.

`GET /api/v1/projects/{project_id}/build/{build_id}/download`

- скачать весь build zip-архивом.

`GET /api/v1/projects/{project_id}/build/{build_id}/download?path=...`

- скачать конкретный файл.

`GET /api/v1/projects/{project_id}/build/{build_id}/files/content?path=...`

- текстовое содержимое build-артефакта.

`POST /api/v1/projects/{project_id}/build/{engine}/preview`

- preview рендера SQL под engine;
- параметр пути реализован через `build_id` segment, но фактически туда передается id engine.

### 11.8 Validation API

`POST /api/v1/projects/{project_id}/validate`

Payload:

```json
{
  "model_id": "SampleModel",
  "categories": ["general", "sql", "descriptions"]
}
```

`GET /api/v1/projects/{project_id}/validate/history`

- до 5 последних validation runs из памяти процесса.

`POST /api/v1/projects/{project_id}/validate/quickfix`

Поддерживаемые типы:

- `add_field`
- `rename_folder`

Пример:

```json
{
  "type": "add_field",
  "model_id": "SampleModel",
  "field_name": "description",
  "rerun": true
}
```

---

## 12. WebSocket API

### 12.1 Terminal

`WS /ws/terminal/{session_id}`

Назначение:

- двусторонняя shell session;
- backend поднимает `/bin/bash` в `PROJECTS_PATH`.

Особенности:

- один `session_id` соответствует одному PTY;
- вывод читается polling-циклом каждые ~50 мс;
- при disconnect session закрывается.

### 12.2 Validation progress

`WS /ws/validation/{project_id}`

Первое сообщение от клиента:

```json
{
  "model_id": "SampleModel",
  "categories": ["general", "sql"]
}
```

Сервер отправляет:

- `progress`
- `done`
- `error`

### 12.3 Build progress

`WS /ws/build/{project_id}`

Первое сообщение от клиента:

```json
{
  "model_id": "SampleModel",
  "engine": "dqcr",
  "context": "default",
  "dry_run": false,
  "output_path": ".dqcr_builds"
}
```

Сервер отправляет:

- `progress`
- `done`
- `error`

---

## 13. Workflow cache и статусы

### 13.1 Файлы cache

Для каждой модели:

- payload: `.dqcr_workflow_cache/<model_id>.json`
- meta: `.dqcr_workflow_cache/<model_id>.meta.json`

### 13.2 Значения статуса

`ready`

- cache существует и считается актуальным.

`stale`

- исходные файлы изменились, cache нуждается в rebuild.

`building`

- идет rebuild workflow.

`error`

- rebuild завершился ошибкой.

`missing`

- cache еще не был построен.

### 13.3 Source workflow данных

`framework_cli`

- данные пришли из framework CLI.

`fallback`

- backend восстановил ответ напрямую из файловой структуры.

---

## 14. Безопасность и ограничения

### 14.1 Path traversal protection

Все файловые операции проходят через `ensure_within_base(...)`. Это обязательный guardrail против выхода за пределы project root.

### 14.2 Linked projects

Linked проект может указывать на внешний каталог. Backend проверяет его доступность и отражает состояние в `availability_status`.

### 14.3 Authentication/authorization

В текущей реализации полноценной auth-схемы нет. Frontend добавляет `Authorization` header из localStorage, но backend его не валидирует.

### 14.4 Runtime persistence limits

Не персистятся между рестартами:

- build history;
- validation history;
- admin runtime changes;
- terminal sessions.

---

## 15. Конфигурация и переменные окружения

Backend (`backend/app/core/config.py`):

- `APP_NAME`
- `API_PREFIX`
- `PROJECTS_PATH`
- `CORS_ORIGINS`
- `SECRET_KEY` - обязательный
- `LOG_LEVEL`
- `FW_USE_CLI`
- `FW_CLI_COMMAND`

Стандартные значения для локального docker запуска:

- `PROJECTS_PATH=/app/projects`
- `FW_USE_CLI=true`
- `FW_CLI_COMMAND=fw2`

---

## 16. Тестовая стратегия и текущие тесты

### 16.1 Backend

`backend/tests/test_projects_api.py`

Покрывает:

- list/create projects;
- import/connect/upload;
- contexts;
- validate/history;
- build/history/files/download;
- workflow status/rebuild;
- files API;
- часть lineage/model behavior.

`backend/tests/test_fw_service.py`

Покрывает:

- error mapping;
- fallback/CLI branch behavior;
- workflow build behavior.

### 16.2 Frontend

`frontend/tests/e2e/critical-path.spec.ts`

Покрывает основные UI-сценарии:

- открыть проект и lineage;
- редактировать SQL, сохранить и валидировать;
- создать проект wizard-ом и перейти к build;
- открыть model editor и переключить режимы.

### 16.3 Команды запуска тестов

```bash
make test
uv run --directory backend pytest
pnpm --dir frontend test
pnpm --dir frontend test:e2e
```

---

## 17. Карта каталогов репозитория

### 17.1 Корень репозитория

`README.md`

- краткий вход в проект.

`Makefile`

- `dev`, `build`, `test`, `deploy`, `down`.

`Docs/`

- инженерные и продуктовые документы.

`backend/`

- backend API.

`frontend/`

- frontend SPA.

`infra/docker/`

- docker-compose + nginx.

`projects/`

- локальные проекты студии.

`FTRepCBR.Workflow.FW/`

- framework-движок.

### 17.2 `backend/`

`app/main.py`

- FastAPI app.

`app/core/`

- config, fs, registry, logging.

`app/routers/`

- HTTP/WS endpoints.

`app/services/`

- FW integration, workflow cache, terminal.

`app/schemas/`

- Pydantic response models базового уровня.

`tests/`

- backend tests.

### 17.3 `frontend/`

`src/api/`

- API client и DTO-типы.

`src/app/store/`

- Zustand stores.

`src/features/`

- feature-oriented UI modules.

`src/shared/components/`

- shell и переиспользуемые UI-компоненты.

`tests/e2e/`

- Playwright e2e.

### 17.4 `FTRepCBR.Workflow.FW/`

`src/cli.py`

- CLI entry.

`src/parsing/`

- parsing layer.

`src/models/`

- framework domain models.

`src/generation/`

- workflow/build generation.

`src/validation/`

- validation subsystem.

`src/macros/`

- macros/functions/materialization/workflow-engine templates.

`src/config/`

- template/tool/workflow registries.

`docs/`

- framework-specific docs.

`sample/`

- sample framework project.

---

## 18. Ограничения текущей реализации

1. Истории build/validation живут только в памяти backend.
2. Admin templates/rules/macros сейчас runtime-only и не имеют выделенного persistent storage.
3. Полноценная auth/roles модель не реализована.
4. `GET /files/content` возвращает пустой контент для отсутствующего файла, что важно учитывать в тестах и UI.
5. `POST /build/{engine}/preview` маршрутизирован через `build_id` path-параметр, хотя фактически используется как engine id.
6. Workflow cache является производным слоем и может расходиться с файлами до rebuild.
7. Часть ответов backend построена на regex/file-based parsing fallback, а не только на framework payload.

---

## 19. Что важно для дальнейшей разработки

### 19.1 Точки расширения

- новые workflow engines добавляются через framework + backend supported engines;
- новые validation rules могут жить во framework и/или admin runtime rules;
- новые UI-экраны логично добавлять как отдельные feature-модули;
- новые API-операции почти всегда должны учитывать workflow cache invalidation.

### 19.2 Инварианты, которые нельзя ломать

- файловая структура проекта остается основным источником истины;
- файловые операции должны быть path-safe;
- любое изменение project/model/parameter/sql должно корректно помечать workflow cache как устаревший или пересобранный;
- linked/imported/internal проекты должны корректно различаться на уровне registry и UI.

### 19.3 Рекомендации для QA

- отдельно тестировать `workflow` и `fallback` режимы;
- после file/model/parameter edits проверять статус workflow;
- проверять совместимость build и validate для разных engine/context комбинаций;
- покрывать imported и linked проекты отдельно, так как у них разная файловая семантика;
- учитывать неперсистентность in-memory histories при рестарте backend.

---

## 20. Рекомендуемые документы следующего уровня

На базе этого reference имеет смысл дальше поддерживать:

1. API contract document с формальными JSON-примерами для каждого endpoint.
2. Test design document с матрицей сценариев по проектам, контекстам и engine.
3. Architecture Decision Records по workflow cache, linked projects и admin persistence.
4. Developer onboarding guide с типовым жизненным циклом изменения backend/frontend/framework.

Этот документ должен считаться главным обзорным описанием текущего решения и использоваться как стартовая точка для анализа, разработки и тестирования.
