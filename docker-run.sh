#!/bin/bash
set -euo pipefail
IMAGE_NAME="bittensor_pylon"
PORT=8000

docker build -t "$IMAGE_NAME" .
# Ensure the local DB file exists for mounting
DB_FILE="bittensor_pylon.sqlite3"
if [ ! -f "$DB_FILE" ]; then
    echo "Creating local database file: $DB_FILE"
    touch "$DB_FILE"
fi

docker run --rm \
  --env-file .env \
  -v "$(pwd)/$DB_FILE:/app/$DB_FILE" \
  -p "$PORT:8000" \
  "$IMAGE_NAME"