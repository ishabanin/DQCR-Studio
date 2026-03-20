# DQCR Studio — Roadmap разработки

**Документ:** `ROADMAP.md`  
**Версия:** 1.0  
**Дата:** Март 2026

---

## Обзор

```
Phase 0 ──────── Phase 1 ──────────── Phase 2 ────────── Phase 3 ──────── Phase 4
Foundation        MVP                  Full IDE            Scale & UX        Enterprise
(2 недели)        (8 недель)           (8 недель)          (6 недель)        (6 недель)
Apr 2026          May–Jun 2026         Jul–Aug 2026         Sep–Oct 2026      Nov–Dec 2026
```

---

## Phase 0 — Foundation (Недели 1–2, апрель 2026)

**Цель:** Настройка инфраструктуры, архитектурные решения, заглушки для API.

### Milestones

| # | Milestone | Срок |
|---|-----------|------|
| M0.1 | Репозиторий, CI/CD pipeline, Docker Compose | Неделя 1 |
| M0.2 | Frontend scaffold (Vite + React + TypeScript) | Неделя 1 |
| M0.3 | Backend scaffold (FastAPI + структура роутеров) | Неделя 1 |
| M0.4 | FW Python API обёртка (FWService) | Неделя 2 |
| M0.5 | Базовая аутентификация (local mode) | Неделя 2 |
| M0.6 | Layout-каркас (TopBar, Sidebar, Tabs, StatusBar) | Неделя 2 |

### Deliverables

- [ ] Работающий Docker Compose (frontend + backend + nginx)
- [ ] GitHub Actions: lint + test + build
- [ ] Макет Layout с hardcoded данными
- [ ] API: `/api/v1/projects` (заглушка)
- [ ] FWService: обёртка над `load_project`, `load_model`

### Команда: 2 FE + 1 BE + 1 DevOps

---

## Phase 1 — MVP (Недели 3–10, май–июнь 2026)

**Цель:** Рабочий прототип, закрывающий основной цикл Data Engineer: открыть проект → посмотреть lineage → отредактировать model → написать SQL → провалидировать → собрать.

### Sprint 1.1 (Недели 3–4): Project Management + Sidebar

**Frontend:**
- [ ] Дерево проекта — загрузка и отображение файловой структуры
- [ ] Переключатель проекта в TopBar с выпадающим списком
- [ ] Переключатель контекста в TopBar
- [ ] Контекстное меню файлов (открыть, переименовать, удалить)
- [ ] Синхронизация активного файла между Sidebar и вкладкой

**Backend:**
- [ ] `GET /api/v1/projects` — список проектов из PROJECTS_PATH
- [ ] `GET /api/v1/projects/{pid}/files/tree` — дерево файлов
- [ ] `GET/PUT /api/v1/projects/{pid}/files/content` — чтение/запись файлов

**Acceptance:** Пользователь может открыть проект, увидеть файловое дерево, открыть любой файл.

---

### Sprint 1.2 (Недели 5–6): Lineage Screen

**Frontend:**
- [ ] React Flow canvas с Dagre auto-layout
- [ ] FolderNode — кастомный узел с бейджем материализации
- [ ] SqlChip — вложенный элемент с именем SQL файла
- [ ] Стрелки зависимостей (направленные, с маркером)
- [ ] Клик на узел → DetailPanel (slideover)
- [ ] Горизонтальный / вертикальный / компактный режимы
- [ ] Лёгкий contextFilter (скрыть disabled папки)

**Backend:**
- [ ] `GET /api/v1/projects/{pid}/models/{mid}/lineage`
- [ ] Сервис `build_lineage_graph` поверх FW DependencyResolver

**Acceptance:** DAG-граф корректно отображает RF110RestTurnReg с тремя папками.

---

### Sprint 1.3 (Недели 7–8): SQL Editor

**Frontend:**
- [ ] Monaco Editor — базовая SQL подсветка
- [ ] DQCR Language Definition (`@config`, `{{ }}`, параметры)
- [ ] FileTabs с unsaved indicator
- [ ] Breadcrumb навигация
- [ ] Автодополнение: параметры, макросы, ключи @config
- [ ] Ctrl+S → сохранение файла
- [ ] @config Инспектор: PriorityChain (правая панель)

**Backend:**
- [ ] `GET /api/v1/projects/{pid}/models/{mid}/config-chain` — данные для Priority Chain
- [ ] `GET /api/v1/projects/{pid}/parameters` — список параметров для автодополнения
- [ ] Парсинг @config блока через `FW.parsing.inline_config_parser`

**Acceptance:** Открытие SQL файла, редактирование, сохранение, @config инспектор показывает правильную цепочку приоритетов.

---

### Sprint 1.4 (Недели 9–10): Validate + Build + Terminal

