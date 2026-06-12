# UNO Q — Claude Instructions

## Hardware

- **Board**: Arduino UNO Q (Qualcomm QRB2210, Debian 13)
- **ADB serial**: `4154450840` — always use `-s 4154450840` to target the board (a second device `58201FDCR003MF` is a phone)
- **App URL**: `http://localhost:7700` (ADB port forward `tcp:7700 → tcp:7000`)
- **App path on board**: `/home/arduino/ArduinoApps/uno-q-vlm-chat/`

## Deploying assets

```bash
# Re-establish port forward (drops on container restart / board reboot)
adb -s 4154450840 forward tcp:7700 tcp:7000

# Push a single file
adb -s 4154450840 push <local-path> /home/arduino/ArduinoApps/uno-q-vlm-chat/assets/<file>

# Verify the server is up
curl -s -o /dev/null -w "%{http_code}" http://localhost:7700/
```

## Service management (Docker Compose)

The compose file lives at `/home/arduino/ArduinoApps/uno-q-vlm-chat/docker-compose.yml` (also tracked locally at `uno-q-vlm-chat/docker-compose.yml`).

```bash
# Run these via: adb -s 4154450840 shell "cd /home/arduino/ArduinoApps/uno-q-vlm-chat && docker compose <cmd>"

docker compose up -d          # start all services
docker compose down           # stop all services
docker compose restart        # restart all services
docker compose logs -f        # tail all logs
docker compose logs -f main   # tail main app only
```

If the app isn't responding after a board reboot, the container likely needs starting:

```bash
adb -s 4154450840 shell "docker start uno-q-vlm-chat-main-1"
adb -s 4154450840 forward tcp:7700 tcp:7000
```

**Important**: `arduino-app-cli app restart` resets the container restart policy to `no`.
After any `arduino-app-cli` restart, fix it with:

```bash
adb -s 4154450840 shell "docker update --restart=unless-stopped uno-q-vlm-chat-main-1"
```

**Use `arduino-app-cli app restart user:uno-q-vlm-chat` when the LED matrix stops working** — it recompiles and re-flashes the STM32 sketch. For container-only restarts, use `docker start/stop`.

## Services

| Service | Container | Port | Notes |
|---|---|---|---|
| VLM chat app | `uno-q-vlm-chat-main-1` | `7000` (host) | Python, serves the web UI |
| Object detection | `yoloe-detect` | `7801` (host) | NCNN YOLOe, bridge network |

## Key files

| Local | On board | Notes |
|---|---|---|
| `uno-q-vlm-chat/assets/style.css` | `.../assets/style.css` | Full CSS — edit and push |
| `uno-q-vlm-chat/assets/index.html` | `.../assets/index.html` | HTML — edit and push |
| `uno-q-vlm-chat/assets/app.js` | `.../assets/app.js` | **Do not modify** — canvas animation + all JS logic |
| `uno-q-vlm-chat/python/ollama_client.py` | `.../python/ollama_client.py` | Ollama HTTP client |
| `uno-q-vlm-chat/docker-compose.yml` | `.../docker-compose.yml` | Service definitions |

## Ollama

- Runs on the host at `172.17.0.1:11434` (Docker bridge) — stable across WiFi changes
- `HOST_IP=192.168.1.29` in the original container was stale; compose file overrides it to `172.17.0.1`
- `ollama_client.py` probes bridge IPs first as a fallback safety net

## Design system

- **Palette**: OKLCH throughout; primary `oklch(0.62 0.265 290)` (violet), accent `oklch(0.67 0.305 330)` (magenta)
- **Canvas**: `#stage-wrap` is a fixed full-screen element behind `#app`; `#stage` carries a `hue-rotate(120deg) blur(52px)` filter — do not touch JS
- **Theming**: `[data-theme="light"/"dark"]` on `<html>`, persisted in `localStorage('uno-theme')`
- **`app.js` is untouchable** — all behaviour lives there; UI changes go to CSS and HTML only

## Model files (excluded from git)

`*.gguf`, `*.bin`, `*.safetensors`, `*.onnx`, `*.pt`, `*.ts`, `model.ncnn.*`, `ncnn_*/`
