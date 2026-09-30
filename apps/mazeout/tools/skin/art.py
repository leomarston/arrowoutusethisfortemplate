#!/usr/bin/env python3
"""tools/skin/art.py — the skin's art SLOTS and SCENES (docs/SKIN.md §4).

    python3 tools/skin/art.py              # validate skin/art.json + skin/scenes.json, write the two generated Swift files
    python3 tools/skin/art.py --check      # (CI) validate + fail if a generated file is stale or a Swift source breaks the
                                           #      slot rules (below)
    python3 tools/skin/art.py --list       # slot -> file table
    python3 tools/skin/art.py --selftest

skin/art.json    {"slots": {"<slot id>": "<art/MANIFEST.json raster id>", …},
                  "rigs":  {"<rig slot id>": "<art/MANIFEST.json rig id>", …}}
  A slot says what a raster is FOR (`home.backdrop`, `currency.coin.icon`, `avatar.3`, `event.skyJump.badge`); the manifest
  id names the file that fills it in this skin (its file, size and group come from art/MANIFEST.json). Slot ids are dotted
  words ([a-z][A-Za-z0-9]*(.[A-Za-z0-9]+)*); the Swift case is the id camel-cased (`currency.coin.icon` ->
  `UIArt.currencyCoinIcon`), its raw value the id itself. Two slots may share a file.
skin/scenes.json  the home scene (`home.back` / `home.front` layer lists, back to front), the rig part sets (`rigParts`)
  and the Loading scene (`loading`: backdrop, logo, cast); see its "about".

Generated (never edit):
  App/Shell/Components/UIArt.swift                 `enum UIArt` (one case per slot: asset, path, sizePt, group) and
                                                   `enum ArtRig` (one case per rig slot: folder)
  App/Shell/Components/SkinScenes.generated.swift  `enum SkinScenes` (the scene layer lists, the Loading cast)
tools/uiart_gen.py writes UIArt.swift through this module (its --check stays CI's art-index check; its --exclude-list, the
never-ships rule of tools/sync_art.sh, is unchanged).

--check fails on (besides the JSON rules and stale output):
  - a shipped raster of the manifest (tools/uiart_gen.py's rule) that no slot maps, or a shipped rig no rig slot maps: the
    bundle would carry a file no code can draw (UIArtBundleTests);
  - a slot whose file is missing from art/ui/out or art/out (the bundle sources), or a rig without its rig.json;
  - a slot the Swift sources name as a string that art.json lacks: `UIArt(rawValue: "<slot>")`, the string constants of
    `enum UpAwayArt`, and every image id of ui.json `win.logo` (read as the slot `logo.part.<id>`);
  - a Swift source (App/, art/ui/code/) that names an art FILE instead of a slot: a string literal holding a manifest id, a
    rig folder, "@3x", ".png", or a "UI/" / "Art/" bundle path. tools/skin/art_allowlist.json lists the few files that must
    (the puzzle module's sprite catalogue, the rig loader, the logo spec's part names), each with its reason; an entry that
    no longer matches anything fails as stale.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import skinlib as S          # noqa: E402  (the Swift lexer, swift_name)
import uiart_gen as U        # noqa: E402  (the manifest's never-ships rule)

APP = S.APP
ART_JSON = os.path.join(APP, "skin", "art.json")
SCENES_JSON = os.path.join(APP, "skin", "scenes.json")
MANIFEST = os.path.join(APP, "art", "MANIFEST.json")
UI_JSON = os.path.join(APP, "App", "Resources", "Tuning", "ui.json")
UIART_SWIFT = os.path.join(APP, "App", "Shell", "Components", "UIArt.swift")
SCENES_SWIFT = os.path.join(APP, "App", "Shell", "Components", "SkinScenes.generated.swift")
ALLOWLIST = os.path.join(HERE, "art_allowlist.json")
SCAN_DIRS = ["App", "art/ui/code"]
LOGO_SLOT_PREFIX = "logo.part."

SLOT_ID = re.compile(r"^[a-z][A-Za-z0-9]*(\.[A-Za-z0-9]+)*$")
SWIFT_KEYWORDS = U.SWIFT_KEYWORDS | {"true", "false", "nil", "init", "super", "static", "inout", "operator", "throws",
                                      "rethrows", "public", "private", "internal", "fileprivate", "open", "some", "any"}


def rel(p):
    return os.path.relpath(p, APP)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def swift_case(slot):
    return S.swift_name(slot)


# ============================================================================================ the manifest side

class Manifest:
    """Shipped rasters (id -> bundle path, size, group, source file) and shipped rigs (id -> folder)."""

    def __init__(self, doc, root=APP, build_only=None):
        extra = U.build_only() if build_only is None else build_only
        self.all_ids, self.file_ids = set(), set()
        self.rasters, self.rigs, self.rig_sources = {}, {}, {}
        for e in doc.get("entries", []):
            eid = e.get("id")
            if not eid:
                continue
            self.all_ids.add(eid)
            if e.get("family") in ("svg", "3d") and e.get("file"):
                self.file_ids.add(eid)                    # art with a file (code / SwiftUI entries are drawn, not files)
            path = U.shipped(e, extra)
            if path:
                w, h = (e.get("size_pt") or [0, 0])[:2]
                self.rasters[eid] = {"path": path, "w": float(w), "h": float(h), "group": e.get("group", ""),
                                     "file": os.path.join(root, e["file"])}
                continue
            f = (e.get("file") or "").rstrip("/")
            if f.startswith("art/out/") and f.endswith("_rig") and not U.never_ships(e, extra):
                self.rigs[eid] = os.path.basename(f)
                self.rig_sources[eid] = os.path.join(root, f)

    @property
    def rig_folders(self):
        return set(self.rigs.values())


def load_manifest():
    return Manifest(load_json(MANIFEST))


# ============================================================================================ validation

def check_art(art, man, check_files=True):
    errs = []
    if not isinstance(art, dict) or not isinstance(art.get("slots"), dict) or not isinstance(art.get("rigs"), dict):
        return ["art.json needs 'slots' {slot: manifest raster id} and 'rigs' {rig slot: manifest rig id}"]
    for section, known in (("slots", man.rasters), ("rigs", man.rigs)):
        cases = {}
        for slot, asset in art[section].items():
            where = f"art.json {section} {slot!r}"
            if not SLOT_ID.match(slot):
                errs.append(f"{where}: a slot id is dotted words [a-z][A-Za-z0-9]*(.[A-Za-z0-9]+)*")
                continue
            case = swift_case(slot)
            if case in SWIFT_KEYWORDS:
                errs.append(f"{where}: its Swift name {case!r} is a keyword")
            if case in cases:
                errs.append(f"{where}: its Swift name {case} is also {cases[case]!r}'s")
            cases[case] = slot
            if not isinstance(asset, str) or asset not in known:
                kind = "raster (family svg/3d, a shipped @3x.png)" if section == "slots" else "rig (an art/out/*_rig folder)"
                why = "retired / build-only (it never ships)" if asset in man.all_ids else "not in art/MANIFEST.json"
                errs.append(f"{where}: {asset!r} is not a shipped manifest {kind}: {why}")
                continue
            if check_files and section == "slots" and not os.path.isfile(known[asset]["file"]):
                errs.append(f"{where}: its file {rel(known[asset]['file'])} does not exist (render it: art/PIPELINE.md)")
            if check_files and section == "rigs" and not os.path.isfile(os.path.join(man.rig_sources[asset], "rig.json")):
                errs.append(f"{where}: {rel(man.rig_sources[asset])}/rig.json does not exist")
        unmapped = sorted(set(known) - set(art[section].values()))
        if unmapped:
            errs.append(f"art.json {section}: shipped manifest ids no slot maps (they would ship with no code to draw them; "
                        f"map a slot or retire them in the manifest / tools/art_build_only.txt): {unmapped}")
    return errs


def _frame_value(ui, key):
    v = ui.get("frames") if isinstance(ui, dict) else None
    for p in key.split("."):
        v = v.get(p) if isinstance(v, dict) else None
    return v


def _rect(v):
    return isinstance(v, list) and len(v) == 4 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v)


def check_scenes(sc, art, ui):
    errs = []
    if not isinstance(sc, dict):
        return ["scenes.json must be an object"]
    slots, rigs = art.get("slots", {}), art.get("rigs", {})
    parts = sc.get("rigParts", {})
    if not isinstance(parts, dict):
        errs.append("scenes.json rigParts: {rig slot: {set name: [layer names]}}")
        parts = {}
    for rig, sets in parts.items():
        if rig not in rigs:
            errs.append(f"scenes.json rigParts: {rig!r} is not a rig slot of art.json")
        if not isinstance(sets, dict) or not all(isinstance(v, list) and v and all(isinstance(x, str) for x in v)
                                                 for v in sets.values()):
            errs.append(f"scenes.json rigParts {rig}: {{set name: [layer names]}}")
    home = sc.get("home")
    if not isinstance(home, dict) or not isinstance(home.get("back"), list) or not isinstance(home.get("front"), list):
        errs.append("scenes.json home: {back: [layers], front: [layers]}")
        home = {"back": [], "front": []}
    for lst in ("back", "front"):
        for i, layer in enumerate(home[lst]):
            where = f"scenes.json home.{lst}[{i}]"
            if not isinstance(layer, dict):
                errs.append(f"{where}: a layer is an object")
                continue
            kinds = [k for k in ("art", "rig", "centrepiece") if k in layer]
            if len(kinds) != 1:
                errs.append(f"{where}: exactly one of art / rig / centrepiece")
                continue
            kind = kinds[0]
            ref = layer[kind]
            if kind == "art" and ref not in slots:
                errs.append(f"{where}: art {ref!r} is not a slot of art.json")
            if kind != "art" and ref not in rigs:
                errs.append(f"{where}: {kind} {ref!r} is not a rig slot of art.json")
            known = {"art", "rig", "centrepiece", "frame", "at", "fill", "only", "excluding"}
            extra = sorted(set(layer) - known)
            if extra:
                errs.append(f"{where}: unknown keys {extra}")
            if kind in ("art", "centrepiece") and not _rect(layer.get("at")):
                errs.append(f"{where}: 'at' [x, y, w, h] (pt) is required for {kind}")
            if kind == "rig" and ("at" in layer or "frame" in layer or "fill" in layer):
                errs.append(f"{where}: a rig is placed by its rig.json (no at / frame / fill)")
            if "frame" in layer:
                if not isinstance(layer["frame"], str) or not _rect(_frame_value(ui, layer["frame"])):
                    errs.append(f"{where}: frame {layer.get('frame')!r} is not a 4-number ui.json frames key")
            if "fill" in layer and not isinstance(layer["fill"], bool):
                errs.append(f"{where}: fill is true / false")
            if layer.get("fill") and kind != "art":
                errs.append(f"{where}: only art fills")
            if layer.get("fill") and "frame" in layer:
                errs.append(f"{where}: a fill layer is drawn over 'at' (no frame key)")
            for k in ("only", "excluding"):
                if k in layer:
                    if kind != "rig":
                        errs.append(f"{where}: {k} applies to a rig")
                    elif layer[k] not in (parts.get(ref) or {}):
                        errs.append(f"{where}: {k} {layer[k]!r} is not a rigParts set of {ref}")
            if "only" in layer and "excluding" in layer:
                errs.append(f"{where}: only OR excluding")
    loading = sc.get("loading")
    if not isinstance(loading, dict):
        errs.append("scenes.json loading: {backdrop, logo, cast}")
        loading = {}
    for k in ("backdrop", "logo"):
        if loading.get(k) not in slots:
            errs.append(f"scenes.json loading.{k}: {loading.get(k)!r} is not a slot of art.json")
    cast = loading.get("cast")
    if not isinstance(cast, list):
        errs.append("scenes.json loading.cast: [{art, at}] back to front")
        cast = []
    for i, c in enumerate(cast):
        if not isinstance(c, dict) or c.get("art") not in slots or not _rect(c.get("at")) or set(c) != {"art", "at"}:
            errs.append(f"scenes.json loading.cast[{i}]: {{art: <slot>, at: [x, y, w, h]}}")
    return errs


# ============================================================================================ generation

def _num(v):
    v = float(v)
    return str(int(v)) if v.is_integer() else repr(v)


def _rect_swift(r):
    return f"CGRect(x: {_num(r[0])}, y: {_num(r[1])}, width: {_num(r[2])}, height: {_num(r[3])})"


def _str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def generate_uiart(art, man):
    rows = sorted(art["slots"].items())
    rigs = sorted(art["rigs"].items())
    files = len({man.rasters[a]["path"] for _, a in rows})
    L = ["import CoreGraphics", "",
         "// GENERATED by tools/skin/art.py from skin/art.json (slot -> art/MANIFEST.json id) and art/MANIFEST.json (file, size,",
         "// group). Do not edit: edit skin/art.json, then run python3 tools/skin/art.py (docs/SKIN.md §4).",
         f"// {len(rows)} art slots ({files} files), {len(rigs)} rig slots. Loader + placeholder: ArtStore.swift.", "",
         "/// An art SLOT: what a raster is for (`home.backdrop`, `currency.coin.icon`, `avatar.3` …). The raw value is the slot",
         "/// id of skin/art.json; the file that fills it is the skin's (`path`), so no Swift names a file.",
         "enum UIArt: String, CaseIterable, Sendable {"]
    for slot, _ in rows:
        L.append(f"    case {swift_case(slot)} = {_str(slot)}")

    def switch(doc, typ, name, fn):
        L.append("")
        L.append(f"    /// {doc}")
        L.append(f"    var {name}: {typ} {{")
        L.append("        switch self {")
        for slot, asset in rows:
            L.append(f"        case .{swift_case(slot)}: return {fn(asset)}")
        L.append("        }")
        L.append("    }")

    switch("The art/MANIFEST.json id of the file the skin maps this slot to.", "String", "asset", _str)
    switch("The file inside the app bundle (tools/sync_art.sh: art/ui/out -> UI/, art/out -> Art/).", "String", "path",
           lambda a: _str(man.rasters[a]["path"]))
    switch("The manifest size in pt (the @3x file is 3x this).", "CGSize", "sizePt",
           lambda a: f"CGSize(width: {man.rasters[a]['w']:g}, height: {man.rasters[a]['h']:g})")
    switch("The manifest group (placeholder tint, preload sets).", "String", "group", lambda a: _str(man.rasters[a]["group"]))
    L.append("}")
    L.append("")
    L.append("/// A puppet RIG slot (skin/art.json `rigs`): its folder under the bundle's Art/ (`PuppetRig.load`; its motion is")
    L.append("/// ui.json `puppet.<folder>`).")
    L.append("enum ArtRig: String, CaseIterable, Sendable {")
    for slot, _ in rigs:
        L.append(f"    case {swift_case(slot)} = {_str(slot)}")
    L.append("")
    L.append("    /// The rig folder (art/out/<folder>/rig.json -> Art/<folder>/rig.json).")
    L.append("    var folder: String {")
    L.append("        switch self {")
    for slot, asset in rigs:
        L.append(f"        case .{swift_case(slot)}: return {_str(man.rigs[asset])}")
    L.append("        }")
    L.append("    }")
    L.append("}")
    L.append("")
    return "\n".join(L)


def generate_scenes(sc):
    parts = sc.get("rigParts", {})

    def layer(d):
        if "art" in d:
            kind = f".art(.{swift_case(d['art'])})"
        elif "rig" in d:
            kind = f".rig(.{swift_case(d['rig'])})"
        else:
            kind = f".centrepiece(.{swift_case(d['centrepiece'])})"
        rig = d.get("rig")
        only = parts.get(rig, {}).get(d["only"], []) if "only" in d else []
        excl = parts.get(rig, {}).get(d["excluding"], []) if "excluding" in d else []
        lst = lambda xs: "[" + ", ".join(_str(x) for x in xs) + "]"
        rect = _rect_swift(d["at"]) if "at" in d else ".zero"
        return (f"        Layer(kind: {kind}, frameKey: {_str(d.get('frame', ''))}, rect: {rect}, "
                f"fill: {'true' if d.get('fill') else 'false'}, only: {lst(only)}, excluding: {lst(excl)}),")

    L = ["import CoreGraphics", "",
         "// GENERATED by tools/skin/art.py from skin/scenes.json. Do not edit: edit the JSON, then run python3 tools/skin/art.py",
         "// (docs/SKIN.md §4). No logic here: HomeView / LoadingScreen draw these lists.", "",
         "/// The skin's scenes: what the home and Loading scenes draw, back to front, on the 393 x 852 reference canvas.",
         "enum SkinScenes {",
         "    /// One layer of a scene.",
         "    struct Layer {",
         "        enum Kind {",
         "            case art(UIArt)             // a raster at `rect` (aspect fit; aspect fill over `rect` when `fill`)",
         "            case rig(ArtRig)            // a puppet at its rig.json placement (its motion: ui.json puppet.<folder>)",
         "            case centrepiece(ArtRig)    // home's centrepiece rig at `rect` (its idle loop and its refill steps)",
         "        }",
         "        let kind: Kind",
         "        /// The ui.json frames key that places it (\"\" = `rect` as is); `rect` is that key's default (pt).",
         "        let frameKey: String",
         "        let rect: CGRect",
         "        let fill: Bool",
         "        /// The rig layers this stage draws (empty = every layer) or leaves out (skin/scenes.json rigParts).",
         "        let only: [String]",
         "        let excluding: [String]",
         "    }",
         "",
         "    /// A raster at a fixed rect (pt on the reference canvas).",
         "    struct Placed {",
         "        let art: UIArt",
         "        let rect: CGRect",
         "    }",
         "",
         "    /// Home, behind the level controls: back to front.",
         "    static let homeBack: [Layer] = ["]
    L += [layer(d) for d in sc["home"]["back"]]
    L += ["    ]", "", "    /// Home, in front of the level controls (behind the top bar).", "    static let homeFront: [Layer] = ["]
    L += [layer(d) for d in sc["home"]["front"]]
    lo = sc["loading"]
    L += ["    ]", "",
          "    /// Loading: the full-bleed backdrop (aspect fill), the logo (at ui.json frames.loading.logo) and the cast, back to front.",
          f"    static let loadingBackdrop: UIArt = .{swift_case(lo['backdrop'])}",
          f"    static let loadingLogo: UIArt = .{swift_case(lo['logo'])}",
          "    static let loadingCast: [Placed] = ["]
    L += [f"        Placed(art: .{swift_case(c['art'])}, rect: {_rect_swift(c['at'])})," for c in lo["cast"]]
    L += ["    ]", "}", ""]
    return "\n".join(L)


def targets(art=None, sc=None, man=None):
    art = load_json(ART_JSON) if art is None else art
    sc = load_json(SCENES_JSON) if sc is None else sc
    man = load_manifest() if man is None else man
    return [(UIART_SWIFT, generate_uiart(art, man)), (SCENES_SWIFT, generate_scenes(sc))]


# ============================================================================================ the Swift sources

def swift_files(dirs=None, root=APP):
    out = []
    for d in dirs or SCAN_DIRS:
        base = os.path.join(root, d)
        for dp, dn, fn in os.walk(base):
            dn[:] = sorted(x for x in dn if not x.startswith("."))
            out += [os.path.join(dp, f) for f in sorted(fn) if f.endswith(".swift")]
    return out


RAW_LIT = re.compile(r'UIArt\(rawValue:\s*"([^"\\]*)"\s*\)')
UPAWAY = re.compile(r"\benum\s+UpAwayArt\b[^{]*\{")


def _block(text, start):
    """The text of the {…} block opening at text[start] ('{'), braces in comments / strings ignored by the caller's lexing."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
    return start, len(text)


