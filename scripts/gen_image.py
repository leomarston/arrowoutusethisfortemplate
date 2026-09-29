#!/usr/bin/env python3
"""Generate an image via the Gemini image API (Nano Banana Pro / Imagen).

Usage:
  python3 scripts/gen_image.py --prompt "..." --out path.png [--model gemini-3-pro-image]
                               [--ref ref1.png --ref ref2.png] [--size 1024]

Reads GEMINI_API_KEY from .env. Saves the first returned image as PNG.
Model default: gemini-3-pro-image (Nano Banana Pro) — best for icons/scenes.
"""
import argparse, base64, io, os, re, sys
from pathlib import Path

import requests, certifi

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://generativelanguage.googleapis.com/v1beta"


def env():
    e = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            v = re.sub(r"\s+#.*$", "", v)
            e[k.strip()] = v.strip().strip('"').strip("'")
    return e


def generate(prompt, out, model="gemini-3-pro-image", refs=None, size=None):
    key = env()["GEMINI_API_KEY"]
    parts = [{"text": prompt}]
    for rp in (refs or []):
        b = Path(rp).read_bytes()
        parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(b).decode()}})
    body = {"contents": [{"parts": parts}]}
    if size:
        body["generationConfig"] = {"imageConfig": {"aspectRatio": "1:1"}}
    r = requests.post(f"{BASE}/models/{model}:generateContent?key={key}",
                      json=body, timeout=180, verify=certifi.where())
    if r.status_code != 200:
        print(f"!! {r.status_code}: {r.text[:400]}", file=sys.stderr)
        sys.exit(1)
    data = r.json()
    for cand in data.get("candidates", []):
        for p in cand.get("content", {}).get("parts", []):
            inline = p.get("inlineData") or p.get("inline_data")
            if inline and inline.get("data"):
                raw = base64.b64decode(inline["data"])
                Path(out).parent.mkdir(parents=True, exist_ok=True)
                Path(out).write_bytes(raw)
                print(f"wrote {out} ({len(raw)} bytes)")
                return out
    print(f"!! no image in response: {str(data)[:400]}", file=sys.stderr)
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="gemini-3-pro-image")
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--size", type=int, default=None)
    a = ap.parse_args()
    generate(a.prompt, a.out, a.model, a.ref, a.size)


if __name__ == "__main__":
    main()
