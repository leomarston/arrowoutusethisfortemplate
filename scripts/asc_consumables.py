#!/usr/bin/env python3
"""App Store Connect: consumable (and non-consumable) in-app purchases from a catalog JSON.

The subscription tooling (asc_iap.py) cannot create a single coin pack. This script is the
consumables counterpart, for coin games (first user: Arrow Out, apps/mazeout):

  python3 scripts/asc_consumables.py --bundle com.manycode.arrowout \\
      --catalog apps/mazeout/design/publish/iap.json \\
      [--rules apps/mazeout/App/Resources/Tuning/rules.json] \\
      [--storekit apps/mazeout/App/Resources/StoreKit/ArrowOut.storekit] \\
      [--screenshot shots/final/shop-review.png] [--dry-run] [--readback out.json]

Per product, idempotently (existing IAPs are looked up by productId first):
  1. POST /v2/inAppPurchases              name (reference), productId, type, reviewNote, familySharable=false
  2. localizations x N (default: the 13 factory store locales)
         POST /v1/inAppPurchaseLocalizations (relationship inAppPurchaseV2); if Apple refuses the
         unversioned route, POST /v2/inAppPurchaseLocalizations on the IAP's editable version.
  3. POST /v1/inAppPurchaseAvailabilities  every territory except --exclude-territories (default CHN:
         a game with IAP there needs a Game Registration Number we do not have)
  4. POST /v1/inAppPurchasePriceSchedules  base territory USA + ONE manual USA price (the catalog's usd).
         Nothing else is written: Apple fills every other storefront itself (automaticPrices). A manual
         price in any other territory would freeze that territory's automatic adjustment, so there is
         deliberately NO per-territory loop here (unlike subscriptions in asc_iap.py).
  5. --screenshot: the App Store review screenshot (reserve -> PUT upload operations -> commit md5),
         the same image for every product. Without it an IAP stays MISSING_METADATA.
  6. VERIFY BY READING (never by trusting the POSTs): state, localizations, USA manual price,
         automaticPrices total (meta.paging.total, >= 170), TUR automatic price == the catalog's "try"
         column when present (the golden test of "Apple localises the money").

--dry-run: GET requests only. Every non-GET call is refused inside the HTTP layer (it raises), and the
run ends with the per-method call count. Exit codes: 0 ok / 1 error or failed verification /
3 dry-run found a prerequisite a real run would stop on (e.g. no ASC app record yet).

Catalog JSON (one truth for ids + prices; texts are written by the store-text package):
  {
    "productPrefix": "com.manycode.arrowout.",        # optional when ids are full product ids
    "reviewNote": "How the reviewer finds the shop",  # default for every product (<= 4000)
    "excludeTerritories": ["CHN"],                    # optional (the CLI flag wins)
    "products": [
      {"id": "offer.special", "type": "CONSUMABLE", "usd": 0.99, "try": 49.99,
       "referenceName": "Special Offer",              # optional, default = en-US name (<= 64)
       "locales": {"en-US": {"name": "Special Offer", "description": "1,000 coins, ..."}, ...}}
    ]
  }
Locale keys may be ASC codes (en-US, de-DE, sl-SI) or app language codes (en, de, sl); they are
normalised to ASC codes. Name <= 35 and description <= 55 characters (INFERRED from ASC Help; a 409
on the first real run is printed verbatim). Brand stems of other games are refused in every text.

Requirements: pip install pyjwt cryptography requests (setup.sh installs them).
"""
import argparse
import hashlib
import json
import re
import sys
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asc_iap  # noqa: E402  (API with token refresh + 429/5xx/RemoteDisconnected retries)

ROOT = Path(__file__).resolve().parent.parent
BASE = asc_iap.BASE

# The factory's 13 store locales (memory localize-top-13-locales; store uses sl-SI).
FACTORY_LOCALES = ["en-US", "de-DE", "fr-FR", "es-ES", "it", "pt-BR", "tr", "ja", "ko",
                   "zh-Hans", "pl", "sk", "sl-SI"]
# App-language code -> ASC store locale (only where they differ).
LOCALE_ALIASES = {"en": "en-US", "de": "de-DE", "fr": "fr-FR", "es": "es-ES", "sl": "sl-SI",
                  "pt": "pt-BR", "zh": "zh-Hans", "en_US": "en-US", "pt_BR": "pt-BR"}
TYPES = ("CONSUMABLE", "NON_CONSUMABLE", "NON_RENEWING_SUBSCRIPTION")
NAME_MAX, DESC_MAX, REF_MAX, NOTE_MAX = 35, 55, 64, 4000   # name/desc limits INFERRED (ASC Help)
AUTO_PRICE_MIN = 170                                        # ~175 storefronts minus tolerance

# Other games' brands (and our own internal working names) never appear in store-visible text.
# Word boundaries keep real words in other languages legal (fr/es/it/pt "grand(e)").
BRAND_BAN = re.compile(r"maze\s*out|\bmaze\b|grand\s*games|arrow\s*jam|\bjam\b|tap\s*away|v552",
                       re.IGNORECASE)
# English-only honesty words: the social world is simulated on the device.
EN_BAN = re.compile(r"\bonline\b|multiplayer|\bfriends?\b|\bgrand\b", re.IGNORECASE)

