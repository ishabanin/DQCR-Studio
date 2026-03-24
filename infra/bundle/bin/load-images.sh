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
IMAGES_ARCHIVE="$ROOT_DIR/images/dqcr-studio-images.tar.gz"

if [[ ! -f "$IMAGES_ARCHIVE" ]]; then
  echo "Images archive not found: $IMAGES_ARCHIVE"
  exit 1
fi

echo "==> Loading Docker images"
gzip -dc "$IMAGES_ARCHIVE" | docker load
