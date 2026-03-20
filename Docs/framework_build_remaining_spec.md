# DQCR Studio — Спецификация оставшихся доработок по `fw2 build`

**Документ:** `framework_build_remaining_spec.md`  
**Версия:** 1.0  
**Дата:** Март 2026  
**Статус:** Draft

---

## 1. Контекст

В `DQCR Studio` уже выполнен первый рабочий этап интеграции `FTRepCBR.Workflow.FW` через `fw2 build`.

На текущий момент реализовано:

- backend умеет вызывать `fw2 build`
- результат `build` сохраняется в кэш проекта `.dqcr_workflow_cache/<model>.json`
- при upload/import/create/save/rename/delete запускается мягкая автопересборка
- `Lineage` строится из `workflow.steps` и `dependencies` с fallback на старую локальную логику
- `Model Editor` и `Parameters` читают данные из workflow cache с fallback на YAML/files

Это уже создаёт единый источник данных для части интерфейса, но ещё не доводит систему до состояния:

> "весь интерфейс DQCR Studio строится на основании результата framework build"

Настоящий документ фиксирует оставшиеся доработки до этого состояния.

---

## 2. Цель следующего этапа

Перевести оставшиеся пользовательские сценарии на использование workflow build как primary source of truth.

Итоговое целевое поведение:

1. Studio при открытии проекта получает актуальный workflow build.
2. Основные экраны читают состояние проекта из workflow JSON, а не из разрозненных парсеров файлов.
3. Ошибка build не ломает редактирование, но явно видна в UI.
4. Старые локальные эвристики остаются только как временный fallback и могут быть постепенно удалены.

---

## 3. Что уже считать in-scope / out-of-scope

### In scope

- перевод оставшихся экранов и backend endpoint'ов на workflow cache
- унификация API вокруг workflow-derived данных
- отображение статуса и ошибок workflow build в UI
- улучшение invalidation и refresh логики на frontend
- расширение тестов

### Out of scope

- полный отказ от fallback в этом этапе
- real-time file watching на уровне ОС
- server-side push обновлений по workflow через WebSocket subscriptions
- рефакторинг самого framework
- исправление доменных ошибок конкретных проектов, если `fw2 build` падает из-за содержимого проекта

---

## 4. Основные оставшиеся проблемы

### 4.1 SQL Editor всё ещё опирается на локальные file-based вычисления

Сейчас `SqlEditorScreen` и связанные backend endpoint'ы используют:

- `fetchProjectAutocomplete`
- `fetchModelConfigChain`
- локальный разбор параметров/CTE/priority chain

Это означает, что SQL-инспектор в ряде случаев может расходиться с тем, что реально построил framework.

### 4.2 Build/Validate экраны не используют workflow build как базовую модель проекта

Сейчас:

- `Build` использует workflow engine generate/build history, но не показывает состояние последнего абстрактного `fw2 build`
- `Validate` запускается отдельно и не привязывается явно к версии текущего workflow cache

Из-за этого пользователь не видит, на каком именно build состоянии основан интерфейс.

### 4.3 В UI нет явного статуса workflow cache

Пока автопересборка работает как `soft-fail`, но пользователь не видит:

- когда workflow был собран в последний раз
- для какой модели cache актуален
- есть ли ошибка последнего build
- использует ли экран свежий cache или fallback

### 4.4 Нет единого API-контракта для workflow cache

Сейчас workflow cache используется внутри backend-логики, но нет отдельного явного контракта:

- получить статус workflow cache проекта
- получить workflow cache модели
- принудительно пересобрать workflow

Без этого сложно строить predictable frontend flow.

---

## 5. Целевая архитектура следующего этапа

### 5.1 Новый основной принцип

Для каждой модели проекта backend должен поддерживать два слоя данных:

- `raw project files`
- `derived workflow state`

Все read-oriented UI endpoint'ы по возможности должны брать данные из `derived workflow state`.

