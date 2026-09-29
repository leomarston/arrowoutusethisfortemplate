# socialsim/v2.py — the v2 world ("international"), as a patch over the SHIPPED model (shipped.py, v552 = SOC1+SOC1b+SOC1c).
#
# design/publish/social-intl.md §6 (T6 SOC-PY, PLAN-P §4.1; SPEC.md rulings 37(f) and 38). v2 = v552 + eight mechanisms that
# live, switched OFF, in the reference modules (population.py / names.py / data.py), switched on here:
#   M1 per-member country blocks          population.COUNTRY_BLOCKS
#   M2 stratified quantile jitter         population.U_JITTER
#   M3 country table v2 + aliases         data.use_countries_v2() (data_v2/countries_v2.tsv, regions_v2.tsv, buckets_v2.tsv)
#   M4 LOCAL only for unknown codes       population.LOCAL_V2 (+ world_for_home below: never the device offset)
#   M5 per-member culture                 population.MEMBER_CULTURE (+ data_v2/social_names_v2.json cultures)
#   M6 native-script name shares          names.NATIVE_T, names.KANA_P
#   M7 popularity head scaled to the list names.DRAW['headScaled'], ['tailUniformP']
#   M8 the world's own epoch              population.WORLD_EPOCH (the event calendar keeps core.EPOCH)
# and three T6 additions the calibration needed (same switch pattern, all off in the reference modules):
#   M9  shards: a weekly cohort split into independent cohorts of ~T players (+ a minimum of 3 shards for regulars and
#       returners)                        population.SHARD_TARGET, population.MIN_SHARDS
#   M10 member clock lag (0 = off in v2)  population.MEMBER_LAG_MIN
#   M11 per-row archetype tilt (Turkey)   population.ROW_TILT
# Each switch can be left off (apply(off={'M2', ...})) for ablations and the mutation checks.
# Swift: B2 ports these into PathCore/Social (SocialWorldModel v2 + aliases); the goldens come from tools/v2/fixtures_v2.py.
import os
from . import core as K, data as D, population as Pp, names as Nm, shipped as SH

MODEL = None                       # 'v2' once applied

# M8 (OD9 default, PLAN-P §6.1): Monday 2026-09-07 07:00 UTC = the expected live Monday (2026-10-05) minus 4 weeks. A later
# release only ages the world. Exactly 19 weeks after core.EPOCH, so world weeks and event weeks share their boundaries.
WORLD_EPOCH = 1788764400
assert (WORLD_EPOCH - K.EPOCH) % K.WEEK == 0

# M5: cultures appended AFTER the reference's 16 (names._tokkey keys a token by the culture's index, so the old indices never
# move). 'easteu' and 'sea' stay in the list (index stability) but no v2 row uses them.
NEW_CULTURES = ['sk', 'sl', 'cs', 'hu', 'ro', 'el', 'ru', 'uk', 'bg', 'hr', 'sr', 'th', 'vi', 'id', 'ms', 'tl', 'zh', 'he',
                'ptpt', 'fi', 'fa', 'sq', 'lt', 'lv', 'et', 'ur', 'hy', 'ka', 'az', 'kk', 'uz', 'af']

# M6 (ruling 38: "native-script name shares per the doc" = social-intl §7-2): % of first-name rows shown in the native script
# for cultures whose native form is not Latin (the rest show the Latin romanisation). Latin cultures keep 70 % accented
# spelling (the reference's 180/256). fa (Arabic script) and kk (Cyrillic), not in the doc's list: like ar / ru
# (DECISION). hy and ka: 0 — Armenian and Georgian script names are never shown, because the block lists carry no stems
# for those two scripts (social-intl §6.2 asks for native-script stems for every script that is shown); their Latin
# romanisations are screened like every Latin name.
NATIVE_SHARE = dict(jp=45, kr=50, zh=60, ar=30, ru=35, uk=35, bg=35, el=30, th=30, he=25, fa=30, hy=0, ka=0, kk=35)
KANA_P = 35                        # Japanese native names: 35 % katakana, 65 % hiragana (DECISION)

# M7: the shipped draw (40 % of first-name draws uniform over the 50 most common names, the rest floor(n u^2)) puts ~57 % of
# draws on the 50 most common names (the audit's Minjun x11 in a 39-name list). The REAL frequencies (Wikidata, adults born
# 1950-2008; tools/v2/build_name_data_v2.py) give the most common name 1.8-2.8 %, the top 10 12-15 %, the top 50 34-40 %.
# v2: a head of 20 % over min(50, n/6) names (scaled down under 300 names), and half of the rest uniform over the list:
# #1 ~2.1 %, top 10 ~10 %, top 50 ~35 % for a 600-name list (Monte Carlo in build/p/T6/names_mc.json).
DRAW = dict(SH.DRAW, headP=20, headScaled=True, tailUniformP=50)

DATA_V2 = D.DATA_V2
NAMES_FILE = os.environ.get('SOC_V2_NAMES') or os.path.join(DATA_V2, 'social_names_v2.json')   # env: a scratch build

ALL = ('M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9', 'M10', 'M11')

