#!/usr/bin/env python3
"""Per-storefront keyword research for Arrow Out (T3 STORE).

Two public, read-only Apple endpoints, curl-equivalent (urllib), no login:

  hints   App Store search autocomplete (what people TYPE), per storefront:
          search.itunes.apple.com/WebObjects/MZSearchHints.woa/wa/hints
          with header X-Apple-Store-Front: <storefront id>,29
  rank    iTunes Search API (what RANKS for a phrase), per country:
          itunes.apple.com/search?term=..&entity=software&country=..

Raw answers go to build/p/T3/aso/ (gitignored); design/publish/aso-evidence.json is the
curated summary that design/keywords.json cites.

  python3 tools/release/aso_research.py hints  [--locales de-DE tr ...]
  python3 tools/release/aso_research.py rank   [--locales ...]   # the phrases in keywords.json
  python3 tools/release/aso_research.py query  --locale de-DE "pfeil spiel" ...   # merged into hints-<loc>.json
  python3 tools/release/aso_research.py evidence   # -> design/publish/aso-evidence.json

The Search API allows ~20 calls a minute, so `rank` sleeps 3.2 s between calls.
"""
import argparse
import json
import plistlib
import re
import subprocess
import sys
import time
import unicodedata
import urllib.parse
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
OUT = APP / "build" / "p" / "T3" / "aso"

# store locale -> (storefront id, iTunes country, research note)
STOREFRONT = {
    "en-US": (143441, "us", ""),
    "de-DE": (143443, "de", ""),
    "fr-FR": (143442, "fr", ""),
    "es-ES": (143454, "es", ""),
    "it": (143450, "it", ""),
    "pt-BR": (143503, "br", ""),
    "tr": (143480, "tr", ""),
    "ja": (143462, "jp", ""),
    "ko": (143466, "kr", ""),
    # China mainland is NOT sold (ruling 38). zh-Hans metadata is read in SG/MY and by
    # zh-Hans users of other storefronts; CN is only used to learn how people phrase it.
    "zh-Hans": (143465, "cn", "vocabulary only: CN is excluded from sale"),
    "pl": (143478, "pl", ""),
    "sk": (143496, "sk", ""),
    "sl-SI": (143499, "si", ""),
}

EN_SEEDS = ["arrow", "arrow out", "arrow escape", "arrow puzzle", "arrow game",
            "arrows", "tap arrow", "arrows escape"]
SEEDS = {
    "en-US": EN_SEEDS + ["arrow e", "arrow p", "arrow g", "hard arrow", "escape puzzle",
                         "tap puzzle game", "brain puzzle", "logic puzzle", "timed puzzle"],
    "de-DE": EN_SEEDS + ["pfeil", "pfeile", "pfeil spiel", "pfeile raus", "pfeil rätsel",
                         "pfeil puzzle", "logik rätsel", "denkspiel", "knobelspiel", "rätsel spiele"],
    "fr-FR": EN_SEEDS + ["flèche", "fleche", "flèches", "jeu de flèche", "jeu fleche",
                         "puzzle flèche", "casse tête", "jeu de logique", "jeu de réflexion"],
    "es-ES": EN_SEEDS + ["flecha", "flechas", "juego de flechas", "juego flechas", "puzzle flechas",
                         "rompecabezas", "juegos de lógica", "juegos de logica", "juego de escape"],
    "it": EN_SEEDS + ["freccia", "frecce", "gioco frecce", "gioco delle frecce", "puzzle frecce",
                      "rompicapo", "giochi di logica", "gioco logica"],
    "pt-BR": EN_SEEDS + ["flecha", "flechas", "jogo da flecha", "jogo de flecha", "seta", "setas",
                         "jogo das setas", "quebra cabeça", "jogo de lógica", "jogos de raciocinio"],
    "tr": EN_SEEDS + ["ok", "ok oyunu", "ok bulmaca", "oklar", "ok çıkarma", "ok kaçırma",
                      "zeka oyunu", "bulmaca", "bulmaca oyunu"],
    "ja": EN_SEEDS + ["矢印", "矢印ゲーム", "矢印パズル", "矢印 脱出", "脱出パズル", "パズル",
                      "脳トレ", "矢印 タップ"],
    "ko": EN_SEEDS + ["화살표", "화살표 게임", "화살표 퍼즐", "화살표 탈출", "퍼즐 게임", "두뇌 게임",
                      "퍼즐"],
    "zh-Hans": EN_SEEDS + ["箭头", "箭头游戏", "箭头消除", "箭头解谜", "箭头 逃脱", "益智游戏",
                           "烧脑", "解谜"],
    "pl": EN_SEEDS + ["strzałki", "strzałka", "gra w strzałki", "gra strzałki", "strzalki",
                      "łamigłówki", "gry logiczne", "puzzle"],
    "sk": EN_SEEDS + ["šípky", "šípka", "sipky", "hra šípky", "hlavolam", "logické hry", "puzzle"],
    "sl-SI": EN_SEEDS + ["puščice", "puscice", "puščica", "igra puščice", "uganka", "logične igre",
                         "puzzle"],
}

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15"}


