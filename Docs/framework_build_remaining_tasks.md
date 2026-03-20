# DQCR Studio — Tasks по оставшейся интеграции `fw2 build`

**Документ:** `framework_build_remaining_tasks.md`  
**Версия:** 1.0  
**Дата:** Март 2026

> Основано на спецификации: [framework_build_remaining_spec.md](/Users/IgorShabanin/dev/DQCR%20Studio/Docs/framework_build_remaining_spec.md)  
> Этот документ является рабочим backlog для реализации оставшихся пунктов из спецификации.  
> Формат: `[FWB-XXX]` — уникальный ID задачи.  
> Статус: `✅` в колонке ID означает, что задача завершена.  
> Приоритет: 🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low  
> Оценка: SP = Story Points

---

## EPIC-FWB-01: Workflow Cache API

Связанный раздел спецификации:
[framework_build_remaining_spec.md](/Users/IgorShabanin/dev/DQCR%20Studio/Docs/framework_build_remaining_spec.md)

### Backend

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|----|-------------|
| ✅ FWB-001 | Ввести meta-слой для `.dqcr_workflow_cache/<model>.json` | 🔴 | 2 | — |
| ✅ FWB-002 | Хранить `status`, `updated_at`, `error`, `source` для workflow cache | 🔴 | 2 | FWB-001 |
| ✅ FWB-003 | `GET /api/v1/projects/{pid}/workflow/status` | 🔴 | 2 | FWB-002 |
| ✅ FWB-004 | `GET /api/v1/projects/{pid}/models/{mid}/workflow` | 🔴 | 1 | FWB-002 |
| ✅ FWB-005 | `POST /api/v1/projects/{pid}/models/{mid}/workflow/rebuild` | 🔴 | 2 | FWB-002 |
| ✅ FWB-006 | Возвращать `missing/error/stale/ready` для модели и проекта | 🟠 | 2 | FWB-003 |
| ✅ FWB-007 | Логировать workflow rebuild как отдельное бизнес-событие | 🟡 | 1 | FWB-002 |
| ✅ FWB-008 | Покрыть unit/API тестами workflow status endpoints | 🔴 | 2 | FWB-003, FWB-004, FWB-005 |

---

## EPIC-FWB-02: SQL Editor Migration

Связанный раздел спецификации:
[framework_build_remaining_spec.md](/Users/IgorShabanin/dev/DQCR%20Studio/Docs/framework_build_remaining_spec.md)

### Backend

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|----|-------------|
| ✅ FWB-009 | Перевести `config-chain` endpoint на workflow-backed вычисление | 🔴 | 3 | FWB-004 |
| ✅ FWB-010 | Привязать SQL path к конкретному `sql step` в workflow | 🔴 | 2 | FWB-009 |
| ✅ FWB-011 | Использовать `workflow.config` и `sql_model.metadata` как primary source | 🔴 | 2 | FWB-009 |
| ✅ FWB-012 | Оставить явный fallback на file parsing только для отсутствующих полей | 🟠 | 2 | FWB-009 |
| ✅ FWB-013 | Перевести autocomplete параметров на workflow-backed данные | 🔴 | 2 | FWB-004 |
| ✅ FWB-014 | Отдавать в autocomplete контексты из `all_contexts` workflow | 🟠 | 1 | FWB-013 |
| ✅ FWB-015 | Тесты на config-chain и autocomplete поверх workflow cache | 🔴 | 2 | FWB-009, FWB-013 |

### Frontend

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|----|-------------|
| ✅ FWB-016 | Перевести `PriorityChainPanel` на новый workflow-backed API | 🔴 | 2 | FWB-009 |
| ✅ FWB-017 | `Parameters Used` брать из workflow-derived metadata | 🔴 | 1 | FWB-013 |
| ✅ FWB-018 | `CTE Inspector` строить из workflow/cache данных | 🟠 | 1 | FWB-009 |
| ✅ FWB-019 | Показать индикатор `fallback` в SQL Editor | 🟠 | 1 | FWB-016 |
| ✅ FWB-020 | Инвалидировать workflow-backed query после сохранения SQL | 🔴 | 1 | FWB-016 |

---

## EPIC-FWB-03: Build & Validate Alignment

Связанный раздел спецификации:
[framework_build_remaining_spec.md](/Users/IgorShabanin/dev/DQCR%20Studio/Docs/framework_build_remaining_spec.md)

### Backend

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|----|-------------|
| ✅ FWB-021 | Добавить `workflow_updated_at` в validate history/result | 🟠 | 1 | FWB-002 |
| ✅ FWB-022 | Добавить `workflow_updated_at` в generate/build history/result | 🟠 | 1 | FWB-002 |
| ✅ FWB-023 | Связать validate/build с актуальным workflow cache модели | 🟠 | 2 | FWB-021, FWB-022 |
| ✅ FWB-024 | Тесты на связку history ↔ workflow timestamp | 🟡 | 1 | FWB-021, FWB-022 |

