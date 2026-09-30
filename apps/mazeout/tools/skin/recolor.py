#!/usr/bin/env python3
"""tools/skin/recolor.py — move whole colour families of the skin to new base colours (docs/SKIN.md).

    python3 tools/skin/recolor.py --map teal=#3A6FE0 --map pink=#8E44AD --preview /tmp/recolor.html --dry-run
    python3 tools/skin/recolor.py --map teal=#3A6FE0                    # rewrite skin/colors.json
    python3 tools/skin/recolor.py --config my_skin_recolor.json          # the same rules from a file
    python3 tools/skin/recolor.py --list-families                        # what each family holds today
    python3 tools/skin/recolor.py --selftest

Then run `python3 tools/skin/build.py` (and build the app). Nothing here edits Swift.

Rules (applied to the ORIGINAL colours; the first rule that selects a colour wins):
  SELECT=TO            SELECT is a family (teal, pink, brown … see --list-families), `hue:A-B` (OKLCh hue window in
                       degrees, wraps past 360, optional `:minChroma` e.g. hue:160-212:0.03) or `name:teal.42,teal.44`
                       (explicit palette entries); TO is the new base colour '#RRGGBB'.
  SELECT=FROM>TO       FROM names the source colour that becomes TO (default: the selection's most chromatic colour).
  --config FILE        {"rules": [{"select": "teal", "to": "#3A6FE0", "from": "#00A293", "lightness": "keep",
                                   "hueSpread": 1.0, "chroma": 1.0}, …]}

How one colour moves (CIELAB LCh, the D1 reskin's approach: tools/palette_map.py, art/ui/src/d1_skin.py):
  L*   lightness "keep" (default): the colour's own L*, so every ramp (face -> rim -> outline, gradient stops, light
       edges) keeps its exact lightness structure; "shift": L* + (L*(TO) - L*(FROM)), the ramp moves as a whole
  C*   the colour's chroma x C*(TO) / C*(FROM) (x `chroma`), so the family's relative saturation is kept
  h    h(TO) + hueSpread x (h - h(FROM)): the family's hue spread is kept (hueSpread 1) or compressed (< 1)
  then the chroma is reduced (L* and h kept) until the colour is inside sRGB.
Palette NAMES stay (they name Arrow Out's family: "teal.42" after a blue recolour is the blue that replaced it).

What moves: the palette (so every token and every ui.json colour naming a palette entry follows), and the few token / ui
values that are their own "#RRGGBB[AA]" literal (an equal palette colour's new value, else the first rule selecting it;
an alpha suffix is kept). ui.json itself holds no colour (its slots are "@<ui id>" references into colors.json `ui`), so
nothing else needs rewriting: run build.py and the app picks the new colours up.
--preview FILE writes a self-contained HTML swatch sheet (before -> after per family, with usage counts).
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skinlib as S  # noqa: E402


class Rule:
    def __init__(self, select, to, frm=None, lightness="keep", hue_spread=1.0, chroma=1.0):
        self.select, self.to, self.frm = select, S.norm_hex(to), (S.norm_hex(frm) if frm else None)
        self.lightness, self.hue_spread, self.chroma = lightness, float(hue_spread), float(chroma)
        if lightness not in ("keep", "shift"):
            raise SystemExit(f"rule {select}: lightness must be keep or shift")
        self.kind, self.arg = self._parse(select)

    @staticmethod
    def _parse(sel):
        if sel.startswith("hue:"):
            parts = sel[4:].split(":")
            a, b = (float(x) for x in parts[0].split("-"))
            minc = float(parts[1]) if len(parts) > 1 else 0.025
            return "hue", (a, b, minc)
        if sel.startswith("name:"):
            return "name", set(x.strip() for x in sel[5:].split(",") if x.strip())
        if sel not in S.FAMILIES:
            raise SystemExit(f"unknown family {sel!r}; families: {', '.join(S.FAMILIES)}")
        return "family", sel

    def selects(self, hx, name=None):
        if self.kind == "family":
            return (S.family_of_name(name) if name else S.family(hx)) == self.arg
        if self.kind == "name":
            return name in self.arg
        a, b, minc = self.arg
        L, C, h = S.oklch(hx)
        if C < minc:
            return False
        if a <= b:
            return a <= h < b
        return h >= a or h < b                           # wraps past 360

    def bind(self, members):
        """Fix FROM: given, or the selection's most chromatic colour (CIELAB C*)."""
        if not self.frm:
            if not members:
                self.frm = self.to
            else:
                self.frm = max(members, key=lambda h: (S.lch(h)[1], h))
        self.L0, self.C0, self.h0 = S.lch(self.frm)
        self.L1, self.C1, self.h1 = S.lch(self.to)
        return self

    def apply(self, hx):
        L, C, h = S.lch(hx)
        ratio = (self.C1 / self.C0) if self.C0 > 1e-6 else 0.0
        C2 = C * ratio * self.chroma
        dh = S.hue_diff(self.h0, h)
        h2 = (self.h1 + self.hue_spread * dh) % 360
        L2 = L if self.lightness == "keep" else L + (self.L1 - self.L0)
        if hx == self.frm and self.lightness == "shift":
            return self.to, False
        return S.lch_hex(L2, C2, h2)


