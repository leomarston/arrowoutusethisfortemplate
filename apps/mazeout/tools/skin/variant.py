#!/usr/bin/env python3
"""tools/skin/variant.py — alternate colour skins, and the proof that a reskin is data only (docs/SKIN.md §5).

    python3 tools/skin/variant.py --check                  # (CI) every skin/variants/<name>/colors.json builds, and its
                                                           #      generated outputs differ from the active skin's ONLY in
                                                           #      colour values (same files, same lines, same names)
    python3 tools/skin/variant.py --write cobalt --map teal=#3A6FE0 --map pink=#7B3FE4 [--lightness shift] [--hue-spread F]
                                                           # (re)make a variant with tools/skin/recolor.py's rules
    python3 tools/skin/variant.py --refresh                # re-apply each variant's stored rules to today's skin/colors.json
    python3 tools/skin/variant.py --selftest

A variant file is an OVERLAY on the active skin (skin/colors.json), never a copy of it:
  {"about": …, "recolor": {"rules": [{select, to, from?, lightness?, hueSpread?, chroma?}, …]},
   "palette": {"<palette name>": "#RRGGBB", …},              the variant's palette (every entry of the skin it was made from)
   "tokens":  {"<token id>": "#RRGGBB", …}, "ui": {"<ui id>": "#RRGGBB[AA]", …}}   own-literal values it changes (optional)
so tokens the UI gains later (skin/colors.json grows with the code) follow the variant through their palette names, and a
palette entry added after the variant was made keeps the reference colour until `--refresh` (reported, not an error). A
name the active skin no longer has fails the check (the overlay is stale: `--refresh`).

The variants are NOT shipped: nothing reads skin/variants/ at build or run time. To TRY one in the app, copy the merged
result over skin/colors.json (`--apply NAME`, then tools/skin/build.py and build the app); to START a new game from one, the
game's skin/colors.json is the merged file (docs/SKIN.md §5).
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import skinlib as S          # noqa: E402
import build as B            # noqa: E402  (the generators: the same code path as the real build)
import recolor as R          # noqa: E402

VARIANTS = os.path.join(S.APP, "skin", "variants")
SECTIONS = ("palette", "tokens", "ui")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$")


def variant_files(root=VARIANTS):
    if not os.path.isdir(root):
        return []
    return [(n, os.path.join(root, n, "colors.json")) for n in sorted(os.listdir(root))
            if os.path.isfile(os.path.join(root, n, "colors.json"))]


def merge(active, overlay):
    """-> (merged doc, errors, palette names the overlay does not cover)."""
    doc, errs = copy.deepcopy(active), []
    for sec in SECTIONS:
        for k, v in (overlay.get(sec) or {}).items():
            if k not in active.get(sec, {}):
                errs.append(f"{sec} {k!r}: not in skin/colors.json any more (stale overlay: --refresh)")
            elif not isinstance(v, str) or not HEX.match(v):
                errs.append(f"{sec} {k!r}: {v!r} is not #RRGGBB[AA]")
            elif sec == "palette" and len(v) != 7:
                errs.append(f"palette {k!r}: a palette colour is #RRGGBB")
            else:
                doc[sec][k] = v.upper()
    uncovered = sorted(set(active["palette"]) - set((overlay.get("palette") or {})))
    return doc, errs, uncovered


def outputs(doc):
    """The colour-bearing generated files, exactly as tools/skin/build.py writes them (path -> text)."""
    return {S.GEN_SWIFT: B.generate(doc), S.GEN_TEST_SWIFT: B.generate_test_table(doc), S.UI_COLORS_GEN: B.generate_ui_colors(doc)}


COLOUR = re.compile(r"0x[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{8}\b|#[0-9A-Fa-f]{6}\b")


def colour_only_diff(a, b):
    """-> (same shape, number of colour values that differ): `a` and `b` must be equal once every colour literal (0xRRGGBB,
    #RRGGBB, #RRGGBBAA) is masked; then count the literals that differ."""
    ma, mb = COLOUR.sub("<c>", a), COLOUR.sub("<c>", b)
    if ma != mb:
        return False, 0
    ca, cb = COLOUR.findall(a), COLOUR.findall(b)
    return True, sum(1 for x, y in zip(ca, cb) if x.upper() != y.upper())


def check_variant(active, overlay, ui_text):
    """-> (errors, report lines)."""
    merged, errs, uncovered = merge(active, overlay)
    errs += ["colors.json + overlay: " + e for e in B.check_doc(merged)]
    errs += B.check_ui(merged, ui_text)
    if errs:
        return errs, []
    before, after = outputs(active), outputs(merged)
    report, total = [], 0
    for path in before:
        same, n = colour_only_diff(before[path], after[path])
        if not same:
            errs.append(f"{S.rel(path)}: the variant changes more than colour values (a name, a line, a file shape)")
        total += n
        report.append(f"{S.rel(path)}: {n} colour values differ")
    moved = sum(1 for k, v in (overlay.get("palette") or {}).items() if active["palette"].get(k, "").upper() != v.upper())
    if total == 0 or moved == 0:
        errs.append("the variant changes no colour: it proves nothing")
    # a real build from the variant: write the outputs where a game's build would, then read them back
    with tempfile.TemporaryDirectory() as d:
        for path, text in after.items():
            p = os.path.join(d, S.rel(path))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
        json.load(open(os.path.join(d, S.rel(S.UI_COLORS_GEN)), encoding="utf-8"))
    report.append(f"{moved} of {len(active['palette'])} palette colours moved"
                  + (f"; {len(uncovered)} palette entries newer than the variant keep the reference colour (e.g. {uncovered[0]}; "
                     "--refresh)" if uncovered else ""))
    return errs, report


def make_overlay(active, rules_json, about):
    """Apply recolor.py's rules to the active skin -> the overlay: the whole recoloured palette (so a palette entry the
    skin gains later is visible as not covered) and the own-literal token / ui values the rules move."""
    rules = [R.Rule(r["select"], r["to"], r.get("from"), r.get("lightness", "keep"), r.get("hueSpread", 1.0),
                    r.get("chroma", 1.0)) for r in rules_json]
    doc = copy.deepcopy(active)
    new_pal, changes = R.recolor_palette(doc, rules)
    lit = R.recolor_literals(doc, rules, {old: nh for _, old, nh, _, _ in changes})
    overlay = {"about": about, "recolor": {"rules": rules_json},
               "palette": dict(sorted(new_pal.items()))}
    for sec in ("tokens", "ui"):
        vals = {k: new for s, k, _, new in lit if s == sec}
        if vals:
            overlay[sec] = dict(sorted(vals.items()))
    return overlay


def rules_from_args(a):
    out = []
    for m in a.map or []:
        if "=" not in m:
            raise SystemExit(f"--map {m!r}: expected SELECT=TO or SELECT=FROM>TO")
        sel, rhs = m.split("=", 1)
        frm, to = rhs.split(">", 1) if ">" in rhs else (None, rhs)
        r = {"select": sel.strip(), "to": to.strip()}
        if frm:
            r["from"] = frm.strip()
        if a.lightness != "keep":
            r["lightness"] = a.lightness
        if a.hue_spread != 1.0:
            r["hueSpread"] = a.hue_spread
        out.append(r)
    return out


ABOUT = ("A colour variant of the skin (tools/skin/variant.py; docs/SKIN.md §5): an OVERLAY on skin/colors.json made by "
         "recolor.py's rules below, never shipped. CI builds the generated colour files from it and proves they differ "
         "from the active skin's only in colour values. Regenerate: python3 tools/skin/variant.py --refresh.")


def save(path, overlay):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(overlay, indent=1, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--write", metavar="NAME")
    ap.add_argument("--map", action="append", metavar="SELECT=[FROM>]TO")
    ap.add_argument("--lightness", default="keep", choices=["keep", "shift"])
    ap.add_argument("--hue-spread", type=float, default=1.0)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--apply", metavar="NAME", help="write the merged variant over skin/colors.json (to try it; git restores)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    active = S.load_colors()
    if a.write:
        rules = rules_from_args(a)
        if not rules:
            ap.error("--write needs --map rules")
        path = os.path.join(VARIANTS, a.write, "colors.json")
        save(path, make_overlay(active, rules, ABOUT))
        print(f"wrote {S.rel(path)}")
    if a.refresh:
        for name, path in variant_files():
            old = json.load(open(path, encoding="utf-8"))
            save(path, make_overlay(active, old["recolor"]["rules"], old.get("about", ABOUT)))
            print(f"refreshed {S.rel(path)}")
    if a.apply:
        path = os.path.join(VARIANTS, a.apply, "colors.json")
        merged, errs, _ = merge(active, json.load(open(path, encoding="utf-8")))
        if errs:
            raise SystemExit("\n".join(errs))
        S.save_colors(merged)
        print(f"skin/colors.json = {a.apply} (run tools/skin/build.py; `git checkout skin/colors.json` goes back)")
        return
    if a.check or not (a.write or a.refresh):
        files = variant_files()
        if not files:
            raise SystemExit("no skin/variants/<name>/colors.json: nothing proves a reskin is data only")
        ui_text = B.read(S.UI_JSON)
        bad = False
        for name, path in files:
            errs, report = check_variant(active, json.load(open(path, encoding="utf-8")), ui_text)
            for e in errs:
                print(f"{S.rel(path)}: {e}")
            bad = bad or bool(errs)
            if not errs:
                print(f"variant {name}: builds; only colour values change — " + "; ".join(report))
        sys.exit(1 if bad else 0)


def selftest():
    fails = []

    def ok(cond, what):
        if not cond:
            fails.append(what)

    active = {"palette": {"teal.42": "#00706B", "teal.60": "#00A293", "red.50": "#E02020"},
              "tokens": {"a.fill": "teal.42", "a.rim": "teal.60", "b.x": "red.50", "c.hex": "teal.42", "d.own": "#00706B"},
              "ui": {"colors.p": "teal.60", "colors.q": "#00A293CC"}}
    ok(S.validate(active) == [], f"fixture valid: {S.validate(active)}")
    ov = make_overlay(active, [{"select": "teal", "to": "#3A6FE0"}], "t")
    ok(set(ov["palette"]) == {"teal.42", "teal.60", "red.50"} and ov["palette"]["red.50"] == "#E02020"
       and ov["palette"]["teal.42"] != "#00706B", f"overlay palette {ov['palette']}")
    ok(ov.get("tokens", {}).get("d.own", "").startswith("#") and ov.get("ui", {}).get("colors.q", "").endswith("CC"),
       f"overlay own literals {ov.get('tokens')} {ov.get('ui')}")
    merged, errs, unc = merge(active, ov)
    ok(errs == [] and unc == [] and merged["palette"]["red.50"] == "#E02020"
       and merged["palette"]["teal.42"] != "#00706B", f"merge {errs} {unc}")
    grown = copy.deepcopy(active)
    grown["palette"]["red.60"] = "#FF4040"
    ok(merge(grown, ov)[2] == ["red.60"], "merge: a palette entry newer than the variant is reported")
    _, errs, _ = merge(active, {"palette": {"gone.10": "#000000", "teal.42": "nope"}})
    ok(len(errs) == 2, f"merge errors {errs}")
    same, n = colour_only_diff("let a = 0x00706B // x\n\"#00A293CC\"", "let a = 0x3A6FE0 // x\n\"#00A293CC\"")
    ok(same and n == 1, "colour_only_diff: one colour")
    ok(not colour_only_diff("static let a = 0x00706B", "static let b = 0x00706B")[0], "colour_only_diff: a renamed constant")
    ok(not colour_only_diff("a\n", "a\nb\n")[0], "colour_only_diff: an extra line")
    # generated outputs through build.py's own generators
    o1, o2 = outputs(active), outputs(merged)
    ok(all(colour_only_diff(o1[p], o2[p])[0] for p in o1) and sum(colour_only_diff(o1[p], o2[p])[1] for p in o1) > 0,
       "outputs differ only in colours")
    ui_text = json.dumps({"colors": {"p": "@colors.p", "q": "@colors.q"}})
    errs, rep = check_variant(active, ov, ui_text)
    ok(errs == [] and any("palette colours moved" in r for r in rep), f"check_variant clean: {errs} {rep}")
    errs, _ = check_variant(active, {"palette": {}}, ui_text)
    ok(any("proves nothing" in e for e in errs), f"check_variant: an empty overlay {errs}")
    class A:
        map, lightness, hue_spread = ["teal=a>#3A6FE0", "pink=#7B3FE4"], "shift", 0.5
    ok(rules_from_args(A) == [{"select": "teal", "to": "#3A6FE0", "from": "a", "lightness": "shift", "hueSpread": 0.5},
                              {"select": "pink", "to": "#7B3FE4", "lightness": "shift", "hueSpread": 0.5}], "rules_from_args")
    for f in fails:
        print("SELFTEST FAIL:", f)
    print(f"selftest: {'OK' if not fails else f'{len(fails)} failures'}")
    return not fails


if __name__ == "__main__":
    main()
