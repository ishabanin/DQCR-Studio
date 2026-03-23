# SQL Editor — Спецификация для AI-агента
## DQCR Studio · Улучшение интерфейса на основе Viewer Guide

> **Целевая кодовая база:** React 18 + TypeScript + Vite + Zustand + TanStack Query + Monaco Editor  
> **Frontend feature:** `frontend/src/features/sql/`  
> **Backend:** FastAPI (`backend/app/`)  
> **Дата спеки:** Март 2026

---

## Контекст задачи

Необходимо улучшить существующий SQL Editor в DQCR Studio, добавив четыре функциональных блока, заимствованных из FW Workflow Viewer:

1. **Индикаторы валидации** в левом дереве файлов  
2. **Режимы SQL** — Source / Prepared / Rendered с выбором tool  
3. **Аккордеон метаданных** вместо правой панели @config  
4. **Мульти-таб** для одновременно открытых SQL-файлов  
5. **Полноэкранный режим Monaco** — Monaco на весь экран без отвлекающего UI  

Панель `@config Priority Chain` **полностью удаляется** из SQL Editor.  
Навигация к графу workflow реализована через переход на вкладку **«Линейность»** (`lineage`).

---

## Архитектурный контекст

### Стек и соглашения

- State management: **Zustand** stores, расположены в `frontend/src/app/store/`
- HTTP-запросы: **TanStack Query** (`useQuery`, `useMutation`)
- Стиль кода: TypeScript strict mode, именование компонентов PascalCase, хуков useXxx
- Новые feature-компоненты добавляются в `frontend/src/features/sql/`
- Общие UI-компоненты — в `frontend/src/shared/components/`
- Теминг: CSS-переменные приложения (светлая/тёмная тема уже работают)

### Ключевые источники данных

| Данные | Источник |
|--------|----------|
| Содержимое SQL-файлов | `GET /api/v1/projects/{project_id}/files/content?path={path}` (не `/files` — тот возвращает дерево, не контент) |
| Workflow cache (шаги, metadata, prepared/rendered SQL) | `.dqcr_workflow_cache/<model_id>.json` через Workflow API |
| Результаты валидации | `POST /api/v1/projects/{project_id}/validate` / history |
| Список tools для контекста | `workflow.tools[]` из workflow cache |
| Параметры `{{...}}` SQL-файла | `step.sql_model.metadata.parameters[]` из workflow cache |
| Таблицы SQL-файла | `step.sql_model.metadata.tables` из workflow cache |
| Зависимости шага | `step.dependencies[]` из workflow cache |
| Target table | `workflow.target_table` из workflow cache |
| prepared_sql по tool | `step.sql_model.prepared_sql[tool]` |
| rendered_sql по tool | `step.sql_model.rendered_sql[tool]` |

### Как найти шаг в workflow по SQL-файлу

SQL-файл имеет путь вида `model/<ModelId>/SQL/<folder>/<filename>.sql`.  
В workflow cache шаг идентифицируется через `step.full_name`, который строится как `<folder>/<query_name>` (без расширения `.sql`).

**Алгоритм поиска (важно — один файл может дать несколько шагов):**

1. Отфильтровать все шаги с `step.step_type === 'sql'`
2. Исключить CTE-шаги: `step.full_name` содержит `/cte/` — пропустить
3. Среди оставшихся найти шаги, у которых `step.full_name === '<folder>/<filename_without_ext>'`
4. Если найдено несколько (разворот по контекстам) — выбрать шаг, у которого `step.context` совпадает с текущим активным контекстом workbench (значение из глобального селектора контекста в верхнем баре). Если точного совпадения нет — взять шаг с `step.context === 'all'` или первый найденный.

---

## Задача 1 · Индикаторы валидации в дереве файлов

### Описание

После запуска валидации («Проверить») левый файловый навигатор SQL Editor должен отображать цветные точки-бейджи рядом с именами файлов и папок, указывая на наличие проблем.

### Источник данных валидации

Валидация в DQCR Studio работает через WebSocket (`WS /ws/validation/{project_id}`): сервер стримит события `progress` → `done` / `error`. Результаты после завершения также доступны через `GET /api/v1/projects/{project_id}/validate/history`.

