# SQL Autocomplete from Connected Catalog

## 1. Назначение

Этот документ описывает реализацию доработки SQL autocomplete в DQCR Studio для AI-агента.

Цель: сделать так, чтобы в `SQL Editor` при наборе SQL-запроса в autocomplete появлялись объекты из загруженного Data Catalog, а также их колонки при обращении через алиас.

Документ ориентирован на реализацию в коде, а не на продуктовую презентацию.

---

## 2. Проблема

На текущий момент Data Catalog уже существует в системе:

- каталог можно загрузить через backend;
- каталог можно просматривать в UI;
- из каталога можно импортировать атрибуты в `Model Editor`.

Однако SQL autocomplete фактически использует только данные проекта:

- параметры;
- builtin macros;
- config keys;
- project target tables;
- workflow queries активной модели.

Из-за этого после загрузки каталога пользователь не видит сущности каталога в подсказках SQL editor, если они не были отдельно импортированы в `model.yml`.

---

## 3. Целевое поведение

После загрузки каталога:

1. В `SQL Editor` в object-context autocomplete должны появляться сущности каталога.
2. При вводе:

```sql
select a.
from Account a
```

autocomplete должен предлагать колонки сущности `Account`.

3. Project objects не должны пропасть:
   - `workflow_query`
   - `target_table`

4. Подсказки из каталога должны работать даже если сущность не импортирована в модель.

5. Если каталог не загружен, система должна вести себя как сейчас, без ошибок и без деградации текущего autocomplete.

---

## 4. Scope

## In scope

- расширение backend autocomplete API;
- преобразование catalog entities в autocomplete objects;
- расширение frontend типов autocomplete objects;
- использование catalog objects в SQL Monaco autocomplete;
- инвалидация autocomplete cache после загрузки/замены каталога;
- unit/integration/e2e тесты на новую функциональность.

## Out of scope

- fuzzy ranking или умный поиск по catalog display name;
- отдельный UI-переключатель "показывать только каталог";
- навигация по F12 в сущности каталога;
- SQL validation against real DB catalog;
- изменение формата хранения самого `catalog.json`.

---

## 5. Текущее состояние системы

### 5.1 Backend autocomplete

`GET /api/v1/projects/{project_id}/autocomplete` возвращает:

- `parameters`
- `macros`
- `config_keys`
- `objects`

Сейчас `objects` собираются только из project-level источников:

- `target_table`
- `workflow_query`

Ключевые места:

- `backend/app/routers/projects.py`
- `_collect_project_autocomplete_objects(...)`
- `get_project_autocomplete(...)`

### 5.2 Catalog backend

Catalog уже умеет:

- парсить `.xlsx`;
- сохранять `catalog.json`;
- хранить `CatalogEntity` и `CatalogAttribute`;
- отдавать список сущностей и конкретную сущность через API.

Ключевое место:

- `backend/app/services/catalog_service.py`

### 5.3 Frontend SQL autocomplete

Frontend уже умеет принимать `objects` и использовать их:

- для object suggestions;
- для member/column suggestions через алиас;
- для сортировки project objects и локальных CTE.

Но типы frontend сейчас ожидают только:

- `kind: "target_table" | "workflow_query"`
- `source: "project_workflow" | "project_model_fallback"`

Ключевые места:

- `frontend/src/api/projects.ts`
- `frontend/src/features/sql/SqlEditorScreen.tsx`
- `frontend/src/features/sql/dqcrLanguage.ts`

---

## 6. Требуемые изменения

### 6.1 Backend: добавить catalog objects в autocomplete

Нужно реализовать новый слой сборки autocomplete objects из Data Catalog.

Рекомендуемый подход:

1. Создать helper-функцию уровня `projects.py`, например:

```python
def _collect_catalog_autocomplete_objects() -> list[dict[str, object]]:
    ...
```

2. Внутри использовать `CatalogService`.

3. Если каталог недоступен:
   - вернуть пустой список;
   - не выбрасывать ошибку;
   - не менять существующее поведение `/autocomplete`.

4. Для каждой `CatalogEntity` построить autocomplete object.

