"""Shared code of the skin colour tools (tools/skin/{build,codemod,recolor}.py). Stdlib only (runs on Linux CI).

  - paths                  the app folder, skin/colors.json, the generated Swift files, the scanned sources
  - swift_lex(text)        a Swift lexer good enough to tell code from comments and string literals (nested block comments,
                           escapes, "\\(…)" interpolation, multi-line and raw strings)
  - colour maths           sRGB <-> CIELAB (D65/2°), LCh, OKLab/OKLCh, gamut-clipped LCh -> sRGB
  - family(hex)            the hue family a colour belongs to (palette names are "<family>.<L*>")
  - colors.json            load / validate / save (stable formatting), token id -> Swift constant name
  - literal scanning       every colour literal in the scanned Swift sources (the codemod's input, build.py --check-literals)
  - ui.json                the string values of Tuning/ui.json with their JSON paths and text positions (colour slots are
                           "@<ui id>" references to colors.json `ui`), the ui id of a slot, the resolved ui colour table
"""
from __future__ import annotations

import json
import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, "..", ".."))                  # apps/mazeout
COLORS_JSON = os.path.join(APP, "skin", "colors.json")
GEN_SWIFT = os.path.join(APP, "App", "Shell", "Components", "SkinColors.generated.swift")
GEN_TEST_SWIFT = os.path.join(APP, "Tests", "AppTests", "SkinColorsTable.generated.swift")
ALLOWLIST = os.path.join(HERE, "literal_allowlist.json")
UI_JSON = os.path.join(APP, "App", "Resources", "Tuning", "ui.json")
UI_COLORS_GEN = os.path.join(APP, "App", "Resources", "Tuning", "ui-colors.json")     # generated: ui id -> "#RRGGBB"
FONTS_JSON = os.path.join(APP, "skin", "fonts.json")
NAMES_JSON = os.path.join(APP, "skin", "names.json")
GEN_DATA_SWIFT = os.path.join(APP, "App", "Shell", "Components", "SkinData.generated.swift")
FONTS_DIR = os.path.join(APP, "App", "Resources", "Fonts")
PROJECT_YML = os.path.join(APP, "project.yml")
INFO_PLIST = os.path.join(APP, "App", "Info.plist")

# The sources whose colour literals are skin tokens. App/Board reads board.json (its own data), App/Game, App/Audio and the
# PathCore package hold no UI colours; they are outside the skin scan on purpose. App/Puzzles (template phase 5: the boards
# of the modules after the reference one) draws only skin tokens.
SCAN_DIRS = ["App/Shell", "App/FX", "App/Puzzles"]
SCAN_FILES = ["art/ui/code/GlossyChrome.swift"]
GENERATED_REL = os.path.relpath(GEN_SWIFT, APP)
GENERATED_RELS = {GENERATED_REL, os.path.relpath(GEN_DATA_SWIFT, APP)}


def rel(p):
    return os.path.relpath(p, APP).replace(os.sep, "/")


def scanned_files():
    out = []
    for d in SCAN_DIRS:
        for dp, _, fs in os.walk(os.path.join(APP, d)):
            out += [os.path.join(dp, f) for f in fs if f.endswith(".swift")]
    out += [os.path.join(APP, f) for f in SCAN_FILES]
    return sorted(p for p in out if rel(p) not in GENERATED_RELS)


# ============================================================================================ Swift lexer

class Lexed:
    """`code`: the text with every comment and every string literal's CONTENT blanked (same length, newlines kept;
    interpolated code inside strings stays code). `strings`: (start, end, content, interpolated) of each string literal,
    start/end spanning the quotes (and any raw-string #s)."""

    def __init__(self, text, code, strings, comments):
        self.text, self.code, self.strings, self.comments = text, code, strings, comments

    def line_of(self, pos):
        return self.text.count("\n", 0, pos) + 1


