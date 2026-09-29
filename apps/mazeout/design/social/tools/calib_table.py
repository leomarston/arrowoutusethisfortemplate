#!/usr/bin/env python3
"""calib_table.py — renders the SOC1b before/after calibration table (build/soc1b/calibration.md) from
    build/soc1b/calib-before.json  (calib_s2.py v552 … --soc1: SOC1's shipped parameters)
    build/soc1b/calib-after.json   (calib_s2.py v552 …: the recalibrated shipped model)
    build/soc1/bench/summary.json + build/soc1b/bench/summary.json    (the Swift 52-week benches, before / after)
    build/soc1/evidence/soc1-perf-release.json + build/soc1b/evidence/soc1-perf-release.json   (Swift -O perf)
    python3 design/social/tools/calib_table.py
"""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
B = json.load(open(os.path.join(APP, 'build/soc1b/calib-before.json')))
A = json.load(open(os.path.join(APP, 'build/soc1b/calib-after.json')))


def load(p):
    try:
        return json.load(open(os.path.join(APP, p)))
    except Exception:
        return None


BB, BA = load('build/soc1/bench/summary.json'), load('build/soc1b/bench/summary.json')
PA = load('build/soc1b/evidence/soc1-perf-release.json')
# SOC1's clean run B (build/soc1/perf-runs.txt, load ~3.7): its saved JSON is from a run at load 60-180 (its own note)
PB = {k: {'p95_ms': v} for k, v in dict(
    [('page50.world.top', 0.273), ('page50.country.aroundMe', 0.128), ('page50.world.aroundMe', 0.631), ('page.weekly10', 0.013),
     ('page.streak50', 0.117), ('y3.worldRank', 1.165), ('y3.top100', 0.035), ('y3.countryRank', 0.082), ('y3.neighbours', 0.106),
     ('y3.materialise50rows', 0.004), ('y3.worldNeighbours', 4.018), ('y3.page50.world.top', 1.284),
     ('y3.page50.country.aroundMe', 0.329)]).items()}
L = []
w = L.append


def pct(x):
    return '%d %%' % round(100 * x) if isinstance(x, (int, float)) else str(x)


def lst(x):
    return ' / '.join(str(int(v)) if isinstance(v, float) and v == int(v) else str(v) for v in x)


def row(what, phone, before, after, note=''):
    w('| %s | %s | %s | %s | %s |' % (what, phone, before, after, note))


w('# SOC1b — the offline world recalibrated to phone session 2')
w('')
w('Evidence: research/social-dynamics.md (phone session 2, 25 Sep 2026 12:07-14:47 TRT: Weekly group x6, World top 15-31, '
  'Turkey top 7 + the player\'s rank x7, Streak Race 50 rows x6, Rocket Race x3, Sky Jump stages 2-3, a name-style breakdown). '
  '**before** = SOC1\'s shipped parameters (25 Sep 11:27), **after** = the recalibrated shipped model (design/social/tools/socialsim/'
  'shipped.py = PathCore `SocialWorldModel.v552` + `SocialConfig.default`). Measured by design/social/tools/calib_s2.py on the '
  'Python reference (bit-exact with the Swift port: Tests/Fixtures/soc_v552_*.json), the same scenarios for both columns. '
  'Phone times are TRT (UTC+3). One phone sample per statistic, so the "after" column aims at the phone\'s shape, not its '
  'every digit; where a gap remains it is stated.')
w('')
w('| what | phone (v552) | before (SOC1) | after (SOC1b) | note |')
w('|---|---|---|---|---|')
# names
no, nb, na = A['names_observed'], B['names_ours'], A['names_ours']
for k in ('default', 'firstName', 'capitalised', 'lowercase', 'camelCase', 'allCaps', 'digitsLeet'):
    row('names on the boards: %s' % k, pct(no['pooled']['share'][k]), pct(nb['pooled']['share'][k]), pct(na['pooled']['share'][k]),
        {'default': 'player_xxxxxxx; phone 9/49 Streak, 1/9 Weekly, 2/23 World, 3/20 Turkey',
         'firstName': 'plain first names are a finite list (~3.3k) and every nickname is unique, so most carry a number',
         'digitsLeet': 'numbers mostly on first names (Kate23); leet handles L8M/K710/0xBK are ~3 %',
         'capitalised': 'Tetety/Ttam-like handles, first name+suffix (Limminator-like)',
         'allCaps': 'case variants ASLAN/DER (collision-free: uniqueness is case-insensitive)'}.get(k, ''))
for b in ('streak', 'weekly', 'world', 'turkey', 'rocket'):
    row('  default share, %s' % b, pct(no[b]['share']['default']), pct(nb[b]['share']['default']), pct(na[b]['share']['default']))
