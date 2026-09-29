#!/usr/bin/env python3
"""CONTENT (L2): the Turkish review gate for the strings table (SPEC-gameplay §16: "TR is natural casual-game Turkish").

    python3 -B tools/strings/tr_review.py [--report FILE] [--ctmeasure build/l2/bin/ctmeasure]

Reads the merged table exactly as tools/strings/build.py builds the catalogue (strings.tsv + requests/*.tsv, a strings.tsv
row wins). Hard checks (any finding -> exit 1):
  sen        the informal "sen" everywhere (the game talks to one player, casual register): no formal/plural
             second person ("-ınız/-iniz/-unuz/-ünüz", "siz", "sizin") and no plural imperatives of the game's verbs
             ("dokunun", "oynayın", "kazanın", ...).
  glossary   one Turkish word per game term, so the same thing is never called two names: coins = altın, lives and the
             in-level hearts = can, token = jeton, streak = seri, level = seviye, stage = aşama, booster = güçlendirici,
             shop = mağaza, hint = ipucu, leaderboard = sıralama; drifts that must not appear: "bölüm" (a level), "para"
             (coins), "hayat" / "kalp" (lives, hearts), "coin", "level", "booster", "bonus".
  punctuation a TR row ends with the EN row's closing "!", "?", ":" or "." (a short list of deliberate exceptions).
  suffix     no Turkish suffix glued to a placeholder ("%@'a", "%lld'den", "%lldye"): its vowel harmony would depend on the
             value the app fills in (the ruled d/h/m countdown units are the same glued letters in EN and TR).
  caps       an all-caps TR word keeps the Turkish I: flagged when a dotless "I" (ı) sits only with front vowels
             (E, İ, Ö, Ü) or a dotted "İ" only with back vowels (A, I, O, U) — "SEVIYE" / "KAPALİ" type mistakes.
  english    no TR row left in English (equal to its EN row while that has an English word).
  owner      OWNER 10:35 (SPEC.md §5.24): 0 hits for "simulat", "simüle" or "bot " in any EN or TR row.
  fit        every row whose EN is in SPEC-ui's measured string table (design/ui-crops/_tools/strings_fit.py `ROWS`: style
             size, tracking, text box, lines; read with ast, the design tool is never imported or written) and the extra
             layouts below is measured with the shipped font (design/fonts/PCDisplay-Black.ttf, CoreText through ctmeasure,
             exact ink width); the TR scale min(1, box / (width / lines x 1.12 for 2+ lines)) must be >= 0.70
             (SPEC.md §5.14). EN is reported.
"""
import ast
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import build  # noqa: E402

APP = build.APP
FIT_TABLE = os.path.join(APP, "design", "ui-crops", "_tools", "strings_fit.py")
FONT = os.path.join(APP, "design", "fonts", "PCDisplay-Black.ttf")
FLOOR = 0.70