Рекомендуемая форма объекта:

```json
{
  "name": "Account",
  "kind": "catalog_entity",
  "source": "catalog",
  "model_id": null,
  "path": null,
  "lookup_keys": ["Account"],
  "columns": [
    {
      "name": "account_id",
      "domain_type": "bigint",
      "is_key": true
    }
  ]
}
```

### 6.2 Backend: расширить `get_project_autocomplete`

В `get_project_autocomplete(...)` нужно:

1. Получить project objects как сейчас.
2. Получить catalog objects.
3. Объединить их в один список через существующую логику merge или через расширенную merge-логику.

Целевой принцип:

- project objects остаются;
- catalog objects добавляются;
- конфликтующие объекты не должны дублироваться бесконтрольно.

### 6.3 Merge strategy

Если имя объекта есть и в проекте, и в каталоге:

1. Предпочитать project object как основной объект.
2. Если у project object меньше колонок, можно дополнять/обогащать из catalog object.
3. Не перезаписывать `path` project object значением из catalog.

Минимально допустимое поведение:

- dedupe по `(kind, normalized_name)` или по `normalized lookup key`;
- project object приоритетнее catalog object.

Если merge по типу слишком сложный, допустим упрощённый вариант:

- не мержить catalog object с project object разных `kind`;
- но не допускать идентичные дубликаты одного и того же catalog object.

### 6.4 Frontend: расширить типы API

Нужно обновить типы в `frontend/src/api/projects.ts`.

Добавить:

- `kind: "catalog_entity"`
- `source: "catalog"`

Итоговый union:

```ts
kind: "target_table" | "workflow_query" | "catalog_entity";
source: "project_workflow" | "project_model_fallback" | "catalog";
```

### 6.5 Frontend: SQL autocomplete logic

`frontend/src/features/sql/dqcrLanguage.ts` уже умеет работать с универсальным массивом `objects`.

Нужно:

1. Убедиться, что `catalog_entity` не ломает текущую сортировку и нормализацию.
2. Обеспечить, чтобы catalog objects участвовали:
   - в object suggestions;
   - в column suggestions через алиас.

Желательное поведение сортировки:

1. local CTE;
2. workflow queries активной модели;
3. target table активной модели;
4. catalog entities;
5. остальные project objects.

Если текущую сортировку сложно менять без лишнего риска, допустим более простой вариант:

- local CTE остаются первыми;
- все остальные объекты сортируются стабильно и без регрессии.

### 6.6 Frontend: invalidate autocomplete after catalog upload

После успешной загрузки или замены каталога нужно инвалидировать query:

```ts
["autocomplete"]
```

или эквивалентно все project-specific autocomplete queries.

Цель:

- пользователь загрузил каталог;
- перешёл в SQL Editor;
- autocomplete уже использует актуальные catalog objects без ручного hard refresh.

---

## 7. API контракт

### 7.1 Изменение response `GET /api/v1/projects/{project_id}/autocomplete`

Поле `objects` теперь может содержать три типа:

```json
{
  "name": "Account",
  "kind": "catalog_entity",
  "source": "catalog",
  "model_id": null,
  "path": null,
  "lookup_keys": ["Account"],
  "columns": [
    {
      "name": "account_id",
      "domain_type": "bigint",
      "is_key": true
    }
  ]
}
```

### 7.2 Совместимость

Изменение должно быть backward compatible:

- старые клиенты, которые читают `objects` как массив, не должны падать;
- новые поля допустимы;
- существующие project objects должны остаться в прежнем формате.

---

## 8. Нефункциональные требования

1. Если каталог отсутствует, `/autocomplete` должен продолжать отвечать `200`.
2. Нельзя делать сетевых вызовов наружу.
3. Нельзя ломать fallback-логику project autocomplete.
4. Реализация должна быть безопасна для linked/imported/internal проектов.
5. Производительность должна быть достаточной для обычного объёма каталога.

Допустимое решение:

- читать catalog entities из локального `catalog.json` на каждый запрос autocomplete.

Желательное решение:

- не усложнять premature optimization, если текущий объём каталога не даёт реальной проблемы.

