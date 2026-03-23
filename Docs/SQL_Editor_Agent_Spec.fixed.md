# SQL Editor — Исправленная спецификация для AI-агента
## DQCR Studio · Реализация без архитектурных конфликтов

> Целевая кодовая база: React 18 + TypeScript + Vite + Zustand + TanStack Query + Monaco Editor  
> Frontend feature: `frontend/src/features/sql/`  
> Backend: FastAPI (`backend/app/`)  
> Версия документа: 24 марта 2026

---

## Контекст и цель

Нужно улучшить текущий SQL Editor, сохранив устойчивость текущей архитектуры и избегая дублирования store-логики.

Целевые блоки:

1. Индикаторы валидации в дереве файлов (sidebar).
2. Режимы SQL: `Source / Prepared / Rendered` + выбор `tool`.
3. Панель метаданных SQL-шага (аккордеон).
4. Улучшение мульти-таба на базе уже существующего `editorStore`.
5. Полноэкранный режим Monaco (layout-aware).

Требование по `@config`:

- `@config Priority Chain` **скрывается из UI SQL Editor**.
- Удалять backend API и связанные вычисления `config-chain` не требуется в рамках этой задачи.
- Хук/запрос `fetchModelConfigChain` можно оставить для совместимости до отдельного cleanup-этапа.

---

## Что есть в проекте сейчас (факт)

### Frontend, существующие файлы и сущности

- SQL экран: `frontend/src/features/sql/SqlEditorScreen.tsx`
- Store редактора: `frontend/src/app/store/editorStore.ts`
- Store валидации: `frontend/src/app/store/validationStore.ts`
- Sidebar (дерево проекта): `frontend/src/shared/components/Sidebar.tsx`
- App shell/layout: `frontend/src/App.tsx`
- API слой: `frontend/src/api/projects.ts`
- Axios base URL: `frontend/src/api/client.ts` (`/api/v1`)

### Важные текущие детали

- Мульти-таб уже есть (`openFiles`, `activeFilePath`, `dirtyFiles`) в `editorStore`.
- Валидация использует поле `status`, не `severity`:
  - `ValidationRuleResult.status: "pass" | "warning" | "error"`
- `@config Priority Chain` сейчас рендерится внутри `SqlEditorScreen`.
- Глобальные зоны UI (`TopBar`, `Sidebar`, `TabBar`, `StatusBar`, `BottomPanel`) собираются в `App.tsx`.

---

## Реальные API и методы (использовать именно их)

### Frontend API functions (источник истины)

Файл: `frontend/src/api/projects.ts`

- `fetchProjectTree(projectId)` → `GET /projects/{projectId}/files/tree`
- `fetchFileContent(projectId, path)` → `GET /projects/{projectId}/files/content?path=...`
- `saveFileContent(projectId, path, content)` → `PUT /projects/{projectId}/files/content`
- `fetchProjectAutocomplete(projectId, modelId?)` → `GET /projects/{projectId}/autocomplete`
- `fetchModelWorkflow(projectId, modelId)` → `GET /projects/{projectId}/models/{modelId}/workflow`
- `fetchModelConfigChain(projectId, modelId, sqlPath?)` → `GET /projects/{projectId}/models/{modelId}/config-chain`
- `fetchBuildPreview(projectId, engine, payload)` → `POST /projects/{projectId}/build/{engine}/preview`
- `runProjectValidation(projectId, payload?)` → `POST /projects/{projectId}/validate`
- `fetchValidationHistory(projectId)` → `GET /projects/{projectId}/validate/history`

### Backend routes (для проверки контрактов)

- Files router: `backend/app/routers/files.py` (`/projects/{project_id}/files/...`)
- Projects router: `backend/app/routers/projects.py`
  - `GET /{project_id}/models/{model_id}/workflow`
  - `GET /{project_id}/models/{model_id}/config-chain`
  - `POST /{project_id}/build/{build_id}/preview` (`build_id` фактически engine id)
  - `POST /{project_id}/validate`
  - `GET /{project_id}/validate/history`

---

## Архитектурные правила внедрения

1. Не вводить второй store для табов (`useSqlTabsStore`) в этой задаче.
2. Расширять существующий `useEditorStore` минимально и обратно-совместимо.
3. Не дублировать логику дерева: индикаторы валидации добавлять в `Sidebar.tsx`.
4. Полноэкранный режим делать с учётом `App.tsx` (скрытие shell на уровне layout), а не только локально в `SqlEditorScreen`.
5. `@config` скрыть на уровне рендера, не ломая API-контракты и существующие invalidate-цепочки.

---

## Задача 1 · Индикаторы валидации в дереве файлов

### Описание

После выполнения validate отображать цветовой индикатор у файлов и родительских папок в Sidebar.

### Источник данных

- Основной: `useValidationStore().latestRun`
- Тип записи: `ValidationRuleResult` с `status` (`error|warning|pass`), `file_path`, `message`

### Требования

