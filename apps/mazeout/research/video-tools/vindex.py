#!/usr/bin/env python3
"""vindex — index the owner's two gameplay videos (levels, taps, bumps, wins/fails, popups/captions).

  python3 vindex.py scan V1|V2          # run ./vscan over the whole video (cached in video-frames/work/V?.scan.jsonl)
  python3 vindex.py build [V1] [V2]     # segment + OCR + per-level events -> video-frames/work/V?.index.json
  python3 vindex.py write               # merge both into research/video-index.json + research/video-index.md

Inputs: video-frames/work/V?.scan.jsonl (./vscan, one JSON row per frame: V1 every frame at 25 fps, V2 every 2nd at ~30 fps),
        video-frames/V?/scan/f<ms>.jpg (2 fps, width 296; mfx pass, used for screen signatures).
Full-res frames are grabbed on demand with ./vgrab and read with ./vocr (both cached under video-frames/).
Coordinates: FULL-RES PIXELS of the 592x1280 frame; pt = px * 393/592 (0.6639).
"""
import json, os, re, subprocess, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.dirname(HERE)
FR = os.path.join(RES, 'video-frames')
WORK = os.path.join(FR, 'work')
VGRAB, VOCR, VSCAN = (os.path.join(HERE, n) for n in ('vgrab', 'vocr', 'vscan'))
VIDEOS = {
    'V1': dict(path='research/video/owner/V1-levels-01-20.mp4', dur=505.12, fps=25.0, scan_fps=0),
    'V2': dict(path='research/video/owner/V2-levels-11-38.mp4', dur=1683.508, fps=59.643, scan_fps=30),
}
PT = 393 / 592.0
os.makedirs(WORK, exist_ok=True)


# ------------------------------------------------------------------------------------------------ helpers
def load_scan(V):
    rows = [json.loads(l) for l in open(os.path.join(WORK, V + '.scan.jsonl'))]
    rows.sort(key=lambda d: d['t'])
    return rows


def grab(V, t, name=None, sub='grab', width=None):
    """exact full-res frame at t -> path (cached; a named frame is re-grabbed when its time changed)"""
    d = os.path.join(FR, V, sub)
    os.makedirs(d, exist_ok=True)
    nm = name or 't%07d' % int(round(t * 1000))
    p = os.path.join(d, nm + '.png')
    side = os.path.join(d, '_times.json')
    times = json.load(open(side)) if os.path.exists(side) else {}
    if not os.path.exists(p) or (name and abs(times.get(nm, -1) - t) > 1e-4):
        cmd = [VGRAB, V, d, '--quiet']
        if width:
            cmd += ['--width', str(width)]
        subprocess.run(cmd + ['%.3f:%s' % (t, nm)], check=True, capture_output=True)
        if name:
            times[nm] = round(t, 4)
            json.dump(times, open(side, 'w'), indent=0, sort_keys=True)
    return p


_ocr_cache = {}


def ocr(path, crop=None, scale=1):
    key = (path, int(os.path.getmtime(path) * 1000), tuple(crop) if crop else None, scale)
    cf = os.path.join(WORK, 'ocr_cache.json')
    if not _ocr_cache and os.path.exists(cf):
        for k, v in json.load(open(cf)).items():
            _ocr_cache[k] = v
    ks = json.dumps(key)
    if ks in _ocr_cache:
        return _ocr_cache[ks]
    cmd = [VOCR]
    if crop:
        cmd += ['--crop'] + [str(int(c)) for c in crop]
    if scale != 1:
        cmd += ['--scale', str(scale)]
    r = subprocess.run(cmd + [path], capture_output=True, text=True, check=True)
    d = json.loads(r.stdout.strip().splitlines()[0])
    res = dict(lines=d.get('lines', []), words=d.get('words', []))
    _ocr_cache[ks] = res
    return res


def save_ocr_cache():
    json.dump(_ocr_cache, open(os.path.join(WORK, 'ocr_cache.json'), 'w'))


DIGIT = str.maketrans({'L': '1', 'S': '5', 's': '5', 'O': '0', 'o': '0', 'I': '1', 'l': '1', '|': '1', 'B': '8', 'Z': '2', 'z': '2',
                       'G': '6', 'g': '9', 'q': '9', 'T': '7', 'A': '4'})


def num(tok):
    t = tok.translate(DIGIT)
    return int(t) if t.isdigit() else None


def btn_kind(btn):
    r, g, b = btn
    if r > 150 and g < 110 and b < 120:
        return 'hard'
    if r > 180 and g < 150 and b < 160 and r > b + 50:
        return 'hard'
    if r > 90 and b > 150 and g < 90:
        return 'superhard'
    return 'normal'


def hearts(d):
    return sum(1 for h in d['hrt'] if h > 0.3)


# ------------------------------------------------------------------------------------------------ classification
def is_play(d):
    return d['bg'] > 0.45


def runs(rows, key):
    out = []
    for i, d in enumerate(rows):
        k = key(d)
        if out and out[-1][0] == k:
            out[-1][2] = i
        else:
            out.append([k, i, i])
    return out


def smooth_runs(rows, key, min_dur=0.3):
    """runs of key(d); runs shorter than min_dur are absorbed by the previous run"""
    rr = runs(rows, key)
    changed = True
    while changed and len(rr) > 1:
        changed = False
        for j, (k, a, b) in enumerate(rr):
            dur = rows[b]['t'] - rows[a]['t']
            if dur < min_dur and 0 < j < len(rr) - 1:
                rr[j - 1][2] = b
                del rr[j]
                # merge neighbours that now touch with the same key
                if j < len(rr) and rr[j][0] == rr[j - 1][0]:
                    rr[j - 1][2] = rr[j][2]
                    del rr[j]
                changed = True
                break
    return rr


