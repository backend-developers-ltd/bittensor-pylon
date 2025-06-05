#!/bin/bash
set -euo pipefail
IMAGE_NAME="bittensor_pylon"
PORT=8000

docker build -t "$IMAGE_NAME" .
docker run --rm --env-file .env --name "$IMAGE_NAME" -p $PORT:8000 "$IMAGE_NAME"