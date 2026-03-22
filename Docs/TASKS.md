# DQCR Studio — Перечень задач (Backlog)

**Документ:** `TASKS.md`  
**Версия:** 1.0  
**Дата:** Март 2026

> Формат: `[КОМПОНЕНТ-NNN]` — уникальный ID задачи.  
> Статус: `✅` в колонке ID означает, что задача завершена.  
> Приоритет: 🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low  
> Оценка: SP = Story Points (1 SP ≈ 1 день работы одного разработчика)

---

## EPIC-01: Foundation & Infrastructure

### INFRA — DevOps / CI / CD

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|-----|------------|
| INFRA-001 ✅ | Создать monorepo (frontend/, backend/, docker/) с общим package.json/pyproject | 🔴 | 1 | — |
| INFRA-002 ✅ | Docker Compose: frontend (Nginx), backend (FastAPI), volumes | 🔴 | 2 | INFRA-001 |
| INFRA-003 ✅ | Nginx конфигурация: static files, proxy /api, WebSocket upgrade | 🔴 | 1 | INFRA-002 |
| INFRA-004 | GitHub Actions: lint (eslint + ruff), unit tests, Docker build | 🟠 | 2 | INFRA-001 |
| INFRA-005 | GitHub Actions: deploy to staging on merge to main | 🟡 | 2 | INFRA-004 |
| INFRA-006 ✅ | Makefile: `make dev`, `make build`, `make test`, `make deploy` | 🟡 | 1 | INFRA-002 |
| INFRA-007 ✅ | Health check endpoints: `/health` (liveness) и `/ready` (readiness) | 🟠 | 1 | BE-001 |
| INFRA-008 ✅ | Structured JSON logging в Backend | 🟡 | 1 | BE-001 |
| INFRA-009 ✅ | Environment variables validation при старте (missing vars → fail fast) | 🟠 | 1 | BE-001 |
| INFRA-010 ✅ | Docker image hardening: non-root user, minimal base image | 🟡 | 1 | INFRA-002 |

### BE — Backend Scaffold

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|-----|------------|
| BE-001 ✅ | FastAPI app: main.py, CORS, lifespan, exception handlers | 🔴 | 1 | INFRA-001 |
| BE-002 ✅ | Pydantic settings (config.py): все env vars с validation | 🔴 | 1 | BE-001 |
| BE-003 ✅ | File System API: path traversal prevention, base_path validation | 🔴 | 2 | BE-001 |
| BE-004 ✅ | FWService: обёртка `load_project`, `load_model`, `TemplateRegistry` | 🔴 | 3 | BE-001 |
| BE-005 ✅ | FWService: `get_lineage(project, model)` → LineageResponse | 🔴 | 3 | BE-004 |
| BE-006 ✅ | FWService: `run_validation(project, model, rules)` → ValidationResult | 🔴 | 2 | BE-004 |
| BE-007 ✅ | FWService: `run_generation(project, model, engine, context)` → BuildResult | 🔴 | 2 | BE-004 |
| BE-008 ✅ | Pydantic schemas: Project, Model, Parameter, ValidationResult, BuildResult | 🔴 | 2 | BE-001 |
| BE-009 ✅ | Глобальный error handler: FW-исключения → HTTP 4xx/5xx с деталями | 🟠 | 1 | BE-001 |
| BE-010 ✅ | API versioning: все роутеры под /api/v1/ | 🟠 | 1 | BE-001 |

### FE — Frontend Scaffold

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|-----|------------|
| FE-001 ✅ | Vite + React 18 + TypeScript 5: базовый scaffold | 🔴 | 1 | INFRA-001 |
| FE-002 ✅ | Zustand stores: projectStore, editorStore, uiStore | 🔴 | 2 | FE-001 |
| FE-003 ✅ | React Query client + axios instance с auth interceptor | 🔴 | 1 | FE-001 |
| FE-004 ✅ | CSS переменные (design tokens): цвета, радиусы, типографика | 🔴 | 1 | FE-001 |
| FE-005 ✅ | ThemeProvider: light/dark mode с localStorage persistence | 🟠 | 1 | FE-004 |
| FE-006 ✅ | Базовые UI компоненты: Button, Badge, Input, Select, Tooltip | 🟠 | 2 | FE-004 |
| FE-007 ✅ | ErrorBoundary + глобальный toast (sonner или react-hot-toast) | 🟠 | 1 | FE-001 |

