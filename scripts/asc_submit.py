#!/usr/bin/env python3
"""App Store Connect: bir app'i (ve varsa aboneliklerini) incelemeye gonder.

Kullanim (repo kokunden):  python3 scripts/asc_submit.py --slug <slug>

Faz 11'in tam otomasyonu. `fastlane release`/`deliver` sadece app VERSION'i submit
eder; YENI bir subscription group'un abonelikleri OTOMATIK bundle OLMAZ. Apple'in
kurali:
  - Yeni subscription group (onceden onaylanmis versiyonu yok) icin abonelikler
    version ile AYNI reviewSubmission'da gonderilmeli.
  - reviewSubmissionItems'a subscription EKLENEMEZ; item tipleri:
      appStoreVersion, subscriptionGroupVersion, subscriptionVersion
  - Yeni grupta group version "en az bir subscription ile", her subscription da
    "group version ile" gonderilmeli => hepsi TEK submission'da:
      appStoreVersion + subscriptionGroupVersion + her subscriptionVersion

Bu script bunu yapar:
  1. Bundle'dan app'i bulur, en son editable version'i (PREPARE_FOR_SUBMISSION /
     DEVELOPER_REJECTED) ve ekli build'i dogrular.
  2. Acik (WAITING/READY) reviewSubmission varsa iptal eder.
  3. Yeni reviewSubmission acar.
  4. appStoreVersion + (varsa) subscriptionGroupVersion + her subscriptionVersion
     item'ini ekler.
  5. submitted=true PATCH'ler, WAITING_FOR_REVIEW'i dogrular.

Consumable / non-consumable IAP'ler (coin oyunlari, 2026-09-28, additive):
  - Apple spec 4.5: reviewSubmissionItems'in `inAppPurchaseVersion` iliskisi var. Onaylanmamis her
    IAP'in editable versiyonu (/v2/inAppPurchases/{id}/versions) version ile AYNI submission'a girer.
  - Onaylanmamis bir IAP READY_TO_SUBMIT degilse submit YOK (dukkani bos bir app gondermektense dur;
    submit-without-subscriptions dersinin aynasi). Abonelikler inAppPurchasesV2'de gorunmez: aboneli
    fabrika app'lerinde liste bostur ve akisa tek bir GET disinda hicbir sey eklenmez.
  - --bundle: bundle'i slug'dan turemeyen app icin (mazeout -> com.manycode.arrowout). Verilmezse
    eski formul aynen: BUNDLE_PREFIX.slug.
  - --dry-run: yalniz GET; app/version/build/IAP durumunu okur, plani basar, hicbir sey yazmaz.

IDFA beyani (--uses-idfa, 2026-09-29, additive; verilmezse davranis diger app'ler icin AYNEN):
  - Reklam-atif SDK'si (Meta FacebookCore) linkleyen bir app'in version'i usesIdfa=true demeli; yoksa Apple'in asenkron
    binary kontrolu version'i INVALID_BINARY yapar ve hicbir yerde okunur bir sebep yoktur (memory
    idfa-declaration-and-invalid-binary). fastlane 2.240.1 deliver add_id_info_* anahtarlarinin HICBIRINI kullanmaz.
  - --uses-idfa: build baglandiktan sonra, reviewSubmission OLUSTURULMADAN ONCE PATCH /v1/appStoreVersions/<id>
    {usesIdfa: true} + geri okuma; true okunmazsa submit YOK. --dry-run'da yalniz mevcut degeri basar.
  - Submit sonrasi version'i en az 15 dk INVALID_BINARY icin izle (dogrulama asenkron).

Not: /items alt-endpoint'i guvenilir degil; item sayimi icin ?include=items kullan.
Gereksinim: pip install pyjwt cryptography certifi
"""
import argparse, json, os, re, ssl, sys, time
from pathlib import Path
from urllib import request, error

import certifi, jwt

_CTX = ssl.create_default_context(cafile=certifi.where())
ROOT = Path(__file__).resolve().parent.parent
B = "https://api.appstoreconnect.apple.com"


def env():
    e = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            v = re.sub(r"\s+#.*$", "", v)
            e[k.strip()] = v.strip().strip('"').strip("'")
    return e