# ------------------------------------------------------------------------------------------------ taps
def tap_tracks(rows, a, b, dt_max=0.13, dist=45):
    """link touch blobs of rows[a..b] into tracks; one track = one touch (tap or drag)"""
    tracks = []
    live = []
    for i in range(a, b + 1):
        d = rows[i]
        if not is_play(d):
            continue
        nxt = []
        used = set()
        for (x, y, n) in d['tch']:
            best = None
            for tr in live:
                if id(tr) in used:
                    continue
                lx, ly = tr['pts'][-1][1], tr['pts'][-1][2]
                if d['t'] - tr['pts'][-1][0] <= dt_max and abs(x - lx) + abs(y - ly) <= dist:
                    best = tr
                    break
            if best is None:
                best = dict(pts=[])
                tracks.append(best)
            best['pts'].append((d['t'], x, y, n))
            used.add(id(best))
            nxt.append(best)
        live = [tr for tr in live if d['t'] - tr['pts'][-1][0] <= dt_max and id(tr) not in used] + nxt
    out = []
    for tr in tracks:
        p = tr['pts']
        big = max(p, key=lambda q: q[3])
        if len(p) < 2 and big[3] < 150:
            continue
        span = max(abs(p[-1][1] - p[0][1]), abs(p[-1][2] - p[0][2]))
        # debris (a box / curtain shattering throws grey shards) = several grey blobs in the same frame
        debris = max(len(rows[at(rows, q[0])]['tch']) for q in p) >= 3
        out.append(dict(t=round(p[0][0], 3), t_last=round(p[-1][0], 3), x=int(big[1]), y=int(big[2]), frames=len(p),
                        area=int(big[3]), drag=span > 40, weak=len(p) < 2 or debris))
    return out


# ------------------------------------------------------------------------------------------------ screens (non-play)
def scan_jpg(V, t):
    d = os.path.join(FR, V, 'scan')
    fs = SCANJPG.get(V)
    if fs is None:
        fs = sorted((int(f[1:8]) / 1000.0, f) for f in os.listdir(d) if f.endswith('.jpg'))
        SCANJPG[V] = fs
    ts = [x[0] for x in fs]
    i = int(np.argmin(np.abs(np.array(ts) - t)))
    return os.path.join(d, fs[i][1]), fs[i][0]


SCANJPG = {}


def signature(path):
    im = Image.open(path).convert('RGB').resize((12, 26), Image.BILINEAR)
    return np.asarray(im, dtype=np.float32).ravel()


PRIVATE = re.compile(r'commented|phút trước|Trụng tâm|Trung tâm|Viettel|Thứ \w+, \d+ tháng|Control Center|Tập\s*trung', re.I)


def redact(lines):
    """the recordings show the recorder's own phone UI (notification centre, other apps' notifications with people's names and
    messages, control centre): keep only that such a screen was there, never its personal text"""
    if any(PRIVATE.search(l) for l in lines):
        game = [l for l in lines if re.search(r'Maze Out|MAZE|OUT!|Loading', l)]
        return game[:2] + ['[phone system UI / notification: personal text omitted]']
    return lines


def screen_kind(lines, d):
    s = ' '.join(lines).lower()
    table = [
        ('notification_prompt', r'muốn gửi|would like to send you notifications'),
        ('unlock', r'unlocked'), ('win_panel', r'perfect|rewards'), ('win_splash', r'well done'),
        ('fail_continue', r'continue\?|play on|keep playing'), ('fail_time', r'out of time|\+30|add time'),
        ('fail_panel', r'failed|try again'), ('quit', r'quit level|lose a life'), ('pause', r'paused|resume'),
        ('shop', r'\bshop\b|special offer|bundle'), ('leaderboard', r'leaderboard|weekly contest|reach level'),
        ('settings', r'settings|notifications|support'), ('profile', r'profile|username|general stats'),
        ('streak', r'streak'), ('home', r'\bplay\b|\bhome\b'), ('loading', r'loading'),
        ('tutorial', r'tap to|move!|tap the|clear|arrows'),
    ]
    for k, rx in table:
        if re.search(rx, s):
            return k
    if d is not None and d['dark'] > 0.6:
        return 'dark'
    return 'other'


def screens_for(V, rows, a, b, min_dur=0.45):
    """sub-segment rows[a..b] (non-play) by 2-fps signature changes; OCR one full-res frame per sub-segment"""
    t0, t1 = rows[a]['t'], rows[b]['t']
    ts = [x for x in np.arange(t0, t1 + 1e-6, 0.5)] or [t0]
    sigs = []
    for t in ts:
        p, tt = scan_jpg(V, t)
        sigs.append((tt, signature(p)))
    segs = []
    cur = [sigs[0][0], sigs[0][0], sigs[0][1]]
    for tt, sg in sigs[1:]:
        if np.abs(sg - cur[2]).mean() > 22:
            segs.append(cur)
            cur = [tt, tt, sg]
        else:
            cur[1] = tt
    segs.append(cur)
    out = []
    for s0, s1, _ in segs:
        tm = min(max((s0 + s1) / 2, t0), t1)
        p = grab(V, tm, sub='screens')
        o = ocr(p)
        row = rows[min(range(a, b + 1), key=lambda i: abs(rows[i]['t'] - tm))]
        k = screen_kind(o['lines'], row)
        seg = dict(t0=round(max(s0, t0), 2), t1=round(min(s1 + 0.5, t1), 2), t_ocr=round(tm, 2), kind=k,
                   text=redact([l for l in o['lines'] if l.strip()][:14]), frame=os.path.relpath(p, os.path.dirname(RES)))
        if seg['text'] and seg['text'][-1].startswith('[phone system UI'):
            seg['kind'] = 'phone_ui'
        if out and out[-1]['kind'] == seg['kind'] and out[-1]['text'] == seg['text']:
            out[-1]['t1'] = seg['t1']
            continue
        out.append(seg)
    return out


