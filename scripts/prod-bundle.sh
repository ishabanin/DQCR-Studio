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
TEMPLATE_DIR="$ROOT_DIR/infra/bundle"
DIST_DIR="$ROOT_DIR/dist"
TARGET_PLATFORM="${DQCR_TARGET_PLATFORM:-linux/amd64}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BUNDLE_NAME="${DQCR_BUNDLE_NAME:-dqcr-studio-bundle-$TIMESTAMP}"
BUNDLE_DIR="$DIST_DIR/$BUNDLE_NAME"
ARCHIVE_PATH="$DIST_DIR/$BUNDLE_NAME.tar.gz"
IMAGES_ARCHIVE="$BUNDLE_DIR/images/dqcr-studio-images.tar.gz"

export DQCR_TARGET_PLATFORM="$TARGET_PLATFORM"
export DOCKER_DEFAULT_PLATFORM="$TARGET_PLATFORM"

echo "==> Preparing source environment"
prepare_backend_env

echo "==> Building production images for platform: $TARGET_PLATFORM"
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
Platform: $TARGET_PLATFORM
Images:
- dqcr-studio-backend:prod
- dqcr-studio-frontend:prod
EOF

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
