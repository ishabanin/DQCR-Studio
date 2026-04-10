# TODO: Улучшения DQCR Studio

- [x] 1. Почистить репозиторий от артефактов сборки и кэшей, расширить `.gitignore`.
- [x] 2. Зафиксировать единый пакетный менеджер для фронта (`pnpm`), убрать конфликтующий lockfile (`package-lock.json`).
- [x] 3. Разбить `backend/app/routers/projects.py` на модули/сервисы.
- [x] 4. Подтянуть безопасность обработки ошибок в API (не отдавать raw exception наружу).
- [x] 5. Сделать реальный readiness-check вместо заглушки.
- [x] 6. Усилить тестовую стратегию (edge-cases, контракты, smoke).
- [x] 7. Добавить CI pipeline (lint + test + typecheck + build).
- [x] 8. Добавить линтеры/форматтеры и pre-commit.