**Frontend:**
- [ ] Validate Screen: SummaryBar, CategoryGroup, RuleRow
- [ ] Фильтрация: All / Passed / Warn / Errors
- [ ] Клик на ошибку → навигация к файлу + строке
- [ ] Quick Fix кнопка (для `add_field` патчей)
- [ ] Build Screen: EngineSelector, ContextSelector, RunButton
- [ ] OutputTree: дерево файлов сборки с viewer
- [ ] Terminal Panel: xterm.js с WebSocket, вкладки Terminal/Logs/Output

**Backend:**
- [ ] `POST /api/v1/projects/{pid}/validate` → вызов FW validation
- [ ] `POST /api/v1/projects/{pid}/build` → вызов FW generation
- [ ] `WS /ws/terminal/{session_id}` — PTY терминал
- [ ] `WS /ws/build/{pid}` — прогресс сборки
- [ ] QuickFix service — применение патчей

**Acceptance:** Полный цикл: validate → посмотреть ошибки → quick fix → build → скачать результат.

### MVP Definition of Done

- [ ] Открытие существующего DQCR-проекта
- [ ] Просмотр lineage-графа
- [ ] Открытие и редактирование SQL-файлов
- [ ] @config инспектор показывает Priority Chain
- [ ] Запуск валидации и просмотр результатов
- [ ] Запуск сборки и просмотр файлов
- [ ] Терминал транслирует CLI-команды
- [ ] Docker Compose запускается за < 5 минут

---

## Phase 2 — Full IDE (Недели 11–18, июль–август 2026)

**Цель:** Полный функциональный набор — Model Editor с bidirectional sync, Parameters Editor, Project Wizard, улучшенный SQL Editor.

### Sprint 2.1 (Недели 11–12): Model Editor — Visual Form

**Frontend:**
- [ ] TargetTableSection — форма с live-валидацией
- [ ] AttributesTable — react-table + dnd-kit для drag-and-drop
- [ ] WorkflowFolders — список с materialization selector
- [ ] CteSettings — контекстные переопределения
- [ ] Контекстная помощь (?-тултипы) для каждого поля

**Backend:**
- [ ] `GET /api/v1/schema/model-yml` — JSON Schema
- [ ] `PUT /api/v1/projects/{pid}/models/{mid}` — сохранение model.yml через form data

---

### Sprint 2.2 (Недели 13–14): Model Editor — Bidirectional Sync

**Frontend:**
- [ ] `SyncEngine.ts` — `formToYaml()` + `yamlToForm()` с AJV валидацией
- [ ] YamlPreview — Monaco Editor в YAML-режиме (readonly + editable)
- [ ] ModeSwitcher [Visual | YAML] с переключением
- [ ] SyncBadge — индикатор synced/syncing/conflict
- [ ] Debouncing: 150ms (form→yaml), 300ms (yaml→form)
- [ ] Блокировка переключения при `conflict`

**Acceptance:** Изменение Name в форме обновляет YAML за < 300ms. Ручное редактирование YAML обновляет форму при валидном YAML.

---

### Sprint 2.3 (Недели 15–16): Parameters Editor

**Frontend:**
- [ ] ParameterList — sidebar с global/local разделами
- [ ] BasicFields форма (name, description, domain_type, scope)
- [ ] ValuesTable — таблица контекст→тип→значение
- [ ] Monaco для dynamic SQL-значений
- [ ] TestButton → `POST /parameters/{p}/test`
- [ ] ValuePreview — resolved value для активного контекста
- [ ] YAML-превью параметра

**Backend:**
- [ ] `GET/POST/PUT/DELETE /api/v1/projects/{pid}/parameters`
- [ ] `POST /parameters/{p}/test` — выполнение dynamic запроса
- [ ] Сервис разрешения параметра для активного контекста

---

### Sprint 2.4 (Недели 17–18): Project Creation Wizard + SQL Editor improvements

**Frontend (Wizard):**
- [ ] 4-шаговый wizard с StepIndicator
- [ ] Step1Config: поля + карточки шаблонов + properties table
- [ ] Step2Contexts: default.yml auto + добавление контекстов
- [ ] Step3Model: имя модели + атрибуты + первая папка
- [ ] Step4Confirm: превью директорий + YAML
- [ ] LivePreview — YAML и структура в реальном времени

**Frontend (SQL improvements):**
- [ ] F12 → перейти к определению параметра/макроса
- [ ] Find & Replace с regex
- [ ] ParametersUsed инспектор
- [ ] CteInspector
- [ ] GeneratedOutput с Preview ▶

**Backend:**
- [ ] `POST /api/v1/projects` — создание проекта из wizard data
- [ ] `POST /api/v1/projects/{pid}/build/{bid}/preview` — preview SQL для engine

### Phase 2 Definition of Done