**Важно:** не создавать новую WS-подписку. Читать данные из **существующего validation store**, который уже обновляется приложением при получении WS-событий. Хук `useValidationBadges` должен подписываться только на этот store / TanStack Query кэш — не на сырой WebSocket.

Каждая запись результата содержит:
- `file_path` — путь к файлу с проблемой
- `severity` — `"error"` | `"warning"` | `"info"`
- `message` — текст проблемы

### Требования к компоненту

**Типы индикаторов:**

| Уровень | CSS-цвет | Условие показа |
|---------|----------|----------------|
| `error` | `var(--color-error, #f14c4c)` | Есть хотя бы одна ошибка уровня error |
| `warning` | `var(--color-warning, #d29922)` | Есть warning, нет error |
| `info` | `var(--color-info, #2196f3)` | Только info-уровень |

**Логика пробрасывания:**
- Индикатор отображается на файле с проблемой
- Индикатор отображается на каждой родительской папке вверх по дереву
- Если в папке есть `error` и `warning` — показывается только `error` (высший приоритет)
- При повторной успешной валидации без проблем — индикаторы убираются

**UX:**
- Бейдж — круглая точка диаметром 8px, позиционируется справа от имени файла/папки
- Tooltip на hover: краткий текст проблемы (или «N ошибок», если несколько)
- Индикатор не мешает кликабельности строки дерева

### Файлы для изменения

- `frontend/src/features/sql/components/ProjectTree.tsx` (или аналогичный компонент дерева)
- Добавить хук `useValidationBadges(projectId)` — вычисляет карту `{ filePath: 'error'|'warning'|'info' }` из результатов последней валидации, включая пробрасывание на родителей
- Хук читает данные из существующего validation store / TanStack Query кэша

### Чеклист задачи 1

- [x] Создать хук `useValidationBadges(projectId: string)`, возвращающий `Map<string, 'error' | 'warning' | 'info'>`
- [x] Хук подписывается на validation results из существующего store или `useQuery`
- [x] Хук реализует алгоритм пробрасывания: для каждого `filePath` прописать бейдж на все сегменты пути вверх
- [x] Передать данные хука в компонент дерева файлов
- [x] В компоненте строки дерева рендерить `<ValidationBadge level={level} />` справа от имени
- [x] Компонент `ValidationBadge` использует CSS-переменные темы для цвета
- [x] Tooltip на `ValidationBadge` отображает количество и максимальный уровень проблем
- [x] Покрыть хук `useValidationBadges` unit-тестом: проверить пробрасывание от файла до корня, приоритет error > warning > info
- [x] Убедиться, что при отсутствии результатов валидации — бейджи не рендерятся (нет пустых элементов)

---

## Задача 2 · Режимы SQL: Source / Prepared / Rendered + выбор Tool

### Описание

Добавить три режима просмотра SQL-файла, переключаемые таб-группой над Monaco Editor. Дополнительно — группу переключателей инструмента (tool).

### Режимы

| Режим | Поведение Monaco | Источник данных |
|-------|-----------------|-----------------|
| `source` | Редактируемый (текущее поведение) | Текст файла с диска |
| `prepared` | Read-only + copyable | `step.sql_model.prepared_sql[selectedTool]` из workflow cache |
| `rendered` | Read-only + copyable | `step.sql_model.rendered_sql[selectedTool]` из workflow cache |

**Read-only + copyable означает:**
- `monaco.updateOptions({ readOnly: true })`
- Контекстное меню Monaco остаётся активным (Copy доступен)
- Выделение текста мышью доступно

### Tool selector

- Отображается только в режимах `prepared` и `rendered`
- Скрывается (не просто disabled) в режиме `source`
- Список tools берётся из `workflow.tools[]` текущего workflow cache
- Если workflow cache недоступен — показать заглушку «Кэш недоступен, переключитесь в Source»
- Выбранный tool сохраняется в `localStorage` как `dqcr_sql_editor_selected_tool`

### Состояние панели действий

В режимах `prepared` и `rendered`:
- Кнопки `Save` и `Format` — скрыть (`display: none`) или задизейблить с tooltip «Недоступно в режиме просмотра»
- Индикатор `Saved / Editing` — скрыть
- Чекбокс `Auto validate on save` — скрыть

