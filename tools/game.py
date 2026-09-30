#!/usr/bin/env python3
"""game.py: one config file per game (apps/<slug>/game.yml) -> every place that repeats it, plus a doctor.

    python3 tools/game.py doctor   --game <slug> [--quick] [--strict]
    python3 tools/game.py generate --game <slug> [--check]
    python3 tools/game.py new <slug> --from <existing-slug> --name "Brand" --bundle com.x.y
                              [--product CamelName] [--store-name "..."] [--puzzle <module-id>]
                              [--privacy-url URL] [--bans "Word A,Word B"]

doctor    checks that the game folder is consistent and complete: game.yml's schema; every identity value where it is
          used today (project.yml, fastlane, tools, .storekit, iap.json, tuning, store metadata, a few Swift constants);
          brand bans in every gate; the IAP triple (meta.py iap-check); the string catalogue; the level bundle (the
          puzzle's own checks from game.yml); the store texts (meta.py audit); every shipped art file of art/MANIFEST.json
          at its size; machine.env; no identity of ANOTHER game under apps/. Prints PASS / WARN / FAIL per item.
          Exit 0 = no FAIL (WARN allowed unless --strict), 1 = at least one FAIL, 2 = game.yml unreadable.
generate  writes game.yml's values into those places with targeted text replacement (a regex group or a JSON value span;
          nothing else in the file moves). --check only lists what would change (exit 1 if anything would).
new       scaffolds apps/<slug> from an existing game: copies the generic parts (see COPY_* below and docs/TEMPLATE.md),
          renames the old identity (bundle id, product, apps/<old> paths), writes apps/<slug>/game.yml, runs generate,
          then lists what is left to make (art, levels, store texts: doctor's FAILs marked TODO).

Only the standard library + PyYAML (requirements.txt). No network. Never prints secrets (machine.env is only tested for
existence). Tests: python3 -m unittest discover -s tools/tests
"""
from __future__ import annotations

import argparse
import ast
import difflib
import glob
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - requirements.txt has it
    yaml = None

REPO = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 1

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


# ================================================================================================= game.yml
class ConfigError(Exception):
    pass


def apps_dir(repo: Path) -> Path:
    return repo / "apps"


def game_dir(repo: Path, slug: str) -> Path:
    return apps_dir(repo) / slug


def load_game(repo: Path, slug: str) -> dict:
    p = game_dir(repo, slug) / "game.yml"
    if not p.exists():
        raise ConfigError(f"{p.relative_to(repo)} not found")
    if yaml is None:
        raise ConfigError("PyYAML missing: pip3 install -r requirements.txt")
    try:
        cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ConfigError(f"game.yml is not valid YAML: {e}")
    if not isinstance(cfg, dict):
        raise ConfigError("game.yml must be a mapping")
    return cfg


def get(cfg: dict, dotted: str, default=None):
    cur = cfg
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


RE_SLUG = re.compile(r"^[a-z][a-z0-9-]*$")
RE_BUNDLE = re.compile(r"^[a-zA-Z][a-zA-Z0-9-]*(\.[a-zA-Z][a-zA-Z0-9-]*){2,}$")
RE_TEAM = re.compile(r"^[A-Z0-9]{10}$")
RE_PRODUCT = re.compile(r"^[A-Z][A-Za-z0-9]*$")
RE_MODULE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$")
RE_URL = re.compile(r"^https://[^\s]+$")
RE_HEX64 = re.compile(r"^0x[0-9A-Fa-f]{16}$")

# key -> (type, check or None, meaning). Every key the tool reads; unknown keys are allowed (documentation, future keys).
SCHEMA = {
    "schema": (int, lambda v: v == SCHEMA_VERSION, f"format version {SCHEMA_VERSION}"),
    "id": (str, RE_SLUG.match, "slug [a-z][a-z0-9-]*"),
    "identity.brand_name": (str, lambda v: 0 < len(v) <= 30, "1-30 chars"),
    "identity.product": (str, RE_PRODUCT.match, "CamelCase product name"),
    "identity.bundle_id": (str, RE_BUNDLE.match, "reverse-DNS bundle id with >= 3 parts"),
    "identity.team_id": (str, RE_TEAM.match, "10-char Apple team id"),
    "identity.profile_name": (str, None, "provisioning profile name"),
    "puzzle.module": (str, RE_MODULE.match, "kebab-case module id"),
    "puzzle.levels_source": (str, None, "path"),
    "puzzle.levels_bundle": (str, None, "path"),
    "store.name": (str, lambda v: 0 < len(v) <= 30, "App Store name, 1-30 chars"),
    "store.keyword_seed": (str, lambda v: v == v.lower(), "lowercase"),
    "store.texts": (str, None, "path"),
    "store.keywords": (str, None, "path"),
    "store.primary_category": (str, None, "App Store category"),
    "store.subcategories": (list, lambda v: all(isinstance(x, str) for x in v), "list of subcategories"),
    "store.privacy_url": (str, RE_URL.match, "https URL"),
    "store.support_url": (str, RE_URL.match, "https URL"),
    "store.support_email": (str, RE_EMAIL.match, "e-mail"),
    "store.copyright": (str, None, "text"),
    "store.locales": (list, lambda v: v and all(isinstance(x, str) for x in v) and "en-US" in v, "list incl. en-US"),
    "store.app_locales": (list, lambda v: v and all(isinstance(x, str) for x in v) and "en" in v, "list incl. en"),
    "economy.tuning": (str, None, "path"),
    "economy.sections": (list, None, "list of section names"),
    "iap.catalogue": (str, None, "path"),
    "events.unlocks": (dict, lambda v: all(isinstance(x, int) and x >= 1 for x in v.values()), "event -> level"),
    "events.rotation.enabled": (bool, None, "bool"),
    "events.rotation.always": (list, None, "event ids"),
    "events.rotation.ladder": (list, None, "event ids"),
    "events.rotation.race": (list, None, "event ids"),
    "social.world_seed": (str, RE_HEX64.match, "0x + 16 hex digits"),
    "social.world_epoch": (int, lambda v: v > 0, "unix seconds"),
    "social.calendar_epoch": (int, lambda v: v > 0, "unix seconds"),
    "social.rotation_seed": (str, RE_HEX64.match, "0x + 16 hex digits"),
    "brand_bans": (list, lambda v: v and all(isinstance(x, str) and x.strip() for x in v), "non-empty word list"),
    "features.ad_attribution": (bool, None, "bool"),
    "features.notifications": (bool, None, "bool"),
    "features.ipad": (bool, None, "bool"),
    "features.rating_after_level": (int, lambda v: v >= 1, "level >= 1"),
}


def validate(cfg: dict, slug: str | None = None) -> list[str]:
    """-> problems (empty = valid)."""
    probs = []
    for key, (typ, check, meaning) in SCHEMA.items():
        v = get(cfg, key, None)
        if v is None:
            probs.append(f"{key}: missing ({meaning})")
            continue
        if typ is int and isinstance(v, bool) or not isinstance(v, typ):
            probs.append(f"{key}: {type(v).__name__} {v!r}, want {typ.__name__} ({meaning})")
            continue
        if check is not None and not check(v):
            probs.append(f"{key}: {v!r} is not a {meaning}")
    if slug is not None and cfg.get("id") != slug:
        probs.append(f"id: {cfg.get('id')!r} but the folder is apps/{slug}")
    unlocks = get(cfg, "events.unlocks", {}) or {}
    for pool in ("always", "ladder", "race"):
        for ev in get(cfg, f"events.rotation.{pool}", []) or []:
            if ev not in unlocks:
                probs.append(f"events.rotation.{pool}: {ev!r} is not in events.unlocks")
    for w in get(cfg, "brand_bans", []) or []:
        if isinstance(w, str) and '"' in w:
            probs.append(f"brand_bans: {w!r} contains a double quote")
    return probs


# derived values ------------------------------------------------------------------------------------------------
def iap_prefix(cfg):
    return cfg["identity"]["bundle_id"] + "."


def sku_prefix(cfg):
    return cfg["identity"]["bundle_id"].rsplit(".", 1)[1]


def bundle_org(bundle: str) -> str:
    return bundle.rsplit(".", 1)[0]


def brands_list(cfg):
    """tools/strings/build.py BRANDS: the original's names + ours (copy must interpolate Brand.name)."""
    out = []
    for w in list(cfg["brand_bans"]) + [cfg["identity"]["brand_name"], cfg["identity"]["product"]]:
        if w not in out:
            out.append(w)
    return out


