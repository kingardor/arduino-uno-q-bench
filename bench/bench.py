import base64, json, sys, urllib.request
model, img, threads = sys.argv[1], sys.argv[2], int(sys.argv[3])
data = base64.b64encode(open(img, "rb").read()).decode()
req = {"model": model, "prompt": "Describe this image in one sentence.",
       "images": [data], "stream": False, "keep_alive": "30m",
       "options": {"num_predict": 40, "num_thread": threads}}
body = json.dumps(req).encode()
r = urllib.request.urlopen(urllib.request.Request(
    "http://127.0.0.1:11434/api/generate", body, {"Content-Type": "application/json"}))
d = json.loads(r.read())
ec = d.get("eval_count") or 0
ed = (d.get("eval_duration") or 1) / 1e9
pe = (d.get("prompt_eval_duration") or 0) / 1e9
tot = (d.get("total_duration") or 0) / 1e9
print(f"threads={threads}  prompt_eval_s={pe:.1f}  gen={ec}@{ec/ed:.1f}tok/s  total_s={tot:.1f}")
print("  caption:", d.get("response", "").strip()[:90])
