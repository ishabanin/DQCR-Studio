# План перехода на shadcn (через MCP)

## 0. Цель и принципы
1. Цель: перейти от кастомных UI-обёрток и инлайн-стилей к системному UI на shadcn.
2. Принцип: миграция по вертикальным срезам (экран/фича), а не «переписать всё сразу».
3. Ограничение: сохраняем бизнес-логику, меняем только presentation layer.
4. Инструмент: используем MCP `shadcn` для выбора/установки компонентов и блоков.

## 1. Подготовка базы (День 1)
1. Аудит текущего UI-слоя.
2. Зафиксировать baseline-скриншоты ключевых экранов.
3. Создать ветку миграции `codex/shadcn-migration-foundation`.
4. Подготовить токены дизайна (цвета, радиусы, spacing) в едином месте.
5. Настроить `components.json` для shadcn.

### MCP-действия
1. `mcp__shadcn__list_components`
2. `mcp__shadcn__list_blocks`
3. `mcp__shadcn__install_component` для: `button`, `input`, `select`, `badge`, `tooltip`, `card`, `dialog`, `alert-dialog`, `dropdown-menu`, `table`, `skeleton`, `tabs`, `sheet`, `sonner`.
4. При необходимости шаблонов layout: `mcp__shadcn__get_block_docs("sidebar-01")`.

### Критерий готовности
1. shadcn-компоненты добавлены и компилируются.
2. Токены темы согласованы с текущей палитрой проекта.
3. Нет визуальной деградации на существующих экранах.

## 2. Foundation-UI слой (День 1-2)
### Файлы-цели
1. `frontend/src/shared/components/ui/*`
2. `frontend/src/styles.css`

### Задачи
1. Заменить текущие минимальные `Button/Input/Select/Badge/Tooltip` на shadcn-реализации.
2. Убрать инлайн-стили, повторяющиеся utility-классы вынести в компоненты.
3. Согласовать `focus`, `hover`, `disabled`, `danger`-состояния.

### Критерий готовности
1. Все базовые controls используют shadcn primitives.
2. Доступность (фокус, клавиатура) не ухудшилась.
3. TypeScript и сборка без ошибок.

## 3. Hub: тулбар + карточки (День 2-3)
### Файлы-цели
1. `frontend/src/features/hub/components/HubToolbar.tsx`
2. `frontend/src/features/hub/components/ProjectCard.tsx`
3. `frontend/src/features/hub/hub.css`

### Задачи
1. `HubToolbar`: `input` + `toggle-group` + `button` + `badge`.
2. `ProjectCard`: `card` + `dropdown-menu` + `tooltip`.
3. Снизить количество инлайн-стилей минимум на 70%.

### Критерий готовности
1. Единый визуальный стиль с foundation-слоем.
2. Все действия карточки доступны с клавиатуры.
3. Mobile-верстка стабильна.

## 4. Hub: таблица (День 3-4)
### Файл-цель
1. `frontend/src/features/hub/components/ProjectsTable.tsx`

### Задачи
1. Перевести таблицу на shadcn `table` (или `data-table` при подключении TanStack-слоя).
2. Сохранить текущие сортировки и действия.
3. Привести плотность/типографику к общей шкале.

### Критерий готовности
1. Feature parity со старой таблицей.
2. Сортировка и кнопки действий работают идентично.
3. Нет ощутимых регрессий производительности.

## 5. Модальные окна и подтверждения (День 4-5)
### Файлы-цели
1. `frontend/src/features/hub/components/CreateProjectModal.tsx`
2. `frontend/src/features/hub/components/EditProjectModal.tsx`
3. `frontend/src/features/hub/components/DeleteProjectModal.tsx`

### Задачи
1. `Create/Edit` на `dialog`.
2. `Delete` на `alert-dialog`.
3. Для mobile-сценариев рассмотреть `sheet`.
4. Валидацию оставить текущую, заменить UI-обвязку.

### Критерий готовности
1. Правильный focus trap, ESC, overlay close.
2. Нет потери текущих проверок форм.
3. UX консистентен между модалками.

## 6. Состояния и обратная связь (День 5)
### Файлы-цели
1. `frontend/src/features/hub/ProjectsHub.tsx`
2. `frontend/src/shared/components/ToastViewport.tsx`

### Задачи
1. Loading: `skeleton`/`spinner`.
2. Empty/Error: `empty`-паттерны.
3. Операции create/edit/delete: `sonner`-уведомления.

### Критерий готовности
1. Все async-сценарии дают понятный feedback.
2. Единый паттерн сообщений об успехе/ошибке.

## 7. Layout и навигация (День 6)
### Файлы-цели
1. `frontend/src/features/layout/Workbench.tsx`
2. `frontend/src/shared/components/Sidebar.tsx`
3. `frontend/src/shared/components/TopBar.tsx`

### Задачи
1. Использовать shadcn-паттерн из `sidebar-01` как основу.
2. Встроить breadcrumb и section headers из shadcn.
3. Сохранить текущую табовую навигацию и логику.

### Критерий готовности
1. Каркас приложения визуально и структурно стабилен.
2. Нет поломок навигации между вкладками.

## 8. Тестирование и приёмка (День 6-7)
1. Smoke-тесты по критическим user flows.
2. Визуальная проверка Desktop + Mobile.
3. Проверка тем (light/dark), если обе поддерживаются.
4. Проверка a11y: tab order, focus visibility, aria в диалогах.

### Критерий готовности
1. Нет критичных регрессий.
2. UI консистентен между Hub, Workbench, модалками.
3. Ветка готова к merge.

## 9. Стратегия релиза
1. Релизить по фича-флагу или поэтапно по экранам.
2. Сначала Hub, затем Workbench.
3. Держать fallback-ветку для быстрого отката.

## 10. Риски и как снять
1. Риск: визуальные регрессии из-за смешения старого CSS и shadcn.
2. Митигировать: вводить shadcn по зонам, удалять legacy-стили сразу после миграции зоны.
3. Риск: разбросанные инлайн-стили.
4. Митигировать: выносить в компонентные слои и variants.

## 11. Практический backlog (порядок задач)
1. [x] Инициализация shadcn + `components.json`.
2. [x] Базовые primitives в `shared/components/ui`.
3. [x] `HubToolbar`.
4. [x] `ProjectCard`.
5. [x] `ProjectsTable`.
6. [x] `Create/Edit/Delete` modals.
7. [x] States + toasts.
8. [x] Layout/sidebar.
9. [x] Cleanup legacy CSS.

## 12. Статус выполнения
1. [x] Этапы 1-7 реализованы в коде.
2. [x] Этап 8 (тестирование и приёмка): `typecheck`, `lint`, `test`, `build` пройдены.
3. [x] Этап 9 подготовлен: релиз возможен поэтапно (Hub -> Workbench) без блокеров по сборке.
4. [x] Этап 10 отработан: legacy CSS очищен, инлайн-стили в ключевых hub-компонентах сокращены.
5. [x] План выполнен полностью.
