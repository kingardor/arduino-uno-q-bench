# SPDX-License-Identifier: MPL-2.0
"""UNO Q VLM Chat — on-device conversational vision agent.

Serves a web UI (WebUI brick, port 7000) and proxies chat to the local ollama
server. Mirrors app state on the physical 8x13 LED matrix + RGB LED via the
animation engine.
"""
from arduino.app_bricks.web_ui import WebUI
from arduino.app_utils import App, Logger

import ollama_client
import detect_client
from animator import Animator

logger = Logger("uno-q-vlm-chat")
ui = WebUI()

MODELS = {
    "qwen": {"tag": "qwen3.5:0.8b", "label": "Qwen3.5 0.8B \U0001f4ad"},
}
DEFAULT_MODEL = "qwen"

anim = Animator(logger)  # starts in "boot", auto-settles to "idle"
logger.info("UNO Q VLM Chat starting; ollama base=%s" % ollama_client.base_url())


def get_config(payload=None):
    return {
        "models": [{"id": k, "label": v["label"]} for k, v in MODELS.items()],
        "default": DEFAULT_MODEL,
        "matrix": {"w": 13, "h": 8},
    }


def chat(payload: dict):
    model_id = payload.get("model", DEFAULT_MODEL)
    messages = payload.get("messages", [])
    model = MODELS.get(model_id, MODELS[DEFAULT_MODEL])
    if not messages:
        return {"ok": False, "error": "no messages"}

    anim.set_state("processing")
    logger.info(f"chat: model={model_id} turns={len(messages)}")
    try:
        result = ollama_client.chat(model["tag"], messages)
        anim.flash_done()
        logger.info(f"chat ok in {result.get('timing')}s")
        return {"ok": True, "reply": result["reply"], "timing": result.get("timing")}
    except Exception as e:
        anim.flash_error()
        logger.warning(f"chat failed: {e}")
        return {"ok": False, "error": str(e)}


def boot(payload=None):
    """Replay the matrix boot twinkle — the frontend calls this on every page load."""
    anim.set_state("boot")
    return {"ok": True}


def detect(payload: dict):
    """Run YOLOE-26n object detection on an uploaded image (via the NCNN sidecar)."""
    import base64
    img = payload.get("image", "")
    if isinstance(img, str) and img.startswith("data:") and "," in img:
        img = img.split(",", 1)[1]
    if not img:
        return {"ok": False, "error": "no image"}
    anim.set_state("detecting")
    try:
        res = detect_client.detect(base64.b64decode(img))
        anim.flash_done()
        return {"ok": True, "boxes": res.get("boxes", []), "n": res.get("n", 0), "ms": res.get("ms")}
    except Exception as e:
        anim.flash_error()
        logger.warning(f"detect failed: {e}")
        return {"ok": False, "error": str(e)}


ui.expose_api('GET', '/config', get_config)
ui.expose_api('POST', '/boot', boot)
ui.expose_api('POST', '/chat', chat)
ui.expose_api('POST', '/detect', detect)

App.run()