---

## EPIC-02: Layout & Navigation

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|-----|------------|
| LAYOUT-001 ✅ | TopBar компонент: логотип, кнопки Validate и Build | 🔴 | 2 | FE-004 |
| LAYOUT-002 ✅ | TopBar: переключатель проектов — выпадающий список + API | 🔴 | 2 | BE-011, FE-002 |
| LAYOUT-003 ✅ | TopBar: переключатель контекста (single + multi) | 🔴 | 2 | LAYOUT-002 |
| LAYOUT-004 ✅ | Sidebar: дерево файлов из API, группировка по типу | 🔴 | 3 | BE-012 |
| LAYOUT-005 ✅ | Sidebar: иконки по типу файла (yml, sql, folder) | 🟡 | 1 | LAYOUT-004 |
| LAYOUT-006 ✅ | Sidebar: контекстное меню (переименовать, удалить, открыть) | 🟠 | 2 | LAYOUT-004 |
| LAYOUT-007 ✅ | Sidebar: подсветка активного файла (левая полоса + bg) | 🟠 | 1 | LAYOUT-004 |
| LAYOUT-008 ✅ | Sidebar: collapsible (кнопка свернуть/развернуть) | 🟢 | 1 | LAYOUT-004 |
| LAYOUT-009 ✅ | TabBar: 6 вкладок, active state, переключение | 🔴 | 1 | FE-002 |
| LAYOUT-010 ✅ | BottomPanel: Terminal/Logs/Output вкладки, toggle высоты | 🔴 | 2 | TERMINAL-001 |
| LAYOUT-011 ✅ | StatusBar: постоянные данные (проект, контекст, шаблон, статус) | 🟠 | 1 | FE-002 |
| LAYOUT-012 ✅ | Keyboard shortcuts: Ctrl+1..6 для вкладок | 🟡 | 1 | LAYOUT-009 |
| BE-011 ✅ | `GET /api/v1/projects` — список проектов | 🔴 | 1 | BE-001 |
| BE-012 ✅ | `GET /api/v1/projects/{pid}/files/tree` — дерево файлов | 🔴 | 2 | BE-003 |
| BE-013 ✅ | `POST/DELETE /api/v1/projects/{pid}/files/rename` — переименование | 🟠 | 1 | BE-003 |
| BE-014 ✅ | `DELETE /api/v1/projects/{pid}/files` — удаление | 🟠 | 1 | BE-003 |

---

## EPIC-03: Lineage Screen

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|-----|------------|
| LIN-001 ✅ | `GET /api/v1/projects/{pid}/models/{mid}/lineage` — API | 🔴 | 2 | BE-005 |
| LIN-002 ✅ | LineageScreen: загрузка данных, loading/error states | 🔴 | 1 | LIN-001 |
| LIN-003 ✅ | DagGraph: React Flow + Dagre auto-layout (horizontal) | 🔴 | 3 | FE-001 |
| LIN-004 ✅ | FolderNode: кастомный узел (заголовок, бейдж, SQL-чипы) | 🔴 | 3 | LIN-003 |
| LIN-005 ✅ | Edge: styled arrows с маркерами, цветовое кодирование | 🟠 | 2 | LIN-003 |
| LIN-006 ✅ | DetailPanel: slideover при клике на узел | 🟠 | 2 | LIN-004 |
| LIN-007 ✅ | DetailPanel: материализация, параметры, CTE, quick-navigate | 🟠 | 2 | LIN-006 |
| LIN-008 ✅ | Режим вертикальный (Dagre direction TB) | 🟡 | 1 | LIN-003 |
| LIN-009 ✅ | Режим компактный (без аннотаций, только имена) | 🟡 | 1 | LIN-004 |
| LIN-010 ✅ | ContextFilter: фильтр disabled-папок по контексту | 🟠 | 2 | LIN-003, LAYOUT-003 |
| LIN-011 ✅ | SummaryBadges: счётчики folders / queries / params | 🟡 | 1 | LIN-002 |
| LIN-012 ✅ | Export PNG (html-to-image или React Flow toBlob) | 🟢 | 2 | LIN-003 |
| LIN-013 ✅ | Search/filter по именам узлов | 🟢 | 2 | LIN-003 |
| LIN-014 ✅ | Zoom controls + fit to screen | 🟡 | 1 | LIN-003 |

