#!/usr/bin/env python3
"""replay_log.py — the phone bot's winning taps replayed on the imported boards under arrowcore's rules (a rules check).

The session-2 bot (research/bot/go2.py + corners.py) tapped only arrows it read as free and won every level below with 3/3
hearts, so under the right rules every logged tap must EXIT (a bump would have cost a heart on the phone). For each level:
the taps of research/bot/log.jsonl (cells in that round's read frame) are mapped to the start frame by the integer shift that
matches the most logged units to known arrows (start + hidden, reveal_backfill), then played in log order on arrowcore.Board
(doors open before the next tap, as the solver does). Reports every tap that bumps or matches no arrow.

  python3 design/tools/replay_log.py [70 73 76 ...]    (default: every L62-L105 level whose log is one clean attempt)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import arrowcore as ac  # noqa: E402

# one winning attempt in the log, the logged units = the level's units minus the taps made by hand (clips/probes)
# levels with an earlier failed attempt in the log: the winning run (research/bot/tmp/Lnnn-HHMMSS-rNN, local time)
WINNING_RUN = {62: '111843', 77: '135026'}
DEFAULT = [62, 63, 64, 65, 66, 67, 68, 69, 72, 73, 74, 75, 76, 79, 80, 81, 82, 77, 78, 83]
# phone session 3 (research/bot/go3.py: go2 + corners + automatic clip hooks; every level won on the first attempt; the
# deliberate long-gap bumps of the clip hook are not 'tapped' records of the bot's log)
# L103 (= the older build's V2-L033, a stand-in slot that does not ship) is left out: its log repeats the cells of two platform
# arrows (28, 35) after they left and the replay cannot place the elevator clip's unlogged taps (build/recast2/replay-L103.txt)
DEFAULT += [n for n in range(84, 106) if n != 103]


def best_shift(cells_list, known):
    best, bs = (0, 0), -1
    for dx in range(-3, 4):
        for dy in range(-20, 21):
            n = sum(1 for cs in cells_list if frozenset((c + dx, r + dy) for c, r in cs) in known)
            if n > bs:
                best, bs = (dx, dy), n
    return best


def shift_matches(cells_list, known, dx, dy):
    return sum(1 for cs in cells_list if frozenset((c + dx, r + dy) for c, r in cs) in known)


def wide_shift(cells_list, known):
    best, bs = (0, 0), -1
    for dx in range(-40, 41):
        for dy in range(-60, 61):
            n = shift_matches(cells_list, known, dx, dy)
            if n > bs:
                best, bs = (dx, dy), n
    return best, bs


def replay(lvl, refined=False):
    """(taps that exit, logged taps, problems, arrows left, hand taps) for one level.

    refined=False is content recast 1's mapping, kept as it was for the callers that pin it: ONE integer shift for every
    logged unit of the level, the start-visible arrows the log never taps removed once, first, in id order. PathCore's
    BotReplayTests implements exactly this mapping and checks its own result against this verdict
    (Packages/PathCore/Tests/tools/c4b_bot_replay.py calls replay(level) for Fixtures/c4b_bot_replay.json).
    refined=True (main(), the rules check since content recast 2, phone session 3): a round the level's shift does not
    explain gets its own shift, hand taps are removed again whenever a logged tap would not exit, a layer-2 arrow with
    the cells of the platform arrow above it is told apart, and an elevator clip's platform arrows go last. On the six
    levels pinned for BotReplayTests only L73 reads differently (4 units of one round the bot read in another frame: 57
    exit + 4 unmatched + 4 hand taps with one shift; all 61 exit with per-round shifts)."""
    L = lvl['level']
    recs = [json.loads(x) for x in open(os.path.join(APP, 'research', 'bot', 'log.jsonl'))]
    recs = [r for r in recs if r.get('level') == L and r.get('result') == 'tapped']
    if L in WINNING_RUN:                  # a level the log holds twice: keep the winning attempt (its round shots' stamp)
        import time
        t0 = time.mktime(time.strptime('2026-09-25 ' + WINNING_RUN[L], '%Y-%m-%d %H%M%S')) - 5
        recs = [r for r in recs if r['t'] >= t0]
    known = {frozenset(map(tuple, a['cells'])): a['id'] for a in lvl['arrows']}
    # a layer-2 arrow can have exactly the cells of the platform arrow above it (V2-L033 = v552 L103: 29 / 46): a logged unit
    # with those cells is the layer-1 arrow while it is alive, the hidden one after
    same = {}
    for a in sorted(lvl['arrows'], key=lambda a: (a.get('layer') or 1, a['id'])):
        if refined:
            same.setdefault(frozenset(map(tuple, a['cells'])), []).append(a['id'])
    rounds = {}
    for r in recs:
        rounds.setdefault((r.get('round'), int(r['t']) // 30), []).append(r)
    b = ac.Board(lvl)
    out, ok = [], 0
    # The board never moves during a level (no zoom), but the bot's free grid fit can land on another origin in a later round
    # (session 3's elevator levels: the platform's lavender shifts the fit): one shift for the level where it explains a round,
    # else the round's own shift, chosen among the shifts that explain >= 3 units of some round (a 1-tap round alone could match
    # a short straight arrow at a wrong shift).
    kset = set(known)
    dx, dy = best_shift([[tuple(c) for c in r['cells']] for r in recs], kset)
    cands = [(dx, dy)]
    for key in rounds:
        cl = [[tuple(c) for c in r['cells']] for r in rounds[key]]
        if refined and shift_matches(cl, kset, dx, dy) < len(cl):
            sh, n = wide_shift(cl, kset)
            if n >= 3 and sh not in cands:
                cands.append(sh)
    shift_of = {}
    for key in rounds:
        cl = [[tuple(c) for c in r['cells']] for r in rounds[key]]
        shift_of[key] = max(cands, key=lambda s_: (shift_matches(cl, kset, *s_), s_ == (dx, dy)))
    logged = set()
    for key, rs in rounds.items():
        sx, sy = shift_of[key]
        for r in rs:
            aid = known.get(frozenset((c + sx, rr + sy) for c, rr in map(tuple, r['cells'])))
            if aid is not None:
                logged.update(b.unit(aid))
    # taps made by hand (clips, probes: research/phone-session{2,3}-progress.md) = the start-visible arrows the log never taps:
    # removed first while they are free, and again whenever a logged tap would not exit (a hand tap mid-level, e.g. the
    # session-3 hit-tolerance clip), before that tap is judged
    hand = [a['id'] for a in lvl['arrows'] if a['id'] not in logged and a.get('hidden_by') is None]

    # an unlogged round of session 3's elevator clip (research/bot/go3.py elevator_guard) tapped every free unit of one read
    # and stopped right AFTER the tap that emptied a platform: so the platform arrows go last, one at a time
    plat = {a for o in lvl['obstacles'] if o['kind'] == 'elevator' for a in o.get('arrows', [])}

    def remove_free_hand():
        if not refined:                   # recast 1: once, first, in id order
            n = 0
            for aid in hand:
                res = b.resolve(aid)
                if res[0] == 'exit':
                    b.commit_exit(res[1], res[2])
                    b.open_pending_doors()
                    n += 1
            return n
        n, more = 0, True
        while more:                       # to a fixpoint: a hand tap can free another
            more = False
            for group in ([a for a in hand if a not in plat], [a for a in hand if a in plat]):
                for aid in group:
                    if aid in b.alive:
                        res = b.resolve(aid)
                        if res[0] == 'exit':
                            b.commit_exit(res[1], res[2])
                            b.open_pending_doors()
                            n += 1
                            more = True
                            if aid in plat:
                                break     # one platform arrow, then the others again
                if more:
                    break
        return n
    remove_free_hand()
    for key in sorted(rounds, key=lambda k: min(r['t'] for r in rounds[k])):
        rs = rounds[key]
        sx, sy = shift_of[key]
        for r in rs:
            k = frozenset((c + sx, rr + sy) for c, rr in map(tuple, r['cells']))
            aid = next((x for x in same.get(k, []) if x in b.alive), known.get(k))
            if aid is None:
                out.append('round %s: logged unit %s..%s matches no arrow' % (r.get('round'), r['cells'][0], r['cells'][-1]))
                continue
            res = b.resolve(aid)
            if refined and res[0] != 'exit' and remove_free_hand():
                res = b.resolve(aid)
            if res[0] != 'exit':
                out.append('round %s: arrow %d %s -> %s %s' % (r.get('round'), aid, lvl['arrows'][aid]['dir'] if aid <
                                                               len(lvl['arrows']) else '', res[0], res[2] if len(res) > 2 else ''))
                continue
            b.commit_exit(res[1], res[2])
            b.open_pending_doors()
            ok += 1
    return ok, len(recs), out, len(b.alive), hand


def main():
    levels = [int(x) for x in sys.argv[1:]] or DEFAULT
    imp = {l['level']: l for l in json.load(open(os.path.join(HERE, 'work', 'imported.json')))}
    lines, bad, unmatched = [], 0, 0
    for L in levels:
        ok, n, problems, left, hand = replay(imp[L], refined=True)
        corners = sum(1 for o in imp[L]['obstacles'] if o['kind'] == 'corner')
        lines.append('L%d: %d/%d logged taps exit under arrowcore (corners %d; untapped in the log, removed first: %s); '
                     'arrows left %d%s' % (L, ok, n, corners, hand or 'none', left,
                                           '' if not problems else '  PROBLEMS: ' + '; '.join(problems[:4])))
        bad += sum(1 for p in problems if 'matches no arrow' not in p)
        unmatched += sum(1 for p in problems if 'matches no arrow' in p)
    lines.append('logged taps that BUMP or are ignored under arrowcore: %d (must be 0); logged units the bot misread '
                 '(mid-exit / partial reads; its tap still hit an arrow, removed with the hand taps): %d' % (bad, unmatched))
    print('\n'.join(lines))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