# ------------------------------------------------------------------------------------------------ boards
def episodes_in_run(rows, a, b):
    """split a play run into ink episodes: an episode ends when the ink stays below thr for > 0.3 s"""
    ink = np.array([rows[i]['ink'] for i in range(a, b + 1)], float)
    if len(ink) == 0 or ink.max() < 150:
        return []
    # 'cleared' must mean NO arrow left: the last few 2-cell arrows of a big board carry < 2 % of its peak ink (V2 L25 ended with
    # 3 short arrows = ~150 samples while the peak was 18000), so the threshold is near the empty-board noise floor (0-10)
    thr = max(25, 0.002 * ink.max())
    on = ink > thr
    eps = []
    i, n = 0, len(ink)
    while i < n:
        if not on[i]:
            i += 1
            continue
        j, last_on = i, i
        while j < n:
            if on[j]:
                last_on = j
            elif rows[a + j]['t'] - rows[a + last_on]['t'] > 0.3:
                break
            j += 1
        eps.append((a + i, a + last_on))
        i = j
    # the win logo (V1 'MAZE OUT!', V2 'Well Done!') pops within ~0.3-1 s of the last exit, while trails/particles still keep a
    # little ink on screen: split an episode where ink jumps from < 5 % of its peak by > max(1500, 10 % of peak) within 0.2 s
    split = []
    for s, e in eps:
        seg = ink[s - a:e - a + 1]
        pk = seg.max()
        cut = None
        # search BACKWARDS for the last near-empty valley (< 150 samples: trails and sparkles keep 60-100) followed by a jump > 1500 within 0.2 s: in V1 the logo
        # outweighs the board (14000 vs ~9000 samples), so 'after the peak' would miss it; the build-up ramp at the start is
        # excluded by requiring >= 0.5 s of board before the cut
        for k in range(len(seg) - 1, 0, -1):
            if seg[k - 1] < 150:
                k2 = k
                while k2 + 1 < len(seg) and rows[s + k2 + 1]['t'] - rows[s + k - 1]['t'] <= 0.2:
                    k2 += 1
                if seg[k2] - seg[k - 1] > 1500 and rows[s + k]['t'] - rows[s]['t'] >= 0.5:
                    cut = k
                    break
        if cut is not None and cut > 1:
            end = cut - 1
            while end > 0 and seg[end] < 150:      # drop the particle-only valley: the board ends with its last stroke ink
                end -= 1
            split += [(s, s + end), (s + cut, e)]
        else:
            split.append((s, e))
    eps = split
    out = []
    for s, e in eps:
        if rows[e]['t'] - rows[s]['t'] < 0.2:
            continue
        cleared = e < b and rows[b]['t'] - rows[e]['t'] > 0.25   # ink gone before the run ended
        out.append(dict(s=s, e=e, a=a, b=b, cleared=cleared, thr=thr))
    return out


def ep_stats(rows, ep):
    s, e = ep['s'], ep['e']
    t0 = rows[s]['t']
    early = [rows[i]['ink'] for i in range(s, e + 1) if rows[i]['t'] <= t0 + 0.8]
    ep['t0'], ep['t_end'] = t0, rows[e]['t']
    ep['dur'] = ep['t_end'] - t0
    ep['ink_first'] = rows[s]['ink']
    ep['ink_early'] = int(np.median(early))
    ep['ink_max'] = int(max(rows[i]['ink'] for i in range(s, e + 1)))
    ep['ink_end'] = int(np.median([rows[i]['ink'] for i in range(max(s, e - 3), e + 1)]))
    near = [i for i in range(max(ep['a'], s - 25), min(ep['b'], s + 25) + 1) if abs(rows[i]['t'] - t0) <= 0.8]
    ep['heart_fill'] = any(hearts(rows[i]) == 0 for i in near)
    ep['fresh'] = ep['heart_fill'] or ep['ink_first'] < 0.6 * ep['ink_early']
    ep['kind'] = btn_kind(rows[min(e, s + 10)]['btn'])
    return ep


def timer_changes(rows, s, e):
    """times at which the timer-digit signature changes (a tick) inside rows[s..e] (play frames only)"""
    out = []
    prev = None
    for i in range(s, e + 1):
        d = rows[i]
        if not is_play(d) or 'tmr' not in d:
            continue
        sig = np.array(d['tmr'], float)
        if prev is not None and np.abs(sig - prev).max() > 18:
            out.append(d['t'])
        prev = sig
    return out


def at(rows, t):
    ts = TCACHE.setdefault(id(rows), np.array([d['t'] for d in rows]))
    i = int(np.searchsorted(ts, t))
    i = min(max(i, 0), len(rows) - 1)
    if i > 0 and abs(ts[i - 1] - t) < abs(ts[i] - t):
        i -= 1
    return i


TCACHE = {}


def heart_drops(rows, s, e):
    """confirmed heart losses in rows[s..e]: the count falls and STAYS down for 1 s (an iOS notification banner hides all
    three hearts at once for ~1 s; that is not a loss unless it was the last heart) -> [(t, from, to)]"""
    ser = [(rows[i]['t'], hearts(rows[i])) for i in range(s, e + 1) if is_play(rows[i])]
    out, cur = [], None
    for k, (t, h) in enumerate(ser):
        if cur is None:
            if h > 0:
                cur = h
            continue
        if h == cur:
            continue
        win = [v for (tt, v) in ser[k:] if tt <= t + 1.0]
        if len(win) < 5:
            continue
        if h < cur and sum(1 for v in win if v == h) >= 0.85 * len(win) and (h > 0 or cur == 1):
            out.append((t, cur, h))
            cur = h
        elif h > cur and all(v >= h for v in win):
            cur = h
    return out


def tap_outcomes(rows, taps, s, e):
    """approximate effect of each tap: bump (a confirmed heart loss within 1.0 s), exit (ink falls within 0.7 s), none"""
    heart_drops_ = [t for (t, a, b) in heart_drops(rows, s, e)]
    for tp in taps:
        tp['outcome'] = 'none'
    for hd in heart_drops_:        # the loss belongs to the LAST board tap before it
        cand = [tp for tp in taps if 0 <= hd - tp['t'] <= 1.0 and tp['y'] <= 1130 and tp['outcome'] == 'none']
        if cand:
            tp = cand[-1]
            tp['outcome'] = 'bump'
            tp['t_effect'] = round(hd, 3)
    for tp in taps:
        if tp['outcome'] == 'none' and tp['y'] > 1130:
            tp['outcome'] = 'booster_bar'
        if tp['outcome'] == 'none':
            i0 = at(rows, tp['t'] - 0.04)
            i1 = at(rows, tp['t'] + 0.7)
            d0 = rows[i0]['ink']
            d1 = min(rows[k]['ink'] for k in range(i0, i1 + 1))
            if d0 - d1 > max(40, 0.01 * d0):
                tp['outcome'] = 'exit'
                tp['ink_drop'] = int(d0 - d1)
    return heart_drops_


def build(V):
    rows = load_scan(V)
    TCACHE.clear()
    rr = smooth_runs(rows, lambda d: 'P' if is_play(d) else 'N', 0.3)
    items = []
    for k, a, b in rr:
        if k == 'N':
            for sc in screens_for(V, rows, a, b):
                items.append(dict(type='screen', **sc))
        else:
            for ep in episodes_in_run(rows, a, b):
                items.append(dict(type='ep', **ep_stats(rows, ep)))
    save_ocr_cache()
    # logo pops: a short episode right after a cleared episode, ending the run (MAZE OUT! / Well Done! on the board)
    for j, it in enumerate(items):
        if it['type'] != 'ep':
            continue
        prev = items[j - 1] if j else None
        nxt = items[j + 1] if j + 1 < len(items) else None
        it['logo'] = bool(prev and prev['type'] == 'ep' and prev['cleared'] and it['dur'] < 4.0
                          and (nxt is None or nxt['type'] == 'screen') and rows[it['b']]['t'] - rows[it['e']]['t'] < 0.8)
    json.dump(dict(items=[{k: v for k, v in it.items()} for it in items]),
              open(os.path.join(WORK, V + '.items.json'), 'w'), indent=1, default=float)
    return rows, items