def make_token(e):
    p8 = Path(ROOT, os.path.expanduser(e["ASC_KEY_PATH"])).read_text()
    now = int(time.time())
    return jwt.encode({"iss": e["ASC_ISSUER_ID"], "iat": now, "exp": now + 1100,
                       "aud": "appstoreconnect-v1"}, p8, algorithm="ES256",
                      headers={"kid": e["ASC_KEY_ID"]})


class API:
    def __init__(self, tok):
        self.tok = tok

    def __call__(self, method, path, body=None):
        req = request.Request(B + path, method=method,
                              data=(json.dumps(body).encode() if body is not None else None),
                              headers={"Authorization": f"Bearer {self.tok}",
                                       "Content-Type": "application/json"})
        try:
            with request.urlopen(req, context=_CTX) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if raw and r.status != 204 else {})
        except error.HTTPError as ex:
            try:
                return ex.code, json.loads(ex.read().decode())
            except Exception:
                return ex.code, {}


def item(api, rs_id, rel, rel_type, rel_id):
    return api("POST", "/v1/reviewSubmissionItems", {"data": {
        "type": "reviewSubmissionItems",
        "relationships": {
            "reviewSubmission": {"data": {"type": "reviewSubmissions", "id": rs_id}},
            rel: {"data": {"type": rel_type, "id": rel_id}}}}})


def ensure_submission_prereqs(api, app_id):
    """Ilk submit'in APP-LEVEL zorunluluklari (yoksa version review'a ALINAMAZ):
    contentRightsDeclaration + ucretsiz fiyat cizelgesi. Bunlar olmadan reviewSubmission,
    'contentRightsDeclaration required' + 'APP_PRICING_REQUIRED' ile 409 verir."""
    api("PATCH", f"/v1/apps/{app_id}", {"data": {"type": "apps", "id": app_id,
        "attributes": {"contentRightsDeclaration": "DOES_NOT_USE_THIRD_PARTY_CONTENT"}}})
    # DIKKAT: Var olan bir appPriceSchedule GECERSIZ (bos/hatali base fiyat) olsa bile
    # GET 200 + data doner. Eski "schedule varsa atla" mantigi bu gecersiz cizelgeyi
    # atlayip submit'te APP_PRICING_REQUIRED (409) veriyordu (bluetoothmic 2026-07-23).
    # Cozum: ucretsiz fabrika app'i icin HER ZAMAN gecerli $0 cizelgesini (yeniden) kur.
    st, pts = api("GET", f"/v1/apps/{app_id}/appPricePoints"
                  "?filter[territory]=USA&limit=200&fields[appPricePoints]=customerPrice")
    free = next((p["id"] for p in pts.get("data", [])
                 if p["attributes"].get("customerPrice") in ("0", "0.00", "0.0")), None)
    if not free:
        print("  ! ucretsiz price point bulunamadi — fiyati elle 'Free' yap")
        return
    st, r = api("POST", "/v1/appPriceSchedules", {"data": {"type": "appPriceSchedules",
        "relationships": {"app": {"data": {"type": "apps", "id": app_id}},
            "baseTerritory": {"data": {"type": "territories", "id": "USA"}},
            "manualPrices": {"data": [{"type": "appPrices", "id": "${p1}"}]}}},
        "included": [{"type": "appPrices", "id": "${p1}",
            "attributes": {"startDate": None, "endDate": None},
            "relationships": {"appPricePoint": {"data": {"type": "appPricePoints", "id": free}}}}]})
    print("  + content rights + ucretsiz fiyat cizelgesi"
          if st in (200, 201) else f"  ! fiyat cizelgesi {st}: {r}")


