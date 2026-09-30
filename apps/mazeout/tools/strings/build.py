#!/usr/bin/env python3
"""CONTENT (GAMEPROMPT §8.1 "Shell", §8.3 "Content"): App/Resources/Strings/strings.tsv (+ requests/*.tsv) + the 11 language
tables App/Resources/Strings/l10n/strings.<lang>.tsv -> App/Resources/Localizable.xcstrings, 13 languages (SPEC.md ruling 37a:
en de fr es it pt-BR tr ja ko zh-Hans pl sk sl). Copied from apps/matchfactory/tools/strings/build.py (05424db); the changes
are listed in design/REUSE.md; B3 L10N-APP (2026-09-28) added the 11 language tables.

    python3 tools/strings/build.py            # validate the TSVs, merge, write the catalogue
    python3 tools/strings/build.py --check    # validate and fail (exit 1) if the catalogue on disk is stale
    python3 tools/strings/build.py --tsv F --out G   # another TSV / catalogue (tests, scratch)
    python3 tools/strings/build.py --no-requests     # strings.tsv alone
    python3 tools/strings/build.py --en-tr-only      # without the l10n tables (tests of the EN/TR rules, scratch)

Merge (SPEC-architecture §3.3, L1): strings.tsv (CONTENT) + every App/Resources/Strings/requests/<role>.tsv (append-only, one
per requesting role). A strings.tsv row WINS over a request row with the same key (a request whose TR differs is reported as
"overridden"); two request rows with the same key must agree (else an error, nothing written). Every file is validated with
the same rules; a request row's context is prefixed with its role.

strings.tsv
  - UTF-8, tab-separated, header row `en<TAB>tr<TAB>context`, one string per row. Lines starting with `#` are comments.
  - `en` is the EXACT key Swift generates from the English literal in code: `Text("Level \\(n)")` -> `Level %lld`
    (Int -> %lld, String -> %@). A translation that reorders or repeats arguments uses positional specifiers (%1$@),
    memory `reordered-args-need-positional`; build.py writes positional specifiers whenever a string has 2+ arguments.
  - Escapes inside a cell: \\n newline, \\t tab, \\\\ backslash. Nothing else is interpreted.
  - `**run**` marks a highlighted run (e.g. "Pass arrows through the **PIPE** to break it!"); SHELL draws it in the accent
    colour of the spec (SPEC-ui).
  - `context` = the spec id(s), the evidence tags and notes; it becomes the catalogue comment.

l10n/strings.<lang>.tsv (B3; de fr es it pt-BR ja ko zh-Hans pl sk sl)
  - header `en<TAB><lang><TAB>note`; one row per catalogue key (the merged strings.tsv + requests key set), keyed by the EXACT
    EN key; `#` lines are comments (T2's '#~' superseded rows among them). The note is never shipped.
  - EVERY key must have a row in EVERY table and no table may carry a key the catalogue does not have: a new strings.tsv /
    request row is translated in all 11 tables in the same change (no untranslated string ships).
  - A cell is validated like a TR cell (specifiers in EN argument order — a reordered translation spells %1$@ — balanced
    `**`, no brand, no stray whitespace). `**run**` in a caseless language (ja ko zh-Hans) marks the run MultiRunText lights
    where EN/TR light a CAPS word (the unlock cards).

infoplist.tsv (the Info.plist permission texts; may be empty)
  - header `key<TAB>en<TAB>tr<TAB>de … sl<TAB>note` (the 13 languages in INFOPLIST_LANGS order): one row per Info.plist key
    whose value iOS shows to the player (permission texts: camera, tracking, …; none in the template). Written to
    App/Resources/InfoPlist.xcstrings (Xcode compiles <lang>.lproj/InfoPlist.strings). Every cell non-empty, no stray
    whitespace, no brand, no format specifier or ** run; the EN cell must equal the key's value in project.yml's info: block
    (the base plist's development-language value), or nothing is written.

keys.tsv (FIX-2 lane B, B1b-r3)
  - header `key<TAB>en<TAB>note`: a lowercase dotted IDENTIFIER key of strings.tsv and the English text the catalogue ships
    for it (String(localized: "event.finished", defaultValue: "Finished")); every other key IS its English text. Each keys.tsv
    key must be a row, and an identifier-looking row key must be listed (else English would show the key).

Validation (any error -> exit 1, nothing written):
  - 3 columns, non-empty en and tr, no duplicate en key, no stray whitespace at either end of a cell;
  - the format arguments of tr equal those of en (same count, same types, in en ORDER once positions are resolved:
    memory reordered-args-need-positional);
  - `**` markers are balanced in both columns;
  - no literal brand name (ours or the original's, BRANDS below): copy that names the brand interpolates Brand.name
    (GAMEPROMPT §8.3 "Brand").
"""
import json
import os
import re
import sys

APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TSV = os.path.join(APP, "App", "Resources", "Strings", "strings.tsv")
REQUESTS = os.path.join(APP, "App", "Resources", "Strings", "requests")
OUT = os.path.join(APP, "App", "Resources", "Localizable.xcstrings")
L10N = os.path.join(APP, "App", "Resources", "Strings", "l10n")
# B3: the languages of the l10n tables (EN + TR live in strings.tsv); the catalogue order is Xcode's (sorted keys).
LANGS = ["de", "fr", "es", "it", "pt-BR", "ja", "ko", "zh-Hans", "pl", "sk", "sl"]
# The working title (dev builds only, behind `Brand`), its code spelling, the original's former name and its publisher.
# Matched case-insensitively as substrings of either column.
BRANDS = ("Maze Out", "MazeOut", "Arrow Jam", "Grand Games", "Arrow Out", "ArrowOut")
# FIX-2 lane B (B1b-r3): identifier keys -> their English text (App/Resources/Strings/keys.tsv; header key<TAB>en<TAB>note).
# A key that is not its English text: English says one word where other languages need two ('Finished' = a life arrived vs
# 'event.finished' = the event is over). Code: String(localized: "<key>", defaultValue: "<en>").
KEYS_TSV = os.path.join(APP, "App", "Resources", "Strings", "keys.tsv")
# The Info.plist strings (permission texts) -> App/Resources/InfoPlist.xcstrings (absent when infoplist.tsv has no rows)
INFOPLIST_TSV = os.path.join(APP, "App", "Resources", "Strings", "infoplist.tsv")
INFOPLIST_OUT = os.path.join(APP, "App", "Resources", "InfoPlist.xcstrings")
INFOPLIST_LANGS = ["en", "tr"] + LANGS
PROJECT_YML = os.path.join(APP, "project.yml")
IDENTIFIER_RE = re.compile(r"^[a-z][a-zA-Z0-9]*(\.[a-z][a-zA-Z0-9]*)+$")


def load_keyed(path=KEYS_TSV):
    """keys.tsv -> ({key: English}, errors)."""
    out, errors = {}, []
    if not os.path.exists(path):
        return out, errors
    lines = open(path, encoding="utf-8").read().split("\n")
    if not lines or lines[0].split("\t") != ["key", "en", "note"]:
        return out, ["keys.tsv line 1: the header must be `key<TAB>en<TAB>note`"]
    for no, line in enumerate(lines[1:], start=2):
        if not line.strip() or line.startswith("#"):
            continue
        c = line.split("\t")
        if len(c) != 3 or not c[0] or not c[1] or any(x != x.strip() for x in c):
            errors.append(f"keys.tsv line {no}: want key<TAB>en<TAB>note, no empty key/en, no stray whitespace")
            continue
        if not IDENTIFIER_RE.match(c[0]):
            errors.append(f"keys.tsv line {no}: {c[0]!r} is not a lowercase dotted identifier key")
        if c[0] in out:
            errors.append(f"keys.tsv line {no}: duplicate key {c[0]!r}")
        out[c[0]] = unescape(c[1])
    return out, errors


def english(key):
    """The English text the catalogue ships for a key (the key itself unless keys.tsv maps it)."""
    return KEYED.get(key, key)


