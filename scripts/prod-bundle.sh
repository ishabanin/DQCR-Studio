#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT_DIR/scripts/prod-common.sh"

COMPOSE_FILE="$ROOT_DIR/infra/docker/docker-compose.prod.yml"
TEMPLATE_DIR="$ROOT_DIR/infra/bundle"
DIST_DIR="$ROOT_DIR/dist"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BUNDLE_NAME="${DQCR_BUNDLE_NAME:-dqcr-studio-bundle-$TIMESTAMP}"
BUNDLE_DIR="$DIST_DIR/$BUNDLE_NAME"
ARCHIVE_PATH="$DIST_DIR/$BUNDLE_NAME.tar.gz"
IMAGES_ARCHIVE="$BUNDLE_DIR/images/dqcr-studio-images.tar.gz"

echo "==> Preparing source environment"
prepare_backend_env

echo "==> Building production images"
docker compose -f "$COMPOSE_FILE" build

echo "==> Creating bundle directory"
rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR/images" "$BUNDLE_DIR/bin"

cp "$TEMPLATE_DIR/docker-compose.yml" "$BUNDLE_DIR/docker-compose.yml"
cp "$ROOT_DIR/backend/.env" "$BUNDLE_DIR/backend.env"
cp -R "$ROOT_DIR/projects" "$BUNDLE_DIR/projects"
cp -R "$ROOT_DIR/catalog" "$BUNDLE_DIR/catalog"
cp -R "$TEMPLATE_DIR/bin/." "$BUNDLE_DIR/bin"
cp "$TEMPLATE_DIR/README.md" "$BUNDLE_DIR/README.md"

chmod +x "$BUNDLE_DIR"/bin/*.sh

echo "==> Exporting Docker images"
docker save dqcr-studio-backend:prod dqcr-studio-frontend:prod | gzip > "$IMAGES_ARCHIVE"

cat > "$BUNDLE_DIR/VERSION.txt" <<EOF
Bundle: $BUNDLE_NAME
Created: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Images:
- dqcr-studio-backend:prod
- dqcr-studio-frontend:prod
EOF

if command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "$IMAGES_ARCHIVE" > "$BUNDLE_DIR/images/SHA256SUMS"
fi

echo "==> Packing bundle archive"
tar -C "$DIST_DIR" -czf "$ARCHIVE_PATH" "$BUNDLE_NAME"

echo
echo "Bundle ready:"
echo "Directory: $BUNDLE_DIR"
echo "Archive:   $ARCHIVE_PATH"
echo
echo "Next step on target machine:"
echo "1. Copy $ARCHIVE_PATH"
echo "2. Extract it"
echo "3. Run ./bin/install.sh inside the extracted bundle"
