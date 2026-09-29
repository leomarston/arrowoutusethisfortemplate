#!/usr/bin/env python3
"""52-week plausibility bench of the offline social simulation (SPEC-social.md §7).

Simulates ONE user (profile active | casual | absent) against the shared World from an install date, with a lives
model, first-try rates, Hard/Super Hard pacing, and every social feature the user unlocks; records what the UI would
show and checks the invariants. One profile per run keeps each run under ~3 minutes:
    python3 design/social/tools/bench.py --profile active --weeks 52
Writes design/social/bench/<profile>.json.
"""
import argparse, json, os, sys, time, random, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from socialsim import population as Pp, events as E, core as K, data as D

OUTDIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bench'))

PROFILES = {
    # play_p: chance a day is played; sessions: (min,max); minutes: session length range; first: first-try win rate
    'active': dict(iso='TR', off=180, play_p=0.97, sessions=(2, 4), minutes=(12, 35), first=0.88, hard_first=0.72),
    'casual': dict(iso='US', off=-300, play_p=0.62, sessions=(1, 2), minutes=(6, 16), first=0.80, hard_first=0.60),
    'absent': dict(iso='GB', off=0, play_p=None, sessions=(1, 2), minutes=(8, 20), first=0.82, hard_first=0.62),
}

def is_hard(level):
    return level in (19, 25, 34, 44, 54) or (level > 54 and level % 5 == 4)

def is_super(level):
    return level in (29, 39, 49) or (level > 54 and level % 10 == 9)