def camel(name: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", name)
    s = "".join(p[:1].upper() + p[1:] for p in parts)
    if not s or not s[0].isalpha():
        s = "Game" + s
    return s


def kebab(name: str) -> str:
    return "-".join(p.lower() for p in re.findall(r"[A-Za-z0-9]+", name))


# ================================================================================================= JSON value spans
class JSONSpanError(ValueError):
    pass


def json_spans(text: str) -> dict:
    """Every value's (start, end) character span in a JSON text, keyed by its path tuple (keys / list indices).
    Lets generate replace ONE value in a hand-formatted file without re-serialising (and reformatting) the rest."""
    spans = {}
    n = len(text)
    num = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null")

    def skip(i):
        while i < n and text[i] in " \t\r\n":
            i += 1
        return i

    def string_end(i):
        if text[i] != '"':
            raise JSONSpanError(f"string expected at {i}")
        j = i + 1
        while j < n and text[j] != '"':
            j += 2 if text[j] == "\\" else 1
        if j >= n:
            raise JSONSpanError("unterminated string")
        return j + 1

    def value(i, path):
        i = skip(i)
        if i >= n:
            raise JSONSpanError("unexpected end")
        start, c = i, text[i]
        if c == "{":
            i = skip(i + 1)
            if text[i] == "}":
                i += 1
            else:
                while True:
                    i = skip(i)
                    ke = string_end(i)
                    key = json.loads(text[i:ke])
                    i = skip(ke)
                    if text[i] != ":":
                        raise JSONSpanError(f"':' expected at {i}")
                    i = skip(value(i + 1, path + (key,)))
                    if text[i] == ",":
                        i += 1
                        continue
                    if text[i] != "}":
                        raise JSONSpanError(f"'}}' expected at {i}")
                    i += 1
                    break
        elif c == "[":
            i = skip(i + 1)
            if text[i] == "]":
                i += 1
            else:
                k = 0
                while True:
                    i = skip(value(i, path + (k,)))
                    k += 1
                    if text[i] == ",":
                        i += 1
                        continue
                    if text[i] != "]":
                        raise JSONSpanError(f"']' expected at {i}")
                    i += 1
                    break
        elif c == '"':
            i = string_end(i)
        else:
            m = num.match(text, i)
            if not m:
                raise JSONSpanError(f"value expected at {i}")
            i = m.end()
        spans[path] = (start, i)
        return i

    end = skip(value(0, ()))
    if end != n:
        raise JSONSpanError(f"trailing text at {end}")
    return spans


def json_inline(v) -> str:
    return json.dumps(v, ensure_ascii=False)


# ================================================================================================= anchors
class Anchor:
    """One value of game.yml as it appears in one file.

    kind 're':   `pattern` (re.M) has ONE group = the value's text; every match must equal expect(cfg, found).
    kind 'json': `path` into the JSON file; the parsed value must equal expect(cfg).
    file may be a glob (first file with a match wins: Swift files move while the template is extracted).
    missing: what an absent file / absent match means: 'fail', 'warn' or 'skip' (another check covers it).
    write: False = doctor checks, generate never rewrites it (a (new only) key: product / slug renames are structural).
    """

    def __init__(self, section, key, file, *, pattern=None, path=None, expect, min_count=1, missing="fail",
                 write=True, norm=None, render=None, group=None):
        self.section, self.key, self.file = section, key, file
        self.group = group  # doctor prints one line for all anchors of a group (e.g. 13 locales' URL files)
        self.kind = "re" if pattern is not None else "json"
        self.rx = re.compile(pattern, re.M) if pattern is not None else None
        self.path = path
        self.expect, self.min_count, self.missing, self.write = expect, min_count, missing, write
        self.norm = norm or (lambda s: s)
        self.render = render  # re: expected value -> text for the group (default str)

    def files(self, gdir: Path) -> list[Path]:
        if any(ch in self.file for ch in "*?["):
            return [Path(p) for p in sorted(glob.glob(str(gdir / self.file), recursive=True))]
        p = gdir / self.file
        return [p] if p.exists() else []

    def locate(self, gdir: Path):
        """-> (path, text, found values) or (None, None, []) when neither file nor match exists."""
        for p in self.files(gdir):
            text = p.read_text(encoding="utf-8")
            if self.kind == "re":
                found = [m.group(1) for m in self.rx.finditer(text)]
                if found:
                    return p, text, found
            else:
                try:
                    spans = json_spans(text)
                except JSONSpanError:
                    return p, text, None
                if self.path in spans:
                    s, e = spans[self.path]
                    return p, text, [json.loads(text[s:e])]
        paths = self.files(gdir)
        return (paths[0], paths[0].read_text(encoding="utf-8"), []) if paths else (None, None, [])

    def expected_text(self, cfg):
        v = self.expect(cfg)
        return self.render(v) if self.render else str(v)

    def check(self, gdir: Path, cfg) -> tuple[str, str]:
        """-> (status, detail)."""
        p, text, found = self.locate(gdir)
        where = self.file
        if p is None or not found:
            what = "file missing" if p is None else ("not valid JSON" if found is None else "value not found")
            st = {"fail": FAIL, "warn": WARN, "skip": None}[self.missing]
            return st, f"{self.key}: {where}: {what}"
        if self.kind == "re":
            want = self.expected_text(cfg)
            bad = [f for f in found if self.norm(f) != self.norm(want)]
            if len(found) < self.min_count:
                return FAIL, f"{self.key}: {where}: {len(found)} occurrence(s), want >= {self.min_count}"
        else:
            want = self.expect(cfg)
            bad = [f for f in found if f != want]
        if bad:
            return FAIL, f"{self.key}: {p.name} has {bad[0]!r}, game.yml says {want!r}"
        return PASS, f"{self.key}"

    def apply(self, text: str, cfg) -> str:
        if self.kind == "re":
            want = self.expected_text(cfg)

            def sub(m):
                if self.norm(m.group(1)) == self.norm(want):
                    return m.group(0)
                s, e = m.span(1)
                return m.group(0)[: s - m.start()] + want + m.group(0)[e - m.start():]
            return self.rx.sub(sub, text)
        spans = json_spans(text)
        if self.path not in spans:
            return text
        s, e = spans[self.path]
        want = self.expect(cfg)
        if json.loads(text[s:e]) == want:
            return text
        return text[:s] + json_inline(want) + text[e:]


def _q(v):  # a double-quoted list, Python / Swift / JSON style
    return "[" + ", ".join(f'"{x}"' for x in v) + "]"


def _hex_norm(s):
    return s.replace("_", "").upper().replace("0X", "0x")


def _hex_swift(v):  # 0x4152_4F57_204F_5554 (the Swift sources' grouping)
    h = v[2:].upper()
    return "0x" + "_".join(h[i:i + 4] for i in range(0, len(h), 4))


def _int_swift(v):  # 1_788_764_400
    return f"{v:_}"


def _num_norm(s):
    return s.replace("_", "")


def anchors(cfg) -> list[Anchor]:
    """Every place a game.yml value is repeated today (README §4 rename checklist, rows 1-4, 10-12, 17-20)."""
    A = []
    I = lambda k: (lambda c: c["identity"][k])  # noqa: E731
    S = lambda k: (lambda c: c["store"][k])  # noqa: E731
    product = cfg["identity"]["product"]
    sk = f"App/Resources/StoreKit/{product}.storekit"
    # --- project.yml
    P = "project.yml"
    A += [
        Anchor("identity", "project name", P, pattern=r"^name: *(\S+)", expect=I("product"), write=False),
        Anchor("identity", "DEVELOPMENT_TEAM", P, pattern=r"DEVELOPMENT_TEAM: *(\S+)", expect=I("team_id")),
        Anchor("identity", "PC_BRAND_NAME", P, pattern=r'PC_BRAND_NAME: *"([^"]*)"', expect=I("brand_name")),
        Anchor("identity", "bundleIdPrefix", P, pattern=r"bundleIdPrefix: *(\S+)",
               expect=lambda c: bundle_org(c["identity"]["bundle_id"])),
        Anchor("identity", "PRODUCT_BUNDLE_IDENTIFIER (app, .tests, .uitests)", P,
               pattern=r"PRODUCT_BUNDLE_IDENTIFIER: *([A-Za-z0-9.-]+?)(?:\.tests|\.uitests)?[ \t]*$",
               expect=I("bundle_id"), min_count=3),
        Anchor("identity", "storeKitConfiguration", P,
               pattern=r"storeKitConfiguration: *App/Resources/StoreKit/([^\s}.]+)\.storekit", expect=I("product"),
               write=False),
        Anchor("features", "TARGETED_DEVICE_FAMILY (ipad)", P, pattern=r'TARGETED_DEVICE_FAMILY: *"([^"]*)"',
               expect=lambda c: "1,2" if c["features"]["ipad"] else "1"),
        Anchor("store", "app locales (postGenCommand known regions)", P,
               pattern=r"known_regions\.py +\S+ +([^\n]+?)[ \t]*$", expect=lambda c: " ".join(c["store"]["app_locales"])),
    ]
    # --- fastlane
    A += [
        Anchor("identity", "Appfile app_identifier", "fastlane/Appfile", pattern=r'app_identifier +"([^"]+)"',
               expect=I("bundle_id")),
        Anchor("store", "Deliverfile primary_category", "fastlane/Deliverfile", pattern=r'primary_category +"([^"]+)"',
               expect=S("primary_category")),
        Anchor("store", "Deliverfile first subcategory", "fastlane/Deliverfile",
               pattern=r'primary_first_sub_category +"([^"]+)"', expect=lambda c: c["store"]["subcategories"][0]),
        Anchor("store", "Deliverfile second subcategory", "fastlane/Deliverfile",
               pattern=r'primary_second_sub_category +"([^"]+)"',
               expect=lambda c: (c["store"]["subcategories"] + [""])[1]),
        Anchor("identity", "Fastfile app_identifier", "fastlane/Fastfile", pattern=r'app_identifier: *"([^"]+)"',
               expect=I("bundle_id")),
        Anchor("identity", "Fastfile provisioningProfiles bundle", "fastlane/Fastfile",
               pattern=r'provisioningProfiles: *\{ *"([^"]+)" *=>', expect=I("bundle_id")),
        Anchor("identity", "Fastfile provisioningProfiles profile", "fastlane/Fastfile",
               pattern=r'provisioningProfiles: *\{ *"[^"]+" *=> *"([^"]+)"', expect=I("profile_name")),
        Anchor("identity", "Fastfile scheme", "fastlane/Fastfile", pattern=r'scheme: *"([^"]+)"', expect=I("product"),
               write=False),
        Anchor("identity", "Fastfile Payload/<product>.app", "fastlane/Fastfile",
               pattern=r"""Payload/([A-Za-z0-9]+)\.app""", expect=I("product"), write=False),
        Anchor("identity", "Fastfile provenance slug", "fastlane/Fastfile", pattern=r"grep -ci ([a-z0-9-]+)`",
               expect=lambda c: c["id"], min_count=2),
        Anchor("store", "Fastfile create_app app_name", "fastlane/Fastfile", pattern=r'app_name: *"([^"]+)"',
               expect=S("name")),
        Anchor("identity", "Fastfile create_app sku prefix", "fastlane/Fastfile", pattern=r'sku: *"([^"#]+)-#',
               expect=sku_prefix),
        Anchor("store", "copyright.txt", "fastlane/metadata/copyright.txt", pattern=r"\A([^\n]+)", expect=S("copyright")),
    ]
    for loc in cfg["store"]["locales"]:
        for k, f in (("privacy_url", "privacy_url.txt"), ("support_url", "support_url.txt")):
            A.append(Anchor("store", f"metadata {loc}/{f}", f"fastlane/metadata/{loc}/{f}", pattern=r"\A(\S+)",
                            expect=S(k), missing="skip", group="fastlane/metadata/<locale>/privacy_url + support_url"))
    # --- tools
    A += [
        Anchor("identity", "slot.sh BUNDLE_ID", "tools/slot.sh", pattern=r"^BUNDLE_ID=(\S+)", expect=I("bundle_id")),
        Anchor("identity", "slot.sh SCHEME", "tools/slot.sh", pattern=r"^SCHEME=(\S+)", expect=I("product"), write=False),
        Anchor("identity", "slot.sh <product>.app", "tools/slot.sh", pattern=r"/([A-Za-z0-9]+)\.app\"",
               expect=I("product"), write=False),
        Anchor("identity", "play-watch.sh BUNDLE_ID", "tools/play-watch.sh", pattern=r"^BUNDLE_ID=(\S+)",
               expect=I("bundle_id"), missing="warn"),
        Anchor("identity", "bench.py BUNDLE", "tools/bench/bench.py", pattern=r'^BUNDLE = "([^"]+)"',
               expect=I("bundle_id"), missing="warn"),
        Anchor("identity", "bench.py APP_NAME", "tools/bench/bench.py", pattern=r'^APP_NAME = "([^"]+)"',
               expect=I("product"), missing="warn", write=False),
        Anchor("identity", "capture.py BUNDLE", "tools/capture/capture.py", pattern=r'^BUNDLE = "([^"]+)"',
               expect=I("bundle_id"), missing="warn"),
        Anchor("identity", "meta.py IAP prefix", "tools/release/meta.py", pattern=r'full = "([^"]+)\." \+ pid',
               expect=I("bundle_id")),
        Anchor("identity", "meta.py storekit file", "tools/release/meta.py",
               pattern=r'"StoreKit" / "([A-Za-z0-9]+)\.storekit"', expect=I("product"), write=False),
        Anchor("store", "loc.py BRAND", "tools/release/loc.py", pattern=r'^BRAND = "([^"]*)"', expect=I("brand_name")),
        Anchor("store", "loc.py NAME_EN", "tools/release/loc.py", pattern=r'^NAME_EN = "([^"]*)"', expect=S("name")),
        Anchor("store", "loc.py SEED", "tools/release/loc.py", pattern=r'^SEED = "([^"]*)"', expect=S("keyword_seed")),
        Anchor("store", "loc.py PRIVACY", "tools/release/loc.py", pattern=r'^PRIVACY = "([^"]*)"',
               expect=S("privacy_url")),
        Anchor("store", "loc.py SUPPORT", "tools/release/loc.py", pattern=r'^SUPPORT = "([^"]*)"',
               expect=S("support_url")),
        Anchor("store", "loc.py COPYRIGHT", "tools/release/loc.py", pattern=r'^COPYRIGHT = "([^"]*)"',
               expect=S("copyright")),
        Anchor("store", "loc.py LOCALES", "tools/release/loc.py", pattern=r"^LOCALES = (\[[^\]\n]*\])",
               expect=S("locales"), render=_q),
        Anchor("brand", "strings build.py BRANDS", "tools/strings/build.py", pattern=r"^BRANDS = (\([^)\n]*\))",
               expect=brands_list, render=lambda v: "(" + ", ".join(f'"{x}"' for x in v) + ")"),
        Anchor("brand", "release_gates.sh gate 3 (original's names)", "tools/bench/release_gates.sh",
               pattern=r'^b=\$\(grep -c "([^"]+)" "\$TMP/rel\.txt"\)', expect=lambda c: "\\|".join(c["brand_bans"])),
        Anchor("brand", "release_gates.sh gate 3 (own name literal)", "tools/bench/release_gates.sh",
               pattern=r'a=\$\(grep -c "([^"]+)" "\$TMP/rel\.txt"\)', expect=I("brand_name")),
        Anchor("brand", "release_gates.sh gate 3 message", "tools/bench/release_gates.sh",
               pattern=r"""; '([^']+)' literal \$a""", expect=I("brand_name")),
        Anchor("brand", "BrandTests product name", "Tests/**/BrandTests.swift",
               pattern=r'XCTAssertEqual\(brand, "([^"]+)"', expect=I("brand_name"), missing="warn"),
        Anchor("brand", "BrandTests bannedExact", "Tests/**/BrandTests.swift",
               pattern=r"static let bannedExact = (\[[^\]\n]*\])", expect=lambda c: c["brand_bans"], render=_q,
               missing="warn"),
    ]
    # --- JSON data
    A += [
        Anchor("identity", ".storekit _developerTeamID", sk, path=("settings", "_developerTeamID"), expect=I("team_id")),
        Anchor("iap", "iap.json productPrefix", "design/publish/iap.json", path=("productPrefix",), expect=iap_prefix),
        Anchor("iap", "iap.json appName", "design/publish/iap.json", path=("appName",), expect=I("brand_name")),
        Anchor("iap", "iap.json locales", "design/publish/iap.json", path=("locales",), expect=S("locales")),
        Anchor("iap", "rules.json shop.productPrefix", "App/Resources/Tuning/rules.json", path=("shop", "productPrefix"),
               expect=iap_prefix, missing="skip"),
        Anchor("store", "game.json support.email", "App/Resources/Tuning/game.json", path=("support", "email"),
               expect=S("support_email")),
        Anchor("features", "game.json notifications.askOnFirstLaunch", "App/Resources/Tuning/game.json",
               path=("notifications", "askOnFirstLaunch"), expect=lambda c: c["features"]["notifications"]),
        Anchor("features", "game.json rating.afterLevel", "App/Resources/Tuning/game.json", path=("rating", "afterLevel"),
               expect=lambda c: c["features"]["rating_after_level"]),
        Anchor("identity", "art MANIFEST brand", "art/MANIFEST.json", path=("brand",), expect=I("brand_name"),
               missing="skip"),
    ]
    SJ = "App/Resources/Tuning/social.json"
    for ev in cfg["events"]["unlocks"]:
        A.append(Anchor("events", f"social.json unlocks.{ev}", SJ, path=("unlocks", ev),
                        expect=(lambda e: lambda c: c["events"]["unlocks"][e])(ev)))
    for k in ("enabled", "always", "ladder", "race"):
        A.append(Anchor("events", f"social.json events.rotation.{k}", SJ, path=("events", "rotation", k),
                        expect=(lambda kk: lambda c: c["events"]["rotation"][kk])(k)))
    A += [
        Anchor("social", "social.json events.rotation.seed", SJ, path=("events", "rotation", "seed"),
               expect=lambda c: c["social"]["rotation_seed"]),
        Anchor("social", "social.json events.rotation.epoch", SJ, path=("events", "rotation", "epoch"),
               expect=lambda c: c["social"]["calendar_epoch"]),
    ]
    # --- Swift constants (read where they are today; phase 1 moves them to config -> missing = WARN, not FAIL)
    SW = "Packages/**/*.swift"
    A += [
        Anchor("social", "Swift SocialWorldModel.worldSeed", SW, pattern=r"worldSeed: UInt64 = (0x[0-9A-Fa-f_]+)",
               expect=lambda c: c["social"]["world_seed"], norm=_hex_norm, render=_hex_swift, missing="warn"),
        Anchor("social", "Swift shipped world epoch", SW, pattern=r"\bm\.epoch = ([0-9_]+)",
               expect=lambda c: c["social"]["world_epoch"], norm=_num_norm, render=_int_swift, missing="warn"),
        Anchor("social", "Swift SocialCalendar.epoch", "Packages/**/SocialCalendar.swift",
               pattern=r"static let epoch: Int = ([0-9_]+)", expect=lambda c: c["social"]["calendar_epoch"],
               norm=_num_norm, render=_int_swift, missing="warn"),
        Anchor("iap", "Swift ShopCatalog default productPrefix", SW, pattern=r'productPrefix: String = "([^"]+)"',
               expect=iap_prefix, missing="skip"),
    ]
    return A


# ================================================================================================= files
SKIP_DIRS = {"research", "build", "DerivedData", ".build", "__pycache__", ".git", "node_modules"}
SKIP_REL = ("art/review", "art/lanes", "design/spike-src", "design/spike-results", "design/spike-shots",
            "design/publish/verify", "fastlane/screenshots")
TEXT_EXT = {".swift", ".py", ".sh", ".yml", ".yaml", ".json", ".storekit", ".rb", ".txt", ".tsv", ".plist",
            ".xcprivacy", ".xcstrings", ".js", ".c", ".h", ".m", ".metal", ".strings", ".svg"}
TEXT_NAMES = {"Fastfile", "Appfile", "Deliverfile", "Gemfile", "Package.swift"}


def iter_text_files(gdir: Path):
    """Code + config files of a game (the README §4 'code+config' set: no Markdown notes, research, reviews, spikes,
    release evidence, screenshots or build products)."""
    for root, dirs, files in os.walk(gdir):
        r = Path(root)
        rel = r.relative_to(gdir).as_posix()
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.endswith(".xcodeproj")
                         and not any((f"{rel}/{d}" if rel != "." else d).startswith(s) for s in SKIP_REL))
        for f in sorted(files):
            p = r / f
            if p.suffix in TEXT_EXT or f in TEXT_NAMES:
                yield p


