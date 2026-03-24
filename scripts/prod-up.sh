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
source "$ROOT_DIR/scripts/prod-common.sh"

COMPOSE_FILE="$ROOT_DIR/infra/docker/docker-compose.prod.yml"
APP_PORT="${DQCR_PORT:-80}"
TARGET_PLATFORM="${DQCR_TARGET_PLATFORM:-linux/amd64}"

export DQCR_TARGET_PLATFORM="$TARGET_PLATFORM"
export DOCKER_DEFAULT_PLATFORM="$TARGET_PLATFORM"

if command -v lsof >/dev/null 2>&1 && lsof -iTCP:"$APP_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  if [[ -z "${DQCR_PORT:-}" ]]; then
    APP_PORT=8080
    export DQCR_PORT="$APP_PORT"
    echo "Port 80 is busy. Falling back to port $APP_PORT (override with DQCR_PORT=...)."
  else
    echo "Requested port $APP_PORT is busy. Stop the service on this port or set another port:"
    echo "DQCR_PORT=8080 ./scripts/prod-up.sh"
    exit 1
  fi
elif ! command -v lsof >/dev/null 2>&1; then
  echo "lsof is not installed, skipping preflight port check."
fi

prepare_backend_env

echo "==> Building and starting production containers ($TARGET_PLATFORM)"
docker compose -f "$COMPOSE_FILE" up -d --build

echo "==> Waiting for backend readiness"
for attempt in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:$APP_PORT/ready" >/dev/null; then
    echo "Application is ready: http://127.0.0.1:$APP_PORT"
    exit 0
  fi
  sleep 2
done

echo "Application started, but readiness check did not pass in time."
echo "Run: ./scripts/prod-logs.sh"
exit 1
