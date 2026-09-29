#!/usr/bin/env python3
"""App Store Connect: subscription group + abonelikler (weekly/monthly/yearly) + fiyat + localization + trial.

Kullanım (repo kökünden):  python3 scripts/asc_iap.py --slug <slug>

>>> İLK ÇALIŞTIRMADA HATA NORMALDİR. Apple bu API'nin şemasını sık günceller.
>>> Hata gövdesi aynen basılır — Claude Code okur, scripti düzeltir, tekrar dener.
>>> Bir kez yeşil geçtikten sonra her app için deterministiktir.

Yaptıkları:
  1. Bundle ID'den app'i bulur
  2. Subscription group ("<Name> Pro") + group localization (en-US)
  3. pricing'teki her plan için abonelik: weekly_usd → <bundle>.weekly (ONE_WEEK),
     monthly_usd → .monthly (ONE_MONTH), yearly_usd → .yearly (ONE_YEAR);
     pricing'te hiçbiri yoksa eski varsayılan: monthly + yearly
  4. Abonelik localization'ları (en-US)
  5. Fiyat: price point eşleştirme (USA, ideas.yaml'daki USD, string karşılaştırma)
  6. Availability: tüm bölgeler + yeni bölgelerde otomatik
  7. <plan>_trial_days > 0 ise FREE_TRIAL introductory offer (tüm bölgeler)

Manuel kalabilen: abonelik review screenshot'ı (ASC arayüzünden 30 sn).
Gereksinim: pip install pyjwt cryptography requests  (setup.sh kurar)
"""
import argparse, json, os, re, sys, time
from pathlib import Path

import jwt
import requests

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://api.appstoreconnect.apple.com"

# ASC enum'lari — ISO-8601 (P1W/P3D) DEGIL; literal ISO gonderimi 409 ENTITY_ERROR verir.
PERIOD_BY_PLAN = {"weekly": "ONE_WEEK", "monthly": "ONE_MONTH", "yearly": "ONE_YEAR"}
TRIAL_DURATION_BY_DAYS = {3: "THREE_DAYS", 7: "ONE_WEEK", 14: "TWO_WEEKS", 30: "ONE_MONTH",
                          60: "TWO_MONTHS", 90: "THREE_MONTHS", 180: "SIX_MONTHS", 365: "ONE_YEAR"}


def plans_from_pricing(pricing):
    """pricing'teki *_usd anahtarlarindan (suffix, fiyat_str, trial_days) listesi.

    Fiyat string'e 2 ondalikla cevrilir: price point eslestirmesi API'nin dondurdugu
    customerPrice string'i uzerinden yapilir (float karsilastirmasi degil).
    Hicbir *_usd anahtari yoksa eski monthly+yearly varsayilani korunur.
    """
    plans = []
    for suffix in ("weekly", "monthly", "yearly"):
        if f"{suffix}_usd" in pricing:
            plans.append((suffix, f'{float(pricing[f"{suffix}_usd"]):.2f}',
                          int(pricing.get(f"{suffix}_trial_days") or 0)))
    return plans or [("monthly", "4.99", 0), ("yearly", "29.99", 0)]


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


def token(e):
    key = Path(ROOT, os.path.expanduser(e["ASC_KEY_PATH"])).read_text()
    now = int(time.time())
    return jwt.encode(
        {"iss": e["ASC_ISSUER_ID"], "iat": now, "exp": now + 1200, "aud": "appstoreconnect-v1"},
        key, algorithm="ES256", headers={"kid": e["ASC_KEY_ID"]},
    )


