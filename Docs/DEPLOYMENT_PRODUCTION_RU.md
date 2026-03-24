# Production deployment (простая инструкция)

## Быстрый запуск

1. Перейдите в папку проекта:

```bash
cd "/Users/IgorShabanin/dev/DQCR Studio"
```

2. Запустите production:

```bash
make prod-up
```

3. Откройте приложение:

- [http://127.0.0.1](http://127.0.0.1)
- Если порт `80` занят, скрипт автоматически запустит на `8080`.

4. Проверьте здоровье сервисов:

```bash
make prod-health
```

## Что автоматизировано

- Если `backend/.env` отсутствует, он создаётся автоматически из `backend/.env.example`.
- Если `SECRET_KEY=dev-secret-key`, скрипт автоматически ставит безопасный случайный ключ.
- Контейнеры собираются и запускаются в фоне.

## Полезные команды

```bash
make prod-up      # запустить/обновить
make prod-logs    # смотреть логи
make prod-down    # остановить
make prod-build   # только пересобрать образы
```

Запуск на своем порту:

```bash
DQCR_PORT=8080 make prod-up
```

## Где что работает

- Frontend + gateway nginx: `http://<host>:<port>`
- Backend API через gateway: `http://<host>:<port>/api/v1/...`
- Backend health: `http://<host>:<port>/health`

## Первый запуск на новом сервере (3 команды)

```bash
git clone <REPO_URL>
cd "DQCR Studio"
make prod-up
```

## Перенос на другую машину без сборки

Этот сценарий нужен, если вы хотите один раз собрать контейнеры на исходной машине, а на другой машине только импортировать готовые образы и запустить приложение.

### Что именно получится в результате

Команда сборки bundle создаёт переносимый пакет, в который входят:

- готовые Docker-образы `dqcr-studio-backend:prod` и `dqcr-studio-frontend:prod`
- `backend.env`
- папка `projects/`
- папка `catalog/`
- отдельный `docker-compose.yml` без секции `build`
- набор эксплуатационных скриптов `bin/*.sh`

То есть на целевой машине сборка приложения уже не потребуется.

### Шаг 1. Подготовить bundle на исходной машине

Перейдите в корень проекта и выполните:

```bash
make prod-bundle
```

Что делает эта команда автоматически:

- проверяет `backend/.env`
- при необходимости создаёт его из `backend/.env.example`
- если `SECRET_KEY` ещё дефолтный, генерирует безопасное значение
- собирает production-образы
- экспортирует образы в архив `docker save | gzip`
- копирует runtime-данные и конфигурацию в bundle
- упаковывает итог в `.tar.gz`

После выполнения появятся два артефакта:

```bash
dist/dqcr-studio-bundle-<timestamp>/
dist/dqcr-studio-bundle-<timestamp>.tar.gz
```

### Шаг 2. Перенести bundle на целевую машину

Скопируйте архив:

```bash
dist/dqcr-studio-bundle-<timestamp>.tar.gz
```

на целевую машину любым удобным способом:

- `scp`
- `rsync`
- через сетевую папку
- через внешний диск

Пример:

```bash
scp dist/dqcr-studio-bundle-<timestamp>.tar.gz user@target-host:/opt/dqcr/
```

### Шаг 3. Развернуть bundle на целевой машине

На целевой машине нужны только:

- Docker Engine
- Docker Compose plugin
- `bash`, `tar`, `gzip`, `curl`
- `lsof` опционально, нужен только для автоматической проверки занятого порта до старта

Дальше выполните:

```bash
cd /opt/dqcr
tar -xzf dqcr-studio-bundle-*.tar.gz
cd dqcr-studio-bundle-*
./bin/install.sh
```

Команда `./bin/install.sh` делает два действия подряд:

1. загружает готовые образы через `docker load`
2. запускает `docker compose up -d` без сборки

### Шаг 4. Проверить приложение

После запуска откройте:

- [http://127.0.0.1](http://127.0.0.1)

Если порт `80` занят, скрипт автоматически попробует `8080`.

Проверка состояния:

```bash
./bin/health.sh
```

Просмотр логов:

```bash
./bin/logs.sh
```

Остановка:

```bash
./bin/down.sh
```

### Запуск на другом порту

Если вы хотите сразу запустить на нестандартном порту:

```bash
DQCR_PORT=8080 ./bin/up.sh
```

### Как обновлять поставку

Когда на исходной машине появилась новая версия:

1. Выполните заново:

```bash
make prod-bundle
```

2. Перенесите новый архив на целевую машину.
3. В каталоге старой версии остановите контейнеры:

```bash
./bin/down.sh
```

4. Распакуйте новый bundle.
5. Выполните:

```bash
./bin/install.sh
```

### Максимально короткий сценарий

На исходной машине:

```bash
make prod-bundle
```

На целевой машине:

```bash
tar -xzf dqcr-studio-bundle-*.tar.gz
cd dqcr-studio-bundle-*
./bin/install.sh
```