def absent_plays(day_idx):
    """absent profile: 3 active weeks, 4 away, 1 back, 6 away, then one day a fortnight."""
    w = day_idx // 7
    if w < 3:
        return True
    if w < 7:
        return False
    if w < 8:
        return day_idx % 2 == 0
    if w < 14:
        return False
    return day_idx % 14 == 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--profile', default='active')
    ap.add_argument('--weeks', type=int, default=52)
    ap.add_argument('--install', default='2026-10-05T18:00:00')
    ap.add_argument('--seed', type=int, default=7)
    a = ap.parse_args()
    prof = PROFILES[a.profile]
    rng = random.Random(a.seed * 1000 + {'active': 1, 'casual': 2, 'absent': 3}[a.profile])
    from datetime import datetime, timezone
    t_install = int(datetime.fromisoformat(a.install).replace(tzinfo=timezone.utc).timestamp())
    install_seed = K.h64(a.seed, 'install', a.seed)
    W = Pp.World()
    W.extend_to(t_install)
    iso, off = prof['iso'], prof['off']

    # ---------------- user state
    level = 1
    lives = 5
    life_clock = None           # time the next life refills (20 min per life)
    inf_until = 0
    streak = E.Streak()
    wins = []                   # (t, level_won, first_try)
    fails = 0
    first_try_level = True
    # events
    weekly = None; weekly_w = None; weekly_user = 0; weekly_last_win = None; weekly_results = []
    streak_race = None; streak_day = None; streak_user = 0; streak_last = None; streak_results = []
    rocket = None; rocket_times = []; rocket_stage = 1; rocket_id = 0; rocket_cool = 0; rocket_results = []
    rocket_day_joined = None; rocket_starts = 0; sky_runs = 0
    sky = None; sky_step = 0; sky_stage = 1; sky_id = 0; sky_cool = 0; sky_t0 = 0; sky_results = []
    ranks = []                  # (t, level, world_rank, country_rank)
    dynamics = []               # per sampled session: overtakes
    checks = dict(backwards=0, dup_rows=0, rank_inconsistent=0, views=0)
    timing = dict(world_rank=[], country_rank=[], neighbours=[], top100=[])
    seen_levels = {}            # gid -> last level shown (backwards-jump check)
    idle = []                   # while the user was away: players who passed the user, neighbours that moved
    last_view = None            # (t, level, below-ids, window-ids) at the end of the last session
    top_prev = None; top_churn = []
    weekly_dyn = []
    play_windows = []           # (start, end) of the user's recent sessions (the app stores the last 10)

    def refill(t):
        nonlocal lives, life_clock
        while lives < 5 and life_clock is not None and t >= life_clock:
            lives += 1
            life_clock = life_clock + 1200 if lives < 5 else None

    def show_rows(rows, t):
        # invariants of any materialised list: unique ids (a row = one player), levels never decrease per id over time.
        # A repeated NAME is not a defect since SOC1c (the shipped world draws names like the original's two "Bobby"; the
        # reference's names are unique anyway): counted, not asserted (= Swift SocialBenchTests)
        ids = [r['gid'] for r in rows]
        nms = [D.key(r['name']) for r in rows]
        if len(set(ids)) != len(ids):
            checks['dup_rows'] += 1
        if len(set(nms)) != len(nms):
            checks['name_repeat_views'] = checks.get('name_repeat_views', 0) + 1
        for r in rows:
            prev = seen_levels.get(r['gid'])
            if prev is not None and r['level'] < prev:
                checks['backwards'] += 1
            seen_levels[r['gid']] = r['level']
        checks['views'] += 1

    def settle_weekly(now):
        nonlocal weekly, weekly_w
        if weekly is None or now < weekly.we:
            return
        st = weekly.standings(weekly.we, weekly_user, weekly_last_win or weekly.t0)
        rank = [k for k, x in enumerate(st) if x[2] < 0][0] + 1
        top = -st[0][0]
        weekly_results.append(dict(week=weekly_w, rank=rank, size=len(st), user=weekly_user, top=top,
                                   third=-st[2][0] if len(st) > 2 else None))
        weekly = None

    def settle_streak(now):
        nonlocal streak_race
        if streak_race is None or now < streak_race.end:
            return
        st = streak_race.standings(streak_race.end, streak_user, streak_last or streak_race.t0)
        rank = [k for k, x in enumerate(st) if x[2] < 0][0] + 1
        streak_results.append(dict(day=streak_day, rank=rank, size=len(st), user=streak_user, top=-st[0][0],
                                   prize=E.STREAK_PRIZES[rank - 1] if rank <= len(E.STREAK_PRIZES) else 0))
        streak_race = None

    def rocket_check(now):
        nonlocal rocket, rocket_stage, rocket_cool
        if rocket is None:
            return
        res, tf = rocket.outcome(rocket_times)
        if res == 'win' or (res in ('lose', 'none') and tf <= now):
            rocket_results.append(dict(stage=rocket_stage, result=res, wins=len(rocket_times),
                                       minutes=round((tf - rocket.t0) / 60.0, 1)))
            if res == 'win' and rocket_stage < 3:
                rocket_stage += 1
            elif res == 'win':
                rocket_stage = 1
                rocket_cool = K.event_day_start(K.event_day(tf) + 1)      # all 3 stages done: next event day
            else:
                rocket_stage = 1
                rocket_cool = tf + E.ROCKET_RETRY_COOLDOWN
            rocket = None

    day0 = K.event_day(t_install)
    n_days = a.weeks * 7
    t_start = time.time()
    for di in range(n_days):
        day_start_local = t_install - (t_install + off * 60) % 86400 + di * 86400     # local midnight of this day
        W.extend_to(day_start_local + 2 * 86400)
        plays = absent_plays(di) if prof['play_p'] is None else (rng.random() < prof['play_p'])
        if di == 0:
            plays = True
        sessions = []
        if plays:
            k = rng.randint(*prof['sessions'])
            for _ in range(k):
                x = rng.random()
                cdf = D.DIURNAL_CDF[0]
                h = 0
                while h < 23 and cdf[h + 1] <= x:
                    h += 1
                sessions.append(day_start_local + int((h + rng.random()) * 3600))
            if di == 0:
                sessions = [t_install]
            sessions.sort()
        sampled_dyn = (di % 3 == 0)
        for si, s0 in enumerate(sessions):
            t = s0
            settle_weekly(t); settle_streak(t); rocket_check(t)
            refill(t)
            dur = rng.uniform(*prof['minutes']) * 60
            s_end = s0 + dur
            # event joins at session start
            ed = K.event_day(t)
            if level >= E.UNLOCK['streakRace'] and streak_day != ed:
                settle_streak(t)
                daily_ref, spw, weekly_ref = E.user_pace(wins, t)
                streak_race = E.StreakRace(W, install_seed, ed, t, daily_ref, play_windows)
                streak_day = ed; streak_user = 0; streak_last = None
            if rocket_day_joined != ed:
                rocket_day_joined = ed; rocket_starts = 0; sky_runs = 0
            if (level >= E.UNLOCK['rocketRace'] and rocket is None and t >= rocket_cool and
                    (rocket_stage > 1 or rocket_starts < E.ROCKET_MAX_RACES_PER_DAY)):
                if rocket_stage == 1:
                    rocket_starts += 1
                daily_ref, spw, weekly_ref = E.user_pace(wins, t)
                rocket_id += 1
                rocket = E.RocketRace(W, install_seed, rocket_id, rocket_stage, t, spw)
                rocket_times = []
            if (level >= E.UNLOCK['skyJump'] and sky is None and t >= sky_cool and
                    (sky_stage > 1 or sky_runs < E.SKY_MAX_RUNS_PER_DAY)):
                if sky_stage == 1:
                    sky_runs += 1
                sky_id += 1
                sky = E.SkyJump(install_seed, sky_id, sky_stage)
                sky_step = 0; sky_t0 = t
            # while-away dynamics: compare with the view at the end of the previous session
            if last_view is not None and si == 0:
                tv, lv, below_ids, win_ids = last_view
                passed = sum(1 for (c, j) in below_ids if W.level(c, j, t) > level)
                moved = sum(1 for (c, j) in win_ids if W.level(c, j, t) > W.level(c, j, tv))
                idle.append(dict(hours=round((t - tv) / 3600, 1), passed_user=passed, window_moved=moved))
            # leaderboard dynamics sample: neighbours at start
            dyn = None
            if sampled_dyn and si == 0:
                t0q = time.time()
                ab, be = W.neighbours(level, t, 6, 6, iso)
                timing['neighbours'].append(time.time() - t0q)
                rows = [W.row(c, j, t) for (_, _, c, j) in ab + be]
                show_rows(rows, t)
                dyn = dict(start_level=level, below=[(c, j) for (_, _, c, j) in be], above=[(c, j) for (_, _, c, j) in ab],
                           rank0=W.rank_of_level(level, t, iso))
            wk_snap = None
            if weekly is not None and sampled_dyn and si == 0:
                wk_snap = (t, [weekly.member_score(i, t) for i in range(len(weekly.members))],
                           weekly.standings(t, weekly_user, weekly_last_win or weekly.t0))
            # play
            while t < s_end:
                refill(t)
                if lives <= 0 and t >= inf_until:
                    break
                hard = is_hard(level); sup = is_super(level)
                med = 95 if not (hard or sup) else (150 if hard else 185)
                d = med * math.exp(rng.gauss(0, 0.35))
                if level == 1:
                    d = 30
                t += d
                p = prof['first'] if not (hard or sup) else prof['hard_first']
                if not first_try_level:
                    p = min(0.97, p + 0.1)
                if rng.random() < p:
                    lw = level
                    wins.append((t, lw, first_try_level))
                    pts = streak.win()
                    level = 5 if level == 1 else level + 1
                    if streak_race is not None and t < streak_race.end:
                        streak_user += pts; streak_last = t
                    if level - 1 >= E.UNLOCK['weekly'] or lw >= E.UNLOCK['weekly']:
                        w = K.event_week(t)
                        if weekly is not None and w != weekly_w:
                            settle_weekly(t)
                        if weekly is None and lw >= E.UNLOCK['weekly']:
                            daily_ref, spw, weekly_ref = E.user_pace(wins, t)
                            weekly = E.WeeklyContest(W, install_seed, w, t, weekly_ref, play_windows)
                            weekly_w = w; weekly_user = 0
                        if weekly is not None:
                            weekly_user += 1; weekly_last_win = t
                    if rocket is not None:
                        rocket_times.append(t)
                        rocket_check(t)
                    if sky is not None:
                        if first_try_level:
                            sky_step += 1
                            if sky_step >= sky.N:
                                sky_results.append(dict(stage=sky_stage, result='win', winners=sky.alive[-1],
                                                        share=sky.share))
                                if sky_stage < 3:
                                    sky_stage += 1
                                else:
                                    sky_stage = 1; sky_cool = K.event_day_start(K.event_day(t) + 1)
                                sky = None
                        else:
                            pass
                    first_try_level = True
                else:
                    fails += 1
                    first_try_level = False
                    streak.fail()
                    if t >= inf_until:
                        lives -= 1
                        if life_clock is None:
                            life_clock = t + 1200
                    if sky is not None:
                        sky_results.append(dict(stage=sky_stage, result='lose', step=sky_step, alive=sky.alive[sky_step]))
                        sky = None; sky_stage = 1; sky_cool = t + E.SKY_RETRY_COOLDOWN
                if sky is not None and t - sky_t0 > 86400:
                    sky_results.append(dict(stage=sky_stage, result='expired', step=sky_step))
                    sky = None; sky_stage = 1
            # session end
            if dyn is not None:
                ab2, be2 = W.neighbours(level, t, 6, 6, iso)
                rows = [W.row(c, j, t) for (_, _, c, j) in ab2 + be2]
                show_rows(rows, t)
                # rivals that were BELOW the user at the start and are ABOVE the user's (new) level now
                overtook = sum(1 for (c, j) in dyn['below'] if W.level(c, j, t) > level)
                moved = sum(1 for (c, j) in dyn['below'] + dyn['above'] if W.level(c, j, t) > W.level(c, j, s0))
                r1 = W.rank_of_level(level, t, iso)
                dynamics.append(dict(minutes=round((t - s0) / 60, 1), levels=level - dyn['start_level'],
                                     rank_gain=dyn['rank0'] - r1, overtaken_by=overtook, neighbours_moved=moved))
            if wk_snap is not None and weekly is not None and t < weekly.we:
                t_a, sc_a, st_a = wk_snap
                sc_b = [weekly.member_score(i, t) for i in range(len(weekly.members))]
                st_b = weekly.standings(t, weekly_user, weekly_last_win or weekly.t0)
                pos_a = {x[2]: k for k, x in enumerate(st_a)}; pos_b = {x[2]: k for k, x in enumerate(st_b)}
                changed = sum(1 for i in range(len(sc_a)) if sc_a[i] is not None and sc_b[i] is not None and sc_b[i] > sc_a[i])
                arrived = sum(1 for i in range(len(sc_a)) if sc_a[i] is None and sc_b[i] is not None)
                passed_user = sum(1 for i in pos_a if i >= 0 and i in pos_b and pos_a[i] > pos_a[-1] and pos_b[i] < pos_b[-1])
                weekly_dyn.append(dict(minutes=round((t - t_a) / 60, 1), members_scored=changed, arrived=arrived,
                                       passed_user=passed_user, user_rank_before=pos_a[-1] + 1, user_rank_after=pos_b[-1] + 1))
            if t > s0:
                play_windows.append((s0, t)); play_windows[:] = play_windows[-10:]
            if si == len(sessions) - 1:
                ab3, be3 = W.neighbours(level, t, 10, 10, iso)
                last_view = (t, level, [(c, j) for (_, _, c, j) in be3], [(c, j) for (_, _, c, j) in ab3 + be3])
        # end of day snapshot
        t_day_end = day_start_local + 86399
        settle_weekly(t_day_end); settle_streak(t_day_end); rocket_check(t_day_end)
        t0q = time.time(); wr = W.rank_of_level(level, t_day_end); timing['world_rank'].append(time.time() - t0q)
        t0q = time.time(); cr = W.rank_of_level(level, t_day_end, iso); timing['country_rank'].append(time.time() - t0q)
        if cr > wr:
            checks['rank_inconsistent'] += 1
        ranks.append((t_day_end, level, wr, cr))
        if di % 28 == 0:
            t0q = time.time(); tp = W.top(t_day_end, 100); timing['top100'].append(time.time() - t0q)
            ids = [g for (_, g, _, _) in tp]
            if top_prev is not None:
                top_churn.append(dict(days=28, new_entries=len(set(ids) - set(top_prev)),
                                      same_rank=sum(1 for a2, b2 in zip(ids, top_prev) if a2 == b2),
                                      top1=W.row(tp[0][2], tp[0][3], t_day_end)['name'], top1_level=W.row(tp[0][2], tp[0][3], t_day_end)['level'],
                                      l100=W.row(tp[-1][2], tp[-1][3], t_day_end)['level']))
            top_prev = ids
            show_rows([W.row(c, j, t_day_end) for (_, _, c, j) in tp], t_day_end)
            tpc = W.top(t_day_end, 100, iso)
            show_rows([W.row(c, j, t_day_end) for (_, _, c, j) in tpc], t_day_end)
        if di % 7 == 6:
            print('%s day %d level %d world %d country %d (%.0fs)' % (a.profile, di + 1, level, wr, cr,
                                                                    time.time() - t_start), flush=True)

    # summaries
    def rate(lst, key, val):
        return round(sum(1 for x in lst if x[key] == val) / len(lst), 3) if lst else None
    summ = dict(
        profile=a.profile, weeks=a.weeks, install=a.install, final_level=level, wins=len(wins), fails=fails,
        world_rank_final=ranks[-1][2], country_rank_final=ranks[-1][3], population_final=W.gid_limit(ranks[-1][0]),
        weekly=dict(n=len(weekly_results), win=rate(weekly_results, 'rank', 1),
                    podium=round(sum(1 for x in weekly_results if x['rank'] <= 3) / len(weekly_results), 3) if weekly_results else None,
                    median_rank=sorted(x['rank'] for x in weekly_results)[len(weekly_results) // 2] if weekly_results else None),
        streak_race=dict(n=len(streak_results), first=rate(streak_results, 'rank', 1),
                         top3=round(sum(1 for x in streak_results if x['rank'] <= 3) / len(streak_results), 3) if streak_results else None,
                         median_rank=sorted(x['rank'] for x in streak_results)[len(streak_results) // 2] if streak_results else None,
                         coins_per_day=round(sum(x['prize'] for x in streak_results) / max(1, len(streak_results)), 1)),
        rocket=dict(n=len(rocket_results), by_stage={s: dict(n=sum(1 for x in rocket_results if x['stage'] == s),
                                                              win=round(sum(1 for x in rocket_results if x['stage'] == s and x['result'] == 'win') /
                                                                        max(1, sum(1 for x in rocket_results if x['stage'] == s)), 3))
                                                      for s in (1, 2, 3)}),
        sky=dict(n=len(sky_results), wins=sum(1 for x in sky_results if x['result'] == 'win'),
                 mean_share=round(sum(x['share'] for x in sky_results if x['result'] == 'win') /
                                  max(1, sum(1 for x in sky_results if x['result'] == 'win')), 1)),
        dynamics=dict(n=len(dynamics),
                      sessions_overtaken_by_someone=round(sum(1 for d in dynamics if d['overtaken_by'] > 0) / max(1, len(dynamics)), 3),
                      mean_neighbours_moved=round(sum(d['neighbours_moved'] for d in dynamics) / max(1, len(dynamics)), 2),
                      mean_rank_gain=round(sum(d['rank_gain'] for d in dynamics) / max(1, len(dynamics)), 1)),
        idle=dict(n=len(idle),
                  returns_with_someone_passing=round(sum(1 for d in idle if d['passed_user'] > 0) / max(1, len(idle)), 3),
                  mean_passed=round(sum(d['passed_user'] for d in idle) / max(1, len(idle)), 2),
                  mean_window_moved=round(sum(d['window_moved'] for d in idle) / max(1, len(idle)), 2)),
        top100_churn_per_4w=top_churn[-6:],
        weekly_session=dict(n=len(weekly_dyn),
                            with_members_scoring=round(sum(1 for d in weekly_dyn if d['members_scored'] > 0) / max(1, len(weekly_dyn)), 3),
                            mean_members_scoring=round(sum(d['members_scored'] for d in weekly_dyn) / max(1, len(weekly_dyn)), 2),
                            someone_passed_user=round(sum(1 for d in weekly_dyn if d['passed_user'] > 0) / max(1, len(weekly_dyn)), 3)),
        checks=checks,
        timing_ms={k: (round(1000 * sorted(v)[len(v) // 2], 1), round(1000 * max(v), 1)) for k, v in timing.items() if v},
        runtime_s=round(time.time() - t_start, 1),
    )
    out = dict(summary=summ, ranks=ranks[::7], weekly=weekly_results, streak=streak_results[-60:],
               rocket=rocket_results, sky=sky_results, dynamics=dynamics, idle=idle[-80:], weekly_dyn=weekly_dyn)
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, a.profile + '.json'), 'w') as f:
        json.dump(out, f, indent=1)
    print(json.dumps(summ, indent=1))

if __name__ == '__main__':
    main()