def fetch(url, headers=None, tries=3):
    """curl, not urllib: this machine's python.org build has no CA bundle, and the task
    asks for curl against Apple's public endpoints anyway."""
    args = ["curl", "-s", "-m", "25", "--fail"]
    for k, v in {**UA, **(headers or {})}.items():
        args += ["-H", f"{k}: {v}"]
    for i in range(tries):
        r = subprocess.run(args + [url], capture_output=True)
        if r.returncode == 0:
            return r.stdout
        time.sleep(4 * (i + 1))
    raise RuntimeError(f"curl failed ({r.returncode}) for {url}")


def hints(locale, term):
    sf = STOREFRONT[locale][0]
    url = ("https://search.itunes.apple.com/WebObjects/MZSearchHints.woa/wa/hints?"
           "clientApplication=Software&term=" + urllib.parse.quote(term))
    body = fetch(url, {"X-Apple-Store-Front": f"{sf},29"})
    try:
        d = plistlib.loads(body)
    except Exception:  # noqa: BLE001
        return []
    return [h.get("term", "") for h in d.get("hints", [])]


def search(locale, term, limit=25):
    cc = STOREFRONT[locale][1]
    url = ("https://itunes.apple.com/search?entity=software&limit=%d&country=%s&term=%s"
           % (limit, cc, urllib.parse.quote(term)))
    d = json.loads(fetch(url))
    return [{"name": r.get("trackName"), "dev": r.get("artistName"),
             "ratings": r.get("userRatingCount", 0), "genre": r.get("primaryGenreName"),
             "id": r.get("trackId")} for r in d.get("results", [])]


