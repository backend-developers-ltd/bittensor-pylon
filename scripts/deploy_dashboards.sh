#!/usr/bin/env bash
set -euo pipefail

# Configuration
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OBSERVABILITY_DIR="${ROOT_DIR}/observability"
GRAFANA_DIR="${OBSERVABILITY_DIR}/grafana"
OUTPUT_DIR="${OUTPUT_DIR:-${ROOT_DIR}/build/dashboards}"

PROM_DS_UID="${PROM_DS_UID:-prom-local}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
GRAFANA_TOKEN="${GRAFANA_TOKEN:-}"

# Detect if we have native tools or need Docker
USE_DOCKER=false
if ! command -v jsonnet >/dev/null 2>&1 || ! command -v jb >/dev/null 2>&1; then
  USE_DOCKER=true
  JSONNET_IMAGE="${JSONNET_IMAGE:-pylon-jsonnet:latest}"
fi

echo "==> Deploying Pylon Grafana Dashboards"
echo "    Datasource UID: ${PROM_DS_UID}"
echo "    Grafana URL: ${GRAFANA_URL}"
echo "    Using: $([ "$USE_DOCKER" = true ] && echo "Docker (${JSONNET_IMAGE})" || echo "Native tools")"
echo ""

# Build Docker image if needed
if [ "$USE_DOCKER" = true ]; then
  if ! docker image inspect "${JSONNET_IMAGE}" >/dev/null 2>&1; then
    echo "==> Building ${JSONNET_IMAGE}..."
    docker build -t "${JSONNET_IMAGE}" "${OBSERVABILITY_DIR}"
    echo ""
  fi
fi

# Install dependencies
echo "==> Installing Grafonnet dependencies..."
if [ "$USE_DOCKER" = true ]; then
  docker run --rm -v "${ROOT_DIR}:/work" -w /work/observability "${JSONNET_IMAGE}" jb install
else
  (cd "${OBSERVABILITY_DIR}" && jb install)
fi
echo ""

# Compile dashboards
echo "==> Compiling dashboards..."
mkdir -p "${OUTPUT_DIR}"

shopt -s nullglob
dashboards=("${GRAFANA_DIR}"/pylon-dashboard-*.jsonnet)

if [[ ${#dashboards[@]} -eq 0 ]]; then
  echo "Error: No dashboard files found in ${GRAFANA_DIR}" >&2
  exit 1
fi

for dashboard in "${dashboards[@]}"; do
  dashboard_name=$(basename "$dashboard" .jsonnet)
  output_file="${OUTPUT_DIR}/${dashboard_name}.json"

  echo "    Compiling ${dashboard_name}..."

  if [ "$USE_DOCKER" = true ]; then
    rel_path=$(realpath --relative-to="${ROOT_DIR}" "${dashboard}")
    docker run --rm -v "${ROOT_DIR}:/work" -w /work "${JSONNET_IMAGE}" \
      jsonnet -J observability/vendor --ext-str PROM_DS_UID="${PROM_DS_UID}" "${rel_path}" > "${output_file}"
  else
    jsonnet -J "${OBSERVABILITY_DIR}/vendor" --ext-str PROM_DS_UID="${PROM_DS_UID}" "${dashboard}" > "${output_file}"
  fi
done

echo "    ✓ Compiled ${#dashboards[@]} dashboard(s) to ${OUTPUT_DIR}"
echo ""

# Deploy to Grafana
if [ -z "${GRAFANA_TOKEN}" ]; then
  echo "==> Skipping deployment (GRAFANA_TOKEN not set)"
  echo "    Compiled dashboards are available in: ${OUTPUT_DIR}"
  exit 0
fi

echo "==> Deploying dashboards to Grafana..."

PYTHON_BIN="${PYTHON_BIN:-python3}"
compiled_dashboards=("${OUTPUT_DIR}"/pylon-dashboard-*.json)

for dashboard_file in "${compiled_dashboards[@]}"; do
  dashboard_name=$(basename "$dashboard_file" .json)
  echo "    Deploying ${dashboard_name}..."

  payload=$("${PYTHON_BIN}" - <<PY
import json, sys
with open('${dashboard_file}', 'r') as f:
    dashboard = json.load(f)
payload = {'dashboard': dashboard, 'overwrite': True, 'folderId': 0}
print(json.dumps(payload))
PY
)

  response=$(curl -s -w "\n%{http_code}" -X POST "${GRAFANA_URL}/api/dashboards/db" \
    -H "Authorization: Bearer ${GRAFANA_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$payload")

  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | sed '$d')

  if [[ "$http_code" -ge 200 ]] && [[ "$http_code" -lt 300 ]]; then
    echo "    ✓ Successfully deployed ${dashboard_name}"
  else
    echo "    ✗ Failed to deploy ${dashboard_name} (HTTP ${http_code})" >&2
    echo "$body" >&2
    exit 1
  fi
done

echo ""
echo "==> All dashboards deployed successfully!"
