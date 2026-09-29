#!/usr/bin/env python3
"""calib_table_soc1c.py — renders the SOC1c before/after table (build/soc1c/calibration.md) from
    build/soc1c/calib-before.json  (calib_s2.py v552 … --soc1b: SOC1b's shipped parameters — unique names, Sky Jump 5/7/9)
    build/soc1c/calib-after.json   (calib_s2.py v552 …: the shipped model with drawn names + Sky Jump stage 3 = 10 levels)
    build/soc1c/before/name_audit_v552_2031-09-25.json + design/social/bench/name_audit_v552_2031-09-25.json (whole world)
    build/soc1b/bench/summary.json + build/soc1c/bench/summary.json    (the Swift 52-week benches, before / after)
    build/soc1b/evidence/soc1-perf-release.json + build/soc1c/evidence/soc1-perf-release.json   (Swift -O perf)
    python3 design/social/tools/calib_table_soc1c.py
"""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, '..', '..', '..'))


def load(p):
    try:
        return json.load(open(os.path.join(APP, p)))
    except Exception:
        return None


B, A = load('build/soc1c/calib-before.json'), load('build/soc1c/calib-after.json')
NB, NA = load('build/soc1c/before/name_audit_v552_2031-09-25.json'), load('design/social/bench/name_audit_v552_2031-09-25.json')
BB, BA = load('build/soc1b/bench/summary.json'), load('build/soc1c/bench/summary.json')
PB, PA = load('build/soc1b/evidence/soc1-perf-release.json'), load('build/soc1c/evidence/soc1-perf-release.json')
L = []
w = L.append


def pct(x):
    return '%d %%' % round(100 * x) if isinstance(x, (int, float)) else str(x)


def lst(x):
    return ' / '.join(str(int(v)) if isinstance(v, float) and v == int(v) else str(v) for v in x)


def row(*cells):
    w('| ' + ' | '.join(str(c) for c in cells) + ' |')


w('# SOC1c — drawn nicknames (duplicates allowed) and Sky Jump stage 3 = 10 levels')
w('')
w('Orchestrator (25 Sep): (1) allow DUPLICATE display names like the real game (two "Bobby" in its World top 15) so plain first '
  'names reach the phone\'s ~14 % and names with digits drop toward its ~7 %; identity stays the player index (gid); blocklists, '
  'length rules and determinism kept; (2) Sky Jump stage 3 = the phone\'s 10 levels / 10000, from social.json so C3\'s EventRules '
  'and the opponents\' curves switch together. **before** = SOC1b\'s shipped parameters (unique first-come names, Sky 5/7/9), '
  '**after** = SOC1c (design/social/tools/socialsim/shipped.py = PathCore `SocialWorldModel.v552` + `SocialConfig.default`). '
  'Both columns come from design/social/tools/calib_s2.py on the Python reference (bit-exact with the Swift port: '
  'Tests/Fixtures/soc_v552_*.json), the same scenarios. The name classes are calib_s2.py `classify` on the phone\'s ~113 names '
  '(research/social-dynamics.md §H) and on ours. SOC1c also fixed a SOC1b rounding bias it found on the way: the per-cohort style '
  'counts gave the LAST style (\'leet\') the rounding remainder, several times its 3 % in small cohorts — and the World top is made '
  'of small cohorts (S150 / F689 / Y775 in every install\'s World top 10); the shipped model now apportions the styles '
  'systematically (population.STYLE_SYSTEMATIC, `SocialNameStyle.systematic`), see "Style counts by cohort size".')
w('')
w('## Names on the boards (pooled: World top 23, Turkey, Weekly groups, Streak Race boards, Rocket lanes)')
w('')
row('class', 'phone (v552)', 'before (SOC1b)', 'after (SOC1c)', 'note')
row('---', '---', '---', '---', '---')
no, nb, na = A['names_observed'], B['names_ours'], A['names_ours']
notes = {'default': 'player_xxxxxxx (unchanged: the custom shares are SOC1b\'s)',
         'firstName': 'the goal: drawn with replacement, a plain first name no longer needs a number',
         'capitalised': 'Tetety-like handles, name+suffix (Limminator-like), capitalised words',
         'lowercase': 'rng, ecr, karl, freedom-like',
         'camelCase': 'SneakyFalconer51-like (a third with 2 digits)',
         'allCaps': 'ASLAN, DER, OKTOBERFEST-like',
         'digitsLeet': 'the goal: numbers on 5 % of the handles + the leet L8M/K710/0xBK (3 % at every cohort size)'}
