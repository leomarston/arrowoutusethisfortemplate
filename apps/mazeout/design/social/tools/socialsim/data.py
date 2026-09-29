# socialsim/data.py — static tables of the simulated world: countries, cultures, archetypes, diurnal profiles, name data.
import os, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, '..', '..', 'data'))

def _lines(name):
    out = []
    with open(os.path.join(DATA, name), encoding='utf-8') as f:
        for l in f:
            l = l.rstrip('\n')
            if not l or l.startswith('#'):
                continue
            out.append(l)
    return out

# ------------------------------------------------------------------ countries

class CountryRow:
    __slots__ = ('iso', 'weight', 'off', 'culture', 'bucket', 'mix')
    def __init__(self, iso, weight, off, culture, bucket, mix=None):
        self.iso = iso; self.weight = weight; self.off = off; self.culture = culture; self.bucket = bucket
        # v2 (M5): the row's culture mix [(culture, weight), ...]; None = the single `culture` (the reference / v552)
        self.mix = mix

COUNTRY_ROWS = []
for l in _lines('countries.tsv'):
    p = l.split('\t')
    COUNTRY_ROWS.append(CountryRow(p[0], float(p[1]), int(p[2]), p[3], p[4]))

BUCKETS = ['AMER_W', 'AMER_E', 'AMER_S', 'EUR_W', 'EUR_C', 'EUR_E', 'ASIA_S', 'ASIA_SE', 'ASIA_E']
HOME_FLOOR_SHARE = 0.006          # the user's own country is at least 0.6 % of the world

# Culture for a home country that is not in the table (ISO region -> culture); default 'en'.
EXTRA_CULTURE = {
    'VE': 'es', 'EC': 'es', 'UY': 'es', 'PY': 'es', 'BO': 'es', 'CR': 'es', 'PA': 'es', 'GT': 'es', 'DO': 'es', 'PR': 'es',
    'SV': 'es', 'HN': 'es', 'NI': 'es', 'CU': 'es', 'AO': 'pt', 'MZ': 'pt', 'LU': 'fr', 'MC': 'fr', 'SN': 'fr', 'CI': 'fr',
    'MA': 'ar', 'DZ': 'ar', 'TN': 'ar', 'JO': 'ar', 'LB': 'ar', 'KW': 'ar', 'QA': 'ar', 'BH': 'ar', 'OM': 'ar', 'IQ': 'ar',
    'SK': 'pl', 'SI': 'easteu', 'HR': 'easteu', 'RS': 'easteu', 'BG': 'easteu', 'LT': 'easteu', 'LV': 'easteu', 'EE': 'nordic',
    'IS': 'nordic', 'BY': 'easteu', 'KZ': 'easteu', 'AZ': 'tr', 'CY': 'easteu', 'PK': 'in', 'BD': 'in', 'LK': 'in', 'NP': 'in',
    'MM': 'sea', 'KH': 'sea', 'LA': 'sea', 'CN': 'en', 'MO': 'en', 'NG': 'en', 'KE': 'en', 'GH': 'en', 'JM': 'en', 'TT': 'en',
}

