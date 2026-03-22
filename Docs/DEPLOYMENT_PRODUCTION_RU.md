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