IAP_VERSION_EDITABLE = ("PREPARE_FOR_SUBMISSION", "READY_FOR_REVIEW", "DEVELOPER_REJECTED", "REJECTED")
IAP_READY_OR_BEYOND = ("READY_TO_SUBMIT", "WAITING_FOR_REVIEW", "IN_REVIEW", "APPROVED",
                       "PENDING_BINARY_APPROVAL")


class DryRunWrite(RuntimeError):
    pass


# ----------------------------------------------------------------------------- catalog

def norm_locale(loc):
    return LOCALE_ALIASES.get(loc, loc)


def money(v):
    """'0.99' / 0.99 -> '0.99' (ASC customerPrice strings have exactly 2 decimals for USD/TRY)."""
    try:
        return f"{Decimal(str(v)).quantize(Decimal('0.01'))}"
    except (InvalidOperation, ValueError):
        raise SystemExit(f"!! not a price: {v!r}")


def load_catalog(path, required_locales, rules=None, storekit=None):
    """Load + self-check the catalog. Returns (products, meta). Exits on any violation."""
    raw = json.loads(Path(path).read_text())
    if isinstance(raw, list):
        raw = {"products": raw}
    prefix = raw.get("productPrefix", "")
    note_default = raw.get("reviewNote") or ""
    errs, products = [], []
    seen_ids, seen_refs = set(), set()
    for i, p in enumerate(raw.get("products") or []):
        short = p.get("id") or ""
        pid = p.get("productId") or (short if (not prefix or short.startswith(prefix)) else prefix + short)
        if prefix and pid.startswith(prefix):
            short = pid[len(prefix):]
        tag = pid or f"#{i}"
        if not re.fullmatch(r"[A-Za-z0-9._-]+", pid or ""):
            errs.append(f"{tag}: bad productId")
        if pid in seen_ids:
            errs.append(f"{tag}: duplicate productId")
        seen_ids.add(pid)
        typ = (p.get("type") or "CONSUMABLE").upper()
        if typ not in TYPES:
            errs.append(f"{tag}: type {typ} not in {TYPES}")
        if p.get("usd") is None:
            errs.append(f"{tag}: no usd price")
            usd = None
        else:
            usd = money(p["usd"])
        tr = money(p["try"]) if p.get("try") is not None else None
        locs = {}
        for loc, t in (p.get("locales") or {}).items():
            L = norm_locale(loc)
            if L in locs:
                errs.append(f"{tag}: locale {loc} given twice (after normalising to {L})")
            locs[L] = {"name": (t or {}).get("name", "").strip(),
                       "description": (t or {}).get("description", "").strip()}
        missing = [L for L in required_locales if L not in locs]
        extra = [L for L in locs if L not in required_locales]
        if missing:
            errs.append(f"{tag}: missing locales {missing}")
        if extra:
            errs.append(f"{tag}: locales not in the required set {extra} (pass --locales to widen it)")
        for L, t in locs.items():
            if not t["name"]:
                errs.append(f"{tag} [{L}]: empty name")
            if len(t["name"]) > NAME_MAX:
                errs.append(f"{tag} [{L}]: name {len(t['name'])} > {NAME_MAX}: {t['name']!r}")
            if not t["description"]:
                errs.append(f"{tag} [{L}]: empty description")
            if len(t["description"]) > DESC_MAX:
                errs.append(f"{tag} [{L}]: description {len(t['description'])} > {DESC_MAX}: "
                            f"{t['description']!r}")
        en = locs.get("en-US", {})
        ref = (p.get("referenceName") or en.get("name") or "").strip()
        if not ref or len(ref) > REF_MAX:
            errs.append(f"{tag}: reference name empty or > {REF_MAX}")
        if ref in seen_refs:
            errs.append(f"{tag}: reference name {ref!r} not unique")
        seen_refs.add(ref)
        note = (p.get("reviewNote") or note_default).strip()
        if len(note) > NOTE_MAX:
            errs.append(f"{tag}: review note > {NOTE_MAX}")
        texts = [("referenceName", ref), ("reviewNote", note)] + \
                [(f"{L}.{k}", v) for L, t in locs.items() for k, v in t.items()]
        for where, text in texts:
            if BRAND_BAN.search(text or ""):
                errs.append(f"{tag} {where}: banned brand stem {BRAND_BAN.search(text).group(0)!r}")
        for where, text in [("referenceName", ref), ("reviewNote", note)] + \
                [(f"en-US.{k}", v) for k, v in en.items()]:
            if EN_BAN.search(text or ""):
                errs.append(f"{tag} {where}: banned English word {EN_BAN.search(text).group(0)!r}")
        products.append({"productId": pid, "short": short, "type": typ, "usd": usd, "try": tr,
                         "referenceName": ref, "reviewNote": note, "locales": locs})
    if not products:
        errs.append("catalog has no products")

    # Cross-checks: three copies (catalog, rules.json:shop, the .storekit file), one truth.
    if rules:
        shop = (json.loads(Path(rules).read_text()).get("shop") or {})
        rprefix = shop.get("productPrefix") or prefix
        want = {(rprefix + r["id"]): (money(r["usd"]) if r.get("usd") is not None else None,
                                      money(r["try"]) if r.get("try") is not None else None)
                for r in shop.get("products") or []}
        have = {p["productId"]: (p["usd"], p["try"]) for p in products}
        if set(want) != set(have):
            errs.append(f"rules.json ids differ: only in rules {sorted(set(want) - set(have))}, "
                        f"only in catalog {sorted(set(have) - set(want))}")
        for k in set(want) & set(have):
            if want[k][0] != have[k][0]:
                errs.append(f"{k}: usd catalog {have[k][0]} != rules.json {want[k][0]}")
            if have[k][1] is not None and want[k][1] is not None and want[k][1] != have[k][1]:
                errs.append(f"{k}: try catalog {have[k][1]} != rules.json {want[k][1]}")
    if storekit:
        sk = json.loads(Path(storekit).read_text())
        want = {x["productID"]: (money(x.get("displayPrice")), (x.get("type") or "").upper())
                for x in sk.get("products") or []}
        have = {p["productId"]: (p["usd"], p["type"]) for p in products}
        if set(want) != set(have):
            errs.append(f".storekit ids differ: only in storekit {sorted(set(want) - set(have))}, "
                        f"only in catalog {sorted(set(have) - set(want))}")
        for k in set(want) & set(have):
            if want[k][0] != have[k][0]:
                errs.append(f"{k}: usd catalog {have[k][0]} != .storekit {want[k][0]}")
            if want[k][1] and want[k][1] != have[k][1]:
                errs.append(f"{k}: type catalog {have[k][1]} != .storekit {want[k][1]}")
    if errs:
        print("!! catalog self-check FAILED:")
        for x in errs:
            print("   -", x)
        sys.exit(1)
    meta = {"excludeTerritories": raw.get("excludeTerritories")}
    print(f"catalog ok: {len(products)} products x {len(required_locales)} locales"
          + (" (+ rules.json)" if rules else "") + (" (+ .storekit)" if storekit else ""))
    return products, meta


