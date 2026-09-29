#!/usr/bin/env python3
"""Arrow Out store metadata: write it for fastlane, and audit everything T3 STORE owns.

  python3 tools/release/meta.py write [--out DIR]   # design/publish/store/*.json -> fastlane/metadata (default)
  python3 tools/release/meta.py audit [--dir DIR]   # sources + keywords + captions + evidence + IAP (+ a written tree)
  python3 tools/release/meta.py iap-check           # iap.json == rules.json:shop == ArrowOut.storekit
  python3 tools/release/meta.py selftest            # negative controls: every audit rule must catch its mutation

Sources (the truth): design/publish/store/<loc>.json {name, subtitle, promotional_text, description},
design/publish/store/review.json {notes, copyright, categories}, design/keywords.json, design/captions/<loc>.json,
design/publish/aso-evidence.json (tools/release/aso_research.py evidence), design/publish/iap.json.

`write` never writes keywords.txt or release_notes.txt (1.0.0 has no whatsNew; keywords go up with
scripts/asc_keywords.py). URLs are written before the length check (memory locale-urls-before-the-length-check).
Exit code 0 = all green.
"""
import argparse
import json
import re
import shutil
import sys
import tempfile
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import loc as L  # noqa: E402

APP = L.APP


class Paths:
    def __init__(self, root=APP):
        self.root = root
        self.store = root / "design" / "publish" / "store"
        self.keywords = root / "design" / "keywords.json"
        self.captions = root / "design" / "captions"
        self.evidence = root / "design" / "publish" / "aso-evidence.json"
        self.iap = root / "design" / "publish" / "iap.json"
        self.rules = root / "App" / "Resources" / "Tuning" / "rules.json"
        self.storekit = root / "App" / "Resources" / "StoreKit" / "ArrowOut.storekit"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def nfc(s):
    return unicodedata.normalize("NFC", s)


