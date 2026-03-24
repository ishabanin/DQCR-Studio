# Task completion checklist

When finishing a coding task in this project, run the smallest relevant subset below:

1. Backend checks (if backend files changed):
- `python3 -m compileall backend/app`
- `uv run --directory backend pytest`

2. Frontend checks (if frontend files changed):
- `pnpm --dir frontend test`
- `pnpm --dir frontend build`

3. End-to-end checks (if UI flow/routing/API integration changed):
- `pnpm --dir frontend test:e2e`

4. Full baseline check (when changes touch multiple layers):
- `make test`

5. Runtime sanity checks (when running stack):
- `curl -fsS http://127.0.0.1:80/health`
- `curl -fsS http://127.0.0.1:80/ready`
- `curl -fsS http://127.0.0.1:80/api/v1/projects`

6. Production script changes:
- verify `make prod-up` and `make prod-health` work as expected.

Notes:
- Keep checks scoped to changed areas to reduce cycle time.
- If local ports are busy, use `DQCR_PORT=<port>` for prod helpers.