# Layouts measured in code that SPEC-ui's table keys differently: (id, EN key, size, tracking, box, lines).
EXTRA_FIT = [
    # S2's Continue? token popup draws GP's one sentence as two lines (SPEC-ui §2.6.3: "You will lose **100** token" /
    # "and your streak!", 21.0 / -0.64 and 21.1 / -0.08, box 235; App/Shell/Popups/ContinuePopup.swift).
    ("continueToken.l1", "You will lose %lld tokens", 21.0, -0.64, 235, 1),
    ("continueToken.l2", "and your streak!", 21.1, -0.08, 235, 1),
    # the ruled GP strings in the layouts SPEC-ui measured for its own (superseded) wording (CONSISTENCY §16)
    ("booster.freezeDesc (GP)", "Freeze the timer for 10 seconds!", 21.0, -0.64, 270, 2),
    ("booster.hintDesc (GP)", "Find an arrow that can move!", 21.0, -0.64, 270, 2),
    ("page.terms (GP)", "Terms", 37.0, -1.19, 220, 1),
    ("page.privacy (GP)", "Privacy", 37.0, -1.19, 220, 1),
    ("rocket.offer (%lld)", "Beat %lld Levels before others to win and advance to next stages for greater prizes!", 14.6, -0.16, 290, 2),
    ("rocket.race (%lld)", "Beat %lld levels before others to finish the race", 19.7, -0.38, 345, 2),
    # A1 (T1 W1 merge): the Special Offer's STARTER ribbon (ruling 38) — ONE key in ONE run, 15.5 pt / +0.4 in a 98 pt box
    # (App/Shell/Shop/ShopView.swift StarterRibbon; was the "90% OFF" seal's two runs in a 46 pt box). The ad toast row is gone
    # with the rewarded-ad button (owner item 9).
    ("shop.starter", "STARTER", 15.5, 0.4, 98, 1),
    # T1's own event names in the layouts SPEC-ui measured for the names they replace (ruling 38; same size, box and lines)
    ("profile.weeklyWins (T1)", "Weekly Cup Wins", 14.2, -0.34, 165, 1),
    ("profile.streakWins (T1)", "Hot Streak Wins", 14.0, -0.2, 165, 1),
    ("profile.rocketWins (T1)", "Rocket Rally Wins", 14.0, -0.2, 165, 1),
    ("profile.skyWins (T1)", "Cloud Hop Wins", 14.0, -0.2, 165, 1),
    ("profile.clawWins (T1)", "Treasure Climb Wins", 14.0, -0.2, 165, 1),
    ("lb.locked (T1)", "Reach level 50 to join the Weekly Cup!", 26.0, -0.5, 330, 3),
    ("weekly.title (T1)", "Weekly Cup", 32.8, 0.0, 330, 1),
    ("weekly.tut (T1)", "Tap to join the Weekly Cup!", 26.0, -1.0, 250, 2),
    ("weekly.compete1 (T1)", "The top 3 win prizes!", 16.0, 0.0, 280, 1),
    ("streak.title (T1)", "Hot Streak", 45.0, -1.0, 290, 1),
    ("claw.title (T1)", "Treasure Climb", 45.0, -1.0, 300, 1),
    ("rocket.title (T1)", "Rocket Rally", 45.0, -1.0, 260, 1),
    ("sky.title (T1)", "Cloud Hop", 45.0, -1.0, 250, 1),
]

FORMAL = re.compile(r"\b\w+(?:ınız|iniz|unuz|ünüz)\b|\bsiz(?:in|e|i|den)?\b", re.I)
PLURAL_IMPERATIVE = re.compile(
    r"\b(?:dokun|oyna|kazan|geç|yaz|dene|topla|temizle|aç|bekle|katıl|yarış|ilerle|bul|kaydet|kopyala|başla|bitir|artır|"
    r"doldur|ekle|dondur|geçir|kaybet|dön|seç|düzenle|oluştur|al)(?:ın|in|un|ün|yın|yin|yun|yün)\b", re.I)
# (English term regex, the Turkish stem it must use)
GLOSSARY = [
    (r"\bcoins?\b", "altın"),
    (r"\blives?\b|\bhearts?\b", "can"),
    (r"\btokens?\b", "jeton"),
    (r"\bstreak\b", "seri"),
    (r"\blevels?\b", "seviye"),
    (r"\bstages?\b", "aşama"),
    (r"\bboosters?\b", "güçlendirici"),
    (r"\bshop\b", "mağaza"),
    (r"\bhint\b", "ipucu"),
    (r"\bleaderboards?\b", "sıralama"),
]
# EN rows whose ruled TR drops the term on purpose (the reason is the ruling).
GLOSSARY_EXEMPT = {
    # ruled drops (CONSISTENCY §16, SPEC.md §5.21-22): the fitted variant leaves the term out
    "Quit Level?": "S-2: UI's \"Çıkılsın mı?\" (GP's \"Seviyeden Çık?\" fails the 0.70 floor)",
    "Beat %lld Levels before others to win and advance to next stages for greater prizes!": "S-30: UI's listed rewording",
}
BANNED = [r"\bbölüm", r"\bpara\b", r"\bhayat", r"\bkalp", r"\bcoin", r"\blevel", r"\bbooster", r"\bbonus"]
PUNCT_EXCEPT = {
    "Write to us at",                     # TR needs the colon before the address: "Bize şu adresten yazabilirsin:"
    "%lld levels!",                       # SOC2 highlight RUN, never shown alone: EN lights "N levels!" at the end of "Beat N
                                          # levels!", TR lights "N seviye" inside "N seviye geç!" (the "!" closes the unlit verb)
}
BACK, FRONT = set("AIOU"), set("EİÖÜ")
OWNER_BANNED = ("simulat", "simüle", "bot ")