- Приоритет уровней: `error > warning > info`.
- `info` выводить только при наличии явных non-error/non-warning записей (если в данных их нет, `info` не рисуется).
- Для папки уровень вычисляется как max по дочерним узлам.
- Tooltip:
  - если 1 проблема: текст проблемы
  - если много: `N issues (max: error|warning)`
- Индикатор не должен ломать hit-area клика по строке.

### Реализация

- Добавить хук: `frontend/src/features/sql/hooks/useValidationBadges.ts`
- Интегрировать в: `frontend/src/shared/components/Sidebar.tsx`
- Вынести UI-точку: `frontend/src/shared/components/ui/ValidationBadge.tsx`

### Чеклист

- [ ] `useValidationBadges(projectId)` возвращает `Map<string, { level, count, sampleMessage }>`
- [ ] Алгоритм поднимает статус по всем предкам пути
- [ ] В Sidebar рендер бейджа для `file` и `directory`
- [ ] Unit test на хук: приоритет + propagation

---

## Задача 2 · Режимы SQL: Source / Prepared / Rendered + Tool

### Описание

Добавить строку режимов над Monaco:

- `Source` — редактирование как сейчас
- `Prepared` — read-only контент для выбранного tool
- `Rendered` — read-only контент для выбранного tool

### Источник данных

- `fetchModelWorkflow(projectId, modelId)`
- Из `workflow` payload:
  - `workflow.tools[]`
  - `steps[].sql_model.prepared_sql[tool]`
  - `steps[].sql_model.rendered_sql[tool]`

### Правила поиска шага

Для SQL-файла вида `model/<ModelId>/<SQL|workflow>/<folder>/<file>.sql`:

- Сначала матчить по `sql_model.path` (если присутствует в шаге)
- Фолбэк: `step.full_name === <folder>/<filename_without_ext>`

### Поведение UI

- Tool selector показывать только в `Prepared/Rendered`.
- В `Prepared/Rendered` Monaco read-only, но selectable/copyable.
- `Save`, `Format`, `Auto validate on save`, `Saved/Editing` скрывать при read-only режимах.
- Если workflow cache отсутствует: показать fallback-плашку и дать кнопку вернуться в `Source`.

### State

- Не вводить отдельный tabs store.
- Расширить `editorStore`:
  - `fileViewStateByPath[path] = { mode, selectedTool }`
- Дефолт при первом открытии файла: `{ mode: "source", selectedTool: lastToolFromLocalStorageOrNull }`

### Реализация

- `frontend/src/features/sql/components/SqlModeBar.tsx`
- `frontend/src/features/sql/hooks/useSqlViewState.ts`
- `frontend/src/features/sql/hooks/useSqlWorkflowStep.ts`
- обновления в `frontend/src/features/sql/SqlEditorScreen.tsx`

### Чеклист

- [ ] Добавлен `SqlViewMode = "source" | "prepared" | "rendered"`
- [ ] Состояние режима хранится per file в `editorStore`
- [ ] Переключение режима не теряет draft и dirty source
- [ ] Tool сохраняется в `localStorage` ключом `dqcr_sql_editor_selected_tool`
- [ ] Работа в light/dark без отдельных theme-веток

---

## Задача 3 · Панель метаданных SQL-шага (вместо @config в UI)

### Описание

Правая панель SQL Editor: показывать метаданные шага workflow в формате аккордеона.

`@config Priority Chain` из UI не показывать.

### Секции

1. `Parameters (N)`
2. `Tables (N)`
3. `Attributes (N)`
4. `Dependencies (N)`
5. `Target Table`

### Источники данных

- `fetchModelWorkflow(...).workflow`
- Поля шага:
  - `step.sql_model.metadata.parameters[]`
  - `step.sql_model.metadata.tables`
  - `step.sql_model.attributes[]` (или fallback `workflow.target_table.attributes[]`)
  - `step.dependencies[]`
- Глобально:
  - `workflow.target_table`

### Интеракции

- Клик по parameter chip: открыть файл параметра через существующий `openFile(path)`:
  - проверять `parameters/<name>.yml`
  - затем `model/<ModelId>/parameters/<name>.yml`
- Клик по dependency: `setLineageTarget(...)` + `setActiveTab("lineage")`

### Состояния

- Нет файла: стандартная empty-state
- Нет workflow cache: сообщение о недоступности метаданных
- Шаг не найден: явная плашка `Step not found in workflow`

### Реализация

- `frontend/src/features/sql/components/SqlMetaPanel.tsx`
- `frontend/src/features/sql/components/SqlMetaAccordion.tsx`
- `frontend/src/features/sql/hooks/useSqlStepMeta.ts`
- Скрыть рендер `PriorityChainPanel` в `SqlEditorScreen.tsx`

### Чеклист

- [ ] `@config` блок не рендерится
- [ ] Аккордеон секций рендерится по наличию данных
- [ ] Состояние раскрытия секций хранится в `localStorage` (`dqcr_sql_meta_accordion_<section>`)
- [ ] Expanded-режим продолжает переносить мета-панель вниз

---

## Задача 4 · Мульти-таб (эволюция существующей реализации)

### Описание

Улучшить текущие табы SQL-файлов (`FileTabs`) без замены базового store.

### Поведение