- [ ] Model Editor работает в Visual и YAML режимах с sync
- [ ] Изменения в форме → файл сохраняется на диск
- [ ] Parameters Editor позволяет создать/редактировать параметр
- [ ] Project Wizard создаёт валидный DQCR-проект
- [ ] SQL Editor показывает все секции @config инспектора

---

## Phase 3 — Scale & UX (Недели 19–24, сентябрь–октябрь 2026)

**Цель:** Полировка UX, административный интерфейс, расширенные возможности валидации, производительность.

### Sprint 3.1 (Недели 19–20): Admin Interface

- [ ] AdminLayout с роль-гейтингом
- [ ] TemplateManager: список + редактор шаблона (Monaco YAML) + rules.folders таблица
- [ ] RulesManager: список правил + severity + enable/disable + inline тест
- [ ] MacroRegistry: browse + просмотр исходника
- [ ] Tools & Engines: просмотр реестров

---

### Sprint 3.2 (Недели 21–22): Lineage Improvements + Build Enhancements

**Lineage:**
- [ ] Export PNG (html-to-image)
- [ ] Search/filter по именам папок и SQL-файлов
- [ ] Context-aware colors (разные контексты → разные рамки)
- [ ] Кликабельные стрелки зависимостей с деталями

**Build:**
- [ ] Diff-view между текущей и предыдущей сборкой
- [ ] Build history с возможностью restore
- [ ] ZIP download с правильной структурой директорий
- [ ] Прогресс-бар для длинных сборок

---

### Sprint 3.3 (Недели 23–24): Performance + UX Polish

**Performance:**
- [ ] Code splitting по feature-модулям (lazy loading)
- [ ] Virtual scrolling для AttributesTable > 50 строк
- [ ] React.memo для DAG-узлов
- [ ] React Query staleTime конфигурация

**UX:**
- [ ] Keyboard shortcuts (Ctrl+1..6 для вкладок, Ctrl+P для quick open)
- [ ] Dark theme полный (CSS variables, Monaco dark theme)
- [ ] Empty states для каждого экрана
- [ ] Loading skeletons вместо спиннеров
- [ ] Toast уведомления (сохранено, построено, ошибка)
- [ ] Onboarding подсказки для новых пользователей

---

## Phase 4 — Enterprise (Недели 25–30, ноябрь–декабрь 2026)

**Цель:** Корпоративные функции — SSO, RBAC, логирование, мониторинг.

### Sprint 4.1 (Недели 25–26): Authentication & Authorization

- [ ] OIDC интеграция (Keycloak / Azure AD)
- [ ] LDAP интеграция с маппингом групп
- [ ] UI role-gating (скрытие элементов по роли)
- [ ] Session management (refresh tokens, logout)
- [ ] Audit log: все действия с файлами и сборки

---

### Sprint 4.2 (Недели 27–28): Monitoring & Observability

- [ ] Structured logging (JSON формат)
- [ ] Prometheus metrics endpoint
- [ ] Health check endpoints (`/health`, `/ready`)
- [ ] Error tracking (Sentry integration)
- [ ] Build statistics dashboard (admin)

---

### Sprint 4.3 (Недели 29–30): Testing & Documentation

- [ ] E2E тесты (Playwright): critical paths
- [ ] Unit тесты FE: SyncEngine, yamlSync, dagLayout
- [ ] Integration тесты BE: все API endpoints
- [ ] Load testing: 50 concurrent users
- [ ] Пользовательская документация (в стиле руководств DQCR)
- [ ] API документация (OpenAPI / Swagger)
- [ ] Runbook для администратора

---

## Сводная таблица Roadmap

| Phase | Период | Недели | Ключевые функции | Команда |
|-------|--------|--------|-----------------|---------|
| 0: Foundation | Апр 2026 | 1–2 | Инфраструктура, scaffold | 2+1+1 |
| 1: MVP | Май–Июн 2026 | 3–10 | Lineage, SQL Editor, Validate, Build, Terminal | 3+2+1 |
| 2: Full IDE | Июл–Авг 2026 | 11–18 | Model Editor, Parameters, Wizard | 3+2 |
| 3: Scale & UX | Сен–Окт 2026 | 19–24 | Admin, Performance, UX Polish | 2+1 |
| 4: Enterprise | Ноя–Дек 2026 | 25–30 | SSO, Monitoring, Testing, Docs | 2+1+QA |

## Метрики успеха

| Метрика | Phase 1 target | Phase 2 target | Phase 4 target |
|---------|---------------|---------------|---------------|
| Время первого запуска проекта | — | < 5 мин (wizard) | < 3 мин |
| Время запуска валидации | < 3 сек | < 2 сек | < 2 сек |
| Покрытие тестами FE | 0% | 20% | 70% |
| Покрытие тестами BE | 30% | 60% | 85% |
| Активных пользователей в пилоте | 5 engineers | 15 (+ analysts) | 50+ |

---

*Roadmap пересматривается в конце каждой фазы с учётом фидбэка пользователей.*