def cmd_hints(locales):
    OUT.mkdir(parents=True, exist_ok=True)
    for loc in locales:
        res = {}
        for t in SEEDS[loc]:
            res[t] = hints(loc, t)
            time.sleep(0.6)
        (OUT / f"hints-{loc}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
        n = sum(len(v) for v in res.values())
        print(f"{loc:8} {len(res)} queries, {n} hints")


# a result counts as "genre" when its title names arrows in any of our languages
ARROW_WORDS = ["arrow", "pfeil", "flèche", "fleche", "flecha", "frecc", "setas", "seta ",
               "ok ", "oklar", "矢印", "화살표", "箭头", "strzał", "šíp", "sip", "pušč", "pusc"]


def is_genre(name):
    n = (name or "").lower()
    return any(w in n for w in ARROW_WORDS)


def cmd_rank(locales, phrases=None):
    OUT.mkdir(parents=True, exist_ok=True)
    kw = json.loads((APP / "design" / "keywords.json").read_text())
    for loc in locales:
        terms = phrases or kw[loc].split(",")
        f = OUT / f"rank-{loc}.json"
        have = json.loads(f.read_text()) if f.exists() else {}
        res = {}
        for t in terms:
            if t in have and not phrases:
                continue          # already measured; `query`-style re-runs stay cheap
            r = search(loc, t)
            res[t] = {"genre_in_top10": sum(is_genre(x["name"]) for x in r[:10]),
                      "results": len(r), "top": r[:10]}
            time.sleep(3.2)
            print(f"{loc:8} {t:34} results {len(r):2}  arrow-titles in top10: "
                  f"{res[t]['genre_in_top10']}  #1 {r[0]['name'] if r else '-'}")
        f = OUT / f"rank-{loc}.json"
        old = json.loads(f.read_text()) if f.exists() else {}
        old.update(res)
        f.write_text(json.dumps(old, ensure_ascii=False, indent=1))


STOP = {"de", "da", "das", "do", "di", "del", "la", "le", "les", "des", "w", "z", "na", "s", "so", "der",
         "die", "the", "of", "a", "e", "et", "y"}


def norm(s):
    """Accent-, case- and stop-word-insensitive word list (App Store search ignores diacritics)."""
    s = unicodedata.normalize("NFKD", s.casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("ı", "i")
    words = [w for w in re.split(r"[\s:\-–—·,.!?()（）：]+", s) if w]
    return [w for w in words if w not in STOP]


def contains(hint, phrase):
    h, p = norm(hint), norm(phrase)
    if not p:
        return False
    if len(p) == 1 and len(h) >= 1 and not p[0].isascii():
        return any(p[0] in w for w in h)          # CJK: one token, may sit inside a longer token
    return any(h[i:i + len(p)] == p for i in range(len(h) - len(p) + 1))


def cmd_evidence():
    """design/publish/aso-evidence.json: every keyword phrase with the autocomplete hints that contain it
    (VERIFIED if >= 1) and what the Search API ranks for it."""
    kw = json.loads((APP / "design" / "keywords.json").read_text())
    doc = {"_about": ("Generated by tools/release/aso_research.py evidence from the raw answers in build/p/T3/aso/ "
                      "(App Store autocomplete per storefront + iTunes Search API per country, curl, 2026-09-28). "
                      "hints = autocomplete suggestions that contain the phrase (accent/case/stop-word-insensitive); "
                      "arrow_titles_top10 = how many of the top 10 search results carry an arrow word in their title "
                      "(high = a genre long tail we can rank in; 0 = a head term owned by big generic apps)."),
           "locales": {}}
    for loc, line in kw.items():
        hints_f = OUT / f"hints-{loc}.json"
        rank_f = OUT / f"rank-{loc}.json"
        H = json.loads(hints_f.read_text()) if hints_f.exists() else {}
        Rk = json.loads(rank_f.read_text()) if rank_f.exists() else {}
        rows = []
        for ph in line.split(","):
            ex = []
            for q, hs in H.items():
                for h in hs:
                    if contains(h, ph) and h not in ex:
                        ex.append(h)
            r = Rk.get(ph, {})
            rows.append({"phrase": ph, "hint_count": len(ex), "hints": ex[:4],
                         "search_results": r.get("results"), "arrow_titles_top10": r.get("genre_in_top10"),
                         "top3": [x["name"] for x in r.get("top", [])[:3]]})
        doc["locales"][loc] = {"storefront": STOREFRONT[loc][0], "country": STOREFRONT[loc][1],
                               "note": STOREFRONT[loc][2], "keywords": rows}
    out = APP / "design" / "publish" / "aso-evidence.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    missing = [(l, r["phrase"]) for l, v in doc["locales"].items() for r in v["keywords"] if not r["hint_count"]]
    print(f"wrote {out.relative_to(APP)}; phrases without a hint: {missing or 'none'}")
    return not missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["hints", "rank", "query", "evidence"])
    ap.add_argument("--locales", nargs="*")
    ap.add_argument("--locale")
    ap.add_argument("terms", nargs="*")
    a = ap.parse_args()
    locs = a.locales or list(STOREFRONT)
    if a.cmd == "hints":
        cmd_hints(locs)
    elif a.cmd == "rank":
        cmd_rank(locs)
    elif a.cmd == "evidence":
        sys.exit(0 if cmd_evidence() else 1)
    else:
        if not a.locale:
            sys.exit("query needs --locale")
        f = OUT / f"hints-{a.locale}.json"
        saved = json.loads(f.read_text()) if f.exists() else {}
        for t in a.terms:
            h = hints(a.locale, t)
            saved[t] = h
            print(f"[hints {a.locale}] {t!r}: {h}")
            time.sleep(0.6)
        OUT.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(saved, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
