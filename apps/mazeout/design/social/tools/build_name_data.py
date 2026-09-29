#!/usr/bin/env python3
"""Build design/social/data/social_names.json — the ONE name resource the app ships (App/Resources/Social/social_names.json).

Inputs (all in design/social/data, see SOURCES.md): given_<culture>.txt, words_adj.txt, words_noun.txt, words_plain.txt,
blocklist_substring.txt, blocklist_token.txt, block_names.txt.
Output token sets are made mutually DISJOINT by case/diacritic-insensitive key so that every nickname style produces
strings no other style can produce (the generator is then injective by construction; names.py proves it empirically).
Deterministic: same inputs -> byte-identical JSON.
    python3 design/social/tools/build_name_data.py
"""
import json, os, sys, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from socialsim import data as D
from socialsim.core import h64, unit

OUT = os.path.join(D.DATA, 'social_names.json')
VOWELS = set('aeiouy')

def blocked(s):
    k = D.key(s)
    for b in D.BLOCK_SUB:
        if b in k:
            return True
    if k in D.BLOCK_TOK or k in D.BLOCK_NAMES:
        return True
    return False

def cap(s):
    return s[:1].upper() + s[1:]

def main():
    used = set()          # keys already owned by some token set
    report = {}

    # 1. given names per culture, priority: specific cultures first, 'en' last (so 'Maria' belongs to es, not en).
    cultures = {}
    for c in D.CULTURES:
        toks = []
        for t in D._lines('given_%s.txt' % c):
            t = t.strip()
            if not t or len(D.fold(t)) < 2 or not D.fold(t).replace('-', '').isalpha():
                continue
            k = D.key(t)
            if k in used or blocked(t):
                continue
            used.add(k)
            toks.append([t, D.fold(t)])
        cultures[c] = toks
        report['given_' + c] = len(toks)
    name_keys = set(used)

    # 2. adjectives and nouns (compound + caps + initials styles)
    def clean_words(fn, extra_block=()):
        out = []
        seen = set()
        for w in D._lines(fn):
            w = w.strip().lower()
            if not w.isalpha() or w in seen or blocked(w) or w in extra_block:
                continue
            seen.add(w)
            out.append(w)
        return out
    adjs = clean_words('words_adj.txt')
    nouns = clean_words('words_noun.txt')
    # an adjective that is also a noun would make "Sage"+"X" ambiguous only inside compounds (fine) but CAPS needs unique keys
    caps = []
    seen = set()
    for w in adjs + nouns:
        if w in seen or w in name_keys:
            continue
        seen.add(w)
        caps.append(w.upper())
    compound_keys = set(a + n for a in adjs for n in nouns)

    # 3. plain words: not a name, not an adjective/noun (CAPS owns those keys), not a compound key
    words = []
    for w in clean_words('words_plain.txt'):
        if w in name_keys or w in seen or w in compound_keys:
            continue
        words.append(w)
    word_keys = set(words)

    # 4. invented short handles (Tetety / Ttam / Ptr / Hihi / Grib / Mema style), generated deterministically
    onsets = ['b', 'bl', 'br', 'ch', 'd', 'dr', 'f', 'fl', 'fr', 'g', 'gl', 'gr', 'h', 'j', 'k', 'kl', 'kr', 'l', 'm', 'n',
              'p', 'pl', 'pr', 'r', 's', 'sh', 'sk', 'sl', 'sn', 'sp', 'st', 't', 'th', 'tr', 'v', 'w', 'z', 'zh']
    vowels = ['a', 'e', 'i', 'o', 'u', 'ee', 'oo', 'ai', 'ou', 'ay', 'ey', 'y']
    codas = ['', '', '', 'n', 'r', 's', 'x', 'k', 'm', 'l', 't', 'b', 'p', 'g', 'z', 'ck', 'nk', 'rp', 'sh']
    cand = set()
    # doubled syllables: Hihi, Mimi, Bobo, Tete(ty)
    for o in onsets:
        for v in ['a', 'e', 'i', 'o', 'u']:
            s = o + v
            cand.add(s + s)
            cand.add(s + s + 'y')
            cand.add(s + s[-2:] if len(s) > 1 else s + s)
    # CV-CV(C) and CVC
    for o1 in onsets:
        for v1 in vowels:
            for c1 in codas:
                cand.add(o1 + v1 + c1)
            for o2 in ['b', 'd', 'g', 'k', 'l', 'm', 'n', 'p', 'r', 's', 't', 'v', 'z']:
                for v2 in ['a', 'e', 'i', 'o', 'u', 'y', 'o']:
                    for c2 in ['', 'n', 'x', 'r', 's', 'k']:
                        cand.add(o1 + v1 + o2 + v2 + c2)
    def pronounceable_rev(r):
        # at most two consonants in a row, and a doubled consonant only at the start (Ttam)
        run = 0
        for i, ch in enumerate(r):
            run = 0 if ch in VOWELS else run + 1
            if run >= 3:
                return False
        return True
    # reversed and devowelled given names (Matt -> Ttam, Peter -> Ptr)
    for c in D.CULTURES:
        for nat, fol in cultures[c]:
            f = fol.lower()
            r = f[::-1]
            if 3 <= len(f) <= 5 and (r[0] in VOWELS) != (r[1] in VOWELS) and pronounceable_rev(r):
                cand.add(r)
                dv = f[0] + ''.join(ch for ch in f[1:] if ch not in 'aeiou')
                if len(dv) == 3 and dv != f and f[0] not in VOWELS:
                    cand.add(dv)
    def pronounceable(s):
        run = 0
        for ch in s:
            if ch in VOWELS:
                run = 0
            else:
                run += 1
                if run >= 4:
                    return False
        return True
    MIXED_SUFFIXES = ['inator', 'zilla', 'tron', 'bot', 'zor', 'xd', 'master', 'star', 'ninja', 'wolf', 'king',
                      'queen', 'jr', 'thegreat', 'plays', 'gamer', 'pro', 'max', 'boss', 'fan', 'tastic', 'licious', 'xo']
    adj_noun_keys = set(adjs) | set(nouns)
    mixed_tokens = {}
    for c in D.CULTURES:
        mixed_tokens[c] = [fol for nat, fol in cultures[c] if D.key(fol) not in adj_noun_keys]
    mixed_keys = set(D.key(t) + sfx for c in D.CULTURES for t in mixed_tokens[c] for sfx in MIXED_SUFFIXES)
    tok_stems = [b for b in D.BLOCK_TOK if len(b) >= 3 and b.isalpha()]
    def awkward(s):
        # an invented handle must not start or end with a blocked short word ("Gayker", "Asska")
        return any(s.startswith(b) or s.endswith(b) for b in tok_stems)
    inv = []
    for s in cand:
        if not (3 <= len(s) <= 9) or not s.isalpha():
            continue
        k = s
        if k in name_keys or k in word_keys or k in seen or k in compound_keys or k in mixed_keys or blocked(s) or awkward(s) or not pronounceable(s):
            continue
        inv.append(s)
    # deterministic order + keep a well-mixed 40k subset
    inv.sort(key=lambda s: (h64(0x5EED, 'inv', *[ord(ch) for ch in s]), s))
    inv = [cap(s) for s in inv[:40000]]
    inv.sort(key=lambda s: s)

    underscore_suffixes = list('abcdefghijklmnopqrstuvwxyz') + ['x', 'xo', 'plays', 'gamer', 'fan', 'life', 'love', 'here',
                          'official', 'real', 'online', 'games', 'fun', 'cool', 'tv', 'yt', 'mom', 'dad', 'jr', 'sr']
    # de-duplicate underscore suffixes, keep order
    seen_u = set(); us = []
    for s in underscore_suffixes:
        if s not in seen_u:
            seen_u.add(s); us.append(s)

    out = dict(
        version=1,
        cultures=cultures,
        adjectives=adjs,
        nouns=nouns,
        caps=caps,
        words=words,
        invented=inv,
        mixedSuffixes=MIXED_SUFFIXES,
        mixedTokens=mixed_tokens,
        underscoreSuffixes=us,
        initialsLetters='bcdfghjklmnpqrstvwxz',
        blockSubstring=D.BLOCK_SUB,
        blockToken=sorted(D.BLOCK_TOK),
        blockNames=sorted(D.BLOCK_NAMES),
    )
    report.update(adjectives=len(adjs), nouns=len(nouns), caps=len(caps), words=len(words), invented=len(inv))
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=0, sort_keys=True)
        f.write('\n')
    print(json.dumps(report, indent=1))
    print('wrote', OUT, os.path.getsize(OUT), 'bytes')

if __name__ == '__main__':
    main()
