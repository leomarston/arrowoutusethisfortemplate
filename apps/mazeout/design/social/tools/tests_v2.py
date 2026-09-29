"""tests_v2.py — the v2-only property checks (social-intl §6.3 items 1, 3, 4, 5), run by `tests.py v2` after the shared ones.
The Swift port mirrors them in SocialPropertyTests (B2). Each check receives the World tests.py built (v2 applied)."""
import os, sys, unicodedata, math
from socialsim import core as K, population as Pp, names as Nm, data as D, v2 as V2

HERE = os.path.dirname(os.path.abspath(__file__))


def members_by_iso(W, isos, t_max):
    """iso -> [(c, j)] of every member (brute force over the whole world, the definition the unit queries must equal)."""
    out = {iso: [] for iso in isos}
    for c in W.cohorts:
        if c.n == 0 or c.join0 - c.span > t_max:
            continue
        for j in range(c.n):
            iso = W.iso_of(c, j)
            if iso in out:
                out[iso].append((c, j))
    return out


def brute_members(W, mem, t):
    """(P, gid, c, j) of the given members joined by t."""
    out = []
    for c, j in mem:
        P = W.progress(c, j, t)
        if P is not None:
            out.append((P, W.gid(c, j), c, j))
    return out


def graphemes(s):
    """Grapheme count as the username rule sees it (Swift Character count): combining marks join their base."""
    return sum(1 for ch in s if not unicodedata.category(ch).startswith('M'))


def username_ok(s):
    """The player's own username rule (Names.swift validateUsername + social-intl P2-4 for Han/Hangul/kana)."""
    cjk = any(unicodedata.name(ch, '').startswith(('CJK UNIFIED', 'HANGUL', 'HIRAGANA', 'KATAKANA')) for ch in s)
    n = graphemes(s)
    if not ((2 if cjk else 3) <= n <= 16):
        return False
    for ch in s:
        cat = unicodedata.category(ch)
        if not (ch == '_' or cat.startswith('L') or cat.startswith('M') or cat == 'Nd' or ch == 'ー'):
            return False
    return not s.lower().startswith('player_')