row('uniqueness / blocklist (whole world to 2031)', 'two "Bobby" in the World top 15 (no uniqueness)', '4.9 M names, 0 dup (reference)',
    '4,875,040 names, 0 dup, 0 blocked, 0 > 16 chars', 'design/social/bench/name_audit_v552_2031-09-25.json')
# world
wp, wb, wa = A['world']['phone'], B['world']['ours'], A['world']['ours']
row('World #1 / #2 / #3 / #15 / #23 at 12:09', lst([wp['top23'][i] for i in (0, 1, 2, 14, 22)]),
    lst([wb['top23'][i] for i in (0, 1, 2, 14, 22)]), lst([wa['top23'][i] for i in (0, 1, 2, 14, 22)]), 'SOC1\'s level calibration kept')
row('World top 15 static over 1.9 h (12:09 -> 14:01)', '9 of 15', '%d (median over 60 windows %s)' % (wb['static15_1h52'], wb['static15_1h52_over60windows']['median']),
    '%d (median over 60 windows %s)' % (wa['static15_1h52'], wa['static15_1h52_over60windows']['median']), 'grinders: 1-3 longer sessions a day')
row('World top 15: biggest climb in 1.9 h', '+66 (Crazzijj, ~35/h), +40', 'median %s, max %s' % (wb['static15_1h52_over60windows']['maxGainMedian'], wb['static15_1h52_over60windows']['maxGainMax']),
    'median %s, max %s' % (wa['static15_1h52_over60windows']['maxGainMedian'], wa['static15_1h52_over60windows']['maxGainMax']), 'a mover plays 24-39 levels/h')
# turkey
tp, tb, ta = A['turkey']['phone'], B['turkey']['ours'], A['turkey']['ours']
row('Turkey: player rank at L62/64/68/72/77/80/84', lst([r for _, r in tp['ranks']]), lst([r for _, r in tb['ranks']]), lst([r for _, r in ta['ranks']]),
    'the phone\'s times; honeymoon + TR weight 0.30')
row('Turkey: places per level won (L62 -> L84)', tp['slope'], tb['slope'], ta['slope'])
row('Turkey top 7 at 12:11', lst(tp['top7']), lst(tb['top7']), lst(ta['top7']), '#1 on the phone is a lone outlier (= World #10)')
# weekly
kp, kb, ka = A['weekly']['phone'], B['weekly']['ours'], A['weekly']['ours']
for sc, lab in (('phoneHour', 'join at the phone\'s hour (00:06 UTC)'), ('allHours', 'join at 8 hours of the day')):
    row('Weekly (%s): idle from +3.5 h to +11.2 h' % lab, pct(kp['static_3h30_11h12']), pct(kb[sc]['static_3h30_11h12']), pct(ka[sc]['static_3h30_11h12']),
        'ref 175 = a ~35-wins-a-day player (the phone\'s)')
    row('Weekly (%s): rivals moving +3.5 h -> +9 h' % lab, kp['movers_3h30_9h'], kb[sc]['movers_3h30_9h'], ka[sc]['movers_3h30_9h'], 'of 9')
    row('Weekly (%s): rivals moving +9 h -> +11.2 h' % lab, kp['movers_9h_11h12'], kb[sc]['movers_9h_11h12'], ka[sc]['movers_9h_11h12'])
    row('Weekly (%s): shares of the rivals\' 11.2 h progress' % lab, lst(kp['shares11h12']), lst(kb[sc]['shares11h12']), lst(ka[sc]['shares11h12']),
        'the shape of the group')
    row('Weekly (%s): rival scores at +11.2 h' % lab, lst(kp['at11h12']), lst(kb[sc]['at11h12']), lst(ka[sc]['at11h12']),
        'absolute: the phone\'s player (a bot) was ~2x a ref-175 player')
    row('Weekly (%s): top at +85 min / leader +3.5 -> +9 h' % lab, '%s / %s' % (kp['top85'], kp['leader_3h30_9h']),
        '%s / %s' % (kb[sc]['top85'], kb[sc]['leader_3h30_9h']), '%s / %s' % (ka[sc]['top85'], ka[sc]['leader_3h30_9h']))