def turkish_lower(s):
    return s.replace("I", "ı").replace("İ", "i").lower()


def placeholder_free(s):
    return build.SPEC_RE.sub("", s)


def ink_text(s):
    s = re.sub(r"%(?:\d+\$)?lld", "100", s)
    s = re.sub(r"%(?:\d+\$)?@", "Turkey", s)
    return s.replace("**", "")


def fit_rows():
    tree = ast.parse(open(FIT_TABLE, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "ROWS":
            return [(k, en, size, track, box, lines) for k, en, _tr, size, track, box, lines in ast.literal_eval(node.value)]
    raise SystemExit("tr_review: ROWS not found in %s" % FIT_TABLE)


def measure(jobs, ctmeasure):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(jobs, f)
        path = f.name
    try:
        out = subprocess.run([ctmeasure, path], capture_output=True, text=True, check=True).stdout
    finally:
        os.unlink(path)
    return {j["id"]: j for j in (json.loads(line) for line in out.strip().split("\n") if line.strip())}


def main(argv):
    report = argv[argv.index("--report") + 1] if "--report" in argv else None
    ctm = argv[argv.index("--ctmeasure") + 1] if "--ctmeasure" in argv else os.path.join(APP, "build", "l2", "bin", "ctmeasure")
    rows, errors, _notes = build.load_all()
    if errors:
        for e in errors:
            print("error:", e)
        return 1
    hard, lines = [], []

    def say(s=""):
        print(s)
        lines.append(s)

    for r in rows:
        en, tr = build.english(r["en"]), r["tr"]                   # FIX-2 B: an identifier key reads its English (keys.tsv)
        where = "%s %r" % ("requests/%s.tsv" % r["role"] if r.get("role") else "strings.tsv", r["en"][:60])
        low = turkish_lower(tr)
        # sen
        for m in FORMAL.finditer(tr):
            hard.append("sen: formal/plural second person %r in TR %r (%s)" % (m.group(0), tr, where))
        for m in PLURAL_IMPERATIVE.finditer(tr):
            hard.append("sen: plural imperative %r in TR %r (%s)" % (m.group(0), tr, where))
        # glossary
        for pat, stem in GLOSSARY:
            if re.search(pat, en, re.I) and en not in GLOSSARY_EXEMPT and stem not in low:
                hard.append("glossary: EN has %s but TR %r lacks %r (%s)" % (pat, tr, stem, where))
        for pat in BANNED:
            if re.search(pat, low):
                hard.append("glossary: TR %r uses %s (%s)" % (tr, pat, where))
        # punctuation
        e_end, t_end = en.rstrip()[-1:], tr.rstrip()[-1:]
        if e_end in "!?:." and e_end != t_end and en not in PUNCT_EXCEPT:
            hard.append("punctuation: EN ends %r, TR %r ends %r (%s)" % (e_end, tr, t_end, where))
        # suffix glued to a placeholder
        for m in re.finditer(r"(%(?:\d+\$)?(?:lld|@))(['’]?[a-zçğıöşü]+)", tr):
            glued = re.sub(r"%\d+\$", "%", m.group(0))
            if glued not in re.sub(r"%\d+\$", "%", en):
                hard.append("suffix: %r glued to a placeholder in TR %r (%s)" % (m.group(0), tr, where))
        # caps and the Turkish I
        for w in re.findall(r"[A-ZÇĞİÖŞÜ]{2,}", placeholder_free(tr)):
            vowels = [ch for ch in w if ch in BACK | FRONT]
            if "I" in w and vowels and all(v in FRONT or v == "I" for v in vowels) and any(v in FRONT for v in vowels):
                hard.append("caps: %r has a dotless I among front vowels (%s)" % (w, where))
            if "İ" in w and vowels and all(v in BACK or v == "İ" for v in vowels) and any(v in BACK - {"I"} for v in vowels):
                hard.append("caps: %r has a dotted İ among back vowels (%s)" % (w, where))
        # untranslated
        words = re.findall(r"[A-Za-z]{2,}", placeholder_free(en))
        if tr == en and words:
            hard.append("english: TR row identical to EN %r (%s)" % (en, where))
        # owner 10:35
        for s in (en, tr):
            for b in OWNER_BANNED:
                if b in s.lower():
                    hard.append("owner 10:35: %r in %r (%s)" % (b, s, where))

    # fit with the shipped font
    by_en = {r["en"]: r for r in rows}
    table = [(k, en, size, track, box, n, None) for k, en, size, track, box, n in fit_rows()] + \
        [tuple(x) + (None,) * (7 - len(x)) for x in EXTRA_FIT]
    measured = [x for x in table if x[1] in by_en]
    skipped = sorted({x[1] for x in table if x[1] not in by_en})

    def run(text, part):
        return text if part is None else text.split(" ", 1)[part]
    fit = []
    if not os.path.exists(ctm):
        hard.append("fit: ctmeasure not built at %s (xcrun swiftc -O -o %s design/ui-crops/_tools/ctmeasure.swift)" % (ctm, ctm))
    else:
        jobs = []
        for k, en, size, track, box, n, part in measured:
            for lang, text in (("en", en), ("tr", by_en[en]["tr"])):
                jobs.append({"id": "%s|%s" % (k, lang), "font": FONT, "text": ink_text(run(text, part)), "size": size, "track": track})
        res = measure(jobs, ctm)
        for k, en, size, track, box, n, part in measured:
            sc = {}
            for lang in ("en", "tr"):
                v = res["%s|%s" % (k, lang)]
                w = v["inkX1"] - v["inkX0"]
                eff = w / n * (1.12 if n > 1 else 1.0)
                sc[lang] = round(min(1.0, box / eff), 2) if eff > 0 else 1.0
            fit.append((k, run(en, part), run(by_en[en]["tr"], part), size, box, n, sc["en"], sc["tr"]))
            if sc["tr"] < FLOOR:
                hard.append("fit: TR %r needs scale %.2f in %s (%d pt box, %d line(s)); floor %.2f" % (by_en[en]["tr"], sc["tr"], k, box, n, FLOOR))

    say("tr_review: %d rows (strings.tsv + requests), %d measured for fit with PCDisplay-Black (%d SPEC-ui layouts not in the "
        "table: superseded variants), floor %.2f" % (len(rows), len(fit), len(skipped), FLOOR))
    low_fit = sorted(fit, key=lambda x: x[7])[:12]
    say("  tightest TR fits: " + "; ".join("%s %r %.2f" % (k, tr, s) for k, _en, tr, _s, _b, _n, _se, s in low_fit))
    for k, en, tr, size, box, n, se, st in fit:
        lines.append("  fit %-28s EN %.2f  TR %.2f  %r / %r (%.1f pt, %d pt, %d line)" % (k, se, st, en, tr, size, box, n))
    say("tr_review: %d finding(s)" % len(hard))
    for h in hard:
        say("FAIL " + h)
    if report:
        with open(report, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
