#!/usr/bin/env python3
"""art/MANIFEST.json: the one list of every graphic the game needs (shared helpers for the art tools).

    python3 art/tools/manifest.py list [--family svg] [--status todo] [--owner pipeline]
    python3 art/tools/manifest.py show <id>
    python3 art/tools/manifest.py set <id> status=wip [owner=characters] [notes="..."]   # small edits, keeps order
    python3 art/tools/manifest.py idmap                  # regenerate art/ID-MAP.md from the manifest
    python3 art/tools/manifest.py add '<json object>'    # append one entry (validated like the checker's schema)
    python3 art/tools/manifest.py add-door W H [L c0 r0] # a door size for a level (copies doorW4H4's fields; gen_board makes it)
    python3 art/tools/manifest.py ref <id>               # save the entry's reference crop to build/ui-art/refcrops/<id>.png
    python3 art/tools/manifest.py merge art/lanes/<lane>.entries.json [--out copy.json | --apply] [--ids a b]
                                                         # a lane's scratch manifest -> field diffs vs MANIFEST.json
                                                         # (dry run); --out writes the merged manifest elsewhere (to
                                                         # check it), --apply writes MANIFEST.json (the art director only)

Schema (one entry per graphic):
    id          neutral lowerCamelCase, unique (never the brand: see BANNED)
    family      swiftui | svg | 3d | code
    route       STYLE.md route: A (board code), B1 (SwiftUI chrome), B2 (SVG icon), B3 (3D UI prop), C1 (3D scene /
                character), C2 (3D glossy arrows), C3 (board obstacle vector sprite)
    purpose     what it is;  screen: where it is seen
    size_pt     [w, h] frame in pt (whole numbers for rasters); size_px = size_pt x 3 (@3x)
    pitch_pt    board sprites only: the design pitch the frame is drawn at (the engine scales by pitch/pitch_pt)
    anchor_pt   optional: the registration point inside the frame (board sprites, puppet layers)
    source      the generator: "art/ui/src/gen_board.py:tapeV4" (svg), "art/ui/recipes/worker.py:workerHome" (3d),
                "art/ui/code/GlossyChrome.swift:HeartHUD" (swiftui), "App/...:<symbol>" or "engine" (code)
    file        the shipped raster (svg/3d): art/ui/out/<id>@3x.png (UI, board sprites) or art/out/<id>@3x.png (3D
                characters, scenes, glossy arrows, props); null for swiftui/code
    ref         the capture to LOOK at (never traced, never sampled into an asset), one of
                  {shot, box_pt [x0, y0, x1, y1], pitch_pt?, anchor_pt?, note?}   phone shots (393 pt wide) / store (440 pt)
                  {shot, box_px [x0, y0, x1, y1], px_per_pt, note?}                annotated web frames (research/web/yt_frames)
                  {video, t, box_pt, note?}   a frame of the owner's videos at t s (grabbed by art/tools/vgrab.swift;
                                              592 px = 393 pt assumed)
    status      todo | wip | done | graded
    owner       lane: pipeline | ui-art | characters | scene | engine | shell | fx | audio
    notes       free text (unconfirmed items say so)
Optional: variants (list of ids that share the generator), full_bleed (opaque backgrounds may touch the edge),
          text_live (the label is live EN/TR text drawn over it), confirmed (false = not yet seen in v552), rig (the file is a
          cut-out rig directory with rig.json, art/ui/tools/rig.py), exact_px [w, h] (a raster that is not @3x: the app icon),
          group (ID-MAP section), preview (a rendered PNG of a swiftui/code entry for the sheets).
          The win logo's parts (group logo; art/ui/tools/logo_parts.py writes them): render_scale (the file is size_pt x 3
          x render_scale px: size_pt is the SETTLED on-screen size and the file is bigger, the animation only scales it
          down; size_pt may be fractional), file_px [w, h] (the exact file size), anchor_pt (the frame's top-left in the
          settled logo), logo_rect [x, y, w, h] (the frame as fractions of the logoArrowOut canvas: the exact placement),
          z (paint order, 0 = bottom). Round 2 (LOGO-ART-2, build/logo/LOGO-SPEC.md §9): anchor_frac [x, y] (the animation
          anchor as a fraction of the frame = the layer's anchorPoint: a glyph's cream-face centroid, the sign's purple-face
          centroid), anchor_ref_pt [x, y] (that anchor at rest on the 393 x 852 reference canvas), variant_of / bend_deg /
          bend_measured_deg (logoSignPurple's bend variants); a sign lists its variants in `variants`. Round 3 (LOGO-ART-3,
          build/logo/art3/): every letter / glyph is a PAIR of layers <base>Ext + <base>Face -- pair_of (the letter / glyph),
          layer ("ext" | "face"), pair [ext id, face id] (the two share ONE transform: same frame, anchor and values),
          parent ("logoSignBlue" for ARROW's letters, "group" for OUT!); a composed round-1/2 letter / glyph lists its `pair`.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
APP = os.path.dirname(ART)
PATH = os.path.join(ART, "MANIFEST.json")
IDMAP = os.path.join(ART, "ID-MAP.md")

FAMILIES = ("swiftui", "svg", "3d", "code")
ROUTES = ("A", "B1", "B2", "B3", "C1", "C2", "C3")
STATUSES = ("todo", "wip", "done", "graded", "not-shipped")   # A4: not-shipped = retired, its file moved out (uiart_gen skips it)
BANNED = ("maze", "grand", "arrowjam", "arrow_jam")   # + the 'mo' prefix (checked as a word / camel prefix)
SHOT_W_PX, SHOT_W_PT = 1178, 393.0


def load(path=None):
    with open(path or PATH, encoding="utf-8") as f:
        return json.load(f)


def save(m, path=None):
    path = path or PATH
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(m, f, indent=1, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def entries(m=None):
    m = m or load()
    return m["entries"]


def by_id(m=None):
    return {e["id"]: e for e in entries(m)}


def app_path(rel):
    return rel if os.path.isabs(rel) else os.path.join(APP, rel)


def id_problems(i):
    p = []
    if not re.fullmatch(r"[a-z][A-Za-z0-9]*", i):
        p.append("not lowerCamelCase")
    low = i.lower()
    for b in BANNED:
        if b in low:
            p.append(f"brand word '{b}'")
    if re.match(r"mo[A-Z0-9]", i) or low == "mo":
        p.append("brand prefix 'mo'")
    return p


def shot_scale(shot_path):
    """px per pt of a reference image: phone shots are 1178 px for 393 pt; store shots are @3x (1320 px = 440 pt)."""
    from PIL import Image
    w = Image.open(shot_path).width
    if w in (1178, 1179):
        return w / SHOT_W_PT
    if w in (1242, 1284, 1290, 1320):   # store iPhone shots, @3x
        return 3.0
    return w / SHOT_W_PT


VIDEO_W_PX = 592     # the owner's recordings: 592 x 1280 for a 393 pt wide screen (assumed)


def video_frame(video, t):
    """PNG of the frame at t s of a video (cached in build/ui-art/refframes/), via art/tools/vgrab.swift."""
    import subprocess
    tool = os.path.join(APP, "build", "ui-art", "vgrab")
    src = os.path.join(HERE, "vgrab.swift")
    if not os.path.exists(tool) or os.path.getmtime(tool) < os.path.getmtime(src):
        os.makedirs(os.path.dirname(tool), exist_ok=True)
        subprocess.run(["xcrun", "swiftc", "-O", "-o", tool, src], check=True, capture_output=True)
    d = os.path.join(APP, "build", "ui-art", "refframes", re.sub(r"\W", "_", os.path.basename(video)))
    out = os.path.join(d, "t_%07.1f.jpg" % float(t))
    if not os.path.exists(out):
        subprocess.run([tool, app_path(video), d, str(float(t)), str(float(t)), "1", str(VIDEO_W_PX)], check=True,
                       capture_output=True, timeout=120)
    return out if os.path.exists(out) else None


def ref_image(r):
    """(path, px per pt) of a ref dict, or (None, None)."""
    if r.get("video"):
        p = video_frame(r["video"], r.get("t", 0))
        return (p, VIDEO_W_PX / SHOT_W_PT) if p else (None, None)
    if not r.get("shot"):
        return None, None
    p = app_path(r["shot"])
    if not os.path.exists(p):
        return None, None
    return p, (r["px_per_pt"] if r.get("px_per_pt") else shot_scale(p))


def ref_box_pt(r):
    """The ref box in the source's pt (box_pt as is; box_px / px_per_pt; else the whole image) or None."""
    p, k = ref_image(r)
    if not p:
        return None
    if r.get("box_px"):
        return [v / k for v in r["box_px"]]
    if r.get("box_pt"):
        return list(r["box_pt"])
    from PIL import Image
    w, h = Image.open(p).size
    return [0, 0, w / k, h / k]


