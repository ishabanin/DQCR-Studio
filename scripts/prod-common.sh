#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/backend/.env"
ENV_EXAMPLE="$ROOT_DIR/backend/.env.example"

prepare_backend_env() {
  echo "==> Preparing backend environment"

  if [[ ! -f "$ENV_FILE" ]]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "Created $ENV_FILE from .env.example"
  fi

  if grep -q '^SECRET_KEY=dev-secret-key$' "$ENV_FILE"; then
    local generated_secret
    generated_secret="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
    sed -i.bak "s|^SECRET_KEY=.*$|SECRET_KEY=$generated_secret|" "$ENV_FILE"
    rm -f "$ENV_FILE.bak"
    echo "Replaced default SECRET_KEY with a generated secure value"
  fi
}
