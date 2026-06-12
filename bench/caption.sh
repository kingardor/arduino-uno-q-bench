#!/usr/bin/env bash
# caption.sh — caption an image with qwen3.5:0.8b via the local ollama server.
# Usage: ./caption.sh <image.jpg> ["your prompt"]
# Example: ./caption.sh photo.jpg "What objects are on the table?"
set -euo pipefail

IMG="${1:?usage: caption.sh <image> [prompt]}"
PROMPT="${2:-Describe this image in one sentence.}"
MODEL="${OLLAMA_VLM:-qwen3.5:0.8b}"
HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"

[ -f "$IMG" ] || { echo "no such file: $IMG" >&2; exit 1; }

REQ="$(mktemp)"; trap 'rm -f "$REQ"' EXIT
python3 - "$IMG" "$PROMPT" "$MODEL" >"$REQ" <<'PY'
import sys, base64, json
img = base64.b64encode(open(sys.argv[1], "rb").read()).decode()
json.dump({
    "model": sys.argv[3],
    "prompt": sys.argv[2],
    "images": [img],
    "stream": False,
    "think": False,                 # skip Qwen3 "thinking" -> far fewer tokens
    "keep_alive": "30m",            # keep model resident between calls
    "options": {"num_predict": 120}
}, sys.stdout)
PY

curl -s "$HOST/api/generate" -d @"$REQ" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('response','').strip())"
