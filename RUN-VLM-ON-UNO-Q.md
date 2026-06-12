# Running a VLM on the Arduino UNO Q — deployed & working

Local, offline image captioning on the UNO Q with **ollama + `qwen3.5:0.8b`** (a
multimodal 0.8B model). Set up and benchmarked on 2026-06-12. CPU inference.

---

## What's deployed

| Thing | Value |
|---|---|
| Board | `arduino@jamespocketq` @ **192.168.1.14** (your LAN) |
| Hardware | QRB2210, aarch64, **4× Cortex-A53**, **3.6 GB RAM**, Debian 13 (trixie), kernel 7.0 |
| Runtime | **ollama 0.30.7**, installed at `/home/arduino/ollama` (NOT root — root only had 2.6 GB free) |
| Model | **`qwen3.5:0.8b`** — 873M params, **Q8_0**, 1.0 GB, multimodal (text+image) |
| Model store | `/home/arduino/.ollama/models` (on the 17 GB `/home` partition) |
| Server | `http://127.0.0.1:11434`, started detached (survives SSH logout, **not** reboot yet) |
| SSH | passwordless via `~/.ssh/uno_q` (key installed in `authorized_keys`) |
| Helper | `/home/arduino/caption.sh` |

The whole stack lives on `/home/arduino` — root partition untouched.

---

## How to use it

### From the board (SSH in)
```bash
ssh -i ~/.ssh/uno_q arduino@192.168.1.14
cd /home/arduino
./caption.sh photo.jpg                       # default: one-sentence caption
./caption.sh photo.jpg "What objects do you see?"
OLLAMA_VLM=qwen3.5:0.8b ./caption.sh photo.jpg   # override model via env
```

### From the Mac (drive it remotely)
```bash
# caption a local Mac image by piping it through SSH:
ssh -i ~/.ssh/uno_q arduino@192.168.1.14 'cat > /tmp/x.jpg && ./caption.sh /tmp/x.jpg' < /Users/kn1ght/Pictures/photo.jpg
```

### Raw API (for your own apps, e.g. from the STM32-side app or Python)
```bash
curl http://127.0.0.1:11434/api/generate -d '{
  "model":"qwen3.5:0.8b",
  "prompt":"Describe this image in one sentence.",
  "images":["<base64-jpeg>"],
  "stream":false, "think":false,
  "options":{"num_predict":120}
}'
```

---

## Performance (measured, CPU-only)

Benchmarked on the COCO "two cats on a pink couch" image. The **image encoder
(vision ViT) dominates**, and it scales with input resolution:

| Image size | Image-encode | **Total** | Quality |
|---|---|---|---|
| 640×480 (full) | 71 s | 84 s | ✅ accurate |
| **512×384** ⭐ | 45 s | **60 s** | ✅ accurate — best balance |
| 320×240 | 19 s | 31 s | ❌ miscounted ("six cats") |

- **Generation** is cheap: ~5.5–5.9 tok/s, and captions are short.
- The big one-time wins, already applied in `caption.sh`:
  - **`think:false`** — Qwen3.5 otherwise "thinks" for ~400 tokens before
    answering (cut a cold run from 174 s → 84 s).
  - **`keep_alive`** — keeps the model resident so you don't pay the ~7–20 s
    reload each call. (RAM cost: ~1.1 GB resident; board has plenty.)
- **Tuning knob: input resolution.** Feed ~512 px images for the best
  speed/accuracy balance. Don't go below ~448 px or it starts miscounting.

> Note on acceleration: this runs on the **CPU**. The Adreno 702 GPU has a
> llama.cpp OpenCL path, but Qualcomm only tuned it for flagship Adreno (SD 8
> series) and it's often *slower* than CPU on this tier — so CPU is the right
> call here. The Hexagon DSP is "lightweight AI" only, not for VLMs.

---

## Feeding it camera frames
The board has no image tools (no Pillow/ffmpeg/ImageMagick), so **capture small
JPEGs directly** (which also makes inference faster — see the table):
```bash
# if a USB UVC camera is attached, e.g. with fswebcam (apt install fswebcam):
fswebcam -r 512x384 --no-banner /home/arduino/frame.jpg
./caption.sh /home/arduino/frame.jpg
```
The STM32 ("dual brain") side can trigger a capture and act on the caption via
the Arduino App Lab bridge.

---

## Operational notes
- **Restart the server** (after a reboot, until persistence is set up):
  ```bash
  OLLAMA_MODELS=/home/arduino/.ollama/models setsid nohup \
    /home/arduino/ollama/bin/ollama serve >/home/arduino/.ollama/serve.log 2>&1 </dev/null &
  ```
- **Logs:** `/home/arduino/.ollama/serve.log`
- **Not yet done (opt-in):** auto-start on boot (cron `@reboot`) and adding
  `ollama` to your PATH in `~/.bashrc`. Say the word and I'll add them.

## Speeding up inference — measured findings (2026-06-12)

The bottleneck is the **vision encoder (prompt_eval), a CPU matmul** — not text
generation. Empirically tested on SmolVLM2-256M @ 512px:

| Config | Image encode | Total | Verdict |
|---|---|---|---|
| baseline (flash off, 4 threads) | 18.7 s | 23.4 s | — |
| `OLLAMA_FLASH_ATTENTION=1` + `OLLAMA_KV_CACHE_TYPE=q8_0` | 18.7 s | 23.5 s | **no change** |
| 3 threads | 24.1 s | 27.8 s | worse |
| 2 threads | 35.2 s | 40.5 s | worse |

**What works:**
1. **Smaller model / encoder** — the #1 lever. SmolVLM2-256M was 3–4× faster than
   qwen3.5:0.8b. The encoder size dominates everything.
2. **4 threads** (the default = nproc) is optimal; don't reduce it.
3. **`performance` CPU governor** (pin 2.016 GHz) — small win, **needs sudo**:
   `echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor`

**What does NOT help (measured):** flash-attention and KV-cache quantization —
they optimize *text attention*, which is already trivial for captioning. (They'd
help long-context text chat.) Thread tuning — 4 is already best.

**The only path with real upside: GPU offload.** The board *does* expose the
Adreno 702 for compute — `clinfo` → `rusticl / FD702` (OpenCL) and `vulkaninfo`
→ `Turnip Adreno 702` (Vulkan). But our ollama binary is **CPU-only**, so using
the GPU requires building **llama.cpp from source** with `GGML_VULKAN=ON`
(turnip, more portable) or `GGML_OPENCL=ON` (rusticl, but llama.cpp's Adreno
kernels were tuned for Qualcomm's driver, not rusticl). Caveats: the 702 has no
matrix/coopmat units and turnip reports Vulkan 1.0 here, so the speedup is
unproven — it's a build-and-benchmark project, not a config flag.

CPU note: the Cortex-A53 lacks **dotprod/i8mm**, so llama.cpp's int8 matmul
fast-paths (Q4_0_4_8 etc.) that accelerate A55/A76 don't apply — capping
CPU-only gains.

## Alternative / "more optimized" path (not installed)
`yzma` (Go wrapper for llama.cpp, what Arduino/Edge Impulse demoed) is lighter
than ollama's 2.1 GB runtime and better for an embedded app. Worth a look if you
want a smaller footprint or to embed inference directly in a Go/Arduino app:
<https://github.com/hybridgroup/yzma> · Arduino's guide:
<https://projecthub.arduino.cc/marc-edgeimpulse/running-local-llms-and-vlms-on-the-arduino-uno-q-with-yzma-74e288>