def load_rules(args):
    rules = []
    if args.config:
        with open(args.config, encoding="utf-8") as f:
            for r in json.load(f)["rules"]:
                rules.append(Rule(r["select"], r["to"], r.get("from"), r.get("lightness", args.lightness),
                                  r.get("hueSpread", args.hue_spread), r.get("chroma", 1.0)))
    for m in args.map or []:
        if "=" not in m:
            raise SystemExit(f"--map {m!r}: expected SELECT=TO or SELECT=FROM>TO")
        sel, rhs = m.split("=", 1)
        frm, to = rhs.split(">", 1) if ">" in rhs else (None, rhs)
        rules.append(Rule(sel.strip(), to.strip(), frm.strip() if frm else None, args.lightness, args.hue_spread))
    return rules


def recolor_palette(doc, rules):
    """-> (new palette, changes [(name, old, new, rule select, clipped)])."""
    pal = doc["palette"]
    owner = {}
    for name, hx in pal.items():
        for r in rules:
            if r.selects(hx, name):
                owner[name] = r
                break
    for r in rules:
        r.bind([pal[n] for n, rr in owner.items() if rr is r])
    new, changes = dict(pal), []
    for name, r in owner.items():
        nh, clipped = r.apply(pal[name])
        new[name] = nh
        changes.append((name, pal[name], nh, r.select, clipped))
    return new, sorted(changes)


def recolor_literals(doc, rules, palette_map):
    """Token and ui values written as their own "#RRGGBB[AA]" (not a palette name): a value equal to a recoloured palette
    colour takes exactly that colour's new value; other values go through the first rule selecting them. Alpha kept.
    -> [(section, id, old, new)] (the doc is changed in place)."""
    changes = []
    for sec in ("tokens", "ui"):
        for k, v in sorted(doc.get(sec, {}).items()):
            if not v.startswith("#"):
                continue
            hx, alpha = v[:7], v[7:]
            nh = palette_map.get(hx)
            if nh is None:
                for r in rules:
                    if r.selects(hx):
                        nh = r.apply(hx)[0]
                        break
            if nh is None or nh == hx:
                continue
            doc[sec][k] = nh + alpha
            changes.append((sec, k, v, nh + alpha))
    return changes


def usage(doc):
    """palette name -> how many tokens and ui.json colours use it."""
    n = {}
    for v in list(doc["tokens"].values()) + list(doc.get("ui", {}).values()):
        if not v.startswith("#"):
            n[v] = n.get(v, 0) + 1
    return n