def ref_label(r):
    if r.get("video"):
        return f"{os.path.basename(r['video'])} @ {r.get('t', 0)} s"
    return os.path.basename(r.get("shot", "?"))


def use_manifest(path):
    """Point every tool at another manifest (tests, scratch batches)."""
    global PATH
    PATH = os.path.abspath(path)


def ref_crop(e, pad_pt=0):
    """(PIL RGB crop of the reference resampled to 3 px per pt, px-per-pt of the source) or (None, None).
    box_pt is in the shot's pt; box_px (web frames) is in image px and is converted with px_per_pt."""
    from PIL import Image
    r = e.get("ref") or {}
    p, k = ref_image(r)
    if not p:
        return None, None
    im = Image.open(p).convert("RGB")
    if r.get("box_px"):
        x0, y0, x1, y1 = [v / k for v in r["box_px"]]
    elif r.get("box_pt"):
        x0, y0, x1, y1 = r["box_pt"]
    else:
        x0, y0, x1, y1 = 0, 0, im.width / k, im.height / k
    x0 -= pad_pt; y0 -= pad_pt; x1 += pad_pt; y1 += pad_pt
    box = [max(0, round(x0 * k)), max(0, round(y0 * k)), min(im.width, round(x1 * k)), min(im.height, round(y1 * k))]
    c = im.crop(box)
    if abs(k - 3) > 0.01:  # resample to exactly 3 px per pt
        c = c.resize((max(1, round(c.width * 3 / k)), max(1, round(c.height * 3 / k))), Image.LANCZOS)
    return c, k


