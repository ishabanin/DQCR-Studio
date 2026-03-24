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
