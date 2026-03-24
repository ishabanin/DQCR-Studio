# Style and conventions

## General

- Architecture is filesystem-first: project data is represented by files under `projects/`.
- Prefer explicit, readable code over compact but opaque patterns.
- Keep API/UI behavior aligned with existing routes and feature module boundaries.

## Python backend conventions

- Use type hints consistently (`-> None`, `dict[str, str]`, etc.).
- `snake_case` for functions/variables; `PascalCase` for classes.
- Group imports by stdlib / third-party / local modules.
- FastAPI routers live under `backend/app/routers`, services under `backend/app/services`, shared core utilities under `backend/app/core`.
- Pydantic settings/models are used for structured config and request/response models.
- Raise/translate domain errors to proper HTTP responses.
- Tests use `pytest`, with names `test_*.py` and focused unit/integration scenarios.

## TypeScript frontend conventions

- TypeScript strict mode is enabled (`frontend/tsconfig.json` has `"strict": true`).
- Prefer typed APIs (`type` aliases/interfaces, `import type` where relevant).
- `PascalCase` for React components, `camelCase` for hooks/helpers/state fields.
- Organize by feature folders under `frontend/src/features/*`; shared UI primitives in `frontend/src/shared`.
- State management uses Zustand stores under `frontend/src/app/store`.
- Keep side effects explicit in hooks (`useEffect`) and data fetching via API modules + React Query.

## Formatting and linting status

- No dedicated repo-level lint/format commands were found in root scripts.
- Primary quality gates currently are:
  - backend tests (`pytest`);
  - frontend tests (`vitest`, `playwright`);
  - TypeScript build/type-check via `pnpm --dir frontend build`;
  - Python compile check via `python3 -m compileall backend/app` (via `make test`).
