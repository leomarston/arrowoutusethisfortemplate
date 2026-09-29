#!/usr/bin/env python3
"""sources_table.py — the per-culture source table of the v2 name lists (markdown), from data_v2/social_names_v2_report.json
and the cached Wikidata responses (their fetch dates). Pasted into design/social/SOURCES.md."""
import os, sys, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import wd_fetch as WF                                                          # noqa: E402

rep = json.load(open(os.path.join(ROOT, 'data_v2', 'social_names_v2_report.json'), encoding='utf-8'))
dates = []
for f in glob.glob(os.path.join(ROOT, 'sources', 'wikidata', '*.json')):
    d = json.load(open(f, encoding='utf-8'))
    if d.get('fetched'):
        dates.append(d['fetched'][:10])
print('Wikidata responses fetched %s .. %s (%d cached files in sources/wikidata/).' % (min(dates), max(dates), len(dates)))
print()
print('| culture | source | names | people counted | singletons used | most common (list order) |')
print('|---|---|---|---|---|---|')
for cu, v in rep['cultures'].items():
    if cu in ('easteu', 'sea'):
        src = 'v1 list, kept for index stability (no v2 row uses it)'
    elif cu == 'en':
        src = 'SSA baby names 1945-2008 (v1 `data/given_en.txt`), public domain'
    elif cu == 'th':
        src = 'Wikidata: first word of the Thai labels of Thai citizens born 1950-2008'
    elif cu == 'vi':
        src = 'Wikidata: last word of the Vietnamese labels of Vietnamese citizens born 1950-2008'
    else:
        src = 'Wikidata P735 (first given name), citizens of ' + '+'.join(WF.CULTURES[cu][0]) + ', born 1950-2008'
    print('| %s | %s | %d | %s | %s | %s |' % (cu, src, v['n'], v.get('persons', '-'), v.get('singlesFilled', '-'),
                                             ', '.join((v.get('top10') or [])[:6])))
