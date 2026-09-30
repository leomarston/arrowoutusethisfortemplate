#!/usr/bin/env python3
"""Arrow Out App Store metadata: the limits, the locale set, the banned-word gate and the writer.

The conduitbend pattern (tools/loc.py there), extended for a published copy of another game:
  * every App Store limit is checked, and the two URL files are written BEFORE the check, so a locale
    that trips one limit never also loses its privacy/support URLs (memory locale-urls-before-the-length-check);
  * keywords are NEVER written here: they live in design/keywords.json and go up with
    scripts/asc_keywords.py (memories keywords-are-user-owned, template-scaffolds-empty-keywords-txt);
  * no release_notes.txt for 1.0.0 (whatsNew on a first version answers 409);
  * the brand gate: nothing in any store text, keyword, caption or IAP text may name the original game or its
    publisher, echo the other game's brand phrases, or claim online play/other people (owner item 11, ruling 37b/38).
"""
import re
import unicodedata
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
STORE_SRC = APP / "design" / "publish" / "store"      # <loc>.json + review.json (the source of truth)
FASTLANE_META = APP / "fastlane" / "metadata"           # T5 scaffolds fastlane/; S3 writes here

# memory localize-top-13-locales: store locale sl-SI, catalogue sl
LOCALES = ["en-US", "de-DE", "fr-FR", "es-ES", "it", "pt-BR", "tr", "ja", "ko", "zh-Hans", "pl", "sk", "sl-SI"]
LIM = {"name": 30, "subtitle": 30, "promotional_text": 170, "description": 4000}
KEYWORDS_LIMIT = 100
IAP_NAME_LIMIT, IAP_DESC_LIMIT = 35, 55          # ASC Help (INFERRED until T5's first POST reads them back)
REVIEW_NOTES_LIMIT = 4000

# BRAND, SEED, NAME_EN, PRIVACY, SUPPORT, COPYRIGHT and LOCALES are written by `python3 tools/game.py generate` from
# apps/<slug>/game.yml (identity.brand_name, store.*): edit game.yml, not these lines.
SEED = "arrow out"                                 # first keyword in every locale; every name starts with it
BRAND = "Arrow Out"                                # the product name every store name starts with
NAME_EN = "Arrow Out: Arrow Escape Puzzle"         # ruling 38 (verbatim)

PRIVACY = "https://leomarston.github.io/manycode-legal/privacy-arrow-out.html"  # RFIX 09-29: the Arrow Out page (Meta SDK), live since 23:24
SUPPORT = "https://leomarston.github.io/manycode-legal/support.html"
EULA = "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/"
COPYRIGHT = "2026 Manycode Apps"

# --- the banned-word gate ------------------------------------------------------------------------------
# Matched case-insensitively on NFC text. Every locale is checked against ALL lists (a German word in the
# Polish description is still a hit). Word-ish boundaries where a stem would hit innocent words.
BANNED_ALL = [
    # the original, its publisher, its former name and brand phrases (owner item 11; release-plan §6.3)
    r"maze", r"mazeout", r"grand\s*games", r"\bgrand\b", r"\bjam\b", r"arrow\s*jam", r"tap\s*away",
    # "maze" in our 12 other languages: Apple combines name words, and "Out" + maze = the other brand
    r"labyrinth", r"labyrinthe", r"laberint", r"labirint", r"labirent", r"labirynt", r"labyrint",
    r"迷路", r"迷宮", r"迷宫", r"미로",
    # competitors' exact brands (guideline 2.3.7)
    r"arrowscapes", r"arrows\s*go\b", r"amaze", r"point\s*out", r"cube\s*away", r"lessmore", r"easybrain",
    r"popcore", r"arrows\s*[–-]?\s*puzzle\s*escape",
    # no online / other-people claims: the social world and events are an on-device simulation (ruling 24)
    r"\bonline\b", r"multi\s*-?\s*player", r"\bfriends?\b", r"simulat", r"\bplayers?\b", r"worldwide",
    r"mehrspieler", r"\bfreunde?\b", r"\bspieler", r"en\s+ligne", r"multijoueur", r"\bamis?\b", r"joueur",
    r"en\s+l[ií]nea", r"multijugador", r"\bamigos?\b", r"jugador", r"multigiocatore", r"\bamici\b",
    r"giocator", r"multijogador", r"jogador", r"çevrimiçi", r"çok\s+oyunculu", r"arkadaş", r"oyuncu",
    r"オンライン", r"マルチプレイ", r"対戦", r"友達", r"プレイヤー", r"온라인", r"멀티", r"친구", r"플레이어",
    r"在线", r"联网对战", r"多人", r"好友", r"朋友", r"玩家", r"wieloosobow", r"znajom", r"przyjaci", r"gracz",
    r"hráč", r"priateľ", r"priatel", r"viacerých\s+hráčov", r"večigralsk", r"prijatelj", r"igralc", r"igralec",
    # store-copy hygiene
    r"test\s*store", r"90\s*%", r"lorem",
]
# case-SENSITIVE (Spanish/Portuguese "todo" is a normal word)
BANNED_CASE = [r"\bTODO\b", r"\bTBD\b", r"\bFIXME\b", r"XXX"]
# "Free" is banned in the NAME only (docs/archive/ASO-subscription-apps.md); fine in descriptions ("free to play").
BANNED_NAME = [r"\bfree\b", r"kostenlos", r"gratuit", r"\bgratis\b", r"ücretsiz", r"無料", r"무료", r"免费",
               r"za\s+darmo", r"zadarmo", r"brezplač", r"!"]


def nfc(s):
    return unicodedata.normalize("NFC", s)


def banned_hits(text, extra=()):
    t = nfc(text)
    hits = {p for p in list(BANNED_ALL) + list(extra) if re.search(p, t.casefold(), flags=re.IGNORECASE)}
    hits |= {p for p in BANNED_CASE if re.search(p, t)}
    return sorted(hits)


def write(loc, vals, base=FASTLANE_META):
    """Write one locale's text files. URLs first, then every field that fits; returns False on any limit hit."""
    d = base / loc
    d.mkdir(parents=True, exist_ok=True)
    (d / "privacy_url.txt").write_text(PRIVACY)
    (d / "support_url.txt").write_text(SUPPORT)
    bad = [(k, len(vals[k]), LIM[k]) for k in LIM if len(vals[k]) > LIM[k]]
    for k in LIM:
        if len(vals[k]) <= LIM[k]:
            (d / f"{k}.txt").write_text(vals[k])
    for stray in ("keywords.txt", "release_notes.txt"):
        if (d / stray).exists():
            (d / stray).unlink()
            print(f"  removed {loc}/{stray} (keywords are user-owned; no whatsNew on 1.0.0)")
    if bad:
        print("  !! " + loc + ": " + ", ".join(f"{k} {n}>{l}" for k, n, l in bad) + "  (other fields + URLs written)")
        return False
    print(f"  {loc:8} name {len(vals['name']):2} sub {len(vals['subtitle']):2} "
          f"promo {len(vals['promotional_text']):3} desc {len(vals['description'])}")
    return True
