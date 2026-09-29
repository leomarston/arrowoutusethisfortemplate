#!/usr/bin/env python3
"""wd_fetch.py — download the raw given-name statistics for the v2 name lists from Wikidata (CC0).

For every source country and sex: the FIRST given name (P735, series ordinal 1 or unqualified) of every human (P31 Q5) with
that citizenship (P27) and sex (P21), born 1950-01-01 .. 2008-12-31 (P569) — i.e. today's adult population as far as
Wikidata records it — counted per given-name item. Then the labels of every counted item in the culture's languages
(rdfs:label, P1705 native label, P2125 Revised Hepburn, P1721 pinyin). Thai people rarely carry P735, so for TH the first
word of each person's own Thai and English labels is counted instead (see `thai`).

Every response is cached under design/social/sources/wikidata/ (the query text is stored next to it), so a rebuild never
needs the network. The data is Wikidata's: CC0 1.0 (https://www.wikidata.org/wiki/Wikidata:Licensing).
    python3 design/social/tools/v2/wd_fetch.py            # fetch what is missing (sequential, polite)
    python3 design/social/tools/v2/wd_fetch.py --list     # print the plan
"""
import os, sys, json, time, subprocess, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))          # design/social
OUT = os.path.join(ROOT, 'sources', 'wikidata')
UA = 'ArrowOutNameStats/1.0 (offline research script; one request at a time)'
ENDPOINT = 'https://query.wikidata.org/sparql'
SEX = {'m': 'Q6581097', 'f': 'Q6581072'}

# country ISO -> Wikidata item
Q = dict(TR='Q43', DE='Q183', AT='Q40', CH='Q39', FR='Q142', BE='Q31', ES='Q29', MX='Q96', AR='Q414', CO='Q739', CL='Q298',
         BR='Q155', PT='Q45', IT='Q38', NL='Q29999', SE='Q34', NO='Q20', DK='Q756617', IS='Q189', FI='Q33', PL='Q36', SK='Q214',
         SI='Q215', CZ='Q213', HU='Q28', RO='Q218', MD='Q217', GR='Q41', CY='Q229', RU='Q159', BY='Q184', UA='Q212',
         BG='Q219', HR='Q224', RS='Q403', BA='Q225', ME='Q236', AL='Q222', XK='Q1246', LT='Q37', LV='Q211', EE='Q191',
         IN='Q668', PK='Q843', BD='Q902', TH='Q869', VN='Q881', ID='Q252', MY='Q833', BN='Q921', PH='Q928', CN='Q148',
         TW='Q865', HK='Q8646', SG='Q334', JP='Q17', KR='Q884', SA='Q851', EG='Q79', JO='Q810', IQ='Q796', MA='Q1028',
         DZ='Q262', TN='Q948', SY='Q858', LB='Q822', AE='Q878', KW='Q817', IL='Q801', IR='Q794', AF='Q889', US='Q30',
         AM='Q399', GE='Q230', AZ='Q227', KZ='Q232', UZ='Q265', NG='Q1033', GH='Q117', KE='Q114', UG='Q1036', TZ='Q924',
         ZA='Q258', ZW='Q954', TJ='Q863')