def verify_trial_offers(api, slug, bundle, app_id):
    """Config'in vaat ettigi introductory offer ASC'de gercekten var mi?

    SPINWHEEL DERSI (2026-09-19): app, config'i 3 gun trial derken ASC'de sifir offer'la
    yayina cikti ve bir musteri trial'siz odeme yapti. Bu kapi, ideas.yaml'daki
    *_trial_days ile ASC'deki offer sayisini karsilastirir ve uyusmazlikta submit'i
    DAHA HICBIR SEYE DOKUNMADAN iptal eder. Esik 170 (~175 bolge - tolerans).
    """
    import yaml
    ideas = yaml.safe_load((ROOT / "ideas.yaml").read_text())
    if isinstance(ideas, dict):
        ideas = ideas.get("ideas", [])
    idea = next((i for i in ideas if i.get("slug") == slug), None)
    pricing = (idea or {}).get("pricing") or {}
    promised = {f"{bundle}.{s}": int(pricing.get(f"{s}_trial_days") or 0)
                for s in ("weekly", "monthly", "yearly") if f"{s}_usd" in pricing}
    if not promised:
        print("  ! pricing bloku yok — trial dogrulamasi atlandi (eski app olabilir)")
        return
    st, r = api("GET", f"/v1/apps/{app_id}/subscriptionGroups?include=subscriptions")
    subs = {d["attributes"]["productId"]: d["id"]
            for d in (r.get("included") or []) if d["type"] == "subscriptions"} if st == 200 else {}
    for pid, days in promised.items():
        sid = subs.get(pid)
        if sid is None:
            sys.exit(f"!! {pid}: ASC'de abonelik yok ama pricing'de tanimli. SUBMIT IPTAL.")
        n, path = 0, f"/v1/subscriptions/{sid}/introductoryOffers?limit=200"
        while path:
            st2, r2 = api("GET", path)
            if st2 != 200:
                sys.exit(f"!! {pid}: introductoryOffers okunamadi ({st2}). SUBMIT IPTAL.")
            n += len(r2.get("data") or [])
            nxt = (r2.get("links") or {}).get("next")
            path = nxt.split("appstoreconnect.apple.com")[1] if nxt else None
        if days > 0 and n < 170:
            sys.exit(f"!! {pid}: config {days} gun trial vaat ediyor, ASC'de {n} bolgede offer "
                     f"var (>=170 gerekir).\n   Once: python3 scripts/asc_iap.py --slug {slug}\n"
                     f"   SUBMIT IPTAL — trial'siz yayina cikmak musteriye vaadsiz para odetir.")
        if days == 0 and n > 0:
            sys.exit(f"!! {pid}: config trial YOK diyor ama ASC'de {n} offer var — paywall "
                     f"yanlis plani one cikarabilir. Once tutarliligi duzelt. SUBMIT IPTAL.")
        print(f"  trial ok: {pid} trial_days={days} offer_bolgesi={n}")


def set_uses_idfa(api, vid, tries=12):
    """PATCH appStoreVersions/<vid> usesIdfa=true until it READS BACK true (never trust the PATCH's 2xx alone); exit if not.
    Runs before the review submission exists: Apple compares the declaration with the binary asynchronously."""
    for attempt in range(tries):
        st, cur = api("GET", f"/v1/appStoreVersions/{vid}?fields[appStoreVersions]=usesIdfa")
        if (cur.get("data") or {}).get("attributes", {}).get("usesIdfa") is True:
            print("  = usesIdfa true (IDFA beyani) — geri okundu")
            return
        st, r = api("PATCH", f"/v1/appStoreVersions/{vid}", {"data": {
            "type": "appStoreVersions", "id": vid, "attributes": {"usesIdfa": True}}})
        if st != 200:
            print(f"  ... usesIdfa PATCH HTTP {st}: {json.dumps(r)[:300]} — {attempt + 1}/{tries}")
        time.sleep(5)
    sys.exit("!! usesIdfa=true yazilamadi / geri okunamadi. Submit EDILMEDI (INVALID_BINARY riski).")


def resolve_bundle(e, slug, bundle=None):
    """Bundle id. Default = the factory formula BUNDLE_PREFIX.slug (unchanged for every app);
    --bundle overrides it for an app whose bundle does not follow its folder slug."""
    return bundle or f'{e["BUNDLE_PREFIX"]}.{slug}'


# Non-subscription IAP states (spec 4.5 InAppPurchaseState).
IAP_SETTLED = ("APPROVED", "DEVELOPER_REMOVED_FROM_SALE", "REMOVED_FROM_SALE",
               "PENDING_BINARY_APPROVAL")                      # reviewed already: no item needed
