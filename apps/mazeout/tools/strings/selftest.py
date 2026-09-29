#!/usr/bin/env python3
"""selftest.py — negative controls for tools/strings/build.py and coverage.py (CONTENT, L1). Each mutation of the real
strings.tsv / requests must be REJECTED (build error or coverage FAIL); the two legal cases must be accepted.

    python3 tools/strings/selftest.py        -> prints CAUGHT / MISSED per case, exit 1 on any MISSED
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build  # noqa: E402
import coverage  # noqa: E402

REAL = open(build.TSV, encoding="utf-8").read()
CFG = json.load(open(coverage.CONFIG, encoding="utf-8"))


def run(tsv_text, requests=None, check_coverage=False):
    """-> (build errors, notes, coverage missing count or None, merged rows)"""
    d = tempfile.mkdtemp()
    try:
        tsv = os.path.join(d, "strings.tsv")
        open(tsv, "w", encoding="utf-8").write(tsv_text)
        rq = os.path.join(d, "requests")
        os.makedirs(rq)
        src = requests if requests is not None else {
            f: open(os.path.join(build.REQUESTS, f), encoding="utf-8").read()
            for f in os.listdir(build.REQUESTS) if f.endswith(".tsv")}
        for name, text in src.items():
            open(os.path.join(rq, name), "w", encoding="utf-8").write(text)
        rows, errors, notes = build.load_all(tsv, rq)
        miss = None
        if check_coverage and not errors:
            res = coverage.spec_coverage(rows, CFG)
            keys, _ = coverage.data_keys(CFG)
            en = {r["en"] for r in rows}
            miss = len(res["missing"]) + sum(1 for _, k in keys if k not in en)
        return errors, notes, miss, rows
    finally:
        shutil.rmtree(d)


def replace_row(text, en, new_line):
    out = []
    for line in text.split("\n"):
        out.append(new_line if line.split("\t")[0] == en else line)
    return "\n".join(out)


def drop_row(text, en):
    return "\n".join(l for l in text.split("\n") if l.split("\t")[0] != en)


H = "en\ttr\tcontext\n"
cases = []
# must be REJECTED
cases.append(("TR swaps two arguments of different types without positions",
              lambda: run(REAL + "\nVersion %@ · Build %lld\tDerleme %lld · Sürüm %@\ttest\n"), "error"))
cases.append(("TR drops an argument", lambda: run(replace_row(REAL, "Level %lld", "Level %lld\tSeviye\ttest")), "error"))
cases.append(("TR mixes positional and plain specifiers",
              lambda: run(REAL + "\nA %lld of %lld\t%2$lld içinden %lld\ttest\n"), "error"))
cases.append(("a literal brand name in a row", lambda: run(REAL + "\nWelcome to Arrow Out!\tArrow Out'a hoş geldin!\ttest\n"),
              "error"))
cases.append(("a duplicate key", lambda: run(REAL + "\nPlay\tOyna\tduplicate\n"), "error"))
cases.append(("unbalanced ** run markers", lambda: run(REAL + "\nPass the **PIPE\tBORU**\ttest\n"), "error"))
cases.append(("two request files disagree on a key",
              lambda: run(REAL, {"game.tsv": H + "Hello there\tMerhaba\tg\n", "board.tsv": H + "Hello there\tSelam\tb\n"}),
              "error"))
cases.append(("the tutorial caption row removed (spec + data coverage)",
              lambda: run(drop_row(REAL, "Tap to move!"), check_coverage=True), "coverage"))
cases.append(("Quit Level? given GP's loser TR (the ruled winner must ship)",
              lambda: run(replace_row(REAL, "Quit Level?", "Quit Level?\tSeviyeden Çık?\ttest"), check_coverage=True), "coverage"))
cases.append(("an unlock card row removed", lambda: run(drop_row(REAL, "Collect the KEY to open the DOOR!"), check_coverage=True),
              "coverage"))
# A1 (T1 W1 merge): the paragraph used here is one the spec still quotes verbatim — the old "The game works offline.
# Purchases are handled by Apple." is superseded by T1 (release-plan §2.5 S-7), so dropping it proves nothing any more.
cases.append(("a Terms/Privacy paragraph removed (GP §16.10 blockquote source)",
              lambda: run(drop_row(REAL, "Your progress, settings and profile name are stored only on this device."), {},
                          check_coverage=True),
              "coverage"))
# must be ACCEPTED
cases.append(("legal: TR reorders with positional specifiers",
              lambda: run(REAL + "\nVersion %@ · Build %lld\tDerleme %2$lld · Sürüm %1$@\ttest\n", check_coverage=True), "ok"))
cases.append(("legal: a request row overridden by strings.tsv (a note, strings.tsv wins)",
              lambda: run(REAL, {"game.tsv": H + "Play\tOynat\tg\n"}), "ok-note"))

# B3 L10N-APP: the 11 language tables (l10n/strings.<lang>.tsv) — a mutated copy of the REAL tables must be rejected
L10N_REAL = {lang: open(os.path.join(build.L10N, "strings.%s.tsv" % lang), encoding="utf-8").read() for lang in build.LANGS}
KEYS = {r["en"] for r in build.load_all()[0]}


def run_l10n(mutate):
    """-> (errors, notes, None, rows) of build.load_l10n on the real tables with `mutate(lang, text) -> text` applied."""
    d = tempfile.mkdtemp()
    try:
        for lang, text in L10N_REAL.items():
            open(os.path.join(d, "strings.%s.tsv" % lang), "w", encoding="utf-8").write(mutate(lang, text))
        _tables, errors = build.load_l10n(KEYS, d)
        return errors, [], None, []
    finally:
        shutil.rmtree(d)


def l10n_row(lang, en, value):
    def mutate(l, text):
        if l != lang:
            return text
        out = replace_row(text, en, "%s\t%s\tselftest" % (en, value))
        assert out != text, "selftest: %r is not a row of the %s table (the mutation would be vacuous)" % (en, lang)
        return out
    return mutate


cases.append(("l10n: a key missing from the German table",
              lambda: run_l10n(lambda l, t: drop_row(t, "Tap to move!") if l == "de" else t), "error"))
cases.append(("l10n: a stale key (not in the catalogue) in the Korean table",
              lambda: run_l10n(lambda l, t: t + "Stale key\t오래된 키\tselftest\n" if l == "ko" else t), "error"))
cases.append(("l10n: Japanese drops the %lld of 'Level %lld'", lambda: run_l10n(l10n_row("ja", "Level %lld", "レベル")), "error"))
cases.append(("l10n: Polish swaps two argument types without positions",
              lambda: run_l10n(l10n_row("pl", "Version %@ · Level %lld", "Poziom %lld · Wersja %@")), "error"))
cases.append(("l10n: an unbalanced ** run in the Chinese unlock card",
              lambda: run_l10n(l10n_row("zh-Hans", "Pass arrows through the PIPE to break it!", "让箭头穿过**管道来打破它！")), "error"))
cases.append(("l10n: a literal brand name in the French table",
              lambda: run_l10n(l10n_row("fr", "Play", "Jouer à Arrow Out")), "error"))
cases.append(("l10n: a table without its header",
              lambda: run_l10n(lambda l, t: t.split("\n", 1)[1] if l == "sl" else t), "error"))
cases.append(("l10n: the Slovak table missing altogether",
              lambda: run_l10n(lambda l, t: "" if l == "sk" else t), "error"))
cases.append(("legal: l10n Italian reorders two arguments with positions",
              lambda: run_l10n(l10n_row("it", "Version %@ · Level %lld", "Livello %2$lld · Versione %1$@")), "l10n-ok"))
cases.append(("legal: the real 11 tables", lambda: run_l10n(lambda l, t: t), "l10n-ok"))


# FIX-2 lane B (B1b-r3): identifier keys (keys.tsv) — an identifier row with no English text, a keys.tsv key with no row
def run_keyed(tsv_text, keyed):
    d = tempfile.mkdtemp()
    try:
        tsv = os.path.join(d, "strings.tsv")
        open(tsv, "w", encoding="utf-8").write(tsv_text)
        rows, errors, notes = build.load_all(tsv, os.path.join(d, "none"))
        return errors + build.check_keyed(rows, keyed), notes, None, rows
    finally:
        shutil.rmtree(d)


cases.append(("keys: an identifier-looking key with no English text in keys.tsv",
              lambda: run_keyed(REAL + "event.ended\tBitti\tselftest\n", dict(build.KEYED)), "error"))
cases.append(("keys: a keys.tsv key with no strings.tsv row",
              lambda: run_keyed(REAL, dict(build.KEYED, **{"event.gone": "Gone"})), "error"))
cases.append(("keys: a keyed English text that takes other arguments than its key",
              lambda: run_keyed(REAL, dict(build.KEYED, **{"event.finished": "Finished %lld"})), "error"))
cases.append(("legal: the real keys.tsv", lambda: run_keyed(REAL, dict(build.KEYED)), "l10n-ok"))

caught = 0
for name, fn, want in cases:
    errors, notes, miss, rows = fn()
    if want == "error":
        ok = bool(errors)
        detail = errors[0] if errors else "accepted"
    elif want == "coverage":
        ok = bool(errors) or (miss or 0) > 0
        detail = "coverage missing %s" % miss if not errors else errors[0]
    elif want == "ok":
        ok = not errors and miss == 0
        detail = "accepted, coverage missing %s" % miss if not errors else errors[0]
    elif want == "l10n-ok":
        ok = not errors
        detail = "accepted" if not errors else errors[0]
    else:
        ok = not errors and any("overridden" in n for n in notes) and \
            next(r["tr"] for r in rows if r["en"] == "Play") == "Oyna"
        detail = notes[0] if notes else "no note"
    caught += ok
    label = ("CAUGHT" if want in ("error", "coverage") else "OK    ") if ok else ("MISSED" if want in ("error", "coverage") else "WRONG ")
    print("%s %s  [%s]" % (label, name, detail[:110]))
print("strings selftest: %d/%d cases behave as required" % (caught, len(cases)))
sys.exit(0 if caught == len(cases) else 1)
