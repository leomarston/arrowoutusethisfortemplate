#!/usr/bin/env python3
"""Cihazsiz (device-free) App Store imzalama kurulumu — App Manager API key yeterli.

Xcode'un cloud signing'i Admin key ister; ham ASC API istemez. Bu script:
  1. Apple Distribution sertifikasi: ~/keys/signing/dist.{key,cer,id} varsa ve ASC'de
     hala geciliyse yeniden kullanir; yoksa CSR uretir, API'yle olusturur, keychain'e yukler.
  2. Bundle ID kaydini garantiler (yoksa acar).
  3. "manycode <slug> appstore" IOS_APP_STORE profili olusturur/yeniler ve
     ~/Library/MobileDevice/Provisioning Profiles/ altina kurar.

Kullanim: python3 scripts/signing_setup.py --slug <slug>
          [--bundle <id>] [--profile-name "manycode <x> appstore"]   (additive, 2026-09-28:
          bundle'i slug'dan turemeyen app icin; verilmezse eski formul aynen: BUNDLE_PREFIX.slug
          ve "manycode <slug> appstore". --slug yine apps/<slug>/App/*.entitlements'i bulur.)
Sonrasi: fastlane release (gym arsivi imzasiz alir, export'ta manual imzalar).
"""
import argparse, base64, json, os, re, secrets, ssl, subprocess, sys, time
from pathlib import Path
from urllib import request, error
from urllib.parse import quote

import certifi
import jwt

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://api.appstoreconnect.apple.com"
# Portable: signing material lives inside the repo (keys/signing), so the
# Distribution cert + private key travel with the project. Falls back to the
# legacy ~/keys/signing only if the repo copy doesn't exist.
SIGN_DIR = (ROOT / "keys" / "signing") if (ROOT / "keys" / "signing").exists() \
    else Path(os.path.expanduser("~/keys/signing"))
_SSL_CTX = ssl.create_default_context(cafile=certifi.where())


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


