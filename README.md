# DQCR Studio

Foundation scaffold for DQCR Studio.

## Structure

- `frontend/` — Vite + React + TypeScript scaffold
- `backend/` — FastAPI scaffold with health and API v1 routing
- `infra/docker/` — Docker Compose and Nginx proxy config
- `Docs/` — product and engineering documentation

Main system reference:

- `Docs/SYSTEM_REFERENCE.md` — architecture, API, internal folders, runtime flows, and testing context

## Quick start

1. Run `make dev`
2. Open `http://localhost:80`
3. Check API health:
   - `http://localhost:80/health`
   - `http://localhost:80/ready`
4. Check projects API:
   - `http://localhost:80/api/v1/projects`
5. Check files API for demo project:
   - `http://localhost:80/api/v1/projects/demo/files/tree`
   - `http://localhost:80/api/v1/projects/demo/files/content?path=project.yml`

## Production deploy (very simple)

Minimal requirements:

- Docker + Docker Compose

### 1) Go to project directory

```bash
cd "/Users/IgorShabanin/dev/DQCR Studio"
```

### 2) Start production (automated)

```bash
make prod-up
```

What this does automatically:

- creates `backend/.env` from `backend/.env.example` if missing
- generates secure `SECRET_KEY` if default value is still used
- builds production images
- starts containers in background
- waits for readiness

### 3) Open application

- [http://127.0.0.1](http://127.0.0.1)
- If port `80` is busy, script auto-switches to `8080`.

### 4) Check health

```bash
make prod-health
```

### Useful commands

- Start/update: `make prod-up`
- View logs: `make prod-logs`
- Stop: `make prod-down`
- Rebuild only: `make prod-build`
- Build portable bundle: `make prod-bundle`
- Custom port example: `DQCR_PORT=8080 make prod-up`

## Portable deploy without build on target machine

If you want to deploy on another machine without rebuilding images there:

1. On the source machine run:

```bash
make prod-bundle
```

2. This creates:

- `dist/dqcr-studio-bundle-<timestamp>/`
- `dist/dqcr-studio-bundle-<timestamp>.tar.gz`

3. Copy the `.tar.gz` archive to the target machine and run:

```bash
tar -xzf dqcr-studio-bundle-*.tar.gz
cd dqcr-studio-bundle-*
./bin/install.sh
```

What the bundle already contains:

- prebuilt Docker images
- `backend.env`
- `projects/`
- `catalog/`
- scripts for start, stop, logs, and health checks

Detailed Russian guide:

- `Docs/DEPLOYMENT_PRODUCTION_RU.md`

Detailed Russian guide:

- `Docs/DEPLOYMENT_PRODUCTION_RU.md`

## Implemented now

- `GET /health`
- `GET /ready`
- `GET /api/v1/projects` (filesystem-backed)
- `GET /api/v1/projects/{project_id}/files/tree`
- `GET /api/v1/projects/{project_id}/files/content?path=...`
- `PUT /api/v1/projects/{project_id}/files/content`
- `POST /api/v1/projects/{project_id}/files/rename`
- `DELETE /api/v1/projects/{project_id}/files?path=...`
- Path traversal protection for file APIs
- JSON structured request logging
- Environment validation on startup (required `SECRET_KEY`)
- SQL editor on Monaco (`@monaco-editor/react`)

## Runtime config

- `backend/.env.example` contains the required and optional backend variables.

## Testing (EPIC-13 baseline)

- Frontend unit tests: `pnpm --dir frontend test`
- Backend unit + integration tests: `uv run --directory backend pytest`
- Combined check: `make test`
- Frontend E2E critical path: `pnpm --dir frontend test:e2e`
- Load smoke (k6, 50 VUs): `k6 run backend/tests/load/epic13_smoke.js`

## Lint and quality

- Combined lint/format checks: `make lint`
- Backend lint: `uv run --directory backend --with ruff ruff check app tests`
- Frontend lint: `pnpm --dir frontend lint`
- Frontend format check: `pnpm --dir frontend format:check`

## Pre-commit

- Install hooks once: `pre-commit install`
- Run all hooks manually: `pre-commit run --all-files`
