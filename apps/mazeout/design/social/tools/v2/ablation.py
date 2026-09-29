#!/usr/bin/env python3
"""ablation.py — what each v2 switch buys: the per-country realism metrics with one switch left off at a time.

    python3 design/social/tools/v2/ablation.py OUT.json [config ...]
Configs: all (v2), -M1 (one country per cohort), strata1 (M1 with one contiguous block per cohort, the audit's prototype),
-M2 (no jitter), -M9 (no shards), -M3 (the v1 table), v552 (the shipped world, the audit's baseline). Each runs in its own
process (the switches patch modules in memory). Countries: US GB DE FR JP KR TR SK at the launch week and at world age 22 weeks.
"""
import os, sys, json, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIGS = dict(all=([], {}), **{'-M1': (['M1'], {}), 'strata1': ([], {'SOC_V2_STRATA': '1'}), '-M2': (['M2'], {}),
                                 '-M9': (['M9'], {}), '-M3': (['M3'], {}), 'v552': (None, {})})
ISOS = ['US', 'GB', 'DE', 'FR', 'JP', 'KR', 'TR', 'SK']

CHILD = r'''
import sys, json
sys.path.insert(0, %(tools)r)
sys.path.insert(0, %(here)r)
off = %(off)r
if off is None:
    from socialsim import shipped as SH; SH.apply()
    from socialsim import core as K; EPOCH = K.EPOCH
else:
    from socialsim import v2 as V2; V2.apply(off); EPOCH = V2.WORLD_EPOCH if 'M8' not in off else None
from socialsim import core as K, population as Pp, data as D
import calib_v2 as C
EPOCH = EPOCH or K.EPOCH
from datetime import datetime, timezone
weeks = dict(launch=int(datetime(2026, 10, 5, 7, tzinfo=timezone.utc).timestamp()) + (0 if off is not None else -19 * 7 * 86400),
             age22=EPOCH + 22 * K.WEEK)
W = Pp.World(); W.extend_to(max(weeks.values()) + 8 * 86400)
out = dict(cohorts=len(W.cohorts))
for k, ws in weeks.items():
    out[k] = {}
    for iso in %(isos)r:
        if not any(r.iso == iso for r in D.COUNTRY_ROWS):
            continue
        r = C.country_week(W, iso, ws, first_name=False)
        out[k][iso] = dict(players=W.joined(ws, iso), dead=r['deadHours'], ladder=r['ladderPairsWorst'], run=r['equalGapRunWorst'],
                           movers=r['medianMovers'])
print('RESULT' + json.dumps(out))
'''


def main():
    out = sys.argv[1]
    which = sys.argv[2:] or list(CONFIGS)
    res = {}
    for name in which:
        off, env = CONFIGS[name]
        code = CHILD % dict(tools=os.path.normpath(os.path.join(HERE, '..')), here=HERE, off=off, isos=ISOS)
        t = time.time()
        # calib_v2 applies v2 at import: give it the same switches through argv
        argv = ['--off', ','.join(off)] if off else []
        r = subprocess.run(['nice', '-n', '19', sys.executable, '-c', code] + argv, capture_output=True, text=True,
                           env=dict(os.environ, **env, **({'SOC_CALIB_NOAPPLY': '1'} if off is None else {})))
        line = [l for l in r.stdout.splitlines() if l.startswith('RESULT')]
        res[name] = json.loads(line[0][6:]) if line else dict(error=r.stderr[-1500:])
        res[name]['seconds'] = round(time.time() - t)
        print(name, json.dumps(res[name])[:600], flush=True)
        with open(out, 'w') as f:
            json.dump(res, f, indent=1)


if __name__ == '__main__':
    main()
