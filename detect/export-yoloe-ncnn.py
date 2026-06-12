#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Export YOLOE-26n to NCNN, reparameterized to a fixed open-world class list.

Run on a dev machine:  pip install ultralytics  &&  python export-yoloe-ncnn.py
Produces  ncnn_416/{model.ncnn.param, model.ncnn.bin}  (~10.6 MB).

Models are NOT committed to git — regenerate with this script, then push the
ncnn_416/ folder to the board's app dir (the sidecar bind-mounts it). Edit
CLASSES to change what gets detected (open-vocabulary baked in at export).
"""
import os
import shutil
from ultralytics import YOLO

CLASSES = ["person", "car", "dog", "cat", "bottle", "cup", "cell phone", "laptop"]
IMGSZ = int(os.environ.get("IMGSZ", "416"))
OUT = os.environ.get("OUT", f"ncnn_{IMGSZ}")

m = YOLO("yoloe-26n-seg.pt")                 # auto-downloads from Ultralytics
m.set_classes(CLASSES, m.get_text_pe(CLASSES))   # reparameterize (drops text encoder)
out = m.export(format="ncnn", imgsz=IMGSZ)        # pnnx -> ncnn
shutil.rmtree(OUT, ignore_errors=True)
shutil.move(out, OUT)
print("NCNN model ->", OUT, ":", sorted(os.listdir(OUT)))
print("classes:", CLASSES)
print(f"\nPush to the board:\n  adb push {OUT} /home/arduino/ArduinoApps/uno-q-vlm-chat/")
