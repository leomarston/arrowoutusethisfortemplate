#!/usr/bin/env python3
"""Upload App Store screenshots straight through the ASC API.

Why this exists: fastlane's `deliver` cannot do it here. On this machine (fastlane 2.236.1
on Ruby 4.0.5) every screenshot call dies with `SSL_read: unexpected eof while reading` out
of Faraday/OpenSSL — and `languages:` does not narrow the pass, so deliver enumerates all 50
locales and fails on each one. The same requests through this script return 200. Separately,
even when spaceship works, re-uploading 250 images outlives Apple's 20-minute JWT cap
([[asc-token-20min-cap]]), so anything that pushes a full set needs its own token refresh —
which this does, per locale.

Flow per image, straight from the ASC docs:
  reserve  POST /v1/appScreenshots            -> uploadOperations
  upload   PUT  each operation's url + chunk
  commit   PATCH uploaded=true + sourceFileChecksum (md5)

Usage:
  python3 scripts/asc_screenshots.py --slug camdetect --version 1.0.3
  python3 scripts/asc_screenshots.py --slug camdetect --version 1.0.3 --locales en-US,ja
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import jwt
import requests

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://api.appstoreconnect.apple.com"

# The screenshot display type each of our generated sizes belongs to.
DISPLAY_TYPE = {
    "iphone69": "APP_IPHONE_67",
    "ipad13": "APP_IPAD_PRO_3GEN_129",
}


def env():
    e = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            e[k.strip()] = re.sub(r"\s+#.*$", "", v).strip().strip('"').strip("'")
    return e


def make_token(e):
    """Fresh token. Called per locale, because Apple caps the JWT at 20 minutes and a full
    50-locale push takes longer than that."""
    p8 = Path(ROOT, os.path.expanduser(e["ASC_KEY_PATH"])).read_text()
    now = int(time.time())
    return jwt.encode({"iss": e["ASC_ISSUER_ID"], "iat": now, "exp": now + 1100,
                       "aud": "appstoreconnect-v1"},
                      p8, algorithm="ES256", headers={"kid": e["ASC_KEY_ID"]})


class API:
    def __init__(self, e):
        self.e = e
        self.refresh()

    def refresh(self):
        self.h = {"Authorization": f"Bearer {make_token(self.e)}",
                  "Content-Type": "application/json"}

    def req(self, method, path, body=None, ok=(200, 201, 204)):
        for attempt in range(5):
            try:
                r = requests.request(method, BASE + path, headers=self.h,
                                     data=json.dumps(body) if body else None, timeout=90)
            except (requests.ConnectionError, requests.Timeout) as err:
                # Apple drops connections mid-run on a long push. This is transport-level,
                # so there is no status code to branch on — retry the whole request.
                if attempt == 4:
                    raise SystemExit(f"!! {method} {path} -> {type(err).__name__}: {err}")
                time.sleep(4 * (attempt + 1))
                continue
            if r.status_code in ok:
                return r.json() if r.text.strip() else {}
            # 401 means the token aged out mid-run; 429/5xx are worth another go.
            if r.status_code == 401:
                self.refresh(); continue
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(3 * (attempt + 1)); continue
            raise SystemExit(f"!! {method} {path} -> {r.status_code}: {r.text[:400]}")
        raise SystemExit(f"!! {method} {path} kept failing")


def screenshot_set(api, loc_id, display_type):
    """The set for one display size, created if the version does not have one yet.

    A newly opened version record starts with NO screenshot sets at all — they are not
    inherited from the previous version — so this has to create rather than assume.
    """
    res = api.req("GET", f"/v1/appStoreVersionLocalizations/{loc_id}/appScreenshotSets")
    for s in res.get("data", []):
        if s["attributes"]["screenshotDisplayType"] == display_type:
            return s["id"]
    res = api.req("POST", "/v1/appScreenshotSets", {
        "data": {"type": "appScreenshotSets",
                 "attributes": {"screenshotDisplayType": display_type},
                 "relationships": {"appStoreVersionLocalization": {
                     "data": {"type": "appStoreVersionLocalizations", "id": loc_id}}}}})
    return res["data"]["id"]


def clear_set(api, set_id):
    """Delete what is already in the set.

    Without this a re-upload APPENDS, and the listing ends up with ten screenshots where
    five were intended — the trap recorded in [[deliver-force-appends-screenshots]].
    """
    res = api.req("GET", f"/v1/appScreenshotSets/{set_id}/appScreenshots?limit=50")
    for shot in res.get("data", []):
        api.req("DELETE", f"/v1/appScreenshots/{shot['id']}")
    return len(res.get("data", []))


def upload_one(api, set_id, image: Path):
    data = image.read_bytes()
    res = api.req("POST", "/v1/appScreenshots", {
        "data": {"type": "appScreenshots",
                 "attributes": {"fileName": image.name, "fileSize": len(data)},
                 "relationships": {"appScreenshotSet": {
                     "data": {"type": "appScreenshotSets", "id": set_id}}}}})
    shot = res["data"]
    for op in shot["attributes"]["uploadOperations"]:
        headers = {h["name"]: h["value"] for h in op.get("requestHeaders", [])}
        chunk = data[op["offset"]: op["offset"] + op["length"]]
        for attempt in range(5):
            try:
                ur = requests.request(op["method"], op["url"], headers=headers,
                                      data=chunk, timeout=180)
            except (requests.ConnectionError, requests.Timeout) as err:
                if attempt == 4:
                    raise SystemExit(f"!! chunk upload {type(err).__name__}: {err}")
                time.sleep(4 * (attempt + 1))
                continue
            if ur.status_code in (200, 201, 204):
                break
            if attempt == 4:
                raise SystemExit(f"!! chunk upload {ur.status_code}: {ur.text[:200]}")
            time.sleep(3 * (attempt + 1))
    api.req("PATCH", f"/v1/appScreenshots/{shot['id']}", {
        "data": {"type": "appScreenshots", "id": shot["id"],
                 "attributes": {"uploaded": True,
                                "sourceFileChecksum": hashlib.md5(data).hexdigest()}}})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--locales", help="comma separated; default every locale on disk")
    ap.add_argument("--only-incomplete", action="store_true",
                    help="skip locales that already have the right number of screenshots")
    args = ap.parse_args()

    e = env()
    api = API(e)
    app_dir = ROOT / "apps" / args.slug
    shots_root = app_dir / "fastlane" / "screenshots"
    bundle = re.search(r"PRODUCT_BUNDLE_IDENTIFIER:\s*(\S+)",
                       (app_dir / "project.yml").read_text()).group(1)

    apps = api.req("GET", f"/v1/apps?filter[bundleId]={bundle}&limit=1")
    app_id = apps["data"][0]["id"]
    vers = api.req("GET", f"/v1/apps/{app_id}/appStoreVersions"
                          f"?filter[platform]=IOS&filter[versionString]={args.version}&limit=1")
    if not vers.get("data"):
        raise SystemExit(f"!! no iOS version {args.version} for {bundle}")
    version_id = vers["data"][0]["id"]

    locs = api.req("GET", f"/v1/appStoreVersions/{version_id}"
                          f"/appStoreVersionLocalizations?limit=200")
    by_locale = {l["attributes"]["locale"]: l["id"] for l in locs["data"]}

    wanted = args.locales.split(",") if args.locales else sorted(
        p.name for p in shots_root.iterdir() if p.is_dir())

    total_ok = total_fail = 0
    for locale in wanted:
        loc_id = by_locale.get(locale)
        if not loc_id:
            print(f"  ~ {locale}: no localization on ASC, skipped")
            continue
        files = sorted((shots_root / locale).glob("*.png"))
        if not files:
            print(f"  ~ {locale}: no screenshots on disk, skipped")
            continue

        if args.only_incomplete:
            # Resume a part-finished push without re-uploading what already landed.
            have = 0
            for s in api.req("GET", f"/v1/appStoreVersionLocalizations/{loc_id}"
                                    f"/appScreenshotSets").get("data", []):
                have += len(api.req("GET", f"/v1/appScreenshotSets/{s['id']}"
                                           f"/appScreenshots?limit=50").get("data", []))
            if have == len(files):
                print(f"  = {locale}: already {have}, skipped")
                continue

        # One fresh token per locale keeps every set inside the 20-minute window.
        api.refresh()
        by_type = {}
        for f in files:
            suffix = f.stem.split("_")[-1]
            by_type.setdefault(DISPLAY_TYPE.get(suffix, "APP_IPHONE_67"), []).append(f)

        for display_type, images in by_type.items():
            try:
                set_id = screenshot_set(api, loc_id, display_type)
                removed = clear_set(api, set_id)
            except SystemExit as err:
                print(f"  !! {locale} {display_type}: {err}")
                total_fail += len(images)
                continue
            for img in images:
                try:
                    upload_one(api, set_id, img)
                    total_ok += 1
                except SystemExit as err:
                    print(f"  !! {locale}/{img.name}: {err}")
                    total_fail += 1
            print(f"  + {locale} {display_type}: {len(images)} uploaded"
                  f"{f' (replaced {removed})' if removed else ''}")

    print(f"\ndone: {total_ok} uploaded, {total_fail} failed")
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())