IAP_NEVER_READY = ("MISSING_METADATA", "WAITING_FOR_UPLOAD", "PROCESSING_CONTENT")  # a cancel cannot fix
IAP_VERSION_EDITABLE = ("PREPARE_FOR_SUBMISSION", "READY_FOR_REVIEW", "DEVELOPER_REJECTED", "REJECTED")


def list_iaps(api, app_id):
    """Consumable / non-consumable / non-renewing IAPs of the app (never subscriptions).
    Fail-closed: if the list cannot be read, we cannot prove the shop is complete -> no submit."""
    out, path = [], (f"/v1/apps/{app_id}/inAppPurchasesV2?limit=200"
                     "&fields[inAppPurchases]=productId,state,inAppPurchaseType")
    while path:
        for attempt in range(3):
            st, r = api("GET", path)
            if st == 200:
                break
            time.sleep(3)
        else:
            sys.exit(f"!! IAP listesi okunamadi (HTTP {st}) — IAP'siz submit riski. SUBMIT IPTAL.")
        out += r.get("data") or []
        nxt = (r.get("links") or {}).get("next")
        path = nxt.split("appstoreconnect.apple.com")[1] if nxt else None
    return out


def iap_versions_to_submit(api, app_id):
    """One pass: [(iap_id, productId, version_id)] ready to submit, and [(productId, why)] not ready."""
    ready, not_ready = [], []
    for i in list_iaps(api, app_id):
        a = i["attributes"]
        if a.get("state") in IAP_SETTLED:
            continue
        if a.get("state") != "READY_TO_SUBMIT":
            not_ready.append((a.get("productId"), a.get("state")))
            continue
        st, vs = api("GET", f"/v2/inAppPurchases/{i['id']}/versions?limit=20")
        vid = next((v["id"] for v in (vs.get("data") or []) if st == 200
                    and v["attributes"].get("state") in IAP_VERSION_EDITABLE), None)
        if vid:
            ready.append((i["id"], a.get("productId"), vid))
        else:
            not_ready.append((a.get("productId"), f"READY_TO_SUBMIT but no editable version (HTTP {st})"))
    return ready, not_ready


