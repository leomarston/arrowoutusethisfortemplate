#!/usr/bin/env python3
"""Abonelik review metadata'sini otomatik yukler: reviewNote + review screenshot.

ASC UI'daki "Review Information" bolumunun API karsiligi:
  - PATCH /v1/subscriptions/{id}  attributes.reviewNote
  - subscriptionAppStoreReviewScreenshots: reserve (POST) -> binary upload (PUT
    uploadOperations) -> commit (PATCH uploaded=true + md5)

Kullanim: python3 scripts/asc_review_assets.py --slug <slug> --image <png> [--note "..."]
Idempotent: mevcut screenshot varsa dokunmaz (--force ile degistir).
"""
import argparse, hashlib, json, os, re, ssl, sys, time
from pathlib import Path
from urllib.parse import quote

import certifi
import jwt
import requests

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://api.appstoreconnect.apple.com"

DEFAULT_NOTE = (
    "{name} Pro is a standard auto-renewable subscription unlocking premium features. "
    "Where to find it: launch the app, complete onboarding (or open Settings > Upgrade to Pro). "
    "The paywall lists the weekly plan (3-day free trial) and the yearly plan. "
    "Purchases are processed by StoreKit/RevenueCat; no account or login is required."
)


def env():
    e = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            v = re.sub(r"\s+#.*$", "", v)
            e[k.strip()] = v.strip().strip('"').strip("'")
    return e


def token(e):
    key = Path(ROOT, os.path.expanduser(e["ASC_KEY_PATH"])).read_text()
    now = int(time.time())
    return jwt.encode({"iss": e["ASC_ISSUER_ID"], "iat": now, "exp": now + 1200,
                       "aud": "appstoreconnect-v1"},
                      key, algorithm="ES256", headers={"kid": e["ASC_KEY_ID"]})


class API:
    def __init__(self, tok):
        self.h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}

    def req(self, method, path, body=None, params=None, ok=(200, 201, 204)):
        r = requests.request(method, BASE + path, headers=self.h, json=body, params=params)
        if r.status_code in ok:
            return r.json() if r.text else {}
        print(f"\n!! {method} {path} -> HTTP {r.status_code}\n{r.text[:500]}")
        sys.exit(1)


def ensure_review_note(api, sub, note):
    sid = sub["id"]
    current = sub["attributes"].get("reviewNote")
    if current:
        print(f"  = reviewNote zaten var ({sub['attributes']['productId']})")
        return
    api.req("PATCH", f"/v1/subscriptions/{sid}",
            {"data": {"type": "subscriptions", "id": sid,
                      "attributes": {"reviewNote": note}}})
    print(f"  + reviewNote yazildi ({sub['attributes']['productId']})")


def ensure_screenshot(api, sub, image: Path, force=False):
    sid = sub["id"]
    pid = sub["attributes"]["productId"]
    r = requests.get(BASE + f"/v1/subscriptions/{sid}/appStoreReviewScreenshot", headers=api.h)
    if r.status_code == 200 and (r.json().get("data") or None):
        if not force:
            print(f"  = review screenshot zaten var ({pid})")
            return
        api.req("DELETE", f"/v1/subscriptionAppStoreReviewScreenshots/{r.json()['data']['id']}")
        print("  ~ eski screenshot silindi")

    data = image.read_bytes()
    res = api.req("POST", "/v1/subscriptionAppStoreReviewScreenshots", {
        "data": {"type": "subscriptionAppStoreReviewScreenshots",
                 "attributes": {"fileName": image.name, "fileSize": len(data)},
                 "relationships": {"subscription": {"data": {"type": "subscriptions", "id": sid}}}}})
    shot = res["data"]
    for op in shot["attributes"]["uploadOperations"]:
        headers = {h["name"]: h["value"] for h in op.get("requestHeaders", [])}
        chunk = data[op["offset"]: op["offset"] + op["length"]]
        ur = requests.request(op["method"], op["url"], headers=headers, data=chunk)
        if ur.status_code not in (200, 201, 204):
            print(f"!! upload {ur.status_code}: {ur.text[:200]}")
            sys.exit(1)
    api.req("PATCH", f"/v1/subscriptionAppStoreReviewScreenshots/{shot['id']}", {
        "data": {"type": "subscriptionAppStoreReviewScreenshots", "id": shot["id"],
                 "attributes": {"uploaded": True,
                                "sourceFileChecksum": hashlib.md5(data).hexdigest()}}})
    print(f"  + review screenshot yuklendi ({pid}, {len(data)//1024} KB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--image", required=True)
    ap.add_argument("--note")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    e = env()
    idea = json.loads(os.popen(f"python3 {ROOT}/scripts/idea.py json {args.slug}").read())
    bundle = f'{e["BUNDLE_PREFIX"]}.{args.slug}'
    image = Path(args.image)
    if not image.exists():
        sys.exit(f"!! goruntu yok: {image}")
    note = args.note or DEFAULT_NOTE.format(name=idea["name"])

    api = API(token(e))
    apps = api.req("GET", "/v1/apps", params={"filter[bundleId]": bundle})["data"]
    if not apps:
        sys.exit(f"!! ASC'de app yok: {bundle}")
    groups = api.req("GET", f"/v1/apps/{apps[0]['id']}/subscriptionGroups")["data"]
    print(f"Review assets: {bundle}")
    for g in groups:
        subs = api.req("GET", f"/v1/subscriptionGroups/{g['id']}/subscriptions",
                       params={"fields[subscriptions]": "productId,state,reviewNote"})["data"]
        for sub in subs:
            ensure_review_note(api, sub, note)
            ensure_screenshot(api, sub, image, force=args.force)
    print("OK.")


if __name__ == "__main__":
    main()