class API:
    def __init__(self, e):
        self.e = e
        self._tok = None
        self._tok_at = 0.0

    def _headers(self):
        # ASC JWTs live 20 min; the long per-territory loops run longer, so refresh
        # the token well before it expires (and on 401 below) — otherwise the run
        # dies mid-way with NOT_AUTHORIZED.
        now = time.time()
        if self._tok is None or now - self._tok_at > 18 * 60:
            self._tok = token(self.e)
            self._tok_at = now
        return {"Authorization": f"Bearer {self._tok}", "Content-Type": "application/json"}

    def _send(self, method, url, **kw):
        # Retry transient network drops / 429 / 5xx / expired-token 401. Apple's API
        # intermittently closes the connection (RemoteDisconnected) or rate-limits
        # during long loops; those are not real failures.
        last = None
        for attempt in range(6):
            try:
                r = requests.request(method, url, headers=self._headers(), timeout=60, **kw)
            except requests.exceptions.RequestException as ex:
                last = ex
                if attempt == 5:
                    raise
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 401 and attempt < 5:
                self._tok = None            # force a fresh token, then retry
                time.sleep(1)
                continue
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(2 ** attempt)
                continue
            return r
        raise last  # unreachable

    def req(self, method, path, body=None, params=None, ok=(200, 201)):
        r = self._send(method, BASE + path, json=body, params=params)
        if r.status_code in ok:
            return r.json() if r.text else {}
        print(f"\n!! {method} {path} -> HTTP {r.status_code}\n{r.text}")
        sys.exit(1)

    def get_all(self, path, params=None):
        params = dict(params or {}, limit=200)
        out, url = [], path
        while url:
            r = self._send("GET", BASE + url if url.startswith("/") else url,
                           params=params if url == path else None)
            if r.status_code != 200:
                print(f"\n!! GET {url} -> HTTP {r.status_code}\n{r.text}")
                sys.exit(1)
            j = r.json()
            out += j.get("data", [])
            url = (j.get("links") or {}).get("next")
        return out


def rel(t, i):
    return {"data": {"type": t, "id": i}}


def ensure_price(api, sub_id, product_id, price_usd, reprice=False):
    """Abonelige TUM bolgeler icin baz fiyat yazar (eksik olanlari tamamlar).

    KRITIK: ASC arayuzu USA baz fiyati girince ~175 bolgenin hepsini otomatik
    doldurur; API'de tek subscriptionPrices POST'u YALNIZ o bolgeyi olusturur.
    Kalan bolgeler fiyatsiz kalirsa abonelik kalici MISSING_METADATA'da takilir
    (READY_TO_SUBMIT'e gecmez). Cozum: USA price point'inin equalizations'i
    (her bolkedeki esdeger fiyat) uzerinden eksik her bolgeye fiyat yaz.
    availability'den SONRA cagrilmali. Idempotent: fiyatli bolgeler atlanir.
    Yeni aboneliklerde kisa sure 409 'processing the pricing' gorulebilir — beklenir.
    """
    priced = set()
    for pr in api.get_all(f"/v1/subscriptions/{sub_id}/prices", params={"include": "territory"}):
        t = ((pr.get("relationships", {}).get("territory") or {}).get("data") or {}).get("id")
        if t:
            priced.add(t)
    pts = api.get_all(f"/v1/subscriptions/{sub_id}/pricePoints",
                      params={"filter[territory]": "USA",
                              "fields[subscriptionPricePoints]": "customerPrice"})
    base = next((p for p in pts if p["attributes"]["customerPrice"] == price_usd), None)
    if not base:
        print(f"  !! ${price_usd} icin USA price point yok. Yakin fiyatlar: "
              f"{sorted({p['attributes']['customerPrice'] for p in pts})[:20]} ...")
        sys.exit(1)
    # USA equalizations'ta yer almaz; onu ayrica hedefe ekle.
    targets = [(base["id"], "USA")]
    for p in api.get_all(f"/v1/subscriptionPricePoints/{base['id']}/equalizations",
                         params={"include": "territory"}):
        t = ((p.get("relationships", {}).get("territory") or {}).get("data") or {}).get("id")
        targets.append((p["id"], t))
    # --reprice: write the new point to EVERY territory, not just the unpriced ones. Without it
    # this function can only fill gaps, so a price change on a live subscription silently did
    # nothing and the app kept selling at the old price.
    missing = targets if reprice else [(pid, t) for pid, t in targets if t and t not in priced]
    missing = [(pid, t) for pid, t in missing if t]
    if not missing:
        print(f"    = fiyat tum bolgelerde tanimli ({product_id})")
        return
    print(f"    fiyat: ${price_usd} baz — {len(missing)} bolge yaziliyor...")
    done = 0
    for pid, t in missing:
        body = {"data": {"type": "subscriptionPrices",
                         "relationships": {"subscription": rel("subscriptions", sub_id),
                                           "subscriptionPricePoint": rel("subscriptionPricePoints", pid)}}}
        for attempt in range(4):
            r = api._send("POST", BASE + "/v1/subscriptionPrices", json=body)
            if r.status_code in (200, 201):
                done += 1
                break
            if r.status_code == 409 and "processing the pricing" in r.text and attempt < 3:
                time.sleep(5 * (attempt + 1))
                continue
            print(f"\n!! POST /v1/subscriptionPrices ({t}) -> HTTP {r.status_code}\n{r.text}")
            sys.exit(1)
        if done % 40 == 0:
            print(f"      {done}/{len(missing)}")
    print(f"      {done}/{len(missing)} tamam")