for k in ('default', 'firstName', 'capitalised', 'lowercase', 'camelCase', 'allCaps', 'digitsLeet', 'other'):
    row(k, pct(no['pooled']['share'][k]), pct(nb['pooled']['share'][k]), pct(na['pooled']['share'][k]), notes.get(k, ''))
row('names classified', no['pooled']['n'], nb['pooled']['n'], na['pooled']['n'], '')
w('')
w('Per board (after): ' + '; '.join('%s default %s / first names %s / digits %s' % (
    b, pct(na[b]['share']['default']), pct(na[b]['share']['firstName']), pct(na[b]['share']['digitsLeet']))
    for b in ('world', 'turkey', 'weekly', 'streak', 'rocket')) + '.')
w('')
if B.get('styles_ours') and A.get('styles_ours'):
    sb_, sa_ = B['styles_ours'], A['styles_ours']
    w('## Style counts by cohort size (custom names; the weight is the target at every size)')
    w('')
    row('style', 'weight (after)', 'before n<10 / n<50 / n>=50', 'after n<10 / n<50 / n>=50', 'World top 100 before / after')
    row('---', '---', '---', '---', '---')
    for st in sa_['weights']:
        row(st, pct(sa_['weights'][st]) if sa_['weights'][st] >= 0.01 else '%.1f %%' % (100 * sa_['weights'][st]),
            ' / '.join('%.1f %%' % (100 * sb_['byCohortSize'][b]['share'].get(st, 0)) for b in ('n<10', 'n<50', 'n>=50')),
            ' / '.join('%.1f %%' % (100 * sa_['byCohortSize'][b]['share'].get(st, 0)) for b in ('n<10', 'n<50', 'n>=50')),
            '%s / %s' % (sb_['worldTop100'].get(st, 0), sa_['worldTop100'].get(st, 0)))
    row('custom names counted', '', ' / '.join(str(sb_['byCohortSize'][b]['custom']) for b in ('n<10', 'n<50', 'n>=50')),
        ' / '.join(str(sa_['byCohortSize'][b]['custom']) for b in ('n<10', 'n<50', 'n>=50')),
        'player_ %s / %s' % (sb_['worldTop100'].get('default', 0), sa_['worldTop100'].get('default', 0)))
    w('')
    w('World top 15 at 12:09 — phone: player_ah8prp7, Winner, ezbee, Tetety, Sunshine, Limminator, Crazzijj, Han, Bobby, Caco17, '
      'Neil, Debbie, SweetiePie, Alex56k, Bobby. Before: ' + ', '.join(sb_['worldTop15']) + '. After: ' + ', '.join(sa_['worldTop15'])
      + '. (The levels are the same in both columns: only the names moved.)')
    w('')
w('## Repeated names (identity is the gid; a repeat is two players showing the same name, case/accent-insensitive)')
w('')
row('observable', 'phone (v552)', 'before (SOC1b)', 'after (SOC1c)', 'note')
row('---', '---', '---', '---', '---')
do, db, da = A['dups_observed'], B['dups_ours'], A['dups_ours']


def dline(d):
    return '%s repeated pairs in %s row pairs (rate %s); %s of %s boards' % (d['pairs'], d['rowPairs'], d['pairRate'], d['boardsWithDup'], d['boards'])


row('pair rate inside a board (pooled)', dline(do['pooled']), dline(db['pooled']), dline(da['pooled']),
    'phone 95 % CI 1.5e-5 … 3.2e-3 (one event); the target band of the tests')
row('Streak Race boards (50 rows)', dline(do['streak']), dline(db['streak']), dline(da['streak']), 'the best-measured board')
row('World top 23', dline(do['world']), dline(db['world']), dline(da['world']),
    'phone: Bobby #9 + Bobby #15; ours: 61 windows of a slowly changing top (not independent)')
row('any two board-like names match', '-', db['anyTwoNames']['pairRate'], da['anyTwoNames']['pairRate'],
    '60k different non-tourist players; most common after: ' + ', '.join('%s x%s' % (k, v) for k, v in da['anyTwoNames']['mostCommon'][:6]))
