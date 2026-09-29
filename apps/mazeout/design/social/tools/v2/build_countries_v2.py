#!/usr/bin/env python3
"""build_countries_v2.py — the v2 country table (M3; design/publish/social-intl.md §6.1, ruling 38 "~200 country rows with
documented weights + territory aliases").

Inputs
  data_v2/country_facts_v2.tsv   hand-written: every Locale.Region.isoRegions alpha-2 code -> row / alias, offset, bucket,
                                 culture mix, weight rule (DECISIONS, see its header)
  data_v2/ios_regions.tsv        Foundation's Locale.Region.isoRegions (the codes a device can report) + containment
  sources/wikidata/countries_pop_gdp.json   population (P1082) and nominal GDP (P2131), latest value per country
                                 (Wikidata, CC0), fetched once by this script (--fetch); GDP per capita = GDP / population
Outputs (data_v2/)
  buckets_v2.tsv     bucket, schedule offset (minutes)
  countries_v2.tsv   iso, weight, std offset, culture mix, bucket, weight basis — the table the model reads
  regions_v2.tsv     EVERY isoRegions code (+ the 2-letter codes of the table) -> kind (row|alias|numeric), board ISO
  countries_v2_report.json   the per-class per-capita weights, every formula input, the checks

Weight rule for a 'formula' row (the 49 reference rows keep their weights; they define the per-capita scale):
  class = World Bank-style income class from nominal GDP per capita (USD): high >= 14,005, upper-middle >= 4,516,
          lower-middle >= 1,146, else low (the FY2025 GNI thresholds applied to GDP per capita: a proxy)
  k(class, region) = the MEDIAN weight per million inhabitants of the reference rows of that class in the same UN M.49
          sub-region (Eastern Europe, Western Asia, South America, ...) when there are at least 3 such rows, else of every
          reference row of that class (computed here, printed); low income (no reference row): 0.001 (DECISION)
  weight = population_millions x k(class) x 1.5 if the row's culture mix is at least half English (the game's
          language; DECISION) — capped at 0.5 (high / upper-middle) or 0.25 (lower-middle / low) so no new market
          outweighs the reference's mid-size ones, floored at 0.004 (a board of a few players at launch), 2 significant
          digits. Caps: 0.5 high income, 0.3 upper-middle, 0.2 lower-middle, 0.1 low (DECISION).
    python3 design/social/tools/v2/build_countries_v2.py [--fetch]
"""
import os, sys, json, math, subprocess, time, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
D2 = os.path.join(ROOT, 'data_v2')
SRC = os.path.join(ROOT, 'sources', 'wikidata', 'countries_pop_gdp.json')
UA = 'ArrowOutNameStats/1.0 (offline research script)'

POP_Q = '''SELECT ?iso ?v ?date WHERE { ?c wdt:P297 ?iso ; p:P1082 ?s . ?s ps:P1082 ?v .
  OPTIONAL { ?s pq:P585 ?date } FILTER NOT EXISTS { ?s wikibase:rank wikibase:DeprecatedRank } }'''
GDP_Q = '''SELECT ?iso ?v ?date WHERE { ?c wdt:P297 ?iso ; p:P2131 ?s . ?s ps:P2131 ?v .
  OPTIONAL { ?s pq:P585 ?date } FILTER NOT EXISTS { ?s wikibase:rank wikibase:DeprecatedRank } }'''

HIGH, UPPER, LOWER = 14005.0, 4516.0, 1146.0
K_LOW = 0.001
ENGLISH_FACTOR = 1.5
CAP = dict(high=0.5, upper=0.3, lower=0.2, low=0.1)
FLOOR = 0.004


def sparql(query):
    for attempt in range(4):
        r = subprocess.run(['curl', '-s', '-m', '90', '-G', 'https://query.wikidata.org/sparql', '-H', 'User-Agent: ' + UA,
                            '-H', 'Accept: application/sparql-results+json', '--data-urlencode', 'query=' + query],
                           capture_output=True)
        try:
            return json.loads(r.stdout)['results']['bindings']
        except Exception:
            time.sleep(10 * (attempt + 1))
    raise SystemExit('query failed')


