# DQCR Studio — Workflow API

**Документ:** `workflow_api.md`  
**Версия:** 1.0  
**Дата:** Март 2026

---

## 1. Назначение

Workflow API предоставляет единый контракт для derived-состояния проекта, полученного через `fw2 build`, и используется как primary source of truth для UI.

---

## 2. Статусы и источники

### 2.1 `status`

Допустимые значения:

- `ready` — workflow cache актуален
- `stale` — последняя пересборка неуспешна, используется предыдущий cache
- `building` — идёт пересборка
- `error` — build завершился ошибкой, cache недоступен
- `missing` — cache отсутствует

### 2.2 `source`

Допустимые значения:

- `framework_cli` — данные получены из `fw2`/workflow cache
- `fallback` — выдан fallback-ответ

---

## 3. Endpoints

### 3.1 `GET /api/v1/projects/{project_id}/workflow/status`

Возвращает агрегированный статус workflow по проекту.

Пример:

```json
{
  "project_id": "demo",
  "status": "stale",
  "models": [
    {
      "project_id": "demo",
      "model_id": "SampleModel",
      "status": "stale",
      "updated_at": "2026-03-21T12:00:00Z",
      "error": "Framework build failed: ...",
      "source": "fallback",
      "has_cache": true
    }
  ]
}
```

### 3.2 `GET /api/v1/projects/{project_id}/models/{model_id}/workflow`

Возвращает workflow состояния модели и сам workflow payload (если доступен).

Пример:

```json
{
  "project_id": "demo",
  "model_id": "SampleModel",
  "status": "ready",
  "updated_at": "2026-03-21T12:00:00Z",
  "error": null,
  "source": "framework_cli",
  "workflow": {
    "steps": [],
    "config": {}
  }
}
```

### 3.3 `POST /api/v1/projects/{project_id}/models/{model_id}/workflow/rebuild`

Принудительно пересобирает workflow для модели и возвращает её состояние.

Ответ имеет тот же формат, что и `GET .../workflow`.

---

## 4. Workflow-связанные поля в существующих endpoint'ах

### 4.1 Build / Validate

В `build` и `validate` результаты и history добавлены поля:

- `workflow_updated_at`
- `workflow_status`
- `workflow_source`
- `workflow_attached`

Это позволяет определить, на каком workflow state выполнялась операция.

### 4.2 Config Chain / Autocomplete / Model Object

Дополнительные поля для прозрачности источника:

- `data_source`: `workflow|fallback`
- `fallback`: `true|false`
- workflow-контекст: `workflow_status`, `workflow_source`, `workflow_updated_at` (где применимо)

---

## 5. Наблюдаемость (Observability)

### 5.1 Логи fallback

Для всех случаев fallback вместо workflow-backed ответа пишется warning:

- `workflow.fallback endpoint=... project_id=... model_id=... reason=...`

### 5.2 Логи rebuild

Пересборка моделей логируется как отдельные события:

- `workflow.rebuild.succeeded`
- `workflow.rebuild.soft_failed`
- `workflow.rebuild.failed`
- `workflow.rebuild.batch` (с перечнем `changed_paths`, `rebuilt_models`, `errors`)