---

## EPIC-04: SQL Editor

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|-----|------------|
| SQL-001 ✅ | Monaco Editor базовая интеграция (@monaco-editor/react) | 🔴 | 1 | FE-001 |
| SQL-002 ✅ | DQCR Language Definition: @config, {{ }}, параметры | 🔴 | 3 | SQL-001 |
| SQL-003 ✅ | Автодополнение: параметры из API, макросы, ключи @config | 🔴 | 3 | SQL-002, BE-015 |
| SQL-004 ✅ | FileTabs: открытые файлы, unsaved indicator (●), закрыть | 🔴 | 2 | FE-002 |
| SQL-005 ✅ | `GET/PUT /api/v1/projects/{pid}/files/content` — чтение/запись | 🔴 | 1 | BE-003 |
| SQL-006 ✅ | Ctrl+S → сохранение файла + очистка dirty state | 🔴 | 1 | SQL-004, SQL-005 |
| SQL-007 ✅ | Breadcrumb навигация: кликабельные сегменты пути | 🟠 | 1 | SQL-004 |
| SQL-008 ✅ | `GET /api/v1/.../config-chain` — данные Priority Chain | 🔴 | 2 | BE-004 |
| SQL-009 ✅ | ConfigInspector: PriorityChain компонент | 🔴 | 2 | SQL-008 |
| SQL-010 ✅ | ConfigInspector: ParametersUsed (parse {{ }} из SQL) | 🟠 | 2 | SQL-009, BE-015 |
| SQL-011 ✅ | ConfigInspector: CteInspector секция | 🟠 | 1 | SQL-009 |
| SQL-012 ✅ | ConfigInspector: GeneratedOutput с кнопкой Preview ▶ | 🟠 | 2 | SQL-009, BE-016 |
| SQL-013 ✅ | F12 → navigate to parameter/macro definition | 🟡 | 2 | SQL-002 |
| SQL-014 ✅ | Find & Replace панель (Ctrl+H) | 🟡 | 1 | SQL-001 |
| SQL-015 ✅ | Format SQL (Ctrl+Shift+F) через prettier-sql | 🟡 | 1 | SQL-001 |
| SQL-016 ✅ | Ctrl+P → QuickOpen файлов проекта | 🟡 | 2 | LAYOUT-004 |
| SQL-017 ✅ | Drag-and-drop вкладок для изменения порядка | 🟢 | 1 | SQL-004 |
| BE-015 ✅ | `GET /api/v1/projects/{pid}/autocomplete` — данные для автодополнения | 🔴 | 2 | BE-004 |
| BE-016 ✅ | `POST /api/v1/projects/{pid}/build/{bid}/preview` — preview SQL | 🟠 | 2 | BE-007 |

---