---

## 9. Требования к тестам

### 9.1 Backend tests

Нужно добавить тесты на `backend/tests/test_projects_api.py` или соседний тестовый модуль.

Обязательные кейсы:

1. `/autocomplete` возвращает catalog entities, если каталог загружен.
2. `columns` для catalog entity корректно маппятся из `CatalogAttribute`.
3. Если каталог не загружен, `/autocomplete` работает как раньше.
4. При наличии project object и catalog object с одинаковым именем результат не содержит нежелательных дублей.

### 9.2 Frontend tests

Нужно обновить/добавить unit tests в `frontend/src/features/sql/dqcrLanguage.test.ts`.

Обязательные кейсы:

1. catalog entity появляется в object-context suggestions;
2. колонки catalog entity появляются в member-context;
3. local CTE по-прежнему имеют приоритет в object suggestions.

### 9.3 E2E / integration

Если есть существующий e2e тест на catalog flow, нужно довести его до реального подтверждения новой логики:

1. загрузить catalog;
2. открыть SQL Editor;
3. убедиться, что autocomplete response или UI-логика включает catalog entity.

Если в текущем mock e2e это уже частично симулируется, привести его в соответствие с реальной backend-моделью.

---

## 10. Файлы-кандидаты для изменения

Основные:

- `backend/app/routers/projects.py`
- `backend/app/services/catalog_service.py` или новый helper рядом
- `frontend/src/api/projects.ts`
- `frontend/src/features/sql/SqlEditorScreen.tsx`
- `frontend/src/features/sql/dqcrLanguage.ts`
- `frontend/src/features/catalog/CatalogPanelBase.tsx`
- `backend/tests/test_projects_api.py`
- `frontend/src/features/sql/dqcrLanguage.test.ts`
- при необходимости `frontend/tests/e2e/critical-path.spec.ts`

Нежелательно менять без необходимости:

- общую архитектуру catalog API;
- существующий формат `catalog.json`;
- unrelated части `Model Editor`.

---

## 11. Пошаговый план реализации для AI-агента

1. Изучить текущую реализацию `get_project_autocomplete(...)`.
2. Реализовать преобразование `CatalogEntity -> autocomplete object`.
3. Подмешать catalog objects в backend response `/autocomplete`.
4. Обновить TS-типы frontend для нового `kind/source`.
5. Проверить и при необходимости поправить сортировку/нормализацию в `dqcrLanguage.ts`.
6. Добавить invalidation autocomplete queries после upload catalog.
7. Написать backend tests.
8. Написать frontend unit tests.
9. Прогнать релевантные тесты.
10. Убедиться, что без каталога старое поведение не изменилось.

---

## 12. Критерии приёмки

Задача считается выполненной, если:

1. После загрузки каталога `GET /api/v1/projects/{project_id}/autocomplete` возвращает catalog entities в `objects`.
2. В SQL Editor catalog entities участвуют в autocomplete object suggestions.
3. После выбора alias для catalog entity autocomplete предлагает её колонки.
4. Project objects продолжают работать как раньше.
5. Если каталог отсутствует, ошибок нет и текущее поведение не ломается.
6. Есть automated tests минимум на backend и frontend unit level.

---

## 13. Ограничения и подсказки для реализации

1. Не нужно делать отдельный новый API endpoint, если можно расширить текущий `/autocomplete`.
2. Не нужно требовать импорт сущности в `model.yml` для того, чтобы она появилась в SQL autocomplete.
3. Не нужно связывать catalog autocomplete с активной моделью, если на это нет отдельной бизнес-логики.
4. `display_name`, `module`, `info_object` не обязаны попадать в autocomplete response, если они не используются SQL editor.
5. Основной payload для SQL autocomplete:
   - `name`
   - `lookup_keys`
   - `columns`

---

## 14. Ожидаемый результат для пользователя

Пользователь загружает каталог и затем в SQL editor может писать:

```sql
select a.account_id
from Account a
```

и получать:

- подсказку `Account` в секции объектов;
- подсказку `account_id` и других колонок после `a.`

без предварительного импорта этой сущности в модель проекта.
