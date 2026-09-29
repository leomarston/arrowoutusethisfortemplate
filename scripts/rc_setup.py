#!/usr/bin/env python3
"""RevenueCat kurulumu (API v2) — tek app için her şeyi kurar ve Config.swift'e yazar.

Kullanım (repo kökünden):  python3 scripts/rc_setup.py --slug <slug>

Yaptıkları:
  1. Projeye App Store app'i ekler (bundle_id ile)         POST /apps
  2. App'e özel public API key'i çeker (appl_...)           GET  /apps/{id}/public_api_keys
  3. Entitlement oluşturur:  <slug>_pro                     POST /entitlements
  4. pricing'teki planlara göre product oluşturur            POST /products
     (weekly_usd → <bundle>.weekly, monthly_usd → .monthly, yearly_usd → .yearly;
      pricing'te hiçbiri yoksa eski varsayılan: monthly + yearly)
  5. Product'ları entitlement'a bağlar                      POST /entitlements/{id}/actions/attach_products
  6. Offering oluşturur:     <slug>_default                 POST /offerings
  7. $rc_weekly / $rc_monthly / $rc_annual paketleri + bağları  POST /offerings/{id}/packages, /packages/{id}/actions/attach_products
  8. apps/<slug>/App/Config.swift içine key/id'leri yazar

Not: RC API v2 alan adları değişmiş olabilir. Hata alırsan yanıt gövdesi aynen
basılır — Claude Code hatayı okuyup bu scripti düzeltir, tekrar çalıştırır.
Idempotent: "zaten var" (409) yanıtlarında mevcut kaydı bulup devam eder.
"""
import argparse, json, os, re, ssl, sys, time
from pathlib import Path
from urllib import request, error

import certifi

# macOS'ta framework Python sistem sertifikalarini gormez; certifi sart.
_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://api.revenuecat.com/v2"

# Plan tanimlari: (product suffix, RC paket lookup_key, paket display name).
# Sira = paket pozisyonu (1'den baslar); yearly her zaman en ustte.
PLAN_DEFS = (
    ("yearly", "$rc_annual", "Annual"),
    ("monthly", "$rc_monthly", "Monthly"),
    ("weekly", "$rc_weekly", "Weekly"),
)


def plans_from_pricing(pricing):
    """pricing'te *_usd anahtari olan planlar; hicbiri yoksa eski monthly+yearly davranisi."""
    plans = [p for p in PLAN_DEFS if f"{p[0]}_usd" in pricing]
    return plans or [p for p in PLAN_DEFS if p[0] in ("yearly", "monthly")]


def env():
    e = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            # satir sonu yorumunu at — yalniz bosluk + '#' kirpilir, '#' iceren degerler korunur
            v = re.sub(r"\s+#.*$", "", v)
            e[k.strip()] = v.strip().strip('"').strip("'")
    return e


def call(method, path, key, body=None):
    # next_page yollari zaten /v2 ile baslar; BASE de iceriyor, cifti onle
    if path.startswith("/v2/"):
        path = path[len("/v2"):]
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    })
    try:
        with request.urlopen(req, context=_SSL_CTX) as r:
            return r.status, json.loads(r.read() or b"{}")
    except error.HTTPError as ex:
        payload = ex.read().decode()
        try:
            payload = json.loads(payload)
        except Exception:
            pass
        return ex.code, payload


def must(status, payload, what, ok=(200, 201)):
    if status in ok:
        return payload
    print(f"\n!! {what} basarisiz (HTTP {status}):\n{json.dumps(payload, indent=2, ensure_ascii=False) if isinstance(payload, dict) else payload}")
    sys.exit(1)


def find_in_list(key, path, pred):
    """Sayfalı listelerde pred'e uyan ilk item."""
    p = path
    while p:
        status, payload = call("GET", p, key)
        if status != 200:
            return None
        for it in payload.get("items", []):
            if pred(it):
                return it
        p = payload.get("next_page")
    return None