ex = [e for e in da['streak']['examples'] + da['pooled']['examples']][:6]
row('examples (after)', 'Bobby, Bobby', '-', '; '.join(' + '.join(e) for e in ex), '')
if NB and NA:
    row('whole world to 2031 (name_audit.py --v552)', '-',
        '%s players, %s dup, %s blocked, %s > 16' % (NB['players'], NB['fnv_duplicates'], NB['blocked_shown'], NB['longer_than_16']),
        '%s players, %s distinct names, %s blocked, %s > 16; board-like pair rate %s; verdict %s' % (
            NA['players'], NA.get('distinct_names'), NA['blocked_shown'], NA['longer_than_16'], NA.get('board_like_pair_rate'),
            NA.get('verdict')),
        'rule: 0 blocked, 0 > 16, repeats at the phone\'s rate (was: 0 duplicates)')
    if NA.get('most_common_first_names'):
        w('')
        w('Most common first names in the whole world to 2031 (after): ' + ', '.join('%s x%s' % (k, v) for k, v in NA['most_common_first_names'][:10]) + '.')
w('')
w('## Sky Jump')
w('')
row('observable', 'phone (v552)', 'before (SOC1b)', 'after (SOC1c)', 'note')
row('---', '---', '---', '---', '---')
kp, kb, ka = A['sky']['phone'], B['sky']['ours'], A['sky']['ours']
row('levels per stage', '5 / 7 / 10 ("Pass 10 Levels in a row", sessions 2 + 3)', lst([kb[s]['levels'] for s in ('stage1', 'stage2', 'stage3')]),
    lst([ka[s]['levels'] for s in ('stage1', 'stage2', 'stage3')]), 'social.json events.skyJump.levels (C3 + SOC read it)')
row('stage 3 curve (example)', ' '.join(map(str, kp['stage3'])), ' '.join(map(str, kb['stage3']['example'])), ' '.join(map(str, ka['stage3']['example'])),
    'phone S3 won 10/10 with 6 other winners')
row('stage 3 drop per level (median) / first drop', '8-9 / 0', '%s / %s' % (kb['stage3']['drop_per_level_median'], kb['stage3']['first_drop_median']),
    '%s / %s' % (ka['stage3']['drop_per_level_median'], ka['stage3']['first_drop_median']), 'drop 7.5-9.5 (was 7.5-10)')
row('stage 3 winners (median, range) / share', '7 / 1428 (10000/7)', '%s %s / %s' % (kb['stage3']['winners_median'], kb['stage3']['winners_range'], int(kb['stage3']['share_median'])),
    '%s %s / %s' % (ka['stage3']['winners_median'], ka['stage3']['winners_range'], int(ka['stage3']['share_median'])), 'winners 5-9 (was 14-24, a DECISION)')
for s, ph in (('stage1', '100 82 64 ? 47 -> 7 (714)'), ('stage2', '100 100 88 75 62 49 36 -> 15 (466)')):
    row('%s curve (example) / winners / share' % s, ph, '%s / %s / %s' % (' '.join(map(str, kb[s]['example'])), kb[s]['winners_range'], int(kb[s]['share_median'])),
        '%s / %s / %s' % (' '.join(map(str, ka[s]['example'])), ka[s]['winners_range'], int(ka[s]['share_median'])), 'unchanged')
w('')
w('## Everything else (unchanged by SOC1c; the same harness, to show nothing else moved)')
w('')
row('observable', 'phone (v552)', 'before (SOC1b)', 'after (SOC1c)')
row('---', '---', '---', '---')
wp, wb, wa = A['world']['phone'], B['world']['ours'], A['world']['ours']
row('World #1 / #2 / #3 / #15 / #23 at 12:09', lst([wp['top23'][i] for i in (0, 1, 2, 14, 22)]), lst([wb['top23'][i] for i in (0, 1, 2, 14, 22)]),
    lst([wa['top23'][i] for i in (0, 1, 2, 14, 22)]))
tp, tb, ta = A['turkey']['phone'], B['turkey']['ours'], A['turkey']['ours']
row('Turkey rank at L62/64/68/72/77/80/84', lst([r for _, r in tp['ranks']]), lst([r for _, r in tb['ranks']]), lst([r for _, r in ta['ranks']]))
kp2, kb2, ka2 = A['weekly']['phone'], B['weekly']['ours']['phoneHour'], A['weekly']['ours']['phoneHour']
row('Weekly idle +3.5 h -> +11.2 h / movers', '%s / %s' % (pct(kp2['static_3h30_11h12']), kp2['movers_3h30_9h']),
    '%s / %s' % (pct(kb2['static_3h30_11h12']), kb2['movers_3h30_9h']), '%s / %s' % (pct(ka2['static_3h30_11h12']), ka2['movers_3h30_9h']))