# ------------------------------------------------------------------ archetypes
# lam  = levels per PLAYED day, as a piecewise-linear table over u in [0,1] (u = the member's quantile inside its cohort)
# life = active lifetime in days over u; its slope must be >= the cohort's join spread (1 day for daily, 7 for weekly
#        cohorts) so that a higher-u member's active interval CONTAINS a lower-u member's (=> level monotone in u).
# rho  = probability that a given day is a play day; sess = (min,max) sessions on a play day; first = install-session
#        levels (lo, hi) over u; style weights: probability of each nickname style (see names.py) — 'default' first.
ARCHETYPES = [
    dict(key='tourist', share=0.400, daily=True,
         lam=([0, 1], [4.0, 20.0]), life=([0, 1], [0.005, 1.2]), rho=1.0, sess=(1, 2), first=(2.0, 12.0),
         custom=0.15, avatar=(0.08, 0.38)),
    dict(key='dabbler', share=0.220, daily=False,
         lam=([0, 1], [6.0, 30.0]), life=([0, 1], [1.5, 12.0]), rho=0.55, sess=(1, 2), first=(5.0, 14.0),
         lapse=(20.0, 90.0), custom=0.30, avatar=(0.10, 0.42)),
    dict(key='casual', share=0.180, daily=False,
         lam=([0, 0.6, 0.9, 1], [5.0, 10.0, 18.0, 25.0]), life=([0, 0.5, 1], [12.0, 35.0, 90.0]), rho=0.45, sess=(1, 2),
         first=(6.0, 14.0), lapse=(45.0, 200.0), custom=0.45, avatar=(0.12, 0.45)),
    dict(key='regular', share=0.110, daily=False,
         lam=([0, 0.5, 0.9, 1], [10.0, 18.0, 32.0, 45.0]), life=([0, 0.5, 1], [40.0, 140.0, 400.0]), rho=0.70,
         sess=(1, 3), first=(6.0, 14.0), lapse=(60.0, 365.0), custom=0.60, avatar=(0.12, 0.47)),
    dict(key='enthusiast', share=0.045, daily=False,
         lam=([0, 0.5, 0.9, 1], [20.0, 35.0, 58.0, 75.0]), life=([0, 0.5, 1], [150.0, 500.0, 1600.0]), rho=0.88,
         sess=(2, 4), first=(8.0, 16.0), lapse=(90.0, 500.0), custom=0.72, avatar=(0.14, 0.50)),
    dict(key='grinder', share=0.006, daily=False,
         lam=([0, 0.5, 0.9, 0.98, 1], [42.0, 60.0, 79.0, 93.0, 128.0]), life=([0, 0.5, 1], [250.0, 900.0, 3200.0]),
         rho=0.97, sess=(3, 6), first=(8.0, 16.0), lapse=(90.0, 500.0), custom=0.86, avatar=(0.15, 0.55)),
    dict(key='returner', share=0.039, daily=False,
         lam=([0, 1], [8.0, 40.0]), life=([0, 1], [3.0, 32.0]), rho=0.55, sess=(1, 2), first=(6.0, 14.0),
         life2=([0, 1], [30.0, 500.0]), gap=(15.0, 150.0), lapse=(30.0, 120.0), custom=0.45, avatar=(0.12, 0.45)),
]
ARCH_KEYS = [a['key'] for a in ARCHETYPES]

LAPSE_DAY_P = 0.16             # share of a cohort's play days on which its LAPSED members come back
LAPSE_VOLUME = 0.5             # ... playing half their usual daily volume
PACE_RANGE = (0.40, 0.65)       # levels per minute inside a session (a level every 1.5-2.5 min), per cohort
FIRST_PACE = 0.55               # levels per minute in the install session (FTUE boards are quick)
SESSION_GAP = 10.0              # minutes between two sessions of one cohort-day
DAY_BUDGET = 1200.0             # max minutes of play windows per cohort-day (pace is raised if needed)
PATTERN = 28                    # days in a cohort's repeating daily-volume pattern (multiple of 7: weekday-aligned)
WEEKDAY_VOLUME = [0.92, 0.90, 0.92, 0.95, 1.02, 1.22, 1.18]      # Mon..Sun
VOLUME_RANGE = (0.55, 1.45)

# Local-hour play density (relative), weekdays and weekends. A day's session starts are drawn from these.
DIURNAL_WEEKDAY = [0.9, 0.5, 0.3, 0.2, 0.15, 0.2, 0.5, 1.2, 1.6, 1.4, 1.3, 1.4, 1.9, 1.8, 1.5, 1.5, 1.7, 2.0, 2.3, 2.6,
                   2.9, 3.0, 2.6, 1.7]
DIURNAL_WEEKEND = [1.2, 0.8, 0.5, 0.3, 0.2, 0.2, 0.3, 0.6, 1.0, 1.5, 1.8, 2.0, 2.1, 2.1, 2.0, 2.0, 2.0, 2.1, 2.3, 2.5,
                   2.7, 2.8, 2.5, 1.9]

def _cdf(ws):
    c = [0.0]
    for w in ws:
        c.append(c[-1] + w)
    tot = c[-1]
    return [x / tot for x in c]

DIURNAL_CDF = (_cdf(DIURNAL_WEEKDAY), _cdf(DIURNAL_WEEKEND))

# ------------------------------------------------------------------ weekly join volume

def weekly_joins(p):
    """New players in join period p (7 days from EPOCH + p weeks). Launch bump + slowly growing plateau, capped."""
    pf = float(p)
    plateau = 12000.0 * (1.0 + 0.6 * pf / (pf + 40.0))
    bump = 2.0 / (2.0 + pf)
    return plateau + 18000.0 * bump * bump