# ------------------------------------------------------------------------------------------------ levels
LABEL_CROP = (120, 200, 352, 80)     # V1 'Level N' / 'Levels 1-4' tag under the HUD (full-res px)
TIMER_CROP = (180, 100, 110, 64)     # HUD timer digits
HEART_SLOTS = 3


def parse_level_label(lines):
    s = ' '.join(lines)
    m = re.search(r'Level[s]?\s*([0-9SOIlLBZG]{1,2})\s*[-–]\s*([0-9SOIlLBZG]{1,2})', s)
    if m and num(m.group(1)) is not None and num(m.group(2)) is not None:
        return 'Levels %d-%d' % (num(m.group(1)), num(m.group(2))), (num(m.group(1)), num(m.group(2)))
    m = re.search(r'Level\s*([0-9SOIlLBZG]{1,3})', s.replace('Levèl', 'Level'))
    if m and num(m.group(1)) is not None:
        return 'Level %d' % num(m.group(1)), (num(m.group(1)), num(m.group(1)))
    return None, None


def home_level(sc):
    """'LEVEL | 12' on the home screen -> 12 (the level the Play button starts)"""
    L = sc['text']
    for i, l in enumerate(L):
        if l.strip().upper() == 'LEVEL' and i + 1 < len(L) and num(L[i + 1].strip()) is not None:
            return num(L[i + 1].strip())
        m = re.match(r'^\s*LEVEL\s+(\S+)\s*$', l)
        if m and num(m.group(1)) is not None:
            return num(m.group(1))
    # 'LEVEL' missing (animated coin counter hides it): a lone number line right before 'Play'
    for i, l in enumerate(L):
        if l.strip() == 'Play' and i and num(L[i - 1].strip()) is not None and num(L[i - 1].strip()) < 1000:
            return num(L[i - 1].strip())
    return None


def read_timer(path):
    o = ocr(path, TIMER_CROP, 3)
    for l in o['lines']:
        m = re.search(r'(\d)\s*[:.]\s*(\d\d)', l.translate(DIGIT))
        if m:
            return '%s:%s' % (m.group(1), m.group(2))
    return None


def timer_track(V, n, t0, t1, step=1.0):
    """HUD timer read (OCR) every `step` s over [t0, t1] -> ([(t, secs)], events). Events: 'jump' = the timer fell more than the
    video time elapsed + 2 s (a video CUT, or a time penalty), 'frozen' = unchanged >= 3 s while playing (pause popup / freeze
    booster), 'rise' = it went UP (+30 s continue / time booster)."""
    import shutil
    d = os.path.join(WORK, 'timer', '%s-L%03d' % (V, n))
    if os.path.isdir(d):
        shutil.rmtree(d)
    os.makedirs(d)
    ts = list(np.arange(t0, t1 + 1e-6, step))
    subprocess.run([VGRAB, V, d, '--quiet', '--jpg', '--crop'] + [str(c) for c in TIMER_CROP] + ['%.3f:f%04d' % (t, i) for i, t in enumerate(ts)],
                   check=True, capture_output=True)
    files = [os.path.join(d, 'f%04d.jpg' % i) for i in range(len(ts))]
    r = subprocess.run([VOCR, '--scale', '3'] + files, capture_output=True, text=True)
    vals = {}
    for line in r.stdout.splitlines():
        try:
            o = json.loads(line)
        except ValueError:
            continue
        m = re.search(r'(\d)\s*[:.]\s*(\d\d)', ' '.join(o.get('lines', [])).translate(DIGIT))
        if m:
            vals[o['file']] = int(m.group(1)) * 60 + int(m.group(2))
    track = [(round(t, 2), vals[f]) for t, f in zip(ts, files) if f in vals]
    shutil.rmtree(d)
    ev = []
    for (ta, va), (tb, vb) in zip(track, track[1:]):
        if va - vb > (tb - ta) + 2:
            ev.append(dict(kind='jump', t=tb, frm=va, to=vb, video_dt=round(tb - ta, 2)))
        if vb > va:
            ev.append(dict(kind='rise', t=tb, frm=va, to=vb))
    k = 0
    while k < len(track):
        j = k
        while j + 1 < len(track) and track[j + 1][1] == track[k][1]:
            j += 1
        if track[j][0] - track[k][0] >= 3 and track[k][1] < 180:
            ev.append(dict(kind='frozen', t=track[k][0], t_end=track[j][0], at=track[k][1]))
        k = j + 1
    return track, ev


def assemble(V, rows, items):
    attempts, cur, pending, post = [], None, [], None
    for it in items:
        if it['type'] == 'ep' and not it['logo']:
            if cur is None:
                cur = dict(before=pending, eps=[], screens=[], after=[], logo=None, result=None)
                pending, post = [], None
            cur['eps'].append(it)
        elif it['type'] == 'ep':          # logo pop = the level is won
            if cur is not None:
                cur['logo'] = it
                cur['result'] = 'win'
                attempts.append(cur)
                post, cur = cur, None
        else:
            if cur is not None:
                if it['kind'] == 'home':  # left the level without a win
                    cur['result'] = cur['result'] or 'left'
                    attempts.append(cur)
                    cur, post = None, None
                    pending = [it]
                else:
                    cur['screens'].append(it)
            elif post is not None and it['kind'] != 'home':
                post['after'].append(it)
            else:
                post = None
                pending.append(it)
    if cur is not None:
        cur['result'] = cur['result'] or 'video_end'
        attempts.append(cur)
    return attempts


