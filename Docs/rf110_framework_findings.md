# RF110 Framework Findings

## Кратко

После подключения реального `FTRepCBR.Workflow.FW` к `DQCR Studio` подтверждено:

- framework успешно устанавливается в backend Docker image
- `fw2 validate` и `fw2 generate` реально работают на проекте `rf110`
- backend API `POST /api/v1/projects/rf110/validate` и `POST /api/v1/projects/rf110/build` уже ходят в framework CLI

Также выявлены доменные проблемы проекта `rf110`, из-за которых validation/build пока не являются "чистыми".

Дополнительно уже исправлены два безопасных системных момента:

- в шаблонах framework `root` явно помечен как `required: false`
- в `projects/rf110/model/RF110RestTurnReg/model.yml` добавлено описание `target_table`

---

## Что уже подтверждено

### 1. End-to-end API работает

Проверены реальные вызовы backend API:

- `POST /api/v1/projects/rf110/validate`
- `POST /api/v1/projects/rf110/build`

Оба вызова отработали через `framework_cli`, а не через mock fallback.

Это значит, что цепочка:

`Frontend/Studio -> Backend API -> FWService -> fw2 -> Framework`

уже рабочая.

---

## Исправленные системные проблемы

### 1. Ложная template error по `root`

Причина:

В шаблонах framework блок `folders.root` не задавал `required`, а модель `RuleDefinition` по умолчанию считает `required=True`.

Из-за этого framework считал, что папка `root` обязана существовать в workflow как реальная папка.

Исправление:

В шаблонах:

- [flx.yml](/Users/IgorShabanin/dev/DQCR%20Studio/FTRepCBR.Workflow.FW/src/config/templates/flx.yml)
- [dwh_mart.yml](/Users/IgorShabanin/dev/DQCR%20Studio/FTRepCBR.Workflow.FW/src/config/templates/dwh_mart.yml)
- [dq_control.yml](/Users/IgorShabanin/dev/DQCR%20Studio/FTRepCBR.Workflow.FW/src/config/templates/dq_control.yml)

для `root` добавлено:

```yaml
required: false
```

Это снимает системную ложную ошибку в template validation.

---

### 2. Отсутствовало описание target table

Причина:

В `rf110` не было `target_table.description`.

Исправление:

Добавлено описание в:

- [model.yml](/Users/IgorShabanin/dev/DQCR%20Studio/projects/rf110/model/RF110RestTurnReg/model.yml)

---

## Оставшиеся доменные проблемы `rf110`

### 1. `adb_distribution_key` на insert_fc шагах

Сейчас framework продолжает выдавать ошибки вида:

- `adb_distribution_key`

По шагам:

- `001_Load__distr/002_RF110RestTurnReg_ACCDEMAND_default/sql`
- `001_Load__distr/003_RF110RestTurnReg_ACCRSRV_default/sql`
- `001_Load__distr/004_applySettings_iter/applySettings_default/sql`
- `001_Load__vtb/001_RF110RestTurnReg_ACCDEMAND_vtb_vtb/sql`
- `001_Load__vtb/002_RF110RestTurnReg_ACCRSRV_vtb_vtb/sql`

Смысл ошибки:

Для ADB framework ожидает, что на `insert_fc` шаге у query attributes будет хотя бы один `distribution_key`.

Это не инфраструктурная проблема, а проблема конфигурации конкретных запросов.

---

### 2. В проекте есть явно неполные/заглушечные SQL

Особенно выделяются:

- [003_RF110RestTurnReg_ACCRSRV.sql](/Users/IgorShabanin/dev/DQCR%20Studio/projects/rf110/model/RF110RestTurnReg/SQL/001_Load__distr/003_RF110RestTurnReg_ACCRSRV.sql)
- [applySettings.sql](/Users/IgorShabanin/dev/DQCR%20Studio/projects/rf110/model/RF110RestTurnReg/SQL/001_Load__distr/004_applySettings_iter/applySettings.sql)
- [002_RF110RestTurnReg_ACCRSRV_vtb.sql](/Users/IgorShabanin/dev/DQCR%20Studio/projects/rf110/model/RF110RestTurnReg/SQL/001_Load__vtb/002_RF110RestTurnReg_ACCRSRV_vtb.sql)

Причины:

- `003_RF110RestTurnReg_ACCRSRV.sql` возвращает `select 1 as test`, что не похоже на реальный insert в target table.
- `applySettings.sql` не выглядит как полноценный target insert и, вероятно, является промежуточным шагом.
- `002_RF110RestTurnReg_ACCRSRV_vtb.sql` фактически пустой.

Из-за этого build логирует materialization errors уровня доменной логики:

- framework не находит key attributes, ожидаемые для `insert_fc`

Это важный вывод:

часть текущих ошибок не нужно лечить только конфигом, потому что некоторые SQL сами по себе пока не соответствуют ожидаемой материализации.

---

## Что выглядит как правильное следующее направление для `rf110`

### Вариант 1. Уточнить материализацию проблемных шагов

Нужно проверить, должны ли эти шаги вообще быть `insert_fc`.

Если это:

- промежуточные staging-steps
- технические итерационные шаги
- служебные выборки

то им, возможно, лучше подходят:

- `stage_calcid`
- `ephemeral`

а не `insert_fc`.

Это особенно вероятно для:

- `003_RF110RestTurnReg_ACCRSRV.sql`
- `004_applySettings_iter/applySettings.sql`
- `002_RF110RestTurnReg_ACCRSRV_vtb.sql`

---

### Вариант 2. Добавить корректные query attributes для реальных insert_fc шагов

Если шаг действительно должен оставаться `insert_fc`, тогда ему нужно:

- иметь атрибуты, соответствующие target table
- иметь ключевые атрибуты
- для ADB иметь `distribution_key`

Это, вероятно, требуется минимум для:

- `002_RF110RestTurnReg_ACCDEMAND.sql`
- `001_RF110RestTurnReg_ACCDEMAND_vtb.sql`

Но здесь лучше не делать слепые правки без знания бизнес-логики модели.

---

## Что сделано для версионной установки framework

Добавлен пример env-конфига:

- [infra/docker/.env.framework.example](/Users/IgorShabanin/dev/DQCR%20Studio/infra/docker/.env.framework.example)

Он фиксирует рекомендованный режим:

```env
FW_INSTALL_MODE=package
FW_PACKAGE_SPEC=git+ssh://git@your-git-host/FTRepCBR.Workflow.FW.git@v2.0.0
```

Это не ломает текущую локальную разработку, но закрепляет правильную production-схему обновления framework по git tag.

---

## Итог

На текущем этапе инфраструктурная интеграция уже рабочая:

- framework упакован
- Docker его ставит
- backend API вызывает его end-to-end

Оставшиеся проблемы `rf110` уже не про интеграцию как таковую, а про содержимое проекта и точность его конфигурации под правила framework.