def check_slot_references(art, ui, files=None, root=APP):
    """Slots the Swift sources name as STRINGS (the compiler checks `.case` references)."""
    slots = set(art.get("slots", {}))
    errs = []
    for p in files if files is not None else swift_files(root=root):
        text = open(p, encoding="utf-8").read()
        lx = S.swift_lex(text)
        for m in RAW_LIT.finditer(text):
            if lx.code[m.start()] != "U":
                continue                                   # inside a comment / string
            if m.group(1) not in slots:
                errs.append(f"{os.path.relpath(p, root)}:{lx.line_of(m.start())}: UIArt(rawValue: {m.group(1)!r}) is not a slot "
                            "of skin/art.json")
        for m in UPAWAY.finditer(lx.code):
            a, b = _block(lx.code, m.end() - 1)
            for s, e, content, interp in lx.strings:
                if a <= s < b and not interp and content not in slots:
                    errs.append(f"{os.path.relpath(p, root)}:{lx.line_of(s)}: UpAwayArt names {content!r}, not a slot of "
                                "skin/art.json")
    logo = (ui.get("win") or {}).get("logo") if isinstance(ui, dict) else None
    if isinstance(logo, dict):
        ids = set()
        for lid, layer in (logo.get("layers") or {}).items():
            ids.add(lid)
            ids.update((layer or {}).get("contents") or [])
        missing = sorted(i for i in ids if LOGO_SLOT_PREFIX + i not in slots)
        if missing:
            errs.append(f"ui.json win.logo: image ids with no slot {LOGO_SLOT_PREFIX}<id> in skin/art.json: {missing}")
    else:
        errs.append("ui.json win.logo missing: the win logo's image slots cannot be checked")
    return errs