def level_record(V, rows, att, eps, n, label, stage=None, t_next=None):
    """one level record for the episodes eps (one board, or one stage of a multi-stage session)"""
    s, e = eps[0]['s'], eps[-1]['e']
    # the last arrow's tap can land after the ink fell below the threshold (it changes colour on the tap): extend 0.8 s
    t_lim = rows[e]['t'] + 0.8
    if t_next is not None:
        t_lim = min(t_lim, t_next - 0.05)
    e2 = max(e, at(rows, t_lim))
    taps = [tp for tp in tap_tracks(rows, s, e2) if 170 <= tp['y'] <= 1262]
    t_tap0 = min((tp['t'] for tp in taps if tp['y'] <= 1130), default=None)
    hand_level = t_tap0 is not None and hand_in_band(V, t_tap0 - 0.2) > 0
    for tp in taps:
        hy = hand_near(V, tp['t'], tp['x'], tp['y']) if hand_level else 0
        if hy:
            tp['near_hand'] = hy
    drops = tap_outcomes(rows, taps, s, e2)
    ep0 = eps[0]
    ink = np.array([rows[i]['ink'] for i in range(ep0['s'], ep0['e'] + 1)], float)
    ts = np.array([rows[i]['t'] for i in range(ep0['s'], ep0['e'] + 1)])
    btaps = [tp for tp in taps if tp['y'] <= 1130]
    t_tap = btaps[0]['t'] if btaps else None
    lim = int(np.searchsorted(ts, t_tap)) if t_tap is not None else len(ts)
    pre = ink[:max(1, lim)]
    k_built = int(np.argmax(pre >= 0.97 * pre.max()))
    t_built = float(ts[k_built])
    # the cleanest start frame: the LATEST frame before the first tap (>= 0.1 s before it) whose stroke ink is still >= 98.5 % of the
    # pre-tap peak. Normally that is ~0.12 s before the first tap; on tutorial levels the pointing hand hides ink, so this lands
    # on the last frame before the hand appears (board built, hand not yet drawn).
    peak = pre.max()
    if t_tap is not None:
        okk = (ts[:len(pre)] <= t_tap - 0.1) & (pre >= 0.985 * peak) & (ts[:len(pre)] >= t_built)
        if okk.any():
            t_board = float(ts[:len(pre)][okk].max())
        else:
            t_board = max(t_built + 0.05, t_tap - 0.12) if t_tap - t_built > 0.2 else t_built
    else:
        t_board = min(t_built + 0.4, float(ts[-1]))
    popup_before = any(b_['kind'] in ('unlock', 'dark') for b_ in att.get('before', [])[-2:]) and stage in (None, 1)
    if not ep0['fresh'] and popup_before and t_tap is not None and t_tap - 0.12 > t_board:
        # board revealed from under an unlock popup: the first frames still carry the popup's fade; take the frame just
        # before the first tap (V2 L11: ink IoU 0.915 at the popup's end vs 0.946 just before the tap, same 14 arrows)
        t_board = t_tap - 0.12
    t_board = round(float(t_board), 3)
    nm = 'L%03d-start' % n
    if V == 'V1' and label and label.startswith('Levels') and stage:
        nm = 'L%03d-start' % n
    start_png = grab(V, t_board, name=nm, sub='')
    start_png2 = os.path.join(FR, V, nm + '.png')
    tmr = read_timer(start_png2)
    # captions (tutorial text such as 'Tap to move!'): OCR the frame just before the first tap; keep confident, wordy text in
    # the board band only (board strokes OCR as junk like '.I.' or 'Su 16')
    capf = grab(V, (t_tap - 0.15) if t_tap is not None else t_board, sub='captions')
    full = ocr(capf)
    caps = []
    for w in full['words']:
        x_, y_, w_, h_ = w['box']
        txt = w['s'].strip()
        letters = sum(ch.isalpha() for ch in txt)
        if 180 <= y_ <= 1125 and w['conf'] >= 0.6 and letters >= 4 and letters >= 0.7 * len(txt.replace(' ', '')) and 'Level' not in txt:
            caps.append(txt)
    ticks = timer_changes(rows, s, e)
    hs = hearts(rows[at(rows, t_board)])
    he = hearts(rows[at(rows, rows[e]['t'] - 0.1)])
    kind = btn_kind(rows[at(rows, t_board)]['btn'])
    rec = dict(video=V, level=n, label=label, stage=stage, tag={'normal': None, 'hard': 'Hard', 'superhard': 'Super Hard'}[kind],
               t_first=round(ep0['t0'], 3), revealed_after_popup=bool(not ep0['fresh'] and popup_before), t_built=round(t_built, 3),
               t_board=t_board, t_first_tap=t_tap, t_clear=round(rows[e]['t'], 3),
               t_win=round(att['logo']['t0'], 3) if att.get('logo') and (stage is None or stage == att.get('n_stages')) else None,
               t_first_tick=round(ticks[0], 3) if ticks else None,
               timer_start=tmr, hearts_start=hs, hearts_end=he,
               n_taps=len(taps), n_booster_bar_taps=sum(1 for t in taps if t['outcome'] == 'booster_bar'), n_exit=sum(1 for t in taps if t['outcome'] == 'exit'),
               n_bump=sum(1 for t in taps if t['outcome'] == 'bump'), heart_drops=[round(x, 3) for x in drops],
               phases=[dict(t0=round(x['t0'], 3), t_end=round(x['t_end'], 3), ink_max=x['ink_max'], fresh=x['fresh']) for x in eps],
               start_frame=os.path.relpath(start_png2, os.path.dirname(RES)),
               board_bbox_px=None, captions=caps[:8],
               taps=[dict(t=t['t'], x=t['x'], y=t['y'], outcome=t['outcome'], **({'t_effect': t['t_effect']} if 't_effect' in t else {}),
                          **({'drag': True} if t['drag'] else {}), **({'near_hand': t['near_hand']} if t.get('near_hand') else {}),
                          **({'weak': True} if t.get('weak') else {}))
                     for t in taps])
    bb = rows[at(rows, t_board)]['ibox']
    rec['board_bbox_px'] = bb
    # HUD timer when the board is cleared (the last arrow starts leaving): time left
    clr = grab(V, rows[e]['t'], name='L%03d-clear' % n, sub='clear')
    rec['timer_at_clear'] = read_timer(clr)
    tt, tev = timer_track(V, n, t_board, rows[e]['t'])
    rec['timer_track'] = [[a, '%d:%02d' % (b // 60, b % 60)] for a, b in tt]
    rec['timer_events'] = tev
    rec['tutorial_hand'] = bool(hand_level)
    rec['t_board_rule'] = 'last frame >= 98.5% of pre-tap peak ink, >= 0.1 s before the first board tap'
    return rec


def hand_near(V, t, x, y, r=110):
    """yellow tutorial-hand pixels within r px of (x, y) in the 2-fps scan frame nearest t (its grey drop shadow looks
    like a touch disc) -> pixel count (0 = no hand)"""
    p, tt = scan_jpg(V, t)
    if abs(tt - t) > 0.3:
        return 0
    im = np.asarray(Image.open(p).convert('RGB'), dtype=np.int16)
    sx = im.shape[1] / 592.0
    x0, x1 = int(max(0, (x - r) * sx)), int(min(im.shape[1], (x + r) * sx))
    y0, y1 = int(max(0, (y - r) * sx)), int(min(im.shape[0], (y + r) * sx))
    sub = im[y0:y1, x0:x1]
    yel = (sub[..., 0] > 220) & (sub[..., 1] > 150) & (sub[..., 2] < 90)
    n = int(yel.sum())
    return n if n > 40 else 0


def hand_in_band(V, t):
    """yellow tutorial-hand pixels anywhere in the board band (y 180-1120) of the 2-fps scan frame nearest t"""
    p, tt = scan_jpg(V, t)
    if abs(tt - t) > 0.3:
        return 0
    im = np.asarray(Image.open(p).convert('RGB'), dtype=np.int16)
    sx = im.shape[1] / 592.0
    sub = im[int(180 * sx):int(1120 * sx)]
    n = int(((sub[..., 0] > 220) & (sub[..., 1] > 150) & (sub[..., 2] < 90)).sum())
    return n if n > 150 else 0


def build_levels(V, rows, items):
    atts = assemble(V, rows, items)
    levels = []
    prev_n = 0
    starts = [a['eps'][0]['t0'] for a in atts]
    for ai, att in enumerate(atts):
        t_next_att = starts[ai + 1] if ai + 1 < len(atts) else None
        # candidate numbers: home screen before, the tag on the board (V1), the win panel after
        cand = []
        for sc in att['before'][::-1]:
            if sc['kind'] == 'home' and home_level(sc):
                cand.append(('home', home_level(sc)))
                break
        ep0 = att['eps'][0]
        lab_png = grab(V, min(ep0['t_end'], ep0['t0'] + 1.0), sub='labels')
        lab, rng = parse_level_label(ocr(lab_png, LABEL_CROP, 2)['lines'])
        if lab:
            cand.append(('tag', rng[0]))
        for sc in att['after']:
            if sc['kind'] == 'win_panel':
                l2, r2 = parse_level_label(sc['text'])
                if r2:
                    cand.append(('panel', r2[0]))
                    if lab is None:
                        lab, rng = l2, r2
                    break
        nums = [c[1] for c in cand]
        n = None
        for c in nums:
            if c == prev_n + 1:
                n = c
                break
        if n is None:
            n = nums[0] if nums else prev_n + 1
        multi = lab is not None and lab.startswith('Levels')
        if multi:
            lo, hi = rng
            att['n_stages'] = len(att['eps'])
            for k, ep in enumerate(att['eps']):
                tn = att['eps'][k + 1]['t0'] if k + 1 < len(att['eps']) else (att['logo']['t0'] if att.get('logo') else t_next_att)
                levels.append(level_record(V, rows, att, [ep], lo + k, lab, stage=k + 1, t_next=tn))
            prev_n = lo + len(att['eps']) - 1
        else:
            lab = 'Level %d' % n
            tn = att['logo']['t0'] if att.get('logo') else t_next_att
            rec = level_record(V, rows, att, att['eps'], n, lab, t_next=tn)
            levels.append(rec)
            prev_n = n
        last = levels[-1]
        first = levels[-len(att['eps'])] if multi else last
        last['result'] = att['result']
        for r in (levels[-len(att['eps']):] if multi else [last]):
            r['number_sources'] = cand
            r.setdefault('before', [])
        first['before'] = [dict(t0=x['t0'], t1=x['t1'], kind=x['kind'], text=x['text']) for x in att['before']]
        last['popups'] = [dict(t0=x['t0'], t1=x['t1'], kind=x['kind'], text=x['text']) for x in att['screens']]
        last['after'] = [dict(t0=x['t0'], t1=x['t1'], kind=x['kind'], text=x['text']) for x in att['after']]
        for sc in att['after']:
            if sc['kind'] == 'win_panel':
                last['win_panel_text'] = sc['text']
                txt_ = sc['text']
                ri = [k for k, l in enumerate(txt_) if l.strip().lower().startswith('rewards')]
                m = [l for l in (txt_[ri[0] + 1:] if ri else txt_) if re.fullmatch(r'\d{2,3}', l.strip())]
                last['reward'] = int(m[0]) if m else None
                tm = [l for l in sc['text'] if re.match(r'^\d:\d\d', l.strip())]
                last['timer_left_at_win'] = tm[0].strip()[:4] if tm else None
                break
        if multi:
            for r in levels[-len(att['eps']):]:
                r['result'] = 'stage_clear' if r['stage'] < len(att['eps']) else att['result']
    save_ocr_cache()
    return levels


def build_all(V):
    rows, items = build(V)
    levels = build_levels(V, rows, items)
    screens = [dict(t0=it['t0'], t1=it['t1'], kind=it['kind'], text=it['text'], frame=it['frame'])
               for it in items if it['type'] == 'screen']
    out = dict(video=V, levels=levels, screens=screens)
    json.dump(out, open(os.path.join(WORK, V + '.index.json'), 'w'), indent=1, default=float)
    return out


# ------------------------------------------------------------------------------------------------ write
FINDINGS = r'''## Findings the tools established (evidence in the tables above and in `video-frames/work/extract/*-replay.json`)

- **Scale.** Both videos are a 393-pt-wide phone: V2 L21 reads pitch 28.03 pt, the phone's identical L35 28.09 pt (-0.2 %). The video
  board sits 1.7 pt higher (origin y 198.8 vs 200.6 pt): a small layout difference between the builds.
- **Timer.** Every level of both videos shows 3:00 on its clean start frame, Hard and Super Hard included (the phone's v552 L34 Hard
  used 3:30); the clock starts at the first tap (the timer track shows the first tick ~1 s after it). Each "Levels 1-4" stage restarts
  at 3:00 (stages cleared at 2:59, 2:58, 2:56, 2:56). Time left at clear per level: column "left at clear".
- **Rewards on the win panel:** 20 normal, 60 Hard (V1 L19; V2 L19, L25, L35), 100 Super Hard (V2 L29), 80 for "Levels 1-4".
  Tags: V1 L19 Hard; V2 L19 Hard, L25 Hard, L29 Super Hard (cleared with 0:20 left), L35 Hard; V2's last home screen offers L39
  Super Hard.
- **Unlock popups (the only obstacle tutorials; no hand):** V1 "Linked Arrows! Unlocked! LINKED ARROWS move together!" before L7,
  "Curtain! Unlocked! Clear required amount of arrows to open the CURTAIN!" before L11. V2 (other build) "Box! Unlocked! Clear required
  amount of arrows to break the BOX!" before L11, "Pipe! Unlocked! Pass arrows through the PIPE to break it!" before L21, "Elevator!
  Unlocked! Clear all arrows on the ELEVATOR to activate it!" before L31. The board is already built (dimmed) under the popup.
- **Hand tutorial:** only V1 L1 stage 1: "Tap to move!" and a pointing hand over the middle (up) arrow of three vertical arrows; the
  hand appears ~0.1 s after the board is built (clean start frame at 0.72 s is hand-free). Grey discs next to the hand from 1.64 s are
  flagged `near_hand` (the hand's drop shadow looks like a touch); the arrow leaves on the touch at 3.52 s.
- **Counters (replay-verified, every level):** a curtain (V1) or box (V2) breaks on the exit that makes the number of arrows removed
  since the level start equal to its counter; every member of a Linked bundle counts. A pipe breaks after `counter` passes (V2 L23 both
  pipes 3, L38 3). A curtain/box blocks rays until it breaks.
- **Elevator (V2 L31+):** the platform's arrows are normal arrows; when the last one leaves, a hidden second layer is live AT ONCE (V2 L32:
  a tap 0.6 s after that exit bumped into it, 0.3 s before the platform visibly dropped) and is drawn ~0.4-0.9 s later where the platform
  was. Hidden layers read: L31 7, L32 11, L33 9 + 8, L35 39 arrows.
- **Mistakes:** only V2 L32 has any: two taps on blocked arrows, each costing a heart (3 -> 2 -> 1), both BLOCKED in our model. In V2 a
  bumped arrow is redrawn BLACK until it leaves. V1 has no heart loss at all.
- **Edits in the footage:** V1 L17 is CUT at 6:00.7 (timer 2:41 -> 2:28 across one frame) and the board is re-fitted smaller after the
  cut (pitch 28.2 -> 26.7 px); the replay re-registers the grid there. V2 shows iOS notification banners (Vietnamese) over the HUD and
  an AssistiveTouch-like grey circle top right; V2 opens with a meta tour (shop, leaderboard "Reach level 50 to compete in Weekly
  Contest!", settings, profile/username) before L11 and shows the iOS rating prompt on the home screen after L34.
- **V1 vs V2 (L11-L20, the overlap):** all 10 boards are IDENTICAL (every arrow, same grid); only the obstacle skin differs: V1's purple
  "Curtain" crates are V2's cyan "Box" blocks, same cells, same counters (L11 8/13, L12 8/16/23, L13 4/28, L15 26/41, L19 13/20/25).
- **Video build vs the phone (v552, research/levels L32-L61):** V1/V2 L12 = phone L51, V1/V2 L14 = phone L52, V2 L21 = phone L35,
  V2 L26 = phone L45 (identical arrows; the phone also shows boxes on L51 and the pipe on L35; phone L45 runs 2:30, the video's L26
  3:00). Nothing else matches (best other score 0.09): V2 L32-L38 are NOT the phone's L32-L38 (V2 L32 vs phone L32: 1 identical arrow
  of 53/40, 20x20 tapes vs 17x21 elevator). So v552 REORDERED levels (video L21 -> 35, L26 -> 45, L12 -> 51, L14 -> 52) and inserted
  others; L1-L31 content from the videos is real game content, but its v552 position is not the video's number.
'''

def fmt_t(t):
    return '-' if t is None else '%d:%05.2f' % (int(t // 60), t - 60 * int(t // 60))


def write():
    import datetime
    out = dict(
        generated=datetime.date.today().isoformat(),
        tool='research/video-tools/vindex.py (vscan features -> segments -> OCR -> levels); frames via vgrab, text via vocr',
        videos={V: dict(path=c['path'], duration_s=c['dur'], fps=c['fps'], size_px=[592, 1280], pt_per_px=round(PT, 5),
                        scan='every frame' if c['scan_fps'] == 0 else '%d fps' % c['scan_fps'],
                        scan_file='research/video-frames/work/%s.scan.jsonl (gitignored)' % V)
                for V, c in VIDEOS.items()},
        conventions=dict(
            coordinates='full-res pixels of the 592x1280 frame, top-left origin; pt = px * 393/592 (verified: V2 L21 pitch 28.03 pt '
                        'vs the phone L35 pitch 28.09 pt for the same board)',
            times='seconds of video presentation time (vgrab V t grabs that exact frame)',
            t_first='first frame of the level with board ink (board building, or revealed from under an unlock popup)',
            t_built='ink reaches 97 % of its pre-tap peak', t_board='cleanest start frame: the LAST frame >= 0.1 s before the first board '
            'tap whose ink is >= 98.5 % of the pre-tap peak (tutorial hand not drawn yet); grabbed full-res as research/video-frames/V?/L0NN-start.png',
            t_first_tap='first touch disc on the board (the iOS screen-recording touch indicator; touch-DOWN; the game acts on release)',
            t_clear='last frame with arrow ink (the last arrow starts leaving)', t_win='the MAZE OUT! (V1) / Well Done! (V2) logo pops',
            taps='touch-disc tracks: t, x, y (px), outcome = exit (ink fell within 0.7 s) | bump (a confirmed heart loss within 1 s, '
                 'given to the last board tap before it) | none | booster_bar (y > 1130); weak = seen in one frame or among shatter '
                 'debris; near_hand = next to the tutorial pointer. Outcomes here are APPROXIMATE; vextract.py replay decides them per arrow.',
            heart_drops='hearts count falls and stays down >= 1 s (an iOS notification banner hides all 3 hearts for ~1 s: ignored)',
            screens='non-play stretches split by 2-fps frame signature; one full-res OCR per sub-segment; kind from the text'),
        levels=[], screens={})
    for V in ('V1', 'V2'):
        d = json.load(open(os.path.join(WORK, V + '.index.json')))
        out['levels'] += d['levels']
        out['screens'][V] = d['screens']
    json.dump(out, open(os.path.join(RES, 'video-index.json'), 'w'), indent=1, default=float)
    # ---------------- markdown
    L = out['levels']
    md = ['# Video index — the owner\'s two gameplay videos', '',
          'Machine-readable: `research/video-index.json` (every tap, screen and popup with times). Built by `research/video-tools/vindex.py`',
          '(`vindex.py build V1 V2 && vindex.py write`). Frames: `research/video-frames/` (gitignored; `vgrab V1|V2 OUTDIR T` re-grabs any exact frame).',
          '', '| video | file | length | fps | size |', '|---|---|---|---|---|']
    for V, c in VIDEOS.items():
        md.append('| %s | `%s` | %.1f s | %.2f | 592x1280 px (393x852 pt; pt = px x 0.6639) |' % (V, c['path'], c['dur'], c['fps']))
    md += ['', 'Times are video seconds (m:ss.ss). t_board = the clean start frame (`research/video-frames/V?/L0NN-start.png`).',
           'Taps = touch-indicator discs on the board; exit/bump counts are the index\'s approximation (the replay check in',
           '`vextract.py replay` decides per arrow). "left at clear" = HUD timer (OCR) on the frame the board is cleared.', '']
    for V in ('V1', 'V2'):
        md += ['## %s — levels' % V, '',
               '| level | label | tag | first | board | 1st tap | clear | win | result | taps | exit | bump | timer | left at clear | reward | before (popups) |',
               '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
        for x in [y for y in L if y['video'] == V]:
            pre = [b for b in x.get('before', []) if b['kind'] in ('unlock', 'tutorial', 'leaderboard', 'streak', 'other', 'dark', 'loading', 'quit', 'pause')]
            pre_s = '; '.join('%s "%s"' % (b['kind'], ' / '.join(b['text'][:4])[:70]) for b in pre if b['text'])[:160]
            pops = '; '.join('%s@%s' % (p_['kind'], fmt_t(p_['t0'])) for p_ in x.get('popups', []))
            if pops:
                pre_s = (pre_s + ' | in-level: ' + pops)[:200]
            md.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %d | %d | %d | %s | %s | %s | %s |' % (
                x['level'], (x['label'] or '') + (' (stage %d)' % x['stage'] if x.get('stage') else ''), x['tag'] or '',
                fmt_t(x['t_first']), fmt_t(x['t_board']), fmt_t(x['t_first_tap']), fmt_t(x['t_clear']), fmt_t(x['t_win']),
                x.get('result'), x['n_taps'], x['n_exit'], x['n_bump'], x.get('timer_start') or '', x.get('timer_at_clear') or x.get('timer_left_at_win') or '',
                x.get('reward') or '', pre_s.replace('|', '/')))
        md.append('')
        caps = [(x['level'], x['captions']) for x in L if x['video'] == V and x['captions']]
        if caps:
            md.append('Captions on start frames (OCR): ' + '; '.join('L%d: %s' % (n_, ' / '.join(c)) for n_, c in caps))
            md.append('')
        bumps = [(x['level'], t['t'], t.get('t_effect')) for x in L if x['video'] == V for t in x['taps'] if t['outcome'] == 'bump']
        md.append('Mistakes (confirmed heart losses): ' + (', '.join('L%d tap %s -> heart %s' % (a, fmt_t(b), fmt_t(c)) for a, b, c in bumps) or 'none'))
        md.append('')
    for V in ('V1', 'V2'):
        md += ['## %s — screens and popups (non-play)' % V, '', '| from | to | kind | text (OCR, first lines) |', '|---|---|---|---|']
        for sc in out['screens'][V]:
            md.append('| %s | %s | %s | %s |' % (fmt_t(sc['t0']), fmt_t(sc['t1']), sc['kind'], ' / '.join(sc['text'][:6]).replace('|', '/')[:150]))
        md.append('')
    # ---------------- extraction + replay summary and board matches (from vextract/vbatch/vmatch runs, when present)
    bs = os.path.join(WORK, 'extract', 'batch-summary.json')
    if os.path.exists(bs):
        B = json.load(open(bs))
        md += ['## Board extraction check (vextract level + replay, every level)', '',
               'Start frame -> level JSON (`research/video-frames/work/extract/V?-L0NN.json`, overlay `...-overlay.png`). IoU = ink IoU of our '
               're-render vs the frame\'s stroke mask (raw / with 1-px tolerance). Replay: every exit and bump of the video checked against '
               'the model (consistent = exit on a FREE arrow or bump on a BLOCKED one, incl. exits whose touch was not detected); '
               'inconsistent = the model contradicts the video. hidden = elevator second-layer arrows read later in the level.', '',
               '| video | level | arrows | hidden | grid | pitch pt | IoU | IoU tol1 | anomalies | obstacles | taps | consistent | inconsistent | miss | left |',
               '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
        for r in B:
            if 'error' in r:
                md.append('| %s | %s | ERROR %s |' % (r['video'], r['level'], r['error'][:80]))
                continue
            md.append('| %s | %d | %d | %d | %dx%d | %.2f | %.3f | %.3f | %d | %s | %d | %d | %d | %d | %d |' % (
                r['video'], r['level'], r['arrows'], r['hidden'], r['grid'][0], r['grid'][1], r['pitch_pt'], r['iou'], r['iou_tol1'],
                r['anomalies'], ', '.join(r['obstacles']), r['taps'], r['consistent'], r['inconsistent'], r['miss'], r['left_at_end']))
        md.append('')
    mf = os.path.join(WORK, 'extract', 'matches.json')
    if os.path.exists(mf):
        M = json.load(open(mf))
        md += ['## Same boards (vmatch: identical arrows / max count, best integer shift)', '',
               '| a | b | score | identical | arrows |', '|---|---|---|---|---|']
        for r in M['pairs']:
            md.append('| %s | %s | %.3f | %d | %s |' % (r['a'], r['b'], r['score'], r['identical'], r['arrows']))
        md.append('')
    md += [FINDINGS]
    open(os.path.join(RES, 'video-index.md'), 'w').write('\n'.join(md) + '\n')
    print('wrote video-index.json (%d levels) + video-index.md' % len(L))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'scan':
        V = sys.argv[2]
        cfg = VIDEOS[V]
        with open(os.path.join(WORK, V + '.scan.jsonl'), 'w') as f:
            subprocess.run([VSCAN, V, '0', str(cfg['dur'] + 1), str(cfg['scan_fps'])], stdout=f, check=True)
    elif cmd == 'write':
        write()
    elif cmd == 'build':
        for V in sys.argv[2:] or ['V1', 'V2']:
            o = build_all(V)
            for L in o['levels']:
                print(V, L['level'], L['label'], L['stage'], L['tag'], 'first %.2f board %.2f tap %s clear %.2f win %s' % (
                    L['t_first'], L['t_board'], L['t_first_tap'], L['t_clear'], L['t_win']), 'timer', L['timer_start'],
                    'taps', L['n_taps'], 'exit', L['n_exit'], 'bump', L['n_bump'], L['result'], L['number_sources'])