В режиме `source` — всё как сейчас.

### Позиция переключателя режимов

Разместить таб-группу между breadcrumb-чипами пути и областью Monaco Editor. Использовать существующий стиль чипов/табов приложения.

```
┌─────────────────────────────────────────────────────┐
│ SQL Editor: 001_Query.sql              [←Свернуть]  │
├─────────────────────────────────────────────────────┤
│ [model] / [RF110RestTurnReg] / [SQL] / [001_Query]  │ ← breadcrumbs (без изменений)
├─────────────────────────────────────────────────────┤
│ [Source] [Prepared] [Rendered]   [adb][oracle][pg] [⛶]│ ← НОВАЯ строка, [⛶] = fullscreen
├─────────────────────────────────────────────────────┤
│                                                      │
│           Monaco Editor                              │
│                                                      │
└─────────────────────────────────────────────────────┤
│ Save(Ctrl+S)  Format(Ctrl+Shift+F)  □Auto validate  │ ← скрывается в prepared/rendered
└─────────────────────────────────────────────────────┘
```

**Полноэкранный режим** (подробнее — Задача 5): кнопка `⛶` в правом краю строки режимов разворачивает Monaco на весь экран.

### Файлы для изменения

- `frontend/src/features/sql/` — основной компонент SQL Editor
- Добавить `SqlViewMode` type: `'source' | 'prepared' | 'rendered'`
- Добавить компонент `SqlModeBar` с таб-группой режима и tool-переключателем
- Добавить хук `useSqlViewMode()` — управление режимом + selectedTool + сохранение в localStorage
- Добавить хук `useSqlRenderedContent(filePath, modelId, mode, tool)` — получает нужный SQL из workflow cache по режиму

### Чеклист задачи 2

- [x] Определить тип `SqlViewMode = 'source' | 'prepared' | 'rendered'`
- [x] Создать хук `useSqlViewMode()`: возвращает `{mode, setMode, selectedTool, setSelectedTool}`, сохраняет `selectedTool` в localStorage
- [x] Создать `SqlModeBar` компонент: три таба + условный tool-switcher, использует CSS-переменные темы
- [x] Разместить `SqlModeBar` между breadcrumb и Monaco в компоненте SQL Editor
- [x] Создать хук `useSqlRenderedContent(step, mode, tool)`: возвращает `string | null` — нужный SQL из workflow cache по режиму и tool
- [x] При `mode === 'source'` Monaco работает в режиме редактирования как сейчас
- [x] При `mode !== 'source'` вызывать `editor.updateOptions({ readOnly: true })` и подставлять контент из `useSqlRenderedContent`
- [x] При возврате в `mode === 'source'` восстанавливать `readOnly: false` и оригинальный контент файла
- [x] Скрывать/показывать панель действий (Save / Format / Auto validate) по режиму
- [x] Скрывать tool-switcher при `mode === 'source'`
- [x] Показывать заглушку, если workflow cache отсутствует и режим не `source`
- [x] При смене открытого файла — сбрасывать режим обратно в `source`
- [x] Позиция курсора и скролл сохраняются при переключении режима в рамках одного файла (если технически возможно)

---

## Задача 3 · Аккордеон метаданных вместо @config

### Описание

Правая панель SQL Editor полностью переработана: **@config Priority Chain удалён**, вместо него — аккордеон с метаданными открытого SQL-файла. Данные берутся из workflow cache текущей модели.

### Структура аккордеона

Порядок секций сверху вниз:

#### 3.1 Parameters (N)

- Список параметров `{{param_name}}`, найденных в SQL
- Источник: `step.sql_model.metadata.parameters[]`
- Рендер: чипы-теги в стиле существующих breadcrumb-чипов приложения, с цветом `var(--color-param, #4fc1ff)` или аналогичным из дизайн-системы
- **Поведение клика на чип:** навигация в левом дереве файлов к файлу параметра. Параметр ищется в `parameters/*.yml` (глобальные) и `model/<ModelId>/parameters/*.yml` (model-scoped). Открыть/выделить соответствующий узел дерева.
- Если параметров нет — секция скрыта (не рендерится)

#### 3.2 Tables (N)