class _ReadOnly:
    """--dry-run: the same API object, but any non-GET raises before it reaches the network."""

    def __init__(self, api):
        self.api, self.gets = api, 0

    def __call__(self, method, path, body=None):
        if method != "GET":
            raise RuntimeError(f"dry-run refused {method} {path}")
        self.gets += 1
        return self.api(method, path, body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--bundle", help="bundle id when it does not follow the slug "
                                     "(default: BUNDLE_PREFIX.slug)")
    ap.add_argument("--dry-run", action="store_true",
                    help="GET only: read app/version/build/IAP state, print the plan, write nothing")
    ap.add_argument("--uses-idfa", action="store_true",
                    help="the app links an ad-attribution SDK (Meta): PATCH the version's usesIdfa=true and read it "
                         "back BEFORE the review submission is created (else INVALID_BINARY). Default: untouched")
    args = ap.parse_args()

    e = env()
    api = API(make_token(e))
    if args.dry_run:
        api = _ReadOnly(api)
    bundle = resolve_bundle(e, args.slug, args.bundle)

    st, apps = api("GET", f"/v1/apps?filter[bundleId]={bundle}")
    if not apps.get("data"):
        sys.exit(f"!! ASC'de app yok: {bundle}")
    app_id = apps["data"][0]["id"]

    # 0a. Trial tutarliligi — config vaadi ile ASC gercegi uyusmuyorsa submit YOK.
    verify_trial_offers(api, args.slug, bundle, app_id)

    # 0a2. IAP on-kontrolu (DAHA HICBIR SEYE DOKUNMADAN): onaylanmamis bir IAP'in metadata'si
    # eksikse (MISSING_METADATA: review screenshot / localization / fiyat yok) bir cancel onu
    # duzeltemez — dukkani bos bir app gondermektense simdi dur.
    iaps0 = list_iaps(api, app_id)
    pending0 = [i for i in iaps0 if i["attributes"].get("state") not in IAP_SETTLED]
    never = [(i["attributes"].get("productId"), i["attributes"].get("state"))
             for i in pending0 if i["attributes"].get("state") in IAP_NEVER_READY]
    if never:
        sys.exit(f"!! {len(never)} IAP READY_TO_SUBMIT degil: {never}\n"
                 "   Once: python3 scripts/asc_consumables.py ... --screenshot <shop.png> (READY_TO_SUBMIT "
                 "olana kadar). SUBMIT IPTAL — hicbir seye dokunulmadi.")
    if iaps0:
        print(f"  IAP: {len(iaps0)} toplam, {len(pending0)} onaylanmamis "
              f"({sorted({i['attributes'].get('state') for i in pending0})})")

    # 0. Ilk submit app-level zorunluluklari (content rights + free pricing).
    if not args.dry_run:
        ensure_submission_prereqs(api, app_id)

    # 1. version + build
    # filter[platform]=IOS is not optional: an app that ever had a macOS/Catalyst version
    # record keeps it forever (ASC refuses to delete any version once a build exists for the
    # platform), and an unfiltered query can hand back that MAC_OS row instead of the iOS one.
    # The failure then reads as "build could not be attached / version still locked", because
    # an iOS build genuinely cannot attach to a macOS version. (partylights, 2026-09-01.)
    st, vers = api("GET", f"/v1/apps/{app_id}/appStoreVersions"
                   "?filter[platform]=IOS&limit=1&include=build")
    ver = vers["data"][0]
    vid = ver["id"]
    print(f"app {app_id}  version {ver['attributes']['versionString']} "
          f"({ver['attributes']['appStoreState']})")
    # NOTE: the build is attached AFTER the open submission is cancelled (step 2b2).
    # A version in WAITING_FOR_REVIEW is LOCKED — the relationships/build PATCH fails,
    # and because the old code ignored the response status it printed "build eklendi"
    # while the version silently kept the PREVIOUS binary, so the whole resubmission
    # shipped the unfixed build. (Burned 9 apps on 2026-08-07.) Only check here that a
    # VALID build exists at all, so we fail early rather than after cancelling.
    attached = (ver.get("relationships", {}).get("build", {}) or {}).get("data")
    st, builds = api("GET",
        f"/v1/builds?filter[app]={app_id}&filter[processingState]=VALID"
        "&sort=-uploadedDate&limit=1")
    if not builds.get("data") and not attached:
        sys.exit("!! version'a build ekli degil ve VALID build yok — "
                 "build islenene kadar bekle (fastlane release sonrasi ~5-15 dk).")

    if args.dry_run:
        # Read-only plan: nothing above wrote (ensure_submission_prereqs skipped), nothing below runs.
        newest_no = (builds.get("data") or [{}])[0].get("attributes", {}).get("version")
        print(f"[dry-run] newest VALID build: {newest_no}; attached now: "
              f"{(attached or {}).get('id', '-')}")
        ready, not_ready = iap_versions_to_submit(api, app_id) if pending0 else ([], [])
        for _, pid, iap_vid in ready:     # not `vid`: that is the App Store version the usesIdfa probe below reads
            print(f"[dry-run] + inAppPurchaseVersion {pid} ({iap_vid[:8]})")
        for pid, why in not_ready:
            print(f"[dry-run] !! {pid}: {why} (a real run re-polls ~3 min after the cancel, then exits)")
        if args.uses_idfa:
            st, cur = api("GET", f"/v1/appStoreVersions/{vid}?fields[appStoreVersions]=usesIdfa")
            print(f"[dry-run] usesIdfa now: {(cur.get('data') or {}).get('attributes', {}).get('usesIdfa')!r} "
                  "(a real run PATCHes it to true and reads it back before the review submission)")
        st, subs0 = api("GET", f"/v1/apps/{app_id}/reviewSubmissions?limit=20")
        print(f"[dry-run] open review submissions: "
              f"{[r['attributes']['state'] for r in subs0.get('data', [])]}")
        print(f"[dry-run] {api.gets} GET, 0 writes. Nothing was changed.")
        return

    # 2. open review submissions -> clear.
    #  - WAITING_FOR_REVIEW / UNRESOLVED_ISSUES  -> `canceled: true`. Canceling is
    #    what properly RELEASES a rejected submission's items: it flips REJECTED /
    #    IN_REVIEW sub + group versions to DEVELOPER_REJECTED (re-submittable) and
    #    frees the appStoreVersion. (Deleting an UNRESOLVED_ISSUES submission's
    #    items does NOT convert those states, so the resubmit picks up 0 subs.)
    #  - READY_FOR_REVIEW (built-but-not-submitted) can't be canceled (409 "not in
    #    cancellable state") and would LOCK the appStoreVersion
    #    ("ITEM_PART_OF_ANOTHER_SUBMISSION"), so DELETE its items instead.
    st, subs = api("GET", f"/v1/apps/{app_id}/reviewSubmissions?limit=20")
    for r in subs.get("data", []):
        state = r["attributes"]["state"]
        if state in ("WAITING_FOR_REVIEW", "UNRESOLVED_ISSUES"):
            api("PATCH", f"/v1/reviewSubmissions/{r['id']}",
                {"data": {"type": "reviewSubmissions", "id": r["id"],
                          "attributes": {"canceled": True}}})
            print(f"  eski submission iptal edildi: {r['id'][:8]} ({state})")
        elif state == "READY_FOR_REVIEW":
            sti, items = api("GET", f"/v1/reviewSubmissions/{r['id']}/items?limit=50")
            for it in items.get("data", []):
                api("DELETE", f"/v1/reviewSubmissionItems/{it['id']}")
            print(f"  eski submission bosaltildi: {r['id'][:8]} ({len(items.get('data', []))} item)")
    # cancel/temizligin oturmasi icin kisa bekleme (rejected->DEVELOPER_REJECTED gecisi)
    time.sleep(10)

    # 2b2. NOW attach the newest VALID build — the version is editable only after the
    # cancel above has propagated (WAITING_FOR_REVIEW -> CANCELING -> DEVELOPER_REJECTED,
    # a few minutes). Retry until the PATCH really lands, then VERIFY by reading the
    # relationship back. Never trust the PATCH's own 2xx alone, and never proceed to
    # submit with the wrong binary attached.
    if builds.get("data"):
        newest = builds["data"][0]["id"]
        newest_no = builds["data"][0]["attributes"].get("version")
        for attempt in range(30):                       # ~5 min
            st, cur = api("GET", f"/v1/appStoreVersions/{vid}/build")
            if (cur.get("data") or {}).get("id") == newest:
                print(f"  = build {newest_no} ({newest[:8]}) version'a bagli — dogrulandi")
                break
            api("PATCH", f"/v1/appStoreVersions/{vid}/relationships/build",
                {"data": {"type": "builds", "id": newest}})
            time.sleep(10)
        else:
            sys.exit(f"!! build {newest_no} version'a BAGLANAMADI (version hala kilitli "
                     f"olabilir). Submit edilmedi — tekrar calistir.")

    # 2c. IDFA beyani (--uses-idfa): version editable (cancel yayildi, build bagli) ve reviewSubmission henuz YOK.
    if args.uses_idfa:
        set_uses_idfa(api, vid)

    # 2b. Mukerrer screenshot temizligi. deliver, 500 retry / yarim kalan yukleme
    # sonrasi ayni fileName'i tekrar yukleyip 5 yerine 9 gorsel birakabiliyor;
    # submit oncesi (version editable iken) fazlaliklari sil.
    st, vers0 = api("GET", f"/v1/apps/{app_id}/appStoreVersions?limit=1")
    vid0 = vers0["data"][0]["id"]
    st, locs0 = api("GET", f"/v1/appStoreVersions/{vid0}/appStoreVersionLocalizations?limit=50")
    removed = 0
    for L in locs0.get("data", []):
        st, sets0 = api("GET", f"/v1/appStoreVersionLocalizations/{L['id']}/appScreenshotSets")
        for s in sets0.get("data", []):
            st, shots0 = api("GET", f"/v1/appScreenshotSets/{s['id']}/appScreenshots")
            seen = set()
            for sh in shots0.get("data", []):
                fn = sh["attributes"].get("fileName")
                if fn in seen:
                    api("DELETE", f"/v1/appScreenshots/{sh['id']}")
                    removed += 1
                else:
                    seen.add(fn)
    if removed:
        print(f"  + {removed} mukerrer screenshot silindi (5 kaldi)")

    # 3. subscription group version + subscription versions (varsa)
    #
    # DIKKAT (2026-08-20, stopdog): step 2'deki cancel'in ardindan sub/group
    # versiyonlari ANINDA editable OLMUYOR — REJECTED/IN_REVIEW -> DEVELOPER_REJECTED
    # gecisi dakikalar alabiliyor. Tek seferlik okuma yapilirsa hepsi "editable degil"
    # gorunur, script sessizce 0 abonelik bulur ve app version'i ABONELIKSIZ submit
    # edilir => app onaylansa bile paywall'da satin alinacak hicbir sey olmaz.
    # Bu yuzden editable bir grup versiyonu cikana kadar YENIDEN DENE; grup zaten
    # onayliysa (bundle gerekmez) hemen cik.
    EDITABLE = ("PREPARE_FOR_SUBMISSION", "READY_FOR_REVIEW",
                "DEVELOPER_ACTION_NEEDED", "DEVELOPER_REJECTED", "REJECTED")
    SETTLED = ("APPROVED", "LIVE", "READY_FOR_SALE", "REPLACED")   # bundle gerekmez
    group_version_id = None
    sub_version_ids = []
    st, groups = api("GET", f"/v1/apps/{app_id}/subscriptionGroups")
    if groups.get("data"):
        gid = groups["data"][0]["id"]
        for attempt in range(18):                      # ~3 dk
            group_version_id, sub_version_ids = None, []
            st, gvs = api("GET", f"/v1/subscriptionGroups/{gid}/versions?limit=5")
            gstates = [gv["attributes"]["state"] for gv in gvs.get("data", [])]
            for gv in gvs.get("data", []):
                if gv["attributes"]["state"] in EDITABLE:
                    group_version_id = gv["id"]
                    break
            st, gsubs = api("GET", f"/v1/subscriptionGroups/{gid}/subscriptions?limit=50")
            sub_count = len(gsubs.get("data", []))
            for s in gsubs.get("data", []):
                svid = None
                st, svs = api("GET", f"/v1/subscriptions/{s['id']}/versions?limit=3")
                for sv in svs.get("data", []):
                    if sv["attributes"]["state"] in EDITABLE:
                        svid = sv["id"]
                        break
                if svid:
                    sub_version_ids.append(svid)
            if group_version_id and sub_version_ids:
                break                                   # bundle edilecek her sey hazir
            if any(g in SETTLED for g in gstates) and not group_version_id:
                break                                   # grup zaten onayli — bundle yok
            print(f"  ... sub/group versiyonlari henuz editable degil {gstates} "
                  f"(cancel yayiliyor) — {attempt + 1}/18")
            time.sleep(10)
        print(f"  subscription group {gid}: group_version={bool(group_version_id)} "
              f"sub_versions={len(sub_version_ids)}")
        if sub_count and not sub_version_ids and not any(g in SETTLED for g in gstates):
            sys.exit("!! abonelikler submit'e EKLENEMEDI (hala editable degil). Submit "
                     "EDILMEDI — app'i aboneliksiz gondermektense birkac dk sonra tekrar "
                     "calistir.")

    # 3b. IAP versiyonlari (consumable/non-consumable). Yalniz on-kontrolde onaylanmamis IAP
    # varsa calisir (aboneli fabrika app'lerinde bu blok hic calismaz). Cancel'in yayilmasi
    # dakikalar surebildigi icin abonelikteki gibi ~3 dk yeniden dener; sonunda HER onaylanmamis
    # IAP READY_TO_SUBMIT + editable versiyonlu degilse submit YOK.
    iap_items = []
    if pending0:
        for attempt in range(18):                      # ~3 dk
            iap_items, iap_not_ready = iap_versions_to_submit(api, app_id)
            if not iap_not_ready:
                break
            print(f"  ... IAP'ler henuz hazir degil {iap_not_ready[:4]} — {attempt + 1}/18")
            time.sleep(10)
        else:
            sys.exit(f"!! {len(iap_not_ready)} IAP READY_TO_SUBMIT degil: {iap_not_ready}\n"
                     "   Submit EDILMEDI — dukkani bos bir app gondermektense dur.")
        print(f"  IAP versiyonlari: {len(iap_items)} submit'e girecek")

    # 4. create submission
    rs_id = None
    for _ in range(10):
        st, r = api("POST", "/v1/reviewSubmissions", {"data": {
            "type": "reviewSubmissions", "attributes": {"platform": "IOS"},
            "relationships": {"app": {"data": {"type": "apps", "id": app_id}}}}})
        if st in (200, 201):
            rs_id = r["data"]["id"]
            break
        time.sleep(6)
    if not rs_id:
        sys.exit("!! reviewSubmission olusturulamadi")
    print(f"  reviewSubmission {rs_id}")

    # 5. items: appStoreVersion (retry — cancel propagation), then IAP items
    for _ in range(20):
        st, r = item(api, rs_id, "appStoreVersion", "appStoreVersions", vid)
        if st in (200, 201):
            print("  + appStoreVersion")
            break
        time.sleep(8)
    else:
        sys.exit("!! appStoreVersion item eklenemedi")
    if group_version_id:
        st, r = item(api, rs_id, "subscriptionGroupVersion", "subscriptionGroupVersions", group_version_id)
        print("  + subscriptionGroupVersion" if st in (200, 201) else f"  !! groupVersion {st}: {r}")
    for svid in sub_version_ids:
        st, r = item(api, rs_id, "subscriptionVersion", "subscriptionVersions", svid)
        print(f"  + subscriptionVersion {svid[:8]}" if st in (200, 201)
              else f"  !! subVersion {st}: {json.dumps(r)[:200]}")
    iap_failed = []
    for _, pid, ivid in iap_items:
        st, r = item(api, rs_id, "inAppPurchaseVersion", "inAppPurchaseVersions", ivid)
        if st in (200, 201):
            print(f"  + inAppPurchaseVersion {pid}")
        else:
            iap_failed.append(pid)
            print(f"  !! inAppPurchaseVersion {pid} {st}: {json.dumps(r)[:400]}")
    if iap_failed:
        # Not submitted: the open (READY_FOR_REVIEW) submission is emptied by step 2 next run.
        sys.exit(f"!! {len(iap_failed)} IAP submission'a eklenemedi: {iap_failed}. Submit EDILMEDI.")

    # 6. submit
    st, r = api("PATCH", f"/v1/reviewSubmissions/{rs_id}",
                {"data": {"type": "reviewSubmissions", "id": rs_id,
                          "attributes": {"submitted": True}}})
    if st != 200:
        print(f"\n!! SUBMIT HTTP {st}\n{json.dumps(r, indent=2)[:1200]}")
        sys.exit(1)
    print(f"\nOK. reviewSubmission -> {r['data']['attributes']['state']}")
    if args.uses_idfa:
        print("  !! --uses-idfa: Apple'in binary dogrulamasi ASENKRON — version'i en az 15 dk izle; INVALID_BINARY olursa "
              "build'i ayir/yeniden bagla (memory idfa-declaration-and-invalid-binary)")
    if iap_items:
        # Read back what Apple actually holds (never trust the POSTs): IAP items in the submission.
        # limit[items]=50: included to-many lists are capped otherwise (13+ items with IAPs).
        st, rs = api("GET", f"/v1/reviewSubmissions/{rs_id}?include=items&limit[items]=50")
        n_items = len([x for x in rs.get("included") or [] if x.get("type") == "reviewSubmissionItems"])
        want = 1 + (1 if group_version_id else 0) + len(sub_version_ids) + len(iap_items)
        print(f"  submission items (read back): {n_items} (beklenen {want}: version + "
              f"{len(sub_version_ids)} sub + {len(iap_items)} IAP)")
        if n_items != want:
            print("  !! item sayisi uyusmuyor — IAP versiyon durumlarini ASC'den bagimsiz kontrol et")


if __name__ == "__main__":
    main()