def call(tok, method, path, body=None, ok=(200, 201), allow=()):
    req = request.Request(BASE + path, method=method,
                          data=json.dumps(body).encode() if body else None,
                          headers={"Authorization": f"Bearer {tok}",
                                   "Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=60, context=_SSL_CTX) as r:
            return r.status, json.load(r) if r.status != 204 else {}
    except error.HTTPError as ex:
        if ex.code in allow:
            return ex.code, json.loads(ex.read().decode() or "{}")
        print(f"!! {method} {path} -> HTTP {ex.code}\n{ex.read().decode()[:400]}")
        sys.exit(1)


def ensure_certificate(tok):
    """Yerel key'le eslesen gecerli Distribution sertifikasi dondurur (id)."""
    SIGN_DIR.mkdir(parents=True, exist_ok=True)
    id_file = SIGN_DIR / "dist.id"
    if id_file.exists():
        cid = id_file.read_text().strip()
        st, d = call(tok, "GET", f"/v1/certificates/{cid}", allow=(404,))
        if st == 200:
            print(f"  = sertifika mevcut ({cid})")
            return cid
        print("  ~ kayitli sertifika ASC'de yok; yenisi olusturulacak")
    key_p, csr_p, cer_p = SIGN_DIR / "dist.key", SIGN_DIR / "dist.csr", SIGN_DIR / "dist.cer"
    subprocess.run(["openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes",
                    "-keyout", str(key_p), "-out", str(csr_p),
                    "-subj", "/CN=Manycode Distribution"], check=True, capture_output=True)
    st, d = call(tok, "POST", "/v1/certificates",
                 {"data": {"type": "certificates",
                           "attributes": {"certificateType": "DISTRIBUTION",
                                          "csrContent": csr_p.read_text()}}})
    cid = d["data"]["id"]
    cer_p.write_bytes(base64.b64decode(d["data"]["attributes"]["certificateContent"]))
    id_file.write_text(cid)
    for f in (key_p, cer_p):
        subprocess.run(["security", "import", str(f), "-k",
                        os.path.expanduser("~/Library/Keychains/login.keychain-db"),
                        "-T", "/usr/bin/codesign"], capture_output=True)
    print(f"  + sertifika olusturuldu ve keychain'e yuklendi ({cid})")
    return cid


def ensure_bundle_id(tok, bundle):
    st, d = call(tok, "GET", f"/v1/bundleIds?filter[identifier]={quote(bundle)}")
    for x in d.get("data", []):
        if x["attributes"]["identifier"] == bundle:
            return x["id"]
    st, d = call(tok, "POST", "/v1/bundleIds",
                 {"data": {"type": "bundleIds",
                           "attributes": {"name": bundle.split(".")[-1].capitalize(),
                                          "identifier": bundle, "platform": "IOS"}}})
    print(f"  + bundle ID kaydedildi ({bundle})")
    return d["data"]["id"]


def ensure_capabilities(tok, bundle_res_id, slug):
    """App ID uzerinde app'in ENTITLEMENT'larina karsilik gelen capability'leri acar.

    Bir capability App ID'de kapali oldugu surece profil o entitlement'i TASIMAZ; build
    imzalanir ama app calistiginda CloudKit/push sessizce calismaz veya
    "Provisioning profile doesn't include the ... entitlement" ile export patlar.

    Su an fabrikada .entitlements tasiyan app YOK, yani bu fonksiyon 33 app icin no-op.
    CloudKit/push isteyen bir app eklenirse kendiliginden dogru capability'yi acar.

    Kaynak app'in kendi .entitlements dosyasi — tahmin degil. Boylece capability listesi
    app degistikce otomatik dogru kalir.
    """
    # Dosya adi app'in scheme adini takip ediyor (Kin.entitlements), o yuzden glob.
    found = sorted((ROOT / "apps" / slug / "App").glob("*.entitlements"))
    if not found:
        # Cogu fabrika app'inin entitlement'i yok; o zaman acilacak bir sey de yok.
        return
    body = "\n".join(f.read_text() for f in found)
    wanted = []
    if "com.apple.developer.icloud-services" in body:
        wanted.append("ICLOUD")
    if "aps-environment" in body:
        wanted.append("PUSH_NOTIFICATIONS")
    if not wanted:
        return

    st, d = call(tok, "GET", f"/v1/bundleIds/{bundle_res_id}/bundleIdCapabilities")
    existing = {x.get("attributes", {}).get("capabilityType") for x in d.get("data", [])}
    for cap in wanted:
        if cap in existing:
            print(f"  = capability mevcut ({cap})")
            continue
        payload = {"data": {"type": "bundleIdCapabilities",
                            "attributes": {"capabilityType": cap},
                            "relationships": {"bundleId": {"data": {"type": "bundleIds",
                                                                    "id": bundle_res_id}}}}}
        # iCloud icin Apple ayrica "CloudKit kullaniyorum" secimini ister; settings olmadan
        # capability aciliyor ama CloudKit isaretlenmiyor.
        if cap == "ICLOUD":
            payload["data"]["attributes"]["settings"] = [{
                "key": "ICLOUD_VERSION",
                "options": [{"key": "XCODE_6"}]}]
        st, _ = call(tok, "POST", "/v1/bundleIdCapabilities", payload, ok=(200, 201, 409))
        print(f"  + capability acildi ({cap})" if st in (200, 201)
              else f"  = capability zaten acik ({cap})")


def ensure_profile(tok, name, bundle_res_id, cert_id):
    st, d = call(tok, "GET",
                 f"/v1/profiles?filter[profileType]=IOS_APP_STORE&filter[name]={quote(name)}"
                 "&fields[profiles]=name,profileState,profileContent")
    for p in d.get("data", []):
        if p["attributes"]["profileState"] == "ACTIVE":
            print(f"  = profil mevcut ({name})")
            return p
        call(tok, "DELETE", f"/v1/profiles/{p['id']}", ok=(204,))
        print("  ~ INVALID profil silindi, yenisi olusturuluyor")
    st, d = call(tok, "POST", "/v1/profiles", {"data": {
        "type": "profiles",
        "attributes": {"name": name, "profileType": "IOS_APP_STORE"},
        "relationships": {
            "bundleId": {"data": {"type": "bundleIds", "id": bundle_res_id}},
            "certificates": {"data": [{"type": "certificates", "id": cert_id}]}}}})
    print(f"  + profil olusturuldu ({name})")
    return d["data"]


def install_profile(p):
    content = base64.b64decode(p["attributes"]["profileContent"])
    uuid = re.search(rb"<key>UUID</key>\s*<string>([-A-F0-9a-f]+)</string>", content).group(1).decode()
    dest = Path(os.path.expanduser("~/Library/MobileDevice/Provisioning Profiles"))
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{uuid}.mobileprovision").write_bytes(content)
    print(f"  kuruldu: {uuid}.mobileprovision")


SIGN_KEYCHAIN = Path(os.path.expanduser("~/Library/Keychains/manycode-signing.keychain-db"))


def ensure_keychain_access():
    """Guarantee `codesign` can use the Distribution private key non-interactively.

    Uses a DEDICATED keychain whose password lives in keys/signing/keychain.pass,
    so it needs no GUI login-keychain password and travels to any Mac after unzip.
    The crucial step is `set-key-partition-list`: without it, macOS returns
    `errSecInternalComponent` from codesign during `fastlane release` export.
    Idempotent — safe to run every time.
    """
    pass_file = SIGN_DIR / "keychain.pass"
    pw = pass_file.read_text().strip() if pass_file.exists() else secrets.token_urlsafe(16)
    if not pass_file.exists():
        pass_file.write_text(pw)
    kc = str(SIGN_KEYCHAIN)
    cer, key = SIGN_DIR / "dist.cer", SIGN_DIR / "dist.key"
    # Every `security` call runs with stdin closed and a timeout: if macOS ever decides
    # a step needs a GUI/tty password it fails fast instead of hanging the whole pipeline.
    def sec(*args):
        try:
            return subprocess.run(["security", *args], capture_output=True,
                                  stdin=subprocess.DEVNULL, timeout=60)
        except subprocess.TimeoutExpired:
            print(f"  ! security {args[0]} timed out (wanted an interactive password)")
            return None

    if not SIGN_KEYCHAIN.exists():
        sec("create-keychain", "-p", pw, kc)
    # Unlock FIRST — `set-keychain-settings` on a locked keychain prompts for the
    # password on the GUI and blocks forever with no output.
    sec("unlock-keychain", "-p", pw, kc)
    sec("set-keychain-settings", "-lut", "21600", kc)
    if cer.exists():
        sec("import", str(cer), "-k", kc, "-T", "/usr/bin/codesign", "-T", "/usr/bin/security")
    if key.exists():
        sec("import", str(key), "-k", kc, "-P", "",
            "-T", "/usr/bin/codesign", "-T", "/usr/bin/security")
    # Grant codesign non-interactive access to the imported key.
    sec("set-key-partition-list", "-S", "apple-tool:,apple:,codesign:", "-s", "-k", pw, kc)
    # Search list = EXACTLY [signing, login], every time — not "append if missing".
    #
    # Older factory runs left a `manycode-build.keychain-db` holding a COPY of the same
    # "Apple Distribution: ..." certificate whose private-key ACL does not grant codesign
    # access. Sitting earlier in the search list, that copy is the one codesign resolves to,
    # and it fails with errSecInternalComponent — even when the identity is pinned by SHA-1,
    # because the hash matches both copies. Rewriting the list unconditionally evicts any
    # such shadow. (rfdetector, 2026-08-03.)
    login = os.path.expanduser("~/Library/Keychains/login.keychain-db")
    cur = subprocess.run(["security", "list-keychains", "-d", "user"],
                         capture_output=True, text=True).stdout
    shadows = [ln.strip().strip('"') for ln in cur.splitlines()
               if "manycode-" in ln and SIGN_KEYCHAIN.name not in ln]
    sec("list-keychains", "-d", "user", "-s", kc, login)
    if shadows:
        print(f"  + arama listesinden cikarildi (codesign'i golgeliyordu): {', '.join(os.path.basename(s) for s in shadows)}")
    print("  + codesign keychain erisimi hazir (partition-list set)")


def resolve_bundle(e, slug, bundle=None):
    """Bundle id. Default = the factory formula BUNDLE_PREFIX.slug (unchanged for every app);
    --bundle overrides it for an app whose bundle does not follow its folder slug
    (apps/mazeout ships as com.manycode.arrowout)."""
    return bundle or f'{e["BUNDLE_PREFIX"]}.{slug}'


def resolve_profile_name(slug, profile_name=None):
    """Must equal the Fastfile's provisioningProfiles value ("manycode __APP_ID__ appstore")."""
    return profile_name or f"manycode {slug} appstore"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--bundle", help="bundle id when it does not follow the slug "
                                     "(default: BUNDLE_PREFIX.slug)")
    ap.add_argument("--profile-name", help="provisioning profile name when the Fastfile's differs "
                                           "(default: 'manycode <slug> appstore')")
    args = ap.parse_args()
    e = env()
    bundle = resolve_bundle(e, args.slug, args.bundle)
    tok = token(e)
    print(f"Imzalama kurulumu: {bundle}")
    cert_id = ensure_certificate(tok)
    bid = ensure_bundle_id(tok, bundle)
    # SIRA onemli: profil olusturuldugu anda entitlement setini dondurur, bu yuzden
    # capability'ler profilden once acilmali.
    ensure_capabilities(tok, bid, args.slug)
    profile = ensure_profile(tok, resolve_profile_name(args.slug, args.profile_name), bid, cert_id)
    install_profile(profile)
    ensure_keychain_access()
    print("OK. fastlane release artik imzasiz arsiv + manual export ile calisir.")


if __name__ == "__main__":
    main()