- Список таблиц из `FROM` и `JOIN`
- Источник: `step.sql_model.metadata.tables` — объект вида `{ "table_name": { "alias": "s", "is_variable": true, "is_cte": false } }`
- Рендер: строки `alias → table_name` с иконкой типа (переменная / CTE / обычная таблица)
- Если таблиц нет — секция скрыта

#### 3.3 Attributes (N)

- Атрибуты результирующего набора конкретного SQL-запроса
- Источник: `workflow.config.folders.<folder_name>.queries.<query_name>.attributes[]` — атрибуты, заданные для данного конкретного шага в конфигурации
- **Не использовать** `workflow.target_table.attributes[]` как fallback — это атрибуты целевой таблицы всей модели, а не колонки конкретного SELECT; они семантически разные
- Если `attributes[]` для шага пуст или отсутствует — секцию **скрыть**
- Рендер: компактная таблица: Name | Type | Constraints | Dist | Part

#### 3.4 Dependencies (N)

- Шаги workflow, от которых зависит данный SQL
- Источник: `step.dependencies[]` — массив `full_name` зависимых шагов
- Рендер: теги/чипы с `full_name`
- **Поведение клика:** переход на вкладку «Линейность» (`lineage`) приложения — использовать существующий механизм переключения вкладок workbench
- Если зависимостей нет — секция скрыта

#### 3.5 Target Table

- Целевая таблица для данной модели
- Источник: `workflow.target_table.schema + '.' + workflow.target_table.name`
- Рендер: одна строка с иконкой таблицы и полным именем `schema.table`
- Секция показывается всегда, если target_table существует

### Состояния панели

- **Файл не открыт:** панель метаданных не рендерится (показать заглушку «Выберите SQL-файл»)
- **Файл открыт, workflow cache недоступен:** показать сообщение «Метаданные недоступны — workflow cache устарел или не построен»
- **Файл открыт, workflow cache есть, но шаг не найден:** показать «Шаг не найден в workflow»

### Expanded-режим

В expanded-режиме (кнопка «Развернуть»/«Свернуть») панель аккордеона перемещается **ниже** Monaco Editor — сохранить это поведение, которое существовало для @config.

### Секции: поведение по умолчанию

| Секция | Состояние по умолчанию |
|--------|----------------------|
| Parameters | Раскрыта |
| Tables | Раскрыта |
| Attributes | Свёрнута |
| Dependencies | Раскрыта |
| Target Table | Раскрыта |

Состояние раскрытия каждой секции сохраняется в `localStorage` по ключу `dqcr_sql_meta_accordion_<section>`.

### Файлы для изменения

- Удалить компонент правой панели `@config Priority Chain` (или его содержимое)
- Создать `SqlMetaPanel` компонент в `frontend/src/features/sql/components/`
- Создать `SqlMetaAccordion` с дочерними секциями
- Создать хук `useSqlStepMeta(projectId, modelId, filePath)` — находит шаг в workflow cache по filePath и возвращает метаданные

### Чеклист задачи 3

- [x] **Удалить** компонент `@config Priority Chain` из правой панели SQL Editor
- [x] Создать хук `useSqlStepMeta(projectId, modelId, filePath)`:
  - Берёт workflow cache (уже должен быть в TanStack Query кэше)
  - Находит шаг по `full_name` (сопоставление с filePath) с учётом алгоритма из раздела «Как найти шаг»: исключать CTE-шаги, при нескольких совпадениях — выбирать по активному контексту
  - Возвращает `{ step, workflow, status: 'ok'|'no-cache'|'not-found' }`
- [x] Создать компонент `SqlMetaPanel` — контейнер правой панели с тремя состояниями (нет файла / нет кэша / есть данные)
- [x] Создать `AccordionSection` компонент (переиспользуемый): заголовок + контент + состояние раскрытия + localStorage persistence
- [x] Реализовать секцию **Parameters**: чипы `{{param}}` с кликом-навигацией к файлу параметра в дереве
- [x] Логика поиска файла параметра: проверять `parameters/<name>.yml`, затем `model/<modelId>/parameters/<name>.yml`
- [x] Реализовать секцию **Tables**: строки alias/table с иконками типа
- [x] Реализовать секцию **Attributes**: таблица Name|Type|Constraints|Dist|Part; источник — `workflow.config.folders.<folder>.queries.<query>.attributes[]`; если пусто — секция скрыта
- [x] Реализовать секцию **Dependencies**: чипы full_name с кликом-переходом на вкладку `lineage`
- [x] Реализовать секцию **Target Table**: `schema.table` с иконкой
- [x] Состояние по умолчанию каждой секции (см. таблицу выше)
- [x] Сохранение состояния раскрытия в localStorage
- [x] Поддержка expanded-режима: при expanded-состоянии панель рендерится ниже Monaco (сохранить логику из @config)
- [x] При смене открытого файла — панель обновляется под новый файл