def load_allowlist(path=ALLOWLIST):
    if not os.path.exists(path):
        return []
    return load_json(path).get("files", [])


def _allowed(relpath, allow):
    for a in allow:
        p = a["path"]
        if relpath == p or (p.endswith("/") and relpath.startswith(p)):
            return a
    return None


def file_name_hits(text, ids, folders):
    """(pos, line, content, why) for each string literal naming an art file: a manifest file id (the whole literal), a rig
    folder (a word of it), '@3x', '.png', or a 'UI/' / 'Art/' bundle path."""
    lx = S.swift_lex(text)
    hits = []
    for s, e, content, interp in lx.strings:
        words = set(re.findall(r"[A-Za-z0-9_]+", content))
        why = None
        if "@3x" in content or re.search(r"\.png\b", content):
            why = "a file name (@3x / .png)"
        elif re.match(r"^(UI|Art)/", content):
            why = "a bundle art path"
        elif words & folders:
            why = f"the rig folder {sorted(words & folders)[0]}"
        elif content in ids:
            why = f"the art file {content!r}"
        if why:
            hits.append((s, lx.line_of(s), content, why))
    return hits


def check_file_names(man, files=None, allow=None, root=APP):
    allow = load_allowlist() if allow is None else allow
    ids = man.file_ids
    folders = man.rig_folders | {os.path.basename(f) for f in man.rig_sources.values()}
    errs, used = [], set()
    for p in files if files is not None else swift_files(root=root):
        r = os.path.relpath(p, root)
        if os.path.abspath(p) in (UIART_SWIFT, SCENES_SWIFT):
            continue                                       # generated from the mapping itself
        hits = file_name_hits(open(p, encoding="utf-8").read(), ids, folders)
        if not hits:
            continue
        a = _allowed(r, allow)
        if a:
            used.add(a["path"])
            continue
        for _, line, content, why in hits:
            errs.append(f"{r}:{line}: \"{content}\" names {why}: ask for a slot (UIArt.<slot>, ArtRig.<slot>; skin/art.json)")
    for a in allow:
        if a["path"] not in used:
            errs.append(f"tools/skin/art_allowlist.json: {a['path']!r} is stale (no art file name there any more): remove it")
    return errs