class Report:
    def __init__(self, quiet=False):
        self.errors, self.warnings, self.quiet = [], [], quiet

    def err(self, msg):
        self.errors.append(msg)
        if not self.quiet:
            print("  !! " + msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def ok(self):
        return not self.errors


# ------------------------------------------------------------------------------------------ store text
def audit_store(P, R):
    fields = list(L.LIM)
    for loc in L.LOCALES:
        f = P.store / f"{loc}.json"
        if not f.exists():
            R.err(f"store/{loc}.json missing")
            continue
        v = load(f)
        for k in fields:
            s = v.get(k)
            if not isinstance(s, str) or not s.strip():
                R.err(f"{loc}: {k} missing/empty")
                continue
            if len(s) > L.LIM[k]:
                R.err(f"{loc}: {k} {len(s)} > {L.LIM[k]}")
            hits = L.banned_hits(s)
            if hits:
                R.err(f"{loc}: {k} has banned {hits}")
            if re.search(r"[{}]|\\n|\s{3,}\S", s.replace("\n\n", "")):
                R.err(f"{loc}: {k} has template debris (braces / literal \\n / run of spaces)")
        name = v.get("name", "")
        if not name.startswith("Arrow Out"):
            R.err(f"{loc}: name must start with the seed 'Arrow Out' (got {name!r})")
        hits = L.banned_hits(name, L.BANNED_NAME)
        if hits:
            R.err(f"{loc}: name has banned {hits}")
        if loc == "en-US" and name != L.NAME_EN:
            R.err(f"en-US name {name!r} != ruling 38 {L.NAME_EN!r}")
        d = v.get("description", "")
        for url in (L.PRIVACY, L.EULA):
            if url not in d:
                R.err(f"{loc}: description lacks {url}")
        if "arrow out" not in d.casefold():
            R.err(f"{loc}: description never names the app")
    rv = P.store / "review.json"
    if not rv.exists():
        R.err("store/review.json missing")
    else:
        r = load(rv)
        n = r.get("notes", "")
        if not n or len(n) > L.REVIEW_NOTES_LIMIT:
            R.err(f"review notes empty or > {L.REVIEW_NOTES_LIMIT}")
        # brand + online bans apply; the review note may say 'Restore' and must say the two ruling-38 facts
        hits = L.banned_hits(n)
        if hits:
            R.err(f"review notes have banned {hits}")
        for must in ("consumable", "no Restore Purchases", "run entirely on the device"):
            if must.casefold() not in n.casefold():
                R.err(f"review notes must say {must!r} (ruling 38)")
        if r.get("copyright") != L.COPYRIGHT:
            R.err(f"copyright {r.get('copyright')!r} != {L.COPYRIGHT!r}")


# ------------------------------------------------------------------------------------------ keywords
def phrases(line):
    return line.split(",")


def is_latin(s):
    return all(ord(c) < 0x2E80 for c in s)


def audit_keywords(P, R):
    kw = load(P.keywords)
    if sorted(kw) != sorted(L.LOCALES):
        R.err(f"keywords.json locales {sorted(kw)} != the 13 {sorted(L.LOCALES)}")
    for loc, line in kw.items():
        if len(line) > L.KEYWORDS_LIMIT:
            R.err(f"{loc}: keywords {len(line)} > {L.KEYWORDS_LIMIT}")
        if ", " in line or line != line.strip():
            R.err(f"{loc}: keywords have a space after a comma / padding (wasted characters)")
        ps = phrases(line)
        if ps[0] != L.SEED:
            R.err(f"{loc}: first keyword {ps[0]!r} != seed {L.SEED!r}")
        if len(ps) < 5:
            R.err(f"{loc}: {len(ps)} keywords < 5 (captions need 5)")
        if len(set(ps)) != len(ps):
            R.err(f"{loc}: duplicate keyword phrase")
        for p in ps:
            if not p.strip():
                R.err(f"{loc}: empty keyword phrase")
            if is_latin(p) and len(p.split()) < 2:
                R.err(f"{loc}: {p!r} is a single word (the rule is long-tail phrases)")
            if is_latin(p) and p != p.casefold():
                R.err(f"{loc}: {p!r} not lower case")
        hits = L.banned_hits(line)
        if hits:
            R.err(f"{loc}: keywords have banned {hits}")
        name_seed = L.SEED
        store = P.store / f"{loc}.json"
        if store.exists() and not load(store)["name"].casefold().startswith(name_seed):
            R.err(f"{loc}: store name does not start with the first keyword")


def audit_captions(P, R):
    kw = load(P.keywords)
    files = sorted(P.captions.glob("*.json"))
    if sorted(f.stem for f in files) != sorted(L.LOCALES):
        R.err(f"captions {sorted(f.stem for f in files)} != the 13 locales")
    for loc in L.LOCALES:
        f = P.captions / f"{loc}.json"
        if not f.exists() or loc not in kw:
            continue
        caps = load(f).get("captions") or []
        if len(caps) != 5:
            R.err(f"captions/{loc}: {len(caps)} captions, need exactly 5")
        want = phrases(kw[loc])[:5]
        for i, c in enumerate(caps[:5]):
            h = nfc(c.get("headline", ""))
            if h.casefold() != nfc(want[i]).casefold():
                R.err(f"captions/{loc} #{i + 1}: {h!r} != keyword {i + 1} {want[i]!r}")
            if c.get("subline", "") != "":
                R.err(f"captions/{loc} #{i + 1}: subline must be empty (keyword only on the image)")
            if L.banned_hits(h):
                R.err(f"captions/{loc} #{i + 1}: banned {L.banned_hits(h)}")


def audit_evidence(P, R):
    if not P.evidence.exists():
        R.err("aso-evidence.json missing (run tools/release/aso_research.py evidence)")
        return
    ev = load(P.evidence)["locales"]
    kw = load(P.keywords)
    for loc, line in kw.items():
        rows = {r["phrase"]: r for r in ev.get(loc, {}).get("keywords", [])}
        for p in phrases(line):
            if p not in rows:
                R.err(f"evidence/{loc}: {p!r} not researched (stale evidence: re-run aso_research.py rank + evidence)")
            elif rows[p]["hint_count"] < 1:
                R.err(f"evidence/{loc}: {p!r} has no autocomplete hint in that storefront")
            elif rows[p].get("arrow_titles_top10") == 0:
                R.warn(f"evidence/{loc}: {p!r} is a head term (0 arrow titles in its top 10)")


# ------------------------------------------------------------------------------------------ IAP
def numbers(s):
    """Every number in a text, thousands separators (, . space NBSP) removed: '60.000 Münzen, je 36' -> [60000, 36]."""
    return [int(re.sub(r"[^\d]", "", m)) for m in re.findall(r"\d{1,3}(?:[.,\u00a0\u202f ]\d{3})+(?!\d)|\d+", s)]


def audit_iap(P, R):
    iap = load(P.iap)
    shop = load(P.rules)["shop"]["products"]
    sk = load(P.storekit)
    prods = iap.get("products", [])
    if [p["id"] for p in prods] != [p["id"] for p in shop]:
        R.err(f"iap.json ids/order != rules.json:shop ({[p['id'] for p in prods]})")
    by_rules = {p["id"]: p for p in shop}
    sk_by_id = {p["productID"]: p for p in sk.get("products", [])}
    if len(sk_by_id) != len(shop):
        R.err(f"ArrowOut.storekit has {len(sk_by_id)} products, rules.json {len(shop)}")
    for p in prods:
        pid = p["id"]
        r = by_rules.get(pid)
        if not r:
            R.err(f"iap {pid}: not in rules.json:shop")
            continue
        if abs(float(p["usd"]) - float(r["usd"])) > 1e-9:
            R.err(f"iap {pid}: usd {p['usd']} != rules.json {r['usd']}")
        if r.get("try") is not None and (p.get("try") is None or abs(float(p["try"]) - float(r["try"])) > 1e-9):
            R.err(f"iap {pid}: try {p.get('try')} != rules.json {r['try']} (T4's TUR golden check reads it)")
        if p.get("grant") != r.get("grant"):
            R.err(f"iap {pid}: grant != rules.json")
        full = "com.manycode.arrowout." + pid
        if p.get("productId") != full:
            R.err(f"iap {pid}: productId {p.get('productId')} != {full}")
        s = sk_by_id.get(full)
        if not s:
            R.err(f"iap {pid}: {full} missing from ArrowOut.storekit")
        else:
            if abs(float(s["displayPrice"]) - float(p["usd"])) > 1e-9:
                R.err(f"iap {pid}: storekit {s['displayPrice']} != usd {p['usd']}")
            if s.get("type") != "Consumable":
                R.err(f"iap {pid}: storekit type {s.get('type')} != Consumable")
        if p.get("type") != "CONSUMABLE":
            R.err(f"iap {pid}: type {p.get('type')} != CONSUMABLE")
        if not p.get("referenceName") or len(p["referenceName"]) > 64:
            R.err(f"iap {pid}: referenceName empty or > 64")
        locs = p.get("locales", {})
        if sorted(locs) != sorted(L.LOCALES):
            R.err(f"iap {pid}: locales {sorted(locs)} != the 13")
        coins = r["grant"]["coins"]
        is_pack = pid.startswith("coins.")
        for lc, t in locs.items():
            n, d = t.get("name", ""), t.get("description", "")
            if not n or len(n) > L.IAP_NAME_LIMIT:
                R.err(f"iap {pid}/{lc}: name {len(n)} chars (1..{L.IAP_NAME_LIMIT})")
            if not d or len(d) > L.IAP_DESC_LIMIT:
                R.err(f"iap {pid}/{lc}: description {len(d)} chars (1..{L.IAP_DESC_LIMIT})")
            if len(d) > 45:
                R.warn(f"iap {pid}/{lc}: description {len(d)} > 45 (fine at the INFERRED 55 limit; T5 fallback if 409)")
            hits = L.banned_hits(n + " " + d)
            if hits:
                R.err(f"iap {pid}/{lc}: banned {hits}")
            nums = numbers(d)
            if coins not in nums:
                R.err(f"iap {pid}/{lc}: the description does not state the coin amount {coins}")
            if is_pack and coins not in numbers(n):
                R.err(f"iap {pid}/{lc}: a coin pack's name must state its amount {coins}")
            rest = list(nums)
            if coins in rest:
                rest.remove(coins)
            b = r["grant"].get("boosters")
            if b and b["freeze"] not in rest:
                R.err(f"iap {pid}/{lc}: booster count {b['freeze']} not stated")
            elif b:
                rest.remove(b["freeze"])
            ul = r["grant"].get("unlimitedLives")
            if ul and ul // 3600 not in rest:
                R.err(f"iap {pid}/{lc}: unlimited-lives hours {ul // 3600} not stated")
            if not b and not ul and rest:
                R.err(f"iap {pid}/{lc}: stray numbers {rest} in a coin-pack description")
    if iap.get("appName") != "Arrow Out":
        R.err("iap appName must be 'Arrow Out' (rc_consumables.py names the RC app from it)")
    if "CHN" not in (iap.get("excludeTerritories") or []):
        R.err("iap excludeTerritories must hold CHN (ruling 38: no China mainland)")
    if iap.get("familySharable") is not False:
        R.err("iap familySharable must be false (consumables)")
    if not iap.get("reviewNote") or L.banned_hits(iap["reviewNote"]):
        R.err("iap reviewNote empty or banned words")


# ------------------------------------------------------------------------------------------ written tree
def audit_written(base, P, R):
    if not base.exists():
        R.warn(f"{base} does not exist yet (T5 scaffolds fastlane/; run `meta.py write` then)")
        return
    for loc in L.LOCALES:
        d = base / loc
        if not d.is_dir():
            R.err(f"written/{loc}: folder missing")
            continue
        src = load(P.store / f"{loc}.json")
        for url_f, url in (("privacy_url.txt", L.PRIVACY), ("support_url.txt", L.SUPPORT)):
            f = d / url_f
            if not f.exists() or f.read_text().strip() != url:
                R.err(f"written/{loc}: {url_f} missing or wrong")
        for k, lim in L.LIM.items():
            f = d / f"{k}.txt"
            if not f.exists():
                R.err(f"written/{loc}: {k}.txt missing")
                continue
            t = f.read_text()
            if len(t) > lim:
                R.err(f"written/{loc}: {k}.txt {len(t)} > {lim}")
            if t != src[k]:
                R.err(f"written/{loc}: {k}.txt differs from design/publish/store/{loc}.json (re-run write)")
        for stray in ("keywords.txt", "release_notes.txt"):
            if (d / stray).exists():
                R.err(f"written/{loc}: {stray} must not exist")
    rv = load(P.store / "review.json")
    notes = base / "review_information" / "notes.txt"
    if not notes.exists() or notes.read_text() != rv["notes"]:
        R.err("written/review_information/notes.txt missing or stale")
    cp = base / "copyright.txt"
    if not cp.exists() or cp.read_text().strip() != L.COPYRIGHT:
        R.err(f"written/copyright.txt missing or != {L.COPYRIGHT!r}")
    extra = sorted(p.name for p in base.iterdir() if p.is_dir() and p.name not in L.LOCALES
                   and p.name != "review_information")
    if extra:
        R.warn(f"written: extra locale folders {extra} (deliver would upload them)")


def audit_no_keywords_txt(root, R):
    found = [str(p.relative_to(root)) for p in root.rglob("keywords.txt") if ".git" not in p.parts]
    if found:
        R.err(f"keywords.txt present (must not exist anywhere): {found}")


def run_audit(P, written=None, quiet=False):
    R = Report(quiet)
    for fn in (audit_store, audit_keywords, audit_captions, audit_evidence, audit_iap):
        try:
            fn(P, R)
        except Exception as e:  # noqa: BLE001 - a crash is a failure, never a pass
            R.err(f"{fn.__name__} crashed: {type(e).__name__}: {e}")
    if written is not None:
        audit_written(written, P, R)
    audit_no_keywords_txt(P.root, R)
    return R


# ------------------------------------------------------------------------------------------ write
def cmd_write(P, out):
    ok = True
    for loc in L.LOCALES:
        v = load(P.store / f"{loc}.json")
        ok = L.write(loc, {k: v[k] for k in L.LIM}, base=out) and ok
    rv = load(P.store / "review.json")
    (out / "review_information").mkdir(parents=True, exist_ok=True)
    (out / "review_information" / "notes.txt").write_text(rv["notes"])
    (out / "copyright.txt").write_text(rv["copyright"])
    print(f"wrote {len(L.LOCALES)} locales + review notes + copyright to {out}")
    return ok


# ------------------------------------------------------------------------------------------ selftest
def selftest():
    """Each mutation must turn the audit red; the clean copy must be green. Runs on a temp copy."""
    tmp = Path(tempfile.mkdtemp(prefix="arrowout-meta-"))
    try:
        def fresh():
            root = tmp / "app"
            if root.exists():
                shutil.rmtree(root)
            for rel in ("design/publish/store", "design/captions"):
                shutil.copytree(APP / rel, root / rel)
            for rel in ("design/keywords.json", "design/publish/aso-evidence.json", "design/publish/iap.json",
                        "App/Resources/Tuning/rules.json", "App/Resources/StoreKit/ArrowOut.storekit"):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(APP / rel, root / rel)
            return Paths(root)

        def edit_json(path, fn):
            d = load(path)
            fn(d)
            path.write_text(json.dumps(d, ensure_ascii=False, indent=1))

        results = []

        def case(name, mutate, written=False):
            P = fresh()
            out = None
            if written:
                out = P.root / "fastlane" / "metadata"
                cmd_write_quiet(P, out)
            if mutate:
                mutate(P, out)
            R = run_audit(P, out, quiet=True)
            results.append((name, R.ok(), R.errors[:2]))

        def cmd_write_quiet(P, out):
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                cmd_write(P, out)

        case("clean copy", None)
        case("clean copy + written tree", None, written=True)
        case("subtitle 31 chars", lambda P, o: edit_json(P.store / "de-DE.json",
             lambda d: d.update(subtitle="x" * 31)))
        case("'Maze Out' in a description", lambda P, o: edit_json(P.store / "pl.json",
             lambda d: d.update(description=d["description"] + " Maze Out")))
        case("'Tap Away' in the subtitle", lambda P, o: edit_json(P.store / "en-US.json",
             lambda d: d.update(subtitle="Tap Away, Beat the Clock")))
        case("'online' in a promo", lambda P, o: edit_json(P.store / "fr-FR.json",
             lambda d: d.update(promotional_text="Jouez en ligne")))
        case("'Grand Games' in review notes", lambda P, o: edit_json(P.store / "review.json",
             lambda d: d.update(notes=d["notes"] + " Grand Games")))
        case("en-US name drifts from ruling 38", lambda P, o: edit_json(P.store / "en-US.json",
             lambda d: d.update(name="Arrow Out: Puzzle Game")))
        case("'Free' in a name", lambda P, o: edit_json(P.store / "it.json",
             lambda d: d.update(name="Arrow Out: Free Puzzle")))
        case("keyword over 100", lambda P, o: edit_json(P.keywords,
             lambda d: d.update({"tr": d["tr"] + ",x" * 10})))
        case("seed not first", lambda P, o: edit_json(P.keywords,
             lambda d: d.update({"ja": ",".join(reversed(d["ja"].split(",")))})))
        case("'maze' keyword", lambda P, o: edit_json(P.keywords,
             lambda d: d.update({"ko": d["ko"] + ",maze out"})))
        case("single-word Latin keyword", lambda P, o: edit_json(P.keywords,
             lambda d: d.update({"de-DE": "arrow out,pfeil puzzle,pfeile entfernen,logik rätsel,rätsel"})))
        case("caption != keyword", lambda P, o: edit_json(P.captions / "es-ES.json",
             lambda d: d["captions"][2].update(headline="Otra cosa")))
        case("4 captions", lambda P, o: edit_json(P.captions / "sk.json",
             lambda d: d.update(captions=d["captions"][:4])))
        case("unresearched keyword", lambda P, o: edit_json(P.keywords,
             lambda d: d.update({"sl-SI": d["sl-SI"] + ",arrow brain teaser"})))
        case("IAP usd mismatch", lambda P, o: edit_json(P.iap,
             lambda d: d["products"][3].update(usd=18.99)))
        case("IAP description 56 chars", lambda P, o: edit_json(P.iap,
             lambda d: d["products"][5]["locales"]["pl"].update(description="y" * 56)))
        case("IAP coin amount wrong", lambda P, o: edit_json(P.iap,
             lambda d: d["products"][7]["locales"]["de-DE"].update(description="Ein Paket mit 500 Münzen")))
        case("IAP bundle hours wrong", lambda P, o: edit_json(P.iap,
             lambda d: d["products"][4]["locales"]["ko"].update(description="코인 20,000개, 부스터 각 18개, 3시간 무제한 하트")))
        case("IAP booster count wrong", lambda P, o: edit_json(P.iap,
             lambda d: d["products"][2]["locales"]["fr-FR"].update(description="4 000 pièces, 2 bonus de chaque, vies infinies 6 h")))
        case("IAP try mismatch", lambda P, o: edit_json(P.iap,
             lambda d: d["products"][9].update({"try": 1399.99})))
        case("IAP missing a locale", lambda P, o: edit_json(P.iap,
             lambda d: d["products"][0]["locales"].pop("sk")))
        case("keywords.txt in the written tree", lambda P, o: (o / "en-US" / "keywords.txt").write_text("x"),
             written=True)
        case("release_notes.txt in the written tree", lambda P, o: (o / "de-DE" / "release_notes.txt").write_text("x"),
             written=True)
        case("URL file lost", lambda P, o: (o / "ja" / "support_url.txt").unlink(), written=True)
        case("stale written description", lambda P, o: (o / "it" / "description.txt").write_text("vecchio"),
             written=True)

        # write() must write the URLs even when a field is over its limit
        P = fresh()
        edit_json(P.store / "sk.json", lambda d: d.update(subtitle="z" * 40))
        out = P.root / "fastlane" / "metadata"
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            wrote_ok = cmd_write(P, out)
        urls_kept = (out / "sk" / "privacy_url.txt").exists() and (out / "sk" / "support_url.txt").exists()
        results.append(("over-limit locale keeps its URLs", (not wrote_ok) and urls_kept is True, []))

        passed = 0
        for name, ok, errs in results:
            expect_green = name.startswith("clean") or name.startswith("over-limit")
            good = ok if expect_green else not ok
            passed += good
            tag = "PASS" if good else "FAIL"
            what = "green" if expect_green else ("CAUGHT" if not ok else "MISSED")
            print(f"  {tag}  {name:40} -> {what}" + ("" if good else f"  {errs}"))
        print(f"selftest {passed}/{len(results)}")
        return passed == len(results)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["write", "audit", "iap-check", "selftest"])
    ap.add_argument("--out", type=Path, help="write target (default fastlane/metadata; needs fastlane/ to exist)")
    ap.add_argument("--dir", type=Path, help="audit a written metadata tree as well")
    a = ap.parse_args()
    P = Paths()
    if a.cmd == "write":
        out = a.out or L.FASTLANE_META
        if a.out is None and not (APP / "fastlane").exists():
            sys.exit("fastlane/ is not scaffolded yet (T5). Pass --out DIR to write elsewhere.")
        sys.exit(0 if cmd_write(P, out) else 1)
    if a.cmd == "iap-check":
        R = Report()
        audit_iap(P, R)
        print("IAP", "OK" if R.ok() else f"*** {len(R.errors)} FAILURES ***")
        sys.exit(0 if R.ok() else 1)
    if a.cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    written = a.dir if a.dir else (L.FASTLANE_META if L.FASTLANE_META.exists() else None)
    R = run_audit(P, written)
    kw = load(P.keywords)
    for loc in L.LOCALES:
        s = load(P.store / f"{loc}.json")
        print(f"  {loc:8} name {len(s['name']):2}/30 sub {len(s['subtitle']):2}/30 promo {len(s['promotional_text']):3}/170 "
              f"desc {len(s['description']):4}/4000 kw {len(kw.get(loc, '')):3}/100  {s['name']}")
    heads = [w for w in R.warnings if "head term" in w]
    margin = [w for w in R.warnings if "> 45" in w]
    other = [w for w in R.warnings if w not in heads and w not in margin]
    print(f"  ~ {len(heads)} keyword phrases are head terms (0 arrow titles in their top 10; kept for word coverage):")
    for w in heads:
        print("      " + w.split(": ", 1)[1].replace(" is a head term (0 arrow titles in its top 10)", "")
              + "  [" + w.split("/")[1].split(":")[0] + "]")
    print(f"  ~ {len(margin)} IAP descriptions are 46-55 chars (OK at the INFERRED 55 limit; T5's first POST confirms)")
    for w in other:
        print("  ~ " + w)
    print(f"written tree: {written or 'not checked (fastlane/ not scaffolded yet)'}")
    print("AUDIT", "OK" if R.ok() else f"*** {len(R.errors)} FAILURES ***")
    sys.exit(0 if R.ok() else 1)


if __name__ == "__main__":
    main()