# culture -> (source countries, label languages in priority order, script)
#   script 'latin': the name is the label in the culture's language (diacritics kept; the builder folds it for the ASCII
#   spelling); 'native': [native-script label, Latin romanisation] pairs (the romanisation = the English label).
CULTURES = {
    'tr': (['TR'], ['tr'], 'latin'),
    'de': (['DE', 'AT'], ['de'], 'latin'),
    'fr': (['FR'], ['fr'], 'latin'),
    'es': (['ES', 'MX', 'AR', 'CO'], ['es'], 'latin'),
    'pt': (['BR'], ['pt-br', 'pt'], 'latin'),
    'ptpt': (['PT'], ['pt'], 'latin'),
    'it': (['IT'], ['it'], 'latin'),
    'nl': (['NL'], ['nl'], 'latin'),
    'nordic': (['SE', 'NO', 'DK'], ['sv', 'nb', 'da'], 'latin'),
    'fi': (['FI'], ['fi'], 'latin'),
    'pl': (['PL'], ['pl'], 'latin'),
    'sk': (['SK'], ['sk'], 'latin'),
    'sl': (['SI'], ['sl'], 'latin'),
    'cs': (['CZ'], ['cs'], 'latin'),
    'hu': (['HU'], ['hu'], 'latin'),
    'ro': (['RO'], ['ro'], 'latin'),
    'hr': (['HR'], ['hr'], 'latin'),
    'sr': (['RS'], ['sr-el', 'sh', 'hr', 'bs'], 'latin'),
    'sq': (['AL', 'XK'], ['sq'], 'latin'),
    'lt': (['LT'], ['lt'], 'latin'),
    'lv': (['LV'], ['lv'], 'latin'),
    'et': (['EE'], ['et'], 'latin'),
    'vi': (['VN'], ['vi'], 'latin'),
    'id': (['ID'], ['id'], 'latin'),
    'ms': (['MY', 'BN'], ['ms'], 'latin'),
    'tl': (['PH'], ['tl', 'en'], 'latin'),
    'in': (['IN'], ['en'], 'latin'),
    'ur': (['PK', 'BD'], ['en'], 'latin'),
    'el': (['GR', 'CY'], ['el'], 'native'),
    'ru': (['RU', 'BY'], ['ru'], 'native'),
    'uk': (['UA'], ['uk'], 'native'),
    'bg': (['BG'], ['bg'], 'native'),
    'he': (['IL'], ['he'], 'native'),
    'ar': (['SA', 'EG', 'JO', 'IQ', 'MA', 'DZ', 'TN', 'SY', 'LB', 'AE', 'KW'], ['ar'], 'native'),
    'fa': (['IR', 'AF', 'TJ'], ['fa'], 'native'),
    'jp': (['JP'], ['ja'], 'native'),
    'kr': (['KR'], ['ko'], 'native'),
    'zh': (['CN', 'TW', 'HK', 'SG'], ['zh-hans', 'zh-cn', 'zh', 'zh-hant', 'zh-tw', 'zh-hk'], 'native'),
    'th': (['TH'], ['th'], 'native'),
    # smaller markets with names of their own (a proxy culture is used where these stay under 300 names)
    'hy': (['AM'], ['hy'], 'native'),
    'ka': (['GE'], ['ka'], 'native'),
    'az': (['AZ'], ['az'], 'latin'),
    'kk': (['KZ'], ['kk', 'ru'], 'native'),
    'uz': (['UZ'], ['uz'], 'latin'),
    'af': (['NG', 'GH', 'KE', 'UG', 'TZ', 'ZA', 'ZW'], ['en'], 'latin'),
}
YEARS = ('1950-01-01T00:00:00Z', '2009-01-01T00:00:00Z')

COUNT_Q = '''SELECT ?name (COUNT(DISTINCT ?p) AS ?c) WHERE {
  ?p wdt:P27 wd:%(country)s ; wdt:P21 wd:%(sex)s ; wdt:P569 ?b ; p:P735 ?st .
  ?st ps:P735 ?name .
  OPTIONAL { ?st pq:P1545 ?o }
  FILTER(!BOUND(?o) || STR(?o) = "1")
  FILTER(?b >= "%(y0)s"^^xsd:dateTime && ?b < "%(y1)s"^^xsd:dateTime)
} GROUP BY ?name ORDER BY DESC(?c) LIMIT 1500'''

LABEL_Q = '''SELECT ?name ?l ?nl ?hep ?pin WHERE { VALUES ?name { %(vals)s }
  OPTIONAL { ?name rdfs:label ?l . FILTER(LANG(?l) IN (%(langs)s)) }
  OPTIONAL { ?name wdt:P1705 ?nl }
  OPTIONAL { ?name wdt:P2125 ?hep }
  OPTIONAL { ?name wdt:P1721 ?pin }
}'''

