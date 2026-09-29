#!/usr/bin/env python3
"""CONTENT (GAMEPROMPT §8.1 "Shell", §8.3 "Content", §14): proves strings.tsv covers the specs, the tutorial data and
the code, in EN + TR.

    python3 tools/strings/coverage.py [--strict-code] [--report FILE] [--config FILE] [--tsv FILE]

Generalised from apps/matchfactory/tools/strings/coverage.py (05424db). Match Factory hard-coded its spec sections and
compared TURKISH (its phone UI was Turkish). Maze Out's measured copy is ENGLISH (research/flows.md: "Game UI is
ENGLISH"), so every source says which column it quotes (`lang`), and the sources live in tools/strings/sources.json
(the spec writers point them at their real sections). design/REUSE.md lists the changes.

1. SPEC coverage (hard): every string quoted by a source in sources.json `spec_sources` is in strings.tsv, byte for
   byte, in that source's `lang` column. Placeholders compare as placeholders ({n} == %lld == %1$lld). Match kinds:
     exact     identical after placeholder canonicalisation (markup `**` included);
     instance  the spec quotes one instance of a format string ("+30 sec" for "+%lld sec");
     layout    identical except that the spec writes a line break as a space.
   A spec string that a later MEASUREMENT replaced is accepted only when sources.json `superseded` lists it with the
   evidence. A source file that does not exist FAILS unless its entry says "optional": true (a spec that is not
   written yet is not coverage). Kinds: json, json-map, md-table, md-quoted and md-blockquote (every "> " paragraph of the
   blocks whose label line matches `label`, e.g. SPEC-gameplay §16.10's Terms/Privacy texts); `split` may be one separator
   or a list; `substitute` maps literal text to a placeholder (the brand name -> %@, which Brand.name fills).
2. DATA coverage (hard): every strings-table KEY the bundled content carries has a row: sources.json `data_files`
   (Levels/tutorials.json captions, Levels/unlocks.json titles and cards, Levels/sessions.json HUD / panel labels). A data
   file that does not exist fails.
4. L10N coverage (hard; B3 L10N-APP 2026-09-28): every catalogue key has a valid row in each of the 11 language tables
   App/Resources/Strings/l10n/strings.<lang>.tsv (build.py `load_l10n`; `--en-tr-only` skips it).
3. CODE coverage (report; --strict-code makes it hard): every English literal handed to one of `callees` (Text,
   OutlinedLabel, Button, ...) or String(localized:) in App/**/*.swift has a row. Custom components that take `String`
   ship untranslated (memory localizedstringkey-not-string): add every custom text component to `callees`.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build  # noqa: E402  (tools/strings/build.py: TSV loader + specifier grammar)

APP = build.APP
CONFIG = os.path.join(HERE, "sources.json")

PH = "\x00"   # canonical placeholder


def canon(s):
    s = re.sub(r"\{\w+\}", PH, s)
    s = build.SPEC_RE.sub(PH, s)
    return s


def md_section(path, start, end):
    text = open(path, encoding="utf-8").read()
    if start not in text:
        raise KeyError(f"heading {start!r} not found in {os.path.relpath(path, APP)}")
    i = text.index(start)
    j = text.find(end, i + len(start)) if end else -1
    return text[i:j] if j >= 0 else text[i:]


def table_rows(section):
    for line in section.split("\n"):
        if line.startswith("|") and not re.match(r"^\|\s*:?-{3,}", line):
            yield [c.strip() for c in line.strip().strip("|").split("|")]


def unmd(s):
    return s.replace("\\n", "\n")


def _clean(s, src):
    for suf in src.get("strip_suffixes", []):
        s = s.replace(suf, "")
    s = unmd(s.strip())
    for k, v in src.get("substitute", {}).items():
        s = s.replace(k, v)
    sp = src.get("split")
    if sp:
        seps = [sp] if isinstance(sp, str) else sp
        parts = re.split("|".join(re.escape(x) for x in seps), s)
        return [p.strip() for p in parts if p.strip()]
    return [s] if s else []


def _pointer(obj, pointer):
    for part in [p for p in (pointer or "").split("/") if p]:
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    return obj


def source_strings(src):
    """[(where, text)] quoted by one sources.json entry, or raises FileNotFoundError / KeyError."""
    path = os.path.join(APP, src["path"])
    if not os.path.exists(path):
        raise FileNotFoundError(src["path"])
    kind = src["kind"]
    out = []
    if kind in ("json", "json-map"):
        data = _pointer(json.load(open(path, encoding="utf-8")), src.get("pointer"))
        items = data.items() if isinstance(data, dict) else enumerate(data)
        for k, v in items:
            if isinstance(v, dict):
                v = v.get(src.get("field", src["lang"]))
            if isinstance(v, str):
                for p in _clean(v, src):
                    out.append((f"{src['id']} {k}", p))
    elif kind == "md-table":
        sec = md_section(path, src["start"], src.get("end"))
        col, min_cols = src["col"], src.get("min_cols", src["col"] + 1)
        for cells in table_rows(sec):
            if len(cells) < min_cols or cells[0] == src.get("skip_header", "key"):
                continue
            for p in _clean(cells[col], src):
                out.append((f"{src['id']} {cells[0]}", p))
    elif kind == "md-quoted":
        sec = md_section(path, src["start"], src.get("end"))
        col = src.get("col")
        for cells in table_rows(sec):
            if cells[0] == src.get("skip_header", "key"):
                continue
            text = cells[col] if col is not None and col < len(cells) else " | ".join(cells)
            for q in re.findall(r'"([^"\n]+)"', text):
                for p in _clean(q, src):
                    out.append((f"{src['id']} {cells[0]}", p))
    elif kind == "md-blockquote":
        sec = md_section(path, src["start"], src.get("end"))
        label = re.compile(src["label"])
        take = False
        for line in sec.split("\n"):
            st = line.strip()
            if not st.startswith(">"):
                if st:
                    take = bool(label.search(st))
                continue
            para = st[1:].strip()
            if take and para:
                for p in _clean(para, src):
                    out.append((f"{src['id']}", p))
    else:
        raise KeyError(f"unknown source kind {kind!r}")
    return out


def regex_of(text_canon):
    """a spec INSTANCE of a format string: each placeholder stands for a number or ONE token (no whitespace), so
    "+30 sec" is an instance of "+%lld sec" but "+1 Live" is not an instance of "+%lld" (L1 fix: `.+?` matched phrases)"""
    parts = text_canon.split(PH)
    return re.compile("^" + r"(?:\d+|\S+?)".join(re.escape(p) for p in parts) + "$", re.S)


def spec_coverage(rows, cfg):
    by_lang = {}
    for lang in ("en", "tr"):
        texts = [canon(r[lang]) for r in rows]
        by_lang[lang] = (set(texts), {re.sub(r"\s+", " ", t) for t in texts}, [regex_of(t) for t in texts if PH in t])
    superseded = {k.replace("{}", PH): v for k, v in cfg.get("superseded", {}).items()}
    result = {"exact": [], "instance": [], "layout": [], "superseded": [], "missing": [], "no-source": []}
    seen = set()
    for src in cfg.get("spec_sources", []):
        try:
            strings = source_strings(src)
        except (FileNotFoundError, KeyError) as e:
            result["no-source"].append((src, str(e)))
            continue
        exact, squashed, regs = by_lang[src["lang"]]
        for where, text in strings:
            if (where, text) in seen:
                continue
            seen.add((where, text))
            c = canon(text)
            if c in exact:
                result["exact"].append((where, text))
            elif PH not in c and any(r.match(text) for r in regs):
                result["instance"].append((where, text))
            elif re.sub(r"\s+", " ", c) in squashed:
                result["layout"].append((where, text))
            elif c in superseded:
                result["superseded"].append((where, text, superseded[c]))
            else:
                result["missing"].append((where, text))
    return result


def data_keys(cfg):
    """[(where, key)] of every strings-table key in the bundled data files; None entries for missing files."""
    keys, missing = [], []
    for df in cfg.get("data_files", []):
        path = os.path.join(APP, df["path"])
        if not os.path.exists(path):
            missing.append(df["path"])
            continue
        data = json.load(open(path, encoding="utf-8"))
        wanted = set(df["keys"])

        def walk(o, where):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in wanted and isinstance(v, str):
                        keys.append((f"{os.path.basename(df['path'])} {where}.{k}", v))
                    else:
                        walk(v, f"{where}.{k}" if where else k)
            elif isinstance(o, list):
                for i, v in enumerate(o):
                    walk(v, f"{where}[{i}]")

        walk(data, "")
    return keys, missing


def literal_re(callees):
    names = "|".join(re.escape(c) for c in callees)
    return re.compile(r'(?:\b(?:' + names + r')\s*\(\s*(?:(?:text|marked|title|label|key|resource)\s*:\s*)?|'
                      r'String\s*\(\s*localized\s*:\s*|LocalizedStringResource\s*\(\s*)"((?:[^"\\\n]|\\.)*)"')


def swift_literal_to_key(lit):
    out, i = [], 0
    while i < len(lit):
        ch = lit[i]
        if ch == "\\" and i + 1 < len(lit):
            n = lit[i + 1]
            if n == "(":
                depth, j = 1, i + 2
                while j < len(lit) and depth:
                    depth += {"(": 1, ")": -1}.get(lit[j], 0)
                    j += 1
                out.append(PH)
                i = j
                continue
            out.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\", "'": "'"}.get(n, n))
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


IDENT_RE = re.compile(r"^[a-z][A-Za-z0-9_]*(?:[.:/-][A-Za-z0-9_\\()]+)*$")   # "hud.back", "door:\\(id)": ids, not copy


def labelled_re(labels):
    names = "|".join(re.escape(x) for x in labels)
    return re.compile(r'\b(?:' + names + r')\s*:\s*"((?:[^"\\\n]|\\.)*)"')


def code_coverage(rows, cfg):
    """Literals handed to a `callees` function, plus (L2) literals passed as a copy-carrying argument label (`labelled`:
    label:, title:, heading:, body: ... — GameButton(label:), PageChrome(title:), SettingsPopup sections) in the UI folders
    (`labelled.dirs`), skipping comments, lab/debug files and identifier-shaped literals ("hud.back")."""
    keyset = {canon(r["en"]) for r in rows}
    lit_re = literal_re(cfg.get("callees", ["Text", "Button", "Label", "Toggle", "LocalizedStringKey"]))
    lab = cfg.get("labelled", {})
    lab_re = labelled_re(lab["labels"]) if lab.get("labels") else None
    lab_dirs = [os.path.join(APP, d) for d in lab.get("dirs", [])]
    lab_skip = [re.compile(x) for x in lab.get("skip_files", [])]
    found, missing = [], []
    seen = set()
    app_dir = os.path.join(APP, "App")
    for root, _, files in os.walk(app_dir):
        for fn in files:
            if not fn.endswith(".swift"):
                continue
            path = os.path.join(root, fn)
            use_lab = lab_re is not None and any(path.startswith(d + os.sep) for d in lab_dirs) and \
                not any(x.search(fn) for x in lab_skip)
            for no, line in enumerate(open(path, encoding="utf-8"), start=1):
                if line.lstrip().startswith("//"):
                    continue
                if "verbatim:" in line:
                    line = re.sub(r'verbatim:\s*"(?:[^"\\]|\\.)*"', "", line)
                hits = [m.group(1) for m in lit_re.finditer(line)]
                if use_lab and "Log." not in line and "accessibilityIdentifier" not in line:
                    hits += [m.group(1) for m in lab_re.finditer(line) if not IDENT_RE.match(m.group(1))]
                for lit in hits:
                    key = swift_literal_to_key(lit)
                    if not re.search(r"[A-Za-z]", key.replace(PH, "")):
                        continue  # symbols, numbers, punctuation
                    where = f"{os.path.relpath(path, APP)}:{no}"
                    if (where, key) in seen:
                        continue
                    seen.add((where, key))
                    (found if canon(key) in keyset else missing).append((where, key))
    return found, missing


def main(argv):
    strict_code = "--strict-code" in argv
    report = argv[argv.index("--report") + 1] if "--report" in argv else None
    cfg_path = argv[argv.index("--config") + 1] if "--config" in argv else CONFIG
    tsv = argv[argv.index("--tsv") + 1] if "--tsv" in argv else build.TSV
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    if not os.path.exists(tsv):
        print(f"coverage: {tsv} not found (L1 writes it)", file=sys.stderr)
        return 1
    rows, errors, _notes = build.load_all(tsv, use_requests="--no-requests" not in argv)
    if errors:
        for e in errors:
            print("error:", e, file=sys.stderr)
        return 1
    lines = []

    def say(s=""):
        print(s)
        lines.append(s)

    res = spec_coverage(rows, cfg)
    total = sum(len(res[k]) for k in ("exact", "instance", "layout", "superseded", "missing"))
    say(f"SPEC coverage: {total} spec strings from {len(cfg.get('spec_sources', []))} sources -> exact "
        f"{len(res['exact'])}, instance {len(res['instance'])}, layout {len(res['layout'])}, superseded-by-measurement "
        f"{len(res['superseded'])}, MISSING {len(res['missing'])}")
    hard_no_source = []
    for src, why in res["no-source"]:
        optional = src.get("optional", False)
        say(f"  {'skipped  ' if optional else 'NO SOURCE'} {src['id']}: {why}"
            + ("" if optional else " (fix the file or tools/strings/sources.json)"))
        if not optional:
            hard_no_source.append(src["id"])
    for kind in ("instance", "layout"):
        for where, text in res[kind]:
            say(f"  {kind:9s} {text!r}  ({where})")
    for where, text, why in res["superseded"]:
        say(f"  superseded {text!r}  ({where}) -> {why}")
    for where, text in res["missing"]:
        say(f"  MISSING   {text!r}  ({where})")

    tk, dmissing = data_keys(cfg)
    en = {r["en"] for r in rows}
    tmissing = [(w, k) for w, k in tk if k not in en] + [(p, "(file not found)") for p in dmissing]
    say(f"DATA coverage: {len(tk)} keys in {len(cfg.get('data_files', []))} bundled data files, {len(tmissing)} without a row")
    for w, k in tmissing:
        say(f"  MISSING   {k!r}  ({w})")

    found, cmissing = code_coverage(rows, cfg)
    say(f"CODE coverage: {len(found) + len(cmissing)} English literals in App/**/*.swift, {len(found)} covered, "
        f"{len(cmissing)} without a row" + ("" if strict_code else " (report only)"))
    for w, k in cmissing:
        say(f"  no row    {k.replace(PH, '%?')!r}  ({w})")

    # 4. L10N coverage (hard; B3 L10N-APP): every catalogue key in the 11 language tables (EN + TR are strings.tsv)
    lmissing = []
    if "--en-tr-only" not in argv:
        tables, lerrors = build.load_l10n(en)
        for lang in build.LANGS:
            t = tables.get(lang, {})
            say(f"L10N coverage {lang:7s}: {len(t)}/{len(en)} keys" + ("" if len(t) == len(en) else "  INCOMPLETE"))
        for e in lerrors:
            say(f"  L10N error {e}")
        lmissing = lerrors
        say(f"L10N coverage: {2 + len(build.LANGS)} languages x {len(en)} keys, {len(lerrors)} problem(s)")

    if report:
        with open(report, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    bad = bool(res["missing"]) or bool(hard_no_source) or bool(tmissing) or (strict_code and bool(cmissing)) or bool(lmissing)
    say("coverage: FAIL" if bad else "coverage: OK")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
