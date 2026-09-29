#!/usr/bin/env python3
"""batch C: write research/levels/L0NN.json (levels 21-30) from the checked work files."""
import json, os, sys
MZ = '/Users/yago/Downloads/app-factory/apps/mazeout'
W = MZ + '/research/video-frames/work/levelsC/'
SCR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCR)
import chk
idx = json.load(open(MZ + '/research/video-index.json'))
IDX = {L['level']: L for L in idx['levels'] if L['video'] == 'V2'}
TAG = {'Hard': 'Hard Level', 'Super Hard': 'Super Hard', None: None}
PHONE = {21: ('L035', 'research/levels/L035.json', '20/20 arrows and the pipe (cells, ends) identical, shift (0,0); pitch 28.03 vs 28.09 pt; phone timer 3:00, pipe counter 2 (phone clip S1-L35-pipe-first: 2->1)'),
         26: ('L045', 'research/levels/L045.json', '26/26 arrows identical, shift (0,0); pitch 23.075 vs 23.115 pt; phone timer 2:30 (video 3:00)')}


def v2(n):
    return json.load(open(W + 'V2-L%03d-verify2.json' % n))


def model_counter_at(events, bi, t, c0):
    prior = [e for e in events if e['t'] <= t]
    return prior[-1]['boxes_after'][bi][1] if prior else c0


