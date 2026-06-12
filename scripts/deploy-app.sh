#!/usr/bin/env bash
# Deploy the UNO Q VLM Chat app to the board over USB (ADB) and (re)start it.
#
# Run this ON YOUR COMPUTER with the UNO Q connected via USB-C.
# Requires: adb  (macOS: brew install android-platform-tools)
#
# The UNO Q exposes an ADB interface over USB — this is how Arduino App Lab
# talks to it. We use `adb push` to sync files and `adb shell` to drive
# arduino-app-cli. A local port-forward exposes the web UI at localhost:$PORT
# (default 7700 — port 7000 is taken by macOS AirPlay Receiver).
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
APP_LOCAL="$HERE/uno-q-vlm-chat"
APP_REMOTE="/home/arduino/ArduinoApps/uno-q-vlm-chat"
EXAMPLE="/var/lib/arduino-app-cli/examples/led-matrix-painter"
PORT="${PORT:-7700}"

command -v adb >/dev/null || { echo "adb not found — brew install android-platform-tools"; exit 1; }
adb get-state >/dev/null 2>&1 || { echo "No ADB device. Connect the UNO Q via USB-C."; exit 1; }

# First run: scaffold the App Lab app (clones structure + sketch + venv from the example)
if ! adb shell "[ -d $APP_REMOTE ] && echo yes" | grep -q yes; then
  echo "Creating app on board (from example $EXAMPLE)…"
  adb shell "arduino-app-cli app new uno-q-vlm-chat --from-app $EXAMPLE -i '🤖'"
fi

echo "Syncing app files…"
adb push "$APP_LOCAL/app.yaml"   "$APP_REMOTE/app.yaml"
adb push "$APP_LOCAL/python"     "$APP_REMOTE/"
adb push "$APP_LOCAL/assets"     "$APP_REMOTE/"
adb push "$APP_LOCAL/sketch"     "$APP_REMOTE/"

echo "Restarting app (builds/flashes the sketch + starts the container)…"
adb shell "arduino-app-cli app restart $APP_REMOTE"
adb shell "docker update --restart unless-stopped uno-q-vlm-chat-main-1 >/dev/null 2>&1 || true"

echo "Forwarding localhost:$PORT -> board:7000 over USB…"
adb forward --remove tcp:$PORT 2>/dev/null || true
adb forward tcp:$PORT tcp:7000

echo
echo "Done.  Open:  http://localhost:$PORT"
echo "(On the same Wi-Fi as the board you can also use http://<board-ip>:7000)"