def preview_html(doc, new_pal, changes, rules, path):
    use = usage(doc)
    by_rule = {}
    for name, old, nh, sel, clipped in changes:
        by_rule.setdefault(sel, []).append((name, old, nh, clipped))
    esc = html.escape

    def sw(c, big=False):
        return f'<span class="sw{" big" if big else ""}" style="background:{c}" title="{c}"></span>'
    parts = []
    for r in rules:
        rows = sorted(by_rule.get(r.select, []), key=lambda x: (S.lch(x[1])[0], x[0]))
        head = (f'<h2>{esc(r.select)} <small>{len(rows)} colours · from {sw(r.frm)} {r.frm} → {sw(r.to)} {r.to} · '
                f'lightness {r.lightness}, hue spread {r.hue_spread:g}</small></h2>')
        strip_old = "".join(sw(o) for _, o, _, _ in rows)
        strip_new = "".join(sw(n) for _, _, n, _ in rows)
        cells = "".join(
            f'<div class="c">{sw(o, True)}{sw(n, True)}<div class="t">{esc(name)}<br>{o} → {n}'
            f'{" <b>clipped</b>" if cl else ""}<br>{use.get(name, 0)} uses</div></div>'
            for name, o, n, cl in rows)
        parts.append(f'<section>{head}<div class="strip">{strip_old}</div><div class="strip">{strip_new}</div>'
                     f'<div class="grid">{cells}</div></section>')
    untouched = sorted(set(doc["palette"]) - {c[0] for c in changes})
    parts.append(f'<section><h2>unchanged <small>{len(untouched)} colours</small></h2><div class="strip">'
                 + "".join(sw(doc["palette"][n]) for n in sorted(untouched, key=lambda n: (S.family_of_name(n),
                                                                                          S.lch(doc["palette"][n])[0])))
                 + "</div></section>")
    page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Skin recolour preview</title><style>