def swift_lex(text):
    n = len(text)
    code = list(text)
    strings, comments = [], []

    def blank(a, b):
        for k in range(a, b):
            if code[k] != "\n":
                code[k] = " "

    def lex_code(i, stop_at_paren):
        depth = 0
        while i < n:
            c = text[i]
            if text.startswith("//", i):
                j = text.find("\n", i)
                j = n if j < 0 else j
                blank(i, j)
                comments.append((i, j))
                i = j
            elif text.startswith("/*", i):
                d, j = 1, i + 2
                while j < n and d:
                    if text.startswith("/*", j):
                        d, j = d + 1, j + 2
                    elif text.startswith("*/", j):
                        d, j = d - 1, j + 2
                    else:
                        j += 1
                blank(i, j)
                comments.append((i, j))
                i = j
            elif c == '"' or (c == "#" and re.match(r'#+"', text[i:i + 8])):
                i = lex_string(i)
            elif c == "(":
                depth += 1
                i += 1
            elif c == ")":
                if stop_at_paren and depth == 0:
                    return i
                depth -= 1
                i += 1
            else:
                i += 1
        return i

    def lex_string(i):
        start = i
        hashes = 0
        while text[i] == "#":
            hashes += 1
            i += 1
        multi = text.startswith('"""', i)
        q = '"""' if multi else '"'
        i += len(q)
        close = q + "#" * hashes
        esc = "\\" + "#" * hashes
        content_start = i
        interpolated = False
        pieces = []
        seg = i
        while i < n:
            if text.startswith(close, i):
                break
            if text.startswith(esc, i):
                k = i + len(esc)
                if k < n and text[k] == "(":
                    interpolated = True
                    blank(seg, i)
                    pieces.append(text[seg:i])
                    end = lex_code(k + 1, True)          # index of the closing ')'
                    pieces.append("\\(" + text[k + 1:end] + ")")
                    i = end + 1
                    seg = i
                    continue
                i = k + 1
                continue
            if not multi and text[i] == "\n":
                break                                    # unterminated: never swallow the rest of the file
            i += 1
        blank(seg, i)
        pieces.append(text[seg:i])
        end = min(n, i + len(close))
        strings.append((start, end, "".join(pieces) if interpolated else text[content_start:i], interpolated))
        return end

    lex_code(0, False)
    return Lexed(text, "".join(code), sorted(strings), comments)


# ============================================================================================ colour maths

def hex_rgb(h):
    h = h.lstrip("#").replace("0x", "").replace("0X", "")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_hex(rgb):
    return "#" + "".join(f"{int(round(min(max(v, 0), 255))):02X}" for v in rgb)


def norm_hex(h):
    """'0x00a2ff' / '#00A2FF' / '00a2ff' -> '#00A2FF'."""
    return rgb_hex(hex_rgb(h))


def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


_WX, _WY, _WZ = 0.95047, 1.0, 1.08883