# M1: rows are apportioned inside 8 equal strata of every cohort (population.COUNTRY_STRATA), so a country samples the whole
# quantile range of each cohort (tools/v2/calib_v2.py: with one contiguous block per cohort the Country top 20 at launch was
# 15-18 same-cohort pairs and Turkey's level profile depended on where its thin slice fell in a few recent cohorts).
COUNTRY_STRATA = int(os.environ.get('SOC_V2_STRATA', '8'))
# M9 / M10 (added by T6 after the launch-week guards failed with M1-M8 alone; see tools/v2/calib_v2.py)
_SH = os.environ.get('SOC_V2_SHARD', 'mix')
SHARD_TARGET = (dict(dabbler=160.0, casual=80.0, regular=40.0, returner=40.0, enthusiast=40.0, grinder=40.0) if _SH == 'mix'
                else (float(_SH) or None))
MEMBER_LAG_MIN = float(os.environ.get('SOC_V2_LAG', '0'))
# M9 minimum (added by T6 after the full calibration: India's launch-week board had 24 dead daytime hours of 112 because
# the small ASIA_S band played on ~1 schedule per archetype a week; with >= 3 shards: 6). Enthusiasts and grinders are
# not forced (they shape the World top the phone guards pin). Env SOC_V2_MINSH=k (0 = none) for experiments.
_MS = int(os.environ.get('SOC_V2_MINSH', '3'))
_MSA = os.environ.get('SOC_V2_MINSH_ARCH', 'regular,returner').split(',')
MIN_SHARDS = {k: _MS for k in _MSA if k} if _MS > 1 else None
# M11 (added by T6: the phone guards on the Turkey board): Turkey's archetype mix (tools/v2/fit_tr.py). Under M1 a country is
# a thin slice of EVERY cohort of its bucket, so its level profile is the bucket's: at the phone's world age Turkey then had
# ~36 players above L1000 and ~50 between L62 and L84, where the phone's Turkey board showed 7 above L1349 (#6 1604, #7 1349)
# and ~80 between L62 and L84 (455 -> 375 while the player went L62 -> L84). v552 matched it by the luck of which 5 whole
# cohorts were Turkish. The tilt makes Turkey's players more dabbler / casual and less regular / returner / enthusiast than
# the bucket's (grinders and tourists unchanged); the TR weight is re-fitted with it (countries_v2.tsv).
# fit_tr.py grid on the final world (with the M9 minimum above; build/p/T6/fit_tr3.json): low 1.3 / high 0.3 with TR
# 0.3861 -> rank 456 at L62, slope 3.09 places per level, #2-#7 within -4 .. -25 % of the phone; the table keeps 0.39
# (calib: rank 456). Without the tilt (fit_tr.json, before the minimum): slope 2.32, #6 +49 %, #7 +71 %.
ROW_TILT = {'TR': dict(dabbler=1.3, casual=1.3, regular=0.3, returner=0.3, enthusiast=0.3)}


def apply(off=(), names_file=None):
    """Patch the imported modules into the v2 model (in memory, once, before building any World). `off` leaves the given
    switches off (ablation / mutation checks); M1 without M3 is the audit's prototype (blocks over the v1 buckets)."""
    global MODEL
    if MODEL is not None:
        return
    off = set(off)
    SH.apply()                                   # v552 first: archetypes, style mix, variants, draw, events
    MODEL = 'v2'
    SH.MODEL = 'v2'
    if 'M3' not in off:
        D.use_countries_v2(DATA_V2)
    for c in NEW_CULTURES:
        if c not in D.CULTURES:
            D.CULTURES.append(c)
    Pp.refresh_tables()
    Pp._check_containment()
    Pp.COUNTRY_BLOCKS = 'M1' not in off
    Pp.COUNTRY_STRATA = COUNTRY_STRATA
    Pp.SHARD_TARGET = SHARD_TARGET if 'M9' not in off else None
    Pp.MIN_SHARDS = MIN_SHARDS if 'M9' not in off else None
    Pp.MEMBER_LAG_MIN = MEMBER_LAG_MIN if 'M10' not in off else 0
    Pp.ROW_TILT = ROW_TILT if 'M11' not in off and ROW_TILT else None
    Pp.U_JITTER = 'M2' not in off
    Pp.LOCAL_V2 = 'M4' not in off
    Pp.MEMBER_CULTURE = 'M5' not in off
    if 'M8' not in off:
        Pp.WORLD_EPOCH = WORLD_EPOCH
    Nm.DATA_FILE = names_file or NAMES_FILE
    Nm._DATA = None
    if 'M6' not in off:
        Nm.NATIVE_T = {c: (p * 256 + 50) // 100 for c, p in NATIVE_SHARE.items()}
        Nm.KANA_P = KANA_P
    if 'M7' not in off:
        Nm.DRAW = DRAW
    assert Nm.DRAW is not None                    # v2 needs drawn nicknames (a block cohort has no single culture for slots)


def world_for_home(code, seed=Pp.WORLD_SEED):
    """(World, board ISO) for a device region code (M3 + M4). A row, alias or numeric region plays on the shared world only
    (two friends see the same boards); a 2-letter code no table knows gets its own LOCAL partition: offset 0 and culture
    'en' (static, never the device's clock or language)."""
    kind, iso = D.resolve_region(code)
    if kind == 'unknown':
        if len(iso) != 2 or not iso.isalpha():
            iso = 'US'                            # the app's fallbackCountry for anything that is not a 2-letter code
            return Pp.World(seed=seed), iso
        return Pp.World(seed=seed, local=(iso, 0, 'en')), iso
    return Pp.World(seed=seed), iso
