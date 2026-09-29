#!/usr/bin/env python3
"""tools/palette_map.py — R9 PALETTE-MAP (PLAN-P §4.2; art-direction.md §7.3; ruling 38 "D1's UI palette").

Scans every colour literal the app's look is built from, classifies each one into a colour FAMILY (by an explicit token
table, the literal's context and LCh windows), and maps every mapped family onto the D1 "Burrow Works" ladder while KEEPING
each colour's L* and its chroma RELATIVE to the family's anchors (art-direction.md §7.3 step 3), so gradients, rims and light
edges keep the structure that made the chrome read premium. It never edits the app: A5 CODEMOD applies the map.

    PY=~/.venvs/mf3d/bin/python
    nice -n 10 $PY tools/palette_map.py build      # scan + classify + map -> design/publish/palette/{palette_map.csv,
                                                   #   palette_map.json, swatches.png, summary.json}; exit 1 if anything
                                                   #   is unclassified
    nice -n 10 $PY tools/palette_map.py check      # re-scan, assert 0 unclassified + the invariants (selftest included)
    nice -n 10 $PY tools/palette_map.py selftest   # the mapping maths on synthetic cases + mutation checks
    nice -n 10 $PY tools/palette_map.py preview    # pixel preview of the map on our own captures + copygate numbers
                                                   #   (build/p/R9/preview/; a faithful preview, NOT an asset)
    nice -n 10 $PY tools/palette_map.py apply --to DIR   # writes MAPPED COPIES of the scanned files under DIR (never the
                                                   #   source tree); A5's dry run. Re-scanning DIR finds 0 old-family colours.

What is scanned (the "literals"):
  swift     App/**/*.swift + art/ui/code/*.swift (compiled into the app, project.yml): 0xRRGGBB tokens, "#RRGGBB[AA]"
            strings, `red: 0xRR / 255` channel triples and decimal (UI)Color(red:green:blue:) literals, chromatic system
            colours (Color.yellow …). Comments are lexed out (documentation only; counted in the summary).
  json      App/Resources/Tuning/*.json "#RRGGBB[AA]" values (ui.json, board.json) with their JSON path as context.
  colorset  App/Resources/Assets.xcassets/*.colorset (the launch background).
  svg       the SVG generators' colour constants (art/ui/src/gen_*.py, art/ui/src/svg/gen_*.py, art/ui/src/characters/*.py)
            with the manifest ids whose rasters bake them (via each generator's CASES + an AST call graph).
  pathcore  Packages/PathCore/Sources/**/*.swift colour strings (board feedback curves).
Not scanned (other packages own them): 3-D recipes (art/ui/recipes, art/pipeline: R2-R8 re-render), the generated
art/ui/src/*.svg (outputs of the generators above), level JSON (no colours).

Every literal ends in exactly one family. A family is either MAPPED (onto a D1 ladder) or EXCLUDED with a written reason
(generic genre colour, board mechanics kept by ruling, owned by another package that REDESIGNS that art, non-colour hex).
`build` fails while any literal is unclassified.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import math
import os
import re
import sys
import tokenize

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
OUT_DIR = os.path.join(ROOT, "design", "publish", "palette")
EVID = os.path.join(ROOT, "build", "p", "R9")

sys.path.insert(0, HERE)
import copygate as CG  # noqa: E402  (the one sRGB->Lab + CIEDE2000 implementation the gates use)


def rel(p):
    return os.path.relpath(p, ROOT)


# ====================================================================================== colour maths

def hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float64)


def rgb_hex(rgb):
    r, g, b = (int(round(float(np.clip(v, 0, 255)))) for v in rgb)
    return f"{r:02X}{g:02X}{b:02X}"


def lab_of(h):
    return CG.rgb2lab(hex_rgb(h))


def lch_of(h):
    L, a, b = lab_of(h)
    return float(L), float(math.hypot(a, b)), float(math.degrees(math.atan2(b, a)) % 360)


_M_XYZ2RGB = np.array([[3.240479, -1.537150, -0.498535], [-0.969256, 1.875992, 0.041556], [0.055648, -0.204043, 1.057311]])


def lab_to_linrgb(L, a, b):
    """CIELAB (D65/2°) -> LINEAR sRGB (unclipped), the exact inverse of copygate.rgb2lab."""
    fy = (L + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200

    def finv(t):
        return t ** 3 if t ** 3 > 0.008856 else (t - 16 / 116) / 7.787
    xyz = np.array([finv(fx) * 0.95047, finv(fy), finv(fz) * 1.08883])
    return _M_XYZ2RGB @ xyz


def lin_to_srgb255(c):
    c = np.clip(c, 0, 1)
    return np.where(c > 0.0031308, 1.055 * c ** (1 / 2.4) - 0.055, 12.92 * c) * 255


def lch_to_hex(L, C, h):
    """LCh -> sRGB hex, keeping L* and hue and reducing chroma until the colour is inside the sRGB gamut (bisection).
    Returns (hex, clipped: bool)."""
    L = min(max(L, 0.0), 100.0)

    def lin(Cx):
        return lab_to_linrgb(L, Cx * math.cos(math.radians(h)), Cx * math.sin(math.radians(h)))
    eps = 1e-4
    c = lin(C)
    if np.all(c >= -eps) and np.all(c <= 1 + eps):
        return rgb_hex(lin_to_srgb255(c)), False
    lo, hi = 0.0, C
    for _ in range(40):
        mid = (lo + hi) / 2
        c = lin(mid)
        if np.all(c >= -eps) and np.all(c <= 1 + eps):
            lo = mid
        else:
            hi = mid
    return rgb_hex(lin_to_srgb255(lin(lo))), True


def de00(h1, h2):
    return float(CG.de2000(lab_of(h1), lab_of(h2)))


def hue_diff(a, b):
    """signed b - a in (-180, 180]."""
    return (b - a + 180.0) % 360.0 - 180.0


# ====================================================================================== scanning

HEX6 = re.compile(r"(?<![0-9A-Za-z_])0x([0-9A-Fa-f]{6})(?![0-9A-Fa-f_])")
HEXSTR = re.compile(r'"#([0-9A-Fa-f]{6})([0-9A-Fa-f]{2})?"')
HEX_ANY_TOKEN = re.compile(r"(?<![0-9A-Za-z_])0x[0-9A-Fa-f_]+")
SPLIT = re.compile(r"red:\s*0x([0-9A-Fa-f]{2})\s*/\s*255(?:\.0)?\s*,\s*green:\s*0x([0-9A-Fa-f]{2})\s*/\s*255(?:\.0)?\s*,\s*"
                   r"blue:\s*0x([0-9A-Fa-f]{2})\s*/\s*255(?:\.0)?")
NUM = r"(\d+(?:\.\d+)?(?:\s*/\s*255(?:\.0)?)?)"
DEC = re.compile(r"(?:UI)?Color\(\s*(?:\.sRGB,\s*)?red:\s*" + NUM + r"\s*,\s*green:\s*" + NUM + r"\s*,\s*blue:\s*" + NUM)
CGDEC = re.compile(r"CGColor\(\s*s?rgbRed:\s*" + NUM + r"\s*,\s*green:\s*" + NUM + r"\s*,\s*blue:\s*" + NUM)
SYSCOL = re.compile(r"\b(?:Color|UIColor)\.(blue|cyan|teal|indigo|green|yellow|orange|purple|pink|red|mint|brown|"
                    r"system(?:Blue|Teal|Indigo|Green|Red|Yellow|Orange|Purple|Pink|Mint|Cyan|Brown))\b")
SYS_HEX = {"blue": "007AFF", "cyan": "32ADE6", "teal": "30B0C7", "indigo": "5856D6", "green": "34C759", "yellow": "FFCC00",
           "orange": "FF9500", "purple": "AF52DE", "pink": "FF2D55", "red": "FF3B30", "mint": "00C7BE", "brown": "A2845E"}


def _num(s):
    s = s.replace(" ", "")
    if "/" in s:
        return float(s.split("/")[0])            # n / 255 -> channel n
    v = float(s)
    return v * 255.0                              # 0...1 -> channel


def swift_lex(text):
    """Split Swift source into (kind, start, end) spans: 'code', 'string', 'comment'. Handles //, nested /* */, "…" with
    escapes and interpolation, and \"\"\" multi-line strings (enough for colour scanning; not a full Swift lexer)."""
    spans, i, n = [], 0, len(text)
    code_start = 0

    def push(kind, a, b):
        if b > a:
            spans.append((kind, a, b))
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            push("code", code_start, i)
            j = text.find("\n", i)
            j = n if j < 0 else j
            push("comment", i, j)
            i = code_start = j
        elif text.startswith("/*", i):
            push("code", code_start, i)
            depth, j = 1, i + 2
            while j < n and depth:
                if text.startswith("/*", j):
                    depth, j = depth + 1, j + 2
                elif text.startswith("*/", j):
                    depth, j = depth - 1, j + 2
                else:
                    j += 1
            push("comment", i, j)
            i = code_start = j
        elif text.startswith('"""', i):
            push("code", code_start, i)
            j = text.find('"""', i + 3)
            j = n if j < 0 else j + 3
            push("string", i, j)
            i = code_start = j
        elif c == '"':
            push("code", code_start, i)
            j, depth = i + 1, 0
            while j < n:
                if text[j] == "\\":
                    if j + 1 < n and text[j + 1] == "(":
                        depth += 1
                        j += 2
                        continue
                    j += 2
                    continue
                if depth and text[j] == ")":
                    depth -= 1
                elif not depth and text[j] == '"':
                    break
                elif text[j] == "\n" and not depth:
                    break
                j += 1
            j = min(j + 1, n)
            push("string", i, j)
            i = code_start = j
        else:
            i += 1
    push("code", code_start, n)
    return spans


class LineIndex:
    def __init__(self, text):
        self.starts = [0] + [m.end() for m in re.finditer("\n", text)]
        self.text = text

    def pos(self, off):
        import bisect
        ln = bisect.bisect_right(self.starts, off) - 1
        return ln + 1, off - self.starts[ln] + 1

    def line(self, ln):
        a = self.starts[ln - 1]
        b = self.text.find("\n", a)
        return self.text[a:] if b < 0 else self.text[a:b]


def _occ(src, kind, path, off, end, hexv, alpha, li, ctx, extra=None):
    ln, col = li.pos(off)
    o = dict(source=src, kind=kind, file=path, line=ln, col=col, off=off, end=end, hex=hexv.upper(), alpha=alpha,
             text=li.text[off:end], line_text=li.line(ln).strip()[:240], ctx=ctx)
    if extra:
        o.update(extra)
    return o