def check_keyed(rows, keyed=None):
    """Every keys.tsv key is a row, and every identifier-looking row key is in keys.tsv (else English would show the key)."""
    keyed = KEYED if keyed is None else keyed
    errors = list(KEYED_ERRORS) if keyed is KEYED else []
    have = {r["en"] for r in rows}
    for k in sorted(set(keyed) - have):
        errors.append(f"keys.tsv: {k!r} has no strings.tsv row")
    for k in sorted(have):
        if IDENTIFIER_RE.match(k) and k not in keyed:
            errors.append(f"strings.tsv: {k!r} looks like an identifier key but keys.tsv gives it no English text")
        if k in keyed and resolved_types(k) != resolved_types(keyed[k]):
            errors.append(f"keys.tsv: {k!r} and its English {keyed[k]!r} take different arguments")
    return errors

# printf-style specifiers Swift emits for interpolations (%lld, %@, %d, %f, %lf, %.1f ...), optional n$ position.
SPEC_RE = re.compile(r"%(?:(\d+)\$)?(?:[-+ 0#]*\d*(?:\.\d+)?)(lld|ld|d|u|llu|@|f|lf|e|g|s|c)")


def unescape(cell):
    out, i = [], 0
    while i < len(cell):
        ch = cell[i]
        if ch == "\\" and i + 1 < len(cell):
            nxt = cell[i + 1]
            if nxt in "nt\\":
                out.append({"n": "\n", "t": "\t", "\\": "\\"}[nxt])
                i += 2
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def args(s):
    """[(position or None, type)] in textual order; %% is not an argument."""
    s = s.replace("%%", "")
    return [(int(m.group(1)) if m.group(1) else None, m.group(2)) for m in SPEC_RE.finditer(s)]


def resolved_types(s):
    """Argument types in ARGUMENT order (positional specifiers resolved)."""
    a = args(s)
    if not a:
        return []
    if any(p is not None for p, _ in a):
        if not all(p is not None for p, _ in a):
            raise ValueError("mixes positional and non-positional specifiers")
        by = {}
        for p, t in a:
            if p in by and by[p] != t:
                raise ValueError(f"argument {p} used with two types")
            by[p] = t
        if sorted(by) != list(range(1, len(by) + 1)):
            raise ValueError("positional arguments are not 1...n")
        return [by[i] for i in range(1, len(by) + 1)]
    return [t for _, t in a]


def norm_type(t):
    return {"ld": "lld", "d": "lld", "u": "lld", "llu": "lld", "lf": "f"}.get(t, t)


def positional(s):
    """Rewrites non-positional specifiers as %1$..., %2$... (only when there are 2+)."""
    a = args(s)
    if len(a) < 2 or any(p is not None for p, _ in a):
        return s
    n = iter(range(1, len(a) + 1))
    return SPEC_RE.sub(lambda m: m.group(0).replace("%", f"%{next(n)}$", 1), s)


def load(path=TSV):
    rows, errors = [], []
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    if not lines or lines[0].split("\t") != ["en", "tr", "context"]:
        errors.append("line 1: the header must be `en<TAB>tr<TAB>context`")
        return rows, errors
    seen = {}
    for no, line in enumerate(lines[1:], start=2):
        if not line.strip() or line.startswith("#"):
            continue
        cells = line.split("\t")
        if len(cells) != 3:
            errors.append(f"line {no}: {len(cells)} columns (want 3): {line[:60]!r}")
            continue
        raw_en, raw_tr, ctx = cells
        for name, c in (("en", raw_en), ("tr", raw_tr), ("context", ctx)):
            if c != c.strip():
                errors.append(f"line {no}: {name} has leading/trailing whitespace")
        en, tr = unescape(raw_en), unescape(raw_tr)
        if not en or not tr:
            errors.append(f"line {no}: empty en or tr")
            continue
        if en in seen:
            errors.append(f"line {no}: duplicate key {en!r} (first on line {seen[en]})")
            continue
        seen[en] = no
        for name, s in (("en", en), ("tr", tr)):
            if s.count("**") % 2:
                errors.append(f"line {no}: unbalanced ** in {name}: {s!r}")
            for brand in BRANDS:
                if brand.lower() in s.lower():
                    errors.append(f"line {no}: literal brand name {brand!r} in {name}; interpolate Brand.name instead")
        try:
            te, tt = [norm_type(t) for t in resolved_types(en)], [norm_type(t) for t in resolved_types(tr)]
            if te != tt:
                errors.append(f"line {no}: format arguments differ: en {te} vs tr {tt} ({en!r} / {tr!r})")
        except ValueError as e:
            errors.append(f"line {no}: {e}")
        rows.append({"line": no, "en": en, "tr": tr, "context": ctx})
    return rows, errors