def ensure_availability(api, sub_id, product_id, territories):
    """Abonelik availability kaydi yoksa tum bolgelerle olusturur."""
    r = api._send("GET", BASE + f"/v1/subscriptions/{sub_id}/subscriptionAvailability")
    if r.status_code == 200 and (r.json().get("data") or None):
        print(f"    = availability zaten var ({product_id})")
        return
    api.req("POST", "/v1/subscriptionAvailabilities", {
        "data": {"type": "subscriptionAvailabilities",
                 "attributes": {"availableInNewTerritories": True},
                 "relationships": {
                     "subscription": rel("subscriptions", sub_id),
                     "availableTerritories": {"data": [{"type": "territories", "id": t}
                                                        for t in territories]}}}})
    print(f"    availability: {len(territories)} bolge")


def ensure_intro_offer(api, sub_id, product_id, trial_days, territories):
    """trial_days > 0 ise FREE_TRIAL introductory offer'i BOLGE BASINA olusturur.

    Canli API territory iliskisini ZORUNLU tutuyor (409 ENTITY_ERROR.RELATIONSHIP.REQUIRED);
    'omit = tum bolgeler' varsayimi yanlisti. ASC arayuzunun 'tum bolgeler' dugmesi de
    arka planda bolge basina kayit acar. Idempotent: kapsanan bolgeler atlanir.
    Baz fiyat (subscriptionPrices) tanimlandiktan SONRA cagrilmali.
    """
    if trial_days <= 0:
        # Moving a trial between plans means the old plan's offer has to go, or the app ships two
        # trials and Apple reads the paywall as misleading.
        existing = api.get_all(f"/v1/subscriptions/{sub_id}/introductoryOffers")
        if existing:
            print(f"    intro offer: kaldiriliyor ({product_id}) — {len(existing)} kayit")
            for off in existing:
                api._send("DELETE", BASE + f"/v1/subscriptionIntroductoryOffers/{off['id']}")
        return
    duration = TRIAL_DURATION_BY_DAYS.get(int(trial_days))
    if not duration:
        sys.exit(f"!! {product_id}: {trial_days} gunluk trial icin ASC duration enum'u yok. "
                 f"Desteklenen gun degerleri: {sorted(TRIAL_DURATION_BY_DAYS)}")
    covered = set()
    url = f"/v1/subscriptions/{sub_id}/introductoryOffers?include=territory&limit=200"
    while url:
        r = api._send("GET", BASE + url if url.startswith("/") else url)
        if r.status_code != 200:
            print(f"\n!! GET introductoryOffers -> HTTP {r.status_code}\n{r.text}")
            sys.exit(1)
        j = r.json()
        for o in j.get("data", []):
            t = (((o.get("relationships") or {}).get("territory") or {}).get("data") or {})
            if t.get("id"):
                covered.add(t["id"])
        url = (j.get("links") or {}).get("next")
    missing = [t for t in territories if t not in covered]
    if not missing:
        print(f"    = intro offer tum bolgelerde var ({product_id})")
        return
    print(f"    intro offer: FREE_TRIAL {duration} — {len(missing)} bolge yaziliyor...")
    for i, terr in enumerate(missing, 1):
        # 409 STATE_ERROR "DateRange ... overlaps with existing offer" means the offer for
        # this territory ALREADY EXISTS — the end state we want. It shows up when a POST is
        # retried after it actually succeeded, and aborting there left trackdetect with 13
        # of 175 territories and no yearly at all (2026-08-21). Tolerate it and continue.
        api.req("POST", "/v1/subscriptionIntroductoryOffers", {
            "data": {"type": "subscriptionIntroductoryOffers",
                     "attributes": {"offerMode": "FREE_TRIAL", "duration": duration,
                                    "numberOfPeriods": 1},
                     "relationships": {"subscription": rel("subscriptions", sub_id),
                                       "territory": rel("territories", terr)}}},
            ok=(200, 201, 409))
        if i % 25 == 0 or i == len(missing):
            print(f"      {i}/{len(missing)}")