TOKEN_KEY = re.compile(r'\b(?:t|tokens|T|tok|ui\.tokens|f)\.(color|colors|stops|text|string|strings)\(\s*"([^"]+)"')
STATIC_NAME = re.compile(r"\b(?:static\s+)?(?:let|var)\s+([A-Za-z_][A-Za-z0-9_]*)")
LABEL_NAME = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?:\[?\(?\s*)$")
DECL = re.compile(r"\b(struct|class|enum|extension|func|init|var|let|case)\s+\.?([A-Za-z_][A-Za-z0-9_]*)")
CASE_LABEL = re.compile(r"\bcase\s+\.([A-Za-z_][A-Za-z0-9_]*)")


def swift_scopes(text, spans):
    """[(open_off, close_off, name)] for every brace whose header declares something (struct/class/enum/extension/func/
    init/var/let/case NAME); anonymous closures are skipped. Braces inside strings/comments are ignored."""
    stack, out, last = [], [], 0
    for kind, a, b in spans:
        if kind != "code":
            continue
        for i in range(a, b):
            ch = text[i]
            if ch == "{":
                header = text[last:i][-400:]
                names = DECL.findall(header)
                stack.append((i, names[-1][1] if names else ""))
                last = i + 1
            elif ch == "}":
                if stack:
                    o, nm = stack.pop()
                    if nm:
                        out.append((o, i, nm))
                last = i + 1
    return out


def swift_context(text, off, line_start, scopes=()):
    """Context of a Swift literal: the token key it is the compiled default of (t.color("k", 0x…)), the nearest
    `let/var name` on its line (or just above), the argument label right before it, the `case .x` of its switch arm, and
    the enclosing declaration chain (innermost last)."""
    line_end = text.find("\n", off)
    before = text[line_start:off]
    key = ""
    for m in TOKEN_KEY.finditer(before):
        seg = before[m.start():]
        # only if the literal is still inside that call's parentheses
        if seg.count("(") - seg.count(")") >= 1:
            key = m.group(2)
    lm = LABEL_NAME.search(before)
    label = lm.group(1) if lm else ""
    names = STATIC_NAME.findall(before)
    name = names[-1] if names else ""
    if not name:
        lets = STATIC_NAME.findall(text[max(0, line_start - 400):line_start])
        name = lets[-1] if lets else ""
    cm = CASE_LABEL.findall(before)
    case = cm[-1] if cm else ""
    chain = [nm for o, c, nm in scopes if o < off < c]
    return dict(key=key, label=label, name=name, case=case, decl="/".join(chain[-3:]))


def scan_swift(path, src="swift"):
    text = open(path, encoding="utf-8").read()
    li = LineIndex(text)
    out, comments, nonc = [], 0, []
    spans = swift_lex(text)
    scopes = sorted(swift_scopes(text, spans))
    for kind, a, b in spans:
        seg = text[a:b]
        if kind == "comment":
            comments += len(HEX6.findall(seg)) + len(re.findall(r"#[0-9A-Fa-f]{6}\b", seg))
            continue
        if kind == "string":
            for m in HEXSTR.finditer(seg):
                off = a + m.start()
                ls = li.starts[li.pos(off)[0] - 1]
                alpha = int(m.group(2), 16) / 255 if m.group(2) else None
                out.append(_occ(src, "swift-hexstr", rel(path), off, a + m.end(), m.group(1), alpha, li,
                                swift_context(text, off, ls, scopes)))
            continue
        # code
        split_spans = []
        for m in SPLIT.finditer(seg):
            off = a + m.start()
            ls = li.starts[li.pos(off)[0] - 1]
            split_spans.append((off, a + m.end()))
            out.append(_occ(src, "swift-split", rel(path), off, a + m.end(), "".join(m.groups()), None, li,
                            swift_context(text, off, ls, scopes), dict(apply="manual")))
        for m in HEX6.finditer(seg):
            off = a + m.start()
            if any(s <= off < e for s, e in split_spans):
                continue
            ls = li.starts[li.pos(off)[0] - 1]
            out.append(_occ(src, "swift-hex", rel(path), off, a + m.end(), m.group(1), None, li, swift_context(text, off, ls, scopes)))
        for rx in (DEC, CGDEC):
            for m in rx.finditer(seg):
                off = a + m.start()
                if any(s <= off < e for s, e in split_spans):
                    continue
                try:
                    rgb = [_num(g) for g in m.groups()]
                except ValueError:
                    continue
                ls = li.starts[li.pos(off)[0] - 1]
                out.append(_occ(src, "swift-dec", rel(path), off, a + m.end(), rgb_hex(rgb), None, li,
                                swift_context(text, off, ls, scopes), dict(apply="manual")))
        for m in SYSCOL.finditer(seg):
            off = a + m.start()
            ls = li.starts[li.pos(off)[0] - 1]
            nm = m.group(1)
            base = nm[6:].lower() if nm.startswith("system") else nm
            out.append(_occ(src, "swift-system", rel(path), off, a + m.end(), SYS_HEX.get(base, "808080"), None, li,
                            swift_context(text, off, ls, scopes), dict(apply="manual")))
        # every other hex token in code: must be a known non-colour (seed / mask / hash) — recorded, classified 'non-colour'
        for m in HEX_ANY_TOKEN.finditer(seg):
            tok = m.group(0)
            off = a + m.start()
            digits = tok[2:].replace("_", "")
            if len(tok[2:]) == 6 and "_" not in tok:
                continue                          # a 6-digit token: handled above
            if any(s <= off < e for s, e in split_spans):
                continue
            nonc.append(dict(file=rel(path), line=li.pos(off)[0], text=tok, digits=len(digits)))
    return out, comments, nonc


def json_paths(obj, path=""):
    """(path, value) of every string leaf, in document order (json.load keeps key order)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from json_paths(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from json_paths(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


JSON_HEX_VAL = re.compile(r"^#([0-9A-Fa-f]{6})([0-9A-Fa-f]{2})?$")


def scan_json(path):
    text = open(path, encoding="utf-8").read()
    li = LineIndex(text)
    obj = json.loads(text)
    leaves = [(p, v) for p, v in json_paths(obj) if JSON_HEX_VAL.match(v)]
    raw = list(HEXSTR.finditer(text))
    if len(raw) != len(leaves):
        raise SystemExit(f"palette_map: {rel(path)}: {len(raw)} hex strings in the text but {len(leaves)} hex values in the JSON")
    out = []
    for (p, v), m in zip(leaves, raw):
        if v.upper() != "#" + (m.group(1) + (m.group(2) or "")).upper():
            raise SystemExit(f"palette_map: {rel(path)}: order mismatch at {p}")
        alpha = int(m.group(2), 16) / 255 if m.group(2) else None
        out.append(_occ("json", "json-hex", rel(path), m.start(), m.end(), m.group(1), alpha, li, dict(key=p)))
    return out


def scan_colorset(path):
    text = open(path, encoding="utf-8").read()
    li = LineIndex(text)
    d = json.loads(text)
    out = []
    for c in d.get("colors", []):
        comp = c["color"]["components"]

        def ch(v):
            v = str(v)
            return int(v, 16) if v.lower().startswith("0x") else float(v) * 255
        rgb = [ch(comp[k]) for k in ("red", "green", "blue")]
        m = re.search(r'"red"', text)
        out.append(_occ("colorset", "colorset", rel(path), m.start(), m.end(), rgb_hex(rgb), None, li,
                        dict(key=os.path.basename(os.path.dirname(path))), dict(apply="manual")))
    return out


SVG_GENS = ["art/ui/src/gen_chrome.py", "art/ui/src/gen_board.py", "art/ui/src/gen_props.py", "art/ui/src/svg/gen_icons.py",
            "art/ui/src/svg/gen_missing.py", "art/ui/src/characters/gen_avatars.py"]
PYHEX = re.compile(r"#([0-9A-Fa-f]{6})(?![0-9A-Fa-f])")


def _py_graph(tree):
    """function name -> set of names it references (calls + loads), module constant names, CASES map case -> expr names."""
    refs, consts, cases, spans = {}, {}, {}, []

    class V(ast.NodeVisitor):
        def __init__(self):
            self.stack = []

        def visit_FunctionDef(self, node):
            spans.append((node.lineno, node.end_lineno, node.name))
            self.stack.append(node.name)
            refs.setdefault(node.name, set())
            self.generic_visit(node)
            self.stack.pop()

        def visit_Name(self, node):
            if self.stack:
                refs[self.stack[-1]].add(node.id)

        def visit_Attribute(self, node):
            self.generic_visit(node)
    V().visit(tree)
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            nm = node.targets[0].id
            consts.setdefault(nm, []).append((node.lineno, node.end_lineno, node.value))
            if nm == "CASES" and isinstance(node.value, ast.Dict):
                for k, v in zip(node.value.keys, node.value.values):
                    if isinstance(k, ast.Constant):
                        cases[k.value] = {n.id for n in ast.walk(v) if isinstance(n, ast.Name)}
                        cases[k.value] |= {n.value for n in ast.walk(v) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    return refs, consts, cases, spans


def scan_py(path, manifest_cases):
    text = open(path, encoding="utf-8").read()
    li = LineIndex(text)
    tree = ast.parse(text)
    refs, consts, cases, spans = _py_graph(tree)
    doc_lines = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body and isinstance(node.body[0], ast.Expr) \
                and isinstance(getattr(node.body[0], "value", None), ast.Constant) and isinstance(node.body[0].value.value, str):
            doc_lines.update(range(node.body[0].lineno, node.body[0].end_lineno + 1))
    # reachability: case -> every function/const it reaches
    reach = {}
    funcs = set(refs)

    def closure(names):
        seen, todo = set(), list(names)
        while todo:
            n = todo.pop()
            if n in seen:
                continue
            seen.add(n)
            todo.extend(refs.get(n, ()))
        return seen
    for case, names in cases.items():
        reach[case] = closure(names)
    # the manifest's cases for this file (case names the batch builds); a case not in CASES but in the manifest is noted
    file_cases = manifest_cases.get(rel(path), {})
    out, comments = [], 0
    toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    for tok in toks:
        if tok.type == tokenize.COMMENT:
            comments += len(PYHEX.findall(tok.string))
            continue
        if tok.type != tokenize.STRING and tokenize.tok_name.get(tok.type) not in ("FSTRING_MIDDLE", "TSTRING_MIDDLE"):
            continue
        if tok.start[0] in doc_lines:
            comments += len(PYHEX.findall(tok.string))
            continue
        base = li.starts[tok.start[0] - 1] + tok.start[1]
        for m in PYHEX.finditer(tok.string):
            off = base + m.start()
            if text[off:off + 7].upper() != "#" + m.group(1).upper():
                # an f-string middle whose '{{' / '}}' were un-doubled: find the literal on the same line from the token start
                j = text.find("#" + m.group(1), base)
                if j < 0 or li.pos(j)[0] != tok.start[0]:
                    raise SystemExit(f"palette_map: cannot place #{m.group(1)} in {rel(path)}:{tok.start[0]}")
                off = j
            ln = li.pos(off)[0]
            fn = ""
            for a, b, name in spans:
                if a <= ln <= b and (not fn or a >= fn[1]):
                    fn = (name, a)
            fn = fn[0] if fn else ""
            const, ckey = "", ""
            if not fn:
                for nm, rngs in consts.items():
                    for a, b, val in rngs:
                        if a <= ln <= b:
                            const = nm
                            if isinstance(val, ast.Dict):
                                for k, v in zip(val.keys, val.values):
                                    if isinstance(k, ast.Constant) and v.lineno <= ln <= v.end_lineno:
                                        ckey = str(k.value)
            owner = fn or const
            used_by = sorted(c for c, r in reach.items() if owner and owner in r)
            ids = sorted({file_cases.get(c, c) for c in used_by if c in file_cases})
            out.append(_occ("svg", "py-hex", rel(path), off, off + 7, m.group(1), None, li,
                            dict(func=fn, const=const, ckey=ckey, cases=used_by, ids=ids)))
    return out, comments


def manifest_info():
    m = json.load(open(os.path.join(ROOT, "art", "MANIFEST.json")))
    byid, cases = {}, {}
    for e in m["entries"]:
        byid[e["id"]] = e
        s = str(e.get("source") or "")
        if ":" in s:
            f, c = s.split(":", 1)
            cases.setdefault(f, {})[c] = e["id"]
    return byid, cases


def swift_files():
    fs = []
    for base in ("App", os.path.join("art", "ui", "code")):
        for dp, dn, fn in os.walk(os.path.join(ROOT, base)):
            dn[:] = sorted(d for d in dn if d not in ("Resources",))
            for f in sorted(fn):
                if f.endswith(".swift"):
                    fs.append(os.path.join(dp, f))
    return fs


def scan_all():
    byid, mcases = manifest_info()
    occ, stats = [], dict(comment_hex=0, non_colour_tokens=[], files={})
    for p in swift_files():
        o, c, nonc = scan_swift(p)
        occ += o
        stats["comment_hex"] += c
        stats["non_colour_tokens"] += nonc
    pc = os.path.join(ROOT, "Packages", "PathCore", "Sources")
    for dp, dn, fn in os.walk(pc):
        for f in sorted(fn):
            if f.endswith(".swift"):
                o, c, nonc = scan_swift(os.path.join(dp, f), src="pathcore")
                occ += o
                stats["comment_hex"] += c
    tun = os.path.join(ROOT, "App", "Resources", "Tuning")
    for f in sorted(os.listdir(tun)):
        if f.endswith(".json"):
            occ += scan_json(os.path.join(tun, f))
    xc = os.path.join(ROOT, "App", "Resources", "Assets.xcassets")
    for dp, dn, fn in os.walk(xc):
        if dp.endswith(".colorset") and "Contents.json" in fn:
            occ += scan_colorset(os.path.join(dp, "Contents.json"))
    for g in SVG_GENS:
        o, c = scan_py(os.path.join(ROOT, g), mcases)
        occ += o
        stats["comment_hex"] += c
    for o in occ:
        stats["files"][o["file"]] = stats["files"].get(o["file"], 0) + 1
        o["id"] = f"{o['file']}:{o['line']}:{o['col']}"
    return occ, stats, byid




# ====================================================================================== OKLCh (classification windows only)

_OK_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566],
                   [0.0883024619, 0.2817188376, 0.6299787005]])
_OK_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099],
                   [0.0259040371, 0.7827717662, -0.8086757660]])


def oklch_rgb(rgb):
    """sRGB 0-255 (…, 3) -> OKLCh (L 0-1, C, h degrees). OKLab's hue is near-uniform in the blue-violet range where CIELAB
    bends (royal navies and violets share CIELAB hue ~300-306), so the family WINDOWS use it; the MAPPING stays in CIELAB."""
    c = np.clip(np.asarray(rgb, np.float64) / 255.0, 0, 1)
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    lms = np.cbrt(c @ _OK_M1.T)
    lab = lms @ _OK_M2.T
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    return L, np.hypot(a, b), np.degrees(np.arctan2(b, a)) % 360


def oklch_of(h):
    L, C, hh = oklch_rgb(hex_rgb(h))
    return float(L), float(C), float(hh)


# ====================================================================================== families and D1 ladders
#
# A MAPPED family carries anchor pairs (today's measured token -> its D1 token). Mapping one colour (L*, C*, h) of the family:
#   * L*:  lmode "keep" -> the colour's own L* (art-direction §7.3 step 3); lmode "ladder" -> the source L* is carried along the
#          anchors' L* ladder (piecewise linear between anchors, slope 1 outside) — used where keeping L* breaks the token
#          (the title ribbon becomes pale peach, R1 finding) and for the two-colour engine family;
#   * C*:  the colour's own chroma x the family's chroma ratio at that L* (C_D1 / C_today, interpolated between anchors by
#          source L*): "chroma relative to the family's anchor", so a gradient's stops keep their chroma order and spacing;
#   * h:   the D1 ladder's hue at that L* + kh x (the colour's hue offset from the anchors' source hue at that L*), clamped to
#          the family's D1 hue range: gradients and light edges keep a (compressed) trace of their hue structure;
#   * then the chroma is reduced (L* and h kept) until the colour is inside sRGB.
# A mapped colour that moves by less than ΔE00 1.0 is written as "keep (sub-JND)" to avoid churn.

FAMILIES = {
    "chrome-blue": dict(
        action="map", lmode="keep", kh=0.35, hue_clamp=(168.0, 216.0),
        what="blue chrome: glossy button faces/rims/light edges, panel frames/fields/bumpers/rivets, navy outlines and text "
             "outlines, royal page backgrounds, HUD pills/panels/timer, nav bar + raised tab, toggles, blue labels and tints",
        d1="the D1 teal chrome ladder (art-direction §3.1 'UI colour shift'): face #17B3A3, light edge #7FEADB, rim #0B8A83 -> "
           "#075E5E, outline #053F43, page #155158, HUD pill #D4F4EC, HUD digits #0B5A55",
        anchors=[("BDDCFF", "D4F4EC", "HUD pill fill (STYLE §D hud.coinPill.fill)"),
                 ("50C8FF", "7FEADB", "face light edge (STYLE §B square button)"),
                 ("0192FF", "17B3A3", "button face (STYLE §B)"),
                 ("3861AC", "0B5A55", "HUD pill digits (STYLE §D)"),
                 ("0047DB", "0B8A83", "rim top (STYLE §B)"),
                 ("0036BE", "075E5E", "rim bottom (STYLE §B)"),
                 ("16388C", "155158", "page background (art §3.1)"),
                 ("0B2B86", "053F43", "outline (STYLE §B glyph outline)")]),
    "go-green": dict(
        action="map", lmode="keep", kh=0.30, hue_clamp=(50.0, 96.0),
        what="the green 'go' family: Play/Resume/Continue pills, level plate, toggles ON, booster squircles, plus/check icons, "
             "the claw bar fill, the 'me' row, green text outlines",
        d1="the D1 sunflower-orange CTA ladder (art §3.1; OD7 default): face #FFB422 -> #FF9A12, light edge #FFE08A, rim "
           "#D06A06 -> #9E4A00, outline #6B2E00, label outline #8A3F00",
        anchors=[("0A3C00", "6B2E00", "outline"), ("004A00", "9E4A00", "rim bottom"), ("006400", "D06A06", "rim"),
                 ("076D02", "8A3F00", "label outline (Play)"), ("00CA00", "FF9A12", "face bottom"),
                 ("00E400", "FFB422", "face"), ("66EC66", "FFE08A", "face light edge")]),
    "plank": dict(
        action="map", lmode="ladder", kh=0.25, hue_clamp=(50.0, 88.0),
        what="the popup title ribbon (yellow arched banner + orange shade + brown outlines), its title-text outline, the "
             "shop's yellow section plate",
        d1="the honey-wood plank ladder (art §3.1 title ribbon: #F0B86A -> #D9913E, rim #9E5F24, label #6A3510; timber "
           "#7E4E27). LADDER mode: keeping L* made the ribbon a pale peach (R1 palette mock), so L* follows the plank tokens",
        anchors=[("662200", "4A2812", "outline bottom (timber, darker)"), ("7B1D01", "6A3510", "title text outline (label)"),
                 ("993805", "7E4E27", "outline top (timber dark)"), ("D95700", "9E5F24", "shade = plank rim"),
                 ("F9A600", "D9913E", "face bottom"), ("FFD808", "F0B86A", "face top"),
                 ("FFF741", "FAD9A0", "top highlight (light honey)")]),
    "danger-red": dict(
        action="map", lmode="keep", kh=0.30, hue_clamp=(28.0, 48.0),
        what="danger / Hard reds: Quit pill, close X disc, count badges, Hard plate/tab/ribbon, red text and outlines",
        d1="the D1 danger ladder (art §3.1: face #F2553F -> #DC3A26, rim #A82314); red stays red (ΔE00 ~4, generic)",
        anchors=[("A0000C", "A82314", "rim"), ("E20808", "DC3A26", "face bottom"), ("FF3838", "F2553F", "face")]),
    "cream": dict(
        action="map", lmode="keep", kh=0.30, hue_clamp=(55.0, 95.0),
        what="cream insets, card bevels and borders, toggle wells, warm light text fills and bands",
        d1="the D1 cream (art §3.1 panel inset #FFF3DF, border #D8A878)",
        anchors=[("D0987D", "D8A878", "card border"), ("F8E7D2", "FFF3DF", "panel inset")]),
    "ink-brown": dict(
        action="map", lmode="keep", kh=0.30, hue_clamp=(45.0, 70.0),
        what="dark warm inks: panel labels and text outlines on cream and orange",
        d1="the D1 label brown (art §3.1 label #6A3510; STYLE §B panel label #632201 today)",
        anchors=[("632201", "6A3510", "panel label ink")]),
    "berry": dict(
        action="map", lmode="keep", kh=0.30, hue_clamp=(338.0, 372.0),
        what="purple / violet / magenta chrome: purple buttons, Super Hard plate/tab/ribbon/tag, purple frames and outlines, "
             "the shop's purple section plate, event page purples",
        d1="a berry ladder from the boss's pink fur (art §3.0/§3.1 boss ladder #FFA8C8 ... #B22470): D1 has no violet, and "
           "the violet arrow sign / buttons are the original's secondary colour",
        anchors=[("230D63", "3A0A20", "outline"), ("43007E", "5E0F34", "rim dark"), ("8300CF", "B22470", "face bottom"),
                 ("B45CF5", "E8488A", "face"), ("E0B8FF", "FFB3CF", "glare")]),
    "exit-accent": dict(
        action="owner:R7", lmode="ladder", kh=0.0, hue_clamp=(40.0, 90.0),
        what="the board's exit colour and vacated dots (engine colours)",
        d1="tangerine exit #FF8F1F, dots #FFDDB0 (art §3.1). R7 BOARD-UI owns the 2 engine colours (PLAN-P §4.2)",
        anchors=[("10A2EF", "FF8F1F", "exit"), ("C5E1FF", "FFDDB0", "vacated dot")]),
    "loading-base": dict(
        action="owner:R4", lmode="keep", kh=0.0, hue_clamp=(190.0, 215.0),
        what="the launch-screen background and the Loading base colour (a lavender/mauve under the Loading art)",
        d1="R4 LOADING sets it from the new Loading backdrop; reference = D1 rock #4E7F86 at the same L*",
        anchors=[("927E94", "4E7F86", "launch background"), ("ABA0D8", "7FA3A6", "Loading base (lavender)")]),
}

EXCLUDED = {
    "neutral": "white / black / grey (CIELAB C* < 4): generic, unchanged",
    "gold-accent": "saturated gold / yellow / orange accents outside the title ribbon (coins, stars, prize and claim titles, "
                   "streak flames, claw bar palette): generic genre colours and already inside D1's warm ladder (hat #FFCB2F, "
                   "lantern #FFCF6B, vest #FF8A2A)",
    "heart": "hearts / lives: generic (art §2.2 #21, the §7.3 excluded families)",
    "medal": "gold / silver / bronze rank medals and rows: generic genre props (art §2.2 #21)",
    "ice": "the Freeze booster's ice and frost: semantic ice colours, generic",
    "fx-multicolour": "confetti / fireworks / sparkles / rainbow and violet trails / star trails: generic celebration "
                      "palettes (board trails are LOW risk, art §2.2 #19; kept)",
    "board-mechanics": "board ink/ground, marked red, bump badge, hint green, the vignette/bump curves: the board is kept by "
                       "ruling (art §2.2 #20)",
    "board-skin": "board obstacle skins drawn in code or by gen_board.py (tape, door, lock, key, pipe, box, counter, elevator, "
                  "corner, shards): R7 BOARD-UI RESKINS them (new shapes and colours), so a remap would be thrown away; the "
                  "hue family and a reference mapping are recorded",
    "logo": "the win/Loading logo parts: R6 LOGO restyles them (LG-1) in gen_icons.py",
    "owned-svg": "SVG art another package REDRAWS (R7: unlock icons, tutorial hand, pointers, pageBgPattern; R2: avatars)",
    "not-shipped": "a generator constant no shipped manifest id bakes (spike / comparison-only / superseded / removed art)",
    "debug-ui": "developer screens reachable only through -pc launch arguments (SoundBoard, SocialLab, DebugOverlay, "
                "DebugPlaceholder): their own tool colours, not player-visible, not in the capture list",
    "non-colour": "a hex token that is not a colour (an RNG seed)",
}

OWNER_OF_EXCLUDED = {"board-skin": "owner:R7", "logo": "owner:R6"}

# The map is applied ONCE, to today's tree (A5). After it, the "old chrome-blue" check uses this OKLab window: the D1 teal
# outputs sit at OK hue <= ~210 (page #155158 = 206), today's blues at 213-280.
OLD_BLUE_WINDOW = (218.0, 280.0, 0.04)     # OK hue from, to, minimum OK chroma
ALLOWED_AFTER = ("ice", "medal", "fx-multicolour", "board-mechanics", "board-skin", "exit-accent", "debug-ui", "not-shipped",
                 "non-colour", "neutral", "heart", "logo", "owned-svg", "loading-base")


def _unwrap(hs):
    out = [hs[0]]
    for h in hs[1:]:
        out.append(out[-1] + hue_diff(out[-1] % 360, h % 360))
    return out


def _interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    return float(np.interp(x, xs, ys))


class Ladder:
    def __init__(self, name, fam):
        self.name, self.fam = name, fam
        rows = []
        for s, d, role in fam["anchors"]:
            sL, sC, sh = lch_of(s)
            dL, dC, dh = lch_of(d)
            rows.append(dict(src=s, dst=d, role=role, sL=sL, sC=sC, sh=sh, dL=dL, dC=dC, dh=dh))
        rows.sort(key=lambda r: r["sL"])
        self.rows = rows
        self.xs = [r["sL"] for r in rows]
        self.dh = _unwrap([r["dh"] for r in rows])
        self.sh = _unwrap([r["sh"] for r in rows])
        self.cr = [r["dC"] / max(r["sC"], 1e-6) for r in rows]
        self.dL = [r["dL"] for r in rows]
        lo, hi = fam["hue_clamp"]
        self.clamp = (lo, hi)

    def lmap(self, L):
        if self.fam["lmode"] == "keep":
            return L
        xs, ys = self.xs, self.dL
        if len(xs) == 1:
            return L + (ys[0] - xs[0])
        if L <= xs[0]:
            return ys[0] + (L - xs[0])
        if L >= xs[-1]:
            return ys[-1] + (L - xs[-1])
        return float(np.interp(L, xs, ys))

    def map(self, hx):
        L, C, h = lch_of(hx)
        dh0 = _interp(self.xs, self.dh, L)
        sh0 = _interp(self.xs, self.sh, L)
        rel = hue_diff(sh0 % 360, h) if C > 1.0 else 0.0
        hh = dh0 + self.fam["kh"] * rel
        lo, hi = self.clamp
        # clamp in the unwrapped frame around the ladder's hue range
        base = dh0
        lo_u = base + hue_diff(base % 360, lo % 360)
        hi_u = lo_u + (hi - lo)
        hh = min(max(hh, lo_u), hi_u)
        C2 = C * _interp(self.xs, self.cr, L)
        L2 = min(max(self.lmap(L), 0.0), 100.0)
        new, clipped = lch_to_hex(L2, C2, hh % 360)
        return new, clipped


LADDERS = {k: Ladder(k, v) for k, v in FAMILIES.items()}


# ====================================================================================== classification rules
#
# Order: (1) non-colour tokens, (2) whole-file / whole-source decisions (dev screens, board, generators' owners),
# (3) semantic context exclusions (hearts, ice, medals, fx), (4) context families (the title ribbon -> plank), (5) the
# OKLCh hue WINDOWS, which leave deliberate GAPS between families, (6) explicit per-literal decisions for the gap colours.
# Anything a gap still holds after (6) is UNCLASSIFIED and fails `build`.

DEBUG_FILES = re.compile(r"(^|/)(SoundBoard|SocialLab|DebugOverlay|DebugPlaceholder)\.swift$")   # ShellLab mirrors the
# production chrome through the same token keys, so it maps like production (its fallbacks must equal the mapped ui.json)
BOARD_SKIN_FILES = re.compile(r"^App/Board/(PipeLayer|DoorLayer|CounterLayer|ElevatorLayer|CornerLayer|Shards|TapeLayer|"
                              r"LockLayer|KeyLayer|BoxLayer|CurtainLayer)\.swift$")
R7_SVG_IDS = re.compile(r"^(unlockIcon.*|tutorialHand|pointerArrow.*|pageBgPattern|boardTrailStar|doorShards|pipeShards)$")
OWNER_SVG = [(re.compile(r"^logo"), "logo", "owner:R6"),
             (R7_SVG_IDS, "owned-svg", "owner:R7"),
             (re.compile(r"^avatar"), "owned-svg", "owner:R2")]

# windows in OKLab hue (degrees). Gaps between them are deliberate: a literal there needs an explicit decision.
WINDOWS = [("danger-red", 5.0, 38.0), ("warm", 38.0, 112.0), ("go-green", 118.0, 172.0), ("chrome-blue", 180.0, 276.0),
           ("berry", 284.0, 365.0)]
TEXT_INK = re.compile(r"^(outline|dropColor|ink|textOutline|digit|caption|label|line|st|style|labelStyle|countStyle|saveStyle)$")

# Explicit decisions for the literals the windows leave in a GAP (OK hue 112-118, 172-180, 280-284): each names its reason.
# (file regex, hex or None, context regex or None, family, why)
EXPLICIT = [
    (r".", None, r"(?i)purple|SuperHard|case=purple|SkyJumpViews\.swift \| .*SocSky|OfferCardFrame", "berry",
     "indigo-violet in a purple context (purple button / plate, Sky Jump purple panel, the purple offer card)"),
    (r".", None, None, "chrome-blue",
     "indigo navy between blue and violet (OK hue 276-284) outside any purple context: a navy of the blue chrome"),
]
def _ctx_str(o):
    c = o["ctx"]
    parts = [os.path.basename(o["file"])]
    for k in ("key", "name", "label", "case", "decl", "func", "const"):
        if c.get(k):
            parts.append(f"{k}={c[k]}")
    if c.get("ids"):
        parts.append("ids=" + ",".join(c["ids"]))
    parts.append("line=" + o["line_text"])
    return " | ".join(parts)


def _is(o, rx, fields=("key", "name", "label", "case", "decl", "func", "const")):
    c = o["ctx"]
    return any(re.search(rx, str(c.get(f) or "")) for f in fields)


def _near_line(o, rx):
    return re.search(rx, o["line_text"]) is not None


def window_family(hx, o=None):
    """The family by OKLab hue window + lightness/chroma sub-rules (None = a gap)."""
    L, C, h = lch_of(hx)
    if C < 4.0:
        return "neutral", "C*<4"
    Lo, Co, ho = oklch_of(hx)
    for name, a, b in WINDOWS:
        if a <= ho < b or a <= ho + 360 < b:
            if name == "warm":
                ink = o is not None and TEXT_INK.search(o["ctx"].get("label") or o["ctx"].get("name") or "")
                if Lo >= 0.62:
                    return (("cream", f"warm, light low-chroma (OK L {Lo:.2f} C {Co:.3f})") if Co < 0.105 else
                            ("gold-accent", f"warm, light saturated (OK L {Lo:.2f} C {Co:.3f})"))
                if Lo < 0.52:
                    if ink or Co < 0.13:
                        return "ink-brown", f"warm, dark{' text ink' if ink else ''} (OK L {Lo:.2f} C {Co:.3f})"
                    return "gold-accent", f"warm, dark saturated orange (OK L {Lo:.2f} C {Co:.3f})"
                return (("gold-accent", f"warm, mid-L saturated (OK L {Lo:.2f} C {Co:.3f})") if Co >= 0.105 else
                        ("cream", f"warm, mid-L low-chroma brown (OK L {Lo:.2f} C {Co:.3f})"))
            if name == "danger-red" and Co < 0.05:
                return ("cream" if Lo >= 0.62 else "ink-brown"), f"red window, low chroma (OK C {Co:.3f})"
            return name, f"OK hue {ho:.1f} in [{a:g},{b:g})"
    return None, f"OK hue {ho:.1f} in a gap between windows"


def classify(o):
    """-> dict(family, action, rule). action: map | keep | owner:Rn | keep (sub-JND) is decided later from the ΔE."""
    f, hx, src = o["file"], o["hex"], o["source"]
    cs = _ctx_str(o)
    # (1) non-colour
    if o["kind"] == "swift-hex" and re.search(r"seed:|UInt64\(0x" + hx, o["line_text"], re.I):
        return dict(family="non-colour", action="keep", rule="RNG seed token")
    # (2) whole-file / whole-source
    if DEBUG_FILES.search(f):
        return dict(family="debug-ui", action="keep", rule="developer screen file")
    if src == "pathcore":
        return dict(family="board-mechanics", action="keep", rule="PathCore board feedback curve")
    if src == "colorset":
        return dict(family="loading-base", action="owner:R4", rule="launch background colour set")
    if src == "svg":
        ids = o["ctx"].get("ids") or []
        if f.endswith("gen_board.py"):
            return dict(family="board-skin", action="owner:R7", rule="gen_board.py = board obstacle skins (R7 reskin)")
        if not ids:
            return dict(family="not-shipped", action="keep", rule="no shipped manifest id reaches this constant")
        live = [i for i in ids if MANIFEST_BYID.get(i, {}).get("status") != "not-shipped"]
        if not live:
            return dict(family="not-shipped", action="keep", rule="only not-shipped ids (" + ",".join(ids) + ")")
        owners = set()
        free = []
        for i in live:
            for rx_, fam_, act_ in OWNER_SVG:
                if rx_.search(i):
                    owners.add((fam_, act_))
                    break
            else:
                free.append(i)
        if owners and not free:
            fam_, act_ = sorted(owners)[0]
            return dict(family=fam_, action=act_, rule="svg ids " + ",".join(live[:4]) + ("…" if len(live) > 4 else ""))
        o["_svg_shared_with"] = sorted({a for _, a in owners})
    if f.startswith("App/Resources/Tuning/board.json"):
        k = o["ctx"].get("key", "")
        if k in ("color.exit", "color.dot"):
            return dict(family="exit-accent", action="owner:R7", rule="board engine colour " + k)
        if re.search(r"rainbow|violet|stars", k):
            return dict(family="fx-multicolour", action="keep", rule="board trail palette " + k)
        return dict(family="board-mechanics", action="keep", rule="board.json " + k)
    if f.startswith("App/Board/"):
        if f.endswith("DotsPainter.swift"):
            return dict(family="exit-accent", action="owner:R7", rule="vacated-dot engine colour")
        if BOARD_SKIN_FILES.search(f):
            return dict(family="board-skin", action="owner:R7", rule="board obstacle layer (R7 reskin)")
        if f.endswith("EffectsConfig.swift") and re.search(r"palette|solidColors|violet|rainbow|stars", o["line_text"]):
            return dict(family="fx-multicolour", action="keep", rule="board trail palette default")
        return dict(family="board-mechanics", action="keep", rule="board engine (" + os.path.basename(f) + ")")
    if f == "App/Support/Tuning.swift":
        if re.search(r"exitColor|dotColor", o["line_text"]):
            return dict(family="exit-accent", action="owner:R7", rule="board engine colour default (Tuning.swift)")
        if re.search(r"rainbow|violet|palette", o["line_text"]) or o["line"] in (135, 136):
            return dict(family="fx-multicolour", action="keep", rule="board trail palette default (Tuning.swift)")
        return dict(family="board-mechanics", action="keep", rule="board engine default (Tuning.swift)")
    # (3) semantic exclusions from context (the enclosing declaration / token key / generator function names the thing)
    if _is(o, r"(^|\.)heart|Heart(HUD|Big|Glossy|Shape|Icon|Lives|Broken|Infinite)|GlossyHeart|^heart_", ("key", "decl", "func", "const")) \
            and window_family(hx, o)[0] != "chrome-blue":         # a heart's navy halo / empty HUD slot is HUD chrome
        return dict(family="heart", action="keep", rule="heart art (" + (o["ctx"].get("key") or o["ctx"].get("decl") or o["ctx"].get("func") or "") + ")")
    if _is(o, r"(?i)^freeze\.frost|frostColor|icicle|Frozen|^frost|Frost(Cap|Vignette)|IceCap|iceCap|^_?snow") or \
            (o["ctx"].get("ids") and all("Frozen" in i or i.startswith("frost") for i in o["ctx"]["ids"])) or \
            re.search(r"frostColor", o["line_text"]) or (f.endswith("HUDFreeze.swift") and _ice_cap(o)):
        return dict(family="ice", action="keep", rule="ice / frost")
    if (_is(o, r"^(gold|silver|bronze)$|rankBadge(Gold|Silver|Bronze)|^RANK\d*$|^rank_badge|^rank_wings|Medal")
            and o["ctx"].get("ckey") != "plain") or o["ctx"].get("case") in ("gold", "silver", "bronze"):
        return dict(family="medal", action="keep", rule="medal / rank (" + (o["ctx"].get("case") or o["ctx"].get("func") or o["ctx"].get("const") or "") + ")")
    if _is(o, r"(?i)confetti|firework|sparkle|rainbow") or re.search(r"(?i)/(Confetti|Fireworks|Sparkles)\.swift$", f):
        return dict(family="fx-multicolour", action="keep", rule="celebration palette")
    if f.endswith("CoinFly.swift"):
        return dict(family="gold-accent", action="keep", rule="flying coin")
    if _is(o, r"(^|\.)loading\.base$", ("key",)) or re.search(r'"loading\.base"', o["line_text"]):
        return dict(family="loading-base", action="owner:R4", rule="Loading base colour (R4)")
    # (4) the title ribbon + its title text + the shop's yellow section plate -> plank (warm hues only)
    L_, C_, _h = lch_of(hx)
    Lo, Co, ho = oklch_of(hx)
    warm = C_ >= 4 and (ho >= 30 and ho < 118) and not (Lo > 0.9 and Co < 0.08)   # cream text fills stay cream
    if warm and (_is(o, r"^(colors\.)?ribbon\.|^gradients\.pause\.ribbon|^text\.popup\.title\.outline$|^popup\.title$")
                 or (f.endswith("PopupChrome.swift") and re.search(r't\.colors?\("ribbon\.|"popup\.title"', o["line_text"])
                     and not re.search(r"band:", o["line_text"][:0]))
                 or (f.endswith("ShopView.swift") and re.search(r"case \.yellow", o["line_text"]))):
        if not (re.search(r"band: Color\(hex: 0x" + hx, o["line_text"]) or o["ctx"].get("key", "").endswith(".band")):
            return dict(family="plank", action="map", rule="title ribbon / plate context")
    # (5) windows, (6) explicit decisions for the gaps
    fam, why = window_family(hx, o)
    if fam is None:
        for rx_file, hx_, rx_ctx, fam_, why_ in EXPLICIT:
            if re.search(rx_file, f) and (hx_ is None or hx_ == hx) and (rx_ctx is None or re.search(rx_ctx, cs)):
                return dict(family=fam_, action=FAMILIES[fam_]["action"] if fam_ in FAMILIES else "keep",
                            rule=f"gap ({why}) -> explicit: " + why_)
    if fam is None:
        return dict(family="UNCLASSIFIED", action="?", rule=why)
    act = FAMILIES[fam]["action"] if fam in FAMILIES else "keep"
    return dict(family=fam, action=act, rule="window: " + why)


MANIFEST_BYID = {}


def _ice_cap(o):
    """HUDFreeze.swift's ice cap (the icicle layer: fill / stroke / shadow set right after the path)."""
    return bool(re.search(r"^l\.(fillColor|strokeColor|shadowColor) = UIColor\(rgb: 0x", o["line_text"]))


# ====================================================================================== pipeline

def group_key(o):
    """Literals that form one gradient / one style: the same code line, or the same JSON key with its indices stripped."""
    if o["source"] == "json":
        return (o["file"], re.sub(r"(\[\d+\])+$", "", o["ctx"].get("key", "")))
    return (o["file"], o["line"])


WARM_MAPPED = ("cream", "ink-brown")


def cohere(occ):
    """A gradient must not be half-mapped: (a) when a group holds gold-accent (kept) stops AND cream/ink-brown (mapped) stops,
    the warm stops of that group stay together as gold-accent; (b) a blue/violet GAP literal (OK hue 276-284) follows the
    family its group's window-classified stops agree on (berry or chrome-blue). Returns the number of literals changed."""
    groups, n = {}, 0
    for o in occ:
        groups.setdefault(group_key(o), []).append(o)
    for g in groups.values():
        gs = sorted(g, key=lambda o: o["off"])
        for i, o in enumerate(gs):
            if not o["rule"].startswith("gap"):
                continue
            # the nearest window-classified blue/violet stop on each side (a gradient profile: frame blue | face violet)
            near = []
            for j in list(range(i - 1, -1, -1)) + list(range(i + 1, len(gs))):
                q = gs[j]
                if q["family"] in ("berry", "chrome-blue") and q["rule"].startswith("window"):
                    near.append((abs(j - i), q["family"]))
            if near:
                dmin = min(d_ for d_, _ in near)
                fams_ = {f_ for d_, f_ in near if d_ == dmin}
                if len(fams_) == 1:
                    maj = fams_.pop()
                    if maj != o["family"]:
                        o["family"], o["action"] = maj, FAMILIES[maj]["action"]
                        o["rule"] += f" -> {maj} (its nearest gradient neighbour is {maj})"
                        n += 1
        fams = {o["family"] for o in g}
        if "gold-accent" in fams and fams & set(WARM_MAPPED):
            for o in g:
                if o["family"] in WARM_MAPPED:
                    o["family"], o["action"] = "gold-accent", "keep"
                    o["rule"] += " -> gold-accent (shares a gradient/style with kept gold stops)"
                    n += 1
    return n


def run():
    global MANIFEST_BYID
    occ, stats, byid = scan_all()
    MANIFEST_BYID = byid
    for o in occ:
        o.update(classify(o))
    stats["cohered"] = cohere(occ)
    rows = []
    for o in occ:
        fam = o["family"]
        new, clipped = "", False
        if fam in LADDERS:
            new, clipped = LADDERS[fam].map(o["hex"])
        elif fam in ("board-skin", "logo", "owned-svg"):
            wf, _ = window_family(o["hex"], o)               # reference mapping by hue family for the owner
            if wf in LADDERS and FAMILIES[wf]["action"] == "map":
                new, clipped = LADDERS[wf].map(o["hex"])
                o["ref_family"] = wf
        o["new"] = new
        o["clipped"] = clipped
        o["de00"] = round(de00(o["hex"], new), 2) if new else 0.0
        if o["action"] == "map" and new and o["de00"] < 1.0:
            o["action"] = "keep (sub-JND)"
        rows.append(o)
    return rows, stats




# ====================================================================================== outputs

AUTO_KINDS = ("swift-hex", "swift-hexstr", "json-hex", "py-hex")
CSV_COLS = ["id", "source", "kind", "file", "line", "col", "text", "hex", "alpha", "family", "action", "new", "de00", "clipped",
            "rule", "key", "name", "label", "case", "decl", "func", "const", "ckey", "ids", "ref_family", "shared_with_owner",
            "L", "C", "h", "newL", "newC", "newh", "okh", "line_text"]


def new_text(o):
    """The replacement text for an auto edit, in the literal's own format and letter case."""
    old, new = o["text"], o["new"]
    digits = re.search(r"[0-9A-Fa-f]{6}", old[1:] if old.startswith("#") else old[2:]).group(0)
    if digits.islower():
        new = new.lower()
    return old.replace(digits, new, 1)


def file_sha(path):
    return hashlib.sha256(open(os.path.join(ROOT, path), "rb").read()).hexdigest()[:16]


def test_pins(rows):
    mapped = {}
    for r in rows:
        if r["action"] == "map":
            mapped.setdefault(r["hex"], set()).add(r["new"])
    pins = []
    for base in ("Tests", "UITests"):
        for dp, dn, fn in os.walk(os.path.join(ROOT, base)):
            for f in sorted(fn):
                if not f.endswith(".swift"):
                    continue
                path = os.path.join(dp, f)
                for i, line in enumerate(open(path, encoding="utf-8"), 1):
                    for m in list(HEX6.finditer(line)) + list(re.finditer(r'#([0-9A-Fa-f]{6})\b', line)):
                        hx = m.group(1).upper()
                        if hx in mapped:
                            pins.append(dict(file=rel(path), line=i, hex=hx, new=sorted(mapped[hx]), text=line.strip()[:200]))
    return pins


def family_table():
    fams = {}
    for k, f in FAMILIES.items():
        lad = LADDERS[k]
        an = []
        for r in lad.rows:
            m, _ = lad.map(r["src"])
            an.append(dict(src="#" + r["src"], d1="#" + r["dst"], role=r["role"], mapped="#" + m,
                           de00_src_mapped=round(de00(r["src"], m), 1), de00_mapped_d1=round(de00(m, r["dst"]), 1)))
        fams[k] = dict(action=f["action"], lmode=f["lmode"], kh=f["kh"], hue_clamp_cielab=f["hue_clamp"], what=f["what"],
                       d1=f["d1"], anchors=an)
    return fams


def summarise(rows, stats):
    from collections import Counter
    s = dict(total=len(rows),
             by_source=dict(Counter(r["source"] for r in rows)),
             by_kind=dict(Counter(r["kind"] for r in rows)),
             by_family=dict(Counter(r["family"] for r in rows).most_common()),
             by_action=dict(Counter(r["action"] for r in rows).most_common()),
             unclassified=sum(1 for r in rows if r["family"] == "UNCLASSIFIED"),
             swift_app_hex_tokens=sum(1 for r in rows if r["kind"] == "swift-hex" and r["file"].startswith("App/")),
             swift_app_files_with_hex=len({r["file"] for r in rows if r["kind"] == "swift-hex" and r["file"].startswith("App/")}),
             ui_json_hex=sum(1 for r in rows if r["file"].endswith("ui.json")),
             ui_json_distinct=len({r["hex"] for r in rows if r["file"].endswith("ui.json")}),
             svg_generator_hex=sum(1 for r in rows if r["source"] == "svg"),
             comment_hex_not_counted=stats["comment_hex"],
             non_colour_short_tokens=len(stats["non_colour_tokens"]),
             gradient_groups_kept_whole=stats.get("cohered", 0),
             gamut_clipped=sum(1 for r in rows if r.get("clipped") and r["action"] == "map"),
             unique_mapped_pairs=len({(r["hex"], r["new"]) for r in rows if r["action"] == "map"}),
             manual_edits=sum(1 for r in rows if r["action"] == "map" and r["kind"] not in AUTO_KINDS))
    de = [r["de00"] for r in rows if r["action"] == "map"]
    s["de00_mapped"] = dict(min=round(min(de), 2), median=round(float(np.median(de)), 2), max=round(max(de), 2)) if de else {}
    per = {}
    for f in FAMILIES:
        d = [r["de00"] for r in rows if r["family"] == f and r["action"] == "map"]
        if d:
            per[f] = dict(n=len(d), median=round(float(np.median(d)), 1), p10=round(float(np.percentile(d, 10)), 1))
    s["de00_by_family"] = per
    # post-apply literal check: every mapped chrome literal leaves the old blue window
    lo, hi, cmin = OLD_BLUE_WINDOW
    left = []
    for r in rows:
        if r["action"] == "map" and r["family"] == "chrome-blue":
            Lo, Co, ho = oklch_of(r["new"])
            if lo <= ho < hi and Co >= cmin:
                left.append(r["id"])
    s["mapped_chrome_left_in_old_blue_window"] = len(left)
    s["swift_default_vs_ui_json"] = key_consistency(rows)
    # literals that are NOT mapped and still sit in today's blue window, by family: after A5 these are the only blue
    # literals left, and each family must be one the art direction keeps (ice, silver medals, fx, board) or one another
    # package redraws (R7 board skins / engine colours, R6 logo, R2 avatars)
    res = {}
    for r in rows:
        if r["action"] == "map":
            continue
        Lo, Co, ho = oklch_of(r["hex"])
        if lo <= ho < hi and Co >= cmin:
            res[r["family"]] = res.get(r["family"], 0) + 1
    s["unmapped_in_old_blue_window_by_family"] = res
    s["unmapped_in_old_blue_window_outside_allowed"] = sum(v for k, v in res.items() if k not in ALLOWED_AFTER)
    return s


def _json_token_key(k):
    k = re.sub(r"(\[\d+\])+$", "", k)
    if k.startswith("text."):
        return k[5:].rsplit(".", 1)[0]
    return re.sub(r"^(colors|gradients)\.", "", k)


def key_consistency(rows):
    """A Swift compiled default (t.color("k", 0x…) / t.text("k", …)) and the ui.json value of the same key with the same
    colour today must map to the same colour (the tuning-vs-defaults tests compare them)."""
    by = {}
    for r in rows:
        if r["file"].endswith("ui.json"):
            by.setdefault((_json_token_key(r["ctx"]["key"]), r["hex"]), []).append(r)
    paired, bad = 0, []
    for r in rows:
        k = r["ctx"].get("key") if r["source"] == "swift" else None
        if k and (k, r["hex"]) in by:
            paired += 1
            for j in by[(k, r["hex"])]:
                if (j["new"] if j["action"] == "map" else j["hex"]) != (r["new"] if r["action"] == "map" else r["hex"]):
                    bad.append(dict(key=k, hex=r["hex"], swift=r["id"], json=j["id"], swift_family=r["family"],
                                    json_family=j["family"]))
    return dict(paired=paired, mismatched=len(bad), examples=bad[:10])


def write_outputs(rows, stats):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "palette_map.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_COLS)
        for r in rows:
            c = r["ctx"]
            L, C, h = lch_of(r["hex"])
            nL = nC = nh = ""
            if r["new"]:
                nL, nC, nh = (round(v, 1) for v in lch_of(r["new"]))
            w.writerow([r["id"], r["source"], r["kind"], r["file"], r["line"], r["col"], r["text"], "#" + r["hex"],
                        "" if r["alpha"] is None else round(r["alpha"], 3), r["family"], r["action"],
                        ("#" + r["new"]) if r["new"] else "", r["de00"], int(bool(r.get("clipped"))), r["rule"],
                        c.get("key", ""), c.get("name", ""), c.get("label", ""), c.get("case", ""), c.get("decl", ""),
                        c.get("func", ""), c.get("const", ""), c.get("ckey", ""), ",".join(c.get("ids") or []),
                        r.get("ref_family", ""), ",".join(r.get("_svg_shared_with") or []),
                        round(L, 1), round(C, 1), round(h, 1), nL, nC, nh, round(oklch_of(r["hex"])[2], 1), r["line_text"]])
    files = sorted({r["file"] for r in rows})
    edits = []
    for r in rows:
        if r["action"] != "map":
            continue
        e = dict(file=r["file"], line=r["line"], col=r["col"], off=r["off"], end=r["end"], text=r["text"], old="#" + r["hex"],
                 new="#" + r["new"], family=r["family"], kind=r["kind"])
        if r["kind"] in AUTO_KINDS:
            e["apply"] = "auto"
            e["new_text"] = new_text(r)
        else:
            e["apply"] = "manual"
            e["note"] = dict(**{"swift-split": "channel triple 0xRR/255 …: write the new channels",
                                "swift-dec": "decimal (UI)Color(red:green:blue:): write the new channels",
                                "swift-system": "system colour: replace with Color(hex: 0x…)",
                                "colorset": "asset-catalog components"}).get(r["kind"], "")
        if r.get("_svg_shared_with"):
            e["shared_with_owner"] = r["_svg_shared_with"]
        edits.append(e)
    owner_ref = [dict(file=r["file"], line=r["line"], col=r["col"], text=r["text"], old="#" + r["hex"],
                      new=("#" + r["new"]) if r["new"] else "", family=r["family"], ref_family=r.get("ref_family", ""),
                      owner=r["action"].split(":", 1)[1]) for r in rows if r["action"].startswith("owner:")]
    by_hex = {}
    for r in rows:
        if r["action"] == "map":
            by_hex.setdefault(r["family"], {})["#" + r["hex"]] = "#" + r["new"]
    summary = summarise(rows, stats)
    doc = dict(
        about="R9 PALETTE-MAP (PLAN-P §4.2): every colour literal of the app's look, classified into a family and mapped onto "
              "the D1 'Burrow Works' ladder keeping L* and relative chroma (art-direction.md §7.3). A5 CODEMOD applies the "
              "'edits' (exclusive window), re-runs art_batch --svg for the generator constants, then captures + copygate. "
              "Regenerate with `tools/palette_map.py build` right before applying: offsets are exact for the tree whose file "
              "shas are in 'tree'; `apply --to DIR` refuses a drifted file.",
        rule="L*: kept (lmode keep) or carried along the D1 token ladder (lmode ladder: plank, exit-accent); C*: the colour's "
             "own chroma x the family's D1/today chroma ratio at that L*; hue: the D1 ladder hue at that L* + kh x the "
             "colour's hue offset; chroma reduced into sRGB if needed. Moves < ΔE00 1.0 are 'keep (sub-JND)'.",
        tool="tools/palette_map.py", tree={f: file_sha(f) for f in files},
        families=family_table(), excluded=EXCLUDED, windows_oklab_hue=WINDOWS, explicit=[dict(file=a, hex=b, ctx=c, family=d,
                                                                                          why=e) for a, b, c, d, e in EXPLICIT],
        post_apply_check=dict(old_blue_window_oklab=OLD_BLUE_WINDOW, allowed_families=ALLOWED_AFTER,
                              note="after A5, a literal (or a captured pixel) in the old blue window must belong to an "
                                   "allowed family (ice, silver medal, fx, board, owner art, …)"),
        summary=summary, edits=edits, owner_reference=owner_ref, by_hex=by_hex, test_pins=test_pins(rows))
    json.dump(doc, open(os.path.join(OUT_DIR, "palette_map.json"), "w"), indent=1)
    json.dump(summary, open(os.path.join(OUT_DIR, "summary.json"), "w"), indent=1)
    return summary, doc


# ====================================================================================== swatch sheets

FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_B = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def _font(sz, bold=False):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(FONT_B if bold else FONT, sz)
    except OSError:
        return ImageFont.load_default()


def _rgb(hx):
    return tuple(int(v) for v in hex_rgb(hx))


def _text_on(hx):
    return (0, 0, 0) if lch_of(hx)[0] > 60 else (255, 255, 255)


def family_uniques(rows, fam):
    u = {}
    for r in rows:
        if r["family"] == fam:
            k = (r["hex"], r["new"] if r["action"] in ("map",) or r["action"].startswith("owner:") else "")
            u.setdefault(k, []).append(r)
    return sorted(u.items(), key=lambda kv: (-lch_of(kv[0][0])[0]))


def sheet_family(rows, fam, width=1500, sw=58, label=True):
    """One page: title, the anchor strip (today | D1 token | our mapped anchor) and every unique colour of the family as a
    today-over-mapped swatch pair, sorted by L*."""
    from PIL import Image, ImageDraw
    items = family_uniques(rows, fam)
    mapped = fam in FAMILIES
    per_row = max(1, (width - 40) // (sw + 6))
    pair_h = sw * 2 if mapped else sw
    lab_h = 26 if label else 0
    n_rows = (len(items) + per_row - 1) // per_row
    anchors = LADDERS[fam].rows if mapped else []
    desc = (FAMILIES[fam]["what"] + "  ->  " + FAMILIES[fam]["d1"]) if mapped else EXCLUDED.get(fam, "")
    lines, line = [], ""
    for w_ in desc.split():
        if len(line) + len(w_) > 150:
            lines.append(line)
            line = ""
        line += w_ + " "
    lines.append(line)
    top = 56 + 22 * len(lines) + 10
    head_h = top + (150 if anchors else 0)
    H = head_h + n_rows * (pair_h + lab_h + 10) + 20
    im = Image.new("RGB", (width, H), (246, 244, 240))
    d = ImageDraw.Draw(im)
    n = sum(len(v) for _, v in items)
    act = FAMILIES[fam]["action"] if mapped else OWNER_OF_EXCLUDED.get(fam, "keep")
    d.text((20, 14), f"{fam}  —  {n} literals, {len(items)} unique  —  action: {act}", fill=(20, 20, 20), font=_font(30, True))
    for k_, ln_ in enumerate(lines):
        d.text((20, 56 + 22 * k_), ln_, fill=(60, 60, 60), font=_font(17))
    y = top
    if anchors:
        d.text((20, y), "anchors: today | D1 token | mapped (L* kept)" if FAMILIES[fam]["lmode"] == "keep" else
               "anchors: today | D1 token | mapped (ladder: exact)", fill=(20, 20, 20), font=_font(18, True))
        x = 20
        for a in anchors:
            m, _ = LADDERS[fam].map(a["src"])
            for j, hx in enumerate((a["src"], a["dst"], m)):
                d.rectangle([x + j * 44, y + 28, x + j * 44 + 42, y + 98], fill=_rgb(hx))
            d.text((x, y + 102), a["role"][:22], fill=(40, 40, 40), font=_font(12))
            d.text((x, y + 118), f"#{a['src']}>#{m}", fill=(40, 40, 40), font=_font(12))
            x += 3 * 44 + 22
            if x > width - 150:
                break
        y = head_h
    for i, ((hx, new), rs) in enumerate(items):
        cx = 20 + (i % per_row) * (sw + 6)
        cy = y + (i // per_row) * (pair_h + lab_h + 10)
        d.rectangle([cx, cy, cx + sw - 1, cy + sw - 1], fill=_rgb(hx))
        if mapped or new:
            d.rectangle([cx, cy + sw, cx + sw - 1, cy + 2 * sw - 1], fill=_rgb(new) if new else (246, 244, 240))
            if not new:
                d.line([cx, cy + sw, cx + sw, cy + 2 * sw], fill=(150, 150, 150))
        if label:
            d.text((cx, cy + pair_h + 1), hx, fill=(30, 30, 30), font=_font(11))
            d.text((cx, cy + pair_h + 13), (new or "keep") + f" x{len(rs)}", fill=(90, 90, 90), font=_font(10))
    return im


def gradient_strips(rows, limit=48):
    """Gradients (>= 3 mapped stops in one group) drawn as continuous strips, today above mapped: the structure check."""
    from PIL import Image, ImageDraw
    groups = {}
    for r in rows:
        if r["action"] in ("map", "keep (sub-JND)") and r["family"] in FAMILIES:
            groups.setdefault(group_key(r), []).append(r)
    gs = [(k, v) for k, v in groups.items() if len(v) >= 3]
    # the most-used chrome first: popup / HUD / home / page files, then the rest
    prio = ("PopupChrome", "ui.json", "GlossyChrome", "HUDView", "PageChrome", "PlayButton", "LevelPlate", "NavBar", "ShopView")
    gs.sort(key=lambda kv: (min((i for i, p in enumerate(prio) if p in kv[0][0]), default=99), str(kv[0])))
    gs = gs[:limit]
    W, bar_w, bar_h = 1500, 520, 30
    H = 60 + len(gs) * (2 * bar_h + 26)
    im = Image.new("RGB", (W, H), (246, 244, 240))
    d = ImageDraw.Draw(im)
    d.text((20, 14), "gradients: today (top) / mapped (bottom) — stops in file order; structure (value steps, rim/face/edge "
                     "contrast) must survive", fill=(20, 20, 20), font=_font(20, True))
    y = 60
    for k, v in gs:
        v = sorted(v, key=lambda r: r["off"])
        olds = [hex_rgb(r["hex"]) for r in v]
        news = [hex_rgb(r["new"] if r["new"] else r["hex"]) for r in v]
        for row, cols in ((0, olds), (1, news)):
            for x in range(bar_w):
                t_ = x / (bar_w - 1) * (len(cols) - 1)
                i0 = int(math.floor(t_))
                i1 = min(i0 + 1, len(cols) - 1)
                f = t_ - i0
                c = cols[i0] * (1 - f) + cols[i1] * f
                d.line([20 + x, y + row * bar_h, 20 + x, y + (row + 1) * bar_h - 1], fill=tuple(int(q) for q in c))
            # flat stop chips next to the strip
            for j, c in enumerate(cols):
                d.rectangle([560 + j * 30, y + row * bar_h, 560 + j * 30 + 28, y + (row + 1) * bar_h - 1],
                            fill=tuple(int(q) for q in c))
        label = f"{k[0].split('/')[-1]}:{k[1]}  [{v[0]['family']}]  " + " ".join("#" + r["hex"] for r in v[:6])
        d.text((20, y + 2 * bar_h + 4), label[:170], fill=(50, 50, 50), font=_font(13))
        y += 2 * bar_h + 26
    return im


def write_sheets(rows):
    from PIL import Image
    pages = []
    os.makedirs(os.path.join(OUT_DIR, "swatches"), exist_ok=True)
    order = list(FAMILIES) + [f for f in EXCLUDED]
    for fam in order:
        if not any(r["family"] == fam for r in rows):
            continue
        im = sheet_family(rows, fam)
        im.save(os.path.join(OUT_DIR, "swatches", f"{fam}.png"))
        pages.append(im)
    # the one overview sheet: every family, small swatches without labels
    small = [sheet_family(rows, f, width=1500, sw=26, label=False) for f in order if any(r["family"] == f for r in rows)]
    H = sum(p.height for p in small) + 10 * len(small)
    ov = Image.new("RGB", (1500, H), (255, 255, 255))
    y = 0
    for p in small:
        ov.paste(p, (0, y))
        y += p.height + 10
    ov.save(os.path.join(OUT_DIR, "swatches.png"))
    gradient_strips(rows).save(os.path.join(OUT_DIR, "gradients.png"))
    return [os.path.join(OUT_DIR, "swatches.png"), os.path.join(OUT_DIR, "gradients.png")]


# ====================================================================================== pixel preview (our captures only)

def _lab_to_rgb_vec(L, a, b):
    fy = (L + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200

    def finv(t):
        return np.where(t ** 3 > 0.008856, t ** 3, (t - 16 / 116) / 7.787)
    xyz = np.stack([finv(fx) * 0.95047, finv(fy), finv(fz) * 1.08883], -1)
    return xyz @ _M_XYZ2RGB.T                                     # linear, unclipped


def ladder_map_vec(lad, L, C, h):
    """Vectorised Ladder.map over pixel arrays (same maths; gamut by chroma bisection)."""
    dh0 = np.interp(L, lad.xs, lad.dh)
    sh0 = np.interp(L, lad.xs, lad.sh)
    rel = np.where(C > 1.0, (h - sh0 % 360 + 180.0) % 360.0 - 180.0, 0.0)
    hh = dh0 + lad.fam["kh"] * rel
    lo, hi = lad.clamp
    lo_u = dh0 + ((lo % 360) - dh0 % 360 + 180.0) % 360.0 - 180.0
    hh = np.clip(hh, lo_u, lo_u + (hi - lo))
    C2 = C * np.interp(L, lad.xs, lad.cr)
    if lad.fam["lmode"] == "keep":
        L2 = L
    else:
        xs, ys = lad.xs, lad.dL
        L2 = np.interp(L, xs, ys)
        L2 = np.where(L < xs[0], ys[0] + (L - xs[0]), np.where(L > xs[-1], ys[-1] + (L - xs[-1]), L2))
    L2 = np.clip(L2, 0, 100)
    hr = np.radians(hh % 360)
    lo_c, hi_c = np.zeros_like(C2), C2.copy()
    rgb = _lab_to_rgb_vec(L2, C2 * np.cos(hr), C2 * np.sin(hr))
    bad = np.any((rgb < -1e-4) | (rgb > 1 + 1e-4), -1)
    if bad.any():
        for _ in range(18):
            mid = (lo_c + hi_c) / 2
            r_ = _lab_to_rgb_vec(L2, mid * np.cos(hr), mid * np.sin(hr))
            ok = np.all((r_ >= -1e-4) & (r_ <= 1 + 1e-4), -1)
            lo_c = np.where(ok, mid, lo_c)
            hi_c = np.where(ok, hi_c, mid)
        C3 = np.where(bad, lo_c, C2)
        rgb = _lab_to_rgb_vec(L2, C3 * np.cos(hr), C3 * np.sin(hr))
    return lin_to_srgb255(rgb)


def recolor_pixels(img, rects=None):
    """The map applied to a capture's pixels by the same windows (context-free except the plank rects): a PREVIEW of what
    the literal codemod does to that screen, used only to read copygate numbers before A5. Never an asset."""
    a = np.asarray(img.convert("RGB")).astype(np.float64)
    lab = CG.rgb2lab(a)
    L, C, h = lab[..., 0], np.hypot(lab[..., 1], lab[..., 2]), np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    Lo, Co, ho = oklch_rgb(a)
    out = a.copy()
    fam = np.full(L.shape, "", dtype=object)
    chroma = C >= 4.0

    def win(x0, x1):
        return chroma & (((ho >= x0) & (ho < x1)) | ((ho + 360 >= x0) & (ho + 360 < x1)))
    warm = win(38, 112)
    fam[win(180, 280)] = "chrome-blue"
    fam[win(280, 365)] = "berry"
    red = win(5, 38)
    fam[red & (Co >= 0.05)] = "danger-red"
    fam[red & (Co < 0.05) & (Lo >= 0.62)] = "cream"
    fam[red & (Co < 0.05) & (Lo < 0.62)] = "ink-brown"
    fam[warm & (Lo >= 0.62) & (Co < 0.105)] = "cream"
    fam[warm & (Lo < 0.52) & (Co < 0.13)] = "ink-brown"
    fam[warm & (Lo >= 0.52) & (Lo < 0.62) & (Co < 0.105)] = "cream"
    fam[win(118, 172)] = "go-green"
    if rects:
        s = a.shape[1] / 393.0
        yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
        for x, y, w, hh_ in rects:
            m = (xx >= x * s) & (xx < (x + w) * s) & (yy >= y * s) & (yy < (y + hh_) * s) & warm & ~((Lo > 0.9) & (Co < 0.08))
            fam[m] = "plank"
    for f in ("chrome-blue", "berry", "danger-red", "cream", "ink-brown", "go-green", "plank"):
        m = fam == f
        if m.any():
            out[m] = ladder_map_vec(LADDERS[f], L[m], C[m], h[m])
    from PIL import Image
    return Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8), "RGB")


PLANK_RECTS = {"win-normal": [(50, 155, 290, 90)], "win-hard": [(50, 155, 290, 90)], "win-super": [(50, 155, 290, 90)],
               "pause": [(55, 185, 285, 100)], "quitLevel": [(55, 185, 285, 100)], "settings": [(100, 50, 193, 55)],
               "boosterBuy": [(55, 150, 285, 100)], "noLives": [(55, 150, 285, 100)]}


def cmd_preview(args):
    import fnmatch
    from PIL import Image
    cfg = CG.load_config()
    mj = json.load(open(os.path.join(ROOT, "tools", "capture", "manifest.json")))
    man = {m["id"]: m for m in (mj["captures"] if isinstance(mj, dict) else mj)}
    reg = {s["id"]: s["regions"] for s in json.load(open(os.path.join(ROOT, "tools", "compare", "regions.json")))["shots"]}
    cap = os.path.join(ROOT, "build", "compare", "captures")
    out = os.path.join(EVID, "preview")
    os.makedirs(out, exist_ok=True)
    res = []
    ids = args.ids.split(",") if args.ids else sorted(man)
    for sid in ids:
        m = man.get(sid)
        path = os.path.join(cap, f"{sid}-en.png")
        if not m or not m.get("ref") or not os.path.exists(path) or not os.path.exists(os.path.join(ROOT, m["ref"])):
            continue
        kind = next((k for pat, k in cfg["sweep_kinds"].items() if fnmatch.fnmatch(sid, pat)), "screen")
        im = Image.open(path).convert("RGB")
        im = im.resize((393, round(im.height * 393 / im.width)), Image.LANCZOS)
        today_p = os.path.join(out, f"{sid}-today.png")
        im.save(today_p)
        mp = recolor_pixels(im, PLANK_RECTS.get(sid))
        mapped_p = os.path.join(out, f"{sid}-mapped.png")
        mp.save(mapped_p)
        cmin = CG.kind_cmin(cfg, kind)
        row = dict(id=sid, kind=kind, ref=m["ref"])
        for tag, p in (("today", today_p), ("mapped", mapped_p)):
            mm = CG.measure(p, m["ref"], cmin=cmin)
            if sid in reg:
                mm["chrome"] = CG.chrome_delta(p, m["ref"], reg[sid])
            mm["judge"] = CG.judge(mm, kind, cfg)
            row[tag] = mm
        if sid in reg and row["mapped"].get("chrome"):
            # the same chrome ΔE00, only over the ui regions whose TODAY colour is in a family the codemod moves (the red
            # close X, coins, cream cards and neutral rails are kept/generic by the art direction and pin the median)
            ui = [r_ for r_ in reg[sid] if r_.get("kind") == "ui"]
            labs = CG.region_lab(today_p, [r_["r"] for r_ in ui])
            moved = []
            for r_, lab_ in zip(ui, labs):
                if np.any(np.isnan(lab_)):
                    continue
                rgb = lin_to_srgb255(lab_to_linrgb(*lab_))
                wf, _ = window_family(rgb_hex(rgb))
                if wf in ("chrome-blue", "go-green", "berry", "plank"):
                    moved.append((r_["name"], wf, row["mapped"]["chrome"]["per_region"][r_["name"]]))
            row["chrome_moved"] = dict(n=len(moved), median=float(np.median([m_[2] for m_ in moved])) if moved else None,
                                       regions={a_: [b_, c_] for a_, b_, c_ in moved})
        res.append(row)
        ch = row["mapped"].get("chrome") or {}
        print(f"{sid:18s} {kind:6s} overlap {row['today']['overlap']:.3f} -> {row['mapped']['overlap']:.3f}   chrome ΔE00 "
              f"{(row['today'].get('chrome') or {}).get('median', float('nan')):5.1f} -> {ch.get('median', float('nan')):5.1f}   "
              f"{'PASS' if row['mapped']['judge']['pass'] else 'fail'}"
              + (f"   moved-family chrome ΔE00 {row['chrome_moved']['median']:.1f} (n {row['chrome_moved']['n']})"
                 if row.get("chrome_moved", {}).get("median") is not None else ""))
    json.dump(res, open(os.path.join(out, "preview.json"), "w"), indent=1, default=float)
    # a look sheet: today | mapped | theirs for the key screens
    keys = [s for s in ("pause", "hud-L32", "settings", "shop", "win-normal", "home-L32", "profile", "lb-weekly", "claw",
                        "streakRace", "outOfTime", "unlock-box") if any(r["id"] == s for r in res)]
    tiles = []
    for sid in keys:
        a = Image.open(os.path.join(out, f"{sid}-today.png"))
        b = Image.open(os.path.join(out, f"{sid}-mapped.png"))
        th = Image.open(os.path.join(ROOT, man[sid]["ref"])).convert("RGB")
        th = th.resize((393, round(th.height * 393 / th.width)), Image.LANCZOS)
        hgt = min(a.height, b.height, th.height)
        t_ = Image.new("RGB", (393 * 3 + 20, hgt), (255, 255, 255))
        for i, x in enumerate((a, b, th)):
            t_.paste(x.crop((0, 0, 393, hgt)), (i * 403, 0))
        tiles.append((sid, t_))
    for i in range(0, len(tiles), 2):
        grp = tiles[i:i + 2]
        W = sum(t.width for _, t in grp) + 40 * (len(grp) - 1)
        H = max(t.height for _, t in grp) + 40
        sheet = Image.new("RGB", (W, H), (240, 240, 240))
        from PIL import ImageDraw
        d = ImageDraw.Draw(sheet)
        x = 0
        for sid, t in grp:
            d.text((x + 4, 6), f"{sid}: ours today | ours with the R9 map (pixel preview) | the original (looked at)",
                   fill=(0, 0, 0), font=_font(16, True))
            sheet.paste(t, (x, 36))
            x += t.width + 40
        sheet.save(os.path.join(out, f"look-{i // 2 + 1}.png"))
    return res


# ====================================================================================== apply (to a COPY), selftest, check

def cmd_apply(args):
    """Write mapped COPIES of every file with auto edits under --to DIR (A5's dry run; never the source tree). Refuses when a
    file drifted from the scanned tree, then re-scans the copies and asserts every mapped literal now holds its new value,
    the literal counts are unchanged, JSON/Python still parse, and no mapped chrome literal is left in the old blue window."""
    dest = os.path.abspath(args.to)
    for bad in (ROOT, os.path.join(ROOT, "App"), os.path.join(ROOT, "art"), os.path.join(ROOT, "Packages")):
        if dest == bad or dest.startswith(os.path.join(ROOT, "App") + os.sep) or dest.startswith(os.path.join(ROOT, "art") + os.sep):
            raise SystemExit(f"palette_map apply: refusing to write into the source tree ({dest})")
    rows, stats = run()
    unc = [r for r in rows if r["family"] == "UNCLASSIFIED"]
    if unc:
        raise SystemExit(f"palette_map apply: {len(unc)} unclassified literals — run build first")
    by_file = {}
    for r in rows:
        if r["action"] == "map" and r["kind"] in AUTO_KINDS:
            by_file.setdefault(r["file"], []).append(r)
    n = 0
    written = []
    for f, rs in sorted(by_file.items()):
        text = open(os.path.join(ROOT, f), encoding="utf-8").read()
        for r in sorted(rs, key=lambda r: -r["off"]):
            if text[r["off"]:r["end"]] != r["text"]:
                raise SystemExit(f"palette_map apply: {f}:{r['line']} drifted ({text[r['off']:r['end']]!r} != {r['text']!r})")
            text = text[:r["off"]] + new_text(r) + text[r["end"]:]
            n += 1
        out = os.path.join(dest, f)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "w", encoding="utf-8").write(text)
        written.append(out)
    # verify the copies
    errs = []
    for f, rs in sorted(by_file.items()):
        p = os.path.join(dest, f)
        if f.endswith(".json"):
            try:
                json.load(open(p))
            except ValueError as e:
                errs.append(f"{f}: JSON {e}")
            o2 = scan_json(p)
        elif f.endswith(".py"):
            try:
                ast.parse(open(p).read())
            except SyntaxError as e:
                errs.append(f"{f}: Python {e}")
            _, mc = manifest_info()
            o2, _ = scan_py(p, mc)
        else:
            o2, _, _ = scan_swift(p)
        o1 = [r for r in rows if r["file"] == f and r["kind"] in AUTO_KINDS]
        o2 = [o for o in o2 if o["kind"] in AUTO_KINDS]
        if len(o1) != len(o2):
            errs.append(f"{f}: {len(o1)} literals before, {len(o2)} after")
            continue
        for a, b in zip(sorted(o1, key=lambda r: r["off"]), sorted(o2, key=lambda r: r["off"])):
            want = a["new"] if a["action"] == "map" else a["hex"]
            if b["hex"] != want:
                errs.append(f"{f}:{a['line']}: {b['hex']} != {want}")
    lo, hi, cmin = OLD_BLUE_WINDOW
    left = [r["id"] for r in rows if r["action"] == "map" and r["family"] == "chrome-blue"
            and lo <= oklch_of(r["new"])[2] < hi and oklch_of(r["new"])[1] >= cmin]
    rep = dict(dest=dest, files=len(written), edits_applied=n, manual_edits=sum(1 for r in rows if r["action"] == "map"
                                                                               and r["kind"] not in AUTO_KINDS),
               errors=errs, chrome_left_in_old_blue_window=len(left))
    json.dump(rep, open(os.path.join(dest, "apply-report.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1)[:1500])
    return 1 if errs or left else 0


def selftest():
    """The mapping maths on synthetic cases + mutation checks (each mutation must be CAUGHT by an invariant)."""
    fails, caught = [], []
    # 1. ladder anchors map exactly in ladder mode, keep L* in keep mode
    for k, lad in LADDERS.items():
        for r in lad.rows:
            m, clipped = lad.map(r["src"])
            Lm = lch_of(m)[0]
            if lad.fam["lmode"] == "ladder" and de00(m, r["dst"]) > 0.6:
                fails.append(f"{k}: ladder anchor {r['src']} -> {m} != {r['dst']}")
            if lad.fam["lmode"] == "keep" and abs(Lm - r["sL"]) > 0.8:
                fails.append(f"{k}: keep-L anchor {r['src']} L {r['sL']:.1f} -> {Lm:.1f}")
    # 2. every mapped output is inside sRGB, keeps L* (keep families) within 0.8 and lies in the family's D1 hue range
    rows, _ = run()
    for r in rows:
        if r["action"] != "map":
            continue
        L0 = lch_of(r["hex"])[0]
        L1, C1, h1 = lch_of(r["new"])
        if FAMILIES[r["family"]]["lmode"] == "keep" and abs(L1 - L0) > 0.8:
            fails.append(f"{r['id']}: L* {L0:.1f} -> {L1:.1f}")
        lo, hi = FAMILIES[r["family"]]["hue_clamp"]
        if C1 > 3.0 and not (lo - 3 <= h1 <= hi + 3 or lo - 3 <= h1 + 360 <= hi + 3):
            fails.append(f"{r['id']}: hue {h1:.1f} outside {lo}-{hi}")
    # 3. monotone value ladder: within each family, a darker source never maps lighter than a lighter source (by > 1 L*)
    for k in FAMILIES:
        pts = sorted({(lch_of(r["hex"])[0], lch_of(r["new"])[0]) for r in rows if r["family"] == k and r["new"]})
        for (a0, b0), (a1, b1) in zip(pts, pts[1:]):
            if b1 < b0 - 1.0:
                fails.append(f"{k}: L* order broken {a0:.1f}->{b0:.1f} vs {a1:.1f}->{b1:.1f}")
                break
    # 4. determinism: a second run gives the same map
    rows2, _ = run()
    if [(r["id"], r["family"], r["new"]) for r in rows] != [(r["id"], r["family"], r["new"]) for r in rows2]:
        fails.append("two runs differ")
    # 5. mutations (each must be CAUGHT)
    import copy
    base = {k: copy.deepcopy(v) for k, v in FAMILIES.items()}

    spec = {k: (v["lmode"], tuple(v["hue_clamp"]), [(s, d) for s, d, _ in v["anchors"]]) for k, v in base.items()}
    probes = {}
    for r in rows:
        if r["family"] in FAMILIES and r["action"] == "map":
            probes.setdefault(r["family"], set()).add(r["hex"])

    def violations(ladders):
        """Invariants from the ORIGINAL spec, evaluated on (possibly mutated) ladders over anchors + today's literals."""
        bad = []
        for k, lad in ladders.items():
            lmode, (lo, hi), anchors = spec[k]
            for s, d in anchors:
                m, _ = lad.map(s)
                if lmode == "ladder" and de00(m, d) > 0.6:
                    bad.append(f"{k}: anchor {s}")
            for s in sorted(probes.get(k, ()))[:60] + [s for s, _ in anchors]:
                m, _ = lad.map(s)
                L0, (L1, C1, h1) = lch_of(s)[0], lch_of(m)
                if lmode == "keep" and abs(L1 - L0) > 0.8:
                    bad.append(f"{k}: L* {s}")
                if C1 > 3.0 and not (lo - 3 <= h1 <= hi + 3 or lo - 3 <= h1 + 360 <= hi + 3):
                    bad.append(f"{k}: hue {s}")
        return bad

    golden = {(k, s): LADDERS[k].map(s)[0] for k in LADDERS for s in sorted(probes.get(k, ()))[:60]}

    def drifted(ladders):
        """Regression pin: today's literals map exactly as the reviewed map (swatch sheets) says."""
        return [f"{k}:{s}" for (k, s), m in golden.items() if de00(ladders[k].map(s)[0], m) > 1.0]

    def mutated(fn):
        try:
            fn()
            lads = {k: Ladder(k, v) for k, v in FAMILIES.items()}
            return bool(violations(lads) or drifted(lads))
        finally:
            FAMILIES.clear()
            FAMILIES.update({k: copy.deepcopy(v) for k, v in base.items()})

    if violations(LADDERS):
        fails.append("the unmutated ladders violate their own spec: " + ", ".join(violations(LADDERS)[:5]))
    muts = {
        "chrome lmode keep->ladder": lambda: FAMILIES["chrome-blue"].update(lmode="ladder"),
        "plank lmode ladder->keep": lambda: FAMILIES["plank"].update(lmode="keep"),
        "chrome hue clamp -> blue": lambda: FAMILIES["chrome-blue"].update(hue_clamp=(250.0, 300.0)),
        "green anchor swapped to blue": lambda: FAMILIES["go-green"]["anchors"].__setitem__(5, ("00E400", "0192FF", "x")),
        "berry clamp -> violet": lambda: FAMILIES["berry"].update(hue_clamp=(290.0, 320.0)),
    }
    for name, fn in muts.items():
        (caught if mutated(fn) else fails).append(f"mutation {name}")
    # 6. classification mutations: a blue ribbon / an unknown file must not be silently mapped as plank / pass
    o = dict(source="swift", kind="swift-hex", file="App/Shell/Popups/PopupChrome.swift", hex="0192FF", line_text="",
             ctx=dict(key="ribbon.face"), line=1, off=0)
    if classify(o)["family"] == "plank":
        fails.append("a blue literal in the ribbon context became plank")
    else:
        caught.append("blue-in-ribbon stays out of plank")
    o = dict(source="swift", kind="swift-hex", file="App/X.swift", hex="7F7FFF", line_text="", ctx={}, line=1, off=0)
    fam_ = classify(o)["family"]
    if fam_ not in ("chrome-blue", "berry", "UNCLASSIFIED"):
        fails.append(f"#7F7FFF classified {fam_}")
    else:
        caught.append(f"#7F7FFF -> {fam_} (a gap colour is never silently kept)")
    return fails, caught


def cmd_build(args):
    rows, stats = run()
    summary, doc = write_outputs(rows, stats)
    sheets = write_sheets(rows)
    print(json.dumps({k: summary[k] for k in ("total", "by_family", "by_action", "unclassified", "swift_app_hex_tokens",
                                              "swift_app_files_with_hex", "ui_json_hex", "ui_json_distinct",
                                              "svg_generator_hex", "mapped_chrome_left_in_old_blue_window")}, indent=1))
    print("wrote", rel(OUT_DIR), "(palette_map.csv, palette_map.json, summary.json, swatches.png, gradients.png, swatches/)")
    return 1 if summary["unclassified"] else 0


def cmd_check(args):
    rows, stats = run()
    unc = [r for r in rows if r["family"] == "UNCLASSIFIED"]
    fails, caught = selftest()
    doc = json.load(open(os.path.join(OUT_DIR, "palette_map.json")))
    drift = [f for f, s in doc["tree"].items() if os.path.exists(os.path.join(ROOT, f)) and file_sha(f) != s]
    print(f"literals {len(rows)}, unclassified {len(unc)}; selftest failures {len(fails)}, caught {len(caught)}; "
          f"files drifted since the last build: {len(drift)}")
    for x in fails[:20]:
        print("  FAIL", x)
    for x in drift[:20]:
        print("  drift", x)
    return 1 if unc or fails else 0


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    sub.add_parser("check")
    sub.add_parser("selftest")
    p = sub.add_parser("preview")
    p.add_argument("--ids", default="")
    p = sub.add_parser("apply")
    p.add_argument("--to", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "build":
        return cmd_build(a)
    if a.cmd == "check":
        return cmd_check(a)
    if a.cmd == "selftest":
        fails, caught = selftest()
        print(f"selftest: {len(fails)} failures, {len(caught)} mutations/probes caught")
        for x in fails:
            print("  FAIL", x)
        for x in caught:
            print("  CAUGHT", x)
        return 1 if fails else 0
    if a.cmd == "preview":
        cmd_preview(a)
        return 0
    if a.cmd == "apply":
        return cmd_apply(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