## EPIC-05: Validate Screen

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|-----|------------|
| VAL-001 ✅ | `POST /api/v1/projects/{pid}/validate` — запуск валидации | 🔴 | 2 | BE-006 |
| VAL-002 ✅ | `GET /api/v1/projects/{pid}/validate/history` | 🟠 | 1 | VAL-001 |
| VAL-003 ✅ | ValidateScreen: SummaryBar (3 счётчика + фильтрация) | 🔴 | 2 | VAL-001 |
| VAL-004 ✅ | CategoryGroup: раскрывающаяся группа правил | 🔴 | 2 | VAL-003 |
| VAL-005 ✅ | RuleRow: статус, текст, файл, кнопка навигации | 🔴 | 2 | VAL-004 |
| VAL-006 ✅ | Навигация к файлу при клике на ошибку (open + scroll to line) | 🔴 | 2 | VAL-005, SQL-004 |
| VAL-007 ✅ | Фильтры: All / Passed / Warn / Errors | 🟠 | 1 | VAL-003 |
| VAL-008 ✅ | CategoryFilter: выбор категорий правил перед запуском | 🟠 | 2 | VAL-001 |
| VAL-009 ✅ | QuickFix кнопка + `POST /validate/quickfix` API | 🟠 | 3 | VAL-005 |
| VAL-010 ✅ | QuickFix реализация: `add_field` патч (description атрибута) | 🟠 | 2 | VAL-009 |
| VAL-011 ✅ | QuickFix реализация: `rename_folder` патч | 🟡 | 1 | VAL-009 |
| VAL-012 ✅ | История запусков (последние 5) | 🟡 | 2 | VAL-002 |
| VAL-013 ✅ | Inline подсветка ошибок в SQL Monaco (squiggles) | 🟡 | 2 | VAL-006, SQL-001 |
| VAL-014 ✅ | WebSocket прогресс валидации (WS /ws/validation/{pid}) | 🟡 | 2 | VAL-001 |
| VAL-015 ✅ | Автозапуск валидации при сохранении файла (opt-in) | 🟢 | 1 | VAL-001, SQL-006 |

---

## EPIC-06: Model Editor

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|-----|------------|
| ME-001 ✅ | `GET /api/v1/schema/model-yml` — JSON Schema для model.yml | 🔴 | 2 | BE-004 |
| ME-002 ✅ | `GET /api/v1/projects/{pid}/models/{mid}` — модель как объект | 🔴 | 1 | BE-004 |
| ME-003 ✅ | `PUT /api/v1/projects/{pid}/models/{mid}` — сохранение | 🔴 | 1 | BE-004 |
| ME-004 ✅ | TargetTableSection: Name, Schema, Description, Template, Engine | 🔴 | 2 | ME-001 |
| ME-005 ✅ | AttributesTable: react-table с колонками Name/Type/Flags/Default | 🔴 | 3 | ME-004 |
| ME-006 ✅ | AttributesTable: drag-and-drop строк (dnd-kit) | 🟠 | 2 | ME-005 |
| ME-007 ✅ | AttributesTable: inline-редактирование ячеек | 🟠 | 2 | ME-005 |
| ME-008 ✅ | AttributesTable: Add row, Delete row | 🟠 | 1 | ME-005 |
| ME-009 ✅ | WorkflowFolders: список с materialization dropdown | 🔴 | 2 | ME-004 |
| ME-010 ✅ | WorkflowFolders: enabled toggle, description field | 🟠 | 1 | ME-009 |
| ME-011 ✅ | WorkflowFolders: Add folder диалог с выбором паттерна | 🟠 | 2 | ME-009 |
| ME-012 ✅ | WorkflowFolders: drag-and-drop для изменения порядка | 🟡 | 1 | ME-009 |
| ME-013 ✅ | CteSettings: default + by_context таблица | 🟠 | 2 | ME-004 |
| ME-014 ✅ | SyncEngine: `formToYaml()` — форма → валидный YAML | 🔴 | 3 | ME-001 |
| ME-015 ✅ | SyncEngine: `yamlToForm()` — YAML → форма с AJV валидацией | 🔴 | 3 | ME-014 |
| ME-016 ✅ | YamlPreview: Monaco YAML с readonly в visual-mode | 🔴 | 2 | ME-014 |
| ME-017 ✅ | ModeSwitcher [Visual\|YAML]: переключение + state сохранение | 🔴 | 1 | ME-016 |
| ME-018 ✅ | SyncBadge: synced / syncing / conflict индикатор | 🔴 | 1 | ME-015 |
| ME-019 ✅ | YAML-mode: Monaco editable + `yamlToForm()` при изменении | 🔴 | 2 | ME-015, ME-016 |
| ME-020 ✅ | YAML-mode: блокировка переключения при conflict | 🟠 | 1 | ME-018 |
| ME-021 ✅ | Контекстная помощь (?) тултипы для каждого поля | 🟡 | 2 | ME-004 |
| ME-022 ✅ | Debouncing: 150ms form→yaml, 300ms yaml→form | 🔴 | 1 | ME-014 |
| ME-023 | Удалить `fields` из `ModelObjectResponse`, backend payload и JSON Schema model.yml | 🔴 | 3 | ME-001, ME-002, ME-003 |
| ME-024 | Перенести импорт из каталога в `AttributesTable` вместо отдельного блока `Fields` | 🔴 | 3 | ME-005, ME-023 |
| ME-025 | Удалить секцию `Fields` и связанный diff/highlight UI из Model Editor | 🟠 | 2 | ME-024 |
| ME-026 | Обновить сериализацию/парсинг model.yml: писать и читать только `target_table.attributes` | 🔴 | 3 | ME-023, ME-014, ME-015 |
| ME-027 | Обновить autocomplete target table: использовать только `target_table.attributes` | 🔴 | 2 | ME-023 |
| ME-028 | Обеспечить backward compatibility для legacy `fields` при чтении старых model.yml | 🟠 | 2 | ME-026 |
| ME-029 | Переписать backend/unit/e2e тесты под модель без `fields` | 🔴 | 3 | ME-023, ME-024, ME-026, ME-027 |