# ============================================================================================ CLI

def validate_all(art=None, sc=None, man=None, ui=None, check_files=True):
    """The JSON rules. check_files=False leaves out whether each mapped file is rendered yet (build.py's use: a new game's
    skin is valid before its art exists; `game.py doctor` reports missing art as "shipped art files", art.py --check fails)."""
    art = load_json(ART_JSON) if art is None else art
    sc = load_json(SCENES_JSON) if sc is None else sc
    man = load_manifest() if man is None else man
    ui = load_json(UI_JSON) if ui is None else ui
    errs = check_art(art, man, check_files=check_files)
    if not errs:
        errs += check_scenes(sc, art, ui)
    return errs


def summary(art, sc):
    return (f"{len(art['slots'])} art slots, {len(art['rigs'])} rig slots, home {len(sc['home']['back'])} + "
            f"{len(sc['home']['front'])} layers, loading cast {len(sc['loading']['cast'])}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    art, sc, man, ui = load_json(ART_JSON), load_json(SCENES_JSON), load_manifest(), load_json(UI_JSON)
    errs = validate_all(art, sc, man, ui)
    if errs:
        print("\n".join(errs))
        sys.exit(1)
    if a.list:
        for slot, asset in sorted(art["slots"].items()):
            print(f"{slot:34} {asset:26} {man.rasters[asset]['path']}")
        for slot, asset in sorted(art["rigs"].items()):
            print(f"{slot:34} {asset:26} Art/{man.rigs[asset]}/")
        return
    stale = []
    for path, text in targets(art, sc, man):
        cur = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if cur != text:
            stale.append(path)
            if not a.check:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)
    if a.check:
        probs = check_slot_references(art, ui) + check_file_names(man)
        if stale:
            probs.insert(0, "stale (run python3 tools/skin/art.py): " + ", ".join(rel(p) for p in stale))
        if probs:
            print("\n".join(probs))
            sys.exit(1)
        print(f"art up to date: {summary(art, sc)}; Swift names slots, never files")
    else:
        print(f"wrote {', '.join(rel(p) for p in stale) or 'nothing (up to date)'}: {summary(art, sc)}")