# ----------------------------------------------------------------------------- HTTP (guarded)

class Http:
    """asc_iap.API underneath (token refresh, retries); every write goes through write(), which a
    dry-run refuses. Counts calls per method so a dry-run can prove it only read."""

    def __init__(self, e, dry_run):
        self.api = asc_iap.API(e)
        self.dry = dry_run
        self.count = {}

    def _url(self, path):
        return path if path.startswith("http") else BASE + path

    def get(self, path, params=None):
        self.count["GET"] = self.count.get("GET", 0) + 1
        r = self.api._send("GET", self._url(path), params=params)
        try:
            body = r.json() if r.text else {}
        except ValueError:
            body = {"raw": r.text[:300]}
        return r.status_code, body

    def must_get(self, path, params=None, ok=(200,)):
        st, body = self.get(path, params)
        if st not in ok:
            print(f"\n!! GET {path} -> HTTP {st}\n{json.dumps(body)[:1200]}")
            sys.exit(1)
        return body

    def get_all(self, path, params=None):
        params = dict(params or {})
        params.setdefault("limit", 200)
        out, url, first = [], path, True
        while url:
            st, j = self.get(url, params if first else None)
            first = False
            if st != 200:
                print(f"\n!! GET {url} -> HTTP {st}\n{json.dumps(j)[:1200]}")
                sys.exit(1)
            out += j.get("data") or []
            url = (j.get("links") or {}).get("next")
        return out

    def total(self, path, params=None):
        """meta.paging.total — never a capped page length (memory trial-claim-vs-config-drift)."""
        params = dict(params or {}, limit=1)
        st, j = self.get(path, params)
        if st != 200:
            return None
        return ((j.get("meta") or {}).get("paging") or {}).get("total", len(j.get("data") or []))

    def write(self, method, path, body=None, ok=(200, 201, 204)):
        if self.dry:
            raise DryRunWrite(f"dry-run refused {method} {path}")
        self.count[method] = self.count.get(method, 0) + 1
        r = self.api._send(method, self._url(path), json=body)
        try:
            j = r.json() if r.text else {}
        except ValueError:
            j = {"raw": r.text[:300]}
        return r.status_code, j

    def must_write(self, method, path, body=None, ok=(200, 201, 204)):
        st, j = self.write(method, path, body)
        if st not in ok:
            print(f"\n!! {method} {path} -> HTTP {st}\n{json.dumps(j, indent=1)[:2000]}")
            sys.exit(1)
        return j

    def upload(self, op, chunk):
        """PUT one upload operation (Apple's asset host, no ASC auth)."""
        if self.dry:
            raise DryRunWrite("dry-run refused an asset upload")
        import requests
        self.count["UPLOAD"] = self.count.get("UPLOAD", 0) + 1
        headers = {h["name"]: h["value"] for h in op.get("requestHeaders", [])}
        return requests.request(op["method"], op["url"], headers=headers, data=chunk, timeout=120)


def rel(t, i):
    return {"data": {"type": t, "id": i}}


# ----------------------------------------------------------------------------- per-product steps

def find_app(http, bundle):
    apps = http.must_get("/v1/apps", {"filter[bundleId]": bundle,
                                      "fields[apps]": "bundleId,name"}).get("data") or []
    apps = [a for a in apps if a["attributes"].get("bundleId") == bundle]
    return apps[0] if apps else None


def existing_iaps(http, app_id):
    rows = http.get_all(f"/v1/apps/{app_id}/inAppPurchasesV2",
                        {"fields[inAppPurchases]": "name,productId,inAppPurchaseType,state,"
                                                   "reviewNote,familySharable"})
    return {r["attributes"]["productId"]: r for r in rows}


