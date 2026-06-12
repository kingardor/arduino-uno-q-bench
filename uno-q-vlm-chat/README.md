# UNO Q VLM Chat

A funky, on-device conversational **vision** agent for the Arduino UNO Q. Runs as
a native Arduino App Lab app (containerized, port **7000**), talks to a local
ollama VLM, and mirrors its state on the physical **8×13 LED matrix** + RGB LED.

<p align="center">
  <img src="./docs/app-screenshot.png" alt="UNO Q VLM Chat — app UI with VLM responding to an image query" width="720">
</p>

<p align="center">
  <img src="./docs/hardware-photo.jpg" alt="Arduino UNO Q board held up showing the LED matrix lit" width="420">
  <br>
  <sub>The board running live — LED matrix active, connected over USB.</sub>
</p>

## Access
- Open **`http://<board-ip>:7000`** from any device on the same Wi-Fi.
  - Current board IP: `10.31.86.98` (DHCP — changes if the board roams networks;
    on a stable home Wi-Fi it stays put). Find it with:
    `arp -a | grep -i 14:b5:cd:e7:7c:69` from a machine on the same LAN.
- Type a message, attach an image (📎 / drag-drop / paste), pick a model, send.
- Images are auto-downscaled to ~512 px in the browser (the speed sweet spot).

## Two tabs
- **Chat** — talk + vision. Model: **qwen3.5:0.8b** (multimodal) via ollama.
  Attach an image (📎 / drag-drop / paste) and ask about it.
- **Detect** — open-world object detection with **YOLOE-26n** (NCNN FP16 @ 416 px,
  ~180 ms on the A53). Upload an image; boxes render on a canvas overlay. Served by
  the [`detect/`](../detect) sidecar container on `:7801`, reached via `HOST_IP`.

## State animations (browser + board)
| State | Browser hero canvas | 8×13 matrix | RGB LED |
|---|---|---|---|
| boot | dot-grid sweep → orb | random twinkle | teal fade |
| idle | breathing orb + particles | static glyph | green breathe |
| processing | scan + rotating arc | explosive centre-out pulse | blue pulse |
| detecting | radar sweep | rotating radar sweep | cyan pulse |
| done | green ripple + check | checkmark | green flash |

## Architecture
```
browser → http://board:7000 (WebUI brick)
  /config, /chat  →  python/main.py
       │  ollama_client → http://$HOST_IP:11434 (ollama on host, bound 0.0.0.0)
       │  animator → Bridge.call("draw", frame_bytes) → STM32 sketch → matrix
       └           → /dev/leds/builtin/led1_* (RGB LED)
```
- `python/main.py` — WebUI handlers (`/config`, `/chat`) + boot the animator.
- `python/ollama_client.py` — stdlib client; resolves host via `HOST_IP`.
- `python/animator.py` — background thread; state → matrix frames + RGB LED.
- `python/frames.py` — pure-Python 8×13 frame generators (0–7 grayscale).
- `assets/` — `index.html`, `app.js` (chat + Canvas animations), `style.css`.
- `sketch/` — reused from the `led-matrix-painter` example (`draw` RPC provider).

## Resilience (already configured on the board)
- **ollama** runs as a **systemd --user service** (`~/.config/systemd/user/ollama.service`,
  `Restart=always`, `OLLAMA_HOST=0.0.0.0`, `OLLAMA_MAX_LOADED_MODELS=1` to avoid
  OOM on 3.6 GB). **Linger is enabled**, so it survives logout *and* reboot.
- **App container** has `--restart unless-stopped` (auto-recovers + starts on boot).

## Managing it (on the board)
```bash
# app
arduino-app-cli app start   /home/arduino/ArduinoApps/uno-q-vlm-chat
arduino-app-cli app stop    /home/arduino/ArduinoApps/uno-q-vlm-chat
arduino-app-cli app logs    /home/arduino/ArduinoApps/uno-q-vlm-chat
# ollama
systemctl --user status  ollama
systemctl --user restart ollama
journalctl --user -u ollama -f
```

## Redeploy after local edits
```bash
# Via ADB (preferred — no SSH key needed, works over USB)
adb -s 4154450840 push assets/style.css  /home/arduino/ArduinoApps/uno-q-vlm-chat/assets/style.css
adb -s 4154450840 push assets/index.html /home/arduino/ArduinoApps/uno-q-vlm-chat/assets/index.html
adb -s 4154450840 push python/ollama_client.py /home/arduino/ArduinoApps/uno-q-vlm-chat/python/ollama_client.py

# Re-establish port forward (drops on container restart / reboot)
adb -s 4154450840 forward tcp:7700 tcp:7000

# Full app restart (recompiles + re-flashes sketch — needed when LED matrix stops responding)
adb -s 4154450840 shell "arduino-app-cli app restart user:uno-q-vlm-chat"
# After arduino-app-cli restart, restore the auto-restart policy:
adb -s 4154450840 shell "docker update --restart=unless-stopped uno-q-vlm-chat-main-1"
```

## Notes / known limitations
- The board roams DHCP IPs on mobile/hotspot networks; prefer a stable Wi-Fi for a
  fixed URL. (mDNS `jamespocketq.local` didn't resolve cross-subnet in testing.)
- Voice was deferred (text + image only). Adding browser voice later needs HTTPS
  (Web Speech API requires a secure context over a LAN IP).
- Conversation history is client-held; the server is stateless per request.
