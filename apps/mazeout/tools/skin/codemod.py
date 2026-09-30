#!/usr/bin/env python3
"""tools/skin/codemod.py — replace the colour literals of the UI sources with skin tokens (docs/SKIN.md).

    python3 tools/skin/codemod.py --dry-run     # list what would change (token ids, palette names), write nothing
    python3 tools/skin/codemod.py               # rewrite the Swift sources + skin/colors.json, then run build.py
    python3 tools/skin/codemod.py --verify REV  # prove the rewrite kept every value: inline each token's value back into
                                                #   the sources and compare with `git show REV:<file>` (hex case-insensitive)

Re-runnable: literals already tokenised are left alone; a new literal gets a new token (its palette entry is reused when the
colour already has one, else a new palette name "<family>.<L*>[b-z]" is added). Existing ids and names are never renamed.

What is replaced (in code only; comments and other strings are never touched):
  0xRRGGBB            -> Skin.<token>            (UInt32: every call site in the scan takes UInt32 / [UInt32] / tuples of it)
  "#RRGGBB"           -> Skin.<token>Hex         (a String constant; the token id ends in ".hex")
  UIColor(red: r, green: g, blue: b, alpha: a) with decimal channels
                      -> UIColor(rgb: Skin.<token>, alpha: a)   (the channels rounded to 8 bit: < 0.5/255 away, the same
                                                                 rendered pixel)
Literals in tools/skin/literal_allowlist.json (non-colour hex such as RNG seeds) are skipped.

Token ids: "<area>.<file>.<scope…>.<role>[.<n>]", derived from where the literal sits:
  area   the folder (components, home, hud, pages, popups, profile, shop, social, shell, fx, art)
  file   the file's stem in lowerCamel (ShopView -> shopView)
  scope  the ui.json key when the literal is a Tokens default (t.color("popup.ribbon.top", 0x…) -> popup.ribbon.top), else
         the enclosing type and member (PriceButton.body -> priceButton), a `case .x` label, a `let x =` name
  role   the argument label or the modifier the colour feeds (fill, stroke, outline, face, stops …) and array indexes
Identical id + identical value share one token; identical id + another value get ".2", ".3" … in source order.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skinlib as S  # noqa: E402

DECL = re.compile(r"\b(struct|class|enum|extension|protocol|actor|func|init|var|let|subscript)\b\s*([A-Za-z_][A-Za-z0-9_]*)?")
NONDECL_HEAD = re.compile(r"^\s*(?:\}\s*)?(if|guard|while|for|switch|else|catch|do|repeat|defer|return)\b")
TOKEN_CALL = {"color", "colors", "stops", "text", "string", "strings"}
SKIP_CALLEE = {"Color", "UIColor", "cg", "UInt32", "init", "map", "compactMap", "Gradient", "Stop", "opacity", "CGColor",
               "Layer", "cgColor", "s2", "GameTextStyle", "SocStyle", "some", "AnyView"}
SKIP_LABEL = {"hex", "rgb", "color", "socHex", "", "_"}
SKIP_MEMBER = {"body", "init", "draw", "make", "render", "view", "content", "path"}


def lower_camel(s):
    s = re.sub(r"[^A-Za-z0-9]+(.)?", lambda m: (m.group(1) or "").upper(), s)
    m = re.match(r"^([A-Z]+)(?=[A-Z][a-z]|[0-9]|$)", s)
    if m and len(m.group(1)) > 1:
        return m.group(1).lower() + s[len(m.group(1)):]
    return s[:1].lower() + s[1:]


def ident_part(s):
    s = lower_camel(s)
    s = re.sub(r"[^A-Za-z0-9]", "", s)
    return s or "x"


def area_file(relpath):
    parts = relpath.split("/")
    stem = os.path.splitext(parts[-1])[0]
    if relpath.startswith("App/Shell/"):
        area = "shell" if len(parts) == 3 else parts[2].lower()
    elif relpath.startswith("App/FX/"):
        area = "fx"
    else:
        area = "art"
    return area, ident_part(stem)


class Namer:
    def __init__(self, lx):
        self.lx = lx
        self.code = lx.code
        self.text = lx.text
        self.scopes = self._scopes()

    def _scopes(self):
        """(open, close, kind, name) for every brace pair; kind/name from the header text before '{'."""
        code, out, stack = self.code, [], []
        for i, c in enumerate(code):
            if c == "{":
                head = self._header(i)
                # a header that spans lines: keep the part from the last line holding a declaration keyword
                kind = name = None
                if not NONDECL_HEAD.match(head.strip() and head or ""):
                    for m in DECL.finditer(head):
                        # the first declaration keyword at paren depth 0 of the header
                        pre = head[:m.start()]
                        if pre.count("(") - pre.count(")") == 0 and pre.count("[") - pre.count("]") == 0:
                            kind, name = m.group(1), m.group(2) or m.group(1)
                            break
                stack.append((i, kind, name))
            elif c == "}" and stack:
                o, kind, name = stack.pop()
                out.append((o, i, kind, name))
        return sorted(out)

    def _header(self, brace):
        """The text of the line (brackets spanning lines included) that ends at this '{'."""
        code, i, depth = self.code, brace - 1, 0
        while i >= 0:
            c = code[i]
            if c in ")]":
                depth += 1
            elif c in "([":
                if depth == 0:
                    break
                depth -= 1
            elif depth == 0 and c in "\n;{}":
                break
            i -= 1
        return code[i + 1:brace]

    def enclosing(self, pos):
        return [s for s in self.scopes if s[0] < pos < s[1]]      # outer -> inner

    def string_arg(self, open_paren):
        """The first argument of the call opening at `open_paren` when it is a string literal ('' otherwise)."""
        for (s, e, content, interp) in self.lx.strings:
            if s > open_paren:
                between = self.code[open_paren + 1:s]
                if between.strip() == "":
                    c = re.sub(r"\\\(([^()]*(?:\([^()]*\))?[^()]*)\)",
                               lambda m: re.findall(r"[A-Za-z_][A-Za-z0-9_]*", m.group(1))[-1:][0]
                               if re.findall(r"[A-Za-z_][A-Za-z0-9_]*", m.group(1)) else "x", content)
                    return c
                return ""
        return ""

    def path(self, pos):
        """Brackets around pos, inner -> outer, until the enclosing brace: (bracket, callee, label, index, open)."""
        code, i, depth, out = self.code, pos - 1, 0, []
        idx = 0
        label = self._label(pos)
        tern = self._ternary(pos)
        while i >= 0:
            c = code[i]
            if c in ")]}":
                depth += 1
            elif c in "([{":
                if depth == 0:
                    if c == "{":
                        break
                    m = re.search(r"([A-Za-z_][A-Za-z0-9_.]*)\s*$", code[:i])
                    callee = m.group(1).split(".")[-1] if (c == "(" and m) else ""
                    if callee in ("return", "in", "case", "if", "guard", "while", "where", "switch", "some", "let", "var"):
                        callee = ""
                    out.append(dict(br=c, callee=callee, label=label, index=idx, open=i, tern=tern))
                    label = self._label(i)
                    tern = self._ternary(i)
                    idx = 0
                else:
                    depth -= 1
            elif c == "," and depth == 0:
                idx += 1
            i -= 1
        return out

    def _label(self, pos):
        """The argument label of the argument pos sits in (`outline: on ? 0xA : 0xB` -> 'outline'), '' when none."""
        code, i, depth = self.code, pos - 1, 0
        while i >= 0:
            c = code[i]
            if c in ")]}":
                depth += 1
            elif c in "([{":
                if depth == 0:
                    break
                depth -= 1
            elif c == "," and depth == 0:
                break
            i -= 1
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*:(?!:)", code[i + 1:pos])
        return m.group(1) if m else ""

    @staticmethod
    def _assigned(head):
        """The name a statement assigns to: `let rim: [UInt32] = …` -> rim, `var a = 1, frostColor = …` -> frostColor,
        `l.strokeColor = …` -> strokeColor, `face.colors = …` -> faceColors; '' when none."""
        depth, cut = 0, []
        for k, c in enumerate(head):                     # keep depth-0 text only
            if c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            elif depth == 0:
                cut.append((k, c))
        flat = "".join(c for _, c in cut)
        ms = list(re.finditer(r"([A-Za-z_][A-Za-z0-9_.]*)\s*(?::[^=]*?)?(?<![=!<>+\-*/])=(?!=)", flat))
        if not ms:
            return ""
        comps = [c for c in ms[-1].group(1).split(".") if c]
        if not comps or comps[-1] in ("let", "var"):
            return ""
        if len(comps) >= 2 and len(comps[-2]) > 1 and comps[-1] in ("colors", "color", "backgroundColor", "fill", "stroke"):
            return ident_part(comps[-2]) + comps[-1][:1].upper() + comps[-1][1:]
        return ident_part(comps[-1])

    def _arg_start(self, pos):
        code, i, depth = self.code, pos - 1, 0
        while i >= 0:
            c = code[i]
            if c in ")]}":
                depth += 1
            elif c in "([{":
                if depth == 0:
                    break
                depth -= 1
            elif c == "," and depth == 0:
                break
            i -= 1
        return i + 1

    def _ternary(self, pos):
        """When pos starts a branch of a `cond ? a : b` (at the argument's own depth): 'hard' for the then-branch of
        `tag == .hard ? …`, 'notHard' for its else-branch; '' otherwise."""
        start = self._arg_start(pos)
        seg = self.code[start:pos]
        seg = re.sub(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*:(?!:)", lambda m: " " * len(m.group(0)), seg)   # the label
        seg = re.sub(r"^\s*(?:(?:static|private|fileprivate)\s+)*(?:let|var)\s+[^=]*=", lambda m: " " * len(m.group(0)), seg)
        seg = re.sub(r"^\s*(?:return|case\s+\.?[A-Za-z_]\w*\s*:\s*return)\b", lambda m: " " * len(m.group(0)), seg)
        # depth-0 '?' and ':' of the segment
        depth, marks = 0, []
        for k, c in enumerate(seg):
            if c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            elif depth == 0 and c == "?" and (k + 1 >= len(seg) or seg[k + 1] in " \n(["):
                marks.append((k, "?"))
            elif depth == 0 and c == ":" and any(m[1] == "?" for m in marks):
                marks.append((k, ":"))
        if not marks or seg[marks[-1][0] + 1:].strip():
            return ""
        k, kind = marks[-1]
        # the condition of the '?' this branch belongs to
        qs = [m[0] for m in marks if m[1] == "?" and m[0] <= k]
        if not qs:
            return ""
        q = qs[-1]
        prev = [m[0] for m in marks if m[0] < q]
        cond = seg[(prev[-1] + 1) if prev else 0:q]
        toks = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+", cond.replace("&&", " ").replace("||", " "))
        if not toks:
            return ""
        if "==" in cond and toks[-1].isdigit() and len(toks) > 1:
            word = toks[-2] + toks[-1]
        else:
            word = toks[-1]
        neg = cond.strip().startswith("!")
        word = ident_part(word)
        then = (kind == "?") != neg
        return word if then else "not" + word[:1].upper() + word[1:]

    def statement_head(self, pos):
        code = self.code
        j = max(code.rfind(";", 0, pos), code.rfind("{", 0, pos), code.rfind("}", 0, pos))
        return code[j + 1:pos]

    def name(self, pos):
        parts = []
        scopes = self.enclosing(pos)
        types = [s for s in scopes if s[2] in ("struct", "class", "enum", "extension", "protocol", "actor")]
        members = [s for s in scopes if s[2] in ("func", "init", "var", "let", "subscript")]
        path = self.path(pos)
        # a Tokens default: t.color("key", 0x…) / t.text("key", .s2(…)) -> the key
        key = ""
        for p in path:
            if p["br"] == "(" and p["callee"] in TOKEN_CALL:
                key = self.string_arg(p["open"])
                if key:
                    break
        if key:
            parts.append(key)
        else:
            if types:
                parts.append(ident_part(types[-1][3] or "type"))
            if members:
                mname = members[-1][3]
                if mname and mname not in SKIP_MEMBER and (not types or members[-1][0] > types[-1][0]):
                    parts.append(ident_part(mname))
            top = path[-1]["open"] if path else pos
            head = self.code[self.code.rfind("\n", 0, top) + 1:top]
            target = self._assigned(head)
            if target and target not in parts:
                parts.append(target)
            # a switch case in the current scope
            inner = scopes[-1][0] if scopes else 0
            seg = self.code[inner + 1:pos]
            while True:                                  # drop closed nested blocks: their cases are not ours
                seg2 = re.sub(r"\{[^{}]*\}", " ", seg)
                if seg2 == seg:
                    break
                seg = seg2
            cm = list(re.finditer(r"\bcase\s+\.?([A-Za-z_][A-Za-z0-9_]*)|\bdefault\s*:", seg))
            if cm:
                parts.append(ident_part(cm[-1].group(1) or "default"))
        # the role: labels / callees inner -> outer until a meaningful one (keeping array indexes on the way)
        role, idxs = [], []
        terns = [] if path else [t for t in [self._ternary(pos)] if t]
        for p in path:
            if p["tern"]:
                terns.append(p["tern"])
            if p["br"] == "(" and p["callee"] in TOKEN_CALL and key:
                break
            if p["br"] == "[":
                idxs.append(str(p["index"]))
                continue
            lab = p["label"] if p["label"] not in SKIP_LABEL else ""
            if lab:
                role.append(ident_part(lab))
                break
            if p["br"] == "(" and p["callee"] and p["callee"] not in SKIP_CALLEE:
                role.append(ident_part(p["callee"]))
                break
            if p["br"] == "(" and not p["callee"] and len(path) > 1:
                continue                             # a tuple: (location, 0x…) keeps the array index only
        parts += role
        parts += list(reversed(terns))
        parts += list(reversed(idxs))
        return parts


def token_ids(files):
    """-> list of (path, literal dict, base id) for every literal not tokenised yet and not allow-listed."""
    allow = S.load_allowlist()
    out = []
    for p in files:
        text = open(p, encoding="utf-8").read()
        lx = S.swift_lex(text)
        lits = S.scan_literals(p, lx)
        if not lits:
            continue
        namer = Namer(lx)
        relp = S.rel(p)
        area, stem = area_file(relp)
        for o in lits:
            if o["kind"] == "white" or o.get("alpha") or S.allowed(allow, relp, o):
                continue                                 # UIColor(white:) / "#RRGGBBAA": by hand (check-literals lists them)
            parts = [area, stem] + namer.name(o["start"])
            if o["kind"] == "hexstr":
                parts.append("hex")
            tid = ".".join(ident_part(x) if i < 2 or "." not in x else ".".join(ident_part(y) for y in x.split(".") if y)
                           for i, x in enumerate(parts))
            out.append((p, o, tid))
    return out


def next_palette_name(pal, hx):
    base = S.palette_base_name(hx)
    if base not in pal:
        return base
    for suf in "bcdefghijklmnopqrstuvwxyz":
        if base + suf not in pal:
            return base + suf
    raise SystemExit(f"palette: more than 25 colours at {base}")


def plan(files, doc):
    pal, toks = doc["palette"], doc["tokens"]
    by_hex = {}
    for k, v in sorted(pal.items()):
        by_hex.setdefault(v, k)
    names = {S.swift_name(t) for t in toks}
    art = S.uiart_names()
    edits = {}                                           # path -> [(start, end, replacement)]
    new_tokens = {}
    for p, o, tid in token_ids(files):
        hx = o["hex"]
        if hx not in by_hex:
            name = next_palette_name(pal, hx)
            pal[name] = hx
            by_hex[hx] = name
        pname = by_hex[hx]
        # the same id with the same colour shares the token; another colour gets .2, .3 …
        final, n = tid, 1
        while True:
            if final in toks:
                if S.resolve(doc, final) == hx:
                    break
            elif S.swift_name(final) not in names and S.swift_name(final) not in art:
                toks[final] = pname
                names.add(S.swift_name(final))
                new_tokens[final] = pname
                break
            n += 1
            final = (tid[:-4] + f".v{n}.hex") if tid.endswith(".hex") else f"{tid}.v{n}"
        const = "Skin." + S.swift_name(final)
        if o["kind"] == "dec":
            rep = f"UIColor(rgb: {const}"
            end = o["end"]
            # keep the alpha argument: `…, blue: b, alpha: a)` -> `UIColor(rgb: Skin.x, alpha: a)`
            rest = open(p, encoding="utf-8").read()[end:end + 40]
            am = re.match(r"\s*,\s*alpha:\s*([0-9.]+)", rest)
            if am:
                rep += f", alpha: {am.group(1)}"
                end += am.end()
            edits.setdefault(p, []).append((o["start"], end, rep))
        else:
            edits.setdefault(p, []).append((o["start"], o["end"], const))
    return edits, new_tokens


def apply(edits):
    for p, es in edits.items():
        text = open(p, encoding="utf-8").read()
        for s, e, r in sorted(es, reverse=True):
            text = text[:s] + r + text[e:]
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)


def inline_back(text, doc):
    """Replace every Skin.<name> with its colour literal (0xRRGGBB, or "#RRGGBB" for String tokens)."""
    table = {S.swift_name(t): (t, S.resolve(doc, t)) for t in doc["tokens"]}

    def sub(m):
        t, hx = table[m.group(1)]
        return f'"{hx}"' if S.is_string_token(t) else "0x" + hx[1:]
    return re.sub(r"\bSkin\.([A-Za-z0-9_]+)", sub, text)


def verify(rev):
    doc = S.load_colors()
    repo = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=S.APP, capture_output=True, text=True).stdout.strip()
    bad = checked = 0
    for p in S.scanned_files():
        now = open(p, encoding="utf-8").read()
        if "Skin." not in now:
            continue
        gp = os.path.relpath(p, repo).replace(os.sep, "/")
        r = subprocess.run(["git", "show", f"{rev}:{gp}"], cwd=repo, capture_output=True, text=True)
        if r.returncode:
            print(f"verify: {gp} not in {rev}")
            bad += 1
            continue
        old = r.stdout
        back = inline_back(now, doc)
        # the one decimal form: UIColor(rgb: 0xRRGGBB, alpha: a) came from UIColor(red:green:blue:alpha:)
        norm = lambda s: re.sub(r"0x[0-9A-Fa-f]{6}\b", lambda m: m.group(0).upper().replace("0X", "0x"), s)  # noqa: E731
        a, b = norm(old), norm(back)
        checked += 1
        if a != b:
            al, bl = a.splitlines(), b.splitlines()
            diffs = [(i + 1, x, y) for i, (x, y) in enumerate(zip(al, bl)) if x != y]
            ok = len(al) == len(bl) and all(_dec_equiv(x, y) for _, x, y in diffs)
            if not ok:
                bad += 1
                print(f"verify: {gp} differs from {rev} after inlining the tokens back:")
                for ln, x, y in diffs[:5]:
                    print(f"  {ln}: was: {x.strip()}\n  {ln}: now: {y.strip()}")
    print(f"verify: {checked} files compared with {rev}; {bad} differ")
    return bad == 0


def _dec_equiv(old_line, new_line):
    """True when the only change on the line is UIColor(red:green:blue:alpha:) -> UIColor(rgb: 0x…, alpha:) of the same
    8-bit colour."""
    m = S.DEC_COLOR.search(old_line)
    n = re.search(r"UIColor\(rgb: 0x([0-9A-F]{6})", new_line)
    if not (m and n):
        return False
    chans = [S._dec(m.group(i), m.group(i + 1)) for i in (1, 3, 5)]
    return S.rgb_hex([c * 255 for c in chans])[1:] == n.group(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", metavar="REV")
    ap.add_argument("--list", action="store_true", help="with --dry-run: print every literal -> token")
    a = ap.parse_args()
    if a.verify:
        sys.exit(0 if verify(a.verify) else 1)
    doc = S.load_colors() if os.path.exists(S.COLORS_JSON) else {
        "about": "Skin colours: palette = named colours, tokens = every colour the UI code draws "
                 "(docs/SKIN.md). Edit, then python3 tools/skin/build.py.",
        "palette": {}, "tokens": {}}
    pal0, tok0 = len(doc["palette"]), len(doc["tokens"])
    edits, new = plan(S.scanned_files(), doc)
    n_sites = sum(len(v) for v in edits.values())
    if a.dry_run:
        if a.list:
            for t, pn in sorted(new.items()):
                print(f"{t} = {pn} {doc['palette'][pn]}")
        print(f"dry run: {n_sites} literals in {len(edits)} files -> {len(new)} new tokens; palette {pal0} -> "
              f"{len(doc['palette'])}")
        return
    errs = S.validate(doc)
    if errs:
        print("\n".join(errs))
        sys.exit(1)
    apply(edits)
    S.save_colors(doc)
    print(f"codemod: {n_sites} literals in {len(edits)} files -> {len(new)} new tokens (now {len(doc['tokens'])}); "
          f"palette {pal0} -> {len(doc['palette'])}")
    subprocess.run([sys.executable, os.path.join(S.HERE, "build.py")], check=True)


if __name__ == "__main__":
    main()
