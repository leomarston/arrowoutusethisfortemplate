#!/usr/bin/env python3
"""golden_rounds.py — builds Tests/Fixtures/c2_golden_rounds.json for GoldenRoundsTests (SPEC-architecture §4.17, C2).

The golden test from real play: every arrow the phone bot tapped (research/bot/log.jsonl, result == "tapped", L32–L61) must
be FREE in our rules when it was tapped. The bot re-read the board from a screenshot every round, so each round's cells
are in that read's own frame; this tool maps them onto the completed levels (Fixtures/c2_recorded_levels.json) and
records, per level, the RUNS (one bot process = rounds 1, 2, …) with their taps in order:

  * the frame of a round: the bot's own shot of that round (research/bot/tmp/L0NN-<run>-rNN.png, cached read in
    Fixtures/c2_reads.json) when its arrows contain the logged cells (start = read - shift); otherwise the best integer
    shift by cell-set votes over the level's arrows (ties: the previous round's shift);
  * a tap = {row, round, t, arrow (level id), unit (the bot's bundle size: 1 or the tape group)};
  * `observed` = the level ids of the arrows the run's FIRST shot shows (anomaly-free read), so the replay can tell a
    fresh attempt (an arrow the chain removed is back) from a continuation, and find arrows removed by unlogged hand
    taps before the run (research/levels.md: L35 pipe arrows by hand, L47 / L52 probes, L50 the 10th clear by hand);
  * `ended` = the event row that closed the run (guard_stop = a popup: the level ended or the player paused).

Taps whose cells match no arrow of the level are listed as `unmapped` with the reason (never silently dropped).
"""
import json, os, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
LOG = os.path.join(APP, 'research', 'bot', 'log.jsonl')
FIX = os.path.join(HERE, '..', 'Fixtures')
LEVELS = os.path.join(FIX, 'c2_recorded_levels.json')
READS = os.path.join(FIX, 'c2_reads.json')
OUT = os.path.join(FIX, 'c2_golden_rounds.json')
# Runs whose START STATE is unknown and cannot be observed (keyed by level and the run's first log row). Their taps are
# reported as unverifiable, never checked against a guessed state.
UNKNOWN_START = {
    (32, 0): 'L32 attempt 1: the orchestrator played ~52 s by hand before handing over (research/phone-session1-progress.md '
             '00:17 entered, 00:20 "PAUSED at 2:08 … zoomed out"), then the player probed by hand (00:39-00:48: a 5 s press, '
             'the P02 queued taps, clip S1-P02 = a 26-cell snake exiting up); the run\'s own round shots were overwritten by '
             'L32 run 2 (unnamed L032-rNN.png files), so no shot shows the board this run started from',
}
UTC_OFFSET = 3 * 3600          # the bot's RUN ids are local wall time (+03): RUN 011032 ↔ log t 1790287837 (22:10:37 UTC)


def run_seconds(run):
    return int(run[0:2]) * 3600 + int(run[2:4]) * 60 + int(run[4:6])


