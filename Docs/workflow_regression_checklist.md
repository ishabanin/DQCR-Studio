# DQCR Studio — Workflow-Backed Regression Checklist

**Документ:** `workflow_regression_checklist.md`  
**Цель:** QA-проверка экранов и API, работающих от workflow cache.

---

## 1. Подготовка

1. Убедиться, что backend и frontend запущены.
2. Открыть проект с минимум 2 моделями.
3. Выполнить `Rebuild Workflow` хотя бы для одной модели.

---

## 2. SQL Editor

1. Открыть SQL-файл модели.
2. Проверить, что `@config Priority Chain` заполнен.
3. Проверить `Parameters Used` и `CTE Inspector` для SQL с параметрами/CTE.
4. Отредактировать SQL и сохранить.
5. Проверить, что панель перечиталась и workflow-backed данные обновились.
6. В сценарии недоступного workflow убедиться, что показан fallback-индикатор.

---

## 3. Build Screen

1. Открыть Build экран.
2. Проверить блок `Workflow Build State`:
   - статус модели
   - timestamp последнего workflow build
   - source
3. Нажать `Rebuild Workflow`.
4. Проверить обновление статуса и timestamp.
5. При ошибке build проверить отображение текста ошибки.

---

## 4. Validate Screen

1. Запустить validate.
2. Проверить, что в результате показан workflow state/timestamp.
3. Изменить модель/SQL и обновить workflow.
4. Проверить, что предыдущий validate помечается как stale.

---

## 5. Global Status

1. Проверить StatusBar:
   - project-level workflow status
   - source и timestamp активной модели
2. Переключить модель/файл и убедиться, что статус активной модели обновляется.

---

## 6. Edge Scenarios

### 6.1 `missing`

1. Удалить `.dqcr_workflow_cache` для модели.
2. Проверить `GET /workflow/status` → `missing`.

### 6.2 `soft-fail` / `stale`

1. Иметь валидный cache.
2. Смоделировать падение `fw2 build`.
3. Проверить, что статус становится `stale`, `source=fallback`, старый cache используется.

### 6.3 `fallback`

1. Смоделировать недоступный workflow build при отсутствии cache.
2. Проверить fallback-ответы в `config-chain`, `autocomplete`, `parameters`, `lineage`, `model-object`.

### 6.4 Multi-model partial rebuild

1. В проекте с 2+ моделями изменить файл только одной модели.
2. Проверить, что пересобирается только затронутая модель.
3. Убедиться, что `updated_at` незатронутых моделей не меняется.

---

## 7. Логи (Observability)

1. Проверить наличие `workflow.fallback` для fallback-ответов.
2. Проверить наличие `workflow.rebuild.batch` с `changed_paths` и `rebuilt_models`.
3. Проверить `workflow.rebuild.succeeded`/`soft_failed`/`failed` при соответствующих сценариях.