# ============================================================================================ self-test

def selftest():
    fails = []

    def ok(cond, what):
        if not cond:
            fails.append(what)

    ok(swift_case("currency.coin.icon") == "currencyCoinIcon" and swift_case("avatar.0") == "avatar0", "swift_case")
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "art", "ui", "out"))
        os.makedirs(os.path.join(d, "art", "out", "hero_rig"))
        for f in ("art/ui/out/coinA@3x.png", "art/out/bgA@3x.png", "art/out/hero_rig/rig.json"):
            open(os.path.join(d, f), "w").close()
        mdoc = {"entries": [
            {"id": "coinA", "family": "svg", "file": "art/ui/out/coinA@3x.png", "size_pt": [30, 30], "group": "hud"},
            {"id": "bgA", "family": "3d", "file": "art/out/bgA@3x.png", "size_pt": [393, 852], "group": "home"},
            {"id": "oldA", "family": "svg", "file": "art/ui/out/oldA@3x.png", "status": "not-shipped"},
            {"id": "heroRig", "family": "3d", "file": "art/out/hero_rig"}]}
        man = Manifest(mdoc, root=d, build_only=set())
        ok(set(man.rasters) == {"coinA", "bgA"} and man.rigs == {"heroRig": "hero_rig"}, f"manifest {man.rasters} {man.rigs}")
        art = {"slots": {"hud.coin": "coinA", "home.backdrop": "bgA"}, "rigs": {"home.hero": "heroRig"}}
        ok(check_art(art, man) == [], f"check_art clean: {check_art(art, man)}")
        bad = {"slots": {"hud.coin": "coinA", "Bad id": "bgA", "hud.old": "oldA"}, "rigs": {}}
        e = check_art(bad, man)
        ok(any("dotted words" in x for x in e) and any("never ships" in x for x in e) and any("no slot maps" in x for x in e),
           f"check_art errors: {e}")
        ok(any("same" in x or "also" in x for x in check_art({"slots": {"a.b": "coinA", "aB": "bgA"}, "rigs": {"h": "heroRig"}},
                                                               man)), "check_art: two slots, one Swift name")
        os.remove(os.path.join(d, "art/out/bgA@3x.png"))
        ok(any("does not exist" in x for x in check_art(art, man)), "check_art: a missing file")
        ok(check_art(art, man, check_files=False) == [], "check_art without files")
        # generation
        g = generate_uiart(art, man)
        ok('case homeBackdrop = "home.backdrop"' in g and 'case .hudCoin: return "UI/coinA@3x.png"' in g
           and 'case .homeBackdrop: return "bgA"' in g and 'case homeHero = "home.hero"' in g
           and 'case .homeHero: return "hero_rig"' in g and "CGSize(width: 393, height: 852)" in g, "generate_uiart")
        ok(g.index("case homeBackdrop") < g.index("case hudCoin"), "generate_uiart: cases sorted by slot id")
        ui = {"frames": {"home": {"scene": {"stand": [1, 2, 3, 4]}}}, "win": {"logo": {"layers": {"logoA": {"contents": ["logoA", "logoB"]}}}}}
        sc = {"rigParts": {"home.hero": {"arms": ["armL"]}},
              "home": {"back": [{"art": "home.backdrop", "fill": True, "at": [0, 0, 393, 852]},
                                {"rig": "home.hero", "excluding": "arms"},
                                {"art": "hud.coin", "frame": "home.scene.stand", "at": [1, 2, 3, 4.5]},
                                {"centrepiece": "home.hero", "frame": "home.scene.stand", "at": [1, 2, 3, 4]}],
                       "front": [{"rig": "home.hero", "only": "arms"}]},
              "loading": {"backdrop": "home.backdrop", "logo": "hud.coin", "cast": [{"art": "hud.coin", "at": [-6, 434.5, 96, 76]}]}}
        ok(check_scenes(sc, art, ui) == [], f"check_scenes clean: {check_scenes(sc, art, ui)}")
        bad_sc = json.loads(json.dumps(sc))
        bad_sc["home"]["back"].append({"art": "nope", "at": [0, 0, 1, 1]})
        bad_sc["home"]["back"].append({"rig": "home.hero", "only": "legs", "at": [0, 0, 1, 1]})
        bad_sc["home"]["back"].append({"art": "hud.coin", "frame": "home.scene.gone", "at": [0, 0, 1, 1]})
        bad_sc["loading"]["cast"].append({"art": "hud.coin"})
        e = check_scenes(bad_sc, art, ui)
        ok(any("'nope'" in x for x in e) and any("legs" in x for x in e) and any("home.scene.gone" in x for x in e)
           and any("no at / frame" in x for x in e) and any("cast[1]" in x for x in e), f"check_scenes errors: {e}")
        gs = generate_scenes(sc)
        ok('Layer(kind: .art(.homeBackdrop), frameKey: "", rect: CGRect(x: 0, y: 0, width: 393, height: 852), fill: true, '
           'only: [], excluding: []),' in gs, "generate_scenes: fill layer")
        ok('Layer(kind: .rig(.homeHero), frameKey: "", rect: .zero, fill: false, only: [], excluding: ["armL"]),' in gs,
           "generate_scenes: rig part")
        ok('rect: CGRect(x: 1, y: 2, width: 3, height: 4.5)' in gs and ".centrepiece(.homeHero)" in gs, "generate_scenes: frame")
        ok('Placed(art: .hudCoin, rect: CGRect(x: -6, y: 434.5, width: 96, height: 76)),' in gs, "generate_scenes: cast")
        ok("static let loadingLogo: UIArt = .hudCoin" in gs, "generate_scenes: logo")
        # Swift source rules
        src = os.path.join(d, "App", "Shell")
        os.makedirs(src)
        good = ('enum UpAwayArt {\n    static let badge = "hud.coin"\n}\n'
                'let a = UIArt(rawValue: "home.backdrop")  // "coinA@3x.png" in a comment is fine\n'
                'let k = "outlined|\\(art.rawValue)"\n')
        badsrc = ('enum UpAwayArt {\n    static let badge = "coinA"\n}\nlet a = UIArt(rawValue: "gone.slot")\n'
                  'let p = "Art/" + name + "/rig.json"\nlet r = "hero_rig"\nlet f = PathImage(path: "UI/coinA@3x.png")\n'
                  'let x = "bgA"\n')
        with open(os.path.join(src, "Good.swift"), "w") as f:
            f.write(good)
        with open(os.path.join(src, "Bad.swift"), "w") as f:
            f.write(badsrc)
        files = swift_files(["App"], root=d)
        refs = check_slot_references(art, ui, files=files, root=d)
        ok(any("gone.slot" in x for x in refs) and any("'coinA'" in x for x in refs) and not any("Good.swift" in x for x in refs)
           and any("logo.part.<id>" in x and "logoB" in x for x in refs), f"check_slot_references: {refs}")
        ui["win"]["logo"]["layers"] = {}
        ok(not any("logo.part" in x for x in check_slot_references(art, ui, files=[], root=d)), "no logo ids, no logo errors")
        names = check_file_names(man, files=files, allow=[], root=d)
        bad_lines = sorted(int(x.split(":")[1]) for x in names if "Bad.swift" in x)
        ok(bad_lines == [2, 5, 6, 7, 8] and not any("Good.swift" in x for x in names), f"check_file_names: {names}")
        allow = [{"path": "App/Shell/Bad.swift", "reason": "t"}, {"path": "App/Gone/", "reason": "t"}]
        names = check_file_names(man, files=files, allow=allow, root=d)
        ok(len(names) == 1 and "stale" in names[0] and "App/Gone/" in names[0], f"check_file_names allow-list: {names}")
    for f in fails:
        print("SELFTEST FAIL:", f)
    print(f"selftest: {'OK' if not fails else f'{len(fails)} failures'}")
    return not fails


if __name__ == "__main__":
    main()
