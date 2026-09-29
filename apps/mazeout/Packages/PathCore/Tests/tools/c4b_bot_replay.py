#!/usr/bin/env python3
"""c4b_bot_replay.py — pins the phone bot's winning taps on the corner levels (and L69's pipes under doors) for PathCore.

The session-2 bot (research/bot/go2.py + corners.py) tapped only arrows it read as free and won L69 and every corner level
of v552 (L73, L76, L79, L80, L82: 18 corners) with 3/3 hearts, so under the right rules every logged tap must EXIT.
design/tools/replay_log.py checks that under arrowcore; RulesTests.testPhoneBotWinningTapsExitUnderTheGameRules replays
the SAME inputs under PathCore (C2's BoardState and C4's content mirror).

Pinned (hermetic, like Fixtures/research): each level's logged taps (research/bot/log.jsonl, result == "tapped", log
order: round, t, cells in that round's read frame) + what replay_log.replay says on the pinned levels.json board (the
integer shift, the start-visible arrows the log never taps and that are removed first, taps that exit, logged units that
match no arrow, arrows left) so the Swift test can check its own mapping against the reference's.

  python3 Packages/PathCore/Tests/tools/c4b_bot_replay.py            # writes Tests/Fixtures/c4b_bot_replay.json
  python3 Packages/PathCore/Tests/tools/c4b_bot_replay.py --check    # exit 1 when the pinned levels' taps changed

LEVELS are the LOG's level numbers (v552's). Since the level re-order (PUBLISH item 12) a number no longer names a board: each
board is found by its provenance (design/tools/level_order.py: the v552 number in its capture), replayed under the log's
number, and its row records `slot` = the level it ships at (BotReplayTests replays the taps on C4Fixtures.level(slot)).
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(os.path.dirname(HERE))
APP = os.path.dirname(os.path.dirname(PKG))
sys.path.insert(0, os.path.join(APP, 'design', 'tools'))
import replay_log  # noqa: E402
import level_order  # noqa: E402

LEVELS = [69, 73, 76, 79, 80, 82]
LOG = os.path.join(APP, 'research', 'bot', 'log.jsonl')
CONTENT = os.path.join(PKG, 'Tests', 'Fixtures', 'content', 'levels.json')
OUT = os.path.join(PKG, 'Tests', 'Fixtures', 'c4b_bot_replay.json')


def build():
    raw = open(LOG, 'rb').read()
    recs = [json.loads(x) for x in raw.decode('utf-8').splitlines() if x.strip()]
    doc = json.load(open(CONTENT))
    board, slot = level_order.resolver(doc)
    out = []
    for L in LEVELS:
        b = board(doc, L)
        assert b['source'] == 'recorded' and level_order.rslot(b) == L, 'L%d: not the phone board v552 L%d' % (L, L)
        lv = {L: dict(b, level=L)}                   # the board under the log's number (replay_log reads the log by it)
        assert L not in replay_log.WINNING_RUN, 'L%d: the log holds two attempts' % L
        taps = [r for r in recs if r.get('level') == L and r.get('result') == 'tapped']
        known = {frozenset(map(tuple, a['cells'])): a['id'] for a in lv[L]['arrows']}
        dx, dy = replay_log.best_shift([[tuple(c) for c in r['cells']] for r in taps], set(known))
        ok, n, problems, left, hand = replay_log.replay(lv[L])
        out.append(dict(level=L, slot=slot(L), corners=sum(1 for o in lv[L]['obstacles'] if o['kind'] == 'corner'),
                        taps=[dict(round=r.get('round'), t=r['t'], cells=r['cells']) for r in taps],
                        python=dict(shift=[dx, dy], exits=ok, logged=n, hand=hand, left=left,
                                    unmatched=sum(1 for p in problems if 'matches no arrow' in p),
                                    bumps=sum(1 for p in problems if 'matches no arrow' not in p))))
    return dict(_about='The phone bot\'s winning taps (research/bot/log.jsonl) on L69 (pipes under doors) and the corner levels, '
                       'with design/tools/replay_log.py\'s verdict on the pinned levels.json (Tests/tools/c4b_bot_replay.py).',
                log_sha256=hashlib.sha256(raw).hexdigest(),
                content_sha256=hashlib.sha256(open(CONTENT, 'rb').read()).hexdigest(),
                levels=out)


def main():
    doc = build()
    text = json.dumps(doc, sort_keys=True, indent=1) + '\n'
    if '--check' in sys.argv:
        # the log keeps growing while the phone bot plays on (other levels): the pin is current when the pinned levels'
        # taps, the content and the reference's verdicts are still what the log and levels.json give
        old = json.load(open(OUT)) if os.path.exists(OUT) else {}
        same = old.get('levels') == doc['levels'] and old.get('content_sha256') == doc['content_sha256']
        print('c4b_bot_replay.json is %s%s' % ('current' if same else 'STALE',
                                              '' if old.get('log_sha256') == doc['log_sha256'] else
                                              ' (research/bot/log.jsonl has grown since the pin; the pinned levels are unchanged)'
                                              if same else ''))
        return 0 if same else 1
    open(OUT, 'w').write(text)
    for l in doc['levels']:
        p = l['python']
        print('L%d%s: %d taps, corners %d, shift %s, exits %d, unmatched %d, bumps %d, hand %s, left %d' % (
            l['level'], '' if l['slot'] == l['level'] else ' (ships at L%d)' % l['slot'], len(l['taps']), l['corners'], p['shift'], p['exits'], p['unmatched'], p['bumps'], p['hand'], p['left']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
