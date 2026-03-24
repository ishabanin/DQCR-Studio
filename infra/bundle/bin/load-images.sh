#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGES_ARCHIVE="$ROOT_DIR/images/dqcr-studio-images.tar.gz"

if [[ ! -f "$IMAGES_ARCHIVE" ]]; then
  echo "Images archive not found: $IMAGES_ARCHIVE"
  exit 1
fi

if [[ -f "$ROOT_DIR/images/SHA256SUMS" ]] && command -v shasum >/dev/null 2>&1; then
  echo "==> Verifying image archive checksum"
  (cd "$ROOT_DIR/images" && shasum -a 256 -c SHA256SUMS)
fi

echo "==> Loading Docker images"
gzip -dc "$IMAGES_ARCHIVE" | docker load