def add_entry(m, e):
    ids = {x["id"] for x in m["entries"]}
    if e["id"] in ids:
        raise SystemExit(f"id {e['id']} exists")
    probs = id_problems(e["id"])
    for k in ("family", "route", "purpose", "screen", "status", "owner"):
        if not e.get(k):
            probs.append(f"missing {k}")
    if probs:
        raise SystemExit("; ".join(probs))
    if e.get("size_pt"):
        e["size_px"] = [round(v * 3) for v in e["size_pt"]]
    m["entries"].append(e)


def add_door(m, w, h, level=None, c0=None, r0=None):
    import copy
    base = by_id(m)["doorW4H4"]
    e = copy.deepcopy(base)
    e["id"] = f"doorW{w}H{h}"
    e["purpose"] = base["purpose"].replace("4 x 4", f"{w} x {h}")
    e["source"] = base["source"].rsplit(":", 1)[0] + ":" + e["id"]
    e["file"] = f"art/ui/out/{e['id']}@3x.png"
    e["status"] = "todo"
    e.pop("size_pt", None); e.pop("size_px", None); e.pop("anchor_pt", None)
    if level is not None:
        d = json.load(open(os.path.join(APP, "research", "levels", f"L{int(level):03d}.json")))
        p, (ox, oy) = d["pitch_pt"], d["origin_pt"]
        x0, y0 = ox + (c0 - 0.5) * p, oy + (r0 - 0.5) * p
        e["ref"] = {"shot": d["shot"], "box_pt": [round(x0 - 0.4 * p, 1), round(y0 - 0.4 * p, 1), round(x0 + (w + 0.4) * p, 1),
                                                   round(y0 + (h + 0.4) * p, 1)], "pitch_pt": p, "anchor_pt": [round(x0, 2), round(y0, 2)],
                    "level": int(level)}
    else:
        e["ref"] = None
    add_entry(m, e)
    return e


def merge_diff(m, lane, ids=None):
    """Compare a lane's scratch manifest (same schema, e.g. art/lanes/3d-events.entries.json -- lanes never edit
    MANIFEST.json while several run at once) with the manifest. -> [(id, "new" | "update", {field: (old, new)})];
    only fields the lane entry carries are compared (a lane file never deletes a field)."""
    have = by_id(m)
    out = []
    for e in lane["entries"]:
        if ids and e["id"] not in ids:
            continue
        cur = have.get(e["id"])
        if cur is None:
            out.append((e["id"], "new", {k: (None, v) for k, v in e.items()}))
            continue
        ch = {k: (cur.get(k), v) for k, v in e.items() if k != "id" and cur.get(k) != v}
        if ch:
            out.append((e["id"], "update", ch))
    return out


def merge_apply(m, diffs, validate=True):
    """validate=False: new entries are appended without the `add` schema check (manifest_check --lanes reports them)."""
    have = by_id(m)
    for i, kind, ch in diffs:
        if kind == "new":
            e = {k: v for k, (_, v) in ch.items()}
            if validate:
                add_entry(m, e)
            else:
                m["entries"].append(e)
            continue
        e = have[i]
        for k, (_, v) in ch.items():
            if k == "status" and v not in STATUSES:
                raise SystemExit(f"{i}: bad status {v}")
            e[k] = v
        if "size_pt" in ch and e.get("size_pt"):
            e["size_px"] = [round(v * 3) for v in e["size_pt"]]