# Vietnamese: P735's first given name is usually the middle name (Thị, Văn); the name people are called by is the LAST
# word of the person's own Vietnamese label (Nguyễn Văn An -> An).
VIET_Q = '''SELECT ?p ?vi ?en WHERE {
  ?p wdt:P27 wd:Q881 ; wdt:P21 wd:%(sex)s ; wdt:P569 ?b ; rdfs:label ?vi .
  OPTIONAL { ?p rdfs:label ?en . FILTER(LANG(?en) = "en") }
  FILTER(LANG(?vi) = "vi")
  FILTER(?b >= "%(y0)s"^^xsd:dateTime && ?b < "%(y1)s"^^xsd:dateTime)
} LIMIT 60000'''

# Thai: the given name is the first word of the person's own label (Thai people seldom carry P735).
THAI_Q = '''SELECT ?p ?th ?en WHERE {
  ?p wdt:P27 wd:Q869 ; wdt:P21 wd:%(sex)s ; wdt:P569 ?b ; rdfs:label ?th ; rdfs:label ?en .
  FILTER(LANG(?th) = "th" && LANG(?en) = "en")
  FILTER(?b >= "%(y0)s"^^xsd:dateTime && ?b < "%(y1)s"^^xsd:dateTime)
} LIMIT 60000'''


class QueryFailed(Exception):
    pass


def sparql(query, tries=4):
    for attempt in range(tries):
        r = subprocess.run(['curl', '-s', '-m', '90', '-G', ENDPOINT, '-H', 'User-Agent: ' + UA,
                            '-H', 'Accept: application/sparql-results+json', '--data-urlencode', 'query=' + query],
                           capture_output=True)
        try:
            return json.loads(r.stdout)['results']['bindings']
        except Exception:
            print('  retry', attempt + 1, r.stdout[:200], flush=True)
            time.sleep(10 * (attempt + 1))
    raise QueryFailed(query[:200])


def save(name, query, rows):
    path = os.path.join(OUT, name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(dict(source='Wikidata Query Service (CC0 1.0)', endpoint=ENDPOINT,
                       fetched=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), query=query, rows=rows),
                  f, ensure_ascii=False, indent=0, sort_keys=True)
        f.write('\n')


def qid(uri):
    return uri.rsplit('/', 1)[1]


def fetch_counts(iso, sex):
    name = 'counts_%s_%s.json' % (iso, sex)
    if os.path.exists(os.path.join(OUT, name)):
        return
    query = COUNT_Q % dict(country=Q[iso], sex=SEX[sex], y0=YEARS[0], y1=YEARS[1])
    t = time.time()
    try:
        rows = [[qid(b['name']['value']), int(b['c']['value'])] for b in sparql(query, 2) if 'name' in b]
    except QueryFailed:
        # a big country times out: count per birth-decade slice and add the slices up (same population, same rule)
        acc = {}
        parts = []
        cuts = ['1950', '1960', '1970', '1980', '1990', '2009']
        for a, b in zip(cuts, cuts[1:]):
            qs = COUNT_Q % dict(country=Q[iso], sex=SEX[sex], y0=a + '-01-01T00:00:00Z', y1=b + '-01-01T00:00:00Z')
            parts.append(qs)
            for bnd in sparql(qs):
                if 'name' in bnd:
                    k = qid(bnd['name']['value'])
                    acc[k] = acc.get(k, 0) + int(bnd['c']['value'])
            time.sleep(1.5)
        rows = sorted(([k, v] for k, v in acc.items()), key=lambda x: (-x[1], x[0]))[:1500]
        query = '\n#---- sum of the birth-decade slices:\n'.join(parts)
    save(name, query, rows)
    print('counts', iso, sex, len(rows), 'names, %d people, %.1fs' % (sum(c for _, c in rows), time.time() - t), flush=True)
    time.sleep(1.5)


