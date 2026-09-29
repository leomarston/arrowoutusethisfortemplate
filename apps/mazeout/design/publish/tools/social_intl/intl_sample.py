#!/usr/bin/env python3
"""International social audit sampler (READ-ONLY use of the shipped Python reference, v552).
Boards for 15 countries at local 03:00 and 20:00 on Mon 2026-09-28 (real DST offsets), LOCAL partition with the app's
current offset (0) and the intended device offset. Writes JSON + prints a digest."""
import os, sys, json, time, collections
APP = '/Users/yago/Downloads/app-factory/apps/mazeout'
sys.path.insert(0, os.path.join(APP, 'Packages', 'PathCore', 'Tests', 'tools'))
import soc_model as M
M.use('v552')
from socialsim import core as K, population as Pp, names as Nm, events as E, data as D, shipped as SH
from datetime import datetime, timezone

OUT = sys.argv[1]
# real UTC offsets on 2026-09-28 (DST in force in US/EU)
REAL = dict(US=-240, DE=120, FR=120, ES=120, IT=120, BR=-180, TR=180, JP=540, KR=540, CN=480, PL=120, SK=120, SI=120,
            IN=330, SA=180)
TABLE = {r.iso for r in D.COUNTRY_ROWS}
def utc_of_local(h, off, d=28):
    return int(datetime(2026, 9, d, h, 0, tzinfo=timezone.utc).timestamp()) - off * 60

T_END = utc_of_local(20, -600) + 2 * 86400
shared = Pp.World(); shared.extend_to(T_END)
worlds = {}
def world_for(iso, off):
    if iso in TABLE:
        return shared
    k = (iso, off)
    if k not in worlds:
        W = Pp.World(local=(iso, off, D.EXTRA_CULTURE.get(iso, 'en')))
        W.extend_to(T_END)
        worlds[k] = W
    return worlds[k]

def rowinfo(W, c, j, t):
    nm, st = W.name(c, j)
    return dict(name=nm, style=st, level=W.level(c, j, t), iso=c.iso, cul=c.culture, arch=Pp.ARCH[c.a]['key'])

def movers(W, refs, t, dt):
    n = 0
    for (c, j) in refs:
        a = W.level(c, j, t - dt) if dt > 0 else W.level(c, j, t)
        b = W.level(c, j, t) if dt > 0 else W.level(c, j, t - dt)
        if b > a:
            n += 1
    return n

def board(iso, off, h):
    W = world_for(iso, off)
    t = utc_of_local(h, REAL[iso])
    N = W.joined(t, iso)
    top = W.top(t, 100, iso)
    toprefs = [(c, j) for (_, _, c, j) in top]
    out = dict(iso=iso, off=off, local_hour=h, utc=datetime.fromtimestamp(t, timezone.utc).isoformat(), N=N)
    out['top10'] = [rowinfo(W, c, j, t) for (c, j) in toprefs[:10]]
    out['top100_moved_last60'] = movers(W, toprefs, t, 3600)
    out['top100_move_next60'] = movers(W, toprefs, t, -3600)
    nb = {}
    for L in (60, 250):
        R = W.rank_of_level(L, t, iso)
        ab, be = W.neighbours(L, t, 10, 10, iso)
        refs = [(c, j) for (_, _, c, j) in ab] + [(c, j) for (_, _, c, j) in be]
        nb[L] = dict(rank=R, above=[rowinfo(W, c, j, t) for (_, _, c, j) in reversed(ab[:5])],
                     below=[rowinfo(W, c, j, t) for (_, _, c, j) in be[:5]],
                     moved_last60=movers(W, refs, t, 3600), move_next60=movers(W, refs, t, -3600), n=len(refs))
    out['nb'] = nb
    # name mix over the top 100 + both neighbourhoods
    allrefs = toprefs + [(c, j) for L in (60, 250) for (_, _, c, j) in sum(W.neighbours(L, t, 10, 10, iso), [])]
    st = collections.Counter(); cul = collections.Counter(); samples = []
    for (c, j) in allrefs:
        nm, s = W.name(c, j)
        st[s] += 1; cul[c.culture] += 1
        if len(samples) < 40: samples.append(nm)
    out['styles'] = dict(st); out['cultures'] = dict(cul); out['names40'] = samples
    return out

