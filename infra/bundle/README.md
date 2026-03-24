# DQCR Studio Portable Bundle

Этот пакет уже содержит:

- готовые Docker-образы `dqcr-studio-backend:prod` и `dqcr-studio-frontend:prod`
- runtime-конфигурацию `backend.env`
- папки `projects/` и `catalog/`
- скрипты для запуска без локальной сборки

## Требования на целевой машине

- Docker Engine
- Docker Compose plugin (`docker compose`)
- `bash`, `gzip`, `tar`, `curl`
- `lsof` optional, only for automatic preflight port check

## Быстрый запуск

1. Распакуйте архив bundle:

```bash
tar -xzf dqcr-studio-bundle-*.tar.gz
cd dqcr-studio-bundle-*
```

2. Загрузите образы и поднимите приложение:

```bash
./bin/install.sh
```

3. Откройте приложение:

- [http://127.0.0.1](http://127.0.0.1)
- если порт `80` занят, скрипт автоматически переключится на `8080`

## Команды эксплуатации

```bash
./bin/install.sh              # импорт образов + запуск
./bin/load-images.sh          # только импорт образов
./bin/up.sh                   # запуск контейнеров без сборки
./bin/down.sh                 # остановка
./bin/logs.sh                 # логи
./bin/health.sh               # health-check
DQCR_PORT=8080 ./bin/up.sh    # запуск на другом порту
```

## Обновление на целевой машине

1. Остановите текущую версию:

```bash
./bin/down.sh
```

2. Замените bundle на новый архив.
3. Распакуйте новую версию.
4. Выполните:

```bash
./bin/install.sh
```

## Состав bundle

- `docker-compose.yml` — запуск только из готовых образов, без `build`
- `images/dqcr-studio-images.tar.gz` — архив Docker-образов
- `images/SHA256SUMS` — контрольная сумма архива образов
- `backend.env` — backend-конфигурация
- `projects/` — проекты
- `catalog/` — каталог
- `bin/*.sh` — скрипты эксплуатации
