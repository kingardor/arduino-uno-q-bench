#!/usr/bin/env bash
# Build + run the YOLOE-26n detection sidecar ON THE BOARD.
# (Docker's default bridge has internet for the build/pip even when the app's
#  compose network doesn't.) The ncnn model is bind-mounted from the app dir.
#
# Usage (on the board, or via `adb shell`):  bash run-sidecar.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MODEL_DIR="${MODEL_DIR:-/home/arduino/ArduinoApps/uno-q-vlm-chat/ncnn_416}"

[ -f "$MODEL_DIR/model.ncnn.param" ] || {
  echo "ncnn model not found at $MODEL_DIR"
  echo "Generate it with detect/export-yoloe-ncnn.py and push ncnn_416/ to the board."
  exit 1
}

docker build -t yoloe-detect "$HERE"
docker rm -f yoloe-detect 2>/dev/null || true
docker run -d --name yoloe-detect --restart unless-stopped -p 7801:7801 \
  -v "$MODEL_DIR":/models/ncnn_416 yoloe-detect

sleep 2
curl -s --max-time 5 http://127.0.0.1:7801/healthz && echo "  <- detect sidecar up on :7801"
