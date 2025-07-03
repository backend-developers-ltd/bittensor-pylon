#!/bin/bash
set -euo pipefail
DOCKER_HOST_PORT=8000
docker build -t "$PYLON_DOCKER_IMAGE_NAME" .

docker run --rm \
  --env-file .env \
  -v "$PYLON_DB_PATH:/app/$(basename "$PYLON_DB_PATH")" \
  -p "$DOCKER_HOST_PORT:8000" \
  $PYLON_DOCKER_IMAGE_NAME