def write_idmap(m=None):
    m = m or load()
    rows = ["# Art ID map (generated from art/MANIFEST.json by `python3 art/tools/manifest.py idmap`; do not edit by hand)",
            "",
            "id -> shipped file (or code symbol) -> where it is used. Status: todo / wip / done / graded. Board sprites are drawn",
            f"at the design pitch ({m.get('board_design_pitch_pt')} pt per cell) and scaled by the engine.",
            ""]
    groups = {}
    for e in m["entries"]:
        groups.setdefault(e.get("group", "other"), []).append(e)
    counts = {s: sum(1 for e in m["entries"] if e["status"] == s) for s in STATUSES}
    rows.append(f"Totals: {len(m['entries'])} entries; " + ", ".join(f"{s} {n}" for s, n in counts.items()) + ".")
    rows.append("")
    for gname in m.get("groups", list(groups)):
        es = groups.get(gname, [])
        if not es:
            continue
        rows.append(f"## {gname}")
        rows.append("")
        rows.append("| id | family / route | file or symbol | size pt | used where | status | owner |")
        rows.append("|---|---|---|---|---|---|---|")
        for e in es:
            f = e.get("file") or (e.get("source") or "")
            sz = "x".join(str(v) for v in e["size_pt"]) if e.get("size_pt") else "-"
            where = e.get("screen", "")
            rows.append(f"| `{e['id']}` | {e['family']} / {e['route']} | `{f}` | {sz} | {where} | {e['status']} | {e.get('owner', '')} |")
        rows.append("")
    with open(IDMAP, "w", encoding="utf-8") as fh:
        fh.write("\n".join(rows) + "\n")
    return IDMAP


def _cli():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return
    cmd = a[0]
    m = load()
    if cmd == "list":
        flt = {}
        i = 1
        while i < len(a):
            if a[i].startswith("--") and i + 1 < len(a):
                flt[a[i][2:]] = a[i + 1]; i += 2
            else:
                i += 1
        for e in m["entries"]:
            if all(str(e.get(k)) == v for k, v in flt.items()):
                sz = "x".join(str(v) for v in e["size_pt"]) if e.get("size_pt") else "-"
                print(f"{e['id']:28s} {e['family']:8s} {e['route']:3s} {sz:>10s}  {e['status']:6s} {e.get('owner', ''):11s} {e.get('screen', '')}")
    elif cmd == "show":
        print(json.dumps(by_id(m)[a[1]], indent=1, ensure_ascii=False))
    elif cmd == "set":
        e = by_id(m)[a[1]]
        for kv in a[2:]:
            k, v = kv.split("=", 1)
            if k == "status" and v not in STATUSES:
                raise SystemExit(f"bad status {v}")
            e[k] = v
        save(m)
        print("updated", a[1])
    elif cmd == "idmap":
        print("wrote", write_idmap(m))
    elif cmd == "add":
        add_entry(m, json.loads(a[1]))
        save(m)
        print("added", json.loads(a[1])["id"], "(run art/tools/manifest_check.py)")
    elif cmd == "add-door":
        w, h = int(a[1]), int(a[2])
        rest = [int(v) for v in a[3:6]] if len(a) >= 6 else [None, None, None]
        e = add_door(m, w, h, *rest)
        save(m)
        print("added", e["id"], "-> build: art/tools/art_batch.py --ids", e["id"], "--sync")
    elif cmd == "ref":
        c, k = ref_crop(by_id(m)[a[1]], pad_pt=6)
        if c is None:
            raise SystemExit("no reference crop")
        d = os.path.join(APP, "build", "ui-art", "refcrops")
        os.makedirs(d, exist_ok=True)
        c.save(os.path.join(d, a[1] + ".png"))
        print(os.path.join(d, a[1] + ".png"), c.size)
    elif cmd == "merge":
        lane_path = a[1]
        ids = None
        if "--ids" in a:
            ids = []
            for v in a[a.index("--ids") + 1:]:
                if v.startswith("--"):
                    break
                ids.append(v)
        lane = load(lane_path)
        diffs = merge_diff(m, lane, ids)
        short = lambda v: (json.dumps(v, ensure_ascii=False)[:90] + ("..." if len(json.dumps(v, ensure_ascii=False)) > 90 else ""))
        for i, kind, ch in diffs:
            print(f"{kind:6s} {i}")
            for k, (o, n) in ch.items():
                print(f"         {k}: {short(o)} -> {short(n)}")
        print(f"{len(diffs)} entries differ ({sum(1 for d in diffs if d[1] == 'new')} new)")
        out = a[a.index("--out") + 1] if "--out" in a else None
        if out and diffs:   # preview: the merged manifest in another file (manifest_check.py --manifest <out>)
            merge_apply(m, diffs)
            save(m, out)
            print(f"merged copy -> {out} (check it: manifest_check.py --manifest {out} --quiet)")
        elif "--apply" in a and diffs:
            merge_apply(m, diffs)
            save(m)
            print("applied -> art/MANIFEST.json (run manifest_check.py, then manifest.py idmap)")
    else:
        print(__doc__)


if __name__ == "__main__":
    _cli()