def read_text(p: Path):
    try:
        return p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def png_size(p: Path):
    with open(p, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def other_identities(repo: Path, slug: str) -> list[dict]:
    """Identities of every OTHER game under apps/: from its game.yml, else from its project.yml."""
    out = []
    for d in sorted(apps_dir(repo).iterdir()) if apps_dir(repo).exists() else []:
        if not d.is_dir() or d.name == slug:
            continue
        ident = {"slug": d.name}
        try:
            c = load_game(repo, d.name)
            ident.update(bundle=get(c, "identity.bundle_id"), product=get(c, "identity.product"),
                         brand=get(c, "identity.brand_name"))
        except ConfigError:
            py = d / "project.yml"
            if py.exists():
                t = py.read_text(encoding="utf-8")
                m = re.search(r"^name: *(\S+)", t, re.M)
                b = re.search(r"PRODUCT_BUNDLE_IDENTIFIER: *(\S+)", t)
                n = re.search(r'PC_BRAND_NAME: *"([^"]*)"', t)
                ident.update(product=m and m.group(1), bundle=b and b.group(1), brand=n and n.group(1))
        if len(ident) > 1:
            out.append(ident)
    return out


def identity_patterns(ident: dict) -> list[tuple[str, re.Pattern]]:
    pats = [("slug path", re.compile(r"apps/" + re.escape(ident["slug"]) + r"(?![A-Za-z0-9-])"))]
    if ident.get("bundle"):
        pats.append(("bundle id", re.compile(re.escape(ident["bundle"]) + r"(?![A-Za-z0-9-])")))
    if ident.get("product"):
        pats.append(("product", re.compile(r"(?<![A-Za-z0-9])" + re.escape(ident["product"]) + r"(?![a-z0-9])")))
    if ident.get("brand"):
        pats.append(("brand name", re.compile(r"(?<![A-Za-z0-9])" + re.escape(ident["brand"]) + r"(?![A-Za-z0-9])")))
    return pats


# ================================================================================================= doctor
class Report:
    def __init__(self):
        self.items = []  # (status, section, label, detail)

    def add(self, status, section, label, detail=""):
        if status:
            self.items.append((status, section, label, detail))

    def count(self, status):
        return sum(1 for s, *_ in self.items if s == status)

    def render(self, title) -> str:
        lines = [title]
        cur = None
        for st, sec, label, detail in self.items:
            if sec != cur:
                lines.append(f"\n{sec}")
                cur = sec
            lines.append(f"  [{st}] {label}" + (f": {detail}" if detail else ""))
        lines.append(f"\n{self.count(PASS)} PASS, {self.count(WARN)} WARN, {self.count(FAIL)} FAIL")
        return "\n".join(lines)


def run_cmd(gdir: Path, argv: list[str], timeout=900):
    """Runs a game tool (python scripts with this interpreter) -> (ok, last meaningful output line)."""
    if argv and argv[0].endswith(".py"):
        argv = [sys.executable] + argv
    try:
        r = subprocess.run(argv, cwd=gdir, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    out = (r.stdout + "\n" + r.stderr).strip().splitlines()
    tail = [line for line in out if line.strip()]
    msg = tail[-1].strip() if tail else f"exit {r.returncode}"
    if r.returncode != 0:
        errs = [line.strip() for line in out if "ERROR" in line or "FAIL" in line or "error" in line.lower()]
        if errs:
            msg = f"{errs[0]} … ({msg})"
    return r.returncode == 0, msg[:300]


def ast_constant(path: Path, name: str):
    """A module-level literal (tuple/list/str) of a Python tool, read without importing it."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    return None


def doctor(repo: Path, slug: str, quick=False) -> Report:
    R = Report()
    gdir = game_dir(repo, slug)
    C = "1. game.yml"
    if not gdir.is_dir():
        R.add(FAIL, C, "game folder", f"apps/{slug} does not exist")
        return R
    try:
        cfg = load_game(repo, slug)
    except ConfigError as e:
        R.add(FAIL, C, "load", str(e))
        return R
    probs = validate(cfg, slug)
    if probs:
        for p in probs:
            R.add(FAIL, C, "schema", p)
        return R
    R.add(PASS, C, "schema", f"{len(SCHEMA)} keys valid (id {cfg['id']}, module {cfg['puzzle']['module']})")

    # ---- anchors, grouped per section
    names = {"identity": "2. Identity where it is used", "features": "3. Feature flags", "store": "4. Store",
             "iap": "5. IAP and economy", "events": "6. Events", "social": "7. Social world",
             "brand": "8. Brand bans"}
    for sec in names:
        groups = {}
        for a in [a for a in anchors(cfg) if a.section == sec]:
            st, detail = a.check(gdir, cfg)
            if a.group:
                groups.setdefault(a.group, []).append((st, detail))
                continue
            if st == PASS:
                R.add(PASS, names[sec], a.key, a.file if "*" not in a.file else "")
            else:
                R.add(st, names[sec], a.key, detail.split(": ", 1)[1] if ": " in detail else detail)
        for gname, res in groups.items():
            bad = [d for st, d in res if st == FAIL]
            seen = [st for st, _ in res if st]
            if bad:
                R.add(FAIL, names[sec], gname, f"{len(bad)} wrong, e.g. {bad[0]}")
            elif seen:
                R.add(PASS, names[sec], gname, f"{len(seen)} files match")
        _extra_checks(R, repo, gdir, cfg, sec, names[sec], quick)

    # ---- content
    S = "9. Content"
    _content_checks(R, repo, gdir, cfg, S, quick)
    # ---- art
    _art_checks(R, gdir, cfg, "10. Art")
    # ---- machine + leftovers
    M = "11. Machine and hygiene"
    if (repo / "machine.env").exists():
        R.add(PASS, M, "machine.env", "present (values not printed)")
    else:
        R.add(WARN, M, "machine.env", "missing: cp machine.env.example machine.env (simulator/phone ids; needed on the Mac "
                                      "for tools/slot.sh, not for CI or Linux checks)")
    _leftover_checks(R, repo, gdir, cfg, M)
    return R


def _extra_checks(R, repo, gdir, cfg, sec, title, quick):
    ident = cfg["identity"]
    if sec == "identity":
        sk = gdir / f"App/Resources/StoreKit/{ident['product']}.storekit"
        if sk.exists():
            ids = [p.get("productID", "") for p in json.loads(sk.read_text(encoding="utf-8")).get("products", [])]
            bad = [i for i in ids if not i.startswith(iap_prefix(cfg))]
            R.add(FAIL if bad or not ids else PASS, title, ".storekit product ids use the bundle prefix",
                  f"{len(ids)} products" + (f"; not prefixed: {bad[:3]}" if bad else ""))
        else:
            R.add(FAIL, title, ".storekit file", f"App/Resources/StoreKit/{ident['product']}.storekit missing")
        # every com.<org>.<app> literal in code/config belongs to THIS bundle (queue labels, log subsystem, ids)
        org = re.escape(bundle_org(ident["bundle_id"]))
        rx = re.compile(r"(?<![A-Za-z0-9.-])" + org + r"\.([A-Za-z0-9-]+)")
        want = ident["bundle_id"].rsplit(".", 1)[1]
        stray = {}
        for p in iter_text_files(gdir):
            t = read_text(p)
            if not t:
                continue
            for m in rx.finditer(t):
                if m.group(1) != want:
                    stray.setdefault(m.group(0), []).append(p.relative_to(gdir).as_posix())
        if stray:
            k = sorted(stray)[0]
            R.add(FAIL, title, f"'{bundle_org(ident['bundle_id'])}.*' literals are this bundle",
                  f"{len(stray)} other id(s), e.g. {k} in {stray[k][0]} (generate rewrites the old bundle id)")
        else:
            R.add(PASS, title, f"'{bundle_org(ident['bundle_id'])}.*' literals are this bundle",
                  "queue labels, log subsystem, product ids, tools")
    elif sec == "features":
        py = (gdir / "project.yml").read_text(encoding="utf-8") if (gdir / "project.yml").exists() else ""
        sdk = re.findall(r"(?i)facebook|FBSDK|FacebookAppID|appsflyer|adjust-sdk|branch-io|singular|kochava|"
                         r"GoogleMobileAds|applovin|unity-ads|ironsource", py)
        pi = gdir / "App/PrivacyInfo.xcprivacy"
        tracking = pi.exists() and re.search(r"<key>NSPrivacyTracking</key>\s*<true/>", pi.read_text(encoding="utf-8"))
        if cfg["features"]["ad_attribution"]:
            R.add(WARN if not sdk else PASS, title, "ad attribution ON",
                  "project.yml names no attribution SDK yet (docs/recipes/ad-attribution.md)" if not sdk else "SDK wired")
        else:
            bad = sdk or tracking
            R.add(FAIL if bad else PASS, title, "ad attribution OFF (D2)",
                  (f"project.yml names {sorted(set(sdk))}" if sdk else "PrivacyInfo NSPrivacyTracking true") if bad
                  else "no ad/attribution package in project.yml; PrivacyInfo NSPrivacyTracking false")
    elif sec == "store":
        bp = gdir / "tools/strings/build.py"
        if bp.exists():
            langs = ast_constant(bp, "LANGS") or []
            have = set(["en", "tr"] + list(langs))
            want = set(cfg["store"]["app_locales"])
            R.add(PASS if have == want else FAIL, title, "app locales == tools/strings/build.py (en, tr + LANGS)",
                  "" if have == want else f"build.py {sorted(have)} vs game.yml {sorted(want)}")
    elif sec == "iap":
        tun = gdir / cfg["economy"]["tuning"]
        if tun.exists():
            d = json.loads(tun.read_text(encoding="utf-8"))
            miss = [s for s in cfg["economy"]["sections"] if s not in d]
            R.add(FAIL if miss else PASS, title, f"economy sections in {cfg['economy']['tuning']}",
                  f"missing {miss}" if miss else ", ".join(cfg["economy"]["sections"]))
        else:
            R.add(FAIL, title, "economy tuning", f"{cfg['economy']['tuning']} missing")
        cat = gdir / cfg["iap"]["catalogue"]
        if cat.exists():
            prods = json.loads(cat.read_text(encoding="utf-8")).get("products", [])
            bad = [p.get("productId") for p in prods if not str(p.get("productId", "")).startswith(iap_prefix(cfg))]
            R.add(FAIL if bad or not prods else PASS, title, "iap.json productId prefix",
                  f"{len(prods)} products" + (f"; not prefixed: {bad[:3]}" if bad else ""))
        else:
            R.add(FAIL, title, "IAP catalogue", f"{cfg['iap']['catalogue']} missing")
        meta = gdir / "tools/release/meta.py"
        if meta.exists():
            ok, msg = run_cmd(gdir, ["tools/release/meta.py", "iap-check"])
            R.add(PASS if ok else FAIL, title, "IAP triple (meta.py iap-check: iap.json == rules.json shop == .storekit)", msg)
    elif sec == "events":
        sj = gdir / "App/Resources/Tuning/social.json"
        if sj.exists():
            extra = sorted(set(json.loads(sj.read_text(encoding="utf-8")).get("unlocks", {})) - set(cfg["events"]["unlocks"]))
            R.add(FAIL if extra else PASS, title, "every social.json event is listed in game.yml",
                  f"only in social.json: {extra}" if extra else f"{len(cfg['events']['unlocks'])} events")
    elif sec == "brand":
        bans = cfg["brand_bans"]
        bp = gdir / "tools/strings/build.py"
        if bp.exists():
            brands = ast_constant(bp, "BRANDS") or ()
            miss = [w for w in bans + [cfg["identity"]["brand_name"]] if not any(b.lower() in w.lower() for b in brands)]
            R.add(FAIL if miss else PASS, title, "strings BRANDS catches every ban + our own name",
                  f"not caught: {miss}" if miss else "")
        lp = gdir / "tools/release/loc.py"
        if lp.exists():
            pats = ast_constant(lp, "BANNED_ALL") or []
            miss = [w for w in bans if not any(re.search(p, w, re.I) for p in pats)]
            R.add(FAIL if miss else PASS, title, "store-text gate (loc.py BANNED_ALL) catches every ban",
                  f"add a pattern for: {miss}" if miss else f"{len(pats)} patterns")


def _content_checks(R, repo, gdir, cfg, S, quick):
    bp = gdir / "tools/strings/build.py"
    if bp.exists():
        ok, msg = run_cmd(gdir, ["tools/strings/build.py", "--check"])
        R.add(PASS if ok else FAIL, S, "string catalogue up to date (strings/build.py --check)", msg)
    else:
        R.add(FAIL, S, "string catalogue", "tools/strings/build.py missing")
    sk = gdir / "tools/skin/build.py"
    if sk.exists():
        ok, msg = run_cmd(gdir, ["tools/skin/build.py", "--check"])
        R.add(PASS if ok else FAIL, S, "skin generated (colours, fonts, names: skin/build.py --check)", msg)
    sj = gdir / "tools/strings/sources.json"
    if sj.exists():
        d = json.loads(sj.read_text(encoding="utf-8"))
        paths = sorted({s.get("path") for k in ("spec_sources", "data_files") for s in d.get(k, []) if s.get("path")})
        miss = [p for p in paths if not (gdir / p).exists()]
        R.add(WARN if miss else PASS, S, "strings coverage sources (tools/strings/sources.json)",
              f"TODO: {', '.join(miss)} missing: coverage.py / selftest.py compare the catalogue with them; write this "
              "game's spec sections or trim sources.json" if miss else f"{len(paths)} files")
    src = gdir / cfg["puzzle"]["levels_source"]
    bundle = gdir / cfg["puzzle"]["levels_bundle"]
    shipped = sorted(bundle.glob("*.json")) if bundle.is_dir() else []
    if not src.exists() or not shipped:
        R.add(FAIL, S, "levels", f"TODO: {'no ' + cfg['puzzle']['levels_source'] if not src.exists() else ''}"
              f"{' and ' if not src.exists() and not shipped else ''}"
              f"{'no level files in ' + cfg['puzzle']['levels_bundle'] if not shipped else ''} "
              f"(author or generate the {cfg['puzzle']['module']} levels)")
    else:
        R.add(PASS, S, "levels present", f"{len(shipped)} files in {cfg['puzzle']['levels_bundle']}")
        checks = get(cfg, "puzzle.checks", None) or []
        for cmd in checks:
            argv = cmd.split()
            if quick:
                R.add(WARN, S, f"puzzle check `{cmd}`", "skipped (--quick)")
                continue
            if not (gdir / argv[0]).exists():
                R.add(FAIL, S, f"puzzle check `{cmd}`", f"{argv[0]} missing")
                continue
            ok, msg = run_cmd(gdir, argv)
            R.add(PASS if ok else FAIL, S, f"puzzle check `{cmd}`", msg)
        # our own content, not another game's copy
        for other in [o for o in other_identities(repo, cfg["id"]) if o["slug"] == cfg.get("derived_from")]:
            ob = game_dir(repo, other["slug"]) / cfg["puzzle"]["levels_bundle"]
            if ob.is_dir() and sorted(p.name for p in ob.glob("*.json")) == [p.name for p in shipped] and all(
                    (ob / p.name).read_bytes() == p.read_bytes() for p in shipped):
                R.add(WARN, S, "levels are this game's own", f"TODO: identical to apps/{other['slug']}'s levels")
    # store texts
    texts = gdir / cfg["store"]["texts"]
    missing, bad = [], []
    for loc in cfg["store"]["locales"]:
        f = texts / f"{loc}.json"
        if not f.exists():
            missing.append(loc)
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        for k in ("name", "subtitle", "description"):
            if not str(d.get(k, "")).strip():
                bad.append(f"{loc}.{k} empty")
        if loc == "en-US" and d.get("name") != cfg["store"]["name"]:
            bad.append(f"en-US name {d.get('name')!r} != store.name")
    if missing:
        R.add(FAIL, S, "store texts", f"TODO: {cfg['store']['texts']}/<locale>.json missing for {len(missing)} locale(s) "
                                      f"({', '.join(missing[:4])}{'…' if len(missing) > 4 else ''})")
    elif bad:
        R.add(FAIL, S, "store texts", "; ".join(bad[:4]))
    else:
        R.add(PASS, S, "store texts", f"{len(cfg['store']['locales'])} locales with name/subtitle/description")
        kw = gdir / cfg["store"]["keywords"]
        meta = gdir / "tools/release/meta.py"
        if not kw.exists():
            R.add(FAIL, S, "keywords", f"TODO: {cfg['store']['keywords']} missing")
        elif meta.exists() and not quick:
            ok, msg = run_cmd(gdir, ["tools/release/meta.py", "audit"])
            R.add(PASS if ok else FAIL, S, "store audit (meta.py audit: limits, banned words, keywords, IAP texts)", msg)
        md = gdir / "fastlane/metadata"
        nomd = [loc for loc in cfg["store"]["locales"] if not (md / loc / "name.txt").exists()]
        R.add(FAIL if nomd else PASS, S, "fastlane/metadata written",
              f"TODO: run tools/release/meta.py write ({len(nomd)} locale(s) missing)" if nomd else "")


def _art_checks(R, gdir, cfg, T):
    man = gdir / "art/MANIFEST.json"
    if not man.exists():
        R.add(FAIL, T, "art manifest", "art/MANIFEST.json missing")
        return
    entries = json.loads(man.read_text(encoding="utf-8")).get("entries", [])
    shipped = [e for e in entries if e.get("status") in ("done", "graded") and e.get("file")]
    missing, wrong = [], []
    for e in shipped:
        p = gdir / e["file"]
        if not p.exists():
            missing.append(e["file"])
            continue
        if e.get("rig"):
            if not (p / "rig.json").exists():
                missing.append(e["file"] + "/rig.json")
            continue
        if p.suffix != ".png":
            continue
        size = png_size(p)
        if e.get("exact_px"):
            want = tuple(e["exact_px"])
        elif e.get("size_pt"):
            k = 3 * e.get("render_scale", 1)
            want = (round(e["size_pt"][0] * k), round(e["size_pt"][1] * k))
        else:
            want = None
        if size is None or (want and (abs(size[0] - want[0]) > 1 or abs(size[1] - want[1]) > 1)):
            wrong.append(f"{e['file']} {size} want {want}")
    if missing:
        R.add(FAIL, T, "shipped art files", f"TODO: {len(missing)} of {len(shipped)} missing (e.g. {missing[0]}); "
                                             "render the skin (art/PIPELINE.md)")
    elif wrong:
        R.add(FAIL, T, "shipped art sizes", f"{len(wrong)} wrong: {wrong[0]}")
    else:
        R.add(PASS, T, "shipped art files", f"{len(shipped)} done/graded entries present at their size")
    icon = gdir / "App/Resources/Assets.xcassets/AppIcon.appiconset"
    cj = icon / "Contents.json"
    if cj.exists():
        files = [i.get("filename") for i in json.loads(cj.read_text(encoding="utf-8")).get("images", []) if i.get("filename")]
        miss = [f for f in files if not (icon / f).exists()]
        R.add(FAIL if miss or not files else PASS, T, "app icon",
              f"TODO: {miss} missing" if miss else (f"{len(files)} images" if files else "no image listed"))
    else:
        R.add(FAIL, T, "app icon", "AppIcon.appiconset/Contents.json missing")


def _leftover_checks(R, repo, gdir, cfg, M):
    others = other_identities(repo, cfg["id"])
    if not others:
        R.add(PASS, M, "no identity of another game", "no other game under apps/ to compare with")
        return
    hits = {}
    pats = [(o["slug"], k, rx) for o in others for k, rx in identity_patterns(o)]
    own = identity_patterns({"slug": cfg["id"], "bundle": cfg["identity"]["bundle_id"],
                             "product": cfg["identity"]["product"], "brand": cfg["identity"]["brand_name"]})
    for p in iter_text_files(gdir):
        t = read_text(p)
        if not t:
            continue
        for slug, k, rx in pats:
            for m in rx.finditer(t):
                # an old value that is a prefix of ours (com.x.game vs com.x.game2) is not a leftover
                if any(o_rx.match(t, m.start()) and len(o_rx.match(t, m.start()).group(0)) > len(m.group(0))
                       for _, o_rx in own):
                    continue
                hits.setdefault((slug, k), []).append(p.relative_to(gdir).as_posix())
                break
    if hits:
        for (slug, k), files in sorted(hits.items()):
            R.add(FAIL, M, f"leftover {k} of apps/{slug}", f"{len(files)} file(s), e.g. {files[0]}")
    else:
        R.add(PASS, M, "no identity of another game",
              "checked " + ", ".join(f"apps/{o['slug']} ({o.get('bundle')})" for o in others))


# ================================================================================================= generate
def plan_generate(repo: Path, slug: str, cfg: dict | None = None) -> dict[Path, tuple[str, str, list[str]]]:
    """-> {path: (old text, new text, [what changed])} for every file generate would change."""
    gdir = game_dir(repo, slug)
    cfg = cfg or load_game(repo, slug)
    probs = validate(cfg, slug)
    if probs:
        raise ConfigError("game.yml invalid:\n  " + "\n  ".join(probs))
    texts: dict[Path, list] = {}  # path -> [old, new, notes]

    def cur(p):
        if p not in texts:
            t = p.read_text(encoding="utf-8")
            texts[p] = [t, t, []]
        return texts[p]

    # 1. an old bundle id (the one project.yml carries now) -> the new one, everywhere in code/config
    py = gdir / "project.yml"
    if py.exists():
        m = re.search(r"PRODUCT_BUNDLE_IDENTIFIER: *([A-Za-z0-9.-]+?)(?:\.tests|\.uitests)?[ \t]*$", py.read_text("utf-8"), re.M)
        old = m.group(1) if m else None
        new = cfg["identity"]["bundle_id"]
        if old and old != new:
            rx = re.compile(re.escape(old) + r"(?![A-Za-z0-9-])")
            for p in iter_text_files(gdir):
                t = read_text(p) if p.name != "game.yml" else None
                if t and rx.search(t):
                    e = cur(p)
                    e[1] = rx.sub(new, e[1])
                    e[2].append(f"bundle id {old} -> {new}")
        # the brand name the same way (docstrings, test expectations, review notes, name substitutions)
        m = re.search(r'PC_BRAND_NAME: *"([^"]*)"', py.read_text("utf-8"))
        oldb, newb = (m.group(1) if m else None), cfg["identity"]["brand_name"]
        if oldb and oldb != newb:
            rx = re.compile(r"(?<![A-Za-z0-9])" + re.escape(oldb) + r"(?![A-Za-z0-9])")
            for p in iter_text_files(gdir):
                t = read_text(p) if p.name != "game.yml" else None
                if t and rx.search(t):
                    e = cur(p)
                    e[1] = rx.sub(newb, e[1])
                    e[2].append(f"brand {oldb!r} -> {newb!r}")
    # 2. every anchored value
    for a in anchors(cfg):
        if not a.write:
            continue
        for p in a.files(gdir):
            e = cur(p)
            try:
                t2 = a.apply(e[1], cfg)
            except JSONSpanError:
                continue
            if t2 != e[1]:
                e[1] = t2
                e[2].append(a.key)
            if "*" not in a.file:
                break
    return {p: (o, n, notes) for p, (o, n, notes) in texts.items() if o != n}


def generate(repo: Path, slug: str, check: bool, out=sys.stdout) -> int:
    plan = plan_generate(repo, slug)
    gdir = game_dir(repo, slug)
    if not plan:
        print(f"generate: apps/{slug} already matches game.yml (0 files to change)", file=out)
        return 0
    for p, (old, new, notes) in sorted(plan.items()):
        rel = p.relative_to(gdir).as_posix()
        print(f"{'would change' if check else 'changed'} {rel}: {', '.join(dict.fromkeys(notes))}", file=out)
        if check:
            for line in difflib.unified_diff(old.splitlines(), new.splitlines(), f"a/{rel}", f"b/{rel}", n=0, lineterm=""):
                if not line.startswith(("---", "+++", "@@")):
                    print("    " + line[:200], file=out)
        else:
            p.write_text(new, encoding="utf-8")
    print(f"generate: {len(plan)} file(s) {'differ (--check: nothing written)' if check else 'written'}", file=out)
    return 1 if check else 0


# ================================================================================================= new
# What `new` copies from the reference game. Everything else (research/, PLAN.md, SPEC.md, design notes and spikes,
# release evidence, store texts, captions, keywords, screenshots, rendered art, the app icon) is NOT copied: it is the
# reference game's history or its own content, and doctor lists what the new game must make (TODO).
COPY_ALWAYS = [
    ".gitignore",                       # the game's own ignores (research media, build outputs, tool work folders)
    "project.yml",                      # the Xcode project definition (identity rewritten)
    "App",                              # the shell + meta systems + (until phase 1) the puzzle's board code; tuning,
                                        #   strings, fonts, sounds, social name data, .storekit
    "Packages",                         # the pure-Swift core (GameCore + the puzzle module)
    "Tests", "UITests",                 # the regression suites (adapt the puzzle-specific ones)
    "tools",                            # build/run/test/gen, strings, release, capture, store, bench + gates, levels, skin
    "skin",                             # the skin (colors/fonts/names .json, docs/SKIN.md): reskin it, never start empty
    "art/PIPELINE.md", "art/STYLE.md", "art/ID-MAP.md",
    "art/MANIFEST.json",                # the art SLOT list: which graphics the game needs (the files are not copied)
    "art/tools", "art/pipeline",        # the art toolchain
    "art/ui/code",                      # GlossyChrome.swift, compiled into the app
    "art/ui/recipes", "art/ui/src", "art/ui/tools", "art/ui/CASES.txt",   # generators to re-render with the new skin
    "design/ui-tokens.json", "design/ui-tokens-2.json", "design/fonts.md", "design/fonts",   # skin tokens + fonts
    "design/social",                    # the social world's data (simulated players, countries; tests read it)
    "design/publish/iap.json",          # the IAP catalogue (ids rewritten; prices/grants are a starting point)
    "fastlane/Appfile", "fastlane/Deliverfile", "fastlane/Fastfile", "fastlane/README.md",
    "fastlane/metadata/app_privacy_details.json", "fastlane/metadata/app_rating_config.json",
    "fastlane/metadata/copyright.txt", "fastlane/metadata/review_information",
]
# Copied only when the new game uses the SAME puzzle module (else App/Resources/Levels is emptied):
COPY_SAME_PUZZLE = ["design/levels.json", "design/level-order.json", "design/LEVELS.md", "design/tools"]
# Never copied from inside the trees above:
_IGNORE_NAMES = shutil.ignore_patterns("__pycache__", ".build", "build", "DerivedData", "*.xcodeproj", ".DS_Store",
                                       "report.xml", ".swiftpm")
COPY_SKIP_REL = {"design/tools/work"}   # git-ignored tool outputs inside copied trees


def _copy_ignore(sdir: Path):
    def ignore(root, names):
        rel = Path(root).relative_to(sdir).as_posix()
        skip = set(_IGNORE_NAMES(root, names))
        return skip | {n for n in names if (f"{rel}/{n}" if rel != "." else n) in COPY_SKIP_REL}
    return ignore
ICON_PNGS = "App/Resources/Assets.xcassets/AppIcon.appiconset"


def rename_tokens(text: str, old: dict, new: dict) -> str:
    """The reference's identity -> the new game's, in one code/config text (README §4 rows 1-4): bundle id, product
    (and <product>Tests / <product>.app / `import <product>`; not art ids like logo<Product>), apps/<slug> paths, the
    brand name, and the bundle's lowercase last segment (sku, profile, RevenueCat offering, temp-file prefixes)."""
    text = re.sub(re.escape(old["bundle"]) + r"(?![A-Za-z0-9-])", new["bundle"], text)
    if old.get("brand"):
        text = re.sub(r"(?<![A-Za-z0-9])" + re.escape(old["brand"]) + r"(?![A-Za-z0-9])", new["brand"], text)
    seg_o, seg_n = old["bundle"].rsplit(".", 1)[1], new["bundle"].rsplit(".", 1)[1]
    if not any(seg_o in b.lower() for b in old.get("bans", [])):
        text = re.sub(r"(?<![A-Za-z0-9.])" + re.escape(seg_o) + r"(?![A-Za-z0-9])", seg_n, text)
    text = re.sub(r"(?<![A-Za-z0-9])" + re.escape(old["product"]) + r"(?![a-z0-9])", new["product"], text)
    text = re.sub(r"apps/" + re.escape(old["slug"]) + r"(?![A-Za-z0-9-])", "apps/" + new["slug"], text)
    return text


def yml_set(text: str, key: str, value: str) -> str:
    """Replace the scalar of `key:` (first occurrence, keeps the inline comment)."""
    rx = re.compile(r"^(\s*" + re.escape(key) + r":[ \t]*)(\"[^\"]*\"|[^#\n]*?)([ \t]*(#.*)?)$", re.M)
    m = rx.search(text)
    if not m:
        raise ConfigError(f"game.yml template has no '{key}:'")
    return text[:m.start(2)] + value + text[m.end(2):]


def yml_set_list(text: str, key: str, items: list[str], indent: str) -> str:
    """Replace the block list under `key:` ("- item" lines, comments between them kept out); [] -> `key: []`."""
    rx = re.compile(r"^([ \t]*" + re.escape(key) + r":)([^\n]*\n)((?:[ \t]*#[^\n]*\n)*)((?:[ \t]*- [^\n]*\n)+)", re.M)
    m = rx.search(text)
    if not m:
        raise ConfigError(f"game.yml template has no '{key}:' block list")
    if not items:
        rest = m.group(2).strip()
        head = m.group(1) + " []" + (" " + rest if rest.startswith("#") else "") + "\n"
        return text[:m.start()] + head + m.group(3) + text[m.end():]
    return text[:m.start(4)] + "".join(f"{indent}- {i}\n" for i in items) + text[m.end(4):]


def new_game(repo: Path, slug: str, src: str, name: str, bundle: str, product=None, store_name=None, puzzle=None,
             privacy_url=None, bans=None, out=sys.stdout) -> Path:
    if not RE_SLUG.match(slug):
        raise ConfigError(f"slug {slug!r}: use [a-z][a-z0-9-]*")
    if not RE_BUNDLE.match(bundle):
        raise ConfigError(f"bundle {bundle!r} is not a reverse-DNS id")
    sdir, ndir = game_dir(repo, src), game_dir(repo, slug)
    if ndir.exists():
        raise ConfigError(f"apps/{slug} already exists")
    scfg = load_game(repo, src)
    sp = validate(scfg, src)
    if sp:
        raise ConfigError(f"apps/{src}/game.yml invalid: {sp[0]}")
    product = product or camel(name)
    if not RE_PRODUCT.match(product):
        raise ConfigError(f"product {product!r}: CamelCase letters/digits")
    store_name = store_name or name
    puzzle = puzzle or scfg["puzzle"]["module"]
    same_puzzle = puzzle == scfg["puzzle"]["module"]
    old = {"slug": src, "bundle": scfg["identity"]["bundle_id"], "product": scfg["identity"]["product"],
           "brand": scfg["identity"]["brand_name"], "bans": scfg["brand_bans"]}
    newi = {"slug": slug, "bundle": bundle, "product": product, "brand": name}

    # 1. copy
    ndir.mkdir(parents=True)
    copied = []
    for rel in COPY_ALWAYS + (COPY_SAME_PUZZLE if same_puzzle else []):
        s = sdir / rel
        if not s.exists():
            continue
        d = ndir / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        if s.is_dir():
            shutil.copytree(s, d, ignore=_copy_ignore(sdir))
        else:
            shutil.copy2(s, d)
        copied.append(rel)
    # rendered skin is not the new game's: the app icon images go (Contents.json stays: the slots)
    for png in (ndir / ICON_PNGS).glob("*.png"):
        png.unlink()
    if not same_puzzle:
        lv = ndir / scfg["puzzle"]["levels_bundle"]
        if lv.is_dir():
            shutil.rmtree(lv)
        lv.mkdir(parents=True, exist_ok=True)
        (lv / ".gitkeep").write_text("")
    # 2. rename the identity in code/config, and the files named after the product
    for p in iter_text_files(ndir):
        t = read_text(p)
        if t is None:
            continue
        t2 = rename_tokens(t, old, newi)
        if t2 != t:
            p.write_text(t2, encoding="utf-8")
    for p in sorted(ndir.rglob(f"*{old['product']}*"), key=lambda x: -len(x.parts)):
        if re.search(r"(?<![A-Za-z0-9])" + re.escape(old["product"]) + r"(?![a-z0-9])", p.name):
            p.rename(p.with_name(re.sub(r"(?<![A-Za-z0-9])" + re.escape(old["product"]) + r"(?![a-z0-9])",
                                        product, p.name)))
    # 3. game.yml: the reference's (its comments are the documentation) with the new identity
    t = (sdir / "game.yml").read_text(encoding="utf-8")
    old_privacy = scfg["store"]["privacy_url"]
    privacy = privacy_url or old_privacy.replace(kebab(scfg["identity"]["brand_name"]), kebab(name))
    sets = {
        "id": slug, "brand_name": json.dumps(name), "product": product, "bundle_id": bundle,
        "profile_name": json.dumps(f"{bundle_org(bundle).split('.')[-1]} {bundle.rsplit('.', 1)[1]} appstore"),
        "module": puzzle, "name": json.dumps(store_name), "keyword_seed": json.dumps(name.lower()),
        "privacy_url": json.dumps(privacy),
    }
    for k, v in sets.items():
        t = yml_set(t, k, v)
    t = re.sub(r"^derived_from:[^\n]*\n", "", t, flags=re.M)
    t = re.sub(r"^(id:[^\n]*\n)", r"\1derived_from: " + src +
               "              # the game `game.py new` copied (doctor warns while content is still identical)\n", t,
               count=1, flags=re.M)
    if bans:
        t = yml_set_list(t, "brand_bans", [json.dumps(b) for b in bans], indent="  ")
    if not same_puzzle:
        t = yml_set_list(t, "checks", [], indent="    ")
    (ndir / "game.yml").write_text(t, encoding="utf-8")
    cfg = load_game(repo, slug)
    probs = validate(cfg, slug)
    if probs:
        raise ConfigError("the new game.yml is invalid: " + "; ".join(probs))
    # 4. write every repeated value
    for p, (_, new_text, _) in plan_generate(repo, slug, cfg).items():
        p.write_text(new_text, encoding="utf-8")
    print(f"new: apps/{slug} from apps/{src} ({'same' if same_puzzle else 'NEW'} puzzle module {puzzle})", file=out)
    print(f"  copied: {', '.join(copied)}", file=out)
    print("  not copied: research/, PLAN.md, SPEC.md, design notes/spikes, store texts, captions, keywords, "
          "screenshots, rendered art (art/out, art/ui/out, art/review), app icon images"
          + ("" if same_puzzle else ", levels + level tools"), file=out)
    print(f"  next: python3 tools/game.py doctor --game {slug}   (docs/TEMPLATE.md)", file=out)
    return ndir


# ================================================================================================= CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path, default=REPO, help=argparse.SUPPRESS)  # tests / scratch copies
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("doctor", help="check a game folder")
    d.add_argument("--game", required=True)
    d.add_argument("--quick", action="store_true", help="skip the slow checks (puzzle level checks, store audit)")
    d.add_argument("--strict", action="store_true", help="WARN also fails")
    g = sub.add_parser("generate", help="write game.yml values into the files that repeat them")
    g.add_argument("--game", required=True)
    g.add_argument("--check", action="store_true", help="only report what would change")
    n = sub.add_parser("new", help="scaffold apps/<slug> from an existing game")
    n.add_argument("slug")
    n.add_argument("--from", dest="src", required=True)
    n.add_argument("--name", required=True, help="brand / display name")
    n.add_argument("--bundle", required=True)
    n.add_argument("--product", help="Xcode product name (default: the name in CamelCase)")
    n.add_argument("--store-name", help="en-US App Store name (default: the name)")
    n.add_argument("--puzzle", help="puzzle module id (default: the source game's)")
    n.add_argument("--privacy-url", help="privacy page (default: the source's with the brand swapped)")
    n.add_argument("--bans", help="the NEW original's names, comma-separated (default: keep the source's)")
    a = ap.parse_args(argv)
    repo = a.repo.resolve()
    try:
        if a.cmd == "doctor":
            R = doctor(repo, a.game, quick=a.quick)
            print(R.render(f"doctor apps/{a.game}"))
            if any(i[2] in ("load", "schema") and i[0] == FAIL for i in R.items):
                return 2
            return 1 if R.count(FAIL) or (a.strict and R.count(WARN)) else 0
        if a.cmd == "generate":
            return generate(repo, a.game, a.check)
        if a.cmd == "new":
            new_game(repo, a.slug, a.src, a.name, a.bundle, a.product, a.store_name, a.puzzle, a.privacy_url,
                     [b.strip() for b in a.bans.split(",") if b.strip()] if a.bans else None)
            return 0
    except ConfigError as e:
        print(f"game.py: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
