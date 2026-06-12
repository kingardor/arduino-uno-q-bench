# SPDX-License-Identifier: MPL-2.0
"""Tiny stdlib client for the ollama server running on the board host.

The app runs in a container, so 127.0.0.1 is NOT the host. ollama is bound to
0.0.0.0:11434 on the host; we reach it via HOST_IP (injected into the app
container by App Lab) with sensible fallbacks. The working base URL is resolved
once and cached.
"""
import os
import json
import time
import urllib.request

_PORT = 11434
_resolved = None


def _candidates():
    cands = []
    host_ip = os.environ.get("HOST_IP")
    if host_ip:
        cands.append(f"http://{host_ip}:{_PORT}")
    cands += [
        "http://172.17.0.1:%d" % _PORT,        # default docker bridge -> host
        "http://host.docker.internal:%d" % _PORT,
        "http://127.0.0.1:%d" % _PORT,         # if ever run outside a container
    ]
    # de-dupe preserving order
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def base_url():
    global _resolved
    if _resolved:
        return _resolved
    for c in _candidates():
        try:
            urllib.request.urlopen(c + "/api/version", timeout=2).read()
            _resolved = c
            return c
        except Exception:
            continue
    _resolved = _candidates()[0]
    return _resolved


def _strip_data_url(img):
    if isinstance(img, str) and img.startswith("data:") and "," in img:
        return img.split(",", 1)[1]
    return img


def chat(model_tag, messages, num_predict=256, timeout=240):
    """Call ollama /api/chat with multi-turn messages + optional images.

    messages: [{role, content, image?(base64 or data-url)}]
    Returns {"reply": str, "timing": float_seconds}.
    """
    om = []
    for m in messages:
        msg = {"role": m.get("role", "user"), "content": m.get("content", "")}
        img = m.get("image")
        if img:
            msg["images"] = [_strip_data_url(img)]
        om.append(msg)

    body = json.dumps({
        "model": model_tag,
        "messages": om,
        "stream": False,
        "think": False,
        "keep_alive": "30m",
        "options": {"num_predict": num_predict},
    }).encode()

    url = base_url() + "/api/chat"
    req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())
    reply = (data.get("message") or {}).get("content", "").strip()
    return {"reply": reply, "timing": round(time.time() - t0, 1)}
