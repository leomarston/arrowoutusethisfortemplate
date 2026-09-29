# socialsim/names.py — nickname generator (reference for PathCore/Social/Names).
#
# A nickname is decode(style, slot, culture). `slot` is a dense per-(style, culture) counter handed out by the population
# in cohort order (early joiners get small slots = the plain names; later ones get decorated variants, like real
# first-come usernames). decode is INJECTIVE per (style, culture), token sets are disjoint across styles and cultures
# (build_name_data.py), so no two players in the world share a nickname (case- and accent-insensitive).
# That is the REFERENCE (the prototype). The SHIPPED model (socialsim/shipped.py, SOC1c) draws custom nicknames with
# replacement instead (DRAW / drawn() below): names repeat like the original's (two "Bobby" in its World top 15); a
# player's identity is its gid, never its name.
import json, os
from .core import h64, u01, below, perm, fl, M
from . import data as D

STYLES = ['default', 'given', 'word', 'compound', 'invented', 'caps', 'underscore', 'initials', 'mixed']
CULTURE_STYLES = {'given', 'underscore', 'mixed'}
# style mix among players who set a custom name (the rest keep the default "player_xxxxxxx")
CUSTOM_WEIGHTS = [('given', 0.34), ('word', 0.07), ('compound', 0.19), ('invented', 0.14), ('caps', 0.04),
                  ('underscore', 0.10), ('initials', 0.05), ('mixed', 0.07)]
B36 = '0123456789abcdefghijklmnopqrstuvwxyz'
D36_7 = 36 ** 7
LOCAL_DEFAULT_BASE = D36_7 // 2       # LOCAL partition default-name slots
USER_DEFAULT_BASE = D36_7 // 4        # the user's own default name: USER_DEFAULT_BASE + (h64(installSeed,'username') & (2^30-1))
LOCAL_CUSTOM_BASE = 10 ** 9           # LOCAL partition custom-style slots

_DATA = None
DATA_FILE = None                      # v2: design/social/data_v2/social_names_v2.json (None = data/social_names.json)
def data():
    global _DATA
    if _DATA is None:
        with open(DATA_FILE or os.path.join(D.DATA, 'social_names.json'), encoding='utf-8') as f:
            _DATA = json.load(f)
        d = _DATA
        c = d['initialsLetters']
        d['_initials'] = [a + b for a in c for b in c] + [a + b + e for a in c for b in c for e in c]
    return _DATA

def number(r, tokkey):
    """r >= 1 -> a decimal string, injective in r: 1..9 -> 1 digit, 10..99 -> 2 digits, ... each length class permuted by
    the token key so 'Kate' and 'Mia' don't get the same number sequence."""
    lo = 1; hi = 10
    while r >= hi:
        lo = hi; hi *= 10
    cnt = hi - lo
    return str(lo + perm(r - lo, cnt, tokkey))

def _tokkey(style, culture, idx):
    return h64(0x6E616D65, 'tok', STYLES_V2.index(style), D.CULTURES.index(culture) if culture in D.CULTURES else 99, idx)

def _grid(slot, size, style, culture):
    """slot -> (index in [0,size), round) with the round-0 order shuffled per (style, culture) and per round."""
    r = slot // size
    i = slot % size
    key = h64(0x6E616D65, 'grid', STYLES_V2.index(style), D.CULTURES.index(culture) if culture in D.CULTURES else 99, r)
    return perm(i, size, key), r

def to_katakana(s):
    """Hiragana -> katakana (U+3041..U+3096 shifted by 0x60); every other character unchanged."""
    return ''.join(chr(ord(ch) + 0x60) if 0x3041 <= ord(ch) <= 0x3096 else ch for ch in s)

def default_name(slot, salt=0):
    """'player_' + 7 base-36 chars — a keyed bijection of the slot into 36^7 (always salt 0 in the product)."""
    x = perm(slot % D36_7, D36_7, h64(0x706C6179, 'default', salt))
    s = []
    for _ in range(7):
        s.append(B36[x % 36]); x //= 36
    return 'player_' + ''.join(reversed(s))

