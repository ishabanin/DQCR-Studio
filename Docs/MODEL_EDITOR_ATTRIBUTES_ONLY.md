# Model Editor: Attributes-Only Catalog Import

## 1. Summary

Этот документ фиксирует упрощение `Model Editor`:

- `target_table.attributes` становится единственным источником истины для колонок модели;
- отдельный список `fields` удаляется из UI, API и `model.yml`;
- импорт из каталога вставляет данные напрямую в `target_table.attributes`.

Цель изменения: убрать дублирование структуры колонок и сделать поведение редактора модели понятным и предсказуемым.

## 2. Problem

В текущей реализации одновременно существуют два списка:

- `target_table.attributes`
- `fields`

Они оба описывают колонки модели, но:

- имеют разный набор полей;
- показываются в UI как разные сущности;
- создают ощущение, что пользователь должен поддерживать две структуры;
- усложняют сохранение, импорт, YAML sync и autocomplete.

В результате неочевидно:

- какой список является каноническим;
- куда должен писать импорт из каталога;
- откуда downstream-логика должна брать колонки модели.

## 3. Decision

Принимается следующее решение:

- каноническое описание колонок модели хранится только в `target_table.attributes`;
- `fields` как отдельная сущность удаляется;
- импорт из каталога обновляет только `target_table.attributes`;
- UI `Model Editor` показывает только одну таблицу колонок: `Attributes`.

## 4. Goals

- Упростить `Model Editor`.
- Убрать дублирование данных.
- Сделать YAML и visual mode согласованными.
- Сделать поведение импорта из каталога очевидным.
- Упростить backend-сериализацию и autocomplete.

## 5. Non-Goals

- Сохранять в `model.yml` расширенную каталожную метаинформацию вроде `display_name`.
- Поддерживать два параллельных источника колонок.
- Сохранять точную копию структуры сущности каталога внутри модели.

## 6. Source Of Truth

Единственный source of truth для колонок модели:

```yaml
target_table:
  name: Account
  schema: dbo
  attributes:
    - name: ID
      domain_type: bigint
      is_key: true
```

`target_table.attributes` используется для:

- visual editor;
- YAML editor;
- сохранения `model.yml`;
- autocomplete target table;
- downstream workflow/validation logic.

## 7. Data Model

### 7.1 Supported structure

Поддерживаемая структура `model.yml`:

```yaml
target_table:
  name: Account
  table: Account
  schema: dbo
  description: Account model
  template: flx
  engine: dqcr
  attributes:
    - name: ID
      domain_type: bigint
      is_key: true
      required: true
    - name: BranchID
      domain_type: decimal

workflow:
  description: wf
  folders:
    01_stage:
      enabled: true

cte_settings:
  default: insert_fc
  by_context: {}
```

### 7.2 Removed structure

Следующая структура считается legacy и больше не должна записываться:

```yaml
fields:
  - name: ID
    display_name: ИД
    type: bigint
    is_key: true
    nullable: false
```

## 8. Catalog Import Behavior

### 8.1 Entry point

Импорт из каталога запускается из секции `Attributes`.

Отдельного блока `Fields` в UI нет.

### 8.2 Mapping

При выборе сущности каталога её атрибуты маппятся в `target_table.attributes`:

- `catalog.attribute.name` -> `attribute.name`
- `catalog.attribute.domain_type` -> `attribute.domain_type`
- `catalog.attribute.is_key` -> `attribute.is_key`

Не сохраняются в `model.yml`:

- `display_name`
- `nullable`
- прочая каталожная справочная метаинформация, если для неё нет канонического поля в модели

### 8.3 Import modes

Поддерживаются два режима:

- `Replace`
  - полностью заменить `target_table.attributes` атрибутами из каталога;
- `Merge`
  - обновить совпавшие по имени атрибуты;
  - атрибуты, отсутствующие в каталоге, сохранить;
  - новые атрибуты из каталога добавить.

### 8.4 Additional updates

При импорте можно обновлять:

- `target_table.name`
- `target_table.table`

если это соответствует текущему поведению выбора сущности каталога.

## 9. UI Requirements

`Model Editor` в visual mode должен содержать:

- `Target Table`
- `Attributes`
- `Workflow Folders`
- `CTE Settings`

Секция `Attributes` должна поддерживать:

