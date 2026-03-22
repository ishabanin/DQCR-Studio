# DQCR Studio — Техническая спецификация

**Документ:** `SPEC.md`  
**Версия:** 1.0  
**Дата:** Март 2026  
**Статус:** Draft → Review

---

## Содержание

1. [Введение и контекст](#1-введение-и-контекст)
2. [Цели и требования](#2-цели-и-требования)
3. [Архитектура системы](#3-архитектура-системы)
4. [Frontend — структура приложения](#4-frontend--структура-приложения)
5. [Backend API](#5-backend-api)
6. [Экраны и компоненты](#6-экраны-и-компоненты)
7. [Bidirectional Sync Engine](#7-bidirectional-sync-engine)
8. [CLI-интеграция](#8-cli-интеграция)
9. [Аутентификация и авторизация](#9-аутентификация-и-авторизация)
10. [Нефункциональные требования](#10-нефункциональные-требования)
11. [Деплой и инфраструктура](#11-деплой-и-инфраструктура)
12. [Ограничения и допущения](#12-ограничения-и-допущения)

---

## 1. Введение и контекст

### 1.1 Предметная область

DQCR Framework (Data Quality & Conversion Framework) — Python-инструмент для генерации SQL-процессов из структурированных YAML/SQL-файлов. Фреймворк поддерживает несколько целевых СУБД (Oracle, ADB, PostgreSQL) и движков оркестрации (Airflow, dbt, Oracle PL/SQL, native DQCR).

Текущий способ работы с фреймворком — исключительно через CLI и ручное редактирование YAML/SQL-файлов в текстовом редакторе. Это создаёт высокий порог входа и ограничивает аудиторию технически сложными специалистами.

### 1.2 Проблема

- Data Engineers тратят значительное время на ручную навигацию по файловой структуре
- Аналитики и бизнес-пользователи не могут работать с фреймворком без глубоких знаний YAML
- Отсутствует визуализация DAG-зависимостей между SQL-шагами
- Иерархия приоритетов настроек (5 уровней) непрозрачна без знания кода
- Нет интегрированной среды для написания, валидации и сборки в одном окне

### 1.3 Решение

**DQCR Studio** — web-IDE для визуальной разработки проектов DQCR Framework, реализующая:

- Визуальный редактор с bidirectional sync (форма ↔ YAML)
- DAG-граф workflow для визуализации pipeline
- SQL Editor с @config-инспектором и подсветкой DQCR-специфичных конструкций
- Панель валидации с Quick Fix и навигацией к ошибкам
- Полную интеграцию с CLI через WebSocket-терминал
- No-code режим для аналитиков и бизнес-пользователей

### 1.4 Аналоги и вдохновение

| Продукт | Что берём |
|---------|-----------|
| dbt Cloud | Bidirectional YAML/Visual редактор, DAG lineage, integrated terminal |
| Databricks | Notebook-style layout, context switching |
| Hex | Split-panel editor + inspector |
| VS Code | Monaco Editor, sidebar file tree, tab navigation |

---

## 2. Цели и требования

### 2.1 Функциональные требования

#### FR-01: Управление проектами
- FR-01.1 Создание нового проекта через wizard (4 шага: конфигурация, контексты, модель, подтверждение)
- FR-01.2 Открытие существующего проекта из файловой системы
- FR-01.3 Переключение между проектами без перезагрузки страницы
- FR-01.4 Сохранение состояния (открытые файлы, активный контекст) между сессиями

#### FR-02: Навигация и файловое дерево
- FR-02.1 Отображение полной структуры DQCR-проекта в sidebar
- FR-02.2 Группировка по типу: Models, Contexts, Parameters, Templates (admin)
- FR-02.3 Контекстное меню: Переименовать, Дублировать, Удалить, Открыть
- FR-02.4 Подсветка активного файла левой полосой

#### FR-03: Lineage — DAG-граф
- FR-03.1 Отрисовка workflow как направленного ациклического графа
- FR-03.2 Узлы папок с бейджами материализации и чипами SQL-файлов
- FR-03.3 Стрелки зависимостей с цветовым кодированием (resolved/warn/error)
- FR-03.4 Detail panel при клике на узел
- FR-03.5 Фильтрация по контексту (hide disabled folders)
- FR-03.6 Режимы: горизонтальный, вертикальный, компактный
- FR-03.7 Экспорт графа как PNG

#### FR-04: Model Editor
- FR-04.1 Визуальная форма для редактирования model.yml (Target Table, Attributes, Workflow Folders, CTE Settings)
- FR-04.2 YAML-превью с live-обновлением при изменении формы
- FR-04.3 Переключатель Visual / YAML с bidirectional sync
- FR-04.4 Drag-and-drop для атрибутов и папок
- FR-04.5 Inline-валидация полей в реальном времени
- FR-04.6 Контекстная помощь (?) для каждого поля
- FR-04.7 Monaco Editor в YAML-режиме с JSON Schema валидацией
- FR-04.8 Импорт атрибутов из каталога напрямую в `target_table.attributes`
- FR-04.9 Отдельный блок `Fields` отсутствует в UI и в `model.yml`

#### FR-05: SQL Editor
- FR-05.1 Monaco Editor с подсветкой синтаксиса SQL + DQCR (@config, макросы, параметры)
- FR-05.2 Вкладки файлов с индикатором несохранённых изменений
- FR-05.3 Breadcrumb навигация с кликабельными сегментами
- FR-05.4 Автодополнение: имена таблиц, параметры, макросы, ключи @config
- FR-05.5 @config Инспектор: Priority Chain, Parameters Used, CTE Settings, Generated Output
- FR-05.6 Preview SQL — генерация и просмотр целевого SQL для выбранного engine
- FR-05.7 Горячие клавиши (Ctrl+S, Ctrl+Shift+F, F12, Ctrl+Space)
- FR-05.8 Find & Replace с поддержкой regex

#### FR-06: Validate
- FR-06.1 Запуск валидации через UI без CLI
- FR-06.2 Отображение результатов с разбивкой по категориям (general, sql, descriptions, adb, oracle, postgresql)
- FR-06.3 Фильтрация результатов: All / Passed / Warn / Errors
- FR-06.4 Навигация к файлу и строке ошибки
- FR-06.5 Quick Fix для типовых ошибок
- FR-06.6 История запусков (5 последних)
- FR-06.7 Выбор категорий правил перед запуском

#### FR-07: Parameters Editor
- FR-07.1 Список параметров с разбивкой global / local
- FR-07.2 Редактор основных полей (name, description, domain_type, scope)
- FR-07.3 Таблица values по контекстам (static / dynamic)
- FR-07.4 SQL-редактор для dynamic-значений
- FR-07.5 Кнопка Test — выполнение dynamic-запроса с показом результата
- FR-07.6 Preview разрешённого значения для активного контекста

#### FR-08: Build & Output
- FR-08.1 Выбор workflow engine (dqcr, airflow, dbt, oracle_plsql)
- FR-08.2 Настройки: контекст, dry run, путь вывода, выбор моделей
- FR-08.3 Просмотр сгенерированных файлов во встроенном viewer
- FR-08.4 Скачивание отдельного файла или ZIP
- FR-08.5 Diff-view — сравнение текущей и предыдущей сборки
- FR-08.6 История сборок (10 последних)

#### FR-09: Terminal
- FR-09.1 Встроенный WebSocket-терминал (xterm.js)
- FR-09.2 Трансляция каждого UI-действия в видимую CLI-команду
- FR-09.3 Вкладки: Terminal, Logs, Output
- FR-09.4 Цветовое кодирование вывода (success/warning/error/debug)
- FR-09.5 История команд (↑/↓)

#### FR-10: Административный интерфейс
- FR-10.1 Template Manager: просмотр, создание, редактирование шаблонов
- FR-10.2 Validation Rules Manager: список правил, severity, enable/disable, тест
- FR-10.3 Macro Registry: просмотр, документация, тестирование макросов
- FR-10.4 Tools & Engines: управление реестрами tools.yml и workflow_engines.yml

#### FR-11: Project Creation Wizard
- FR-11.1 4-шаговый wizard с прогресс-индикатором
- FR-11.2 Live-превью YAML и структуры директорий на каждом шаге
- FR-11.3 Карточки выбора шаблона с описаниями
- FR-11.4 Валидация каждого поля в реальном времени

### 2.2 Нефункциональные требования

| ID | Требование | Метрика |
|----|-----------|---------|
| NFR-01 | Время загрузки приложения | < 3 сек (первый запуск), < 1 сек (повторный) |
| NFR-02 | Время отклика bidirectional sync | < 300 мс |
| NFR-03 | Время запуска валидации в UI | < 2 сек для проекта до 50 моделей |
| NFR-04 | Отрисовка DAG-графа | < 500 мс для 20 папок |
| NFR-05 | Поддержка браузеров | Chrome 120+, Firefox 120+, Safari 17+ |
| NFR-06 | Разрешение экрана | 1280×800 минимум, оптимально 1440×900+ |
| NFR-07 | Concurrent users | 50 одновременных пользователей на одном instance |
| NFR-08 | Доступность | 99.5% uptime (self-hosted) |
| NFR-09 | Тёмная тема | Обязательна (CSS variables для всех цветов) |
| NFR-10 | Keyboard accessibility | Все основные функции доступны без мыши |

---

## 3. Архитектура системы

### 3.1 Общая схема

```
┌─────────────────────────────────────────────────────────┐
│                     Browser (SPA)                        │
│  React + TypeScript + Monaco Editor + React Flow         │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/REST + WebSocket
┌──────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend                         │
│  ┌─────────────┐  ┌────────────┐  ┌──────────────────┐  │
│  │  REST API   │  │ WebSocket  │  │  File System API  │  │
│  │  /api/v1/   │  │  /ws/      │  │  (project files)  │  │
│  └─────────────┘  └────────────┘  └──────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │              DQCR Framework (Python)                │  │
│  │  CLI · Validation · Generation · Parsing · Macros  │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │ Mount
┌──────────────────────▼──────────────────────────────────┐
│              File System (Project Files)                  │
│  /projects/<name>/  project.yml, model/, contexts/, ...  │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Компоненты

| Компонент | Технология | Назначение |
|-----------|-----------|-----------|
| Frontend SPA | React 18 + TypeScript 5 | Основное UI-приложение |
| Code Editor | Monaco Editor 0.45+ | SQL и YAML редактирование |
| DAG Renderer | React Flow 11 + Dagre | Отрисовка lineage-графа |
| YAML Parser | js-yaml 4 + AJV (JSON Schema) | Bidirectional sync |
| Backend API | FastAPI 0.110+ | REST API и WebSocket |
| PTY Terminal | FastAPI + ptyprocess | Реальный терминал через WebSocket |
| DQCR Engine | Python 3.10+ | Генерация, валидация, парсинг |
| Reverse Proxy | Nginx | Static files, SSL termination |
| Auth | Authlib (OIDC) / python-ldap | SSO интеграция |

### 3.3 Файловая система

Backend монтирует директорию проектов как volume. Все операции с файлами идут через File System API бэкенда — фронтенд никогда не работает с файлами напрямую.

```
/app/
├── backend/           # FastAPI приложение
├── fw/                # DQCR Framework (Python package)
└── projects/          # Проекты (mount point)
    ├── RF110NEW/
    │   ├── project.yml
    │   ├── contexts/
    │   ├── parameters/
    │   └── model/
    └── ...
```

---

## 4. Frontend — структура приложения

### 4.1 Технологический стек

```json
{
  "react": "^18.3",
  "typescript": "^5.4",
  "@monaco-editor/react": "^4.6",
  "reactflow": "^11.11",
  "dagre": "^0.8",
  "js-yaml": "^4.1",
  "ajv": "^8.12",
  "zustand": "^4.5",
  "react-query": "^5.28",
  "axios": "^1.6",
  "xterm": "^5.3",
  "xterm-addon-fit": "^0.8",
  "vite": "^5.2"
}
```

### 4.2 Структура директорий (Frontend)

```
src/
├── app/
│   ├── App.tsx                    # Корневой компонент + роутер
│   ├── store/                     # Zustand stores
│   │   ├── projectStore.ts        # Состояние проекта
│   │   ├── editorStore.ts         # Открытые файлы, вкладки
│   │   ├── contextStore.ts        # Активный контекст
│   │   └── uiStore.ts             # UI state (panels, modals)
│   └── providers/
│       ├── AuthProvider.tsx
│       └── ThemeProvider.tsx
│
├── features/
│   ├── lineage/                   # FR-03
│   │   ├── LineageScreen.tsx
│   │   ├── DagGraph.tsx           # React Flow + Dagre
│   │   ├── FolderNode.tsx
│   │   ├── SqlChip.tsx
│   │   └── DetailPanel.tsx
│   │
│   ├── model-editor/              # FR-04
│   │   ├── ModelEditorScreen.tsx
│   │   ├── VisualForm/
│   │   │   ├── TargetTableSection.tsx
│   │   │   ├── AttributesTable.tsx
│   │   │   ├── WorkflowFolders.tsx
│   │   │   └── CteSettings.tsx
│   │   ├── YamlPreview.tsx        # Monaco Editor (YAML)
│   │   └── SyncEngine.ts          # Bidirectional sync logic
│   │
│   ├── sql-editor/                # FR-05
│   │   ├── SqlEditorScreen.tsx
│   │   ├── SqlMonaco.tsx          # Monaco + DQCR language
│   │   ├── ConfigInspector/
│   │   │   ├── PriorityChain.tsx
│   │   │   ├── ParametersUsed.tsx
│   │   │   ├── CteSettings.tsx
│   │   │   └── GeneratedOutput.tsx
│   │   └── FileTabs.tsx
│   │
│   ├── validate/                  # FR-06
│   │   ├── ValidateScreen.tsx
│   │   ├── CategoryGroup.tsx
│   │   ├── RuleRow.tsx
│   │   └── QuickFix.ts
│   │
│   ├── parameters/                # FR-07
│   │   ├── ParametersScreen.tsx
│   │   ├── ParameterList.tsx
│   │   └── ParameterEditor/
│   │       ├── BasicFields.tsx
│   │       ├── ValuesTable.tsx
│   │       └── ValuePreview.tsx
│   │
│   ├── build/                     # FR-08
│   │   ├── BuildScreen.tsx
│   │   ├── BuildConfig.tsx
│   │   ├── OutputTree.tsx
│   │   └── BuildHistory.tsx
│   │
│   ├── admin/                     # FR-10
│   │   ├── AdminLayout.tsx
│   │   ├── TemplateManager/
│   │   ├── RulesManager/
│   │   └── MacroRegistry/
│   │
│   └── wizard/                    # FR-11
│       ├── ProjectWizard.tsx
│       ├── steps/
│       │   ├── Step1Config.tsx
│       │   ├── Step2Contexts.tsx
│       │   ├── Step3Model.tsx
│       │   └── Step4Confirm.tsx
│       └── WizardPreview.tsx
│
├── shared/
│   ├── components/
│   │   ├── TopBar.tsx
│   │   ├── Sidebar.tsx
│   │   ├── TabBar.tsx
│   │   ├── Terminal.tsx           # xterm.js wrapper
│   │   ├── StatusBar.tsx
│   │   └── ui/                    # Button, Badge, Input, Select...
│   ├── hooks/
│   │   ├── useProject.ts
│   │   ├── useWebSocket.ts
│   │   ├── useValidation.ts
│   │   └── useSyncEngine.ts
│   └── utils/
│       ├── yamlSync.ts            # YAML ↔ Form sync
│       ├── dqcrLanguage.ts        # Monaco language definition
│       └── dagLayout.ts           # Dagre layout calculation
│
└── api/
    ├── client.ts                  # Axios instance
    ├── projects.ts
    ├── models.ts
    ├── validation.ts
    ├── build.ts
    └── ws.ts                      # WebSocket client
```

### 4.3 Управление состоянием

**Zustand stores (клиентский state):**

```typescript
// projectStore.ts
interface ProjectStore {
  currentProject: Project | null;
  activeContext: string;              // 'default' | 'vtb' | ...
  openFiles: OpenFile[];
  activeFileId: string | null;
  setProject: (p: Project) => void;
  setContext: (ctx: string) => void;
  openFile: (path: string) => void;
  closeFile: (id: string) => void;
}

// editorStore.ts
interface EditorStore {
  activeTab: TabId;                   // 'lineage' | 'model' | 'sql' | 'validate' | ...
  modelEditorMode: 'visual' | 'yaml';
  syncStatus: 'synced' | 'syncing' | 'conflict';
  dirtyFiles: Set<string>;            // файлы с несохранёнными изменениями
}
```

**React Query (серверный state):**
- Кэширование ответов API (проекты, модели, результаты валидации)
- Инвалидация кэша при мутациях (save, build, validate)

---

## 5. Backend API

### 5.1 Структура Backend

```
backend/
├── main.py                    # FastAPI app entry point
├── routers/
│   ├── projects.py            # /api/v1/projects/*
│   ├── models.py              # /api/v1/projects/{pid}/models/*
│   ├── files.py               # /api/v1/projects/{pid}/files/*
│   ├── validation.py          # /api/v1/projects/{pid}/validate
│   ├── build.py               # /api/v1/projects/{pid}/build
│   ├── parameters.py          # /api/v1/projects/{pid}/parameters/*
│   ├── admin.py               # /api/v1/admin/*
│   └── ws.py                  # WebSocket endpoints
├── services/
│   ├── project_service.py     # Бизнес-логика проекта
│   ├── fw_service.py          # Обёртка над DQCR Framework
│   ├── file_service.py        # Работа с файловой системой
│   ├── sync_service.py        # YAML ↔ Model sync
│   └── terminal_service.py    # PTY управление
├── schemas/
│   ├── project.py             # Pydantic models
│   ├── model.py
│   ├── parameter.py
│   └── validation.py
└── core/
    ├── config.py              # Настройки приложения
    ├── auth.py                # Middleware аутентификации
    └── fs.py                  # Файловые утилиты
```

### 5.2 REST API endpoints

#### Projects

```
GET    /api/v1/projects                          # Список проектов
POST   /api/v1/projects                          # Создать проект (wizard)
GET    /api/v1/projects/{project_id}             # Метаданные проекта
DELETE /api/v1/projects/{project_id}             # Удалить проект
```

#### Files

```
GET    /api/v1/projects/{pid}/files/tree         # Дерево файлов
GET    /api/v1/projects/{pid}/files/content      # Содержимое файла (?path=)
PUT    /api/v1/projects/{pid}/files/content      # Сохранить файл
POST   /api/v1/projects/{pid}/files/rename       # Переименовать
DELETE /api/v1/projects/{pid}/files              # Удалить файл/папку
```

#### Models

```
GET    /api/v1/projects/{pid}/models             # Список моделей
GET    /api/v1/projects/{pid}/models/{model_id}  # Метаданные модели
PUT    /api/v1/projects/{pid}/models/{model_id}  # Обновить model.yml
GET    /api/v1/projects/{pid}/models/{mid}/lineage  # DAG данные
```

#### Validation

```
POST   /api/v1/projects/{pid}/validate           # Запустить валидацию
GET    /api/v1/projects/{pid}/validate/history   # История запусков
GET    /api/v1/projects/{pid}/validate/{run_id}  # Результаты конкретного запуска
POST   /api/v1/projects/{pid}/validate/quickfix  # Применить quick fix
```

#### Build

```
POST   /api/v1/projects/{pid}/build              # Запустить сборку
GET    /api/v1/projects/{pid}/build/history      # История сборок
GET    /api/v1/projects/{pid}/build/{build_id}/files  # Файлы сборки
GET    /api/v1/projects/{pid}/build/{build_id}/preview # Предпросмотр SQL
GET    /api/v1/projects/{pid}/build/{build_id}/download # Скачать ZIP
```

#### Parameters

```
GET    /api/v1/projects/{pid}/parameters         # Все параметры
POST   /api/v1/projects/{pid}/parameters         # Создать параметр
PUT    /api/v1/projects/{pid}/parameters/{param} # Обновить параметр
DELETE /api/v1/projects/{pid}/parameters/{param} # Удалить параметр
POST   /api/v1/projects/{pid}/parameters/{param}/test  # Тест dynamic-значения
```

#### Admin

```
GET    /api/v1/admin/templates                   # Список шаблонов
PUT    /api/v1/admin/templates/{name}            # Обновить шаблон
GET    /api/v1/admin/rules                       # Список правил валидации
PUT    /api/v1/admin/rules/{name}                # Обновить правило
GET    /api/v1/admin/macros                      # Список макросов
```

### 5.3 WebSocket endpoints

```
WS /ws/terminal/{session_id}     # PTY терминал
WS /ws/validation/{project_id}   # Live результаты валидации
WS /ws/build/{project_id}        # Прогресс сборки
```

### 5.4 Схемы данных (ключевые)

```python
# Ответ lineage API
class LineageResponse(BaseModel):
    model_name: str
    folders: List[FolderNode]
    edges: List[Edge]

class FolderNode(BaseModel):
    id: str
    name: str
    materialization: str
    enabled: bool
    queries: List[SqlQuery]
    target_info: Optional[str]
    params_count: int
    dependencies: List[str]

# Ответ валидации
class ValidationResult(BaseModel):
    run_id: str
    timestamp: datetime
    project: str
    model: str
    summary: ValidationSummary
    categories: List[CategoryResult]

class RuleResult(BaseModel):
    rule_id: str
    name: str
    status: Literal['pass', 'warning', 'error']
    message: str
    file_path: Optional[str]
    line: Optional[int]
    quick_fix: Optional[QuickFix]
```

---

## 6. Экраны и компоненты

### 6.1 Layout (постоянный)

```
┌───────────────────────── TOP BAR (42px) ──────────────────────────┐
│ Logo │ Project▾ │ Context▾ │ Context▾ │ ... │ Validate │ ▶ Build  │
├────────────┬──────────────────────────────────────────────────────┤
│            │                  TAB BAR (36px)                       │
│  SIDEBAR   ├──────────────────────────────────────────────────────┤
│  (212px)   │                                                       │
│            │              MAIN CONTENT (flex-1)                   │
│  - Project │                                                       │
│  - Models  │              Active Screen                           │
│  - SQL     │                                                       │
│  - Context │                                                       │
│  - Params  ├──────────────────────────────────────────────────────┤
│            │           BOTTOM PANEL (104px)                        │
│            │  Terminal │ Logs │ Output                             │
├────────────┴──────────────────────────────────────────────────────┤
│                   STATUS BAR (22px)                                │
└───────────────────────────────────────────────────────────────────┘
```

### 6.2 Lineage Screen

**Ключевые компоненты:**
- `DagGraph` — React Flow canvas с Dagre auto-layout
- `FolderNode` — кастомный React Flow node (заголовок + материализация + SQL-чипы)
- `DetailPanel` — slideover правее графа при клике на узел
- `ContextFilter` — фильтр по контексту скрывает disabled-узлы

**Данные:** `GET /api/v1/projects/{pid}/models/{mid}/lineage` → JSON с nodes и edges

**Состояние:** React Flow internal state + selectedNodeId в uiStore

### 6.3 Model Editor Screen

**Ключевые компоненты:**
- `VisualForm` — форма из 4 секций (TargetTable, Attributes, WorkflowFolders, CteSettings)
- `AttributesTable` — react-table с drag-and-drop (dnd-kit)
- `YamlPreview` — Monaco Editor (readOnly в visual-mode, editable в yaml-mode)
- `SyncBadge` — индикатор synced/syncing/conflict
- `ModeSwitcher` — переключатель [Visual | YAML]

**Bidirectional sync:**
1. Visual → YAML: `formValues → generateYaml(formValues)` → обновление Monaco
2. YAML → Visual: `parseYaml(yamlText)` → `validateSchema(parsed)` → `updateFormValues(parsed)`

### 6.3.1 Model Editor Simplification

Подробная спецификация вынесена в отдельный документ:
- [MODEL_EDITOR_ATTRIBUTES_ONLY.md](/Users/IgorShabanin/dev/DQCR%20Studio/Docs/MODEL_EDITOR_ATTRIBUTES_ONLY.md)

**Проблема:**
- В текущей реализации одновременно существуют `target_table.attributes` и отдельный список `fields`.
- Оба списка описывают колонки модели, но с разным набором метаданных.
- Это создаёт дублирование данных, путаницу в UI и неоднозначность в источнике истины.

**Решение:**
- Единственным списком колонок модели остаётся `target_table.attributes`.
- Импорт из каталога заполняет и обновляет только `target_table.attributes`.
- Отдельный блок `Fields` удаляется из экрана `Model Editor`.
- Верхнеуровневое свойство `fields` удаляется из `model.yml`, API-объекта модели и JSON Schema.

**Новый источник истины:**
- `target_table.attributes` является единственным каноническим описанием колонок модели для:
  - visual editor;
  - YAML editor;
  - сохранения `model.yml`;
  - autocomplete target table;
  - downstream workflow/validation logic.

**Правила импорта из каталога:**
- Пользователь выбирает сущность каталога через диалог импорта.
- Атрибуты выбранной сущности маппятся в `target_table.attributes`.
- Маппинг полей каталога:
  - `attribute.name` -> `attributes[].name`
  - `attribute.domain_type` -> `attributes[].domain_type`
  - `attribute.is_key` -> `attributes[].is_key`
  - `attribute.is_nullable` не хранится в отдельном поле модели и не создаёт новый список
  - `attribute.display_name` не сохраняется в `model.yml`
- Поддерживаются режимы импорта:
  - `Replace` — полностью заменить `target_table.attributes` атрибутами из каталога
  - `Merge` — обновить совпавшие по имени атрибуты и сохранить остальные атрибуты модели

**Поведение UI:**
- Кнопка импорта из каталога располагается в секции `Attributes`.
- После импорта пользователь видит изменения в одной таблице `Attributes`.
- Отдельной секции предпросмотра `Fields` больше нет.
- Если каталог не загружен, импорт недоступен, но ручное редактирование `Attributes` остаётся доступным.

**Требования к обратной совместимости:**
- При чтении старого `model.yml`, если обнаружено поле `fields`, backend игнорирует его или выполняет одноразовую миграцию в `target_table.attributes` по имени.
- При сохранении `model.yml` поле `fields` больше не записывается.
- Autocomplete для target table строится только по `target_table.attributes`.

**Out of scope:**
- Хранение каталожных display name и nullable в `model.yml`.
- Поддержка двух параллельных источников описания колонок.

### 6.4 SQL Editor Screen

**Ключевые компоненты:**
- `SqlMonaco` — Monaco с кастомным language definition для DQCR SQL
- `FileTabs` — вкладки с unsaved indicator
- `Breadcrumb` — кликабельный путь к файлу
- `ConfigInspector` — правая панель из 4 секций
  - `PriorityChain` — 5 уровней с подсветкой активного
  - `ParametersUsed` — список {{ param }} из текущего SQL
  - `CteInspector` — CTE materialization settings
  - `OutputPreview` — список целевых форматов с кнопкой Preview

**DQCR Language Definition (Monaco):**

```typescript
// Токены для подсветки
const dqcrTokens = {
  '@config': 'keyword.dqcr.config',
  '{{': 'keyword.dqcr.macro.start',
  '}}': 'keyword.dqcr.macro.end',
  'materialized': 'variable.dqcr.key',
  'target_table': 'variable.dqcr.key',
};
```

### 6.5 Validate Screen

**Ключевые компоненты:**
- `SummaryBar` — 3 счётчика с фильтрацией
- `CategoryGroup` — раскрывающаяся группа правил
- `RuleRow` — строка правила (статус + текст + кнопки)
- `QuickFixButton` — применяет patch к файлу через API

**Quick Fix реализация:**
Backend возвращает `QuickFix` объект с типом патча:
```python
class QuickFix(BaseModel):
    type: Literal['add_field', 'rename_file', 'update_yaml']
    file_path: str
    patch: dict  # конкретное изменение
    description: str
```

### 6.6 Parameters Screen

**Ключевые компоненты:**
- `ParameterList` — список с разделителями global/local
- `BasicFields` — форма основных полей
- `ValuesTable` — таблица контекст → тип → значение
- `DynamicSqlEditor` — Monaco для SQL в dynamic-значениях
- `TestButton` — вызывает `POST /parameters/{p}/test`

---

## 7. Bidirectional Sync Engine

### 7.1 Принцип работы

```
Visual Form State
       ↕ (debounced 150ms)
 yamlSync.ts: formToYaml()
       ↕
  Monaco Editor (YAML)
       ↕ (on change, debounced 300ms)
 yamlSync.ts: yamlToForm()
       ↕ (AJV validation)
  Visual Form State
```

### 7.2 Состояния синхронизации

| Состояние | Описание | UI-индикатор |
|-----------|---------|-------------|
| `synced` | Обе панели консистентны | ⟳ synced (зелёный) |
| `syncing` | Идёт пересчёт (< 300ms) | ⟳ syncing… (серый) |
| `conflict` | YAML невалиден по схеме | ⚠ conflict (оранжевый) |
| `dirty` | Есть несохранённые изменения | ● в заголовке файла |

### 7.3 Алгоритм yamlToForm

```typescript
function yamlToForm(yamlText: string): FormValues | SyncError {
  try {
    const parsed = jsYaml.load(yamlText);
    const valid = ajv.validate(modelYmlSchema, parsed);
    if (!valid) return { type: 'conflict', errors: ajv.errors };
    return mapYamlToForm(parsed);
  } catch (e) {
    return { type: 'conflict', errors: [e.message] };
  }
}
```

### 7.4 JSON Schema для model.yml

Backend предоставляет JSON Schema через `GET /api/v1/schema/model-yml`. Схема используется:
- В Monaco Editor для валидации и автодополнения YAML
- В AJV для валидации при bidirectional sync
- В Visual Form для отображения контекстной помощи

---

## 8. CLI-интеграция

### 8.1 WebSocket Terminal (PTY)

```python
# backend/services/terminal_service.py
import ptyprocess, asyncio

class TerminalService:
    async def create_session(self, project_path: str) -> str:
        session_id = uuid4().hex
        process = ptyprocess.PtyProcess.spawn(
            ['/bin/bash'],
            cwd=project_path,
            env={**os.environ, 'PYTHONPATH': FW_PATH}
        )
        self.sessions[session_id] = process
        return session_id

    async def send_command(self, session_id: str, cmd: str):
        self.sessions[session_id].write(cmd.encode())
```

### 8.2 UI → CLI трансляция

При каждом вызове API, который запускает FW-команду, backend логирует команду и отправляет её в WebSocket terminal stream:

```python
async def run_build(project_id, model_id, engine, context):
    cmd = f'python -m FW.cli generate "{project_id}" "{model_id}" -w {engine}'
    if context != 'default':
        cmd += f' -c {context}'
    await terminal_service.emit_command(project_id, cmd)  # показать в UI
    result = await fw_service.generate(project_id, model_id, engine, context)
    return result
```

### 8.3 FW Service

```python
# backend/services/fw_service.py
from FW.cli import build, validate, generate

class FWService:
    def validate(self, project_path, model_name, rules=None):
        return run_validation(project_path, model_name, rules)

    def generate(self, project_path, model_name, engine, context):
        return run_generation(project_path, model_name, engine, context)

    def get_lineage(self, project_path, model_name):
        # Загружает проект через FW API (не CLI) и возвращает граф
        from FW.parsing.project_loader import load_project
        from FW.generation.dependency_resolver import resolve
        project = load_project(project_path)
        model = project.models[model_name]
        return build_lineage_graph(model)
```

---

## 9. Аутентификация и авторизация

### 9.1 Роли

| Роль | Право | Доступные экраны |
|------|-------|-----------------|
| `admin` | Чтение, запись, выполнение, управление шаблонами | Все + Administration |
| `engineer` | Чтение, запись SQL/YAML, Build/Validate | Все кроме Admin |
| `analyst` | Чтение + редактирование форм (no YAML direct) | Lineage, Model Editor (visual), Validate, Parameters |
| `viewer` | Только чтение | Lineage, Validate (read-only) |

### 9.2 Методы аутентификации

**Режим 1 — OIDC (рекомендован для production):**
- Поддержка любого OIDC-провайдера (Keycloak, Azure AD, Okta)
- JWT-токены в Authorization header
- Конфигурация через env: `AUTH_OIDC_ISSUER`, `AUTH_OIDC_CLIENT_ID`

**Режим 2 — LDAP:**
- Аутентификация через корпоративный LDAP
- Маппинг LDAP-групп на роли DQCR Studio
- Конфигурация через env: `AUTH_LDAP_URL`, `AUTH_LDAP_BASE_DN`

**Режим 3 — Local users (dev/demo):**
- Простая таблица users в SQLite
- Только для разработки и демо-стендов
- Включается через `AUTH_MODE=local`

### 9.3 Middleware авторизации

```python
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    token = extract_token(request)
    user = await verify_token(token)
    request.state.user = user
    return await call_next(request)

def require_role(roles: List[str]):
    def decorator(func):
        async def wrapper(*args, request: Request, **kwargs):
            if request.state.user.role not in roles:
                raise HTTPException(403, "Insufficient permissions")
            return await func(*args, request=request, **kwargs)
        return wrapper
    return decorator
```

---

## 10. Нефункциональные требования

### 10.1 Производительность

- **Code Splitting:** Vite lazy-loading для каждого feature-модуля (sql-editor, admin, etc.)
- **Virtual Scrolling:** react-virtual для больших списков (атрибуты, правила валидации)
- **Debouncing:** bidirectional sync — 150ms form, 300ms YAML
- **Memoization:** React.memo + useMemo для DAG-рендеринга
- **API Caching:** React Query с staleTime 30s для неизменяемых данных

### 10.2 Безопасность

- Все запросы к Backend через HTTPS (TLS 1.2+)
- CORS ограничен доменом приложения
- Команды в PTY терминале — только из разрешённого списка
- Файловые операции ограничены path `/projects/` (path traversal prevention)
- Content Security Policy заголовки

### 10.3 Доступность (Accessibility)

- ARIA-атрибуты для интерактивных элементов
- Focus management при открытии модалей
- Keyboard shortcuts для всех основных действий
- Контрастность 4.5:1 для текста (WCAG AA)

---

## 11. Деплой и инфраструктура

### 11.1 Docker Compose (production)

```yaml
# docker-compose.yml
version: '3.8'
services:
  frontend:
    image: dqcr-studio-frontend:latest
    build: ./frontend
    environment:
      - VITE_API_URL=/api
    depends_on: [backend]

  backend:
    image: dqcr-studio-backend:latest
    build: ./backend
    environment:
      - PROJECTS_PATH=/app/projects
      - FW_PATH=/app/fw
      - AUTH_MODE=${AUTH_MODE:-oidc}
      - AUTH_OIDC_ISSUER=${AUTH_OIDC_ISSUER}
    volumes:
      - ./projects:/app/projects
      - ./fw:/app/fw
    ports:
      - "8000:8000"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./ssl:/etc/ssl/certs
    depends_on: [frontend, backend]
```

### 11.2 Переменные окружения

| Переменная | Описание | Обязательна |
|-----------|---------|------------|
| `PROJECTS_PATH` | Путь к директории проектов | Да |
| `FW_PATH` | Путь к DQCR Framework | Да |
| `AUTH_MODE` | `oidc` / `ldap` / `local` | Да |
| `AUTH_OIDC_ISSUER` | URL OIDC провайдера | При OIDC |
| `AUTH_OIDC_CLIENT_ID` | Client ID | При OIDC |
| `AUTH_LDAP_URL` | LDAP URL | При LDAP |
| `SECRET_KEY` | JWT signing key | Да |
| `MAX_TERMINAL_SESSIONS` | Максимум PTY сессий | Нет (default: 50) |
| `LOG_LEVEL` | `debug` / `info` / `warning` | Нет (default: info) |

---

## 12. Ограничения и допущения

### 12.1 Ограничения MVP

- Один пользователь редактирует модель в один момент времени (нет real-time collaboration)
- Отсутствует встроенный контроль версий (предполагается внешний Git)
- Terminal — только для DQCR CLI команд, не произвольный shell
- Поддержка файловой системы только локальной (не S3 / Git remote)

### 12.2 Допущения

- DQCR Framework установлен и доступен как Python package на сервере
- Файловая система проектов доступна Backend как volume
- У Backend есть права на чтение/запись в `/projects/`
- Браузер пользователя поддерживает WebSocket

### 12.3 Зависимости от DQCR Framework API

Studio не вызывает CLI как subprocess для получения данных — только для терминала. Для всех структурных операций используется Python API FW:

```python
# Примеры используемых FW модулей
from FW.parsing.project_loader import load_project
from FW.parsing.model_config_loader import load_model
from FW.validation.rule_runner import run_validation
from FW.generation.DefaultBuilder import DefaultBuilder
from FW.config import TemplateRegistry, ToolRegistry
```

---

*Документ актуален для DQCR Studio v1.0 и DQCR Framework v1.0*  
*Следующий review: после завершения Phase 1 (MVP)*
