#!/usr/bin/env python3
"""go4.py (PH-0 2026-09-28: go3 + --r3 [--r3-gap 0.85] = win clip with 4 empty-board taps after the last arrow; clips named S4-*)
go3.py LEVEL NNN [--intro] [--clips long,retap,hit] [--min-left 60] [--min-gap 5] — phone session 3.

go2 (corner-aware bot) + session-3 extras, all AUTOMATIC (no pauses, no thinking with the clock running):
  --intro      record the Play tap + level intro as video/S3-L<lvl>-play-intro.mov (catches any unlock card's entrance)
  --clips K    a hook on bot.plan(): at the start of every bot round (fresh read), if a candidate exists and >= --min-left s remain
               on the level clock (estimated from the start timer), run the clip, then skip that round's taps (re-read):
                 long  = LONG-GAP bump: a blocked arrow whose first blocker is >= --min-gap empty cells ahead on a STRAIGHT ray
                         → clip S3-L<lvl>-bump-gap<G>.mov + lossless shot NNN+k-L<lvl>-bump.png
                 retap = right after it, a re-tap of that (now RED) arrow → clip S3-L<lvl>-red-retap.mov + shot -retap.png
                 hit   = hit tolerance: taps at 1/3 then (2.0 s later) 2/3 between two parallel free straight arrows 1 cell apart
                         → clip S3-L<lvl>-hit-tolerance.mov + shot -hit.png
  then play2 → end popup shot → Continue → home (as go.py). Writes build/phone3/go3-L<lvl>.json (what was done, taps, times).
More (added during session 3): combo (clips-needed #10) in --clips; --win-clip (last taps + celebration); --pause-clip (pause
open/close before the first tap); --elevator (v552 elevator: lavender platform detected per round, the round that empties a platform
stops after that tap and is recorded as S3-L<lvl>-elevator-open, then L<lvl>-open1.json); --fixfit / --fit-from SHOT (every read uses
the start grid: the zoom never changes in a level; fixes a mid-level grid drift); --here (level already open, clock not running);
--resume (level PAUSED by the bot: Resume + continue, start JSON kept); --min-gap/--max-gap/--pre/--hit-max-pitch/--min-timer.
Exit codes: 2 guard (not a clean board: unlock card? popup?), 3 anomalies/unknown before the first tap (clock NOT running),
5 not on a clean HOME before Play, 6 board not clean after the pause clip."""
import os, sys, time, json, subprocess
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import corners  # noqa: F401  (patches bot.read_board / bot.ray)
import bot
if '--fast' in sys.argv:   # PH-0: fewer retry rounds on big boards — wait a bit longer after taps (exits finish), shorter retry sleeps
    import types as _types, time as _time
    _map = {0.45: 0.75, 0.7: 0.3, 0.6: 0.3}
    bot.time = _types.SimpleNamespace(time=_time.time, strftime=_time.strftime, localtime=_time.localtime,
                                      sleep=lambda s_: _time.sleep(_map.get(s_, s_)))
import numpy as np
from PIL import Image