- Лимит 20 открытых файлов.
- При достижении лимита: toast и отказ открытия нового файла.
- Закрытие dirty файла: confirm dialog `Save / Don't save / Cancel`.
- При закрытии активного таба: активировать правый сосед, иначе левый.

### Что уже есть и что доработать

Уже есть:

- `openFiles`
- `activeFilePath`
- `dirtyFiles`
- reorder drag/drop

Добавить:

- `closeFileWithStrategy(path, strategy)` или эквивалентную логику в UI
- `MAX_SQL_TABS = 20`
- per-file `mode/tool` (см. Задача 2)

### Реализация

- `frontend/src/app/store/editorStore.ts`
- `frontend/src/features/sql/SqlEditorScreen.tsx`
- при необходимости: `frontend/src/features/sql/components/SqlTabBar.tsx`

### Чеклист

- [ ] Нет второго store для табов
- [ ] Лимит 20 работает
- [ ] dirty-confirm работает
- [ ] Режим/tool восстанавливаются на уровне файла

---

## Задача 5 · Полноэкранный режим Monaco

### Описание

Добавить fullscreen режим, который фокусирует пользователя на Monaco и скрывает внешний shell.

### Архитектурный принцип

Т.к. shell-элементы находятся в `App.tsx`, флаг fullscreen должен быть доступен на уровне layout.

### Реализация

- Store:
  - добавить `sqlFullscreen: boolean` в `useUiStore` или `useEditorStore`
- Layout:
  - в `frontend/src/App.tsx` условно скрывать `TopBar/Sidebar/TabBar/BottomPanel/StatusBar`
- SQL screen:
  - `SqlFullscreenOverlay` + горячие клавиши
  - кнопка входа в fullscreen в `SqlModeBar`

### UX

- Вход: кнопка `⛶` + shortcut (`Ctrl+Shift+Enter`, `F11` как optional)
- Выход: `Esc`, кнопка `Exit`, `fullscreenchange`
- В fullscreen сохраняются режимы `Source/Prepared/Rendered`
- В `Prepared/Rendered` editor остаётся read-only
- `Ctrl+S` работает в `Source`

### Чеклист

- [ ] Fullscreen не ломает expanded-mode
- [ ] После выхода вызывается `editor.layout()`
- [ ] Overlay autohide работает стабильно

---

## Порядок реализации

1. Скрыть `@config` из UI + метапанель (Задача 3)
2. Validation badges в Sidebar (Задача 1)
3. Режимы SQL + tool (Задача 2)
4. Доработка существующих табов (Задача 4)
5. Fullscreen на уровне App shell (Задача 5)

---

## Definition of Done

- [ ] `@config Priority Chain` не виден в SQL Editor UI
- [ ] Новая метапанель работает для открытого SQL
- [ ] Sidebar показывает индикаторы validate
- [ ] Режимы `Source/Prepared/Rendered` корректны и не ломают save/format в `Source`
- [ ] Мульти-таб без второго store, лимит 20 и dirty-confirm
- [ ] Fullscreen скрывает shell через layout-level управление
- [ ] TS/ESLint проходят без новых ошибок
- [ ] Базовые пользовательские сценарии SQL editor не регрессировали

---

## Что изменено и почему (для AI-агента)

### 1) Убран конфликт store-архитектуры

Изменено:

- Не использовать новый `useSqlTabsStore`.
- Использовать и расширять текущий `useEditorStore`.

Почему:

- В проекте уже есть рабочая модель табов (`openFiles`, `activeFilePath`, `dirtyFiles`).
- Второй store создаст рассинхрон и рост багов при переключении/закрытии файлов.

### 2) Исправлен контракт валидации

Изменено:

- Источник уровня проблем: `ValidationRuleResult.status`.
- `severity` не использовать как обязательное поле.

Почему:

- Реальный контракт фронта и текущий код SQL/Validate экранов работают через `status`.

### 3) Уточнены реальные API-методы

Изменено:

- Добавлены конкретные frontend function names и backend routes из кода.

Почему:

- AI-агент должен опираться на реально существующие вызовы, чтобы не внедрять несуществующие endpoint’ы.

### 4) Исправлена логика fullscreen

Изменено:

- Fullscreen описан как layout-level задача с изменением `App.tsx`.

Почему:

- Локально в `SqlEditorScreen` нельзя корректно скрыть `TopBar/Sidebar/StatusBar`, так как они рендерятся выше в дереве.

### 5) `@config` скрыт из UI, но не ломает совместимость

Изменено:

- `@config` удалён из рендера SQL Editor UI.
- Backend/API cleanup отложен и вынесен за рамки текущей задачи.

Почему:

- Выполняет продуктовое требование “не показывать @config”, но не добавляет риск поломки связанных API/логики в других частях приложения.

### 6) Убрана внутренняя логическая коллизия режима

Изменено:

- Режим (`mode/tool`) хранится per-file и восстанавливается при переключении табов.
- Принудительный глобальный сброс режима при смене файла не используется.

Почему:

- Иначе противоречие с UX мульти-таба и потеря контекста пользователя.
