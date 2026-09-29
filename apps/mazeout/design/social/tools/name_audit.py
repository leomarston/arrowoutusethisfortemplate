#!/usr/bin/env python3
"""Every nickname of the shared world up to a date: blocklist, length, style mix and repeats (case/accent-insensitive).
    python3 design/social/tools/name_audit.py 2027-09-25            # the prototype: every nickname unique
    python3 design/social/tools/name_audit.py 2031-09-25 --v552     # the shipped model (socialsim/shipped.py)
    python3 design/social/tools/name_audit.py 2031-09-25 --v2       # the v2 world (socialsim/v2.py; + native-script checks)
The prototype's rule is uniqueness (0 duplicates). The shipped model (SOC1c) draws nicknames with replacement like the
original (two "Bobby" in its World top 15), so its verdict is: 0 blocked, 0 longer than 16, and repeats at the phone's
rate — the chance that two board-like rows (non-tourist players) share a name inside the 95 % interval of the phone's
boards (1 repeated pair in 1,721 row pairs: 1.5e-5 .. 3.2e-3). Identity is the gid, never the name.

T6 (2026-09-28): the audit STREAMS the world — every cohort is named the moment it is built and then its activity tables,
country blocks and index entries are dropped (names depend on the cohort's id, size, styles and blocks only), so a 5-year
v2 world (~200k cohorts) is audited in a few hundred MB. Outputs carry counts and sha1 prefixes only: never a blocked name.
--v2 also screens every shown name with the published list of tools/v2/pubscreen.py (LDNOOBW, never shipped): whole name /
token equality or a Latin entry of >= 5 letters inside the name ('publishedMatches'; the names themselves are not written).
"""
import os, sys, time, json, collections, hashlib, array, unicodedata
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
V552 = '--v552' in sys.argv
V2M = '--v2' in sys.argv
if V552:
    from socialsim import shipped as SH
    SH.apply()
if V2M:
    from socialsim import v2 as V2
    V2.apply()
from socialsim import population as Pp, core as K, data as D, names as Nm
from datetime import datetime, timezone
until = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else '2027-09-25'
t = int(datetime.fromisoformat(until).replace(tzinfo=timezone.utc).timestamp())

PUB = None
if V2M:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'v2'))
    import pubscreen
    PUB = pubscreen.Published(D.key, Nm.tokens_of)


def sha8(s):
    return hashlib.sha1(s.encode('utf-8')).hexdigest()[:8]


def script_of(nm):
    for ch in nm:
        if ch.isalpha():
            return unicodedata.name(ch, '?').split(' ')[0]
    return 'none'


def fnv(nm):
    h = 0xcbf29ce484222325
    for b in D.key(nm).encode('utf-8'):
        h ^= b
        h = (h * 0x100000001b3) & K.M
    return h


S = dict(n=0, blocked=0, too_long=0, pub=0, pub_whole=0, cohorts=0)
hs = array.array('Q')
hb = array.array('Q')
styles = collections.Counter()
given = collections.Counter()
scripts = collections.Counter()
blocked_sha = []
pub_sha = []
pub_kind = collections.Counter()


def audit_cohort(W, c):
    board_like = Pp.ARCH[c.a]['key'] != 'tourist'
    for j in range(c.n):
        nm, st = W.name(c, j)
        styles[st] += 1
        if Nm.is_blocked(nm):
            S['blocked'] += 1
            if len(blocked_sha) < 20:
                blocked_sha.append(sha8(nm))
        if len(nm) > 16:
            S['too_long'] += 1
        if V2M:
            scripts[script_of(nm)] += 1
            if st != 'default' and st != 'fallback' and PUB.whole_set:
                we = PUB.whole_entry(nm)
                if we is not None or PUB.inside(nm):
                    S['pub'] += 1
                    kind = 'inside' if we is None else ('wholeEnglishWord' if PUB.dictword(we) else 'whole')
                    if kind == 'whole':
                        S['pub_whole'] += 1
                    pub_kind[kind + ':' + st] += 1
                    if len(pub_sha) < 40:
                        pub_sha.append(sha8(nm))
        h = fnv(nm)
        hs.append(h)
        if board_like:
            hb.append(h)
        if st == 'given':
            given[D.key(nm)] += 1
        S['n'] += 1
    S['cohorts'] += 1


_orig_add = Pp.World._add_cohort


def _streaming_add(self, *a, **kw):
    _orig_add(self, *a, **kw)
    c = self.cohorts[-1]
    audit_cohort(self, c)
    # names never need the activity tables again; country units are only read by country queries
    c.m = c.pre = c.ml = c.prel = None
    c.blocks = None if c.blocks is None else ()
    self.units = {}
    self._sess_cache = {}


Pp.World._add_cohort = _streaming_add
W = Pp.World()
t0 = time.time()
W.extend_to(t)
# the whole join period that contains `until` is built (as before); every cohort in it is audited
a = np.frombuffer(hs, dtype=np.uint64).copy()
a.sort()
dups = int(np.sum(a[1:] == a[:-1]))
_, cnt = np.unique(a, return_counts=True)
_, cntb = np.unique(np.frombuffer(hb, dtype=np.uint64), return_counts=True)
nb = int(cntb.sum())
pair_rate_board = float(np.sum(cntb.astype(np.float64) * (cntb - 1))) / (nb * (nb - 1.0)) if nb > 1 else 0.0
drawn = Nm.DRAW is not None
blocked, too_long, n = S['blocked'], S['too_long'], S['n']
if drawn:
    verdict = 'PASS' if blocked == 0 and too_long == 0 and 1.5e-5 <= pair_rate_board <= 3.2e-3 else 'FAIL'
else:
    verdict = 'PASS' if blocked == 0 and dups == 0 else 'FAIL'
res = dict(model='v2' if V2M else 'v552' if V552 else 'reference', until=until, players=n, cohorts=S['cohorts'],
           rule='drawn: 0 blocked, 0 > 16, repeats at the phone rate' if drawn else 'unique: 0 duplicates, 0 blocked',
           verdict=verdict, fnv_duplicates=dups, distinct_names=int(len(cnt)), max_same_name=int(cnt.max()) if len(cnt) else 0,
           board_like_players=nb, board_like_pair_rate=float('%.3g' % pair_rate_board),
           phone_pair_rate='1/1721 (95 % CI 1.5e-5 .. 3.2e-3)',
           most_common_first_names=given.most_common(12), blocked_shown=blocked, blocked_sha1=blocked_sha,
           longer_than_16=too_long, styles=dict(styles), seconds=round(time.time() - t0, 1))
if V2M:
    res['scripts'] = dict(scripts.most_common())
    res['publishedList'] = dict(source='LDNOOBW (CC BY 4.0) via tools/v2/pubscreen.py; audit only, never shipped',
                                matches=S['pub'], wholeNonEnglishWord=S['pub_whole'], byKindAndStyle=dict(pub_kind), sha1=pub_sha,
                                kinds='whole = the name or a token EQUALS a listed word (not an ordinary English word); '
                                      'wholeEnglishWord = equals a listed word that is also plain English (a false friend); '
                                      'inside = a listed word of >= 5 letters occurs inside a longer name (Scunthorpe cases)')
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bench',
                   'name_audit_%s%s.json' % ('v2_' if V2M else 'v552_' if V552 else '', until))
with open(out, 'w', encoding='utf-8') as f:
    json.dump(res, f, indent=1, ensure_ascii=False)
# stdout: counts only (the file above holds the 12 most common plain first names as well)
print(json.dumps({k: v for k, v in res.items() if k not in ('most_common_first_names',)}, indent=1, ensure_ascii=False))