def editable_version(http, iap_id):
    st, j = http.get(f"/v2/inAppPurchases/{iap_id}/versions", {"limit": 20})
    if st != 200:
        return None, []
    vs = j.get("data") or []
    for v in vs:
        if v["attributes"].get("state") in IAP_VERSION_EDITABLE:
            return v["id"], vs
    return None, vs


def ensure_iap(http, app_id, p, have):
    cur = have.get(p["productId"])
    want = {"name": p["referenceName"], "reviewNote": p["reviewNote"] or None}
    if cur is None:
        print(f"  + IAP {p['productId']} ({p['type']})" + ("  [dry-run: would create]" if http.dry else ""))
        if http.dry:
            return None
        j = http.must_write("POST", "/v2/inAppPurchases", {"data": {
            "type": "inAppPurchases",
            "attributes": {"name": want["name"], "productId": p["productId"],
                           "inAppPurchaseType": p["type"], "reviewNote": want["reviewNote"],
                           "familySharable": False},
            "relationships": {"app": rel("apps", app_id)}}})
        return j["data"]
    a = cur["attributes"]
    if a.get("inAppPurchaseType") != p["type"]:
        sys.exit(f"!! {p['productId']} exists as {a.get('inAppPurchaseType')}, catalog says {p['type']}. "
                 "An IAP's type can never change; fix the catalog or pick a new productId.")
    diff = {k: v for k, v in want.items() if (a.get(k) or None) != v}
    if diff:
        print(f"  ~ IAP {p['productId']}: {sorted(diff)} differ" + ("  [dry-run: would PATCH]" if http.dry else ""))
        if not http.dry:
            http.must_write("PATCH", f"/v2/inAppPurchases/{cur['id']}", {"data": {
                "type": "inAppPurchases", "id": cur["id"], "attributes": diff}})
    else:
        print(f"  = IAP {p['productId']} ({a.get('state')})")
    return cur


def read_localizations(http, iap_id):
    """{locale: (id, name, description, route)} from both the unversioned and versioned routes."""
    out = {}
    for L in http.get_all(f"/v2/inAppPurchases/{iap_id}/inAppPurchaseLocalizations"):
        a = L["attributes"]
        out[a["locale"]] = (L["id"], a.get("name"), a.get("description"), "v1")
    vid, _ = editable_version(http, iap_id)
    if vid:
        st, j = http.get(f"/v1/inAppPurchaseVersions/{vid}/localizations", {"limit": 200})
        for L in (j.get("data") or []) if st == 200 else []:
            a = L["attributes"]
            out.setdefault(a["locale"], (L["id"], a.get("name"), a.get("description"), "v2"))
    return out


class LocRoute:
    route = None      # "v1" or "v2", decided by the first POST Apple accepts


def ensure_localizations(http, iap_id, p):
    have = read_localizations(http, iap_id) if iap_id else {}
    todo_new = [L for L in p["locales"] if L not in have]
    todo_fix = [L for L in p["locales"] if L in have and
                (have[L][1] or "", have[L][2] or "") != (p["locales"][L]["name"], p["locales"][L]["description"])]
    stray = sorted(set(have) - set(p["locales"]))
    if stray:
        print(f"    ! localizations not in the catalog (left untouched): {stray}")
    if http.dry:
        if todo_new or todo_fix:
            print(f"    [dry-run] would add {len(todo_new)} and update {len(todo_fix)} localizations")
        else:
            print(f"    = {len(have)} localizations match")
        return
    for L in todo_new:
        t = p["locales"][L]
        attrs = {"name": t["name"], "locale": L, "description": t["description"]}
        v1_err = None
        if LocRoute.route in (None, "v1"):
            st, j = http.write("POST", "/v1/inAppPurchaseLocalizations", {"data": {
                "type": "inAppPurchaseLocalizations", "attributes": attrs,
                "relationships": {"inAppPurchaseV2": rel("inAppPurchases", iap_id)}}})
            if st in (200, 201):
                LocRoute.route = "v1"
                continue
            if LocRoute.route == "v1":          # the route worked before: this is a real error
                print(f"\n!! POST /v1/inAppPurchaseLocalizations {L} -> HTTP {st}\n{json.dumps(j, indent=1)[:1500]}")
                sys.exit(1)
            v1_err = (st, j)
            print(f"    ~ unversioned localization route refused (HTTP {st}); trying the versioned route")
        vid, vs = editable_version(http, iap_id)
        if not vid:
            print(f"\n!! no editable IAP version for {p['productId']} (versions: "
                  f"{[v['attributes'].get('state') for v in vs]}); cannot write {L}")
            if v1_err:
                print(f"   (v1 route answered HTTP {v1_err[0]}: {json.dumps(v1_err[1])[:800]})")
            sys.exit(1)
        st, j = http.write("POST", "/v2/inAppPurchaseLocalizations", {"data": {
            "type": "inAppPurchaseLocalizations", "attributes": attrs,
            "relationships": {"version": rel("inAppPurchaseVersions", vid)}}})
        if st not in (200, 201):
            # Both routes refused: most likely the text itself (length/characters). Show both answers.
            print(f"\n!! localization {L} refused by both routes.")
            if v1_err:
                print(f"   v1 HTTP {v1_err[0]}: {json.dumps(v1_err[1], indent=1)[:1200]}")
            print(f"   v2 HTTP {st}: {json.dumps(j, indent=1)[:1200]}")
            sys.exit(1)
        LocRoute.route = "v2"
    for L in todo_fix:
        lid, _, _, route = have[L]
        t = p["locales"][L]
        http.must_write("PATCH", f"/{route}/inAppPurchaseLocalizations/{lid}", {"data": {
            "type": "inAppPurchaseLocalizations", "id": lid,
            "attributes": {"name": t["name"], "description": t["description"]}}})
    if todo_new or todo_fix:
        print(f"    + localizations: {len(todo_new)} added, {len(todo_fix)} updated")
    else:
        print(f"    = {len(have)} localizations match")