def fetch():
    out = {}
    for key, q in (('population', POP_Q), ('gdp_nominal_usd', GDP_Q)):
        rows = []
        for b in sparql(q):
            rows.append([b['iso']['value'], b['v']['value'], b.get('date', {}).get('value')])
        out[key] = dict(query=q, rows=rows)
        time.sleep(2)
    out['source'] = 'Wikidata Query Service (CC0 1.0); P1082 population, P2131 nominal GDP (USD)'
    out['fetched'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    with open(SRC, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=0, sort_keys=True)
        f.write('\n')


def latest(rows):
    """ISO -> the value with the latest point-in-time (ties: the larger value); rows without a date rank last."""
    best = {}
    for iso, v, date in rows:
        try:
            x = float(v)
        except ValueError:
            continue
        k = (date or '0000', x)
        if iso not in best or k > best[iso][0]:
            best[iso] = (k, x, date)
    return {iso: (x, date) for iso, (k, x, date) in best.items()}


def sig2(x):
    if x <= 0:
        return 0.0
    e = math.floor(math.log10(x)) - 1
    return round(round(x / 10 ** e) * 10 ** e, 6)


def income(gdp):
    if gdp is None:
        return None
    return 'high' if gdp >= HIGH else 'upper' if gdp >= UPPER else 'lower' if gdp >= LOWER else 'low'


def main():
    if '--fetch' in sys.argv or not os.path.exists(SRC):
        fetch()
    src = json.load(open(SRC, encoding='utf-8'))
    pop = latest(src['population']['rows'])
    gdp_total = latest(src['gdp_nominal_usd']['rows'])
    # GDP per capita = the latest nominal GDP / the latest population (different reference years: a class proxy only)
    gdp = {iso: (g / pop[iso][0], date) for iso, (g, date) in gdp_total.items() if iso in pop and pop[iso][0] > 0}
    buckets = []
    facts = []
    for line in open(os.path.join(D2, 'country_facts_v2.tsv'), encoding='utf-8'):
        line = line.rstrip('\n')
        if line.startswith('#@bucket'):
            _, b, off = line.split('\t')
            buckets.append((b, int(off)))
            continue
        if not line or line.startswith('#'):
            continue
        p = line.split('\t')
        p += [''] * (8 - len(p))
        facts.append(dict(code=p[0], kind=p[1], target=p[2], off=p[3], bucket=p[4], mix=p[5], rule=p[6], note=p[7]))
    boff = dict(buckets)
    ios = {}
    for line in open(os.path.join(D2, 'ios_regions.tsv'), encoding='utf-8'):
        if line.startswith('#'):
            continue
        code, name, cont, nsub = line.rstrip('\n').split('\t')
        ios[code] = dict(name=name, container=cont)
    # ---- checks on the hand table
    rows = [f for f in facts if f['kind'] == 'row']
    row_isos = {f['code'] for f in rows}
    problems = []
    for f in facts:
        if f['kind'] == 'alias' and f['target'] not in row_isos:
            problems.append('alias target not a row: %s -> %s' % (f['code'], f['target']))
        if f['kind'] == 'row':
            if f['bucket'] not in boff:
                problems.append('unknown bucket %s' % f['code'])
            elif abs(int(f['off']) - boff[f['bucket']]) > 60:
                problems.append('%s offset %s is more than 60 min from %s (%d)' % (f['code'], f['off'], f['bucket'], boff[f['bucket']]))
            mix = [m.split(':') for m in f['mix'].split(',')]
            if any(len(m) == 2 and float(m[1]) <= 0 for m in mix):
                problems.append('bad mix %s' % f['code'])
    alpha = sorted(c for c in ios if not c[0].isdigit())
    coded = {f['code'] for f in facts}
    missing = [c for c in alpha if c not in coded]
    extra = sorted(c for c in coded if c not in ios)
    if missing:
        problems.append('isoRegions codes without a line: %s' % missing)
    # ---- per-capita weights of the reference rows, by class
    per = {}
    ref_rows = []
    for f in rows:
        if f['rule'].startswith('keep:'):
            w = float(f['rule'].split(':')[1])
            ref_rows.append((f['code'], w))
    tot_ref = {}
    for iso, w in ref_rows:
        tot_ref[iso] = tot_ref.get(iso, 0.0) + w
    for iso, w in tot_ref.items():
        pm = pop.get(iso, (None,))[0]
        cl = income(gdp.get(iso, (None,))[0])
        if pm and cl:
            per.setdefault(cl, []).append((iso, w / (pm / 1e6)))
    K = {cl: statistics.median(v for _, v in xs) for cl, xs in per.items()}
    K.setdefault('low', K_LOW)
    sub = {code: d['container'] for code, d in ios.items()}
    KR = {}
    for cl, xs in per.items():
        by = {}
        for iso, v in xs:
            by.setdefault(sub.get(iso), []).append(v)
        for rg, vs in by.items():
            if len(vs) >= 3:
                KR[(cl, rg)] = statistics.median(vs)

    def k_of(cl, iso, region=None):
        rg = region or sub.get(iso)
        v = KR.get((cl, rg))
        return (v, 'k[%s,%s]' % (cl, rg)) if v is not None else (K[cl], 'k[%s]' % cl)
    # ---- the table
    out_rows = []
    report_rows = []
    for f in rows:
        rule = f['rule']
        pm = pop.get(f['code'], (None, None))
        gd = gdp.get(f['code'], (None, None))
        cl = income(gd[0])
        mix = f['mix']
        en_share = 0.0
        tot = 0.0
        for m in mix.split(','):
            c, w = (m.split(':') + ['1'])[:2]
            tot += float(w)
            if c == 'en':
                en_share += float(w)
        en_share /= tot
        if rule.startswith('formula'):
            region = None
            if '@' in rule:
                # the per-capita weight of another M.49 sub-region (DECISION, the note says why)
                rule, region = rule.split('@')
            if ':' in rule:
                # no GDP on Wikidata: the class is set by hand (DECISION, the note says why)
                cl = rule.split(':')[1]
            if pm[0] is None or cl is None:
                problems.append('no population / GDP for %s' % f['code'])
                w = FLOOR
                basis = 'formula: no data -> floor %.3f' % FLOOR
            else:
                kk, kname = k_of(cl, f['code'], region)
                raw = pm[0] / 1e6 * kk * (ENGLISH_FACTOR if en_share >= 0.5 else 1.0)
                w = sig2(min(CAP[cl], max(FLOOR, raw)))
                basis = ('formula (class set by hand: %s): ' % f['note'] if ':' in rule else 'formula: ') + 'pop %.2fM x %s %.4f%s = %.4f%s' % (
                    pm[0] / 1e6, kname, kk, ' x en 1.5' if en_share >= 0.5 else '', raw,
                    ' -> cap %.2f' % CAP[cl] if raw > CAP[cl] else (' -> floor %.3f' % FLOOR if raw < FLOOR else ''))
        else:
            kind, v = rule.split(':')
            w = float(v)
            basis = {'keep': 'reference weight kept', 'refit': 'refit (calib_v2.py)', 'decision': 'DECISION'}[kind]
            if f['note']:
                basis += ': ' + f['note']
        out_rows.append((f['code'], w, int(f['off']), mix, f['bucket'], basis))
        report_rows.append(dict(iso=f['code'], weight=w, rule=rule, population=pm[0], popDate=pm[1], gdpPerCapita=gd[0],
                                gdpDate=gd[1], incomeClass=cl, englishShare=round(en_share, 3), bucket=f['bucket']))
    # ---- regions: every code of isoRegions + every row / alias code
    total_by_iso = {}
    for iso, w, *_ in out_rows:
        total_by_iso[iso] = total_by_iso.get(iso, 0.0) + w
    region = {}
    for f in facts:
        if f['kind'] == 'row':
            region[f['code']] = ('row', f['code'])
        elif f['kind'] == 'alias':
            region[f['code']] = ('alias', f['target'])
    children = {}
    for code, d in ios.items():
        children.setdefault(d['container'], []).append(code)

    def leaves(code):
        out = []
        for ch in children.get(code, []):
            if ch in region and region[ch][0] == 'row':      # the region's own countries (a territory's parent may lie elsewhere)
                out.append(ch)
            out.extend(leaves(ch))
        return out
    for code in sorted(ios):
        if code[0].isdigit():
            cands = sorted(set(leaves(code)), key=lambda iso: (-total_by_iso[iso], iso))
            if not cands:
                problems.append('numeric region %s contains no row' % code)
                continue
            region[code] = ('numeric', cands[0])
    unresolved = [c for c in ios if c not in region]
    if unresolved:
        problems.append('unresolved isoRegions codes: %s' % unresolved)
    # ---- write
    hdr = ('# countries_v2.tsv — GENERATED by design/social/tools/v2/build_countries_v2.py from country_facts_v2.tsv (+ Wikidata\n'
           '# population / GDP per capita, CC0). Do not edit: edit the facts file and rebuild.\n'
           '# iso\tweight\tstd_offset_min\tculture_mix\tbucket\tweight_basis\n')
    with open(os.path.join(D2, 'countries_v2.tsv'), 'w', encoding='utf-8') as fo:
        fo.write(hdr)
        for iso, w, off, mix, b, basis in out_rows:
            fo.write('%s\t%s\t%d\t%s\t%s\t%s\n' % (iso, repr(w), off, mix, b, basis))
    with open(os.path.join(D2, 'buckets_v2.tsv'), 'w', encoding='utf-8') as fo:
        fo.write('# buckets_v2.tsv — GENERATED (build_countries_v2.py): timezone band, the schedule offset (min) of its cohorts\n')
        for b, off in buckets:
            fo.write('%s\t%d\n' % (b, off))
    with open(os.path.join(D2, 'regions_v2.tsv'), 'w', encoding='utf-8') as fo:
        fo.write('# regions_v2.tsv — GENERATED (build_countries_v2.py): every Locale.Region.isoRegions code -> the board it plays on.\n'
                 '# code\tkind (row | alias | numeric)\tboard ISO\n')
        for code in sorted(region):
            fo.write('%s\t%s\t%s\n' % (code, region[code][0], region[code][1]))
    rep = dict(perCapitaWeightByClass={k: round(v, 5) for k, v in K.items()},
               perCapitaWeightByClassAndRegion={'%s,%s' % k: round(v, 5) for k, v in sorted(KR.items())},
               referenceRowsByClass={k: sorted((iso, round(v, 4)) for iso, v in xs) for k, xs in per.items()},
               rows=len(out_rows), countries=len(total_by_iso), aliases=sum(1 for v in region.values() if v[0] == 'alias'),
               numeric=sum(1 for v in region.values() if v[0] == 'numeric'), isoRegions=len(ios),
               codesNotInIsoRegions=extra, totalWeight=round(sum(w for _, w, *_ in out_rows), 4),
               bucketWeights={b: round(sum(w for _, w, _, _, bb, _ in out_rows if bb == b), 4) for b, _ in buckets},
               problems=problems, table=report_rows, numericResolution={c: region[c][1] for c in region if region[c][0] == 'numeric'})
    with open(os.path.join(D2, 'countries_v2_report.json'), 'w', encoding='utf-8') as fo:
        json.dump(rep, fo, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k not in ('table', 'referenceRowsByClass')}, indent=1))
    if problems:
        sys.exit(1)


if __name__ == '__main__':
    main()