# ------------------------------------------------------------------ shipped-model variants (SPEC-social §14.2)
# The reference (the prototype) never uses these: VARIANTS stays None and STYLES/CUSTOM_WEIGHTS keep their values, so the
# prototype's names are byte-identical. The shipped model (socialsim/shipped.py) sets VARIANTS and its own style weights:
#   'leet'          a procedural style for short handles with digits inside (L8M, K710, 0xBK — phone session 2 §H); no data
#   inventedLower   % of invented handles typed in lowercase (rng, ecr, mern, turko, ezbee, doost, ned)
#   inventedUpper   % of invented handles typed in CAPITALS (DER); givenUpper: % of first names in CAPITALS (ASLAN);
#   mixedLower      % of name+suffix handles typed in lowercase
#                   (case variants of one token: uniqueness is case-insensitive, so they can never collide)
#   compoundDigits  % of Adjective+Noun names whose FIRST form carries a 2-digit number (SneakyFalconer51, ChillKnight71):
#                   round 0 and a hashed round r* in 10..99 swap places, so the per-token suffix map stays a bijection
STYLES_V2 = STYLES + ['leet']
VARIANTS = None
# v2 (M6, OFF here): per-culture share of first names shown in their NATIVE form, as a threshold t of 256 (the spelling byte
# v < t -> native). None = the reference's 180/256 (~70 %) for every culture (the accented spelling of a Latin name).
# Non-Latin cultures carry [native script, Latin romanisation] pairs in the v2 data; KANA_P = % of Japanese native forms
# shown in katakana instead of hiragana (a per-player variant; hiragana U+3041..U+3096 + 0x60 = katakana).
NATIVE_T = None
KANA_P = 0
LEET_LETTERS = 'ABCDEFGHJKLMNPRSTVWXYZ'          # no I O Q U (read as digits / look odd in a handle)
_NL = len(LEET_LETTERS)
LEET_A = _NL * 9 * _NL                           # X d Y        L8M   (d = 1..9)
LEET_B = _NL * 900                               # X ddd        K710  (100..999)
LEET_C = _NL * _NL                               # 0x X Y       0xBK
LEET_SIZE = LEET_A + LEET_B + LEET_C

