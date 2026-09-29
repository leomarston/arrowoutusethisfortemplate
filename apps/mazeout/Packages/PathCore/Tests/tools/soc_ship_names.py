#!/usr/bin/env python3
"""soc_ship_names.py — the SHIPPED name data: App/Resources/Social/social_names.json from T6's design/social/data_v2/social_names_v2.json.

PUBLISH B2 (PLAN-P G4(c): "0 hits of maze ?out / grand ?games / arrowjam … in the compiled app + bundle (blocklist stems
stored hashed)"; SPEC.md ruling 37(b) "never mention Maze Out / Grand Games"). The name generator needs the original's names
in its data only to keep them OFF the boards. The shipped file carries the same generator with no such text:
  * whole-name / token blocklist entries (blockNames, blockToken) whose key names the original, its publisher or another
    arrow game are moved to "blockHashed": the FNV-1a-64 of the key, lowercase hex — SocialNames.isBlocked matches them
    exactly like blockToken ∪ blockNames (the key, every token, every leet-folded token);
  * every list token (words, adjectives, nouns, invented, caps, mixedTokens, each form of a first name) whose key contains one of the
    shipped world's extra blocked stems (SocialWorldModel.shipped.extraBlockedStems, the stem "maze" stored hashed since FIX-3 B) can never be shown: every
    name built on it is blocked. It is replaced IN PLACE (the list indices, so every draw, stay the same) by the mark
    U+0001, which SocialNames.isBlocked blocks — the same verdict, so the same fallback name.
Everything else is byte-for-byte the design data's (same key order, the lists unchanged). A substring blocklist entry that
names the original would need a substring hash, so it stops the tool (none exists). SocialNamesTests pins it: the shipped
bank yields the same names as the design bank for thousands of players, its hashed entries are exactly the removed ones,
and no text of the original remains.
Counts only are printed (never an entry: T6's rule for blocklists).

    python3 Packages/PathCore/Tests/tools/soc_ship_names.py           # (re)write the shipped file
    python3 Packages/PathCore/Tests/tools/soc_ship_names.py --check   # exit 1 when it is not up to date
"""
import json, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
SRC = os.path.join(APP, 'design', 'social', 'data_v2', 'social_names_v2.json')
DST = os.path.join(APP, 'App', 'Resources', 'Social', 'social_names.json')

# the original, its publisher and the other arrow game (BrandTests.bannedAnyCase + "maze"), matched on the entry's key
BRAND = re.compile(r'maze|grand ?games|arrow ?jam')
EXTRA_STEMS = ['maze']              # SocialWorldModel.shipped.extraBlockedStems (FIX-3 B: stored hashed there)
MARK = '\u0001'


def fold(s):
    """data.fold: ı->i, ß->ss, ł->l, ... then NFKD with the combining marks stripped."""
    for a, b in (('ı', 'i'), ('İ', 'I'), ('ß', 'ss'), ('ł', 'l'), ('Ł', 'L'), ('ø', 'o'), ('Ø', 'O'), ('æ', 'ae'), ('Æ', 'Ae'),
                 ('ð', 'd'), ('þ', 'th')):
        s = s.replace(a, b)
    s = unicodedata.normalize('NFKD', s)
    return ''.join(ch for ch in s if not unicodedata.combining(ch))


def key(s):
    return fold(s).lower()


def fnv1a64(s):
    h = 0xcbf29ce484222325
    for b in s.encode('utf-8'):
        h ^= b
        h = (h * 0x100000001b3) & ((1 << 64) - 1)
    return h


def ship(d):
    out = {}
    stats = dict(hashed=0, marked=0, lists=0)
    hashed = []
    for k, v in d.items():
        if k == 'blockSubstring':
            bad = [x for x in v if BRAND.search(key(x))]
            assert not bad, 'a substring blocklist entry names the original: it needs a substring hash (%d)' % len(bad)
            out[k] = v
        elif k in ('blockNames', 'blockToken'):
            keep = []
            for x in v:
                if BRAND.search(key(x)):
                    hashed.append('%016x' % fnv1a64(x))      # names.is_blocked compares the RAW entry: hash it as is
                else:
                    keep.append(x)
            out[k] = keep
        elif k in ('words', 'adjectives', 'nouns', 'invented', 'caps'):
            out[k] = [MARK if any(s in key(x) for s in EXTRA_STEMS) else x for x in v]
            stats['marked'] += sum(1 for x in out[k] if x == MARK)
            stats['lists'] += 1
        elif k == 'mixedTokens':
            out[k] = {cu: [MARK if any(s in key(x) for s in EXTRA_STEMS) else x for x in toks] for cu, toks in v.items()}
            stats['marked'] += sum(1 for toks in out[k].values() for x in toks if x == MARK)
        elif k == 'cultures':
            # each form on its own: a name shows the native OR the Latin form, and only the form with the stem is blocked
            out[k] = {cu: [[MARK if any(s in key(f) for s in EXTRA_STEMS) else f for f in p] for p in toks]
                      for cu, toks in v.items()}
            stats['marked'] += sum(1 for toks in out[k].values() for p in toks for f in p if f == MARK)
        else:
            out[k] = v
    out['blockHashed'] = sorted(set(hashed))
    stats['hashed'] = len(out['blockHashed'])
    return out, stats


def render():
    with open(SRC, encoding='utf-8') as f:
        d = json.load(f)
    out, stats = ship(d)
    text = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
    for pat in (r'(?i)maze ?out', r'(?i)grand ?games', r'(?i)arrow ?jam', r'Maze', r'(?i)maze'):
        assert not re.search(pat, text), 'the shipped name data still names the original'
    return text, stats


def main():
    text, stats = render()
    if '--check' in sys.argv[1:]:
        cur = open(DST, encoding='utf-8').read() if os.path.exists(DST) else ''
        print('up to date' if cur == text else 'STALE: re-run soc_ship_names.py')
        sys.exit(0 if cur == text else 1)
    with open(DST, 'w', encoding='utf-8') as f:
        f.write(text)
    print('wrote %s (%d bytes): %d blocklist entries hashed, %d list tokens marked unshowable' %
          (os.path.relpath(DST, APP), len(text.encode('utf-8')), stats['hashed'], stats['marked']))


if __name__ == '__main__':
    main()