row('Weekly ties', 'earlier reach first (Sneaky 27 above the player\'s 27)', 'earlier reach first', 'earlier reach first', 'unchanged')
# streak
sp, sb, sa = A['streak']['phone'], B['streak']['ours'], A['streak']['ours']
for sc, lab in (('phoneHour', 'join 11:03 TRT'), ('allHours', 'join at 6 hours')):
    row('Streak (%s): rivals at 0 at the join' % lab, '49 of 49', sb[sc]['zerosAtJoin'], sa[sc]['zerosAtJoin'], 'SOC1: members arrived with points')
    row('Streak (%s): rows at 0 at +69 min / +3 h' % lab, '%s / %s' % (sp['zeros69'], sp['zeros3h']), '%s / %s' % (sb[sc]['zeros69'], sb[sc]['zeros3h']),
        '%s / %s' % (sa[sc]['zeros69'], sa[sc]['zeros3h']))
    row('Streak (%s): static from +69 min to +3 h' % lab, pct(sp['static_69m_3h']), pct(sb[sc]['static_69m_3h']), pct(sa[sc]['static_69m_3h']))
    row('Streak (%s): top at +69 min' % lab, sp['top69'], sb[sc]['top69'], sa[sc]['top69'])
    row('Streak (%s): top 6 at +3 h' % lab, lst(sp['top6_3h']), lst(sb[sc]['top6_3h']), lst(sa[sc]['top6_3h']),
        'the phone\'s leaders jumped +2583 in 28 min (not human-paced)')
    row('Streak (%s): top-3 gain +97 min -> +3 h' % lab, lst(sp['top3gain_97m_3h']), lst(sb[sc]['top3gain_97m_3h']), lst(sa[sc]['top3gain_97m_3h']),
        'median over races; the phone: leaders slowed to ~+1 point/min')
row('Streak ties', 'alphabetical, case-insensitive (Babs, ChillRat … karl, KernowCat …)', 'earlier reach first', 'alphabetical (name key)',
    'at the join: ' + ', '.join((sa.get('tiesAtJoin') or [])[:6]))
# rocket
rp, rb, ra = A['rocket']['phone'], B['rocket']['ours'], A['rocket']['ours']
row('Rocket stage 1: first rival finish (min after the join, q1/median/q3)', '6, 8, 19 (S1: 15-20)', lst(rb['stage1']['firstFinishMin_q1_med_q3']),
    lst(ra['stage1']['firstFinishMin_q1_med_q3']), 'a sprinter held until 6-19 min')
row('Rocket stage 1: the other lanes at that moment', '[3,2,1] [3,1,1] [4,3,1]', lst(rb['stage1']['othersAtFinish']), lst(ra['stage1']['othersAtFinish']))
row('Rocket stage 1: a player at 6 / 3 / 2 / 1.5 min a level wins', 'lost 4 of 4 (~5-7 min a level)',
    ' / '.join(pct(rb['stage1'][k]) for k in ('humanWin_6m', 'humanWin_3m', 'humanWin_2m', 'humanWin_1m30')),
    ' / '.join(pct(ra['stage1'][k]) for k in ('humanWin_6m', 'humanWin_3m', 'humanWin_2m', 'humanWin_1m30')))
for st in ('stage2', 'stage3'):
    row('Rocket %s: first finish q1/median/q3' % st, '-', lst(rb[st]['firstFinishMin_q1_med_q3']), lst(ra[st]['firstFinishMin_q1_med_q3']), 'DECISION (not seen)')
# sky
kp_, kb_, ka_ = A['sky']['phone'], B['sky']['ours'], A['sky']['ours']
row('Sky stage 1 curve (example) / winners', '100 82 64 ? 47 -> 7 (714 each)', '%s / %s' % (' '.join(map(str, kb_['stage1']['example'])), kb_['stage1']['winners_range']),
    '%s / %s' % (' '.join(map(str, ka_['stage1']['example'])), ka_['stage1']['winners_range']))
row('Sky stage 2 curve (example) / winners', '100 100 88 75 62 49 36 -> 15 (466 each)', '%s / %s' % (' '.join(map(str, kb_['stage2']['example'])), kb_['stage2']['winners_range']),
    '%s / %s' % (' '.join(map(str, ka_['stage2']['example'])), ka_['stage2']['winners_range']))
row('Sky stage 3 curve (example)', '100 100 91 82 74 65 57 … (10 levels on the phone)', ' '.join(map(str, kb_['stage3']['example'])),
    ' '.join(map(str, ka_['stage3']['example'])), 'C3 ships 9 levels: open issue')
row('Sky: drop per level (median) / first drop', '8-13 / 0 (stages 2-3), 18 (stage 1)',
    ' '.join('%s/%s' % (kb_[s]['drop_per_level_median'], kb_[s]['first_drop_median']) for s in ('stage1', 'stage2', 'stage3')),
    ' '.join('%s/%s' % (ka_[s]['drop_per_level_median'], ka_[s]['first_drop_median']) for s in ('stage1', 'stage2', 'stage3')))