def create_or_get(key, list_path, create_path, body, what, match):
    status, payload = call("POST", create_path, key, body)
    if status in (200, 201):
        print(f"  + {what} olusturuldu")
        return payload
    if status in (409, 422):
        existing = find_in_list(key, list_path, match)
        if existing:
            print(f"  = {what} zaten var, kullaniliyor")
            return existing
    must(status, payload, what)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    args = ap.parse_args()
    slug = args.slug

    e = env()
    key = e["RC_SECRET_KEY"]
    pid = e["RC_PROJECT_ID"]
    P = f"/projects/{pid}"

    idea = json.loads(os.popen(f"python3 {ROOT}/scripts/idea.py json {slug}").read())
    name = idea["name"]
    bundle = f'{e["BUNDLE_PREFIX"]}.{slug}'
    plans = plans_from_pricing(idea.get("pricing") or {})
    sids = {suffix: f"{bundle}.{suffix}" for suffix, _, _ in plans}
    ent_key = f"{slug}_pro"
    off_key = f"{slug}_default"

    print(f"RevenueCat kurulumu: {name} ({bundle})")

    # 1. App
    app = create_or_get(
        key, f"{P}/apps", f"{P}/apps",
        {"name": name, "type": "app_store", "app_store": {"bundle_id": bundle}},
        "app", lambda it: it.get("app_store", {}).get("bundle_id") == bundle,
    )
    app_id = app["id"]

    # 1b. App Store Connect kimlik bilgileri (StoreKit 2). RevenueCat, In-App
    # Purchase Key olmadan satin almalari dogrulayamaz ve offering'ler bos doner
    # ("could not load plans"). ASC API key olmadan urun/abonelik metadata'sini
    # ceremez. Mevcut ASC API key'imiz (.env) her ikisini de karsilar; ayni .p8'i
    # hem subscription (IAP) hem asc_api_key alanlarina yaziyoruz.
    try:
        p8 = Path(ROOT, e["ASC_KEY_PATH"].replace("~", str(Path.home()))).read_text()
        cred = {"app_store": {
            "bundle_id": bundle,
            "subscription_private_key": p8,
            "subscription_key_id": e["ASC_KEY_ID"],
            "subscription_key_issuer": e["ASC_ISSUER_ID"],
            "app_store_connect_api_key": p8,
            "app_store_connect_api_key_id": e["ASC_KEY_ID"],
            "app_store_connect_api_key_issuer": e["ASC_ISSUER_ID"],
        }}
        cs, cp = call("POST", f"{P}/apps/{app_id}", key, cred)
        conf = cp.get("app_store", {}) if isinstance(cp, dict) else {}
        if cs == 200 and conf.get("subscription_key_configured"):
            print("  + ASC In-App Purchase Key + API key baglandi")
        else:
            print(f"  ! ASC key baglama beklenmedik yanit (HTTP {cs}): {conf or cp}")
    except Exception as ex:
        print(f"  ! ASC key baglanamadi (elle ayarla): {ex}")

    # 2. Public API key
    time.sleep(1)
    status, payload = call("GET", f"{P}/apps/{app_id}/public_api_keys", key)
    must(status, payload, "public key fetch", ok=(200,))
    items = payload.get("items", [])
    pub = None
    for it in items:
        pub = it.get("key") or it.get("public_api_key") or it.get("id")
        if pub and str(pub).startswith("appl_"):
            break
    if not pub:
        print(f"!! public key yanitindan appl_ key cikarilamadi, ham yanit:\n{json.dumps(payload, indent=2)}")
        sys.exit(1)

    # 3. Entitlement
    ent = create_or_get(
        key, f"{P}/entitlements", f"{P}/entitlements",
        {"lookup_key": ent_key, "display_name": f"{name} Pro"},
        "entitlement", lambda it: it.get("lookup_key") == ent_key,
    )

    # 4. Products (pricing'teki planlara gore)
    prods = {}
    for suffix, _, _ in plans:
        sid = sids[suffix]
        dn = f"{name} {suffix.capitalize()}"
        pr = create_or_get(
            key, f"{P}/products?app_id={app_id}", f"{P}/products",
            {"store_identifier": sid, "app_id": app_id, "type": "subscription", "display_name": dn},
            f"product {sid}", lambda it, s=sid: it.get("store_identifier") == s,
        )
        prods[sid] = pr["id"]

    # 5. Entitlement <- products
    status, payload = call("POST", f"{P}/entitlements/{ent['id']}/actions/attach_products", key,
                           {"product_ids": list(prods.values())})
    if status not in (200, 201, 409, 422):
        must(status, payload, "entitlement attach")
    print("  + entitlement <- products")

    # 6. Offering
    off = create_or_get(
        key, f"{P}/offerings", f"{P}/offerings",
        {"lookup_key": off_key, "display_name": f"{name} Default"},
        "offering", lambda it: it.get("lookup_key") == off_key,
    )

    # 7. Packages + product bağları (pozisyon = plan sirasi: yearly 1, sonra monthly/weekly)
    for pos, (suffix, pkg_key, dn) in enumerate(plans, start=1):
        sid = sids[suffix]
        pkg = create_or_get(
            key, f"{P}/offerings/{off['id']}/packages", f"{P}/offerings/{off['id']}/packages",
            {"lookup_key": pkg_key, "display_name": dn, "position": pos},
            f"package {pkg_key}", lambda it, k=pkg_key: it.get("lookup_key") == k,
        )
        status, payload = call("POST", f"{P}/packages/{pkg['id']}/actions/attach_products", key,
                               {"products": [{"product_id": prods[sid], "eligibility_criteria": "all"}]})
        if status not in (200, 201, 409, 422):
            must(status, payload, f"package attach {pkg_key}")
        print(f"  + package {pkg_key} <- {sid}")

    # 8. Config.swift
    cfg = ROOT / "apps" / slug / "App" / "Config.swift"
    src = cfg.read_text()
    src = re.sub(r'rcAPIKey = ".*?"', f'rcAPIKey = "{pub}"', src)
    src = re.sub(r'entitlementId = ".*?"', f'entitlementId = "{ent_key}"', src)
    src = re.sub(r'offeringId = ".*?"', f'offeringId = "{off_key}"', src)
    cfg.write_text(src)

    print(f"\nOK. Config.swift guncellendi ({pub[:12]}...).")
    print(f"ASC urunleri: {' / '.join(sids[s] for s, _, _ in plans)}  (asc_iap.py bunlari ayni ID'lerle acar)")


if __name__ == "__main__":
    main()