def read_availability(http, iap_id):
    st, j = http.get(f"/v2/inAppPurchases/{iap_id}/inAppPurchaseAvailability")
    d = (j.get("data") or None) if st == 200 else None
    if not d:
        return None, None
    terrs = {t["id"] for t in http.get_all(f"/v1/inAppPurchaseAvailabilities/{d['id']}/availableTerritories")}
    return d, terrs


def ensure_availability(http, iap_id, p, wanted):
    d, terrs = read_availability(http, iap_id) if iap_id else (None, None)
    if d is not None and terrs == set(wanted) and d["attributes"].get("availableInNewTerritories"):
        print(f"    = availability: {len(terrs)} territories")
        return
    what = "create" if d is None else f"replace ({len(terrs)} -> {len(wanted)} territories)"
    if http.dry:
        print(f"    [dry-run] would {what} availability: {len(wanted)} territories")
        return
    http.must_write("POST", "/v1/inAppPurchaseAvailabilities", {"data": {
        "type": "inAppPurchaseAvailabilities",
        "attributes": {"availableInNewTerritories": True},
        "relationships": {"inAppPurchase": rel("inAppPurchases", iap_id),
                          "availableTerritories": {"data": [{"type": "territories", "id": t}
                                                            for t in wanted]}}}})
    print(f"    + availability {what}: {len(wanted)} territories")


def read_schedule(http, iap_id):
    """-> (schedule_id, base_territory, {territory: customerPrice} of manual prices) or (None, ...)."""
    st, j = http.get(f"/v2/inAppPurchases/{iap_id}/iapPriceSchedule")
    d = (j.get("data") or None) if st == 200 else None
    if not d:
        return None, None, {}
    sid = d["id"]
    st, b = http.get(f"/v1/inAppPurchasePriceSchedules/{sid}/baseTerritory")
    base = ((b.get("data") or {}).get("id")) if st == 200 else None
    manual = {}
    st, m = http.get(f"/v1/inAppPurchasePriceSchedules/{sid}/manualPrices",
                     {"include": "inAppPurchasePricePoint,territory", "limit": 200})
    if st == 200:
        pts = {x["id"]: x["attributes"].get("customerPrice")
               for x in m.get("included") or [] if x["type"] == "inAppPurchasePricePoints"}
        today = time.strftime("%Y-%m-%d")
        for pr in m.get("data") or []:
            a, r = pr["attributes"], pr.get("relationships") or {}
            if a.get("endDate") and a["endDate"] <= today:
                continue
            if a.get("startDate") and a["startDate"] > today:
                continue
            terr = ((r.get("territory") or {}).get("data") or {}).get("id")
            ppid = ((r.get("inAppPurchasePricePoint") or {}).get("data") or {}).get("id")
            manual[terr] = pts.get(ppid)
    return sid, base, manual


def ensure_price(http, iap_id, p, reprice):
    sid, base, manual = read_schedule(http, iap_id) if iap_id else (None, None, {})
    if sid and base == "USA" and manual.get("USA") == p["usd"] and set(manual) == {"USA"}:
        print(f"    = price: USA ${p['usd']} (base USA, automatic elsewhere)")
        return
    if sid and not reprice:
        print(f"\n!! {p['productId']}: a price schedule exists (base {base}, manual {manual}) that is not "
              f"'USA ${p['usd']} only'. Re-run with --reprice to replace it.")
        sys.exit(1)
    if not iap_id:
        print(f"    [dry-run] would set price: USA ${p['usd']} (base USA; automatic prices elsewhere)")
        return
    pts = http.get_all(f"/v2/inAppPurchases/{iap_id}/pricePoints",
                       {"filter[territory]": "USA", "fields[inAppPurchasePricePoints]": "customerPrice",
                        "limit": 8000})
    point = next((x for x in pts if x["attributes"].get("customerPrice") == p["usd"]), None)
    if not point:
        near = sorted({x["attributes"]["customerPrice"] for x in pts}, key=lambda s: Decimal(s))
        print(f"\n!! no USA price point ${p['usd']} for {p['productId']}. Nearby: "
              f"{[s for s in near if abs(Decimal(s) - Decimal(p['usd'])) < 3][:12]}")
        sys.exit(1)
    if http.dry:
        print(f"    [dry-run] would {'replace' if sid else 'set'} price: USA ${p['usd']} "
              f"(price point found; automatic prices elsewhere)")
        return
    for attempt in range(4):
        st, j = http.write("POST", "/v1/inAppPurchasePriceSchedules", {
            "data": {"type": "inAppPurchasePriceSchedules",
                     "relationships": {"inAppPurchase": rel("inAppPurchases", iap_id),
                                       "baseTerritory": rel("territories", "USA"),
                                       "manualPrices": {"data": [{"type": "inAppPurchasePrices",
                                                                  "id": "${p1}"}]}}},
            "included": [{"type": "inAppPurchasePrices", "id": "${p1}",
                          "attributes": {"startDate": None, "endDate": None},
                          "relationships": {
                              "inAppPurchaseV2": rel("inAppPurchases", iap_id),
                              "inAppPurchasePricePoint": rel("inAppPurchasePricePoints", point["id"])}}]})
        if st in (200, 201):
            print(f"    + price: USA ${p['usd']} (base USA; Apple fills the other storefronts)")
            return
        # Right after availability is written Apple can briefly answer 409 "processing" (the
        # subscription lesson in asc_iap.py); anything else is a real error.
        if st == 409 and "process" in json.dumps(j).lower() and attempt < 3:
            time.sleep(5 * (attempt + 1))
            continue
        print(f"\n!! POST /v1/inAppPurchasePriceSchedules -> HTTP {st}\n{json.dumps(j, indent=1)[:2000]}")
        sys.exit(1)


