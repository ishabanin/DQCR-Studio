#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:${DQCR_PORT:-80}}"

echo "Checking $BASE_URL/health"
curl -fsS "$BASE_URL/health"
echo

echo "Checking $BASE_URL/ready"
curl -fsS "$BASE_URL/ready"
echo

echo "Checking $BASE_URL/api/v1/projects"
curl -fsS "$BASE_URL/api/v1/projects"
echo