def run(W, T_NOW, check, rng):
    # 15. country queries over (cohort, block) units = brute force: 10 countries x 3 times
    times = [T_NOW - 50 * 86400, T_NOW - 9 * 86400 - 3 * 3600, T_NOW]
    bad = []
    isos = ('US', 'TR', 'SK', 'SI', 'JP', 'KR', 'BE', 'CH', 'BR', 'IS')
    mem = members_by_iso(W, isos, T_NOW)
    for iso in isos:
        for t in times:
            allp = brute_members(W, mem[iso], t)
            allp.sort(key=lambda x: (-x[0], x[1]))
            for x in (1, 2, 11, 40, 62, 300):
                if sum(1 for P, g, c, j in allp if 1 + math.floor(P) >= x) != W.count_ge(x, t, iso):
                    bad.append(('count', iso, t, x))
            if [g for (_, g, _, _) in W.top(t, 40, iso)] != [g for (_, g, _, _) in allp[:40]]:
                bad.append(('top', iso, t))
            for x in (5, 30, 62):
                ab, be = W.neighbours(x, t, 6, 6, iso)
                want_a = sorted([(P, g) for P, g, c, j in allp if 1 + math.floor(P) >= x + 1])[:6]
                want_b = sorted([(P, g) for P, g, c, j in allp if 1 + math.floor(P) <= x], key=lambda y: (-y[0], -y[1]))[:6]
                if [g for (_, g, _, _) in ab] != [g for _, g in want_a] or [g for (_, g, _, _) in be] != [g for _, g in want_b]:
                    bad.append(('nb', iso, t, x))
    check('v2 country count / top / neighbours = brute force (10 countries x 3 times)', not bad, str(bad[:4]))

    # 16. blocks partition every shared cohort into contiguous ranges of its bucket's rows; country sizes follow the weights
    ok = True
    size = {}
    expect = {}                  # the apportionment's expectation: n x the row's (M11-tilted) weight share in its bucket
    for c in W.cohorts:
        if c.local:
            continue
        rows = Pp.BUCKET_ROWS[D.BUCKETS[c.b]]
        pos = 0
        for ri, s0, e0 in c.blocks:
            ok &= s0 == pos and e0 > s0 and 0 <= ri < len(rows)
            pos = e0
            size[rows[ri].iso] = size.get(rows[ri].iso, 0) + (e0 - s0)
        ok &= pos == c.n
        akey = Pp.ARCH[c.a]['key']
        tilt = Pp.ROW_TILT or {}
        wts = [r.weight * tilt.get(r.iso, {}).get(akey, 1.0) for r in rows]
        tw = sum(wts)
        for r, w in zip(rows, wts):
            expect[r.iso] = expect.get(r.iso, 0.0) + c.n * w / tw
    tot = sum(size.values())
    dev = []
    for iso in ('US', 'GB', 'DE', 'BR', 'TR', 'JP', 'SK', 'SI'):
        want = expect[iso] / tot
        got = size.get(iso, 0) / tot
        if abs(got - want) > 0.08 * want + 3.0 / tot ** 0.5:
            dev.append((iso, round(got / want, 3)))
    check('v2 blocks partition every cohort; country shares follow the table weights', ok and not dev,
          'dev %s, %d players' % (dev, tot))

    # 17. jitter: u strictly increasing in j (never equal to the next member's), inside (0, 1)
    ok = True
    for c in [c for c in W.cohorts if c.n > 2][::37][:200]:
        us = [W.u_of(c, j) for j in range(c.n)]
        ok &= all(0.0 <= a < b <= 1.0 for a, b in zip(us, us[1:]))
    check('v2 jittered quantiles strictly increasing', ok)

    # 18. two unknown region codes: different LOCAL skeletons (sizes, levels, names); neither touches the shared world
    ws = {}
    for code in ('ZZ', 'XA'):
        w, iso = V2.world_for_home(code)
        w.extend_to(T_NOW)
        ws[code] = w
    la = [c for c in ws['ZZ'].cohorts if c.local]
    lb = [c for c in ws['XA'].cohorts if c.local]
    sizes_differ = [c.n for c in la[:40]] != [c.n for c in lb[:40]]
    na = [ws['ZZ'].name(c, j)[0] for c in la[:60] for j in range(min(2, c.n))]
    nb_ = [ws['XA'].name(c, j)[0] for c in lb[:60] for j in range(min(2, c.n))]
    same_names = sum(1 for a, b in zip(na, nb_) if a == b)
    top_a = [W2l for W2l in (ws['ZZ'].top(T_NOW, 10, 'ZZ'))]
    top_b = [W2l for W2l in (ws['XA'].top(T_NOW, 10, 'XA'))]
    lv_a = [ws['ZZ'].level(c, j, T_NOW) for (_, _, c, j) in top_a]
    lv_b = [ws['XA'].level(c, j, T_NOW) for (_, _, c, j) in top_b]
    byck = {c.ck: c for c in ws['ZZ'].cohorts if not c.local}
    shared_same = all(c.ck in byck and byck[c.ck].n == c.n and byck[c.ck].gid0 == c.gid0 and byck[c.ck].blocks == c.blocks
                      and (c.n == 0 or ws['ZZ'].name(byck[c.ck], c.n - 1) == W.name(c, c.n - 1))
                      for c in W.cohorts[::7] if c.p < ws['ZZ'].periods)
    check('v2 LOCAL skeletons differ per ISO and leave the shared world alone',
          sizes_differ and lv_a != lv_b and same_names < len(na) // 4 and shared_same,
          'top10 ZZ %s / XA %s, equal names %d/%d' % (lv_a[:5], lv_b[:5], same_names, len(na)))

    # 19. every Locale.Region.isoRegions code resolves to a board; aliases point at rows; offsets within +-60 min
    codes = []
    for l in open(os.path.join(D.DATA_V2, 'ios_regions.tsv'), encoding='utf-8'):
        if not l.startswith('#'):
            codes.append(l.split('\t')[0])
    row_isos = {r.iso for r in D.COUNTRY_ROWS}
    unresolved = [c for c in codes if D.resolve_region(c)[0] == 'unknown' or D.resolve_region(c)[1] not in row_isos]
    offs = [r.iso for r in D.COUNTRY_ROWS if abs(r.off - D.BUCKET_OFF[r.bucket]) > 60]
    check('v2 every isoRegions code resolves to a row (%d codes)' % len(codes), not unresolved and not offs and len(codes) >= 280,
          'unresolved %s, offsets %s' % (unresolved[:8], offs))

    # 20. native-script names: right script, valid as a username, never blocked; every row culture has >= 300 names
    d = Nm.data()
    bad = []
    for cu in d['nativeScript']:
        toks = d['cultures'].get(cu, [])
        for i in range(0, len(toks), max(1, len(toks) // 60)):
            for vr in range(4):
                s = Nm.build('given', i, 0, cu, vr=vr)
                if not username_ok(s) or Nm.is_blocked(s):
                    bad.append((cu, s))
    used = sorted({cu for r in D.COUNTRY_ROWS for cu, _ in r.mix})
    # hy / ka: every name Wikidata records for Armenia's / Georgia's adults (205 / 258 after screening; SOURCES.md) —
    # below 300, documented, and M7 shrinks the popularity head for short lists
    SMALL_DATA = {'hy': 200, 'ka': 200}
    short = [(cu, len(d['cultures'].get(cu, []))) for cu in used
             if len(d['cultures'].get(cu, [])) < SMALL_DATA.get(cu, 300)]
    # details: counts and sha1 prefixes only (a failing name is never printed)
    import hashlib
    check('v2 native-script names valid usernames, not blocked; row cultures >= 300 names (hy, ka >= 200)',
          not bad and not short,
          'bad %d %s; short %s' % (len(bad), [(cu, hashlib.sha1(s.encode()).hexdigest()[:8]) for cu, s in bad[:6]], short))

    # 21. per-member culture follows the row's mix (BE nl .6 / fr .4, CH de .65, CA en .78)
    dev = []
    for iso, cu, want in (('BE', 'nl', 0.6), ('CH', 'de', 0.65), ('CA', 'en', 0.78), ('US', 'es', 0.0858)):
        n = k = 0
        for c in W.cohorts:
            if c.local or c.join0 - c.span > T_NOW:
                continue
            for (ri, s0, e0) in c.blocks:
                if Pp.BUCKET_ROWS[D.BUCKETS[c.b]][ri].iso != iso:
                    continue
                for j in range(s0, e0):
                    n += 1
                    k += W.culture_of(c, j) == cu
            if n > 6000:
                break
        if n == 0 or abs(k / n - want) > 3.5 * (want * (1 - want) / n) ** 0.5 + 0.01:
            dev.append((iso, cu, n, round(k / max(1, n), 3)))
    check('v2 per-member culture follows the row mix', not dev, str(dev))

    # 22. the world epoch: nobody joins before it; period 0 starts at it; world weeks share the event weeks' boundaries
    first_join = min(W.member(c, c.n - 1)[2] for c in W.cohorts if c.n > 0 and c.p == 0)
    ok = W.epoch == V2.WORLD_EPOCH and first_join >= V2.WORLD_EPOCH and (V2.WORLD_EPOCH - K.EPOCH) % K.WEEK == 0
    ok &= W.gid_limit(V2.WORLD_EPOCH - 1) == 0 and W.joined(V2.WORLD_EPOCH - 1) == 0
    check('v2 world epoch 2026-09-07 07:00 UTC, event weeks aligned', ok)