---

## Задача 4 · Мульти-таб для SQL-файлов

### Описание

Добавить строку табов для одновременно открытых SQL-файлов. Максимум **20** открытых файлов. Каждый файл открывается в своём табе, переключение между ними не требует повторной загрузки.

### Анатомия таба

```
┌──────────────────────────────────────────────────────┐
│ [📄 001_Query.sql ●] [📄 002_RF110.sql ×]  [📄 ...] │
└──────────────────────────────────────────────────────┘
```

- Иконка типа файла (SQL)
- Имя файла (без пути)
- Точка `●` — несохранённые изменения (dirty state)
- Кнопка `×` — закрыть таб
- Активный таб — выделен (стиль как у существующих tab-компонентов приложения)
- При переполнении строки — горизонтальный скролл

### Поведение

**Открытие файла:**
- Клик на файл в дереве → если таб уже открыт, переключиться на него; если нет — создать новый таб
- Если уже открыто 20 табов → показать `toast`-уведомление «Достигнут лимит открытых файлов (20). Закройте ненужные вкладки.»

**Закрытие таба:**
- Клик `×` → если файл clean (нет unsaved changes) — закрыть без вопросов
- Если файл dirty → показать диалог: «Файл {filename} имеет несохранённые изменения. Закрыть без сохранения?» с кнопками «Сохранить» / «Не сохранять» / «Отмена»
- При закрытии активного таба → активировать соседний таб (правый, если есть, иначе левый)

**Состояние режима SQL (Source/Prepared/Rendered):**
- Каждый таб сохраняет свой режим независимо
- При переключении таба — режим и tool восстанавливаются для этого файла

**Dirty state:**
- Изменение текста в Monaco → пометить таб как dirty (точка `●`)
- Успешное сохранение → убрать dirty
- Переключение на Prepared/Rendered не сбрасывает dirty source-контента

### Хранение состояния табов

Использовать новый Zustand store `useSqlTabsStore`:

```typescript
interface SqlTab {
  id: string           // уникальный id таба
  filePath: string     // полный путь к файлу
  fileName: string     // имя файла для отображения
  isDirty: boolean
  viewMode: SqlViewMode
  selectedTool: string | null
  scrollTop: number    // позиция скролла Monaco для восстановления
}

interface SqlTabsStore {
  tabs: SqlTab[]
  activeTabId: string | null
  openTab: (filePath: string) => void
  closeTab: (tabId: string) => void
  setActiveTab: (tabId: string) => void
  setTabDirty: (tabId: string, isDirty: boolean) => void
  updateTabMode: (tabId: string, mode: SqlViewMode, tool?: string) => void
  updateTabScroll: (tabId: string, scrollTop: number) => void
  clearAllTabs: () => void   // вызывается при смене проекта
}
```

**Персистентность:** табы **не** сохранять в localStorage между сессиями (сессионное состояние). При обновлении страницы список табов сбрасывается.

**Смена проекта:** при переключении на другой проект (событие изменения `currentProjectId` в project store) — вызывать `clearAllTabs()` action, очищающий весь список табов. Открытые файлы предыдущего проекта не должны оставаться в баре.

### Файлы для изменения

- Добавить `useSqlTabsStore` в `frontend/src/app/store/`
- Создать компонент `SqlTabBar` в `frontend/src/features/sql/components/`
- Разместить `SqlTabBar` **между** верхней таб-панелью приложения и областью SQL Editor (над строкой режима Source/Prepared/Rendered)
- Обновить логику открытия файла в дереве — теперь через `useSqlTabsStore.openTab()`