def load_all(tsv=TSV, requests_dir=REQUESTS, use_requests=True):
    """strings.tsv + requests/*.tsv -> (merged rows, errors, notes). strings.tsv wins; request rows must agree."""
    rows, errors = load(tsv)
    errors = ["%s %s" % (os.path.basename(tsv), e) for e in errors]
    notes = []
    if not use_requests or not os.path.isdir(requests_dir):
        return rows, errors, notes
    base = {r["en"]: r for r in rows}
    req = {}
    for fn in sorted(os.listdir(requests_dir)):
        if not fn.endswith(".tsv"):
            continue
        path = os.path.join(requests_dir, fn)
        if os.path.getsize(path) == 0:
            continue
        role = fn[:-4]
        rr, ee = load(path)
        errors += ["requests/%s %s" % (fn, e) for e in ee]
        for r in rr:
            r = dict(r, context="%s request: %s" % (role.upper(), r["context"]), role=role)
            k = r["en"]
            if k in base:
                if base[k]["tr"] != r["tr"]:
                    notes.append("overridden: %r requested by %s as %r; strings.tsv has %r" % (k, role, r["tr"], base[k]["tr"]))
                continue
            if k in req:
                if req[k]["tr"] != r["tr"]:
                    errors.append("requests: %r is %r in %s but %r in %s (two request rows must agree)" % (
                        k, req[k]["tr"], req[k]["role"], r["tr"], role))
                continue
            req[k] = r
    merged = rows + [req[k] for k in sorted(req)]
    return merged, errors, notes


def check_cell(where, lang, en, value):
    """The TR cell rules for any language's cell -> [errors]."""
    errors = []
    if value.count("**") % 2:
        errors.append(f"{where}: unbalanced ** in {lang}: {value!r}")
    for brand in BRANDS:
        if brand.lower() in value.lower():
            errors.append(f"{where}: literal brand name {brand!r} in {lang}; interpolate Brand.name instead")
    try:
        te, tt = [norm_type(t) for t in resolved_types(en)], [norm_type(t) for t in resolved_types(value)]
        if te != tt:
            errors.append(f"{where}: format arguments differ: en {te} vs {lang} {tt} ({en!r} / {value!r})")
        a = args(value)
        if len(a) >= 2 and all(p is None for p, _ in a) and [norm_type(t) for _, t in a] != [norm_type(t) for _, t in args(en)]:
            errors.append(f"{where}: {lang} reorders its arguments without positions (%1$@): {value!r}")
    except ValueError as e:
        errors.append(f"{where}: {lang}: {e}")
    return errors


