# DQCR Studio

Foundation scaffold for DQCR Studio.

## Structure

- `frontend/` — Vite + React + TypeScript scaffold
- `backend/` — FastAPI scaffold with health and API v1 routing
- `infra/docker/` — Docker Compose and Nginx proxy config
- `Docs/` — product and engineering documentation

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