### Чеклист задачи 4

- [x] Создать Zustand store `useSqlTabsStore` с описанным выше интерфейсом
- [x] Создать компонент `SqlTabBar`:
  - Горизонтальный скролл при переполнении
  - Таб: иконка + имя файла + dirty-точка + кнопка закрытия
  - Стиль активного/неактивного таба через CSS-переменные темы
- [x] Разместить `SqlTabBar` в layoute SQL Editor (выше строки режимов)
- [x] Подключить открытие файла из дерева к `openTab()` вместо прямой установки активного файла
- [x] Реализовать лимит 20 файлов с toast-уведомлением (использовать существующий toast/notification механизм приложения)
- [x] Реализовать диалог подтверждения закрытия dirty-таба (использовать существующий `Dialog`/`Modal` компонент)
- [x] Каждый таб хранит `viewMode` и `selectedTool` — при переключении таба восстанавливать
- [x] Dirty-state: подписаться на `onChange` Monaco → вызывать `setTabDirty(tabId, true)`; на успешный save → `setTabDirty(tabId, false)`
- [x] При закрытии активного таба: активировать правый сосед, при отсутствии — левый, при отсутствии — null (пустое состояние)
- [x] При пустом состоянии (нет открытых табов) — показывать заглушку «Select a SQL file in sidebar to start editing» (существующий текст)
- [x] Middleware `useSqlViewMode` обновить: теперь режим хранится в store таба, а не в локальном состоянии компонента
- [x] Добавить `clearAllTabs()` action в store; подписаться на изменение `currentProjectId` в project store и вызывать `clearAllTabs()` при каждой смене проекта

---

## Задача 5 · Полноэкранный режим Monaco

### Описание

Добавить кнопку разворота Monaco Editor на весь экран браузера. В полноэкранном режиме весь UI приложения (верхний бар, дерево, таб-панель приложения, правая панель, нижний статус-бар) скрывается — остаётся только Monaco с минимальной управляющей полоской поверх него.

### Схема полноэкранного режима