def main():
    rows = [json.loads(l) for l in open(LOG) if l.strip()]
    levels = {lv['level']: lv for lv in json.load(open(LEVELS))['levels']}
    reads = json.load(open(READS))['levels']
    out_levels = []
    totals = collections.Counter()
    for L in range(32, 62):
        lv = levels[L]
        by_cells = {frozenset(map(tuple, a['cells'])): a['id'] for a in lv['arrows']}
        by_len = collections.defaultdict(list)
        for k in by_cells:
            by_len[len(k)].append(k)
        rr = reads.get(str(L), {}).get('rounds', [])
        shots = {}
        for r in rr:
            shots[(r['run'], r['round'])] = r
        run_ids = sorted({r['run'] for r in rr if r['run']}, key=run_seconds)
        lrows = [(i, r) for i, r in enumerate(rows) if r['level'] == L]
        # --- runs
        runs = []
        cur = None
        last_round = None
        for i, r in lrows:
            if 'event' in r:
                if r['event'] in ('taps_done',):
                    continue
                if cur is not None and cur['ended'] is None:
                    cur['ended'] = r['event']
                    cur['ended_why'] = r.get('why')
                elif cur is None:
                    runs.append(dict(taps_rows=[], ended=r['event'], ended_why=r.get('why'), pre_event_only=True))
                continue
            if r.get('result') != 'tapped':
                continue
            rnd = r.get('round', 0)
            new_run = cur is None or cur['ended'] is not None or (last_round is not None and rnd < last_round) \
                or (cur['taps_rows'] and r['t'] - rows[cur['taps_rows'][-1]]['t'] > 90)
            if new_run:
                cur = dict(taps_rows=[], ended=None, ended_why=None)
                runs.append(cur)
            cur['taps_rows'].append(i)
            last_round = rnd
        runs = [r for r in runs if r.get('taps_rows')]
        # --- which shots belong to which run: a named run id (process start ≤ the first tap), else the UNNAMED files
        # (L0NN-rNN.png, the first bot version) belong to the LAST run with no named id (each run overwrote them)
        named = []
        for run in runs:
            local = (int(rows[run['taps_rows'][0]]['t']) + UTC_OFFSET) % 86400
            cand = [x for x in run_ids if 0 <= local - run_seconds(x) <= 900]
            named.append(cand[-1] if cand else None)
        unnamed_owner = max([k for k, x in enumerate(named) if x is None], default=None)
        # --- map taps
        out_runs = []
        for k, run in enumerate(runs):
            shot_run = named[k] if named[k] is not None else ('' if k == unnamed_owner else None)
            rounds = collections.OrderedDict()
            for i in run['taps_rows']:
                rounds.setdefault(rows[i].get('round', 0), []).append(i)
            taps, unmapped = [], []
            prev_shift = None
            observed = None
            for rnd, idxs in rounds.items():
                shot = shots.get((shot_run, rnd)) if shot_run is not None else None
                shift, how = None, None
                if shot and shot['read']['ok']:
                    rd = shot['read']
                    read_sets = {frozenset(map(tuple, a['cells'])) for a in rd['arrows']}
                    if all(frozenset(map(tuple, rows[i]['cells'])) in read_sets for i in idxs):
                        shift = (-rd['shift'][0], -rd['shift'][1])
                        how = shot['file']
                if shift is None:
                    votes = collections.Counter()
                    for i in idxs:
                        cs = [tuple(c) for c in rows[i]['cells']]
                        m = min(cs)
                        for a in by_len[len(cs)]:
                            ma = min(a)
                            dc, dr = ma[0] - m[0], ma[1] - m[1]
                            if frozenset((c + dc, r_ + dr) for c, r_ in cs) == a:
                                votes[(dc, dr)] += 1
                    if votes:
                        top = votes.most_common()
                        best = [s for s, n in top if n == top[0][1]]
                        shift = prev_shift if prev_shift in best else sorted(best)[0]
                        how = 'votes %d/%d%s' % (top[0][1], len(idxs), ' (tie → previous round)' if len(best) > 1 else '')
                if shift is not None:
                    prev_shift = shift
                for i in idxs:
                    r = rows[i]
                    unit = len(r['ids']) if r.get('ids') else (len(r['group']) if r.get('group') else 1)
                    cs = frozenset((c + shift[0], r_ + shift[1]) for c, r_ in r['cells']) if shift else None
                    aid = by_cells.get(cs) if cs is not None else None
                    frame = how
                    if aid is None and cs is not None and len(cs) >= 2:
                        # a read one cell short (few arrows left: the reused grid fit clips a tail): the unique arrow with
                        # the same direction that contains every read cell and is at most one cell longer
                        fits = [a for a in lv['arrows'] if a['dir'] == r['dir'] and cs < frozenset(map(tuple, a['cells']))
                                and len(a['cells']) - len(cs) <= 1]
                        if len(fits) == 1:
                            aid = fits[0]['id']
                            frame = '%s; read one cell short of arrow %d' % (how, aid)
                    if aid is None:
                        unmapped.append(dict(row=i, round=rnd, cells=[list(c) for c in r['cells']],
                                             why='no frame' if shift is None else 'no arrow of the level has these cells (shift %s, %s)' % (list(shift), how)))
                        continue
                    taps.append(dict(row=i, round=rnd, t=r['t'], arrow=aid, unit=unit, frame=frame))
                if observed is None and shot and shot['read']['ok'] and not shot['read']['anomalies'] and shift is not None:
                    rd = shot['read']
                    ids, extra = [], 0
                    for a in rd['arrows']:
                        cs = frozenset((c - rd['shift'][0], r_ - rd['shift'][1]) for c, r_ in a['cells'])
                        if cs in by_cells: ids.append(by_cells[cs])
                        else: extra += 1
                    observed = dict(round=rnd, file=shot['file'], arrows=sorted(ids), unmatched=extra)
            totals['taps'] += len(taps) + len(unmapped)
            totals['mapped'] += len(taps)
            totals['unmapped'] += len(unmapped)
            out_runs.append(dict(index=k, rows=[run['taps_rows'][0], run['taps_rows'][-1]],
                                 startUnknown=UNKNOWN_START.get((L, run['taps_rows'][0]), ''),
                                 shotRun=shot_run if shot_run is not None else '(overwritten)',
                                 ended=run['ended'] or '', endedWhy=run['ended_why'] or '', observed=observed,
                                 taps=taps, unmapped=unmapped))
        out_levels.append(dict(level=L, runs=out_runs))
    json.dump(dict(schema=1, tool='Tests/tools/golden_rounds.py', source='research/bot/log.jsonl', levels=out_levels,
                   totals=totals), open(OUT, 'w'), separators=(',', ':'), sort_keys=True)
    for lv in out_levels:
        print('L%d: %s' % (lv['level'], ' | '.join('run%d %s taps %d unm %d obs %s end %s' % (
            r['index'], r['shotRun'] or 'unnamed', len(r['taps']), len(r['unmapped']),
            ('%s:%d' % (r['observed']['file'].split('-r')[-1], len(r['observed']['arrows']))) if r['observed'] else '-',
            r['ended'] or '-') for r in lv['runs'])))
    print(dict(totals))
    print('wrote', OUT)


if __name__ == '__main__':
    main()
