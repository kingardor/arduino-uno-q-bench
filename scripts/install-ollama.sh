#!/usr/bin/env bash
# Install the ollama runtime on the Arduino UNO Q (Debian, arm64) and run it as
# an auto-restarting systemd --user service.
#
# Run this ON THE BOARD:  bash install-ollama.sh
#
# Why /home and not the system installer: the root partition is tiny (~2.6 GB
# free) and the ollama arm64 bundle is ~3 GB extracted, so we install under
# $HOME (the 17 GB /home partition) — no sudo needed.
set -euo pipefail

OLLAMA_DIR="$HOME/ollama"
MODELS_DIR="$HOME/.ollama/models"
URL="https://ollama.com/download/ollama-linux-arm64.tar.zst"

command -v zstd >/dev/null || { echo "need zstd (apt-get install zstd)"; exit 1; }
mkdir -p "$OLLAMA_DIR" "$MODELS_DIR"

if [ ! -x "$OLLAMA_DIR/bin/ollama" ]; then
  echo "Downloading ollama (arm64, ~1.5 GB)…"
  curl -fL "$URL" -o /tmp/ollama.tar.zst
  echo "Extracting to $OLLAMA_DIR…"
  zstd -dc /tmp/ollama.tar.zst | tar -xf - -C "$OLLAMA_DIR"
  rm -f /tmp/ollama.tar.zst
fi
"$OLLAMA_DIR/bin/ollama" --version || true

# --- systemd --user service: survives logout + reboot, auto-restarts ---------
mkdir -p "$HOME/.local/bin" "$HOME/.config/systemd/user"

cat > "$HOME/.local/bin/ollama-serve.sh" <<'SH'
#!/bin/bash
export OLLAMA_HOST=0.0.0.0:11434          # reachable from the App Lab container
export OLLAMA_MODELS="$HOME/.ollama/models"
export OLLAMA_MAX_LOADED_MODELS=1         # avoid OOM on 3.6 GB RAM
export OLLAMA_KEEP_ALIVE=30m
exec "$HOME/ollama/bin/ollama" serve
SH
chmod +x "$HOME/.local/bin/ollama-serve.sh"

cat > "$HOME/.config/systemd/user/ollama.service" <<'UNIT'
[Unit]
Description=Ollama server for UNO Q VLM Chat
After=network-online.target

[Service]
ExecStart=%h/.local/bin/ollama-serve.sh
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
UNIT

loginctl enable-linger "$(whoami)" 2>/dev/null || echo "(could not enable linger; service may stop on logout)"
systemctl --user daemon-reload
systemctl --user enable --now ollama.service
sleep 3
if curl -s --max-time 5 http://127.0.0.1:11434/api/version >/dev/null; then
  echo "ollama is up: $(curl -s http://127.0.0.1:11434/api/version)"
  echo "Next: bash pull-models.sh"
else
  echo "ollama did not come up — check: systemctl --user status ollama"
  exit 1
fi
