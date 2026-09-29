#!/usr/bin/env python3
"""B3 L10N-APP (PLAN-P §4.4, gate G7): the review gate for ALL 13 languages of the strings table — tr_review.py's rules
generalised (tr_review.py stays the Turkish grammar gate: sen, the TR glossary, the Turkish I).

    python3 -B tools/strings/l10n_review.py [--report FILE] [--ctfit build/strings/bin/ctfit] [--langs de,ja] [--export-frames]

Reads the table exactly as tools/strings/build.py builds the catalogue (strings.tsv + requests/*.tsv for EN/TR, the 11
tables App/Resources/Strings/l10n/strings.<lang>.tsv for the rest). Hard checks (any finding -> exit 1), per language:
  honesty    no user-facing text claims online play, multiplayer, bots, friends or simulated players (SPEC.md §5.24
             OWNER 10:35 + ruling 38 "drop 'Compete against your friends!'"): a per-language list of the words (online,
             en ligne, オンライン, 온라인, 在线, simul*, マルチ, 多人, bot, ボット, 봇, 机器人, friends/amis/友達/친구/好友 …).
  brand      no Maze Out / Grand Games / Arrow Jam / Tap Away / v552 in any cell (build.py already bans the literal brands).
  runs       every highlight run (a SocTwoLines `hot:` key) is a substring of its host sentence in the same language
             (case-insensitive; the app lights it with localizedCaseInsensitiveContains).
  split      "You will lose %lld tokens" + "and your streak!" concatenate to the full sentence (no space in ja / zh-Hans).
  unlock     every unlock card lights its term: a CAPS word in the cased languages, a `**…**` run in ja / ko / zh-Hans;
             no mixed-case word hides a CAPS run ("l'ASCENSEUR").
  markers    `**` appears ONLY in the unlock cards (the only layout that draws runs from markers; anywhere else it would
             show as asterisks).
  spanish    a Spanish "!" / "?" sentence opens with "¡" / "¿" (highlight runs and split halves excepted).
  french     no plain space before ! ? : ; (French typography uses a no-break space, U+00A0; PC Display has no U+202F).
  fit        every measured layout (SPEC-ui's table design/ui-crops/_tools/strings_fit.py ROWS + tr_review.EXTRA_FIT + the
             B3 rows below) in every language, measured with PC Display AND the app's bold fallback cascade (ctfit:
             the faces and per-string CJK order of GameText.swift FontCascade): scale min(1, box / (ink / lines x 1.12
             for 2+ lines)) >= 0.70 (SPEC.md §5.14). The exact line breaks (LineUnits) are measured in the simulator by
             Tests/AppTests/L10nTests.swift (build/p/B3/fit.json); this is the fast, font-exact first gate.
Reported, not gating: the end punctuation of each row against EN; the tightest fits per language.
--export-frames writes tools/strings/fit_frames.json (the same frame list, for L10nTests.swift).
"""
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
import tr_review  # noqa: E402

APP = build.APP
FONT = tr_review.FONT
FLOOR = 0.70
LANGS = ["en", "tr"] + build.LANGS
CASELESS = {"ja", "ko", "zh-Hans"}
NOSPACE = {"ja", "zh-Hans"}
FRAMES_JSON = os.path.join(HERE, "fit_frames.json")
T1_CHANGES = os.path.join(APP, "design", "publish", "l10n", "T1-changes.tsv")

