#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/backend/.env"
ENV_EXAMPLE="$ROOT_DIR/backend/.env.example"
COMPOSE_FILE="$ROOT_DIR/infra/docker/docker-compose.prod.yml"
APP_PORT="${DQCR_PORT:-80}"

if lsof -iTCP:"$APP_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  if [[ -z "${DQCR_PORT:-}" ]]; then
    APP_PORT=8080
    export DQCR_PORT="$APP_PORT"
    echo "Port 80 is busy. Falling back to port $APP_PORT (override with DQCR_PORT=...)."
  else
    echo "Requested port $APP_PORT is busy. Stop the service on this port or set another port:"
    echo "DQCR_PORT=8080 ./scripts/prod-up.sh"
    exit 1
  fi
fi

echo "==> Preparing backend environment"
if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  echo "Created $ENV_FILE from .env.example"
fi

if grep -q '^SECRET_KEY=dev-secret-key$' "$ENV_FILE"; then
  GENERATED_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  sed -i.bak "s|^SECRET_KEY=.*$|SECRET_KEY=$GENERATED_SECRET|" "$ENV_FILE"
  rm -f "$ENV_FILE.bak"
  echo "Replaced default SECRET_KEY with a generated secure value"
fi

echo "==> Building and starting production containers"
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
