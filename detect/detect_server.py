# SPDX-License-Identifier: MPL-2.0
"""YOLOE-26n object-detection sidecar (NCNN FP16, CPU).

Runs in a python:3.11-slim container (where ncnn pip-installs cleanly) and serves
an HTTP /detect endpoint. The App Lab app POSTs an image and gets back boxes.
NCNN exports the raw detection head, so we decode it here (anchor-free, no DFL).
"""
import io
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import ncnn
from PIL import Image

CLASSES = ["person", "car", "dog", "cat", "bottle", "cup", "cell phone", "laptop"]
SZ = 416
STRIDES = (8, 16, 32)
MODEL_DIR = "/models/ncnn_416"

net = ncnn.Net()
net.opt.num_threads = 4
net.opt.use_fp16_packed = True
net.opt.use_fp16_storage = True
net.opt.use_fp16_arithmetic = True
net.load_param(f"{MODEL_DIR}/model.ncnn.param")
net.load_model(f"{MODEL_DIR}/model.ncnn.bin")


def _letterbox(img):
    w, h = img.size
    r = min(SZ / w, SZ / h)
    nw, nh = round(w * r), round(h * r)
    canvas = Image.new("RGB", (SZ, SZ), (114, 114, 114))
    dx, dy = (SZ - nw) // 2, (SZ - nh) // 2
    canvas.paste(img.resize((nw, nh)), (dx, dy))
    return canvas, r, dx, dy


def _nms(boxes, scores, iou=0.45, topk=100):
    idx = scores.argsort()[::-1][:300]
    keep = []
    while len(idx) and len(keep) < topk:
        i = idx[0]; keep.append(i)
        if len(idx) == 1:
            break
        rest = idx[1:]
        xx1 = np.maximum(boxes[i, 0], boxes[rest, 0]); yy1 = np.maximum(boxes[i, 1], boxes[rest, 1])
        xx2 = np.minimum(boxes[i, 2], boxes[rest, 2]); yy2 = np.minimum(boxes[i, 3], boxes[rest, 3])
        w = np.clip(xx2 - xx1, 0, None); h = np.clip(yy2 - yy1, 0, None)
        inter = w * h
        ai = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
        ar = (boxes[rest, 2] - boxes[rest, 0]) * (boxes[rest, 3] - boxes[rest, 1])
        ov = inter / (ai + ar - inter + 1e-6)
        idx = rest[ov < iou]
    return keep


def detect(jpeg, conf_th=0.30, iou=0.45):
    img = Image.open(io.BytesIO(jpeg)).convert("RGB")
    W, H = img.size
    lb, r, dx, dy = _letterbox(img)
    mat = ncnn.Mat.from_pixels(np.asarray(lb, np.uint8).tobytes(),
                               ncnn.Mat.PixelType.PIXEL_RGB, SZ, SZ)
    mat.substract_mean_normalize([0., 0., 0.], [1 / 255.] * 3)
    t = time.perf_counter()
    ex = net.create_extractor(); ex.input("in0", mat)
    _, o0 = ex.extract("out0")
    ms = (time.perf_counter() - t) * 1000

    a = np.array(o0)                 # (44, 3549) for a single-channel mat
    if a.ndim == 3:
        a = a[0]
    pred = a.T                       # (3549, 44): [x1,y1,x2,y2 (416 px), 8 cls, 32 mask]
    nc = len(CLASSES)
    cls = 1.0 / (1.0 + np.exp(-pred[:, 4:4 + nc]))
    conf = cls.max(1); ci = cls.argmax(1)
    m = conf > conf_th
    if not m.any():
        return [], ms
    b = pred[m, :4].astype(np.float32)              # cx,cy,w,h in letterboxed 416 px
    cx, cy, ww, hh = b[:, 0], b[:, 1], b[:, 2], b[:, 3]
    x1 = (cx - ww / 2 - dx) / r; y1 = (cy - hh / 2 - dy) / r
    x2 = (cx + ww / 2 - dx) / r; y2 = (cy + hh / 2 - dy) / r
    xy = np.stack([x1, y1, x2, y2], 1)
    sc, cc = conf[m], ci[m]
    out = []
    for i in _nms(xy, sc, iou):
        x1, y1, x2, y2 = xy[i]
        out.append({
            "label": CLASSES[int(cc[i])], "conf": round(float(sc[i]), 2),
            "x1": round(float(np.clip(x1, 0, W)), 1), "y1": round(float(np.clip(y1, 0, H)), 1),
            "x2": round(float(np.clip(x2, 0, W)), 1), "y2": round(float(np.clip(y2, 0, H)), 1),
        })
    return out, ms


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/healthz":
            self._send(200, {"ok": True, "classes": CLASSES, "imgsz": SZ})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/detect":
            return self._send(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(n)
        try:
            boxes, ms = detect(data)
            self._send(200, {"ok": True, "boxes": boxes, "n": len(boxes), "ms": round(ms, 1)})
        except Exception as e:
            self._send(500, {"ok": False, "error": str(e)})


if __name__ == "__main__":
    print(f"yoloe-26n detect sidecar on :7801  classes={CLASSES}")
    ThreadingHTTPServer(("0.0.0.0", 7801), Handler).serve_forever()