# ------------------------------------------------------------------ names

CULTURES = ['tr', 'de', 'fr', 'es', 'pt', 'it', 'nl', 'nordic', 'pl', 'easteu', 'in', 'sea', 'jp', 'kr', 'ar', 'en']

def fold(s):
    """ASCII fold for uniqueness keys and the 'folded' spelling variant (ı->i, ß->ss, ł->l, then NFKD strip marks)."""
    s = s.replace('ı', 'i').replace('İ', 'I').replace('ß', 'ss').replace('ł', 'l').replace('Ł', 'L')
    s = s.replace('ø', 'o').replace('Ø', 'O').replace('æ', 'ae').replace('Æ', 'Ae').replace('ð', 'd').replace('þ', 'th')
    s = unicodedata.normalize('NFKD', s)
    return ''.join(ch for ch in s if not unicodedata.combining(ch))

def key(s):
    return fold(s).lower()

BLOCK_SUB = [b.lower() for b in _lines('blocklist_substring.txt')]
BLOCK_TOK = set(b.lower() for b in _lines('blocklist_token.txt'))
BLOCK_NAMES = set(b.lower() for b in _lines('block_names.txt'))

# ------------------------------------------------------------------ v2 (design/publish/social-intl.md §6, M3/M5; OFF by default)
# The reference and v552 never call use_countries_v2(): their table stays countries.tsv (49 rows, 9 buckets). The v2 model
# (socialsim/v2.py) switches to design/social/data_v2: every region iOS can report resolves to a row, an alias or a numeric
# (UN M.49) representative; every bucket has ONE schedule offset (BUCKET_OFF) that all its rows are within +-60 min of;
# every row has a culture mix drawn per member (M5).
COUNTRIES_V2 = False
BUCKET_OFF = None            # bucket -> the cohorts' schedule offset (minutes); None = each cohort uses its picked row's
REGION = {}                  # code -> (kind, target): kind 'row' | 'alias' | 'numeric'; target = the board's ISO
DATA_V2 = os.path.normpath(os.path.join(HERE, '..', '..', 'data_v2'))

def _tsv(path):
    out = []
    with open(path, encoding='utf-8') as f:
        for l in f:
            l = l.rstrip('\n')
            if not l or l.startswith('#'):
                continue
            out.append(l.split('\t'))
    return out

def parse_mix(s):
    """'nl:0.6,fr:0.4' -> [('nl', 0.6), ('fr', 0.4)]; 'en' -> [('en', 1.0)]."""
    out = []
    for part in s.split(','):
        if ':' in part:
            c, w = part.split(':')
            out.append((c, float(w)))
        else:
            out.append((part, 1.0))
    return out

def use_countries_v2(folder=None):
    """Replace the country table, buckets and region map by the v2 files (in memory, once, before building a World)."""
    global COUNTRY_ROWS, BUCKETS, BUCKET_OFF, REGION, COUNTRIES_V2
    folder = folder or DATA_V2
    BUCKETS = []
    BUCKET_OFF = {}
    for b, off in _tsv(os.path.join(folder, 'buckets_v2.tsv')):
        BUCKETS.append(b)
        BUCKET_OFF[b] = int(off)
    COUNTRY_ROWS = []
    for p in _tsv(os.path.join(folder, 'countries_v2.tsv')):
        mix = parse_mix(p[3])
        row = CountryRow(p[0], float(p[1]), int(p[2]), mix[0][0], p[4], mix)
        assert row.bucket in BUCKET_OFF and abs(row.off - BUCKET_OFF[row.bucket]) <= 60, (row.iso, row.off, row.bucket)
        COUNTRY_ROWS.append(row)
    REGION = {}
    for p in _tsv(os.path.join(folder, 'regions_v2.tsv')):
        REGION[p[0]] = (p[1], p[2])
    COUNTRIES_V2 = True

def resolve_region(code):
    """v2: the board a device region code plays on. ('row'|'alias'|'numeric', ISO of the board) or ('unknown', code)
    (a 2-letter code no table knows: a device-only LOCAL partition, M4)."""
    code = (code or '').upper()
    if code in REGION:
        return REGION[code]
    return ('unknown', code)