L = int(sys.argv[1]); N = int(sys.argv[2])
def opt(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default
INTRO = '--intro' in sys.argv
CLIPS = [c for c in opt('--clips', '').split(',') if c]
MINLEFT = float(opt('--min-left', '60')); MINT = int(opt('--min-timer', '150')); MINGAP = int(opt('--min-gap', '5')); PRE = opt('--pre', '3.0'); MAXGAP = int(opt('--max-gap', '99')); HITMAXP = float(opt('--hit-max-pitch', '99'))
R = bot.ROOT; T = '/Users/yago/Downloads/app-factory/apps/mazeout/research/tools'
B3 = '/Users/yago/Downloads/app-factory/apps/mazeout/build/phone3'
SP = '/private/tmp/claude-501/-Users-yago-Downloads-app-factory/67834757-7bc9-4e4f-a907-36f39cf8e3e8/scratchpad'
prev = f'{SP}/prev.png'
rec = dict(level=L, start_n=N, t_start=time.strftime('%H:%M:%S'), clips=[], shots=[])
LL = f'L{L:03d}'
nxt = [N + 1]
def save():
    json.dump(rec, open(f'{B3}/go3-{LL}.json', 'w'), indent=1, default=str)
def newshot(tag):
    p = f'{R}/shots/{nxt[0]:03d}-{LL}-{tag}.png'; nxt[0] += 1; return p
def recact(name, secs, *args, tail='2.5', pre='1.5'):
    env = dict(os.environ, RECACT_TAIL=tail, RECACT_PRE=pre)
    t0 = time.time()
    r = subprocess.run(['sh', f'{T}/recact.sh', name, str(secs), '--', *map(str, args)], capture_output=True, text=True, env=env, timeout=120)
    out = (r.stdout.strip().splitlines() or [''])[-1]
    rec['clips'].append(dict(name=name, act=list(map(str, args)), at=time.strftime('%H:%M:%S', time.localtime(t0)), log=out, stdout=r.stdout.strip().splitlines()))
    print('CLIP', name, out, flush=True)
    return out

# ---- start (only from a clean HOME: a popup that opened by itself would take the Play tap)
S = 1178 / 393
def is_home(path):
    g = np.array(Image.open(path).convert('RGB')).astype(int)[int(800 * S):int(845 * S), int(5 * S):int(30 * S)].reshape(-1, 3)
    return ((g[:, 2] > 180) & (g[:, 0] < 90) & (g[:, 1] > 60)).mean() > 0.6
RESUME = '--resume' in sys.argv      # the level is PAUSED mid-play (bot stop): Resume, fresh shot NNN-L<lvl>-resume.png, keep the start JSON
HERE = '--here' in sys.argv or RESUME          # the level is already open (clock not running): use a fresh shot, no Play tap
FITFROM = opt('--fit-from', None)     # read every round with the grid fitted on this (start) shot: the zoom never changes in a level
if FITFROM:
    _rb = bot.read_board
    _im0 = np.array(Image.open(FITFROM).convert('RGB')).astype(np.int16)
    FIT0 = _rb(_im0)['fit']
    def read_fixed(im_, fit=None):
        return _rb(im_, fit=FIT0)
    bot.read_board = read_fixed
if '--skip-home-check' not in sys.argv and not HERE:
    hp = f'{B3}/go3-home-check.png'; bot.shot(hp)
    if not is_home(hp):
        Image.open(hp).resize((393, 852)).save(prev); print('NOT HOME before Play (popup?) → look at', prev); sys.exit(5)
start = f'{R}/shots/{N:03d}-{LL}-' + ('resume.png' if RESUME else 'start.png')
if RESUME:
    r_ = subprocess.run(['sh', f'{T}/resume.sh'], capture_output=True, text=True).stdout.strip(); print('resume:', r_.splitlines()[-1] if r_ else r_, flush=True)
    time.sleep(0.5)
elif HERE:
    pass
elif INTRO:
    recact(f'S4-{LL}-play-intro', 4, 'tap', 196, 668, tail='2')
    time.sleep(0.2)
else:
    subprocess.run([bot.PHONE, 'tap', '196', '668'], capture_output=True)
    time.sleep(1.6)
im = bot.shot(start)
rec['shots'].append(start)
Image.open(start).resize((393, 852)).save(prev)
ok, why, info = bot.guard(im)
if not ok:
    print('GUARD', why, info, '→ look at', prev); save(); sys.exit(2)
b = bot.apply_overrides(im, bot.read_board(im), L)
if '--fixfit' in sys.argv and not FITFROM:   # every later read uses this start grid (the zoom never changes inside a level)
    _rb2 = bot.read_board; FIT1 = b['fit']
    bot.read_board = lambda im_, fit=None: _rb2(im_, fit=FIT1)
ov = f'{bot.OVL}/{LL}-start.png'
bot.overlay(im, b, ov)
a = Image.open(start).resize((393, 852)); o = Image.open(ov).resize((393, 852))
W = Image.new('RGB', (796, 852), 'white'); W.paste(a, (0, 0)); W.paste(o, (403, 0)); W.save(prev)
unk = [x for x in b['obstacles'] if x['kind'] == 'unknown']
kinds = sorted({x['kind'] for x in b['obstacles']})
tsecs = None
try:
    j = json.loads(subprocess.run([f'{R}/video-tools/vocr', '--crop', '370', '245', '190', '85', '--scale', '2', start],
                                  capture_output=True, text=True, timeout=30).stdout.splitlines()[0])
    t = ''.join(j['lines']).replace(' ', '')
    m, s = t.split(':'); tsecs = int(m) * 60 + int(s); rec['timer'] = t
except Exception:
    rec['timer'] = None
print('READ arrows', len(b['arrows']), 'pitch_pt %.2f' % (b['fit']['pitch'] / bot.SCALE), 'obstacles', kinds, 'corners', len(b.get('corners', [])),
      'timer', rec['timer'], 'anomalies', b['anomalies'], 'unknown', [(x['bbox_px'], x['mean_rgb']) for x in unk], flush=True)
rec.update(arrows=len(b['arrows']), pitch_pt=round(b['fit']['pitch'] / bot.SCALE, 2), obstacles=kinds)
if (b['anomalies'] or unk) and '--force-start' not in sys.argv:   # PH-0: --force-start plays on (with --ignore-anomalies)
    print('STOP before first tap (timer not running) → look at', prev); save(); sys.exit(3)
if not RESUME:
    bot.dump_level(b, L, start, zoom='fit', timer=tsecs)
if '--pause-clip' in sys.argv:        # pause open → Resume, before the first board tap (clock not running yet)
    recact(f'S3-{LL}-pause-open-close', 4.5, 'taps', '352,88;123,530', '2.0', pre='2.0')
    time.sleep(0.4); ps = newshot('after-pause-clip'); bot.shot(ps); rec['shots'].append(ps)
    im2 = np.array(Image.open(ps).convert('RGB')).astype(np.int16)
    ok2, why2, _ = bot.guard(im2)
    if not ok2:
        print('after the pause clip the board is not clean:', why2, '→ look at', ps); save(); sys.exit(6)


# ---- gap candidates on a board (as tools/gapscan.py, + straightness + blocker id)
def find_longs(bd):
    occ = {tuple(c): x['id'] for x in bd['arrows'] for c in x['cells']}
    doors = set(map(tuple, bd.get('door_cells', []))) | bot.pipe_cells(bd); taped = bot.taped_ids(bd)
    out = []
    for x in bd['arrows']:
        if x['id'] in taped: continue
        r = bot.ray(bd, x); gap = None; blk = None
        for i, c in enumerate(r):
            if (c in occ and occ[c] != x['id']) or c in doors: gap = i; blk = occ.get(c, 'door'); break
        if gap is None or gap < MINGAP: continue
        d = bot.DIRS[x['dir']]; hc = x['cells'][-1]
        straight = all(r[i] == (hc[0] + (i + 1) * d[0], hc[1] + (i + 1) * d[1]) for i in range(gap + 1))
        cell, xy = bot.tap_point(bd, x)
        out.append(dict(id=x['id'], dir=x['dir'], gap=gap, n=len(x['cells']), blocker=blk, straight=straight, tap=[round(v, 1) for v in xy]))
    return out
def find_par(bd):
    occ = {tuple(c): x['id'] for x in bd['arrows'] for c in x['cells']}
    doors = set(map(tuple, bd.get('door_cells', []))) | bot.pipe_cells(bd); taped = bot.taped_ids(bd)
    free = []
    for x in bd['arrows']:
        if x['id'] in taped: continue
        r = bot.ray(bd, x)
        if any((c in occ and occ[c] != x['id']) or c in doors for c in r): continue
        free.append(x)
    f = bd['fit']; p = f['pitch']
    def P(c): return [round((f['x0'] + c[0] * p) / bot.SCALE, 1), round((f['y0'] + c[1] * p) / bot.SCALE, 1)]
    st = [x for x in free if len({c[0] for c in x['cells']}) == 1 or len({c[1] for c in x['cells']}) == 1]
    par = []
    for i, x in enumerate(st):
        for y in st[i + 1:]:
            if x['dir'] != y['dir']: continue
            if x['dir'] in ('up', 'down'):
                if abs(x['cells'][0][0] - y['cells'][0][0]) == 1 and set(c[1] for c in x['cells']) & set(c[1] for c in y['cells']):
                    rows = sorted(set(c[1] for c in x['cells']) & set(c[1] for c in y['cells'])); rr = rows[len(rows) // 2]
                    par.append(dict(ids=[x['id'], y['id']], dir=x['dir'], a=P((x['cells'][0][0], rr)), b=P((y['cells'][0][0], rr)), pitch_pt=round(p / bot.SCALE, 2)))
            else:
                if abs(x['cells'][0][1] - y['cells'][0][1]) == 1 and set(c[0] for c in x['cells']) & set(c[0] for c in y['cells']):
                    cols = sorted(set(c[0] for c in x['cells']) & set(c[0] for c in y['cells'])); cc = cols[len(cols) // 2]
                    par.append(dict(ids=[x['id'], y['id']], dir=x['dir'], a=P((cc, x['cells'][0][1])), b=P((cc, y['cells'][0][1])), pitch_pt=round(p / bot.SCALE, 2)))
    return par

l0 = find_longs(b); p0 = find_par(b)
rec.update(start_longs=l0[:6], start_par=p0[:4])
print('START GAP long', [(x['id'], x['dir'], x['gap'], x['straight']) for x in l0][:6], 'par', len(p0), flush=True)
save()

# ---- the clip hook (runs inside play2's round loop, on its fresh read)
T0 = [None]
done = dict(long=False, hit=False)
orig_plan = bot.plan
def plan_hook(board, *aa, **kk):
    taps = orig_plan(board, *aa, **kk)
    try:
        return _hook(board, taps)
    except Exception as e:  # never let a clip helper kill the bot with the clock running
        print('HOOK ERROR', repr(e), flush=True); rec.setdefault('hook_errors', []).append(repr(e))
        if T0[0] is None and taps: T0[0] = time.time()
        return taps
WINCLIP = '--win-clip' in sys.argv or '--r3' in sys.argv
R3 = '--r3' in sys.argv; R3GAP = float(opt('--r3-gap', '0.85')); R3N = int(opt('--r3-n', '4'))    # record the last taps + the win celebration + the popup entrance as S3-L<lvl>-win.mov
def combo_clip(board):
    """clips-needed #10: 6 free arrows ~0.45 s apart, a 2.0 s pause, a 7th, then (~0.3 s later) a bump — one 60 fps recording."""
    frees = bot.batch(board, bot.free_arrows(board))
    if len(frees) < 7: return False
    ids7 = {a['id'] for a in frees[:7]}
    occ = {tuple(c): x['id'] for x in board['arrows'] for c in x['cells']}
    doors = set(map(tuple, board.get('door_cells', []))) | bot.pipe_cells(board); taped = bot.taped_ids(board)
    bump = None
    for x in board['arrows']:
        if x['id'] in ids7 or x['id'] in taped: continue
        r = bot.ray(board, x)
        for c in r:
            if c in doors: break
            if c in occ and occ[c] != x['id']:
                if occ[c] not in ids7: bump = x
                break
        if bump: break
    if not bump: return False
    pts = [bot.tap_point(board, a)[1] for a in frees[:7]]; bp = bot.tap_point(board, bump)[1]
    out = f'{R}/video/S3-{LL}-combo.mov'
    for f in (out, out + '.log'):
        if os.path.exists(f): os.remove(f)
    subprocess.Popen([bot.PHONE, 'rec', out, '12'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(80):
        if os.path.exists(out + '.log') and 'RECORDING' in open(out + '.log').read(): break
        time.sleep(0.1)
    time.sleep(2.0)
    marks = ['ACT1 %.3f' % time.time()]
    r1 = subprocess.run([bot.PHONE, 'taps', ';'.join('%.1f,%.1f' % p for p in pts[:6]), '0.45'], capture_output=True, text=True).stdout.strip()
    marks.append('ACT1_DONE %.3f %s' % (time.time(), r1)); time.sleep(2.0)
    marks.append('ACT2 %.3f' % time.time())
    r2 = subprocess.run([bot.PHONE, 'taps', '%.1f,%.1f;%.1f,%.1f' % (pts[6][0], pts[6][1], bp[0], bp[1]), '0.3'], capture_output=True, text=True).stdout.strip()
    marks.append('ACT2_DONE %.3f %s' % (time.time(), r2))
    open(out + '.marks', 'w').write('\n'.join(marks) + '\n')
    for _ in range(150):
        if os.path.exists(out + '.log') and ('SAVED' in open(out + '.log').read() or 'ERROR' in open(out + '.log').read()): break
        time.sleep(0.2)
    rec['combo'] = dict(frees=[a['id'] for a in frees[:7]], taps=[[round(v, 1) for v in p] for p in pts], bump=dict(id=bump['id'], tap=[round(v, 1) for v in bp]),
                        log=open(out + '.log').read().strip().splitlines()[-1] if os.path.exists(out + '.log') else None)
    print('CLIP', os.path.basename(out), rec['combo']['log'], flush=True)
    s4 = newshot('combo'); bot.shot(s4); rec['shots'].append(s4)
    save()
    return True
ELEV = '--elevator' in sys.argv      # v552 ELEVATOR (unlock L100): platform = lavender double door; arrows stand on it
def platform_cells(im_, bd):
    """cells whose off-centre sample points are lavender (the elevator platform while its doors are CLOSED)."""
    f_ = bd['fit']; p_ = f_['pitch']; c_lo, r_lo, c_hi, r_hi = bd['bounds']
    out = set()
    for c in range(c_lo - 1, c_hi + 2):
        for r in range(r_lo - 1, r_hi + 2):
            n = 0
            for dx, dy in ((-.33, -.33), (.33, -.33), (-.33, .33), (.33, .33)):
                x = int(f_['x0'] + (c + dx) * p_); y = int(f_['y0'] + (r + dy) * p_)
                if 0 <= y < im_.shape[0] and 0 <= x < im_.shape[1]:
                    R_, G_, B_ = [int(v) for v in im_[y, x]]
                    if 125 <= R_ <= 218 and 20 <= B_ - R_ <= 55 and 0 <= G_ - R_ <= 12 and B_ >= 170: n += 1
            if n >= 2: out.add((c, r))
    return out
LASTIM = [None]
_shot = bot.shot
def shot_keep(path):
    a_ = _shot(path); LASTIM[0] = (path, a_); return a_
bot.shot = shot_keep
def elevator_guard(board, taps):
    """one read → if this round's taps would EMPTY the platform, tap only up to that and nothing whose ray crosses the platform
    (the hidden layer blocks from the moment the doors start opening); record that round as clip S3-L<lvl>-elevator-open."""
    if LASTIM[0] is None: return taps
    P = platform_cells(LASTIM[0][1], board)
    rec.setdefault('elev_rounds', []).append(len(P))
    if not P:
        if rec.get('elev_had') and not rec.get('elev_open_dumped'):
            rec['elev_open_dumped'] = True
            bot.dump_level(board, L, LASTIM[0][0], suffix='-open1', extra=dict(note='state after the ELEVATOR opened (hidden layer up); cells in the START json frame'))
            print('elevator open → dumped', f'{LL}-open1.json', flush=True)
        return taps
    rec['elev_had'] = True
    if rec.get('elev_cells') is None:
        rec['elev_cells'] = sorted([list(c) for c in P])
    # connected platforms (a level can hold several elevators; each opens on its own)
    comps = []; seen = set()
    for c0_ in sorted(P):
        if c0_ in seen: continue
        stack = [c0_]; comp = set(); seen.add(c0_)
        while stack:
            q = stack.pop(); comp.add(q)
            for d_ in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n_ = (q[0] + d_[0], q[1] + d_[1])
                if n_ in P and n_ not in seen: seen.add(n_); stack.append(n_)
        comps.append(comp)
    ons = [{a['id'] for a in board['arrows'] if any(tuple(c) in comp for c in a['cells'])} for comp in comps]
    ons = [o_ for o_ in ons if o_]
    rec.setdefault('elev_comps', []).append([len(c) for c in comps])
    if not ons:
        return taps
    tapped = set(); keep = []; empties = False
    for u, c, xy in taps:
        keep.append((u, c, xy)); tapped |= set(u['ids'])
        if any(o_ <= tapped for o_ in ons):
            empties = True; break          # stop right after the tap that empties a platform; re-read next round
    if empties:
        spec = ';'.join('%.1f,%.1f' % xy for _, _, xy in keep)
        if not rec.get('elev_clip'):
            rec['elev_clip'] = dict(n=len(keep), on_platforms=[sorted(o_) for o_ in ons], spec=spec)
            recact(f'S3-{LL}-elevator-open', max(4, 0.8 * len(keep) + 2), 'taps', spec, '0.05', tail='3')
            save()
            return []
        return keep
    return taps
def _hook(board, taps):
    if ELEV:
        taps = elevator_guard(board, taps)
        if not taps: return taps
    if 'combo' in CLIPS and not done.get('combo') and tsecs is not None and tsecs >= MINT:
        done['combo'] = True
        if T0[0] is None: T0[0] = time.time()
        if combo_clip(board):
            return []
    if WINCLIP and not done.get('win') and taps and len(board['arrows']) > 5 and len(taps) > 3 \
            and sum(len(u['ids']) for u, c, xy in taps) == len(board['arrows']) \
            and not any(o['kind'] in ('door', 'key', 'box', 'box_part') for o in board.get('obstacles', [])):
        return taps[:-3]      # PH-0: this round would clear the board with > 5 arrows: keep the last 3 units for the win clip
    if WINCLIP and not done.get('win') and taps and len(board['arrows']) <= 5 \
            and sum(len(u['ids']) for u, c, xy in taps) == len(board['arrows']) \
            and not any(o['kind'] in ('door', 'key', 'box', 'box_part') for o in board.get('obstacles', [])):
        done['win'] = True
        spec = ';'.join('%.1f,%.1f' % xy for _, _, xy in taps)
        if R3:   # PH-0c R3: the last arrows, then 4 taps on the empty board (196,600) — uniform gap R3GAP
            spec = spec + ';' + ';'.join(['196,600'] * R3N)
            rec['win_clip'] = dict(arrows=len(board['arrows']), spec=spec, gap=R3GAP)
            recact(f'S4-R3-{LL}-win-taps' + ('' if R3N == 4 and R3GAP == 0.85 else f'-n{R3N}-g{R3GAP}'), 12, 'taps', spec, str(R3GAP), tail='3', pre='2.5')
        else:
            rec['win_clip'] = dict(arrows=len(board['arrows']), spec=spec)
            recact(f'S4-{LL}-win', 9, 'taps', spec, '0.3', tail='3', pre='2.5')
        save()
        return []
    if not CLIPS or tsecs is None or tsecs < MINT:
        return taps
    left = tsecs - (time.time() - T0[0]) if T0[0] else tsecs
    if left < MINLEFT:
        return taps
    if 'long' in CLIPS and not done['long']:
        cands = [x for x in find_longs(board) if x['straight'] and x['gap'] <= MAXGAP]
        if cands:
            c = sorted(cands, key=lambda z: -z['gap'])[0]
            done['long'] = True; rec['bump'] = dict(c, clock_left_est=round(left, 1), rnd_arrows=len(board['arrows']))
            if T0[0] is None: T0[0] = time.time()
            recact(f'S3-{LL}-bump-gap{c["gap"]}', 3.5, 'tap', *c['tap'], pre=PRE)
            s1 = newshot('bump'); bot.shot(s1); rec['shots'].append(s1)
            if 'retap' in CLIPS:
                recact(f'S3-{LL}-red-retap', 3.5, 'tap', *c['tap'], pre=PRE)
                s2 = newshot('retap'); bot.shot(s2); rec['shots'].append(s2)
            save()
            return []
    if 'hit' in CLIPS and not done['hit']:
        par = [q for q in find_par(board) if q['pitch_pt'] <= HITMAXP]
        if par:
            q = par[0]; A_, B_ = q['a'], q['b']
            t1 = [round(A_[0] + (B_[0] - A_[0]) / 3, 1), round(A_[1] + (B_[1] - A_[1]) / 3, 1)]
            t2 = [round(A_[0] + 2 * (B_[0] - A_[0]) / 3, 1), round(A_[1] + 2 * (B_[1] - A_[1]) / 3, 1)]
            done['hit'] = True; rec['hit'] = dict(pair=q, t1=t1, t2=t2, clock_left_est=round(left, 1))
            if T0[0] is None: T0[0] = time.time()
            recact(f'S3-{LL}-hit-tolerance', 5, 'taps', f'{t1[0]},{t1[1]};{t2[0]},{t2[1]}', '2.0', tail='3')
            s3 = newshot('hit'); bot.shot(s3); rec['shots'].append(s3)
            save()
            return []
    if T0[0] is None and taps: T0[0] = time.time()
    return taps
bot.plan = plan_hook

res = bot.play2(L, 230)
print('PLAY', res, flush=True)
rec['play'] = res; rec['t_end'] = time.strftime('%H:%M:%S')
def is_win(path):
    q = np.array(Image.open(path).convert('RGB')).astype(int)[int(425 * S):int(475 * S), int(215 * S):int(290 * S)].reshape(-1, 3)
    return ((q[:, 0] > 235) & (q[:, 1] > 235) & (q[:, 2] > 235)).mean() > 0.25
shots = [start]
if res == 'guard':
    c1 = newshot('end-a'); bot.shot(c1)
    time.sleep(2.3)
    c2 = newshot('end-popup'); bot.shot(c2); shots.append(c2)
    if is_win(c2):
        print('WIN popup detected → Continue', flush=True); rec['result'] = 'win'
        subprocess.run([bot.PHONE, 'tap', '196', '538'], capture_output=True)
        time.sleep(3.6)
        c3 = f'{R}/shots/{nxt[0]:03d}-after-{LL}.png'; nxt[0] += 1; bot.shot(c3); shots.append(c3)
        for k in range(2):
            if is_home(c3):
                break
            print('after-Continue screen is not home (event progress?) → tap (196,785)')
            subprocess.run([bot.PHONE, 'tap', '196', '785'], capture_output=True)
            time.sleep(2.4)
            c3 = f'{R}/shots/{nxt[0]:03d}-after-{LL}-home{k + 1}.png'; nxt[0] += 1; bot.shot(c3); shots.append(c3)
        rec['home'] = is_home(c3)
        print('NEXT free shot number', nxt[0], 'home' if is_home(c3) else 'NOT HOME')
    else:
        rec['result'] = 'not-win-popup'
        print('NOT a win popup — look; NEXT free shot number', nxt[0])
else:
    c1 = newshot('stopped'); bot.shot(c1); shots.append(c1); rec['result'] = res
    print('NEXT free shot number', nxt[0])
rec['next'] = nxt[0]; rec['end_shots'] = shots
save()
Wd = Image.new('RGB', (268 * len(shots), 568), 'white')
for i, sp in enumerate(shots):
    Wd.paste(Image.open(sp).resize((262, 568)), (i * 268, 0))
Wd.save(prev)
print('montage →', prev)