```
┌──────────────────────────────────────────────────────────────────┐
│ 001_Query.sql  [Source ▾]  [oracle ▾]  Save  Format  [✕ Выйти]  │ ← floating overlay-бар
├──────────────────────────────────────────────────────────────────┤
│                                                                    │
│                                                                    │
│                     Monaco Editor                                  │
│                   (100vw × 100vh)                                  │
│                                                                    │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### Требования

**Вход в полноэкранный режим:**
- Кнопка `⛶` размещается в правом краю строки режимов `SqlModeBar` (см. Задачу 2)
- Горячая клавиша: **`Ctrl+Shift+Enter`** — `F11` не использовать, он перехватывается браузером до JavaScript и вызывает нативный fullscreen браузера
- Реализация — **CSS-only**, без `document.documentElement.requestFullscreen()`: добавить обёртке Monaco класс `.sql-editor--fullscreen` с `position: fixed; inset: 0; z-index: 1000; width: 100vw; height: 100vh`. Это надёжнее Fullscreen API: нет permission issues, нет конфликта с `Escape` браузера, нет проблем с `fullscreenchange` в iframes
- При входе: скрыть все внешние UI-зоны через CSS-класс на корневом layout-элементе

**Floating overlay-бар (поверх Monaco):**
- Позиционирование: `position: fixed`, прижат к верху экрана, `z-index` выше Monaco
- Фон: полупрозрачный (`background: rgba(var(--bg-secondary-rgb), 0.92)`) с `backdrop-filter: blur(4px)`
- Автоскрытие: бар скрывается через 2 секунды после последнего движения мыши; появляется при любом движении мыши или нажатии клавиши
- Содержимое бара:
  - Имя текущего файла (из активного таба)
  - Компактный переключатель режима (Source / Prepared / Rendered) — те же три кнопки
  - Компактный tool-selector — только при режиме Prepared/Rendered
  - Кнопка `Save` (Ctrl+S)
  - Кнопка `Format` (Ctrl+Shift+F) — только в режиме Source
  - Кнопка `✕ Выйти` — выход из полноэкранного режима

**Выход из полноэкранного режима:**
- Кнопка `✕ Выйти` в overlay-баре
- Клавиша `Escape`
- Поскольку используется CSS-only подход (без Fullscreen API), событие `fullscreenchange` не применяется и не нужно
- При выходе: снять CSS-класс с обёртки и layout-элемента, вызвать `editor.layout()` для перерасчёта размеров Monaco

**Совместимость с режимами SQL (Задача 2):**
- Полноэкранный режим работает во всех трёх режимах: Source, Prepared, Rendered
- В режимах Prepared/Rendered Monaco остаётся `readOnly: true` и в полноэкранном виде
- Переключение режима внутри полноэкранного вида работает через overlay-бар

**Совместимость с мульти-табом (Задача 4):**
- Полноэкранный режим показывает содержимое активного таба
- Смена таба в полноэкранном режиме **не поддерживается** (таб-бар не виден) — для смены файла нужно выйти из полноэкранного режима

**Dirty state в полноэкранном режиме:**
- Индикатор несохранённых изменений (точка `●` или текст «●» рядом с именем файла) виден в overlay-баре
- `Ctrl+S` работает и сохраняет текущий файл

**Состояние в store:**
- Добавить флаг `isFullscreen: boolean` в `useSqlTabsStore` (или отдельный `useSqlEditorStore`)
- `enterFullscreen()` и `exitFullscreen()` — actions в store

### Файлы для изменения

- `frontend/src/features/sql/components/SqlModeBar.tsx` — добавить кнопку `⛶`
- Создать `SqlFullscreenOverlay.tsx` — floating overlay-бар с минимальными контролами
- Создать хук `useSqlFullscreen()` — управление состоянием, Fullscreen API браузера, keyboard shortcuts
- Основной layout-компонент SQL Editor — добавить условный рендеринг полноэкранного режима

### Чеклист задачи 5

- [x] Добавить кнопку `⛶` в правый край `SqlModeBar`
- [x] Создать хук `useSqlFullscreen()`: `{ isFullscreen, enter, exit }` — управляет CSS-классом на обёртке Monaco и корневом layout-элементе, **без** `requestFullscreen` / `exitFullscreen`
- [x] При `isFullscreen === true`: добавить класс `.sql-editor--fullscreen` на обёртку Monaco (`position: fixed; inset: 0; z-index: 1000; width: 100vw; height: 100vh`); добавить класс `.app--editor-fullscreen` на корневой layout для скрытия всех внешних зон (верхний бар, дерево, таб-панель приложения, правая панель, статус-бар, `SqlTabBar`, `SqlModeBar`) через CSS-правила
- [x] Создать `SqlFullscreenOverlay` — floating-бар с автоскрытием (2с после последнего mouseMove)
- [x] В overlay-баре: имя файла, режим, tool-selector (условно), Save, Format (условно), кнопка выхода, dirty-индикатор
- [x] Выход по `Escape` и по кнопке `✕` — `fullscreenchange` не использовать (CSS-only подход)
- [x] Горячая клавиша входа: `Ctrl+Shift+Enter` (`F11` не использовать — перехватывается браузером)
- [x] В режимах Prepared/Rendered в полноэкранном виде Monaco остаётся `readOnly: true`
- [x] Автоскрытие overlay-бара реализовать через `useRef` таймера, сброс при `mousemove` / `keydown`
- [x] Убедиться, что `Ctrl+S` работает в полноэкранном режиме
- [x] При выходе из полноэкранного режима вызывать `editor.layout()` для перерасчёта размеров Monaco
- [x] Полноэкранный режим не ломает состояние режима SQL (viewMode сохраняется после выхода)

---

## Удаление @config Priority Chain

### Описание

@config Priority Chain полностью удаляется из SQL Editor. Никакой скрытой версии, никаких свёрнутых секций — компонент убирается.

### Чеклист удаления @config

- [x] Найти компонент `@config Priority Chain` (возможные имена: `ConfigPriorityChain`, `PriorityChainPanel`, `SqlConfigPanel` или аналог) в `frontend/src/features/sql/`
- [x] Удалить рендеринг компонента из правой панели SQL Editor
- [x] Удалить импорт компонента
- [x] Если компонент нигде больше не используется — удалить файл компонента
- [x] Если удаление компонента ломает expanded-режим (логика переноса правой панели вниз) — перенести эту логику на новый `SqlMetaPanel`
- [x] Убедиться, что удаление не сломало layout (нет пустых `div`-блоков, нет CSS-проблем с шириной)

---

## Общие требования к реализации

### Стиль и темизация

- Все новые компоненты используют CSS-переменные приложения (не хардкодить цвета)
- Светлая/тёмная тема должна работать без дополнительных условий
- Ориентироваться на существующие компоненты как на образец стиля: breadcrumb-чипы, кнопки, табы, аккордеоны в других частях приложения

### Обработка состояний загрузки

- Workflow cache может быть `missing`, `stale`, `building`, `error` — обрабатывать все состояния
- В режимах `prepared`/`rendered` показывать `Skeleton`/спиннер пока данные загружаются
- В аккордеоне метаданных показывать `Skeleton` строки пока workflow cache грузится

### Обратная совместимость

- Существующая функциональность SQL Editor не должна регрессировать:
  - Save (Ctrl+S) работает в режиме Source — в том числе в полноэкранном режиме
  - Format (Ctrl+Shift+F) работает в режиме Source — в том числе в полноэкранном режиме
  - Auto validate on save работает в режиме Source
  - Autocomplete в Monaco работает в режиме Source
  - Expanded-режим работает
  - Полноэкранный режим не конфликтует с Expanded-режимом (они взаимоисключающие: при входе в fullscreen expanded сбрасывается)

### Порядок реализации (рекомендуемый)

1. **Задача удаления @config** — первой, чтобы освободить место и не тащить технический долг
2. **Задача 1 (Валидация)** — независимая, минимальные зависимости
3. **Задача 3 (Аккордеон)** — занимает место удалённого @config
4. **Задача 2 (Режимы SQL)** — требует данных workflow cache
5. **Задача 4 (Мульти-таб)** — наибольший scope, затрагивает state management
6. **Задача 5 (Полноэкранный режим)** — надстройка над готовым Monaco + store из Задач 2 и 4

---

## API endpoints (справочно)

```
# Workflow cache (метаданные, prepared_sql, rendered_sql)
GET /api/v1/projects/{project_id}/workflow?model_id={model_id}&context={context}