---

## EPIC-07: Parameters Screen

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|-----|------------|
| PARAM-001 ✅ | `GET /api/v1/projects/{pid}/parameters` | 🔴 | 1 | BE-004 |
| PARAM-002 ✅ | `POST /api/v1/projects/{pid}/parameters` — создание | 🔴 | 1 | PARAM-001 |
| PARAM-003 ✅ | `PUT /api/v1/projects/{pid}/parameters/{p}` — обновление | 🔴 | 1 | PARAM-001 |
| PARAM-004 ✅ | `DELETE /api/v1/projects/{pid}/parameters/{p}` | 🟠 | 1 | PARAM-001 |
| PARAM-005 ✅ | `POST /api/v1/projects/{pid}/parameters/{p}/test` | 🟠 | 2 | PARAM-001 |
| PARAM-006 ✅ | ParameterList: sidebar global/local с разделителями | 🔴 | 2 | PARAM-001 |
| PARAM-007 ✅ | BasicFields форма: name, description, domain_type, scope | 🔴 | 2 | PARAM-006 |
| PARAM-008 ✅ | ValuesTable: строки контекст → тип → значение | 🔴 | 3 | PARAM-007 |
| PARAM-009 ✅ | DynamicSqlEditor: Monaco в поле SQL dynamic-значения | 🟠 | 2 | PARAM-008, SQL-001 |
| PARAM-010 ✅ | TestButton: вызов API + показ результата | 🟠 | 2 | PARAM-005, PARAM-008 |
| PARAM-011 ✅ | ValuePreview: resolved значение для активного контекста | 🟠 | 1 | PARAM-008 |
| PARAM-012 ✅ | YAML-превью параметра (readonly Monaco) | 🟡 | 1 | PARAM-007 |
| PARAM-013 ✅ | Add context строка в ValuesTable | 🟠 | 1 | PARAM-008 |

---

## EPIC-08: Build & Output Screen

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|-----|------------|
| BUILD-001 ✅ | `POST /api/v1/projects/{pid}/build` | 🔴 | 2 | BE-007 |
| BUILD-002 ✅ | `GET /api/v1/projects/{pid}/build/history` | 🟠 | 1 | BUILD-001 |
| BUILD-003 ✅ | `GET /api/v1/projects/{pid}/build/{bid}/files` | 🔴 | 1 | BUILD-001 |
| BUILD-004 ✅ | `GET /api/v1/projects/{pid}/build/{bid}/download` — ZIP | 🟠 | 2 | BUILD-003 |
| BUILD-005 ✅ | BuildConfig: EngineSelector (radio/segmented), ContextSelector | 🔴 | 2 | BUILD-001 |
| BUILD-006 ✅ | BuildConfig: DryRun checkbox, OutputPath field, ModelSelector | 🟠 | 2 | BUILD-005 |
| BUILD-007 ✅ | WebSocket /ws/build/{pid} — прогресс сборки | 🟠 | 2 | BUILD-001 |
| BUILD-008 ✅ | OutputTree: дерево файлов + file viewer (Monaco readonly) | 🔴 | 2 | BUILD-003 |
| BUILD-009 ✅ | Download кнопка для файла и ZIP | 🟠 | 1 | BUILD-004 |
| BUILD-010 ✅ | Diff-view: сравнение с предыдущей сборкой | 🟡 | 3 | BUILD-002, SQL-001 |
| BUILD-011 ✅ | BuildHistory: список сборок с restore | 🟡 | 2 | BUILD-002 |

