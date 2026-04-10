# DQCR Studio: AI Development Summary

## 1) Что это за проект

DQCR Studio - это файловая студия для разработки DQCR-проектов.
Источник истины - файловая структура проекта (YAML/SQL), а не база данных.

Система состоит из:
- `frontend/` (React + Vite + TypeScript)
- `backend/` (FastAPI)
- `FTRepCBR.Workflow.FW/` (framework CLI `fw2` для validate/generate/workflow build)
- `projects/` (рабочие проекты)

Ключевой принцип: frontend и backend строят производные read-модели поверх файлов проекта (workflow cache, lineage, autocomplete, build/validation history).

## 2) Быстрый запуск

- Локально: `make dev`
- Прод: `make prod-up`
- Проверка: `make prod-health`
- Тесты: `make test`

Основные URL:
- `http://localhost:80`
- `GET /health`
- `GET /ready`
- `GET /api/v1/projects`

## 3) Точки входа

Backend:
- `backend/app/main.py` - FastAPI app, middlewares, health/readiness, роутеры, exception handlers.
- `backend/app/routers/projects.py` - основной доменный router (projects, workflow, parameters, lineage, build, validate и т.д.).
- `backend/app/routers/files.py` - файловые операции в проекте (tree/content/rename/delete/new folder/new model).
- `backend/app/services/fw_service.py` - интеграция с `fw2`, normalize ошибок, validate/generate/workflow build.
- `backend/app/core/config.py` - env-конфиг (`API_PREFIX`, `PROJECTS_PATH`, `FW_CLI_COMMAND`, `SECRET_KEY` и т.д.).

Frontend:
- `frontend/src/main.tsx` - bootstrap приложения.
- `frontend/src/App.tsx` - переключение `Hub` vs `Workbench`.
- `frontend/src/features/layout/Workbench.tsx` - маршрутизация по основным вкладкам.
- `frontend/src/api/projects.ts` - типы API и клиентские контракты.

## 4) UI-модель

Режимы:
- `Hub mode`: проект не выбран.
- `Workbench mode`: открыт конкретный проект.

Основные вкладки workbench:
- `project`
- `lineage`
- `model`
- `sql`
- `validate`
- `parameters`
- `build`
- `admin`

Состояние хранится в Zustand-сторах (`projectStore`, `editorStore`, `uiStore`, `contextStore`, `validationStore`).

## 5) Ключевые backend API

Файлы:
- `GET /api/v1/projects/{project_id}/files/tree`
- `GET /api/v1/projects/{project_id}/files/content?path=...`
- `PUT /api/v1/projects/{project_id}/files/content`
- `POST /api/v1/projects/{project_id}/files/folder`
- `POST /api/v1/projects/{project_id}/files/model`
- `POST /api/v1/projects/{project_id}/files/rename`
- `DELETE /api/v1/projects/{project_id}/files?path=...`

Проекты и доменная логика:
- `GET /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `POST /api/v1/projects`
- `DELETE /api/v1/projects/{project_id}`
- `GET /api/v1/projects/{project_id}/contexts`
- `GET /api/v1/projects/{project_id}/autocomplete`
- `GET /api/v1/projects/{project_id}/models/{model_id}/lineage`
- `POST /api/v1/projects/{project_id}/build`
- `POST /api/v1/projects/{project_id}/validate`

Realtime:
- `WS /terminal/{session_id}`
- `WS /validation/{project_id}`
- `WS /build/{project_id}`

## 6) Как устроены проекты на диске

Типовая структура:

```text
<project_id>/
  project.yml
  contexts/*.yml
  parameters/*.yml
  model/<ModelId>/model.yml
  model/<ModelId>/workflow/** or SQL/**
  model/<ModelId>/parameters/*.yml
  .dqcr_workflow_cache/
  .dqcr_builds/
  .dqcr_validation_runs/
```

Registry проектов:
- `projects/.dqcr_projects_registry.json`

## 7) Практика безопасных изменений для AI

1. Сначала определить слой изменения: `frontend`, `backend`, `framework` или `project files`.
2. Не ломать `filesystem-first`: не добавлять БД-зависимую истину для структуры проекта.
3. При изменении file API обязательно сохранять path-safety и защиту от path traversal.
4. При изменении build/validate учитывать, что backend может работать через `fw2` CLI.
5. Изменения в API синхронизировать с типами в `frontend/src/api/projects.ts`.
6. Для UI-фич проверять состояние `Hub` и `Workbench` отдельно.
7. Тесты минимум:
- backend: `uv run --directory backend pytest`
- frontend: `pnpm --dir frontend test`

## 8) Текущие технические риски

- `backend/app/routers/projects.py` очень большой и перегружен доменной логикой.
- Часть функциональности опирается на внешнюю CLI-интеграцию (`fw2`), что требует аккуратной обработки ошибок и артефактов.
- При изменениях контрактов высокий риск расхождения frontend-типов и backend-ответов.

## 9) Рекомендуемый workflow для AI-агента

1. Прочитать `Docs/SYSTEM_REFERENCE.md` и целевой модуль.
2. Найти точку изменения через `frontend/src/api/*`, `backend/app/routers/*`, `backend/app/services/*`.
3. Внести минимальное изменение в один слой, затем синхронизировать контракты.
4. Прогнать релевантные тесты.
5. Проверить пользовательский сценарий end-to-end в UI.