# B3: the layouts of the keys added after T1 (sizes / boxes read from the code that draws them)
B3_FIT = [
    ("balloon.info2 (B1)", "Every stop has a reward!", 16.0, 0.0, 170, 2),                       # BalloonViews SocTwoLines
    ("balloon.redCard (B1)", "If you fail a level, you fall back to the ground!", 16.4, 0.0, 249, 2),  # SocWarningCard 321-72
    ("balloon.collected (B1)", "Already collected!", 15.0, -0.3, 136, 1),                        # BalloonBubble maxWidth 136
    ("profile.upAway (B1)", "Up & Away Best Streak", 13.9, -0.25, 165, 1),                       # ProfileView stat label
    # the booster popup's "Buy" + "x3" group (BoosterBuyPopup.groupScale: both shrink in 118 pt): "Buy"'s share of the group
    # = 118 - 4 - the "x3" frame (~33 pt) - its own outline pads (~6 pt) ≈ 84 pt of ink (B3: it was unmeasured; T2 ratio 2.16)
    ("boosterBuy.buy (B3)", "Buy", 35.5, -0.92, 84, 1),
    # small boxes found by the B3 in-app sweep (FitLedger) that SPEC-ui's table does not list
    ("raceBar.plate (B3)", "Rocket Rally", 17.8, -0.31, 113.1, 1),                                # RaceBar RacePlate 123.1 - 10
    ("home.eventBadge.join (B3)", "Join", 10.8, -0.3, 50, 1),                                     # EventBadges pedestal
    # FIX-2 B (B1b-r3): the ENDED event's word is its own key (keys.tsv) — the lives pill keeps "Finished" (home.livesFinished)
    ("home.eventBadge.finished (B1b)", "event.finished", 13.0, -0.35, 44, 1),                     # ui.json finishedMaxWidth 44
    ("home.clawTimerChip.finished (B1b)", "event.finished", 16.3, -0.3, 47, 1),                   # ui.json finishedMaxWidth 47
    ("page.timerChip.finished (FIX-2 B)", "event.finished", 15.4, -0.3, 56, 1),                   # SocialShells PageTimerChip
    ("claw.timerChip.finished (FIX-2 B)", "event.finished", 12.32, -0.49, 46.3, 1),               # ClawScreen EventTimerChip 67.7 x 23
    # in-app boxes narrower than SPEC-ui's measured ones (the sweep's FitLedger found them)
    ("pause.sound (in-app)", "Sound", 25.5, 0.0, 87.5, 1),                                       # PausePopup toggle.minX - left - 6
    ("pause.haptic (in-app)", "Haptic", 25.5, 0.0, 87.5, 1),
    ("moreLives.refill (in-app)", "Refill", 35.5, -0.92, 95.3, 1),                               # PriceButton coin.minX - face - 14
    ("moreLives.next (B3 250)", "Time to next life:", 25.4, -0.7, 250, 1),                        # inside the 261.6 pt cream card
    ("streak.info3 (in-app)", "Earn more flags than others!", 16.0, 0.0, 130, 2),                  # StreakRaceViews SocTwoLines box 130
    ("home.newRibbon (B1)", "NEW", 11.0, -0.2, 34, 1),                                            # BalloonBar NEW capsule
]

# B3: layouts whose shipped box differs from SPEC-ui's measured one (the app's ui.json wins): the Settings Terms / Privacy
# pills' label box 95 -> 97 pt (ui.json text.settings.link.maxWidth; the pill art is unchanged at 121.8 pt): the German
# 'Datenschutz' needs 95.4 pt at the 0.70 floor and German has no shorter native word (T2 open issue).
BOX_OVERRIDES = {"settings.terms": 97, "settings.privacy": 97}

# SocTwoLines highlight runs: run key -> host keys (T2 build/p/T2/work/l10n_tool.py HOT + B1's red card)
HOT = {
    "%lld Levels": ["Beat %lld Levels before others to win and advance to next stages for greater prizes!",
                    "Pass %lld Levels in a row on first try and advance to next stages!"],
    "%lld levels": ["Beat %lld levels before others to finish the race"],
    "%lld levels!": ["Beat %lld levels!"],
    "100 players": ["Start with 100 players!"],
    "%lld coins": ["Win your share of %lld coins!"],
    "greater prizes": ["Advance to next stages for greater prizes!"],
    "prizes": ["Advance to next stages for greater prizes!"],
    "rewards": ["Win amazing rewards!"],
    "Rewards!": ["Win Rewards!"],
    "fail": ["If you fail a level the multiplier will reset!", "If you fail a level, you will fail the challenge!",
             "If you fail a level, a balloon pops!", "If you fail a level, you fall back to the ground!"],
    "hot air": ["Beat levels to fill your balloons with hot air!"],
    "Hard levels": ["Hard levels give more hot air!"],
    "big prize": ["Reach the top for the big prize!"],
}
SPLIT = ("You will lose %lld tokens", "and your streak!", "You will lose %lld tokens and your streak!")
UNLOCK_CARDS = [
    "LINKED ARROWS move together!", "Clear required amount of arrows to break the BOX!",
    "Pass arrows through the PIPE to break it!", "Clear all arrows on the ELEVATOR to activate it!",
    "Collect the KEY to open the DOOR!", "The CORNER turns arrows around!", "Arrows turn when they hit the CORNER!",
]
BRAND_RE = re.compile(r"\bmaze\s*out|\bmazeout|grand\s*games|arrow\s*jam|tap\s*away|tapaway|v552", re.I)
# honesty: substrings (case-insensitive) that would claim a real online world. Common to all + per language.
HONESTY_ALL = ["simul", "symul", "online", "on-line", "multiplayer", "multi-player", "bot ", "bots", "friend"]
HONESTY = {
    "en": [], "tr": ["simüle", "çevrimiçi", "arkadaş", "çok oyunculu"],
    "de": ["freund", "mehrspieler"], "fr": ["en ligne", "ami", "multijoueur"], "es": ["en línea", "amigo", "multijugador"],
    "it": ["in linea", "amic", "multigiocatore"], "pt-BR": ["amigo", "multijogador"],
    "ja": ["オンライン", "シミュレ", "マルチ", "ボット", "友達", "友だち", "フレンド", "対戦"],
    "ko": ["온라인", "시뮬", "멀티", "봇", "친구"],
    "zh-Hans": ["在线", "联网", "模拟", "多人", "机器人", "好友", "朋友"],
    "pl": ["znajom", "przyjaci", "wieloosob"], "sk": ["priatel", "kamarát", "viac hráč"], "sl": ["prijatelj", "splet", "večigral"],
}
# French "ami" only as a word (ami, amie, amis, amies), never inside "dynamique" / "famille"
FR_AMI_RE = re.compile(r"\bami(e|s|es)?\b", re.I)