sp, sb, sa = A['streak']['phone'], B['streak']['ours']['phoneHour'], A['streak']['ours']['phoneHour']
row('Streak top 6 at +3 h', lst(sp['top6_3h']), lst(sb['top6_3h']), lst(sa['top6_3h']))
row('Streak ties at the join (alphabetical)', 'Babs, ChillRat … karl, KernowCat …', ', '.join((B['streak']['ours'].get('tiesAtJoin') or [])[:5]),
    ', '.join((A['streak']['ours'].get('tiesAtJoin') or [])[:5]))
rb, ra = B['rocket']['ours'], A['rocket']['ours']
row('Rocket stage 1 first finish q1/median/q3', '6, 8, 19', lst(rb['stage1']['firstFinishMin_q1_med_q3']), lst(ra['stage1']['firstFinishMin_q1_med_q3']))
w('')
if BB and BA:
    w('## The 52-week bench (Swift SocialBenchTests, one user per profile from 5 Oct 2026)')
    w('')
    w('| metric | before active / casual / absent | after active / casual / absent |')
    w('|---|---|---|')

    def g(S, p, *ks):
        x = S[p]
        for k in ks:
            x = x.get(k, '-') if isinstance(x, dict) else '-'
        return x
    for lab, ks, f in [('final level', ('final_level',), str), ('World rank', ('world_rank_final',), str),
                       ('Country rank', ('country_rank_final',), str),
                       ('Weekly win / podium', ('weekly',), lambda v: '%s / %s' % (pct(v['win']), pct(v['podium']))),
                       ('Streak Race 1st / top 3', ('streak_race',), lambda v: '%s / %s' % (pct(v['first']), pct(v['top3']))),
                       ('Rocket stage 1 / 2 / 3 win', ('rocket', 'by_stage'), lambda v: ' / '.join(pct(v[s]['win']) for s in ('1', '2', '3'))),
                       ('Sky Jump stage wins / runs, mean share', ('sky',), lambda v: '%s / %s, %d' % (v['wins'], v['n'], v['mean_share'])),
                       ('invariants: backwards / duplicate rows (same player twice) / country > world / bad pages', ('checks',),
                        lambda v: '%s / %s / %s / %s' % (v['backwards'], v['dup_rows'], v['rank_inconsistent'], v['api_bad_pages'])),
                       ('views showing a repeated NAME (two players) / pair rate', ('checks',),
                        lambda v: ('%s of %s / %.2g' % (v['name_repeat_views'], v['views'], v['name_repeat_pairs'] / max(1, v['row_pairs'])))
                        if 'name_repeat_views' in v else 'not measured (SOC1b counted a repeated name as a duplicate row: 0)')]:
        w('| %s | %s | %s |' % (lab, ' / '.join(f(g(BB, p, *ks)) for p in ('active', 'casual', 'absent')),
                                ' / '.join(f(g(BA, p, *ks)) for p in ('active', 'casual', 'absent'))))
    if BA.get('nameRepeats'):
        nr = BA['nameRepeats']
        w('| repeated names, pooled over the three users\' boards (asserted inside the phone\'s 1.5e-5 … 3.2e-3) | - | %s pairs in %s row pairs (%.2g) |'
          % (nr['pairs'], nr['rowPairs'], nr['rate']))
    w('')
if PB and PA:
    w('## Query budgets (Swift -O on this Mac, p95 ms; budgets unchanged; all social work runs off the main thread)')
    w('')
    w('| metric | budget | before (SOC1b) | after (SOC1c) |')
    w('|---|---|---|---|')
    for k in sorted(PA):
        if isinstance(PA[k], dict) and 'p95_ms' in PA[k]:
            b = PB.get(k, {}).get('p95_ms', '-') if isinstance(PB.get(k), dict) else '-'
            fmt = lambda v: ('%.3f' % v) if isinstance(v, float) else str(v)
            w('| %s | %s | %s | %s |' % (k, PA[k].get('budget_ms') or 'report only', fmt(b), fmt(PA[k]['p95_ms'])))
    w('')
out = os.path.join(APP, 'build/soc1c/calibration.md')
open(out, 'w').write('\n'.join(L) + '\n')
print('wrote', out, len(L), 'lines')
