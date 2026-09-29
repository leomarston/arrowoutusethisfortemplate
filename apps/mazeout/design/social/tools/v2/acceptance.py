#!/usr/bin/env python3
"""acceptance.py — T6 SOC-PY's acceptance (PLAN-P row T6) rolled up from the evidence files in build/p/T6/ -> acceptance.json.
Reads only what run_all.sh (or the individual steps) wrote; runs nothing heavy. Counts only.
    python3 design/social/tools/v2/acceptance.py [build/p/T6]
"""
import os, sys, json, re
HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(APP, 'build', 'p', 'T6')


def load(name):
    p = os.path.join(OUT, name)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else None


def tests(model):
    p = os.path.join(OUT, 'tests_%s.log' % model)
    if not os.path.exists(p):
        return None
    m = re.search(r'\[%s\] (\d+)/(\d+) passed' % model, open(p, encoding='utf-8').read())
    return dict(passed=int(m.group(1)), total=int(m.group(2)), ok=m.group(1) == m.group(2)) if m else None


def main():
    res = {}
    res['testsGreen'] = {m: tests(m) for m in ('reference', 'v552', 'v2')}
    ident = load('identity.json')
    res['switchesOffByteIdentical'] = dict(ok=bool(ident and ident['all_identical']), files=len(ident['files']) if ident else 0,
                                           when=ident and ident['when'],
                                           note='make_fixtures.py + soc_fixtures.py reference|v552 regenerated into a scratch '
                                                'folder and compared by sha256 with the files in the tree (the app folder is '
                                                'not tracked by git, so a git diff cannot be taken)')
    cal = load('calib.json')
    if cal:
        a = cal['acceptance']
        res['perCountryGuards'] = dict(countryWeeks=a['countriesEvaluated'], deadHoursLe20=a['deadHoursLe20'],
                                       ladderPairsLe8=a['ladderPairsLe8'], equalGapRunLe3=a['equalGapRunLe3'],
                                       structureOk=a['structureOk'])
        res['topFirstNameLe4pct'] = dict(ok=a['topFirstNameLe4pctOk'],
                                         failingBoards={k: len(v) for k, v in a['topFirstNameLe4pct'].items()},
                                         boards=a['countriesEvaluated'],
                                         le5occurrencesFails=a['topFirstNameLe5rows'],
                                         expectedShareOver4pct=a['expectedTopFirstNameLe4pct'],
                                         expectedShareMax=max(cal['expectedTopFirstName'].values()))
        res['turkeyRankL62'] = a['turkeyRankL62']
        res['isoRegionsResolve'] = dict(ok=a['isoRegionsResolve'], **{k: v for k, v in cal['regions'].items() if k != 'ok'})
        res['phoneGuards'] = {k: v.get('ok') for k, v in cal['phone'].items()}
        res['eventGuards'] = {k: v.get('ok') for k, v in cal['events'].items()}
    na = None
    for p in (os.path.join(OUT, 'name_audit_v2_2031-09-25.json'),
              os.path.join(APP, 'design', 'social', 'bench', 'name_audit_v2_2031-09-25.json')):
        if os.path.exists(p):
            na = json.load(open(p, encoding='utf-8'))
            break
    if na:
        res['nameAudit2031'] = dict(verdict=na['verdict'], players=na['players'], blockedShown=na['blocked_shown'],
                                    longerThan16=na['longer_than_16'], pairRate=na['board_like_pair_rate'],
                                    fallbacks=na['styles'].get('fallback', 0),
                                    publishedList={k: v for k, v in na.get('publishedList', {}).items() if k not in ('sha1', 'source')})
    mc = load('names_mc.json')
    if mc:
        rf = sorted(v['real']['fail4pct'] for v in mc['cultures'].values())
        res['nameMonteCarlo'] = dict(rows=mc['rows'], cultures=len(rf), realFrequenciesFail4pctMedian=rf[len(rf) // 2],
                                     realFrequenciesFail4pctMin=rf[0])
    rep = json.load(open(os.path.join(APP, 'design', 'social', 'data_v2', 'social_names_v2_report.json'), encoding='utf-8'))
    sizes = {cu: v['n'] for cu, v in rep['cultures'].items()}
    res['nameData'] = dict(cultures=len(sizes), culturesWith300plus=sum(1 for n in sizes.values() if n >= 300),
                           under300=sorted(cu for cu, n in sizes.items() if n < 300))
    with open(os.path.join(OUT, 'acceptance.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