def png_or_jpeg(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
        return "png", w, h
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg", None, None
    return None, None, None


def ensure_screenshot(http, iap_id, p, image, force):
    if not image:
        return
    st, j = http.get(f"/v2/inAppPurchases/{iap_id}/appStoreReviewScreenshot") if iap_id else (404, {})
    cur = (j.get("data") or None) if st == 200 else None
    state = (((cur or {}).get("attributes") or {}).get("assetDeliveryState") or {}).get("state")
    if cur and state in ("COMPLETE", "UPLOAD_COMPLETE") and not force:
        print(f"    = review screenshot ({cur['attributes'].get('fileName')}, {state})")
        return
    data = image.read_bytes()
    if http.dry:
        print(f"    [dry-run] would {'replace' if cur else 'upload'} review screenshot {image.name} "
              f"({len(data) // 1024} KB)")
        return
    if cur:
        http.must_write("DELETE", f"/v1/inAppPurchaseAppStoreReviewScreenshots/{cur['id']}")
    res = http.must_write("POST", "/v1/inAppPurchaseAppStoreReviewScreenshots", {"data": {
        "type": "inAppPurchaseAppStoreReviewScreenshots",
        "attributes": {"fileName": image.name, "fileSize": len(data)},
        "relationships": {"inAppPurchaseV2": rel("inAppPurchases", iap_id)}}})
    shot = res["data"]
    for op in shot["attributes"].get("uploadOperations") or []:
        ur = http.upload(op, data[op["offset"]: op["offset"] + op["length"]])
        if ur.status_code not in (200, 201, 204):
            print(f"!! screenshot upload part -> {ur.status_code}: {ur.text[:300]}")
            sys.exit(1)
    http.must_write("PATCH", f"/v1/inAppPurchaseAppStoreReviewScreenshots/{shot['id']}", {"data": {
        "type": "inAppPurchaseAppStoreReviewScreenshots", "id": shot["id"],
        "attributes": {"uploaded": True, "sourceFileChecksum": hashlib.md5(data).hexdigest()}}})
    for _ in range(20):                      # asset processing is asynchronous
        st, j = http.get(f"/v1/inAppPurchaseAppStoreReviewScreenshots/{shot['id']}")
        state = (((j.get("data") or {}).get("attributes") or {}).get("assetDeliveryState") or {}).get("state")
        if state in ("COMPLETE", "FAILED"):
            break
        time.sleep(3)
    if state not in ("COMPLETE", "UPLOAD_COMPLETE"):
        print(f"!! review screenshot for {p['productId']} ended in state {state}: {json.dumps(j)[:600]}")
        sys.exit(1)
    print(f"    + review screenshot {image.name} ({len(data) // 1024} KB, {state})")


# ----------------------------------------------------------------------------- verification

def automatic_price(http, sid, territory):
    st, j = http.get(f"/v1/inAppPurchasePriceSchedules/{sid}/automaticPrices",
                     {"filter[territory]": territory, "include": "inAppPurchasePricePoint", "limit": 50})
    if st != 200:
        return None
    pts = {x["id"]: x["attributes"].get("customerPrice")
           for x in j.get("included") or [] if x["type"] == "inAppPurchasePricePoints"}
    today = time.strftime("%Y-%m-%d")
    for pr in j.get("data") or []:
        a = pr["attributes"]
        if (a.get("startDate") and a["startDate"] > today) or (a.get("endDate") and a["endDate"] <= today):
            continue
        ppid = (((pr.get("relationships") or {}).get("inAppPurchasePricePoint") or {}).get("data") or {}).get("id")
        return pts.get(ppid)
    return None


def verify(http, iap_id, p, wanted_terrs, need_ready, wait_auto):
    """Read everything back. Returns (ok, row)."""
    row = {"productId": p["productId"], "id": iap_id}
    problems = []
    if not iap_id:
        return False, dict(row, problems=["IAP does not exist"])
    # The state moves to READY_TO_SUBMIT asynchronously once the screenshot is processed.
    for attempt in range(8 if (need_ready and wait_auto) else 1):
        j = http.must_get(f"/v2/inAppPurchases/{iap_id}", {"fields[inAppPurchases]": "state,inAppPurchaseType,name"})
        row["state"] = j["data"]["attributes"].get("state")
        if not need_ready or row["state"] in IAP_READY_OR_BEYOND or attempt == 7:
            break
        time.sleep(10)
    row["type"] = j["data"]["attributes"].get("inAppPurchaseType")
    if row["type"] != p["type"]:
        problems.append(f"type {row['type']} != {p['type']}")
    locs = read_localizations(http, iap_id)
    row["localizations"] = len([L for L in p["locales"] if L in locs])
    bad_text = [L for L in p["locales"] if L in locs and
                (locs[L][1], locs[L][2]) != (p["locales"][L]["name"], p["locales"][L]["description"])]
    if row["localizations"] != len(p["locales"]):
        problems.append(f"localizations {row['localizations']}/{len(p['locales'])}")
    if bad_text:
        problems.append(f"localization text differs in {bad_text}")
    d, terrs = read_availability(http, iap_id)
    row["territories"] = len(terrs or ())
    if terrs != set(wanted_terrs):
        problems.append(f"availability {len(terrs or ())} != {len(wanted_terrs)} wanted")
    sid, base, manual = read_schedule(http, iap_id)
    row["base"], row["manual"] = base, manual
    if not (base == "USA" and manual == {"USA": p["usd"]}):
        problems.append(f"price schedule base={base} manual={manual}, want USA {p['usd']} only")
    auto = None
    for attempt in range(8 if wait_auto else 1):
        auto = http.total(f"/v1/inAppPurchasePriceSchedules/{sid}/automaticPrices") if sid else None
        if auto is not None and auto >= AUTO_PRICE_MIN:
            break
        if wait_auto:
            time.sleep(15)
    row["automaticPrices"] = auto
    if auto is None or auto < AUTO_PRICE_MIN:
        problems.append(f"automaticPrices total {auto} < {AUTO_PRICE_MIN}")
    if p["try"] is not None and sid:
        tur = automatic_price(http, sid, "TUR")
        row["TUR"] = tur
        if tur is None or Decimal(tur) != Decimal(p["try"]):
            problems.append(f"TUR automatic price {tur} != golden {p['try']}")
    st, s = http.get(f"/v2/inAppPurchases/{iap_id}/appStoreReviewScreenshot")
    shot = (s.get("data") or None) if st == 200 else None
    row["screenshot"] = ((((shot or {}).get("attributes") or {}).get("assetDeliveryState") or {})
                         .get("state")) if shot else None
    if need_ready and row["state"] not in IAP_READY_OR_BEYOND:
        problems.append(f"state {row['state']} (want READY_TO_SUBMIT)")
    row["problems"] = problems
    return not problems, row


# ----------------------------------------------------------------------------- price probe (read-only)

def price_probe(http, products):
    """Dry-run helper when the app has no record yet: check each USD point on the account's app
    price grid and its TUR equalisation against the golden column (INFERRED: IAPs use the same grid)."""
    st, j = http.get("/v1/apps", {"limit": 1, "fields[apps]": "bundleId"})
    if st != 200 or not j.get("data"):
        print("  ! price probe: no app on the account to read the grid from")
        return True
    probe = j["data"][0]["id"]
    grid = http.get_all(f"/v1/apps/{probe}/appPricePoints",
                        {"filter[territory]": "USA", "fields[appPricePoints]": "customerPrice"})
    by_price = {g["attributes"]["customerPrice"]: g["id"] for g in grid}
    ok = True
    for usd in sorted({p["usd"] for p in products}, key=Decimal):
        gid = by_price.get(usd)
        goldens = sorted({p["try"] for p in products if p["usd"] == usd and p["try"]})
        if not gid:
            print(f"  !! price probe: no USA point ${usd}")
            ok = False
            continue
        tur = None
        st, e = http.get(f"/v3/appPricePoints/{gid}/equalizations",
                         {"filter[territory]": "TUR", "fields[appPricePoints]": "customerPrice", "limit": 5})
        if st == 200 and e.get("data"):
            tur = e["data"][0]["attributes"].get("customerPrice")
        match = all(Decimal(tur) == Decimal(g) for g in goldens) if (tur and goldens) else None
        if match is False:
            ok = False
        print(f"  price probe: USA ${usd} -> TUR {tur}  golden {goldens or '-'}  "
              f"{'OK' if match else ('MISMATCH' if match is False else 'n/a')}")
    return ok


# ----------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bundle", required=True, help="the app's bundle id, e.g. com.manycode.arrowout")
    ap.add_argument("--catalog", required=True, help="catalog JSON (see the module docstring)")
    ap.add_argument("--rules", help="rules.json whose shop.products must match the catalog ids/prices")
    ap.add_argument("--storekit", help=".storekit file whose products must match the catalog ids/prices")
    ap.add_argument("--locales", help="comma list of required ASC locales (default: the factory 13)")
    ap.add_argument("--exclude-territories", help="comma list (default: catalog value, else CHN)")
    ap.add_argument("--screenshot", help="review screenshot (PNG/JPEG) uploaded to every product")
    ap.add_argument("--force-screenshot", action="store_true", help="replace an existing screenshot")
    ap.add_argument("--reprice", action="store_true", help="replace a price schedule that differs")
    ap.add_argument("--dry-run", action="store_true", help="GET requests only; print the plan")
    ap.add_argument("--self-check", action="store_true", help="validate the catalog and exit (no network)")
    ap.add_argument("--price-probe", action="store_true",
                    help="dry-run: read the account's app price grid to check the USD points + TUR golden")
    ap.add_argument("--readback", help="write the verification rows to this JSON file")
    args = ap.parse_args()

    required = [norm_locale(x.strip()) for x in args.locales.split(",")] if args.locales else FACTORY_LOCALES
    products, meta = load_catalog(args.catalog, required, args.rules, args.storekit)
    foreign = [p["productId"] for p in products if not p["productId"].startswith(args.bundle + ".")]
    if foreign:     # a catalog pointed at the wrong app would create another app's products
        sys.exit(f"!! product ids do not start with '{args.bundle}.': {foreign[:4]}")
    if args.self_check:
        return
    image = Path(args.screenshot) if args.screenshot else None
    if image:
        if not image.exists():
            sys.exit(f"!! screenshot not found: {image}")
        kind, w, h = png_or_jpeg(image.read_bytes()[:32])
        if not kind:
            sys.exit(f"!! screenshot is not PNG/JPEG: {image}")
        print(f"review screenshot: {image.name} {kind} {w}x{h}" if w else f"review screenshot: {image.name} {kind}")

    e = asc_iap.env()
    http = Http(e, args.dry_run)
    excl = ([t.strip().upper() for t in args.exclude_territories.split(",") if t.strip()]
            if args.exclude_territories is not None else (meta.get("excludeTerritories") or ["CHN"]))
    mode = "DRY-RUN (GET only)" if args.dry_run else "WRITE"
    print(f"ASC consumables [{mode}]: {args.bundle}  products={len(products)}  exclude={excl}")

    rc = 0
    try:
        terrs = [t["id"] for t in http.get_all("/v1/territories")]
        unknown = [t for t in excl if t not in terrs]
        if unknown:
            sys.exit(f"!! unknown territories to exclude: {unknown}")
        wanted = sorted(t for t in terrs if t not in excl)
        print(f"territories: {len(terrs)} on ASC, {len(wanted)} wanted")

        app = find_app(http, args.bundle)
        if not app:
            print(f"!! no ASC app record for {args.bundle} (run `fastlane create_app` first; it needs the "
                  f"Apple ID session).")
            if not args.dry_run:
                sys.exit(1)
            print("[dry-run] a real run would stop here. Plan for a fresh app:")
            for p in products:
                print(f"  + IAP {p['productId']} {p['type']} USA ${p['usd']}"
                      + (f" (TUR golden {p['try']})" if p["try"] else "")
                      + f"; {len(p['locales'])} localizations; availability {len(wanted)} territories"
                      + ("; review screenshot" if image else "; NO review screenshot (stays MISSING_METADATA)"))
            if args.price_probe and not price_probe(http, products):
                rc = 1
            rc = rc or 3
        else:
            app_id = app["id"]
            print(f"app {app_id} ({app['attributes'].get('name')})")
            have = existing_iaps(http, app_id)
            strays = sorted(set(have) - {p["productId"] for p in products})
            if strays:
                print(f"  ! IAPs on ASC that are not in the catalog (left untouched): {strays}")
            rows, ok_all = [], True
            for p in products:
                iap = ensure_iap(http, app_id, p, have)
                iap_id = iap["id"] if iap else None
                ensure_localizations(http, iap_id, p)
                ensure_availability(http, iap_id, p, wanted)   # availability BEFORE price (asc_iap lesson)
                ensure_price(http, iap_id, p, args.reprice)
                ensure_screenshot(http, iap_id, p, image, args.force_screenshot)
            print("\nverify (read back):")
            if not args.dry_run:
                have = existing_iaps(http, app_id)          # re-read: includes what this run created
            for p in products:
                iap_id = (have.get(p["productId"]) or {}).get("id")
                has_shot = bool(image) or bool(iap_id and ((http.get(
                    f"/v2/inAppPurchases/{iap_id}/appStoreReviewScreenshot")[1].get("data")) or None))
                ok, row = verify(http, iap_id, p, wanted, need_ready=has_shot and not args.dry_run,
                                 wait_auto=not args.dry_run)
                rows.append(row)
                ok_all &= ok
                print(f"  {'ok ' if ok else '!! '}{p['productId']}: state={row.get('state')} "
                      f"locs={row.get('localizations')} terr={row.get('territories')} "
                      f"USA={row.get('manual', {}).get('USA')} auto={row.get('automaticPrices')} "
                      f"TUR={row.get('TUR')} shot={row.get('screenshot')}"
                      + (f"  -> {row['problems']}" if row.get("problems") else ""))
                if ok and not has_shot:
                    print("     (READY_TO_SUBMIT needs the review screenshot: re-run with --screenshot)")
            if args.readback:
                Path(args.readback).parent.mkdir(parents=True, exist_ok=True)
                Path(args.readback).write_text(json.dumps({"bundle": args.bundle, "app": app_id,
                                                           "rows": rows}, indent=1))
                print(f"readback -> {args.readback}")
            if not ok_all:
                rc = 3 if args.dry_run else 1
    except DryRunWrite as ex:            # a code path tried to write during a dry-run: a bug here
        print(f"\n!! {ex}")
        rc = 1
    print(f"\nHTTP calls: {json.dumps(http.count, sort_keys=True)}")
    if args.dry_run:
        writes = sum(v for k, v in http.count.items() if k != "GET")
        print(f"dry-run: {http.count.get('GET', 0)} GET, {writes} writes")
    sys.exit(rc)


if __name__ == "__main__":
    main()