---

## EPIC-09: Terminal

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|-----|------------|
| TERMINAL-001 ✅ | xterm.js интеграция (xterm + xterm-addon-fit) | 🔴 | 2 | FE-001 |
| TERMINAL-002 ✅ | WebSocket клиент для /ws/terminal/{sid} | 🔴 | 1 | TERMINAL-001 |
| TERMINAL-003 ✅ | PTY сервис: ptyprocess, create/destroy session | 🔴 | 3 | BE-001 |
| TERMINAL-004 ✅ | WS /ws/terminal/{sid} — bidirectional PTY stream | 🔴 | 2 | TERMINAL-003 |
| TERMINAL-005 ✅ | CLI трансляция: каждый API-вызов логирует команду в terminal | 🔴 | 2 | TERMINAL-004 |
| TERMINAL-006 ✅ | Terminal вкладки: Terminal, Logs, Output | 🟠 | 1 | TERMINAL-001 |
| TERMINAL-007 ✅ | Цветовое кодирование вывода (ANSI colors) | 🟠 | 1 | TERMINAL-001 |
| TERMINAL-008 ✅ | Resize: fit-addon при изменении размера панели | 🟠 | 1 | TERMINAL-001 |
| TERMINAL-009 ✅ | История команд (↑/↓) | 🟡 | 1 | TERMINAL-001 |
| TERMINAL-010 ✅ | Clear terminal (Ctrl+L) | 🟡 | 1 | TERMINAL-001 |

---

## EPIC-10: Project Creation Wizard

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|-----|------------|
| WIZ-001 ✅ | `POST /api/v1/projects` — создание проекта из wizard data | 🔴 | 3 | BE-004 |
| WIZ-002 ✅ | WizardModal: 4-шаговый stepper с индикатором прогресса | 🔴 | 2 | FE-002 |
| WIZ-003 ✅ | Step1Config: Name, Description, Template cards, Properties table | 🔴 | 3 | WIZ-002 |
| WIZ-004 ✅ | Step2Contexts: default.yml auto + Add context форма | 🟠 | 2 | WIZ-002 |
| WIZ-005 ✅ | Step3Model: имя модели, атрибуты, первая папка | 🟠 | 3 | WIZ-002 |
| WIZ-006 ✅ | Step4Confirm: превью директорий + YAML + кнопка создать | 🟠 | 2 | WIZ-002 |
| WIZ-007 ✅ | LivePreview: правая панель с YAML и tree структурой | 🟠 | 2 | WIZ-003 |
| WIZ-008 ✅ | Шаблонные карточки с описаниями (flx / dwh_mart / dq_control) | 🟠 | 1 | WIZ-003 |
| WIZ-009 ✅ | Inline валидация всех полей wizard | 🟠 | 2 | WIZ-003 |

---

## EPIC-11: Admin Interface

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|-----|------------|
| ADMIN-001 ✅ | AdminLayout с role-gating (только admin) | 🟠 | 1 | AUTH-003 |
| ADMIN-002 ✅ | `GET/PUT /api/v1/admin/templates/{name}` | 🟠 | 2 | BE-004 |
| ADMIN-003 ✅ | TemplateManager: список + Monaco YAML редактор шаблона | 🟠 | 3 | ADMIN-002 |
| ADMIN-004 ✅ | TemplateManager: rules.folders таблица | 🟡 | 2 | ADMIN-003 |
| ADMIN-005 ✅ | `GET/PUT /api/v1/admin/rules` | 🟡 | 2 | BE-006 |
| ADMIN-006 ✅ | RulesManager: список правил + severity + enable/disable | 🟡 | 2 | ADMIN-005 |
| ADMIN-007 ✅ | RulesManager: inline test правила | 🟢 | 2 | ADMIN-006 |
| ADMIN-008 ✅ | `GET /api/v1/admin/macros` | 🟡 | 1 | BE-004 |
| ADMIN-009 ✅ | MacroRegistry: browse + source view | 🟡 | 2 | ADMIN-008 |

