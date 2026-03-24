#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
while [[ -L "$SCRIPT_PATH" ]]; do
  SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_PATH")" && pwd)"
  SCRIPT_PATH="$(readlink "$SCRIPT_PATH")"
  [[ "$SCRIPT_PATH" != /* ]] && SCRIPT_PATH="$SCRIPT_DIR/$SCRIPT_PATH"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SCRIPT_PATH")" && pwd)"
ROOT_DIR="$(cd -P "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"
APP_PORT="${DQCR_PORT:-80}"

if [[ ! -f "$ROOT_DIR/backend.env" ]]; then
  echo "Missing backend.env in bundle root"
  exit 1
fi

if command -v lsof >/dev/null 2>&1 && lsof -iTCP:"$APP_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  if [[ -z "${DQCR_PORT:-}" ]]; then
    APP_PORT=8080
    export DQCR_PORT="$APP_PORT"
    echo "Port 80 is busy. Falling back to port $APP_PORT (override with DQCR_PORT=...)."
  else
    echo "Requested port $APP_PORT is busy. Stop the service on this port or set another port:"
    echo "DQCR_PORT=8080 ./bin/up.sh"
    exit 1
  fi
elif ! command -v lsof >/dev/null 2>&1; then
  echo "lsof is not installed, skipping preflight port check."
fi

echo "==> Starting containers from prebuilt images"
docker compose -f "$COMPOSE_FILE" up -d

echo "==> Waiting for readiness"
for attempt in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:$APP_PORT/ready" >/dev/null; then
    echo "Application is ready: http://127.0.0.1:$APP_PORT"
    exit 0
  fi
  sleep 2
done

echo "Application started, but readiness check did not pass in time."
echo "Run: ./bin/logs.sh"
exit 1