def hourly(iso, off):
    """movers in the previous hour among the country top-100 + L60 neighbourhood, per local hour 0..23"""
    W = world_for(iso, off)
    curve = []
    for h in range(24):
        t = utc_of_local(h, REAL[iso])
        top = [(c, j) for (_, _, c, j) in W.top(t, 100, iso)]
        ab, be = W.neighbours(60, t, 10, 10, iso)
        refs = top + [(c, j) for (_, _, c, j) in ab + be]
        curve.append(movers(W, refs, t, 3600))
    return curve

res = dict(boards=[], hourly={}, world={}, sizes={}, groups=[])
t0 = time.time()
for iso in REAL:
    offs = [REAL[iso]] if iso in TABLE else [0, REAL[iso]]
    for off in offs:
        for h in (3, 20):
            res['boards'].append(board(iso, off, h))
    print(iso, 'boards', round(time.time() - t0, 1), flush=True)
for iso, off in [('US', -240), ('JP', 540), ('BR', -180), ('TR', 180), ('IN', 330), ('CN', 0), ('CN', 480), ('SI', 0),
                 ('SI', 120), ('SK', 120)]:
    res['hourly']['%s@%d' % (iso, off)] = hourly(iso, off)
print('hourly', round(time.time() - t0, 1), flush=True)
# World board at JP 03:00 and US 20:00 (same world for everyone in the table)
for tag, iso, h in (('JP03', 'JP', 3), ('US20', 'US', 20)):
    t = utc_of_local(h, REAL[iso])
    top = [(c, j) for (_, _, c, j) in shared.top(t, 100)]
    res['world'][tag] = dict(top10=[rowinfo(shared, c, j, t) for (c, j) in top[:10]],
                             top100_iso=dict(collections.Counter(shared.cohorts[0].iso if False else c.iso for (c, j) in top)),
                             moved_last60=movers(shared, top, t, 3600))
    R = shared.rank_of_level(60, t)
    ab, be = shared.neighbours(60, t, 10, 10)
    res['world'][tag]['L60'] = dict(rank=R, isos=[c.iso for (_, _, c, j) in ab + be])
# country sizes over time
for d in ('2026-09-28', '2027-03-28', '2027-09-28', '2028-09-28', '2029-09-28'):
    y, mo, da = map(int, d.split('-'))
    t = int(datetime(y, mo, da, 12, tzinfo=timezone.utc).timestamp())
    Ws = Pp.World(); Ws.extend_to(t)
    row = {iso: Ws.joined(t, iso) for iso in sorted(TABLE)}
    row['WORLD'] = Ws.joined(t)
    Wl = Pp.World(local=('SI', 120, 'easteu')); Wl.extend_to(t)
    row['LOCAL(SI)'] = Wl.joined(t, 'SI')
    res['sizes'][d] = row
    print('sizes', d, round(time.time() - t0, 1), flush=True)
# Weekly + Streak groups for a JP / US / SI player joining at local 03:00 and 20:00
for iso, h in (('JP', 3), ('JP', 20), ('US', 3), ('US', 20), ('SI', 20)):
    W = world_for(iso, REAL[iso])
    t = utc_of_local(h, REAL[iso])
    wk = SH.Weekly(W, 777, K.event_week(t), float(t), 175.0)
    g = dict(iso=iso, h=h, weekly=[dict(name=W.name(c, j)[0], iso=c.iso, s3=wk.member_score(i, t + 3 * 3600),
                                        s0=wk.member_score(i, t)) for i, (c, j) in enumerate(wk.members)])
    sr = SH.Streak(W, 777, K.event_day(t), float(t), 20.0)
    g['streak_isos'] = dict(collections.Counter(c.iso for (c, j) in sr.members))
    g['streak_moving_first60'] = sum(1 for i in range(len(sr.members)) if (sr.member_score(i, t + 3600) or 0) > 0)
    res['groups'].append(g)
print('groups', round(time.time() - t0, 1), flush=True)
json.dump(res, open(OUT, 'w'), ensure_ascii=False, indent=1)
print('done', round(time.time() - t0, 1))
