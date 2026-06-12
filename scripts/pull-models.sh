#!/usr/bin/env bash
# Pull the VLM(s) from the ollama registry (the "right place").
# Models are NOT stored in git — this script fetches them on the board.
#
# Run this ON THE BOARD (after install-ollama.sh):  bash pull-models.sh
set -euo pipefail

OLLAMA="$HOME/ollama/bin/ollama"
export OLLAMA_MODELS="$HOME/.ollama/models"

# The app uses Qwen3.5 0.8B (multimodal: text + vision). Add more here if wanted.
MODELS=(
  "qwen3.5:0.8b"
)

[ -x "$OLLAMA" ] || { echo "ollama not installed — run install-ollama.sh first"; exit 1; }
curl -s --max-time 5 http://127.0.0.1:11434/api/version >/dev/null \
  || { echo "ollama server not running — run install-ollama.sh first"; exit 1; }

for m in "${MODELS[@]}"; do
  echo "==> pulling $m"
  "$OLLAMA" pull "$m"
done

echo "--- installed models ---"
"$OLLAMA" list
