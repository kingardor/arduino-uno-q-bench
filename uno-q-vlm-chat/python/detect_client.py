# SPDX-License-Identifier: MPL-2.0
"""Client for the YOLOE-26n detection sidecar (NCNN FP16) on :7801.

The app runs in a container, so the sidecar is reached via HOST_IP (same trick
as the ollama client). The working base URL is resolved once and cached.
"""
import os
import json
import urllib.request

_PORT = 7801
_resolved = None


def _candidates():
    cands = []
    if os.environ.get("HOST_IP"):
        cands.append(f"http://{os.environ['HOST_IP']}:{_PORT}")
    cands += [f"http://172.17.0.1:{_PORT}", f"http://host.docker.internal:{_PORT}",
              f"http://127.0.0.1:{_PORT}"]
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c); out.append(c)
    return out


def base_url():
    global _resolved
    if _resolved:
        return _resolved
    for c in _candidates():
        try:
            urllib.request.urlopen(c + "/healthz", timeout=2).read()
            _resolved = c
            return c
        except Exception:
            continue
    _resolved = _candidates()[0]
    return _resolved


def detect(jpeg_bytes, timeout=30):
    req = urllib.request.Request(base_url() + "/detect", jpeg_bytes,
                                 {"Content-Type": "application/octet-stream"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())