# Validation
POST /api/v1/projects/{project_id}/validate
GET  /api/v1/projects/{project_id}/validate/history

# SQL preview по engine (альтернатива workflow cache для rendered SQL)
POST /api/v1/projects/{project_id}/build/{engine}/preview

# Files
GET  /api/v1/projects/{project_id}/files
GET  /api/v1/projects/{project_id}/files/content?path={path}
PUT  /api/v1/projects/{project_id}/files/content  (save)
```

---

## Критерии завершённости (Definition of Done)

- [x] Все 5 задач + удаление @config реализованы
- [x] TypeScript компилируется без ошибок (`tsc --noEmit`)
- [ ] ESLint не выдаёт новых ошибок
- [ ] Светлая и тёмная тема работают корректно для всех новых элементов
- [x] Workflow cache `missing`/`stale` обработан gracefully в режимах Prepared/Rendered и в аккордеоне
- [x] Лимит 20 табов работает с toast-уведомлением
- [x] Диалог подтверждения закрытия dirty-таба работает
- [x] Клик по `{{param}}` чипу открывает/выделяет нужный файл в дереве
- [x] Клик по `Dependencies` чипу переключает на вкладку Линейности
- [x] Полноэкранный режим: Monaco разворачивается на 100vw × 100vh (CSS-only, без Fullscreen API), overlay-бар автоскрывается
- [x] Полноэкранный режим: выход по Escape и кнопке `✕`
- [x] Полноэкранный режим: Ctrl+S сохраняет файл, dirty-индикатор виден в overlay-баре
- [x] Полноэкранный и Expanded режимы взаимоисключающие, не конфликтуют
- [x] После выхода из fullscreen Monaco корректно перерисовывает размеры (`editor.layout()`)
- [x] При смене проекта все открытые табы очищаются (`clearAllTabs`)
- [x] Существующие сценарии не сломаны: Save, Format, Auto validate, Autocomplete, Expanded-режим
- [x] Удалённый @config не оставил визуальных артефактов в layout
