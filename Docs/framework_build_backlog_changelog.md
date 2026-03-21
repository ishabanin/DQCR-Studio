# DQCR Studio — Final Changelog (`FWB-001…FWB-046`)

**Документ:** `framework_build_backlog_changelog.md`  
**Дата:** Март 2026  
**Статус:** Completed

---

## 1. Scope

Закрыт полный backlog из:

- [framework_build_remaining_spec.md](/Users/IgorShabanin/dev/DQCR%20Studio/Docs/framework_build_remaining_spec.md)
- [framework_build_remaining_tasks.md](/Users/IgorShabanin/dev/DQCR%20Studio/Docs/framework_build_remaining_tasks.md)

Итог: `FWB-001` … `FWB-046` отмечены выполненными.

---

## 2. EPIC-FWB-01: Workflow Cache API

Реализовано:

- meta-слой для workflow cache (`status`, `updated_at`, `error`, `source`)
- явные API:
  - `GET /api/v1/projects/{pid}/workflow/status`
  - `GET /api/v1/projects/{pid}/models/{mid}/workflow`
  - `POST /api/v1/projects/{pid}/models/{mid}/workflow/rebuild`
- статусы `ready/stale/building/error/missing`
- soft-fail rebuild с сохранением старого cache и пометкой `stale`
- API/тесты для workflow status endpoints

Ключевые файлы:

- [projects.py](/Users/IgorShabanin/dev/DQCR%20Studio/backend/app/routers/projects.py)
- [workflow_cache_service.py](/Users/IgorShabanin/dev/DQCR%20Studio/backend/app/services/workflow_cache_service.py)

---

## 3. EPIC-FWB-02: SQL Editor Migration

Реализовано:

- `config-chain` переведён на workflow-first вычисление
- SQL path привязывается к конкретному `sql step`
- `workflow.config` + `sql_model.metadata` используются как primary source
- fallback на file parsing сохранён и явно маркируется
- autocomplete переведён на workflow-backed параметры + `all_contexts`
- SQL Editor:
  - `PriorityChainPanel` на новом API
  - `Parameters Used` из workflow metadata
  - `CTE Inspector` из workflow/cache
  - fallback-индикатор
  - invalidation workflow-backed query после save
- тесты на config-chain/autocomplete поверх cache

Ключевые файлы:

- [projects.py](/Users/IgorShabanin/dev/DQCR%20Studio/backend/app/routers/projects.py)
- [SqlEditorScreen.tsx](/Users/IgorShabanin/dev/DQCR%20Studio/frontend/src/features/sql/SqlEditorScreen.tsx)
- [projects.ts](/Users/IgorShabanin/dev/DQCR%20Studio/frontend/src/api/projects.ts)

---

## 4. EPIC-FWB-03: Build & Validate Alignment

Реализовано:

- `workflow_updated_at` добавлен в validate/build result и history
- validate/build привязаны к актуальному workflow state модели
- BuildScreen:
  - блок `Workflow Build State`
  - timestamp последнего workflow build
  - `Rebuild Workflow`
  - отображение workflow error
- ValidateScreen:
  - отображение workflow state/timestamp
  - stale-маркер, если workflow новее validate результата
- тесты на связку history ↔ workflow timestamp

Ключевые файлы:

- [projects.py](/Users/IgorShabanin/dev/DQCR%20Studio/backend/app/routers/projects.py)
- [ws.py](/Users/IgorShabanin/dev/DQCR%20Studio/backend/app/routers/ws.py)
- [BuildScreen.tsx](/Users/IgorShabanin/dev/DQCR%20Studio/frontend/src/features/build/BuildScreen.tsx)
- [ValidateScreen.tsx](/Users/IgorShabanin/dev/DQCR%20Studio/frontend/src/features/validate/ValidateScreen.tsx)

---

## 5. EPIC-FWB-04: Global Workflow UX

Реализовано:

- global workflow status в StatusBar
- статусы `ready/building/error/fallback/missing` в UI-контексте
- source и timestamp для активной модели
- Model Editor показывает workflow source/status
- Parameters screen показывает source и stale state
- после save/update добавлен явный refresh workflow-backed экранов
- workflow status API возвращает `source=framework_cli|fallback`

Ключевые файлы:

- [StatusBar.tsx](/Users/IgorShabanin/dev/DQCR%20Studio/frontend/src/shared/components/StatusBar.tsx)
- [ModelEditorScreen.tsx](/Users/IgorShabanin/dev/DQCR%20Studio/frontend/src/features/model/ModelEditorScreen.tsx)
- [ParametersScreen.tsx](/Users/IgorShabanin/dev/DQCR%20Studio/frontend/src/features/parameters/ParametersScreen.tsx)

---

## 6. EPIC-FWB-05: Observability & Cleanup

Реализовано:

- fallback-случаи логируются единообразно (`workflow.fallback ...`)
- логируется batch rebuild после file changes (`workflow.rebuild.batch ...`)
- операции workflow cache/meta вынесены в отдельный сервис-модуль
- сокращена дублирующая file-based логика параметров
- добавлена документация workflow API:
  - [workflow_api.md](/Users/IgorShabanin/dev/DQCR%20Studio/Docs/workflow_api.md)
- QA checklist:
  - [workflow_regression_checklist.md](/Users/IgorShabanin/dev/DQCR%20Studio/Docs/workflow_regression_checklist.md)
- QA-тесты на `soft-fail/stale/missing/fallback` и multi-model partial rebuild

---

## 7. Verification

Финальная верификация после завершения backlog:

- Backend tests: `25 passed`
- Frontend typecheck: `pnpm --dir frontend exec tsc --noEmit` — passed

---

## 8. Result

Переход на workflow build как primary source для ключевых read-сценариев завершён.  
Fallback сохранён как контролируемый деградационный режим с явной видимостью в API/UI и логах.