def load_l10n(keys, l10n_dir=L10N, langs=LANGS):
    """The 11 language tables -> ({lang: {en: value}}, errors). Every key of `keys` must have exactly one row per table."""
    tables, errors = {}, []
    for lang in langs:
        path = os.path.join(l10n_dir, f"strings.{lang}.tsv")
        name = f"l10n/strings.{lang}.tsv"
        if not os.path.exists(path):
            errors.append(f"{name}: missing (every language needs its table)")
            continue
        with open(path, encoding="utf-8") as f:
            lines = f.read().split("\n")
        if not lines or lines[0].split("\t") != ["en", lang, "note"]:
            errors.append(f"{name} line 1: the header must be `en<TAB>{lang}<TAB>note`")
            continue
        table, seen = {}, {}
        for no, line in enumerate(lines[1:], start=2):
            if not line.strip() or line.startswith("#"):
                continue
            cells = line.split("\t")
            if len(cells) != 3:
                errors.append(f"{name} line {no}: {len(cells)} columns (want 3): {line[:60]!r}")
                continue
            raw_en, raw_v, _note = cells
            for label, c in (("en", raw_en), (lang, raw_v)):
                if c != c.strip():
                    errors.append(f"{name} line {no}: {label} has leading/trailing whitespace")
            en, v = unescape(raw_en), unescape(raw_v)
            if not en or not v:
                errors.append(f"{name} line {no}: empty en or {lang}")
                continue
            if en in seen:
                errors.append(f"{name} line {no}: duplicate key {en!r} (first on line {seen[en]})")
                continue
            seen[en] = no
            if en not in keys:
                errors.append(f"{name} line {no}: {en!r} is not a catalogue key (stale row, or a typo in the EN key)")
                continue
            errors += check_cell(f"{name} line {no}", lang, en, v)
            table[en] = v
        missing = [k for k in keys if k not in table]
        if missing:
            errors.append(f"{name}: {len(missing)} key(s) untranslated: " + ", ".join(repr(k) for k in missing[:6])
                          + (" …" if len(missing) > 6 else ""))
        tables[lang] = table
    return tables, errors


KEYED, KEYED_ERRORS = load_keyed()        # FIX-2 B: after `unescape` (module load order)


def catalogue(rows, tables=None):
    strings = {}
    for r in rows:
        loc = {
            "en": {"stringUnit": {"state": "translated", "value": english(r["en"])}},          # FIX-2 B: keys.tsv
            "tr": {"stringUnit": {"state": "translated", "value": positional(r["tr"])}},
        }
        for lang, table in (tables or {}).items():
            if r["en"] in table:
                loc[lang] = {"stringUnit": {"state": "translated", "value": positional(table[r["en"]])}}
        strings[r["en"]] = {
            "comment": r["context"],
            "extractionState": "manual",
            "localizations": loc,
        }
    return {"sourceLanguage": "en", "strings": strings, "version": "1.0"}


def load_infoplist(path=INFOPLIST_TSV, project_yml=PROJECT_YML):
    """infoplist.tsv -> ({plist key: {lang: value}}, {key: note}, errors). Absent file = no Info.plist strings."""
    out, notes, errors = {}, {}, []
    if not os.path.exists(path):
        return out, notes, errors
    lines = open(path, encoding="utf-8").read().split("\n")
    want = ["key"] + INFOPLIST_LANGS + ["note"]
    if not lines or lines[0].split("\t") != want:
        return out, notes, ["infoplist.tsv line 1: the header must be " + "<TAB>".join(want)]
    yml = open(project_yml, encoding="utf-8").read() if os.path.exists(project_yml) else ""
    for no, line in enumerate(lines[1:], start=2):
        if not line.strip() or line.startswith("#"):
            continue
        c = line.split("\t")
        where = f"infoplist.tsv line {no}"
        if len(c) != len(want):
            errors.append(f"{where}: {len(c)} columns (want {len(want)})")
            continue
        key, cells, note = c[0], c[1:-1], c[-1]
        if not re.match(r"^[A-Z][A-Za-z0-9]+$", key):
            errors.append(f"{where}: {key!r} is not an Info.plist key")
            continue
        if key in out:
            errors.append(f"{where}: duplicate key {key!r}")
            continue
        vals = {}
        for lang, raw in zip(INFOPLIST_LANGS, cells):
            v = unescape(raw)
            if not v or raw != raw.strip():
                errors.append(f"{where}: {lang} is empty or has leading/trailing whitespace")
                continue
            if args(v) or "%" in v or "**" in v:
                errors.append(f"{where}: {lang} carries a format specifier / % / ** (an Info.plist string is shown as is)")
            for brand in BRANDS:
                if brand.lower() in v.lower():
                    errors.append(f"{where}: literal brand name {brand!r} in {lang} (iOS names the app itself)")
            vals[lang] = v
        m = re.search(r"^\s+" + re.escape(key) + r':\s*"(.*)"\s*$', yml, re.M)
        if not m:
            errors.append(f"{where}: project.yml's info: block has no {key} (the base plist needs the English value)")
        elif m.group(1) != vals.get("en"):
            errors.append(f"{where}: the EN cell differs from project.yml's info: {key} (they must be identical)")
        out[key], notes[key] = vals, note
    return out, notes, errors