def fetch_labels(culture):
    name = 'labels_%s.json' % culture
    if os.path.exists(os.path.join(OUT, name)):
        return
    countries, langs, script = CULTURES[culture]
    ids = []
    seen = set()
    for iso in countries:
        for sex in 'mf':
            with open(os.path.join(OUT, 'counts_%s_%s.json' % (iso, sex)), encoding='utf-8') as f:
                for q, c in json.load(f)['rows']:
                    if q not in seen:
                        seen.add(q); ids.append(q)
    lang_list = list(langs) + (['en', 'mul'] if 'en' not in langs else ['mul'])
    rows = []
    queries = []
    for k in range(0, len(ids), 250):
        query = LABEL_Q % dict(vals=' '.join('wd:' + i for i in ids[k:k + 250]), langs=','.join('"%s"' % x for x in lang_list))
        queries.append(hashlib.sha1(query.encode()).hexdigest())
        for b in sparql(query):
            row = [qid(b['name']['value'])]
            for key in ('l', 'nl', 'hep', 'pin'):
                v = b.get(key)
                row.append(None if v is None else [v['value'], v.get('xml:lang', '')])
            rows.append(row)
        time.sleep(1.0)
    save(name, 'LABEL_Q over %d ids in batches of 250 (languages %s); batch sha1s %s' % (len(ids), lang_list, queries), rows)
    print('labels', culture, len(ids), 'ids ->', len(rows), 'rows', flush=True)


CUTS = ['1950', '1960', '1970', '1980', '1990', '2009']


def fetch_persons(tmpl, name, sex, cols):
    """A persons' labels query, one birth-decade slice at a time (the whole range times out); a slice that still times
    out is halved (by year) until it passes."""
    if os.path.exists(os.path.join(OUT, name)):
        return
    rows = []
    parts = []
    todo = [(int(a), int(b)) for a, b in zip(CUTS, CUTS[1:])]
    while todo:
        a, b = todo.pop(0)
        query = tmpl % dict(sex=SEX[sex], y0='%d-01-01T00:00:00Z' % a, y1='%d-01-01T00:00:00Z' % b)
        try:
            got = sparql(query, 2)
        except QueryFailed:
            if b - a <= 1:
                raise
            m = (a + b) // 2
            todo[:0] = [(a, m), (m, b)]
            print('  split', a, b, flush=True)
            continue
        parts.append(query)
        for bnd in got:
            rows.append([qid(bnd['p']['value'])] + [bnd.get(c, {}).get('value') for c in cols])
        time.sleep(1.5)
    save(name, '\n#---- birth-decade slices:\n'.join(parts), rows)
    print(name, len(rows), flush=True)


def fetch_thai(sex):
    fetch_persons(THAI_Q, 'thai_persons_%s.json' % sex, sex, ('th', 'en'))


def fetch_viet(sex):
    fetch_persons(VIET_Q, 'viet_persons_%s.json' % sex, sex, ('vi', 'en'))


def main():
    os.makedirs(OUT, exist_ok=True)
    plan = []
    for cu, (countries, langs, script) in CULTURES.items():
        for iso in countries:
            plan.append((cu, iso))
    if '--list' in sys.argv:
        for cu, iso in plan:
            print(cu, iso, Q[iso])
        return
    only = [a for a in sys.argv[1:] if not a.startswith('--')]
    for cu, (countries, langs, script) in CULTURES.items():
        if only and cu not in only:
            continue
        for iso in countries:
            for sex in 'mf':
                fetch_counts(iso, sex)
        fetch_labels(cu)
        if cu == 'th':
            for sex in 'mf':
                fetch_thai(sex)
        if cu == 'vi':
            for sex in 'mf':
                fetch_viet(sex)


if __name__ == '__main__':
    main()