row('Sky: winners\' share (median)', '714 (stage 1), 466 (stage 2)', ' / '.join(str(int(kb_[s]['share_median'])) for s in ('stage1', 'stage2', 'stage3')),
    ' / '.join(str(int(ka_[s]['share_median'])) for s in ('stage1', 'stage2', 'stage3')))
c = A['calendar']
row('Resets', 'Weekly/Claw Mon ~10:00 TRT; Streak/Rocket 10:00 TRT daily; Sky 24 h from the join', 'same', 'weekly %s, day %s (UTC)' % (
    c['ours']['weekly_ends_utc'][:16], c['ours']['day_ends_utc'][:16]), 'unchanged, VERIFIED again')
w('')
if BB and BA:
    w('## The 52-week bench (Swift, SocialBenchTests, one user per profile from 5 Oct 2026)')
    w('')
    w('| metric | before active / casual / absent | after active / casual / absent |')
    w('|---|---|---|')

    def g(S, p, *ks):
        x = S[p]
        for k in ks:
            x = x[k]
        return x
    for lab, ks, f in [('final level', ('final_level',), str), ('World rank', ('world_rank_final',), str),
                       ('Country rank', ('country_rank_final',), str),
                       ('Weekly win', ('weekly', 'win'), pct), ('Weekly podium', ('weekly', 'podium'), pct),
                       ('Weekly median rank', ('weekly', 'median_rank'), str),
                       ('Streak Race 1st', ('streak_race', 'first'), pct), ('Streak Race top 3', ('streak_race', 'top3'), pct),
                       ('Streak Race median rank', ('streak_race', 'median_rank'), str),
                       ('Streak Race coins a day', ('streak_race', 'coins_per_day'), lambda v: str(int(v))),
                       ('Rocket stage 1 win', ('rocket', 'by_stage', '1', 'win'), pct), ('Rocket stage 2 win', ('rocket', 'by_stage', '2', 'win'), pct),
                       ('Rocket stage 3 win', ('rocket', 'by_stage', '3', 'win'), pct),
                       ('Sky Jump stage wins / runs, mean share', ('sky',), lambda v: '%s / %s, %d' % (v['wins'], v['n'], v['mean_share'])),
                       ('returns where someone passed the player (Country ±10)', ('idle', 'returns_with_someone_passing'), pct),
                       ('Weekly leader after the join: gain in 85 min / 3.5 h', ('weekly_rival_pace',),
                        lambda v: '%s / %s' % (v['median_top_gain_85min'], v['median_top_gain_3h30'])),
                       ('invariants: backwards / duplicate rows / country > world / bad pages', ('checks',),
                        lambda v: '%s / %s / %s / %s' % (v['backwards'], v['dup_rows'], v['rank_inconsistent'], v['api_bad_pages']))]:
        w('| %s | %s | %s |' % (lab, ' / '.join(f(g(BB, p, *ks)) for p in ('active', 'casual', 'absent')),
                                ' / '.join(f(g(BA, p, *ks)) for p in ('active', 'casual', 'absent'))))
    w('')
if PB and PA:
    w('## Query budgets (Swift -O on this Mac, p95 ms; SOC1\'s gates unchanged; all social work runs off the main thread)')
    w('')
    w('before = SOC1 run B (build/soc1/perf-runs.txt, load ~3.7); after = build/soc1b/evidence/soc1-perf-release.json (load ~4). '
      'The final full -O run is within noise of SOC1 on every metric. One earlier full run (load ~5, right after the 52-week bench) '
      'measured y3.page50.world.top p95 2.21 ms over its 2 ms guard (p50 1.12); standalone reruns gave 1.14 and 1.13 ms and the final '
      'full run 1.20 ms (build/soc1b/release-final-run1-perf-outlier.log, perf-rerun1/2.log).')
    w('')
    w('| metric | budget | before | after |')
    w('|---|---|---|---|')
    for k in sorted(PA):
        if isinstance(PA[k], dict) and 'p95_ms' in PA[k]:
            b = PB.get(k, {}).get('p95_ms', '-') if isinstance(PB.get(k), dict) else 'not in run B'
            fmt = lambda v: ('%.3f' % v) if isinstance(v, float) else str(v)
            w('| %s | %s | %s | %s |' % (k, PA[k].get('budget_ms') or 'report only', fmt(b), fmt(PA[k]['p95_ms'])))
    w('')
out = os.path.join(APP, 'build/soc1b/calibration.md')
open(out, 'w').write('\n'.join(L) + '\n')
print('wrote', out, len(L), 'lines')