### 5.2 Workflow cache как системный артефакт

Для каждой модели:

- файл: `.dqcr_workflow_cache/<model>.json`
- optional meta: `.dqcr_workflow_cache/<model>.meta.json`

Рекомендуемый состав meta:

```json
{
  "project_id": "sample",
  "model_id": "SalesReport",
  "status": "ready",
  "updated_at": "2026-03-21T12:00:00Z",
  "source": "framework_cli",
  "error": null
}
```

Допустимые `status`:

- `ready`
- `stale`
- `building`
- `error`
- `missing`

### 5.3 API-слой

Нужно добавить явные endpoint'ы:

- `GET /projects/{project_id}/workflow/status`
- `GET /projects/{project_id}/models/{model_id}/workflow`
- `POST /projects/{project_id}/models/{model_id}/workflow/rebuild`

Назначение:

- статус проекта целиком
- доступ к сырому workflow JSON модели
- ручной rebuild из UI

---

## 6. Оставшиеся доработки по backend

### 6.1 Workflow status/meta

Нужно реализовать хранение и чтение meta-информации по workflow cache.

Требования:

- после успешного build пишется `status=ready`
- после ошибки build пишется `status=error` и текст ошибки
- после изменения файлов до завершения пересборки можно ставить `status=building` или сразу обновлять на готовый результат
- если cache отсутствует, backend возвращает `missing`

### 6.2 Явный workflow API

Нужно отдать наружу workflow cache как first-class API.

Минимальный response для модели:

```json
{
  "project_id": "sample",
  "model_id": "SalesReport",
  "status": "ready",
  "updated_at": "2026-03-21T12:00:00Z",
  "error": null,
  "workflow": { "...": "..." }
}
```

### 6.3 Config-chain из workflow

Текущий `config-chain` endpoint должен быть переведён на вычисление из workflow cache там, где это возможно.

Минимально нужно:

- использовать `workflow.config`
- использовать `workflow.steps`
- привязывать SQL path к конкретному SQL step
- показывать значения, реально вошедшие в workflow model

Допустимо оставить частичный fallback на file parsing для полей, которых нет в `build`.

### 6.4 Autocomplete из workflow

Автодополнение параметров должно использовать:

- `param` steps
- `sql_model.metadata.parameters`
- `all_contexts`

Цель:

- пользователь видит те параметры и контексты, которые реально распознал framework

### 6.5 Привязка validate/build history к workflow state

Для `validate` и `generate` желательно сохранять ссылку на workflow timestamp или workflow version.

Минимальный вариант:

- в history результата писать `workflow_updated_at`
- при наличии meta показывать, на какой версии workflow выполнялась операция

---

## 7. Оставшиеся доработки по frontend

### 7.1 SQL Editor

Нужно перевести правую инспекторную панель на workflow-backed данные.

Подзадачи:

- `@config Priority Chain` строить из нового workflow/config-chain API
- `Parameters Used` брать из workflow-derived metadata
- `CTE Inspector` брать из `sql_model.metadata` и `workflow.config`
- показывать предупреждение, если экран работает по fallback

### 7.2 Build Screen

Нужно добавить слой "Workflow Build State".

Что должно появиться:

- текущий статус workflow cache по модели
- время последней успешной сборки workflow
- кнопка `Rebuild Workflow`
- отображение ошибки последней workflow build

`Build Screen` должен различать два типа сборки:

- абстрактный `framework build`
- engine-specific `framework generate`

### 7.3 Validate Screen

Нужно показать связь validation с текущим workflow state.

Минимально:

- timestamp текущего workflow
- индикатор устаревшего workflow, если validation старее последнего build

### 7.4 Model Editor и Parameters

Эти экраны уже читают workflow-backed данные, но нужно довести UX:

- показывать, что данные пришли из workflow build
- показывать статус устаревания после несохранённых изменений
- после save делать явное refresh workflow-backed query

### 7.5 Global project status

