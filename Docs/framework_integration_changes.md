# Интеграция Framework в DQCR Studio

## Кратко

Сделаны следующие изменения для следующего этапа интеграции `FTRepCBR.Workflow.FW` с `DQCR Studio`:

- backend Docker теперь умеет устанавливать framework
- добавлена поддержка двух режимов установки framework:
  - локально из папки репозитория
  - как внешнего пакета по `FW_PACKAGE_SPEC`
- backend получил конфиг для запуска framework CLI
- `FWService` теперь умеет вызывать реальный `fw2` для `generate` и `validate`
- оставлен fallback на текущую встроенную mock-логику, если CLI недоступен

Это позволяет постепенно переключать Studio на реальный framework без резкого слома текущего поведения.

---

## Что изменено

### 1. Docker backend переведён на установку framework

Файл: [backend/Dockerfile](/Users/IgorShabanin/dev/DQCR%20Studio/backend/Dockerfile)

Что изменено:

- build context теперь может включать и `backend`, и `FTRepCBR.Workflow.FW`
- в image копируется локальный framework
- добавлены build args:
  - `FW_INSTALL_MODE`
  - `FW_PACKAGE_SPEC`

Поддерживаются два сценария:

**Локальная интеграция**

```bash
FW_INSTALL_MODE=local
```

В этом режиме Docker ставит framework из локальной папки:

```bash
/opt/fw-src
```

Это удобно на текущем этапе разработки.

**Версионируемая внешняя интеграция**

```bash
FW_INSTALL_MODE=package
FW_PACKAGE_SPEC=git+ssh://git@<repo>/FTRepCBR.Workflow.FW.git@v2.1.0
```

В этом режиме backend ставит framework по зафиксированной версии.

Именно этот режим рекомендуется для production и для управляемых обновлений.

---

### 2. Docker Compose подготовлен под версионируемую установку framework

Файл: [infra/docker/docker-compose.yml](/Users/IgorShabanin/dev/DQCR%20Studio/infra/docker/docker-compose.yml)

Что изменено:

- backend build context переведён на корень проекта
- указан `dockerfile: backend/Dockerfile`
- добавлены build args:
  - `FW_INSTALL_MODE`
  - `FW_PACKAGE_SPEC`
- добавлены runtime env vars:
  - `FW_USE_CLI`
  - `FW_CLI_COMMAND`

Теперь можно управлять интеграцией framework через переменные, а не через ручные правки кода.

---

### 3. Backend получил конфиг framework CLI

Файлы:

- [backend/app/core/config.py](/Users/IgorShabanin/dev/DQCR%20Studio/backend/app/core/config.py)
- [backend/.env.example](/Users/IgorShabanin/dev/DQCR%20Studio/backend/.env.example)

Добавлены настройки:

- `FW_USE_CLI`
- `FW_CLI_COMMAND`

Назначение:

- `FW_USE_CLI=true` включает реальный вызов framework из backend
- `FW_CLI_COMMAND=fw2` задаёт команду CLI

Это позволяет:

- держать интеграцию управляемой через конфиг
- временно отключать реальный вызов framework без переписывания кода

---

### 4. `FWService` теперь умеет вызывать реальный framework CLI

Файл: [backend/app/services/fw_service.py](/Users/IgorShabanin/dev/DQCR%20Studio/backend/app/services/fw_service.py)

Добавлено:

- проверка доступности `fw2`
- запуск framework через `subprocess`
- отдельная обработка:
  - `validate`
  - `generate`
- преобразование framework output в текущий формат API Studio

#### `validate`

Backend теперь может запускать:

```bash
fw2 validate <project_path> <model_id> -o <output_dir>
```

После этого backend:

- читает JSON report framework
- преобразует issues в текущий список `rules`
- возвращает их в прежнем API-формате

#### `generate`

Backend теперь может запускать:

```bash
fw2 generate <project_path> <model_id> -c <context> -w <engine> -o <output_dir>
```

После этого backend:

- сканирует output directory
- собирает список generated files
- возвращает build result в текущем формате Studio

---

### 5. Сохранён безопасный fallback

Если framework CLI недоступен, backend не падает сразу.

Он продолжает использовать текущую встроенную логику:

- mock generation
- mock validation

Почему это важно:

- локальная разработка не ломается
- интеграцию можно включать поэтапно
- можно быстро сравнивать новое и старое поведение

---

## Как теперь обновлять framework

Рекомендуемый сценарий:

1. Команда framework выпускает git tag, например `v2.2.0`
2. В окружении сборки меняется:

```bash
FW_INSTALL_MODE=package
FW_PACKAGE_SPEC=git+ssh://git@<repo>/FTRepCBR.Workflow.FW.git@v2.2.0
```

3. Пересобирается backend image
4. Проверяются:
   - build
   - validate
   - чтение generated files

Обновление framework сводится к смене одной версии, а не к ручному копированию файлов.

---

## Почему это соответствует требованию “framework разрабатывает другая команда”

Потому что теперь `DQCR Studio` может использовать framework как отдельную внешнюю зависимость.

Это значит:

- Studio не обязана жить на форке framework
- можно явно фиксировать версию framework
- можно быстро обновлять и откатывать версию
- граница ответственности между командами становится понятнее

---

## Что осталось сделать дальше

Следующие шаги логично делать в таком порядке:

1. Собрать Docker backend и проверить, что `fw2` доступен внутри контейнера.
2. Прогнать реальный `validate` на одном проекте.
3. Прогнать реальный `generate` на одном проекте.
4. При необходимости доработать преобразование framework report в UI-формат Studio.
5. По мере стабилизации убрать fallback mock-реализацию.

---

## Как включить versioned install через `FW_PACKAGE_SPEC`

Для production или общей dev-среды рекомендуется использовать не локальный framework из workspace, а зафиксированную версию из git.

Для этого подготовлен пример файла:

- [infra/docker/.env.framework.example](/Users/IgorShabanin/dev/DQCR%20Studio/infra/docker/.env.framework.example)

Пример:

```env
FW_INSTALL_MODE=package
FW_PACKAGE_SPEC=git+ssh://git@your-git-host/FTRepCBR.Workflow.FW.git@v2.0.0
FW_USE_CLI=true
FW_CLI_COMMAND=fw2
```

Дальше Docker Compose можно запускать так:

```bash
set -a
source infra/docker/.env.framework.example
set +a
docker compose -f infra/docker/docker-compose.yml build backend
docker compose -f infra/docker/docker-compose.yml up -d backend
```

Что это даёт:

- backend image ставит framework по конкретному git tag
- обновление framework сводится к смене `FW_PACKAGE_SPEC`
- откат версии так же прост, как возврат к предыдущему тегу

---

## Итог

Сделан промежуточный, но уже рабочий слой интеграции:

- framework стал устанавливаемой зависимостью
- backend умеет вызывать его CLI
- версия framework может управляться отдельно
- локальная разработка не блокируется, потому что fallback сохранён