def ink_text(s):
    s = re.sub(r"%(?:\d+\$)?lld", "100", s)
    s = re.sub(r"%(?:\d+\$)?@", "Turkey", s)
    return s.replace("**", "")


def aliases():
    """T1 'replace' rows: old key -> new key (a renamed key is measured in its predecessor's frame, as T2 did)."""
    out = {}
    if os.path.exists(T1_CHANGES):
        for line in open(T1_CHANGES, encoding="utf-8").read().split("\n")[1:]:
            c = line.split("\t")
            if len(c) >= 3 and c[0] == "replace":
                out[build.unescape(c[1])] = build.unescape(c[2])
    return out


def frames(keys):
    """[(id, en key, size, tracking, box, lines)] of every measured layout whose key ships (renamed keys via T1 aliases)."""
    al = aliases()
    table = [(k, en, size, track, box, n) for k, en, size, track, box, n in tr_review.fit_rows()] + \
        [tuple(x[:6]) for x in tr_review.EXTRA_FIT] + B3_FIT
    out, seen = [], set()
    for k, en, size, track, box, n in table:
        if en not in keys and en in al and al[en] in keys and al[en] != "STARTER":
            k, en = k + " [T1 key]", al[en]
        if en in keys and (k, en) not in seen:
            seen.add((k, en))
            out.append((k, en, size, track, BOX_OVERRIDES.get(k, box), n))
    return out


def measure(jobs, ctfit):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(jobs, f)
        path = f.name
    try:
        out = subprocess.run(["nice", "-n", "10", ctfit, path], capture_output=True, text=True, check=True).stdout
    finally:
        os.unlink(path)
    return {j["id"]: j for j in (json.loads(line) for line in out.strip().split("\n") if line.strip())}


def is_caps(w):  # UnlockOverlay MultiRunText.isCaps
    letters = [c for c in w if c.isalpha()]
    s = "".join(letters)
    return len(letters) >= 2 and s == s.upper() and s != s.lower()


