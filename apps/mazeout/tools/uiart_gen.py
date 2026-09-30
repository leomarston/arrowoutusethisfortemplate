#!/usr/bin/env python3
"""SHELL S1 (SPEC-architecture §6.11 "UIArt"): skin/art.json + art/MANIFEST.json -> App/Shell/Components/UIArt.swift.

Skin phase 3 (docs/SKIN.md §4): one `UIArt` case per art SLOT of skin/art.json (what the raster is for: `home.backdrop`,
`currency.coin.icon` …), mapped to a shipped RASTER id of the manifest (families svg / 3d with a .png file; code / swiftui
entries are drawn in code, the app icon lives in Assets.xcassets), plus `enum ArtRig` for the puppet rig slots. Each case knows
its bundle path (tools/sync_art.sh copies art/ui/out -> UI/ and art/out -> Art/), its size in pt and its manifest group. The
generator is tools/skin/art.py (this script delegates to it; its --check also covers skin/scenes.json and the Swift sources).
The loader and the placeholder live in App/Shell/Components/ArtStore.swift (hand-written); this file is data only.

    python3 tools/uiart_gen.py            # write App/Shell/Components/UIArt.swift
    python3 tools/uiart_gen.py --check    # exit 1 if the file on disk is stale
    python3 tools/uiart_gen.py --exclude-list ui|art   # rsync exclude patterns for tools/sync_art.sh (below)

FIX-2 lane B (A4-r2 / A4-r6): ONE rule decides what never ships, used by the case list AND by tools/sync_art.sh's copy:
  - every manifest entry with status 'not-shipped' or whose notes START with 'NOT SHIPPED' (retired or provenance-only
    art; its file may still sit in art/ui/out or art/out), whether or not its file exists;
  - every id listed in tools/art_build_only.txt (art the pipeline needs — composite inputs, the 1024 icon renders — that
    no code draws).
Such an entry gets no UIArt case, and `--exclude-list` prints its file (+ an art/out sidecar `<stem>.json`, + a rig folder)
as rsync patterns anchored at the synced folder, so the bundle's UI/ and Art/ hold only what the code can draw.
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MANIFEST = os.path.join(ROOT, "art", "MANIFEST.json")
OUT = os.path.join(ROOT, "App", "Shell", "Components", "UIArt.swift")
SWIFT_KEYWORDS = {"default", "case", "class", "struct", "enum", "func", "var", "let", "in", "is", "as", "self", "Type",
                  "protocol", "extension", "import", "return", "switch", "where", "while", "for", "if", "else", "do", "try"}


BUILD_ONLY = os.path.join(ROOT, "tools", "art_build_only.txt")


def build_only():
    """tools/art_build_only.txt: one manifest id per line ('#' comments, blank lines ignored)."""
    if not os.path.exists(BUILD_ONLY):
        return set()
    ids = set()
    for line in open(BUILD_ONLY, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if line:
            ids.add(line)
    return ids


def never_ships(entry, extra=None):
    """The one rule (docstring above): retired / provenance-only / build-only art never ships."""
    if entry.get("status") == "not-shipped" or (entry.get("notes") or "").startswith("NOT SHIPPED"):
        return True
    return entry.get("id") in (build_only() if extra is None else extra)


def shipped(entry, extra=None):
    f = entry.get("file") or ""
    if entry.get("family") not in ("svg", "3d"):
        return None
    if never_ships(entry, extra):
        return None                                   # FIX-2 B: retired / provenance-only / build-only (see the docstring)
    if not f.endswith("@3x.png"):
        return None                                   # rigs (folders) and the 1024 icon
    if f.startswith("art/ui/out/"):
        return "UI/" + f[len("art/ui/out/"):]
    if f.startswith("art/out/"):
        return "Art/" + f[len("art/out/"):]
    return None


def exclude_patterns(folder):
    """rsync exclude patterns (anchored at the synced folder) for every entry that never ships: folder 'ui' = art/ui/out,
    'art' = art/out. A file's art/out sidecar (<stem>.json, which sync_art.sh ships for char_*) and a rig folder go too."""
    prefix = {"ui": "art/ui/out/", "art": "art/out/"}[folder]
    m = json.load(open(MANIFEST))
    extra = build_only()
    known = {e["id"] for e in m["entries"]}
    unknown = sorted(extra - known)
    if unknown:
        raise SystemExit(f"uiart_gen: tools/art_build_only.txt names ids the manifest does not have: {unknown}")
    out = set()
    for e in m["entries"]:
        f = e.get("file") or ""
        if not f.startswith(prefix) or not never_ships(e, extra):
            continue
        rel = f[len(prefix):].rstrip("/")
        if os.path.isdir(os.path.join(ROOT, f)) or not os.path.splitext(rel)[1]:
            out.add(f"/{rel}/")                       # a rig folder
            continue
        out.add(f"/{rel}")
        stem = rel[:-len("@3x.png")] if rel.endswith("@3x.png") else os.path.splitext(rel)[0]
        if folder == "art":
            out.add(f"/{stem}.json")                  # its placement sidecar (only char_*.json are copied at all)
    # never exclude what a SHIPPED entry needs (two entries naming one file, a shared sidecar or rig folder)
    keep = set()
    for e in m["entries"]:
        f = e.get("file") or ""
        if not f.startswith(prefix) or never_ships(e, extra):
            continue
        rel = f[len(prefix):].rstrip("/")
        stem = rel[:-len("@3x.png")] if rel.endswith("@3x.png") else os.path.splitext(rel)[0]
        keep.update({f"/{rel}", f"/{rel}/", f"/{stem}.json"})
    clash = sorted(out & keep)
    if clash:
        raise SystemExit(f"uiart_gen: a shipped entry needs these excluded paths: {clash}")
    return sorted(out)


def generate():
    """UIArt.swift = the skin's art SLOTS (skin/art.json) resolved through the manifest: tools/skin/art.py writes it (and
    checks that every shipped raster of this manifest has a slot, so the case list still covers the whole shipped set)."""
    sys.path.insert(0, os.path.join(ROOT, "tools", "skin"))
    import art as skin_art
    errs = skin_art.check_art(skin_art.load_json(skin_art.ART_JSON), skin_art.load_manifest(), check_files=False)
    if errs:
        raise SystemExit("uiart_gen: skin/art.json:\n" + "\n".join(errs))
    return skin_art.targets()[0][1]


def main():
    if "--exclude-list" in sys.argv:
        folder = sys.argv[sys.argv.index("--exclude-list") + 1]
        print("\n".join(exclude_patterns(folder)))
        return
    text = generate()
    if "--check" in sys.argv:
        cur = open(OUT).read() if os.path.exists(OUT) else ""
        if cur != text:
            print("uiart_gen: App/Shell/Components/UIArt.swift is stale; run python3 tools/uiart_gen.py", file=sys.stderr)
            sys.exit(1)
        print("uiart_gen: up to date")
        return
    with open(OUT, "w") as f:
        f.write(text)
    print(f"uiart_gen: wrote {os.path.relpath(OUT, ROOT)} ({text.count(chr(10) + '    case ')} cases)")


if __name__ == "__main__":
    main()
