# DQCR Studio — project overview

## Purpose

DQCR Studio is a filesystem-first studio for creating and maintaining DQCR projects.
It provides:
- a project hub for project management;
- an IDE-style workbench for editing model/workflow files;
- backend APIs for file operations, metadata, validation, build, and workflow cache;
- integration with `FTRepCBR.Workflow.FW` (`fw2`) for validation/build workflows.

Core principle: source of truth is project files in `projects/`, not a database.

## Tech stack

- Frontend: React 18, TypeScript (strict), Vite, Zustand, TanStack Query, Monaco, React Flow, xterm.
- Backend: FastAPI, Uvicorn, Pydantic Settings, openpyxl, python-multipart, ptyprocess.
- Infra: Docker Compose + Nginx reverse proxy.
- Build/test tooling: `make`, `uv`, `pnpm`, `pytest`, `vitest`, `playwright`.

## Repository structure (high-level)

- `frontend/` — SPA (hub + workbench UI), tests, Vite/Playwright configs.
- `backend/` — FastAPI app (`app/`), tests (`tests/`), Python package config.
- `infra/docker/` — dev/prod compose and nginx configs.
- `projects/` — filesystem projects (runtime data and artifacts).
- `catalog/` — entity catalog files used by backend/features.
- `scripts/` — production helper scripts (`prod-up`, `prod-down`, `prod-health`, etc.).
- `Docs/` — system/user/product documentation.
- `FTRepCBR.Workflow.FW/` — framework source used by backend and build/validate flows.
