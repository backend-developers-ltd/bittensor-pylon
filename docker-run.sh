#!/bin/bash
set -euo pipefail

DOCKER_HOST_PORT=8000

PYLON_DOCKER_IMAGE_NAME=${PYLON_DOCKER_IMAGE_NAME:-bittensor_pylon:latest}
PYLON_DB_DIR=${PYLON_DB_DIR:-/tmp/pylon}

docker build -t "$PYLON_DOCKER_IMAGE_NAME" .

docker run --rm \
  --env-file .env \
  -v "$PYLON_DB_DIR:/app/db/" \
  -v "$HOME/.bittensor:/root/.bittensor" \
  -p "$DOCKER_HOST_PORT:8000" \
  "$PYLON_DOCKER_IMAGE_NAME" "$@"