def main(n):
    js = json.load(open(W + 'V2-L%03d.json' % n))
    L = IDX[n]
    rep = json.load(open(W + 'V2-L%03d-replay.json' % n))
    sol = chk.solve(js)
    fixes = js.pop('fixes', [])
    js['tag'] = TAG[L.get('tag')]
    js['timer_s'] = 180
    js['hearts'] = 3
    ob = json.load(open(W + 'V2-L%03d-obst.json' % n)) if os.path.exists(W + 'V2-L%03d-obst.json' % n) else None
    ev = json.load(open(W + 'V2-L%03d-events.json' % n)) if os.path.exists(W + 'V2-L%03d-events.json' % n) else None
    obst_out = []
    if ob:
        box_ids = [k for k, o in enumerate(js['obstacles']) if o['kind'] in ('box', 'curtain')]
        pipe_ids = [k for k, o in enumerate(js['obstacles']) if o['kind'] == 'pipe']
        for o in ob['obstacles']:
            k = o['k']
            rec = dict(obstacle=k, kind=o['kind'], counter=js['obstacles'][k].get('counter'), t_break_video=o['t_break'],
                       counter_readings_video=o['readings_collapsed'])
            if o['kind'] in ('box', 'curtain'):
                bi = box_ids.index(k)
                c0 = js['obstacles'][k]['counter']
                z = next((e for e in ev if e['boxes_after'][bi][1] <= 0), None)
                rec['model_zero'] = dict(t=z['t'], arrows_removed=z['removed'], by_arrows=z['ids']) if z else None
                bad = []
                for t, v in o['readings_collapsed']:
                    if v is None:
                        continue
                    cands = {model_counter_at(ev, bi, t, c0)}
                    nxt = [e for e in ev if e['t'] > t]
                    if nxt and (nxt[0]['t'] - t <= 0.1 or not nxt[0]['tapped']):
                        # the replay stamps an exit whose touch was not detected at the NEXT tap's sync frame (late), and tap
                        # times carry the 30-fps scan's +-0.03 s: the video may be one removal (or one bundle) ahead
                        cands.add(nxt[0]['boxes_after'][bi][1])
                    ok = v in cands or ({6: 9, 9: 6}.get(v) in cands)     # Vision reads this font's 9 as 6 and back
                    if ok:
                        continue
                    if not ok:
                        bad.append([t, v, model_counter_at(ev, bi, t, c0)])
                HAND = {(28, 928.06): "tap 927.911 at (251,453) px lies 0.92 cell from arrow 8's head (8,5): the replay could not map it "
                                      "(> 0.75 cell) and stamped arrow 8's exit at 928.881; with arrow 8 leaving at 927.911 the reading 19 is exact"}
                expl = [b_ + [HAND[(n, b_[0])]] for b_ in bad if (n, b_[0]) in HAND]
                rec['readings_unexplained'] = [b_ for b_ in bad if (n, b_[0]) not in HAND]
                if expl:
                    rec['readings_explained_by_hand'] = expl
                rec['rule'] = 'every removed arrow (each Linked member) lowers the counter by 1, all boxes at once, at the tap; breaks when it reaches 0'
            else:
                pk = pipe_ids.index(k)
                rec['passes'] = [dict(t=e['t'], arrows=e['ids']) for e in ev if pk in e['pipe_passes']]
                rec['rule'] = 'each arrow that travels through lowers the counter by 1 (~0.42 s after the tap for an arrow starting next to the mouth); the pass that takes it to 0 shatters the pipe instead (~0.4 s after the tap), its cells become empty board cells'
            obst_out.append(rec)
    ver = v2(n)
    st = rep['stats']
    cols = js['cols']
    rule = min(28.07, max(14.04, 393.0 / (cols + 2)))
    before = [b for b in L.get('before', []) if b['kind'] == 'unlock']
    batch = dict(
        extractor='level extractor batch C (levels 21-30), 2026-09-25; tools: vextract (index agent) + research/levels/video/ccheck/ (chk.py verify2/solve, obst.py, corr.py, fix.py, build.py); report research/video-levels-C.md',
        start_frame=dict(t=js['t'], frame=js['frame'], rule=L.get('t_board_rule'), revealed_after_popup=L.get('revealed_after_popup'),
                         looked_at='yes: full board, HUD 3:00 + 3 hearts, no popup/hand/touch disc'),
        fixes=fixes or ['none: the index extraction was right cell for cell (overlay read by eye)'],
        verify=dict(vextract=dict(ink_iou=js['verify']['ink_iou'], ink_iou_tol1px=js['verify']['ink_iou_tol1px'],
                                  note='obstacle bboxes excluded; triangle heads + unrounded corners'),
                    video_skin=dict(ink_iou=ver['ink_iou2'], ink_iou_tol1px=ver['ink_iou2_tol1px'], missed_px=ver['missed_px'], extra_px=ver['extra_px'],
                                    max_blob_px=ver['max_blob_px'], max_compact_blob_px=ver['max_compact_blob_px'], fit=ver['params'],
                                    note='3x supersampled render with rounded corners + rounded heads, sub-px registration; obstacles excluded per CELL (+-0.7 pitch), not per bbox; a reversed arrow leaves 77-114 px compact blobs (negative control on L25/L29)')),
        replay=dict(report='research/video-frames/work/levelsC/V2-L%03d-replay.json' % n,
                    **{k: st.get(k) for k in ('taps', 'mapped', 'exit_free', 'gone_free', 'miss', 'consistent', 'inconsistent', 'left_at_end',
                                             'blockers_broken', 'pipes_broken', 'counter_mismatch')}),
        solver=dict(rules='research/bot/bot.py ray() (pipe teleport) + tape bundles + box counters (every removed arrow) + pipe counters (passes)',
                    greedy_solved=sol['greedy_solved'], steps=sol['greedy_steps'], units=sol['units'],
                    random_free_orders_stuck=sol['random_orders_stuck']),
        grid_rule=dict(pitch_pt=js['pitch_pt'], clamp_393_over_cols_plus_2=round(rule, 3), diff_pt=round(js['pitch_pt'] - rule, 3)),
        play=dict(timer_start=L.get('timer_start'), hearts_start=L.get('hearts_start'), hearts_end=L.get('hearts_end'),
                  heart_losses=len(L.get('heart_drops') or []), t_first_tap=L.get('t_first_tap'), t_clear=L.get('t_clear'),
                  timer_at_clear=L.get('timer_at_clear'), reward=L.get('reward'), taps=L.get('n_taps'), booster_taps=L.get('n_booster_bar_taps'),
                  unlock_popup_before=[' / '.join(b['text']) for b in before] or None, tutorial_hand=L.get('tutorial_hand'),
                  home_tag=L.get('tag')),
        obstacles=obst_out or None)
    if n in PHONE:
        batch['phone_match'] = dict(phone_level=PHONE[n][0], file=PHONE[n][1], result=PHONE[n][2])
    js['batchC'] = batch
    out = MZ + '/research/levels/L%03d.json' % n
    json.dump(js, open(out, 'w'), indent=1)
    print(n, out, len(js['arrows']), js['cols'], js['rows'], js['tag'], sol['greedy_solved'], st['consistent'], st['inconsistent'], ver['ink_iou2_tol1px'])


if __name__ == '__main__':
    for n in (int(x) for x in sys.argv[1:]):
        main(n)