def main(argv):
    report = argv[argv.index("--report") + 1] if "--report" in argv else None
    ctfit = argv[argv.index("--ctfit") + 1] if "--ctfit" in argv else os.path.join(APP, "build", "strings", "bin", "ctfit")
    langs = argv[argv.index("--langs") + 1].split(",") if "--langs" in argv else LANGS
    rows, errors, _ = build.load_all()
    tables, lerr = build.load_l10n({r["en"] for r in rows})
    if errors or lerr:
        for e in errors + lerr:
            print("error:", e)
        return 1
    V = {"en": {r["en"]: build.english(r["en"]) for r in rows}, "tr": {r["en"]: r["tr"] for r in rows}}   # FIX-2 B: keys.tsv
    V.update(tables)
    keys = [r["en"] for r in rows]
    fr = frames(set(keys))
    if "--export-frames" in argv:
        with open(FRAMES_JSON, "w", encoding="utf-8") as f:
            json.dump({"about": "B3 L10N-APP: the measured text layouts (id, EN key, size pt, tracking pt, box pt, lines) of every "
                                "shipped key; generated by tools/strings/l10n_review.py --export-frames from SPEC-ui's "
                                "strings_fit.py ROWS + tr_review.EXTRA_FIT + l10n_review.B3_FIT; read by Tests/AppTests/L10nTests.swift",
                       "floor": FLOOR,
                       "frames": [{"id": k, "key": en, "size": size, "track": track, "box": box, "lines": n}
                                  for k, en, size, track, box, n in fr]},
                      f, ensure_ascii=False, indent=1)
            f.write("\n")
        print("wrote", os.path.relpath(FRAMES_JSON, APP), len(fr), "frames")
    hard, soft = [], []
    for lang in langs:
        T = V[lang]
        for en in keys:
            v = T[en]
            low = v.lower()
            where = "%s %r" % (lang, en[:50])
            if BRAND_RE.search(v):
                hard.append("brand: %s -> %r" % (where, v))
            for b in HONESTY_ALL + HONESTY.get(lang, []):
                if b.lower() in low:
                    if lang == "fr" and b == "ami" and not FR_AMI_RE.search(v):
                        continue
                    hard.append("honesty: %r in %s -> %r" % (b, where, v))
            if "**" in v and en not in UNLOCK_CARDS:
                hard.append("markers: ** outside an unlock card in %s -> %r (only the unlock card draws marked runs)" % (where, v))
            if lang == "es" and en not in HOT and en not in SPLIT[:2]:
                if v.endswith("!") and "¡" not in v:
                    hard.append("spanish: '!' without '¡' in %s -> %r" % (where, v))
                if v.endswith("?") and "¿" not in v:
                    hard.append("spanish: '?' without '¿' in %s -> %r" % (where, v))
            if lang == "fr" and re.search(r" [!?:;]", v):
                hard.append("french: a plain space before ! ? : ; in %s -> %r (use U+00A0)" % (where, v))
            e_end = en.rstrip()[-1:]
            fw = {"!": "!！", "?": "?？", ":": ":：", ".": ".。"}
            if e_end in fw and en not in HOT and en not in SPLIT[:1] and v.rstrip()[-1:] not in fw[e_end]:
                soft.append("punctuation: %s ends %r, EN ends %r -> %r" % (where, v.rstrip()[-1:], e_end, v))
        for run, hosts in HOT.items():
            if run not in T:
                continue
            for host in hosts:
                if host in T and T[run].casefold() not in T[host].casefold():
                    hard.append("runs: %s run %r (%r) is not inside %r" % (lang, run, T[run], T[host]))
        if all(k in T for k in SPLIT):
            sep = "" if lang in NOSPACE else " "
            if T[SPLIT[0]] + sep + T[SPLIT[1]] != T[SPLIT[2]]:
                hard.append("split: %s %r + %r != %r" % (lang, T[SPLIT[0]], T[SPLIT[1]], T[SPLIT[2]]))
        for card in UNLOCK_CARDS:
            if card not in T:
                continue
            v = T[card]
            if lang in CASELESS:
                if not re.search(r"\*\*[^*]+\*\*", v):
                    hard.append("unlock: %s card without a ** run: %r" % (lang, v))
            else:
                if not any(is_caps(w) for w in v.split(" ")):
                    hard.append("unlock: %s card without a CAPS run: %r" % (lang, v))
                for w in v.split(" "):
                    letters = "".join(c for c in w if c.isalpha())
                    if any(c.isupper() for c in letters[1:]) and not is_caps(w) and sum(c.isupper() for c in letters) >= 2:
                        hard.append("unlock: %s mixed-case word %r hides the CAPS run in %r" % (lang, w, v))
    # fit
    fit = []
    if not os.path.exists(ctfit):
        hard.append("fit: ctfit not built at %s (xcrun swiftc -O -o %s tools/strings/ctfit.swift)" % (ctfit, ctfit))
    else:
        jobs = []
        for k, en, size, track, box, n in fr:
            for lang in langs:
                jobs.append({"id": "%s|%s" % (k, lang), "font": FONT, "text": ink_text(V[lang][en]), "size": size,
                             "track": track, "lang": lang})
        res = measure(jobs, ctfit)
        for k, en, size, track, box, n in fr:
            for lang in langs:
                m = res["%s|%s" % (k, lang)]
                w = max(0.0, m["inkX1"] - m["inkX0"])
                eff = w / n * (1.12 if n > 1 else 1.0)
                sc = round(min(1.0, box / eff), 3) if eff > 0 else 1.0
                fit.append({"frame": k, "key": en, "lang": lang, "text": V[lang][en], "size": size, "box": box, "lines": n,
                            "scale": sc, "fonts": m.get("fonts", [])})
                if sc < FLOOR:
                    hard.append("fit: %s %r needs scale %.2f in %s (%g pt box, %d line(s)); floor %.2f" % (
                        lang, V[lang][en], sc, k, box, n, FLOOR))
    lines = []

    def say(s=""):
        print(s)
        lines.append(s)

    say("l10n_review: %d keys x %d languages; %d measured layouts per language (PC Display + the bold cascade), floor %.2f"
        % (len(keys), len(langs), len(fr), FLOOR))
    for lang in langs:
        f = sorted((x for x in fit if x["lang"] == lang), key=lambda x: x["scale"])[:5]
        say("  %-7s tightest: %s" % (lang, "; ".join("%s %r %.2f" % (x["frame"], x["text"], x["scale"]) for x in f)))
    say("l10n_review: %d finding(s), %d note(s)" % (len(hard), len(soft)))
    for h in hard:
        say("FAIL " + h)
    for s_ in soft:
        lines.append("note " + s_)
    if report:
        with open(report, "w", encoding="utf-8") as f:
            json.dump({"floor": FLOOR, "languages": langs, "keys": len(keys), "frames": len(fr), "findings": hard,
                       "notes": soft, "fit": fit}, f, ensure_ascii=False, indent=1)
            f.write("\n")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