---

## EPIC-12: Authentication & Authorization

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|-----|------------|
| AUTH-001 | Local auth mode: users table в SQLite, login форма | 🔴 | 2 | BE-001 |
| AUTH-002 | JWT middleware: verify + inject user в request.state | 🔴 | 2 | AUTH-001 |
| AUTH-003 | Role-based access: `require_role()` декоратор | 🟠 | 1 | AUTH-002 |
| AUTH-004 | Frontend: AuthProvider + ProtectedRoute | 🔴 | 2 | FE-002 |
| AUTH-005 | Frontend: Login page | 🔴 | 1 | AUTH-004 |
| AUTH-006 | OIDC интеграция (Authlib) | 🟡 | 3 | AUTH-002 |
| AUTH-007 | LDAP интеграция (python-ldap) | 🟡 | 3 | AUTH-002 |
| AUTH-008 | Role-based UI гейтинг (скрытие элементов) | 🟠 | 2 | AUTH-004 |
| AUTH-009 | Refresh token rotation | 🟡 | 2 | AUTH-006 |
| AUTH-010 | Audit log: файловые операции + сборки | 🟡 | 2 | AUTH-002 |

---

## EPIC-13: Testing

| ID | Задача | Приоритет | SP | Зависимости |
|----|--------|-----------|-----|------------|
| TEST-001 | Unit tests FE: SyncEngine (formToYaml, yamlToForm) | 🟠 | 2 | ME-014 |
| TEST-002 | Unit tests FE: yamlSync утилиты | 🟠 | 1 | ME-015 |
| TEST-003 | Unit tests FE: dagLayout (Dagre wrapper) | 🟡 | 1 | LIN-003 |
| TEST-004 | Unit tests BE: FWService (mock FW) | 🟠 | 3 | BE-004 |
| TEST-005 | Integration tests BE: Projects API | 🟠 | 2 | BE-011 |
| TEST-006 | Integration tests BE: Validate API (реальный FW) | 🟠 | 2 | VAL-001 |
| TEST-007 | Integration tests BE: Build API | 🟠 | 2 | BUILD-001 |
| TEST-008 | E2E (Playwright): Critical path — open project → lineage | 🟡 | 2 | LIN-003 |
| TEST-009 | E2E (Playwright): Critical path — edit SQL → save → validate | 🟡 | 2 | VAL-006 |
| TEST-010 | E2E (Playwright): Critical path — wizard → create → build | 🟡 | 3 | WIZ-001 |
| TEST-011 | E2E (Playwright): Model Editor bidirectional sync | 🟡 | 2 | ME-019 |
| TEST-012 | Load test: 50 concurrent users (k6) | 🟡 | 2 | INFRA-007 |

---

## Сводка по Epic

| Epic | Задач | SP total | Phase |
|------|-------|----------|-------|
| Foundation & Infra | 27 | 34 | P0 |
| Layout & Navigation | 17 | 25 | P1 |
| Lineage | 14 | 27 | P1 |
| SQL Editor | 20 | 33 | P1 |
| Validate | 15 | 27 | P1 |
| Model Editor | 22 | 38 | P2 |
| Parameters | 13 | 20 | P2 |
| Build & Output | 11 | 20 | P1/P2 |
| Terminal | 10 | 14 | P1 |
| Wizard | 9 | 18 | P2 |
| Admin | 9 | 15 | P3 |
| Auth | 10 | 18 | P1/P4 |
| Testing | 12 | 23 | P3/P4 |
| **ИТОГО** | **189** | **312** | — |

---

*Backlog обновляется по результатам sprint review каждые 2 недели.*