:root{{--bg:#f6f6f4;--fg:#1d1d1b;--mut:#6b6b66}}
@media (prefers-color-scheme:dark){{:root{{--bg:#1b1b1a;--fg:#ecece8;--mut:#a3a39c}}}}
body{{background:var(--bg);color:var(--fg);font:14px/1.4 -apple-system,system-ui,sans-serif;margin:0;padding:16px}}
h1{{font-size:20px}} h2{{font-size:16px;margin:24px 0 8px}} small{{color:var(--mut);font-weight:400}}
.sw{{display:inline-block;width:14px;height:28px;vertical-align:middle}} .sw.big{{width:40px;height:40px;border-radius:6px 0 0 6px}}
.sw.big+.sw.big{{border-radius:0 6px 6px 0}} .strip{{display:flex;flex-wrap:wrap;margin:2px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px;margin-top:8px}}
.c{{display:flex;gap:0;align-items:center}} .t{{font-size:11px;color:var(--mut);margin-left:8px}}
</style></head><body><h1>Skin recolour preview</h1>
<p>Each section: the family's colours sorted by lightness, before (top strip) and after (bottom strip), then every
colour with its palette name and how many tokens use it. Written by tools/skin/recolor.py.</p>
{''.join(parts)}</body></html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)


def list_families(doc):
    use = usage(doc)
    fams = {}
    for n, h in doc["palette"].items():
        fams.setdefault(S.family_of_name(n), []).append((n, h))
    for fam in S.FAMILIES:
        items = fams.get(fam, [])
        if not items:
            continue
        top = max(items, key=lambda x: S.lch(x[1])[1])
        uses = sum(use.get(n, 0) for n, _ in items)
        print(f"{fam:8s} {len(items):4d} colours {uses:5d} uses  most chromatic {top[1]} ({top[0]})  "
              f"{S.FAMILY_DOC.get(fam, '')}")


def selftest():
    fails = []
    doc = S.load_colors()
    # identity: TO == FROM with keep -> every colour unchanged (L*, C*, h round trip)
    for fam in ("teal", "pink", "brown"):
        r = Rule(fam, "#000000")
        members = [h for n, h in doc["palette"].items() if S.family_of_name(n) == fam]
        r.bind(members)
        r.to = r.frm
        r.bind(members)
        bad = [h for h in members if r.apply(h)[0] != h]
        if bad:
            fails.append(f"identity {fam}: {bad[:3]}")
    # keep: L* is preserved within 0.6 (8-bit rounding), the anchor goes to TO's hue/chroma
    r = Rule("teal", "#3A6FE0")
    members = [h for n, h in doc["palette"].items() if S.family_of_name(n) == "teal"]
    r.bind(members)
    for h in members:
        nh, clipped = r.apply(h)
        if abs(S.lch(nh)[0] - S.lch(h)[0]) > 0.6:
            fails.append(f"keep L*: {h} -> {nh}")
            break
    L0 = sorted(members, key=lambda h: S.lch(h)[0])
    L1 = [S.lch(r.apply(h)[0])[0] for h in L0]
    if any(b < a - 0.6 for a, b in zip(L1, L1[1:])):
        fails.append("keep: lightness order changed")
    # shift: the anchor lands exactly on TO
    r2 = Rule("teal", "#3A6FE0", lightness="shift").bind(members)
    if r2.apply(r2.frm)[0] != "#3A6FE0":
        fails.append("shift: anchor does not land on TO")
    # ui colours: a palette name follows the palette; own literals follow an equal palette colour exactly (alpha kept),
    # else the rule; untouched families stay
    tiny = {"palette": {"teal.60": "#00A293", "neutral.100": "#FFFFFF"},
            "tokens": {"a.b": "teal.60", "a.c": "#00A293"},
            "ui": {"colors.x": "teal.60", "colors.y": "#00A293CC", "colors.z": "#FFFFFF", "colors.w": "#10B0A0"}}
    rt = Rule("teal", "#3A6FE0")
    new_pal, ch = recolor_palette(tiny, [rt])
    pal_map = {old: nh for _, old, nh, _, _ in ch}
    lit = recolor_literals(tiny, [rt], pal_map)
    tiny["palette"] = new_pal
    nt = new_pal["teal.60"]
    if (S.resolve_ui(tiny, "colors.x") != nt or tiny["ui"]["colors.y"] != nt + "CC" or tiny["tokens"]["a.c"] != nt
            or tiny["ui"]["colors.z"] != "#FFFFFF" or tiny["ui"]["colors.w"] == "#10B0A0" or len(lit) != 3):
        fails.append(f"ui/literal recolour: {tiny} {lit}")
    # hue windows wrap
    if not Rule("hue:350-10", "#FF0000").selects("#FF0080") or Rule("hue:350-10", "#FF0000").selects("#00FF00"):
        fails.append("hue window wrap")
    for f in fails:
        print("SELFTEST FAIL:", f)
    print(f"recolor selftest: {'OK' if not fails else f'{len(fails)} failures'}")
    return not fails


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--map", action="append", metavar="SELECT=[FROM>]TO")
    ap.add_argument("--config")
    ap.add_argument("--lightness", default="keep", choices=["keep", "shift"])
    ap.add_argument("--hue-spread", type=float, default=1.0)
    ap.add_argument("--colors", default=S.COLORS_JSON, help="the colors.json to read (default skin/colors.json)")
    ap.add_argument("--out", help="write here instead of --colors")
    ap.add_argument("--preview", metavar="FILE.html")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--list-families", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest() else 1)
    doc = S.load_colors(a.colors)
    if a.list_families:
        list_families(doc)
        return
    rules = load_rules(a)
    if not rules:
        ap.error("no rules: give --map or --config (see --help)")
    new_pal, changes = recolor_palette(doc, rules)
    moved = [c for c in changes if c[1] != c[2]]
    clipped = sum(1 for c in changes if c[4])
    for r in rules:
        n = sum(1 for c in changes if c[3] == r.select)
        print(f"{r.select}: {n} palette colours, from {r.frm} -> {r.to} (lightness {r.lightness})")
    print(f"recolour: {len(moved)} of {len(doc['palette'])} palette colours change, {clipped} chroma-clipped to sRGB")
    if a.preview:
        preview_html(doc, new_pal, changes, rules, a.preview)
        print(f"preview: {a.preview}")
    pal_map = {old: nh for _, old, nh, _, _ in changes}
    lit = recolor_literals(doc, rules, pal_map)
    moved_names = {c[0] for c in moved}
    n_ui = sum(1 for v in doc.get("ui", {}).values() if v in moved_names)
    print(f"ui.json colours following the palette: {n_ui}; own-literal token/ui values changing: {len(lit)}")
    if a.dry_run:
        print("dry run: nothing written")
        return
    doc["palette"] = new_pal
    errs = S.validate(doc)
    if errs:
        raise SystemExit("\n".join(errs))
    S.save_colors(doc, a.out or a.colors)
    print(f"wrote {S.rel(a.out or a.colors)}")
    print("next: python3 tools/skin/build.py, then build the app")


if __name__ == "__main__":
    main()