def ensure_grace_period(api, app_id):
    """3 gunluk billing grace period — hem uretim (optIn) hem sandbox (sandboxOptIn).

    Kullanici standardi: abone odemesi basarisiz olsa bile 3 gun erisim surer (churn
    azaltir). Endpoint id = app_id. Idempotent (PATCH). ASC arayuzunde: Subscriptions
    > Billing Grace Period.
    """
    api.req("PATCH", f"/v1/subscriptionGracePeriods/{app_id}", {
        "data": {"type": "subscriptionGracePeriods", "id": app_id,
                 "attributes": {"optIn": True, "sandboxOptIn": True,
                                "duration": "THREE_DAYS", "renewalType": "ALL_RENEWALS"}}})
    print("  + billing grace period: 3 gun (uretim + sandbox)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--reprice", action="store_true",
                    help="overwrite existing territory prices instead of only filling gaps")
    ap.add_argument("--allow-no-trial", action="store_true",
                    help="explicitly allow a config where NO plan carries a free trial")
    args = ap.parse_args()
    slug = args.slug

    e = env()
    idea = json.loads(os.popen(f"python3 {ROOT}/scripts/idea.py json {slug}").read())
    name = idea["name"]
    plans = plans_from_pricing(idea.get("pricing") or {})
    # SPINWHEEL DERSI (2026-09-19): weekly_trial_days anahtari yoksa 0 sayilir ve offer
    # SESSIZCE atlanirdi — musteri trial'siz $3.99 odedi. Trial'siz kurulum artik ancak
    # bilincli bir bayrakla mumkun; unutulmus bir YAML anahtari asla sessizce gecmez.
    if not any(td > 0 for _, _, td in plans) and not args.allow_no_trial:
        sys.exit(f"!! {slug}: hicbir planda trial yok (pricing'de *_trial_days eksik ya da 0).\n"
                 "   Istenen buysa --allow-no-trial ile tekrar calistir; degilse ideas.yaml'a\n"
                 "   weekly_trial_days: 3 ekle. (spinwheel, 2026-09-19)")
    bundle = f'{e["BUNDLE_PREFIX"]}.{slug}'

    api = API(e)
    print(f"ASC IAP kurulumu: {name} ({bundle})")

    # 1. App
    apps = api.req("GET", "/v1/apps", params={"filter[bundleId]": bundle})["data"]
    if not apps:
        sys.exit(f"!! ASC'de app yok: {bundle} — once 'fastlane create_app' calistir.")
    app_id = apps[0]["id"]

    # 2. Subscription group (varsa kullan)
    groups = api.req("GET", f"/v1/apps/{app_id}/subscriptionGroups")["data"]
    if groups:
        group_id = groups[0]["id"]
        print("  = group zaten var")
    else:
        g = api.req("POST", "/v1/subscriptionGroups", {
            "data": {"type": "subscriptionGroups",
                     "attributes": {"referenceName": f"{name} Pro"},
                     "relationships": {"app": rel("apps", app_id)}}})
        group_id = g["data"]["id"]
        print("  + group olusturuldu")
        api.req("POST", "/v1/subscriptionGroupLocalizations", {
            "data": {"type": "subscriptionGroupLocalizations",
                     "attributes": {"name": f"{name} Pro", "locale": "en-US"},
                     "relationships": {"subscriptionGroup": rel("subscriptionGroups", group_id)}}})

    # 3-6. Abonelikler — her adim idempotent: yarim kalan onceki calismalar tamamlanir.
    existing = {s["attributes"]["productId"]: s["id"]
                for s in api.req("GET", f"/v1/subscriptionGroups/{group_id}/subscriptions")["data"]}

    territories = [t["id"] for t in api.get_all("/v1/territories")]

    built = []
    for suffix, price_usd, trial_days in plans:
        period = PERIOD_BY_PLAN[suffix]
        disp = suffix.capitalize()
        product_id = f"{bundle}.{suffix}"
        if product_id in existing:
            print(f"  = {product_id} zaten var")
            sub_id = existing[product_id]
        else:
            review_note = (
                f"{name} Pro is a standard auto-renewable subscription that unlocks the app's "
                f"premium features. To find it: launch the app and complete onboarding, or open "
                f"Settings and tap Upgrade to Pro. The paywall lists the available plans (including "
                f"any free trial). Purchases are processed by StoreKit/RevenueCat; no account or "
                f"login is required.")
            s = api.req("POST", "/v1/subscriptions", {
                "data": {"type": "subscriptions",
                         "attributes": {"name": f"{name} {disp}", "productId": product_id,
                                        "subscriptionPeriod": period, "groupLevel": 1,
                                        "reviewNote": review_note},
                         "relationships": {"group": rel("subscriptionGroups", group_id)}}})
            sub_id = s["data"]["id"]
            print(f"  + {product_id}")

            api.req("POST", "/v1/subscriptionLocalizations", {
                "data": {"type": "subscriptionLocalizations",
                         "attributes": {"locale": "en-US", "name": disp,
                                        "description": f"Full access to {name}, billed {suffix}."},
                         "relationships": {"subscription": rel("subscriptions", sub_id)}}})

        # SIRA ONEMLI: once availability, sonra fiyat. USA price point'i abonelik USA'da
        # "available" olana kadar GECERSIZ sayilir; availability'siz fiyat POST'u kalici
        # 409 ENTITY_ERROR.RELATIONSHIP.INVALID ("processing the pricing information") verir.
        ensure_availability(api, sub_id, product_id, territories)
        ensure_price(api, sub_id, product_id, price_usd, reprice=args.reprice)
        # Introductory offer (baz fiyat tanimlandiktan SONRA olusturulmali)
        ensure_intro_offer(api, sub_id, product_id, trial_days, territories)
        built.append((product_id, sub_id, trial_days))

    # 8. Billing grace period (3 gun, uretim + sandbox) — kullanici standardi.
    ensure_grace_period(api, app_id)

    # 9. DOGRULAMA — yaz degil, OKU: config'in vaat ettigi trial ASC'de gercekten var mi?
    # ensure_intro_offer'in yarim kalmis/sessizce basarisiz olmus bir kosusu ancak burada
    # yakalanir. Esik 170: ~175 bolge, birkac yeni/kapali bolge toleransi.
    failed = False
    for product_id, sub_id, trial_days in built:
        n = len(api.get_all(f"/v1/subscriptions/{sub_id}/introductoryOffers"))
        if trial_days > 0 and n < 170:
            print(f"!! {product_id}: config {trial_days} gun trial diyor, ASC'de {n} bolgede "
                  f"offer var (>=170 gerekir)")
            failed = True
        elif trial_days == 0 and n > 0:
            print(f"!! {product_id}: config trial YOK diyor, ASC'de {n} offer duruyor")
            failed = True
        else:
            print(f"  ok {product_id}: trial_days={trial_days}, offer bolgesi={n}")
    if failed:
        sys.exit("!! trial dogrulamasi BASARISIZ — yukaridaki urunler config ile uyusmuyor.")

    print("\nOK. Kontrol: ASC > App > Subscriptions. Review screenshot bos ise 30 sn'de ekle.")


if __name__ == "__main__":
    main()