- ручное редактирование;
- добавление строки;
- удаление строки;
- drag-and-drop порядка;
- импорт из каталога;
- replace/merge сценарии.

UI больше не должен содержать:

- секцию `Fields`;
- summary/diff для `fields`;
- отдельное состояние `existingFields`;
- тексты вида `Import fields from catalog`.

Новая формулировка:

- `Import attributes from catalog`
- `Replace model attributes with catalog attributes`
- `Merge catalog attributes into model attributes`

## 10. API Requirements

### 10.1 Read model

API чтения модели не должно возвращать `fields` как часть нормальной структуры модели.

Ожидаемая форма:

```json
{
  "model": {
    "target_table": {
      "name": "Account",
      "schema": "dbo",
      "attributes": []
    },
    "workflow": {
      "folders": []
    },
    "cte_settings": {
      "default": "insert_fc",
      "by_context": {}
    }
  }
}
```

### 10.2 Save model

API сохранения модели:

- принимает только `target_table.attributes` как список колонок модели;
- не пишет `fields` в `model.yml`;
- не требует `fields` в payload.

### 10.3 JSON Schema

JSON Schema для `model.yml`:

- должна содержать `target_table.attributes`;
- не должна содержать верхнеуровневое свойство `fields`.

## 11. Autocomplete Requirements

Autocomplete target table строится только по:

- `target_table.attributes`

Fallback на `fields` в новой логике не используется.

Если у модели нет `target_table.attributes`, autocomplete колонок target table считается пустым.

## 12. Backward Compatibility

Нужно сохранить возможность чтения старых проектов, где `fields` уже записан в `model.yml`.

Поддерживаемое поведение:

- backend может распознать legacy `fields` при чтении;
- если `target_table.attributes` пустой, допустима одноразовая миграция `fields -> target_table.attributes`;
- при следующем сохранении `fields` больше не пишется;
- после сохранения структура модели становится canonical.

Правило приоритета:

- если присутствуют и `target_table.attributes`, и `fields`, каноническим считается `target_table.attributes`.

## 13. Migration Rules

Миграция `fields -> target_table.attributes` выполняется по имени колонки.

Соответствие полей:

- `fields[].name` -> `attributes[].name`
- `fields[].type` -> `attributes[].domain_type`
- `fields[].is_key` -> `attributes[].is_key`

Не мигрируются:

- `display_name`
- `nullable`

Если после миграции получаются дубликаты по имени:

- остаётся первая каноническая запись;
- остальные считаются конфликтными и должны быть отброшены или залогированы.

## 14. Acceptance Criteria

### AC-01 Visual editor

- Пользователь видит только одну таблицу колонок: `Attributes`.
- Секция `Fields` отсутствует.

### AC-02 Catalog import

- Импорт из каталога добавляет колонки в `target_table.attributes`.
- После импорта пользователь сразу видит результат в таблице `Attributes`.

### AC-03 YAML

- После сохранения в `model.yml` отсутствует блок `fields:`.
- Все импортированные колонки находятся в `target_table.attributes`.

### AC-04 API

- `GET /models/{id}` не возвращает `fields` как рабочую часть модели.
- `PUT /models/{id}` не требует `fields`.

### AC-05 Autocomplete

- Колонки target table в autocomplete берутся из `target_table.attributes`.
- Fallback на `fields` отсутствует.

### AC-06 Legacy compatibility

- Старый `model.yml` с `fields` открывается без ошибки.
- После первого сохранения `fields` исчезает, а структура становится canonical.

## 15. Risks

- Возможна потеря legacy-метаданных `display_name` и `nullable`, если кто-то использовал их вне UI.
- Возможны несовпадения в старых тестах и e2e сценариях, завязанных на `fields`.
- Нужна аккуратная миграция, чтобы не затереть уже существующие `target_table.attributes`.

## 16. Implementation Notes

Ожидаемые зоны изменения:

- frontend:
  - `ModelEditorScreen`
  - `EntityPickerDialog`
  - `syncEngine`
  - типы API модели
- backend:
  - parse/dump `model.yml`
  - JSON Schema builder
  - model read/save endpoints
  - autocomplete builder
- tests:
  - backend unit/integration
  - frontend/e2e

## 17. Status

Статус документа: approved product direction, pending implementation.