def infoplist_catalogue(rows, notes):
    strings = {}
    for key, vals in rows.items():
        strings[key] = {
            "comment": notes.get(key, ""),
            "extractionState": "manual",
            "localizations": {lang: {"stringUnit": {"state": "translated", "value": v}} for lang, v in vals.items()},
        }
    return {"sourceLanguage": "en", "strings": strings, "version": "1.0"}


def render(cat):
    # Xcode's own layout: 2-space indent, " : " separators, keys sorted, non-ASCII kept.
    return json.dumps(cat, ensure_ascii=False, indent=2, sort_keys=True, separators=(",", " : ")) + "\n"


def main(argv):
    global OUT
    check = "--check" in argv
    tsv = argv[argv.index("--tsv") + 1] if "--tsv" in argv else TSV
    if "--out" in argv:
        OUT = os.path.abspath(argv[argv.index("--out") + 1])
    if not os.path.exists(tsv):
        print(f"strings: {tsv} not found (L1 writes it)", file=sys.stderr)
        return 1
    rows, errors, notes = load_all(tsv, use_requests="--no-requests" not in argv)
    if tsv == TSV:
        errors = errors + check_keyed(rows)                                   # FIX-2 B: identifier keys (keys.tsv)
    tables = {}
    if "--en-tr-only" not in argv:
        tables, l10n_errors = load_l10n({r["en"] for r in rows})
        errors = errors + l10n_errors
    ip_rows, ip_notes, ip_errors = load_infoplist() if tsv == TSV else ({}, {}, [])     # the Info.plist strings
    errors = errors + ip_errors
    for e in errors:
        print("error:", e, file=sys.stderr)
    if errors:
        print(f"strings: {len(errors)} error(s); nothing written", file=sys.stderr)
        return 1
    for n in notes:
        print("note:", n)
    nreq = sum(1 for r in rows if r.get("role"))
    text = render(catalogue(rows, tables))
    json.loads(text)  # the output must parse
    ip_text = render(infoplist_catalogue(ip_rows, ip_notes)) if ip_rows else None
    if check:
        cur = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else None
        if cur != text:
            print(f"strings: {os.path.relpath(OUT, APP)} is stale; run tools/strings/build.py", file=sys.stderr)
            return 1
        cur = open(INFOPLIST_OUT, encoding="utf-8").read() if os.path.exists(INFOPLIST_OUT) else None
        if cur != ip_text:                          # no rows: the catalogue must not exist (a leftover ships old text)
                print(f"strings: {os.path.relpath(INFOPLIST_OUT, APP)} is stale; run tools/strings/build.py", file=sys.stderr)
                return 1
        print(f"strings: {len(rows)} keys ({nreq} from requests) x {2 + len(tables)} languages, catalogue up to date")
        return 0
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, OUT)
    if ip_text is not None:
        with open(INFOPLIST_OUT + ".tmp", "w", encoding="utf-8") as f:
            f.write(ip_text)
        os.replace(INFOPLIST_OUT + ".tmp", INFOPLIST_OUT)
        print(f"strings: {len(ip_rows)} Info.plist key(s) -> {os.path.relpath(INFOPLIST_OUT, APP)} ({len(INFOPLIST_LANGS)} languages)")
    elif os.path.exists(INFOPLIST_OUT):
        os.remove(INFOPLIST_OUT)
        print(f"strings: no Info.plist strings in infoplist.tsv: removed {os.path.relpath(INFOPLIST_OUT, APP)}")
    print(f"strings: {len(rows)} keys ({len(rows) - nreq} strings.tsv + {nreq} from requests/*.tsv) -> "
          f"{os.path.relpath(OUT, APP)} ({2 + len(tables)} languages: en tr {' '.join(tables)}; all translated)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