### Frontend

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|----|-------------|
| ✅ FWB-025 | Добавить в `BuildScreen` блок `Workflow Build State` | 🔴 | 2 | FWB-003, FWB-004 |
| ✅ FWB-026 | Показать в `BuildScreen` timestamp последнего workflow build | 🟠 | 1 | FWB-025 |
| ✅ FWB-027 | Добавить кнопку `Rebuild Workflow` в `BuildScreen` | 🔴 | 1 | FWB-005, FWB-025 |
| ✅ FWB-028 | Показать ошибку последнего workflow build в `BuildScreen` | 🔴 | 1 | FWB-025 |
| ✅ FWB-029 | Показать workflow timestamp/state в `ValidateScreen` | 🟠 | 1 | FWB-003 |
| ✅ FWB-030 | Отмечать validation как stale, если workflow новее результата | 🟠 | 1 | FWB-021, FWB-029 |

---

## EPIC-FWB-04: Global Workflow UX

Связанный раздел спецификации:
[framework_build_remaining_spec.md](/Users/IgorShabanin/dev/DQCR%20Studio/Docs/framework_build_remaining_spec.md)

### Frontend

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|----|-------------|
| ✅ FWB-031 | Добавить global workflow status в TopBar или StatusBar | 🔴 | 2 | FWB-003 |
| ✅ FWB-032 | Статусы: `ready/building/error/fallback/missing` | 🔴 | 1 | FWB-031 |
| ✅ FWB-033 | Показать build source и timestamp для активной модели | 🟠 | 1 | FWB-031 |
| ✅ FWB-034 | В Model Editor показывать, что данные пришли из workflow build | 🟠 | 1 | FWB-004 |
| ✅ FWB-035 | В Parameters screen показывать источник данных и stale state | 🟠 | 1 | FWB-004 |
| ✅ FWB-036 | После save/update файлов явно рефрешить workflow-backed screens | 🔴 | 2 | FWB-031 |

### Backend

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|----|-------------|
| ✅ FWB-037 | Возвращать `source=framework_cli|fallback` в workflow status API | 🟠 | 1 | FWB-003 |
| ✅ FWB-038 | Явно помечать stale cache при soft-fail rebuild | 🔴 | 2 | FWB-002 |

---

## EPIC-FWB-05: Observability & Cleanup

Связанный раздел спецификации:
[framework_build_remaining_spec.md](/Users/IgorShabanin/dev/DQCR%20Studio/Docs/framework_build_remaining_spec.md)

### Backend

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|----|-------------|
| ✅ FWB-039 | Логировать все случаи fallback вместо workflow-backed ответа | 🟠 | 1 | FWB-003 |
| ✅ FWB-040 | Логировать, какие модели были пересобраны после file changes | 🟡 | 1 | FWB-002 |
| ✅ FWB-041 | Вынести workflow cache/meta операции в отдельный service/module | 🟡 | 2 | FWB-001 |
| ✅ FWB-042 | Сократить дублирующую file-based логику после стабилизации новых API | 🟡 | 3 | FWB-009, FWB-013 |
| ✅ FWB-043 | Документировать окончательный workflow API в `Docs/` | 🟢 | 1 | FWB-003, FWB-004, FWB-005 |

### QA

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|----|-------------|
| ✅ FWB-044 | Составить checklist регрессии для workflow-backed экранов | 🟡 | 1 | FWB-025, FWB-031 |
| ✅ FWB-045 | Проверить сценарии `soft-fail`, `stale`, `missing`, `fallback` | 🔴 | 2 | FWB-038 |
| ✅ FWB-046 | Проверить multi-model проект с частичной пересборкой | 🟠 | 2 | FWB-002 |

---

## Рекомендуемый порядок выполнения

1. `FWB-001` → `FWB-008`
2. `FWB-009` → `FWB-020`
3. `FWB-021` → `FWB-030`
4. `FWB-031` → `FWB-038`
5. `FWB-039` → `FWB-046`

---

## Критерий завершения backlog

Backlog из этого документа можно считать выполненным, если реализованы пункты из спецификации:
[framework_build_remaining_spec.md](/Users/IgorShabanin/dev/DQCR%20Studio/Docs/framework_build_remaining_spec.md)

Минимальный целевой результат:

- есть явный workflow API и workflow status API
- SQL Editor использует workflow-backed данные
- Build/Validate показывают связь с workflow state
- глобальный статус workflow виден в UI
- fallback остаётся только как контролируемый деградационный режим
