# Suggested commands

## Core workflow

- `make dev` — start dev stack (backend + frontend + nginx) via `infra/docker/docker-compose.yml`.
- `make down` — stop dev stack.
- `make build` — build dev docker images.
- `make test` — run backend + frontend test baseline.

## Backend

- `uv run --directory backend pytest` — run backend tests.
- `python3 -m compileall backend/app` — quick backend syntax check (included in `make test`).
- `uv run --directory backend uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` — run backend outside docker (if needed).

## Frontend

- `pnpm --dir frontend install` — install frontend dependencies.
- `pnpm --dir frontend dev --host 0.0.0.0 --port 5173` — run frontend dev server.
- `pnpm --dir frontend build` — type-check/build frontend.
- `pnpm --dir frontend test` — run unit tests (Vitest).
- `pnpm --dir frontend test:e2e` — run E2E tests (Playwright).
- `pnpm --dir frontend preview --host 127.0.0.1 --port 4173` — preview build (used by Playwright config).

## Production helpers

- `make prod-up` — prepare env, build, and start production containers.
- `make prod-down` — stop production containers.
- `make prod-logs` — follow production logs.
- `make prod-health` — check `/health`, `/ready`, and `/api/v1/projects`.
- `make prod-build` — build production images only.
- `make prod-bundle` — build portable deployment bundle.
- `DQCR_PORT=8080 make prod-up` — start prod stack on a custom port.

## Useful local checks

- `curl -fsS http://127.0.0.1:80/health`
- `curl -fsS http://127.0.0.1:80/ready`
- `curl -fsS http://127.0.0.1:80/api/v1/projects`

## Darwin utility commands

- `git status`, `git diff`, `git add`, `git commit`
- `ls`, `find`, `rg`, `cd`
- `sed`, `cat`, `head`, `tail`
- `docker compose ...`
- `lsof -iTCP:<PORT> -sTCP:LISTEN` for port conflicts