def rgb_lab(rgb):
    r, g, b = (_lin(float(v)) for v in rgb)
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / _WX
    y = (0.2126729 * r + 0.7151522 * g + 0.0721750 * b) / _WY
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / _WZ

    def f(t):
        return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def lab_lin(L, a, b):
    fy = (L + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200

    def finv(t):
        return t ** 3 if t ** 3 > 216 / 24389 else (116 * t - 16) / (24389 / 27)
    x, y, z = finv(fx) * _WX, finv(fy) * _WY, finv(fz) * _WZ
    return (3.2404542 * x - 1.5371385 * y - 0.4985314 * z,
            -0.9692660 * x + 1.8760108 * y + 0.0415560 * z,
            0.0556434 * x - 0.2040259 * y + 1.0572252 * z)


def lch(h):
    L, a, b = rgb_lab(hex_rgb(h))
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def lch_hex(L, C, h):
    """LCh -> '#RRGGBB', keeping L* and hue and reducing chroma (bisection) until inside sRGB. -> (hex, clipped)."""
    L = min(max(L, 0.0), 100.0)

    def lin(Cx):
        return lab_lin(L, Cx * math.cos(math.radians(h)), Cx * math.sin(math.radians(h)))

    def inside(c):
        return all(-1e-4 <= v <= 1 + 1e-4 for v in c)
    c = lin(C)
    clipped = False
    if not inside(c):
        clipped = True
        lo, hi = 0.0, C
        for _ in range(40):
            mid = (lo + hi) / 2
            if inside(lin(mid)):
                lo = mid
            else:
                hi = mid
        c = lin(lo)
    return rgb_hex([_gam(min(max(v, 0.0), 1.0)) * 255 for v in c]), clipped


def oklch(h):
    r, g, b = (_lin(float(v)) for v in hex_rgb(h))
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360


def hue_diff(a, b):
    """signed b - a in (-180, 180]."""
    return (b - a + 180.0) % 360.0 - 180.0


# ============================================================================================ families

# OKLCh hue windows (OKLab's hue is near-uniform where CIELAB bends in the blues/violets). A colour is `neutral` below
# OK chroma 0.025, `cream` when light and faintly warm, `brown` / `maroon` when a dark warm/red; else its hue window.
FAMILY_WINDOWS = [("red", 15.0, 40.0), ("orange", 40.0, 75.0), ("yellow", 75.0, 112.0), ("lime", 112.0, 135.0),
                  ("green", 135.0, 160.0), ("teal", 160.0, 212.0), ("cyan", 212.0, 240.0), ("blue", 240.0, 262.0),
                  ("indigo", 262.0, 285.0), ("violet", 285.0, 315.0), ("magenta", 315.0, 345.0), ("pink", 345.0, 375.0)]
FAMILIES = ["neutral", "cream", "maroon", "brown"] + [w[0] for w in FAMILY_WINDOWS]
FAMILY_DOC = {
    "neutral": "white, black and greys (OK chroma < 0.025)",
    "cream": "light, faintly warm off-whites (OK L > 0.86, chroma < 0.07, hue 40-112)",
    "maroon": "dark reds (OK L < 0.5, hue 15-40)",
    "brown": "dark oranges/yellows: ink outlines, wood, shadows (OK L < 0.55, hue 40-112)",
}
for _n, _a, _b in FAMILY_WINDOWS:
    FAMILY_DOC.setdefault(_n, f"OKLCh hue {_a:g}-{_b % 360:g}")


def family(h):
    L, C, hh = oklch(h)
    if C < 0.025:
        return "neutral"
    if 40 <= hh < 112 and L > 0.86 and C < 0.07:
        return "cream"
    if 15 <= hh < 40 and L < 0.5:
        return "maroon"
    if 40 <= hh < 112 and L < 0.55:
        return "brown"
    for name, a, b in FAMILY_WINDOWS:
        if a <= hh < b or a <= hh + 360 < b:
            return name
    return "pink"


def palette_base_name(h):
    L = lch(h)[0]
    return f"{family(h)}.{int(round(L)):02d}"


def family_of_name(name):
    return name.split(".")[0]


# ============================================================================================ colors.json

HEX6 = re.compile(r"^#[0-9A-F]{6}$")
TOKEN_ID = re.compile(r"^[a-z][A-Za-z0-9]*(\.[A-Za-z0-9]+)*$")
PALETTE_NAME = re.compile(r"^[a-z]+\.[0-9]{2,3}[a-z]?$")


def load_colors(path=COLORS_JSON):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve(doc, token_id):
    v = doc["tokens"][token_id]
    return doc["palette"][v] if not v.startswith("#") else v


def validate(doc):
    """-> list of error strings (empty = valid)."""
    errs = []
    pal, toks = doc.get("palette"), doc.get("tokens")
    if not isinstance(pal, dict) or not isinstance(toks, dict):
        return ["colors.json needs 'palette' and 'tokens' objects"]
    for k, v in pal.items():
        if not PALETTE_NAME.match(k):
            errs.append(f"palette name {k!r}: expected '<family>.<L*>[a-z]' (e.g. teal.42, teal.42b)")
        if not isinstance(v, str) or not HEX6.match(v):
            errs.append(f"palette {k}: {v!r} is not '#RRGGBB' (upper case)")
    names = {}
    for t, v in toks.items():
        if not TOKEN_ID.match(t):
            errs.append(f"token id {t!r}: expected dotted lowerCamel parts (a.bC.d0)")
        if not isinstance(v, str):
            errs.append(f"token {t}: value must be a palette name or '#RRGGBB'")
        elif v.startswith("#"):
            if not HEX6.match(v):
                errs.append(f"token {t}: {v!r} is not '#RRGGBB' (upper case)")
        elif v not in pal:
            errs.append(f"token {t}: unknown palette entry {v!r}")
        s = swift_name(t)
        if s in names:
            errs.append(f"tokens {names[s]} and {t} give the same Swift name {s}")
        names[s] = t
    ui = doc.get("ui", {})
    if not isinstance(ui, dict):
        return errs + ["colors.json 'ui' must be an object {ui id: palette name | '#RRGGBB'}"]
    for u, v in ui.items():
        if not UI_ID.match(u):
            errs.append(f"ui id {u!r}: expected the dotted ui.json path (letters, digits, '_')")
        if not isinstance(v, str):
            errs.append(f"ui {u}: value must be a palette name or '#RRGGBB[AA]'")
        elif v.startswith("#"):
            if not (HEX6.match(v) or HEX8.match(v)):
                errs.append(f"ui {u}: {v!r} is not '#RRGGBB' or '#RRGGBBAA' (upper case)")
        elif v not in pal:
            errs.append(f"ui {u}: unknown palette entry {v!r}")
    return errs


def dump_colors(doc):
    """Stable, diff-friendly JSON: palette sorted by family order then name, tokens and ui sorted by id, one entry per line."""
    fam_rank = {f: i for i, f in enumerate(FAMILIES)}
    def pkey(kv):
        m = re.match(r"^([a-z]+)\.(\d+)([a-z]?)$", kv[0])
        if not m:
            return (99, 0, kv[0])
        return (fam_rank.get(m.group(1), 98), int(m.group(2)), m.group(3))
    pal = sorted(doc["palette"].items(), key=pkey)
    toks = sorted(doc["tokens"].items())
    out = ["{"]
    sections = [("palette", pal), ("tokens", toks)]
    if "ui" in doc:
        sections.append(("ui", sorted(doc["ui"].items())))
    for k in doc:
        if k in ("palette", "tokens", "ui"):
            continue
        out.append(f"  {json.dumps(k)}: {json.dumps(doc[k], ensure_ascii=False)},")
    for si, (name, items) in enumerate(sections):
        out.append(f"  {json.dumps(name)}: {{")
        out += [f"    {json.dumps(k)}: {json.dumps(v)}{',' if i < len(items) - 1 else ''}" for i, (k, v) in enumerate(items)]
        out.append("  }," if si < len(sections) - 1 else "  }")
    out.append("}")
    return "\n".join(out) + "\n"


def save_colors(doc, path=COLORS_JSON):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(dump_colors(doc))


def swift_name(token_id):
    """'shop.shopView.priceButton.face.0' -> 'shopShopViewPriceButtonFace0'; ids ending in '.hex' are String tokens."""
    parts = [p for p in token_id.split(".") if p]
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


def is_string_token(token_id):
    return token_id.endswith(".hex")


# ============================================================================================ literal scanning

HEX_INT = re.compile(r"(?<![0-9A-Za-z_])0x([0-9A-Fa-f]{6})(?![0-9A-Fa-f_])")
HEX_STR = re.compile(r"^#([0-9A-Fa-f]{6})([0-9A-Fa-f]{2})?$")
_NUM = r"(\d+(?:\.\d+)?)(?:\s*/\s*(255(?:\.0)?))?"
DEC_COLOR = re.compile(r"\b(?:UIColor|Color|CGColor|NSColor)\(\s*(?:\.sRGB\s*,\s*)?(?:s?rgbR|r)ed:\s*" + _NUM +
                       r"\s*,\s*green:\s*" + _NUM + r"\s*,\s*blue:\s*" + _NUM)
WHITE_COLOR = re.compile(r"\b(?:UIColor|Color|CGColor)\(\s*white:\s*\d")


def _dec(v, over):
    x = float(v)
    return x / 255.0 if over else x


def scan_literals(path, lexed=None):
    """Every colour literal in a Swift file -> list of dicts: kind (hex | hexstr | dec | white), start, end (the text to
    replace), hex ('#RRGGBB'), alpha (hexstr '#RRGGBBAA' only), line, text."""
    text = open(path, encoding="utf-8").read() if lexed is None else lexed.text
    lx = lexed or swift_lex(text)
    code = lx.code
    out = []
    for m in HEX_INT.finditer(code):
        out.append(dict(kind="hex", start=m.start(), end=m.end(), hex=norm_hex(m.group(1)), text=m.group(0)))
    for (s, e, content, interp) in lx.strings:
        m = HEX_STR.match(content) if not interp else None
        if m:
            out.append(dict(kind="hexstr", start=s, end=e, hex=norm_hex(m.group(1)), alpha=m.group(2), text=text[s:e]))
    for m in DEC_COLOR.finditer(code):
        chans = [_dec(m.group(i), m.group(i + 1)) for i in (1, 3, 5)]
        out.append(dict(kind="dec", start=m.start(), end=m.end(), hex=rgb_hex([c * 255 for c in chans]), chans=chans,
                        text=text[m.start():m.end()]))
    for m in WHITE_COLOR.finditer(code):
        out.append(dict(kind="white", start=m.start(), end=m.end(), hex=None, text=text[m.start():m.end()]))
    for o in out:
        o["line"] = lx.line_of(o["start"])
    return sorted(out, key=lambda o: o["start"])


def load_allowlist():
    with open(ALLOWLIST, encoding="utf-8") as f:
        return json.load(f)["allow"]


def allowed(allow, relpath, lit):
    for a in allow:
        if a["file"] == relpath and a["literal"] == lit["text"].strip():
            return a
    return None


def uiart_names():
    """UIArt case names (the app's art ids): tests scan the sources for `.name` references to them, so no Swift constant
    may be spelled like one."""
    p = os.path.join(APP, "App", "Shell", "Components", "UIArt.swift")
    if not os.path.exists(p):
        return set()
    return set(re.findall(r"\bcase\s+([a-z][A-Za-z0-9]*)\b", open(p, encoding="utf-8").read()))


# ============================================================================================ ui.json colour slots

UI_ID = re.compile(r"^[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)*$")
UI_REF = re.compile(r"^@([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*)$")
HEX8 = re.compile(r"^#[0-9A-F]{8}$")
# a colour literal anywhere inside a ui.json string ("#RRGGBB" / "#RRGGBBAA", any case; also inside ';' lists)
UI_RAW_HEX = re.compile(r"(?<![0-9A-Za-z_])#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?(?![0-9A-Za-z_])")
UI_HEX_VALUE = re.compile(r"^#([0-9A-Fa-f]{6})([0-9A-Fa-f]{2})?$")


def json_string_values(text):
    """Every string VALUE of a JSON text (object keys excluded) -> [(start, end, path)], start/end spanning the quotes,
    path a tuple of keys / list indexes. The text is only read, so a rewrite can keep its hand formatting."""
    n = len(text)
    out = []
    num = re.compile(r"-?[0-9][0-9.eE+-]*|true|false|null")

    def ws(i):
        while i < n and text[i] in " \t\r\n":
            i += 1
        return i

    def string_end(i):
        j = i + 1
        while text[j] != '"':
            j += 2 if text[j] == "\\" else 1
        return j + 1

    def value(i, path):
        i = ws(i)
        c = text[i]
        if c == "{":
            i = ws(i + 1)
            if text[i] == "}":
                return i + 1
            while True:
                i = ws(i)
                ke = string_end(i)
                key = json.loads(text[i:ke])
                i = ws(ke)
                if text[i] != ":":
                    raise ValueError(f"JSON: ':' expected at {i}")
                i = ws(value(i + 1, path + (key,)))
                if text[i] == ",":
                    i += 1
                    continue
                if text[i] != "}":
                    raise ValueError(f"JSON: '}}' expected at {i}")
                return i + 1
        if c == "[":
            i = ws(i + 1)
            if text[i] == "]":
                return i + 1
            k = 0
            while True:
                i = ws(value(i, path + (k,)))
                k += 1
                if text[i] == ",":
                    i += 1
                    continue
                if text[i] != "]":
                    raise ValueError(f"JSON: ']' expected at {i}")
                return i + 1
        if c == '"':
            e = string_end(i)
            out.append((i, e, path))
            return e
        m = num.match(text, i)
        if not m:
            raise ValueError(f"JSON: unexpected {c!r} at {i}")
        return m.end()

    value(0, ())
    return out


def json_get(doc, path):
    for p in path:
        doc = doc[p]
    return doc


def ui_id(doc, path):
    """The ui id of the colour slot at `path` of ui.json: the dotted path; a gradient stop [position, colour] is named by
    the stop (gradients.popup.ribbon.2), not by its colour's index inside the pair."""
    parent = json_get(doc, path[:-1]) if path else None
    if (isinstance(parent, list) and len(parent) == 2 and path[-1] == 1 and isinstance(parent[0], (int, float))
            and not isinstance(parent[0], bool)):
        path = path[:-1]
    return ".".join(str(p) for p in path)


def ui_slots(text):
    """ui.json text -> (refs, raws): refs = [(start, end, path, ui id referenced)], raws = [(start, end, path, value)] for
    every string holding a colour literal."""
    doc = json.loads(text)
    refs, raws = [], []
    for s, e, path in json_string_values(text):
        v = json_get(doc, path)
        m = UI_REF.match(v)
        if m:
            refs.append((s, e, path, m.group(1)))
        elif UI_RAW_HEX.search(v):
            raws.append((s, e, path, v))
    return refs, raws


def resolve_ui(doc, uid):
    v = doc["ui"][uid]
    return v if v.startswith("#") else doc["palette"][v]


def ui_color_table(doc):
    """ui id -> "#RRGGBB[AA]" (what App/Resources/Tuning/ui-colors.json carries and Tuning.load resolves "@id" with)."""
    return {u: resolve_ui(doc, u) for u in sorted(doc.get("ui", {}))}


def resolve_ui_json(ui, doc=None):
    """A parsed ui.json with every "@<ui id>" replaced by its colour (for Python tools that read ui.json colours)."""
    table = ui_color_table(doc or load_colors())

    def walk(n):
        if isinstance(n, dict):
            return {k: walk(v) for k, v in n.items()}
        if isinstance(n, list):
            return [walk(v) for v in n]
        if isinstance(n, str) and n.startswith("@") and n[1:] in table:
            return table[n[1:]]
        return n
    return walk(ui)