В `TopBar` или `StatusBar` нужен общий индикатор:

- `Workflow: ready`
- `Workflow: building`
- `Workflow: error`
- `Workflow: fallback`

Это снимет для пользователя неопределённость, на каких данных сейчас живёт Studio.

---

## 8. UX-требования

### 8.1 Soft-fail сохраняется

Если workflow build падает:

- редактирование файла не блокируется
- пользователь видит toast + системный статус ошибки
- старый cache можно продолжать использовать только явно как stale/fallback

### 8.2 Нельзя скрывать источник данных

Каждый экран, который использует workflow-backed модель, должен иметь возможность показать:

- build timestamp
- model id
- status
- источник: `framework_cli` / `fallback`

### 8.3 Refresh должен быть предсказуемым

После сохранения:

1. файл сохраняется
2. запускается rebuild
3. invalidate нужных query
4. экран получает обновлённый workflow state

Frontend не должен полагаться только на повторное открытие вкладки.

---

## 9. Нефункциональные требования

### 9.1 Производительность

- чтение workflow cache должно быть дешевле, чем повторный парсинг проекта
- повторный заход на экран не должен инициировать лишний rebuild
- rebuild должен происходить только для затронутых моделей, кроме глобальных изменений (`project.yml`, `contexts/*`, global parameters)

### 9.2 Наблюдаемость

Нужно логировать:

- запуск workflow rebuild
- успех/ошибку rebuild
- какие модели были затронуты
- какой endpoint отдал fallback вместо workflow data

### 9.3 Тестируемость

Нужно покрыть тестами:

- workflow status API
- workflow raw endpoint
- SQL/config-chain поверх workflow cache
- stale/error сценарии
- frontend query invalidation для rebuild flow

---

## 10. Предлагаемый порядок реализации

### Этап 1. Workflow status API

- meta-файлы или equivalent in-memory status
- endpoint статуса проекта и модели
- ручной rebuild endpoint

### Этап 2. SQL/config-chain migration

- workflow-backed config-chain
- workflow-backed autocomplete
- обновление SQL Editor

### Этап 3. Build/Validate UX alignment

- отображение workflow state в Build/Validate
- маркировка stale/error
- привязка history к workflow timestamp

### Этап 4. Cleanup

- минимизация старых локальных эвристик
- перевод fallback в clearly deprecated path
- финальная ревизия API контрактов

---

## 11. Критерии приёмки

Этап можно считать завершённым, если выполняются все условия:

1. Для каждой модели можно получить raw workflow JSON через API.
2. UI явно показывает статус workflow cache.
3. `SQL Editor`, `Lineage`, `Model Editor`, `Parameters` используют workflow-backed данные как primary source.
4. После изменения файла связанная модель автоматически пересобирается и UI обновляется без ручного reopen.
5. При ошибке `fw2 build` пользователь видит понятную ошибку и индикатор деградации.
6. Для ключевых workflow-backed endpoint'ов есть тесты.

---

## 12. Риски и компромиссы

### Риск 1. В `fw2 build` может не хватать части данных для текущего UI

Смягчение:

- допускается частичный fallback
- fallback должен быть явным и наблюдаемым

### Риск 2. Частые rebuild после каждого save могут быть шумными

Смягчение:

- при необходимости добавить debounce на frontend или backend
- не делать этого преждевременно до появления реальной проблемы

### Риск 3. Несогласованность между stale cache и file system

Смягчение:

- статус `stale`
- явный `updated_at`
- manual rebuild action

---

## 13. Итог

Следующий этап интеграции уже не про сам вызов framework, а про доведение Studio до архитектурной целостности:

- framework build должен стать центральной производной моделью проекта
- UI должен видеть и показывать состояние этой модели
- file-based логика должна остаться только как временный fallback

После выполнения этого документа `DQCR Studio` будет гораздо ближе к режиму, где framework действительно является единственным источником вычисленного состояния проекта.