def leet_token(i):
    """i in [0, LEET_SIZE) -> the i-th short handle. Every form has a digit before a letter or starts with a single letter
    followed by exactly 3 digits, which no other style can produce (their numbers are suffixes after >= 2 letters)."""
    L = LEET_LETTERS
    if i < LEET_A:
        return L[i // (9 * _NL)] + str(1 + (i // _NL) % 9) + L[i % _NL]
    i -= LEET_A
    if i < LEET_B:
        return L[i // 900] + str(100 + i % 900)
    i -= LEET_B
    return '0x' + L[i // _NL] + L[i % _NL]

def grid_size(style, culture):
    """Size of a style's token grid (round 0) for a culture (the culture only matters for the CULTURE_STYLES)."""
    d = data()
    if style == 'leet':
        return LEET_SIZE
    if style == 'given':
        return len(d['cultures'][culture])
    if style == 'word':
        return len(d['words'])
    if style == 'compound':
        return len(d['adjectives']) * len(d['nouns'])
    if style == 'invented':
        return len(d['invented'])
    if style == 'caps':
        return len(d['caps'])
    if style == 'underscore':
        return len(d['cultures'][culture]) * len(d['underscoreSuffixes'])
    if style == 'initials':
        return len(d['_initials']) * len(d['nouns'])
    if style == 'mixed':
        return len(d['mixedTokens'][culture]) * len(d['mixedSuffixes'])
    raise ValueError(style)

def decode(style, slot, culture, spelling_bits=0):
    """The reference's first-come nickname: slot -> (grid index, round) -> build()."""
    if style == 'default':
        return default_name(slot, 0)
    cul = culture if style in CULTURE_STYLES else '*'
    i, r = _grid(slot, grid_size(style, culture), style, cul)
    return build(style, i, r, culture)

def build(style, i, r, culture, vr=None):
    """The nickname at grid index i (round-0 order) and round r (r >= 1 appends number(r, token key)). `vr` keys the case /
    spelling variants (default: the round, as in the reference; the shipped drawn names key them per player)."""
    d = data()
    cul = culture if style in CULTURE_STYLES else '*'
    V = VARIANTS
    if vr is None:
        vr = r
    if style == 'leet':
        s = leet_token(i)
        return s if r == 0 else s + number(r, _tokkey(style, cul, i))
    if style == 'given':
        toks = d['cultures'][culture]
        native, folded = toks[i]
        k = _tokkey(style, cul, i)
        v = h64(k, 'spell', vr) & 0xFF
        use_native = v < (180 if NATIVE_T is None else NATIVE_T.get(culture, 180))
        base = native if use_native else folded              # reference: ~70 % native spelling, ~30 % ASCII-folded
        if KANA_P and use_native and culture == 'jp' and (h64(k, 'kana', vr) % 100) < KANA_P:
            base = to_katakana(native)
        if (v % 5) == 0:
            base = base.lower()                              # ~20 % typed in lowercase
        elif V is not None and (h64(k, 'upper', vr) % 100) < V['givenUpper']:
            base = folded.upper()                            # shipped: ASLAN, KAREN (ASCII spelling: exact in Swift too)
        return base if r == 0 else base + number(r, k)
    if style == 'word':
        toks = d['words']
        k = _tokkey(style, cul, i)
        w = toks[i]
        if (h64(k, 'case', vr) & 3) == 0:
            w = w[:1].upper() + w[1:]                        # 'Nope' vs 'nope'
        return w if r == 0 else w + number(r, k)
    if style == 'compound':
        A = d['adjectives']; N = d['nouns']
        a = A[i // len(N)]; n = N[i % len(N)]
        s = a[:1].upper() + a[1:] + n[:1].upper() + n[1:]
        k = _tokkey(style, cul, i)
        if V is not None and (h64(k, 'd2') % 100) < V['compoundDigits']:
            rs = 10 + h64(k, 'r2') % 90          # a 2-digit round: number(rs) has 2 digits
            r = rs if r == 0 else (0 if r == rs else r)
        return s if r == 0 else s + number(r, k)
    if style == 'invented':
        toks = d['invented']
        s = toks[i]
        if V is not None:
            x = h64(_tokkey(style, cul, i), 'lower', vr) % 100
            if x < V['inventedLower']:
                s = s.lower()                                # rng, ecr, mern, turko, doost
            elif x < V['inventedLower'] + V['inventedUpper']:
                s = s.upper()                                # DER, NAMNAM (invented tokens are ASCII)
        return s if r == 0 else s + number(r, _tokkey(style, cul, i))
    if style == 'caps':
        toks = d['caps']
        s = toks[i]
        return s if r == 0 else s + number(r, _tokkey(style, cul, i))
    if style == 'underscore':
        toks = d['cultures'][culture]; suf = d['underscoreSuffixes']
        t = toks[i // len(suf)][1].lower().replace(' ', '')
        s = t + '_' + suf[i % len(suf)]
        return s if r == 0 else s + number(r, _tokkey(style, cul, i))
    if style == 'initials':
        I = d['_initials']; N = d['nouns']
        n = N[i % len(N)]
        s = I[i // len(N)].upper() + n[:1].upper() + n[1:]
        return s if r == 0 else s + number(r, _tokkey(style, cul, i))
    if style == 'mixed':
        toks = d['mixedTokens'][culture]; suf = d['mixedSuffixes']
        t = toks[i // len(suf)]
        s = t + suf[i % len(suf)]
        if V is not None and (h64(_tokkey(style, cul, i), 'lower', vr) % 100) < V['mixedLower']:
            s = s.lower()                                    # shipped: 'limminator'-style handles typed in lowercase
        return s if r == 0 else s + number(r, _tokkey(style, cul, i))
    raise ValueError(style)

# ------------------------------------------------------------------ shipped: drawn nicknames (duplicates allowed; SOC1c)
# The reference hands out dense first-come slots, so no two players share a nickname and a plain first name is gone after
# the first few thousand joiners (later ones carry numbers: Kate23). The original is not like that: two different "Bobby"
# sit in its World top 15 (phone session 2 §B), plain first names are ~14 % of the names on its boards and names with
# digits only ~7 % (§H). The shipped model (socialsim/shipped.py) sets DRAW: a custom-named player's nickname is DRAWN from
# its style's token grid by a hash of its gid, with replacement, so names repeat like real ones:
#   * first-name styles (given, mixed, underscore) pick the name by popularity — the per-culture lists are ordered most
#     common first (SSA counts for 'en', curated order elsewhere): headP % of the draws take one of the headN most common
#     names uniformly, the rest index = floor(n * u^2) over the whole list (P(index < k) = sqrt(k/n)); their suffix
#     uniformly; every other style uniformly over its grid;
#   * a number is appended with probability numberP[style] % (2 digits with probability twoDigitP %, else 3);
#   * the case / spelling variants are keyed per player (two players drawing 'Bobby' may show 'Bobby' and 'bobby').
# The player's identity is its gid, never its name; 'player_' default names stay one bijection (unique).
DRAW = None
POPULAR_STYLES = ('given', 'mixed', 'underscore')

def drawn(style, culture, key):
    """The shipped nickname of a custom-named player; key = h64(world seed, 'nick', gid)."""
    i, t = draw_index(style, culture, key)
    Dw = DRAW
    r = 0
    if below(key, 'num?', 100) < Dw['numberP'].get(style, 0):
        if below(key, 'num2', 100) < Dw['twoDigitP']:
            r = 10 + below(key, 'num', 90)
        else:
            r = 100 + below(key, 'num', 900)
    return build(style, i, r, culture, vr=h64(key, 'var') & 0x7FFFFFFF)

def draw_index(style, culture, key):
    """The grid index a drawn nickname is built on, and (first-name styles) the index of its first name in the culture's
    list (None for the other styles). Used by drawn() and by the calibration tools that count repeated first names."""
    d = data()
    Dw = DRAW
    if style in POPULAR_STYLES:
        if style == 'given':
            ntok, nsuf = len(d['cultures'][culture]), 1
        elif style == 'mixed':
            ntok, nsuf = len(d['mixedTokens'][culture]), len(d['mixedSuffixes'])
        else:
            ntok, nsuf = len(d['cultures'][culture]), len(d['underscoreSuffixes'])
        if Dw.get('headScaled'):
            # v2 (M7): the head is scaled to the list (headN <= n / 6; headP shrinks below 300 names) and part of the rest
            # is uniform over the list (tailUniformP %), so the most common name of a list is ~1.5-2.5 % of draws, not ~4-11 %
            H = max(1, min(Dw['headN'], ntok // 6))
            if below(key, 'head?', 100) < Dw['headP'] * min(ntok, 300) // 300:
                t = below(key, 'head', H)
            else:
                u = u01(key, 'pop')
                if below(key, 'tailU', 100) < Dw['tailUniformP']:
                    t = int(fl(ntok * u))
                else:
                    t = int(fl(ntok * u * u))
        elif below(key, 'head?', 100) < Dw['headP']:
            t = below(key, 'head', min(Dw['headN'], ntok))      # the most common names: real first names are concentrated
        else:
            u = u01(key, 'pop')
            t = int(fl(ntok * u * u))                          # the rest by rank: P(index < k) = sqrt(k / n)
        i = t * nsuf + below(key, 'suf', nsuf)
        return i, t
    return below(key, 'pick', grid_size(style, culture)), None

# ------------------------------------------------------------------ blocklist

LEET = str.maketrans({'0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't', '8': 'b', '@': 'a', '$': 's', '!': 'i'})

def tokens_of(name):
    """Split into lowercase tokens at '_', letter/digit changes and CamelCase humps, including an acronym run followed by
    a capitalised word ("NHLKitten" -> nhl, kitten)."""
    toks = []; cur = ''
    n = len(name)
    for i, ch in enumerate(name):
        if ch == '_':
            if cur: toks.append(cur)
            cur = ''; continue
        brk = False
        if cur:
            prev = cur[-1]
            nxt = name[i + 1] if i + 1 < n else ''
            if ch.isdigit() != prev.isdigit():
                brk = True
            elif ch.isupper() and prev.islower():
                brk = True
            elif ch.isupper() and prev.isupper() and nxt.islower():
                brk = True
        if brk:
            toks.append(cur); cur = ''
        cur += ch
    if cur: toks.append(cur)
    return [D.key(t) for t in toks]

def is_blocked(name):
    d = data()
    k = D.key(name).translate(LEET)
    for b in d['blockSubstring']:
        if b in k:
            return True
    bt = set(d['blockToken']) | set(d['blockNames'])
    if k in bt:
        return True
    for t in tokens_of(name):
        if t in bt or t.translate(LEET) in bt:
            return True
    return False

def user_default_name(install_seed):
    return default_name(USER_DEFAULT_BASE + (h64(install_seed, 'username') & ((1 << 30) - 1)), 0)
