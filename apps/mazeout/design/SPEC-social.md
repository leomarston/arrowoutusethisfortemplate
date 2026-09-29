# SPEC-social — Arrow Out's offline "online" world

Owner, 02:33 (verbatim): *"For the online features, like leaderboard … we dont do online features. But we can simulate it, for the
users country, the global etc. there will be many logical mock nicknames and they will have points, and there will be a real like
leaderboard race, there should be many many users just like it is online, and they should be getting points etc. Like think that we
are simulating online here, but since the user downloads this once and we dont touch it again possbily, the system should be a
really good offline simulation of the online system."*

Author: social-sim designer, 2026-09-25. Status: complete design + a working, tested Python reference implementation.
**Aligned 2026-09-25 by SOC1 (CONSISTENCY §21.19): the build's rulings and the shipped phone calibration are in §13 and win over the
stale values marked "→ §13" below. The reference values stay as written: they are pinned bit for bit as the `reference` model.**
**Recalibrated 2026-09-25 by SOC1b to phone session 2 (research/social-dynamics.md): §14 wins over §13 where they differ (names,
Weekly/Streak/Rocket/Sky shapes, the honeymoon, Turkey). The shipped parameter set now lives in the Python reference itself:
`design/social/tools/socialsim/shipped.py`.**
**SOC1c (2026-09-25, orchestrator): the shipped world DRAWS nicknames with replacement — duplicates allowed like the original's two
"Bobby" — and Sky Jump stage 3 = the phone's 10 levels / 10000 from social.json; its per-cohort style counts are apportioned
systematically (§15.1; the old rounding over-weighted the last style, 'leet', in the small cohorts the World top is made of)
(§15 wins over §14 and §2.8 / §4.6 for the shipped model; the reference keeps its unique first-come names, its rounding and 5/7/9).**
The Swift port lives in `Packages/PathCore/Sources/PathCore/Social/` and must reproduce the reference bit for bit (§8).

| Reference file | What it is |
|---|---|
| `design/social/tools/socialsim/core.py` | hashing (SplitMix64 + FNV-1a, the `tools/rng_ref.py` primitives), keyed permutations, calendar |
| `design/social/tools/socialsim/data.py` + `design/social/data/*` | world constants, countries, archetypes, name data (see `design/social/SOURCES.md`) |
| `design/social/tools/socialsim/names.py` | nickname generator + blocklist |
| `design/social/tools/socialsim/population.py` | the simulated world: cohorts, activity, levels, leaderboard queries |
| `design/social/tools/socialsim/events.py` | Weekly Contest, Streak Race, Rocket Race, Sky Jump, win-streak multiplier, Claw points |
| `design/social/tools/tests.py` | 18 property tests (all pass) — the Swift `SocialPropertyTests` port them 1:1 |
| `design/social/tools/make_fixtures.py` → `design/social/fixtures/*.json` | golden vectors the Swift `SocialGoldenTests` pin |
| `design/social/tools/bench.py` → `design/social/bench/{active,casual,absent}.json` | the 52-week plausibility bench (§9) |
| `design/social/tools/name_audit.py`, `calibrate.py`, `sample_names.py` | uniqueness audit, calibration numbers, the 200-name sample |
| `design/social/data/social_names.json` | the ONE shipped name resource (0.5 MB), built by `tools/build_name_data.py` |

**How to read this.** VERIFIED = seen on the owner's phone (v552, `research/shots/NNN`), in the owner's videos, or on the store page.
INFERRED = reasoned from several signals. DECISION = ours, made where the evidence is silent; every DECISION is a tunable and is
listed again in §12. Where the phone and the videos differ, the phone wins (owner 02:55).

---

## 0. The five rules of the simulation

1. **One shared world.** Every simulated player is derived from a single constant `WORLD_SEED`, never from the install. Two friends
   comparing phones at the same moment see the **same** World board and the same Country board (only their own row differs). The
   install seed only drives the user's own event groups and rivals (online, those differ per player too).
2. **Nothing about the world is stored.** A player is `(cohort, index)`; every attribute (nickname, avatar, country, level at time t)
   is a pure function of `WORLD_SEED` and t. The app stores only the user's own facts (§6).
3. **Monotone in time.** Every number the UI shows about another player (level, weekly score, streak points, race progress, "Players"
   left in Sky Jump) is non-decreasing in simulated time, and simulated time never goes backwards (§5). So nothing ever jumps back.
4. **Exact and cheap.** Ranks are exact counts over hundreds of thousands to millions of players, computed in O(cohorts · log n)
   (a few milliseconds in Swift), never O(players). Two implementations (Python, Swift) agree bit for bit.
5. **Plausible, winnable, alive.** Calibrated to the original's numbers where they exist (§2.9); events are winnable by an active
   player and lost sometimes (§9); players move while the user is away and during the user's sessions in the contests (§9).

---

## 1. Evidence — what the original shows

### 1.1 Screens and data (all references are LOOK-ONLY evidence, never shipped)

| Feature | What we know | Source | Tag |
|---|---|---|---|
| Leaderboard tabs | "Leaderboard" title; tabs **Weekly · World · <country name>** (phone: "Turkey"; V2 skin: "Country"); Weekly selected = green | phone `shots/132`, V2 29-34 s (`video-frames/tutor/full/V2_t0029.50/31.50/33.50.png`) | VERIFIED |
| Weekly locked | centred "Reach level 50 / to compete in / Weekly Contest!" before L50 | V2 29.5 s; web (June build said 28) | VERIFIED |
| Weekly unlock | first Play tap on the LEVEL 50 home is intercepted: dim, cream card "Tap to compete in Weekly Contest!", yellow arrow down at the trophy tab (only live target) → intro page "Weekly Contest / Beat Levels! / Contest with others! / Win Rewards! / Compete against your friends! There is a new contest every week! / Tap to Continue" → the Weekly board | phone `shots/130-133` | VERIFIED |
| Weekly board | stopwatch countdown under the tab ("3d 6h" at Fri 00:06 UTC → ends **Mon 07:00 UTC**), banner "Weekly Contest" + (i), podium 1st centre gold **2000** coins, 2nd left lilac **1000**, 3rd right orange **500**, each "Score : n"; below, cream rows `rank · avatar · name · Score n`; the user's row GREEN; at the moment the user joined the list ended at the user (rank 10, score 0; ranks 7-9 had 1, 1, 0; podium 4, 4, 3) | phone `shots/132` | VERIFIED (group size UNKNOWN: ≥ 10) |
| Weekly tie order | equal scores: alphabetical in both the phone and July boards, but also consistent with "earlier first"; the user who just joined is last among 0-score rows | `shots/132`, `web/yt_frames/gamemobie_L50_leaderboard-weekly.jpg` | INFERRED |
| World board | ranked by **level**; rows `rank (1-3 star badges gold/silver/bronze) · avatar · name · "Level" n`; 30 Jul 2026 (day 94 after the 27 Apr launch): **11635, 10040, 9120, 9051, 8795, 8443, 8135, 8122**; opens at the top | V2 31.5 s | VERIFIED |
| Country board | the player's country, opens **auto-scrolled to the player's green row**, floating translucent "Top" pill (jumps to rank 1); Vietnam, player at L11 = **rank 132**; ranks 127-135 span levels 14 → 11; the player is FIRST among its level-11 group; all default names at those levels | V2 33.5 s | VERIFIED |
| Names | default `player_` + 7 of [a-z0-9] (player_fiv0pqv, player_3km8b0d …); chosen names: Tetety, Bobby, Alex56k, Stacx251, Ptr, Longy, Limminator, SneakySnakeGal, SneakyFalconer51, Grib, Hihi, Boo, Mema, Ttam, Guy, muffinman, DSMShark, Nope, lady, Mas, karl, Gatorgirl, Ceb, GOLDEN; marketing: Kate, Max, James, Neo | V2, phone `132/167/203`, store `iphone-6`, `web/yt_frames` | VERIFIED |
| Avatars | a grey default silhouette + character portraits (v552: the capsule workers / monster; V2 skin: 3×3 arrow mascots). About a third of named players show a portrait | V2 50-70 s, phone `067/094/167/203` | VERIFIED |
| Profile | tap the home avatar → "Profile" (avatar with pencil, name, purple "Level n" pennant, "General Stats": **First Try Wins**, **Weekly Contest Wins** "-"); first open with no username → "Enter Username / Create your username: / Continue / X" (not forced); pencil → "Edit Profile" (name field + 3×3 avatar grid + "Save") | V2 50-70 s | VERIFIED |
| Streak Race | chips **x1 x5 x10 x25 x100**; a win lights the next chip, a failed level resets to x1; banner under every win/fail panel with a countdown to **07:00 UTC**; the list popup auto-shows (also once over an idle home); rows `rank hexagon (2 silver, 3 bronze, 4+ plain) · avatar · name · coin prize plate · green token score`, the player's row green, auto-scrolled to it; 25 Sep 04:24 TRT: #2 Mas **1000** coins 3423, #3 karl **500** 2950, **#4 the player 100 · 2065**, #5 Gatorgirl 100 · 1882, #6 Ceb 100 · 1846 (more rows below and above) | phone `shots/020/015/203`, `levels.md`; store `iphone-6` (marketing 3000/2000/1000); `web/yt_frames/gamemobie_L76_*` (5 rows visible, all 0 at the start of a day) | VERIFIED (rank-1 prize and group size UNKNOWN) |
| Streak points | the player's 2065 = exactly the sum of the chip value **lit before** each win over the phone session (1824) + 241 = 1+5+10+25+100+100 (six wins before the session): points per win = the multiplier before the win | `levels.md` win log vs `shots/203` | INFERRED (strong) |
| Claw Challenge | weekly (ends Mon 07:00 UTC); "Beat levels without fail to get more rewards!"; points per win = the current multiplier (bar deltas +1 +5 +10 +25 +100); ladder of 20 steps, thresholds seen **1, 200, 300, 400, 300, 500**; rewards seen 1 ∞30m, 2 100 coins, 3 ∞30m, 4 200 coins, 5 ∞1h, 6 bulb×1 (bar later showed 300 coins), 17 bulb×1, 18 600, 19 ∞6h, 20 10000; fail text becomes "You will lose 100 token and your streak!" | phone `021-025, 033-035, 060, 100-101, 113, 172-173, 204` | VERIFIED (steps 7-16 UNKNOWN) |
| Sky Jump | offer popup ("PRIZE 5000", Stage 1/2/3 chests, "Pass 5 Levels in a row on first try and advance to next stages!", Start, countdown to 07:00 UTC) → "Finding players on your level." 29/100 → 100/100 with a fan of portraits → tutorial ("Start with 100 players!", "Beat 5 levels!", "Win your share of 5000 coins!", "Advance to next stages for greater prizes!", red "If you fail a level, you will fail the challenge!") → map (pads 1-4 + prize island; "Stages", "Levels 0/5", "Players 100/100", **23h 58m** = 24 h from joining). After each first-try win: Players **100 → 82 → 64 → (?) → 47** → win: "You are sharing the reward with **6 other winners**!" **714** = 5000 / 7. Stage 2: **7 levels, PRIZE 7000** | phone `065-070, 074-096` | VERIFIED |
| Rocket Race | offer popup ("500 + ∞45m" bubble, Stage 1/2/3 planets, "Beat 5 Levels before others to win and advance to next stages for greater prizes!", "Start ∞", countdown to 07:00 UTC) → claim **∞30m** for joining → first-time tutorial → race screen (5 lanes, rockets + counters, name tiles, the player's green, rank badge "1") → win-panel strip `rank · avatar · name · n/5` (replaces the Streak Race strip while racing). Rivals move on their own clock: joined 03:43; 7 min later 4/5, 3/5, 3/5, 0/5 (player 1/5); 12 min: 4, 4, 3, 0; 14 min 4, 4, 3, 0 (player 2); **DSMShark finished 15-20 min after the join** → "You lost the race! Try again to win amazing rewards!" + Continue; "Join" badge at once, re-offer 6 min later. muffinman sat at 4/5 from ≤ 8 min until the race ended | phone `163-168, 171, 176, 178, 183-184, 189` | VERIFIED |
| Online-ness | the original's privacy policy mentions leaderboards and AWS; our game has **no network**: everything below is offline | `web-research.md` §1, §9 | — |

### 1.2 The event clock (VERIFIED from 12 countdowns on one Turkish device)

Every daily countdown ends at **10:00 TRT = 07:00 UTC**; every weekly one at **Monday 07:00 UTC**:

| Local time (TRT) | Screen | Countdown | → end |
|---|---|---|---|
| Fri 00:09 | home Streak badge | 9h 50m | 09:59–10:00 |
| 00:50:44 | win panel Streak strip | 9h 9m | 09:59:44 |
| 00:51:36 | Claw Challenge | 3d 9h | Mon 09:51–10:51 |
| 01:45:33 | Sky Jump offer | 8h 14m | 09:59:33 |
| 01:47:23 | Sky Jump map (joined) | 23h 58m | join + 24 h |
| 02:17 | Sky Jump stage-2 offer | 7h 42m | 09:59 |
| 03:06:30 | Weekly board | 3d 6h | Mon 09:06–10:06 |
| 03:39:53 | Rocket offer | 6h 20m | 09:59:53 |
| 03:45:13 | Rocket race | 6h 14m | 09:59:13 |
| 04:07:32 | Rocket re-offer | 5h 52m | 09:59:32 |
| 04:23:47 | Streak Race list | 5h 36m | 09:59:47 |

One timezone cannot tell "07:00 UTC" from "10:00 local"; we anchor to **UTC** (a global contest ends for everyone at once, which is how
a real server behaves). DECISION `eventDayAnchor = 07:00 UTC`, `eventWeekAnchor = Monday 07:00 UTC`.

### 1.3 Unlock levels (first appearance on the phone; the videos, older builds, show no events at all through V1 L21 / V2 L39)

| Feature | Phone | Ours | Tag |
|---|---|---|---|
| Streak Race | already live at L32 (x1 chip at the first fail) | reach **L30** | DECISION (evidence: > 21 in the Aug build, ≤ 32 in v552) |
| Claw Challenge | intro right after the L32 win | reach **L33** (shown after the L32 win) | VERIFIED first appearance (could be a release-day coincidence) |
| Sky Jump | "Join" after the L39 win | reach **L40** | VERIFIED |
| Weekly Contest | reach L50 | reach **L50** | VERIFIED (V2 text + phone) |
| Rocket Race | offer after the L54 win | reach **L55** | VERIFIED |

---

## 2. The simulated world

### 2.1 Time and size

- **World epoch** `EPOCH = 2026-04-27 07:00:00 UTC` (a Monday; the original's launch day, aligned to the event anchor).
- **Join periods** `p = floor((t − EPOCH) / 7 days)`. New players per period (closed form, IEEE-exact):
  `J(p) = 12000·(1 + 0.6·p/(p+40)) + 18000·(2/(2+p))²` — a launch bump, then a slowly growing plateau capped near 19,200/week.
- Resulting world (calibration, `bench/calibration.json`): **331k** players on 25 Sep 2026, 373k on 15 Oct 2026, 803k on 27 Apr 2027,
  **1.16 M** on 25 Sep 2027, 2.05 M on 25 Sep 2028, 4.9 M in 2031. The world keeps growing for as long as the app runs.

### 2.2 Cohorts (the unit of the model)

A cohort is `(period p, timezone bucket b, archetype a[, join day d])`:
- tourists get one cohort per join **day** (`d = 0…6`), every other archetype one per join **week**;
- order (fixed forever, defines player ids and name slots): `for p ↑: for b in BUCKETS: [weekly archetypes in table order], then
  for d in 0…6: [daily archetypes]`; key `ck = ((p·16 + b)·16 + a)·8 + (d+1)` (d = −1 for weekly cohorts);
- size `n = floor(J(p) · share(b) · share(a) [/ 7 for daily] + u01(WS,"cn",ck))` (unbiased dithered rounding);
- **country** = one row of the bucket, picked with `u01(WS,"ccountry",ck) · Σweights` (so a cohort is e.g. "casual Brazilians who
  joined in week 12"); the row gives the UTC offset (diurnal rhythm) and the name culture;
- per-cohort constants from hashes: `v` (quantile offset), `pace` ∈ [0.40, 0.65] levels/min, the 28-day volume pattern, lapsed
  pattern, returners' comeback time `R`.
- `gid0` = the running sum of `n` over earlier cohorts → a player's global id `gid = gid0 + j`. ~2.6k cohorts in Sep 2026, 8.7k after
  one more year, 33k after five.

### 2.3 Countries and timezone buckets (`data/countries.tsv`, DECISION)

US-heavy, then the Anglosphere, Western Europe, Brazil/LatAm, Turkey, Asia — a casual English-language puzzle game (the original's
ratings: US 1,435 vs TR 30; reviews US > CA > AU > GB > TR > DE > BR). Weights (relative): US 30 (21 east/central at UTC−5, 9 west at
−8), GB 7, CA 5, DE 4.5, AU 4.5, BR 4, FR 3.5, MX 2.5, ES 2, IT 2, TR 2 (shipped 0.5 → §13), IN 2, PH 2, NL 1.5, PL 1.5, ID 1.5, JP 1.5, SE 1, AR 1, KR 1,
then 0.3–0.8 each for IE, PT, AT, CH, BE, NO, DK, FI, CZ, HU, RO, GR, UA, IL, EG, ZA, RU, SA, AE, CO, PE, CL, TH, VN, MY, SG, TW, HK, NZ.
Buckets: AMER_W, AMER_E, AMER_S, EUR_W, EUR_C, EUR_E, ASIA_S, ASIA_SE, ASIA_E.

**The user's country** = `Locale.current.region` at first launch (fallback US), stored forever (`homeCountry`, like an account's
registration country). If it is in the table, its players are the shared world's (e.g. TR: 7.0k players on 25 Sep 2026, 22.7k a year
later). If it is **not** in the table (e.g. Iceland), a device-only **LOCAL** partition is added: +0.3 % of the world with that country,
the device's UTC offset and a culture from `EXTRA_CULTURE` (default `en`); its ids live at `2^40+` and its name slots in a separate
namespace, so the shared world stays byte-identical (test 10).

### 2.4 Archetypes (`data.py ARCHETYPES`, DECISION calibrated in §2.9)

| key | share | levels per played day λ(u) | active life (days) | play days ρ | sessions/day | install session | lapse after quitting | custom name | portrait (default/custom name) |
|---|---|---|---|---|---|---|---|---|---|
| tourist | 40.0 % | 4 → 20 | 0.005 → 1.2 | 1.00 | 1–2 | 2 → 12 levels | — | 15 % | 8 % / 38 % |
| dabbler | 22.0 % | 6 → 30 | 1.5 → 12 | 0.55 | 1–2 | 5 → 14 | 20 → 90 d | 30 % | 10 % / 42 % |
| casual | 18.0 % | 5 → 10 (u .6) → 18 (.9) → 25 | 12 → 35 (.5) → 90 | 0.45 | 1–2 | 6 → 14 | 45 → 200 d | 45 % | 12 % / 45 % |
| regular | 11.0 % | 10 → 18 (.5) → 32 (.9) → 45 | 40 → 140 → 420 | 0.70 | 1–3 | 6 → 14 | 60 → 365 d | 60 % | 12 % / 47 % |
| enthusiast | 4.5 % | 20 → 35 → 58 → 75 | 150 → 500 → 1600 | 0.88 | 2–4 | 8 → 16 | 90 → 500 d | 72 % | 14 % / 50 % |
| grinder | 0.6 % | 42 → 60 (.5) → 79 (.9) → 93 (.98) → 128 | 250 → 900 → 3200 | 0.97 | 3–6 | 8 → 16 | 90 → 500 d | 86 % | 15 % / 55 % |
| returner | 3.9 % | 8 → 40 | 3 → 32, gap 15–150 d (per cohort), then 30 → 500 | 0.55 | 1–2 | 6 → 14 | 30 → 120 d | 45 % | 12 % / 45 % |

(`a → b (u) → c` = a piecewise-linear table over the member quantile u ∈ [0,1].)

### 2.5 Members

Member `j` of cohort `c` sits at quantile `u = (j + v_c) / n_c`. With `span` = 1 day (daily cohorts) or 7 days:
- `λ(u)` from the table; join `J(u) = join0 − u·span` (higher u joined earlier); `T1(u) = J(u) + life(u)·1 day`;
  `F(u) = first_lo + (first_hi − first_lo)·u` install-session levels; returners: `T2(u) = R_c + life2(u)`;
  lapse end `LE(u) = T1(u) + lapse(u)` (capped at `R_c` for returners).
- **Containment condition** (checked by an assert at build time): every `life` table rises at least `span` per unit of u, so a
  higher-u member's active interval contains every lower-u member's. With λ, F, lapse all rising in u, **level(u, t) is
  non-decreasing in u at every t** (tests 2, 3). That single property makes every query below a binary search.

### 2.6 Activity (IEEE-exact; `population.py`)

- **Volume pattern.** 28 days (a multiple of 7, weekday-aligned): day i is played if `u01(WS,"play",ck,i) < ρ`; volume
  `v_i = 0.55 + 0.90·u01(WS,"vol",ck,i)` × weekday factor (Mon…Sun 0.92 0.90 0.92 0.95 1.02 1.22 1.18); normalised so the mean over
  played days is 1 (λ is "levels per played day"). Prefix sums `pre[0…28]`, `T = pre[28]`.
  `C(dl) = floor(dl/28)·T + pre[dl mod 28]` = volume before local day `dl` (days since `BASE_DAY = 20552`, a multiple of 28).
- **Lapsed pattern.** After quitting, a member still comes back on ~16 % of the cohort's play days at half volume
  (`ml_i = 0.5·m_i` when `u01(WS,"lapse",ck,i) < 0.16`), until `LE(u)`.
- **Sessions of a cohort-day** (shared by the cohort; "they play at the same hours"): k sessions (archetype range, `below(WS,"sk",…)`);
  starts drawn from the local-hour density (weekday / weekend tables, 24 bins, inverse CDF with linear interpolation inside the hour);
  sorted; fractions `f_j ∝ 0.5 + u01`; the longest member (u = 1) needs `Q/pace` minutes, `Q = λmax·m`; if that exceeds 1,200 min
  the day's pace is raised to `Q/1200`; window lengths `L_j = f_j·Q/pace`; a forward pass keeps 10 min gaps, a backward pass keeps
  every window inside 00:00–23:59 (test 5).
- **A member inside a session** plays at the cohort's human pace (a level every 1.5–2.5 min) until it has played its share
  `f_j·λ(u)·m`: `gain(τ) = Σ_j min(pace·max(0, τ − s_j), f_j·λ(u)·m)`. Low-λ members stop early, heavy ones play the whole window.
- `lcum(u, t) = λ(u)·C(dl) + gain(minute of t)` (and the same over the lapsed pattern). Continuous across midnight (test 4).

### 2.7 Level

```
P(u,t) = min(0.55 · (min(t,T1) − J)/60, F(u))                       install session (FTUE boards are quick)
       + lcum(u, min(t,T1)) − lcum(u, J)                            active life
       + lcumLapsed(u, min(t,LE)) − lcumLapsed(u, T1)   if t > T1    lapsed come-backs
       + lcum(u, min(t,T2)) − lcum(u, R)                if t > R     returners
level = 1 + floor(P)          (0 = not joined yet, t < J)
```
`P` (continuous progress) is also the sort key: equal levels are ordered by P (closer to the next level first).

### 2.8 Nicknames (`names.py`, `data/social_names.json`)

- **Styles** (share among players who set a name; the others keep `player_` + 7 chars, like the original's low levels):
  given name 34 % (`Kate`, `Mehmet`, rounds ≥ 1 add a number: `Kate23`), compound 19 % (`SneakyFalcon`), invented handle 14 %
  (`Tetety`-like: `Snyty`, `Breymyn`, reversed `Ttam`, devowelled `Ptr`), underscore 10 % (`kate_m`, `mehmet_games`), plain word 7 %
  (`muffinman`, `nope`, `Lady`), mixed 7 % (`Limminator`-like: `Jordaninator`, `Seulgizilla`), initials 5 % (`DSMShark`-like:
  `HDMTrout`), caps 4 % (`GOLDEN`, `TURBO8`). Given names follow the cohort's culture (16 cultures; native spelling ~70 %, ASCII
  ~30 %, lowercase ~20 %).
- **First come, first served.** Each (style, culture) has a dense slot counter handed out in cohort order: early players get the
  plain names, later ones the decorated variants — exactly how real unique usernames age. `decode(style, slot, culture)` is a keyed
  bijection per round, all token sets are disjoint by case- and accent-insensitive key, so **no two players in the world share a
  nickname**: audited over the whole world to **2031-09-25 — 4.9 M players, 0 duplicates** (`bench/name_audit_*.json`).
  → **the REFERENCE only.** The SHIPPED world (SOC1c, §15) draws custom names with replacement by the player's gid (names repeat
  like the original's two "Bobby"; identity is the gid, never the name); `player_` defaults stay one bijection (below).
- **Blocklist**: profanity/slur stems (EN TR DE FR ES PT IT NL; substring list + whole-token list; leet folded 0→o 1→i 3→e 4→a 5→s
  7→t 8→b), celebrity-evoking names, brands, platform and acronym names (NHL, KFC …), the original's and publisher's names. Tokens are
  split at `_`, digits, CamelCase and acronym runs (`NHLKitten` → nhl, kitten). A blocked result (0.3 %, nearly all random `player_`
  strings) is replaced by a fallback `player_` name.
- **Every `player_xxxxxxx` is one bijection.** `defaultName(slot) = "player_" + base36₇(perm(slot, 36⁷, h64(0x706C6179,"default",0)))`,
  with disjoint slot ranges: shared-world default slots count up from 0; LOCAL partition from 36⁷/2; the user's own name from 36⁷/4 +
  (`h64(installSeed,"username")` & (2³⁰−1)); blocklist fallbacks count DOWN from 36⁷−1 (`f = gid·8 + k`, k = re-try; LOCAL:
  `(gid−2⁴⁰)·8 + k + 2³¹`). LOCAL custom-style slots add 10⁹. (The first audit found exactly one collision — a salted fallback equal
  to a real default name — which is why fallbacks now live inside the same bijection.)
- **Avatar** (shipped: 0 + the 8 portraits, CONSISTENCY V-24 → §13): 0 = default silhouette, 1…14 = the portraits of `art/ID-MAP.md` §avatars (`avatarGreen … avatarWalkie`); probability by
  archetype and whether the player has a custom name (table §2.4); uniform over the 14.
- **The user**: until they pick a username, the `player_` name above; avatar 0. A chosen username: 3-16 characters, letters (any
  script the font covers), digits and `_`; trimmed; checked with the same blocklist (rejected with a shake + red field outline, NEW).
- **200 names as the owner will meet them** (every k-th named player of the world on 12 Oct 2026; 33 % of players have a custom name):

> Damix, Daryl, chica, BVZDolphin, Grahamking, TwistyTrout, José, QBGLeopard, Chaypyx, kasper_games, Sebastianninja, Snyty, Taivan,
> rawan_yt, MagicGardener, hana1, Marian, Spume, wilfredo_e, ElectricStorm, thiago7, Frounir, Wibyx, SturdyLollipop, Dimitra5,
> andi_k, robbin5, Gleyvuk, Maybe2, Jarvis4, SparklyCrow, Mitchelxo, Guillermoking, Katrineplays, xin1, Rivir, Thalia6, EmeraldBard,
> Ty1, Alonso8, Fenna7, PinkPixel, CalmTrout, doyun_t, Chaikex, CheekyBeetle, lucretia_c, elliot_p, WAFFLE5, sheri_u, Maibot,
> Austin2, MaroonDonut, Mommy13, Luiz3, Melanie8, HyperStar, ramesh2, Seulgizilla, wanderlust91, Raúl3, Jason6, Jeedek, ToastyBreeze,
> Aleahlicious, WildParrot, Sleezin, Ryleigh9, Lionel1, Brice7, juliette_fun, Tuncay4, rowena62, Kiddo20, faith_gamer, cocoa71,
> Caio39, RoyalTulip, Arjen8, aiman82, SUPER4, javier_love, Shype, FancyLynx, emilee5, PluckyStar, Despina5, Rickey2, MerryTracker,
> Alonzo7, kia_real, rogerio65, Meety, dilara_life, Rodel80, roderick2, Jordaninator, DreamyToad, NocturnalMelon, Wojciech2,
> Clarapro, nurul_h, Seru, TealRock, Serenityinator, Óscar22, Shairar, Birgit24, Ghadabot, gameon38, AtomicLemur, Dupyx, HyperAcorn,
> SLY2, Iris50, Gunnar8, aisyah16, Kay6, Athena4, RogueGardener, TURBO8, Shaikus, fabian_games, NeonSloth, Hyejin2, JHBBanana, caren9,
> SnowyTinker, Klalor, Haten, nono46, Zaki, Jeepi, Pilar72, yippee32, Terrence1, Dominikmax, Maud90, Fitrixd, BPQPainter, jeannie_dad,
> Letitia1, Predyn, TidyLeopard, GleamingEmber, CobaltIsland, jenna9, Cori2, SpookyPainter, Gillian9, Linda4, Jan52, Sławomir4,
> dewi31, herbert_e, payton4, DZFBlizzard, wilbur4, misti_p, Federico6, Asya7, FancyFalconer, Maryann3, SwiftClimber, OrangeTrout,
> KindSpark, Moritzmaster, Oskar60, Nasserzilla, Kleylok, Chaim2, Maitox, marcus_p, Zzz44, FrostyTuna, will8, RQCLemur, Lakisha3,
> Arturo51, GNOME11, Vuvin, Letha4, Nicolas39, Mahmuttastic, Earlinezilla, Hazel7, Kennedy1, PGRWizardry, samuel73, amigo31, Snone,
> Speykox, Tom1, Stephanninja, matthew_f, SteadySpider, Trelox, Thijs55, SaltyCamel, Kristine85

Rendering note for the UI spec: names contain Latin-Extended letters (ş ğ ı İ ł ą é ü ó ñ ç …) — PCDisplay-Black (Nunito) covers
them; rows must shrink-to-fit up to 16 characters (`Sebastianninja`, `Serenityinator`).

### 2.9 Calibration (DECISION targets, `tools/calibrate.py`)

| Check | Original | Ours |
|---|---|---|
| World top 8 on 30 Jul 2026 (day 94; V2 = an older build — the phone's 25 Sep numbers win, → §13.1) | 11635, 10040, 9120, 9051, 8795, 8443, 8135, 8122 | **11825, 10611, 8768, 8747, 8661, 8500, 8229, 8217** |
| One default name inside the top 8 | player_ah8prp7 (#8) | player_e4zv2qe at #8 (12 Oct 2026 view) |
| Low-level rows are default names | all 9 Country rows at L11-14 | 83 % default at L11-14, 63 % at L50-70, 25 % at L1000+ (Sep 2026) |
| Level curve on day 94 (share of players ≥ L) | FTUE is fast: Levels 1-6 in ~75 s, L7-10 ~20 s each (V1) | ≥6 90 %, ≥11 82 %, ≥21 70 %, ≥51 50 %, ≥101 40 %, ≥501 13 %, ≥2001 2.6 %, ≥5001 0.2 % |
| World top-1 / #100 level | — | 18.8k / 10.4k (Sep 2026) · 64.5k / 39.2k (Sep 2027) · 110k / 70k (Sep 2028) |
| Where a L60 player ranks | Vietnam L11 = #132 (VN is small there) | Sep 2026: World #162k, US #53k, TR #3.1k; Sep 2027: World #588k, TR #10.8k |

---

## 3. Leaderboards

### 3.1 Metrics and order

| Tab | Value shown | Order | Who |
|---|---|---|---|
| **World** | current level (the level to play next, as the home LEVEL plate) | level ↓, then P ↓ | whole world + the user |
| **Country** | current level | same | players whose cohort country = `homeCountry` (+ LOCAL) + the user |
| **Weekly** | Score = levels won since joining this week's group | score ↓, then the moment the score was reached ↑ | the user's group (§4.3) |

The user leads its own level group in World/Country (V2 evidence): `rank = 1 + #players with level ≥ userLevel + 1`.
In Weekly the user is placed by the time its score was reached (last scoring win, or the join time) — so a user who just joined
sits last among the 0-score rows (phone evidence).

### 3.2 Queries (per-cohort binary search; the Swift algorithms = `population.py`)

- `countAtLeast(x, t, country?)`: for each cohort (country-filtered): top member level < x → 0; bottom member ≥ x → n; else a binary
  search for the first j with level ≥ x. Exact (test 6 = brute force).
- `rank(level, t, country?) = 1 + countAtLeast(level + 1)`.
- `top(k, t, country?)`: k-way merge — a heap of each cohort's top member keyed by P, pop and push the next lower member of the same
  cohort (test 7 = brute force). Ties in P → lower gid first.
- `neighbours(level, t, country?, above, below)`: per cohort the boundary index `b = first j with level ≥ level+1`; candidates above =
  `b, b+1, …` (smallest P first), below = `b−1, b−2, …` (largest P first); two heap merges. Rows above all have level > user, rows
  below ≤ user, and the row right above the user is exactly rank−1 (test 8).
- Materialise a row: `name(c,j)`, `avatar(c,j)`, `level(c,j,t)`, `gid`.
- Cost (Python reference, medians over the 52-week bench, world growing to 1.18 M players / 8.7k cohorts): world rank 59-134 ms,
  country 2-15 ms, neighbours 3-23 ms, top 100 19-29 ms. Compiled Swift is expected to be 30-60× faster (an estimate, not measured —
  `SocialBenchTests` measures it): budget on iPhone 15 **world rank ≤ 8 ms, top-100 ≤ 10 ms, country ≤ 2 ms, neighbours ≤ 3 ms** at a
  3-year world. All queries run off the main thread.

### 3.3 List composition and scrolling (DECISION where not captured)

- **World**: ranks 1…100; if the user is below 100: a thin "• • •" separator row, then ranks `R−10 … R+10` with the user's green row in
  the middle. Opens at the TOP (V2). A pinned mini-row of the user at the bottom is NOT in the original — don't add one.
- **Country** (shipped: continuous while `R ≤ 600`, → §13.3): if `R ≤ 300`, one continuous list 1…R+10; else 1…100, separator, `R−10…R+10`. Opens **auto-scrolled** so the user's row
  is centred, with the floating **"Top"** pill (tap → scroll to rank 1; the pill hides when rank 1 is visible). (V2)
- **Weekly**: podium (ranks 1-3) as a fixed header; list rows from rank 4 to the last arrived member; auto-scrolled to the user's row.
  Before L50: the lock text. At L50+ with no group yet this week: opening the tab forms the group (§4.3).
- Rank digits: up to 7 (`1,048,397` in 2028) — the UI spec sets a shrink rule; V2 shows plain numbers (no "#").
- Level digits: up to 6 (world top 110k in Sep 2028; ≈250k in 2031, extrapolated).

### 3.4 Live updates ("alive" without lying)

- While a leaderboard/event screen is visible, recompute every **5 s** in the background (cheap) and diff by player id: a row whose
  value rose animates its number (count-up 0.3 s) and, when the order changes, rows swap with a 0.35 s slide; the user's rank label
  counts to its new value. Nothing is animated backwards because nothing can go backwards (§0 rule 3).
- On (re)open, the list first shows the last cached result instantly, then the fresh one (≤ 1 frame later on device).
- Trophy-tab badge "!" (phone `shots/204` shows one; trigger UNKNOWN) — DECISION: shown when a weekly/streak result is claimable or
  when the user's Weekly rank dropped since the tab was last opened.

### 3.5 What the bench says about "alive" (§9)

Between two sessions, **75 % (active) / 92 % (casual)** of returns find at least one player who passed the user on the Country board,
and 5-10 of the 20 rows around the user moved. During a session the Weekly group scores move in **72 %** of an active user's sessions.
Players passing the user *during* a session is rare (0-1 %) — the user plays at a human pace like everyone else; the Rocket Race and
Streak Race are where the live duel happens (rivals move while you play, by design).

---

## 4. Events

### 4.1 Calendar (forever, no content updates needed)

`eventDay(t) = floor((t − EPOCH)/1 day)` (days start 07:00 UTC), `eventWeek(t) = floor((t − EPOCH)/7 days)` (Monday 07:00 UTC).
Every event runs **every day / every week forever** (the original rotates events by server config; with no server, a fixed
always-on schedule is the only honest offline equivalent — DECISION). Countdown text: `Xd Yh` above one day, else `Xh Ym`, floored
(matches every captured timer).

| Event | Period | Unlock | Instance id |
|---|---|---|---|
| Streak Race | event day | L30 | day index |
| Claw Challenge | event week | L33 | week index |
| Sky Jump | offer per event day; a run lasts 24 h from joining | L40 | attempt counter |
| Weekly Contest | event week | L50 | week index |
| Rocket Race | event day (a race ends at the day end at the latest) | L55 | race counter |

### 4.2 The win-streak multiplier (shared)

Steps x1 x5 x10 x25 x100 (index 0-4). A won level scores `STEPS[step]` points for the Streak Race and the Claw Challenge, then the step
advances (x100 stays). A **failed level** (the fail chain ends in "Level Failed", or Quit) resets to x1. Paying a continue (Play On /
Add Time) keeps the streak (that is what "You will lose your streak!" sells). One global value; persists across days.

### 4.3 Weekly Contest (group contest)

- **Joining.** At L50+, the group of week w forms at the first of: opening the Weekly tab, winning a level in week w. The very first
  time, the L50 forced tutorial precedes it (phone `130-133`).
- **Group** (shipped: 10 players, complete at the join, rivals online → §13.3). 50 players = the user + 49 World members picked by **stratified matchmaking** against the user's reference pace
  `ref = max(35, median levels won in the last 4 completed weeks)` (first week: 5 × the median daily count of the last 14 days; default
  15/day). Bands of r = member's expected weekly levels / ref:

  | count | r | note |
  |---|---|---|
  | 1 | 1.05 – 1.70 | the champion |
  | 5 | 0.92 – 1.18 | close rivals — preferably players who were playing during the user's last 3 sessions (same hours = visible duels) |
  | 8 | 0.70 – 0.92 | also prefer same-hours players |
  | 12 | 0.45 – 0.70 | |
  | 13 | 0.20 – 0.45 | |
  | 10 | 0.04 – 0.20 | mostly lapsed players who drop by |

  Candidates: `gid = below(S,"cand<slot>", gidLimit(t0), attempt)` for attempt = 0…5999 (`S = h64(installSeed,"weekly",w)`), eligible
  if joined, active or lapsed, level ≥ 50, r in band; fallback = any eligible player. `gidLimit(t)` counts only cohorts whose period
  started by t (independent of how far the table was built).
- **Arrivals.** 6-12 members (hash) are already in the group, arrived within the 6 h before the user (they already have a few points
  — the phone saw 4, 4, 3, …, 1, 1, 0); the others arrive `t0 + (weekEnd − 12 h − t0)·x²` (front-loaded): the list grows from ~10 rows
  to 50 over the first day or two, like a real bracket filling up.
- **Score.** Member: `level(t) − level(arrival)`; user: levels won since joining. Standings: score ↓, reach moment ↑ (member: bisection
  on its monotone score; user: last scoring win).
- **End.** Monday 07:00 UTC. Prizes **2000 / 1000 / 500** coins for ranks 1-3 (phone podium). Rank 1 → `weeklyContestWins += 1`.
  Result shown at the next home (§4.8).
- **Tuning result** (bench, 52 weeks): active user win 10 %, podium 43 %, median rank 4; casual win 6 %, podium 34 %, median 6;
  a user who plays one day a fortnight: podium 13 %, median rank 20.

### 4.4 Streak Race (group contest, daily)

- **Group** (shipped: 50 rows, members who play that day → §13.3): 20 players (DECISION; the phone list showed ranks 2-6 with rows above and below). Joined at the first home of the event day
  after L30, where the list auto-shows. Members: 19 World players by bands against the user's daily reference
  (`ref = max(8, median wins per active day over 14 days)`): (2, 1.15–2.0), (4, 0.9–1.15, same-hours), (5, 0.6–0.9, same-hours),
  (5, 0.3–0.6), (3, 0.08–0.3). A share of them equal to the elapsed fraction of the day have already arrived (with points — the
  phone at 18 h into the day saw 3423, 2950, …); the rest arrive during the day (front-loaded, until 2 h before the end).
- **Score**: each win adds the chip value lit before the win; members carry a start step (x1 50 %, x5 20 %, x10 12 %, x25 8 %, x100
  10 %) and fail before each win with their own probability 6-30 %. The user's score = its own chip values since joining.
- **Prizes**: rank 1 **2000** (INFERRED from the 1000/500/100 pattern), 2 **1000**, 3 **500**, 4-10 **100** (phone: 4-6 = 100; 7-10
  DECISION), 11-20 none (no plate).
- **Tuning result**: active: 1st 16 %, top-3 48 %, median rank 4, 632 coins/day; casual: 5 % / 34 %, 378 coins/day.
- Auto-show (phone saw the list pop over an idle home): at the first home of the day, and when the user's rank dropped since the last
  showing (at most once per 30 min, only on an idle home) — DECISION.

### 4.5 Rocket Race (live race, 5 lanes)

- **Offer** once per event day on home after L55 + "Join" badge; **Start** grants ∞ lives 30 min (claim popup). Stage s: beat
  **N = 5 / 7 / 9** levels (5 VERIFIED; 7, 9 DECISION mirroring Sky Jump); prizes **500 coins + ∞45m** (VERIFIED) / 1000 + ∞90m /
  2000 + ∞3h (DECISION). A win offers the next stage at once; stage 3 won → done until the next event day. A loss → "You lost the race!
  Try again to win amazing rewards!" → Continue; the badge says "Join" again immediately (phone re-offered 6 min later; no cooldown,
  no daily cap).
- **Rivals**: 4 World players picked at join t0 by role — 2 **hot** (≥ 2 levels in the next 20 min), 1 **warm** (none in 20 min, ≥ 2
  within 150 min), 1 **idle** (none in 3 h; the phone's "Nope 0/5"). Rival progress = its own World levels won since t0 (so it moves
  on its own clock, like the phone's rivals: 4/5 after 7 min).
- **Fairness gate** (rubber band): a rival that would reach N is held at N−1 until
  `max(naturalFinish, min(t0 + hold, userReachedNminus1 + δ))`, `hold` ∈ 14-40 min (phone: first finisher 15-20 min after the join),
  `δ` = 0.45-1.85 × the user's median seconds per win. A finish time never moves into the past (test 12).
- The race ends at the first finisher. Displayed per lane: `n/N` + a rank badge (progress ↓, then earlier reach); the leader gets the
  gold winged "1". The race also ends (no winner) at the day end.
- **Tuning result**: active user wins stage 1 **64 %**, stage 2 64 %, stage 3 54 %; casual 34 % / 11 % / 0 %; a rarely-playing user 50 %
  of the few races it starts.

### 4.6 Sky Jump (survival, 100 players)

- **Offer** per event day after L40 ("Join" badge), a run lasts **24 h** from Start. Stage s: **N = 5 / 7 / 9** first-try wins in a row
  (5, 7 VERIFIED); pools **5000 / 7000 / 10000** coins (third DECISION). → **SHIPPED (SOC1c, §15): N = 5 / 7 / 10, 10000 VERIFIED**
  (phone sessions 2 and 3: "PRIZE 10000", "Pass 10 Levels in a row on first try"), from social.json `events.skyJump`.
- "Finding players on your level." counter 29 → 100 over ~1.5 s with a fan of 14 portraits (avatars ≠ 0 of the 99 rivals).
- **Players left** is a function of the user's step, not of time (phone: it only changed when the user won): after the user's k-th win
  `A_k = A_{k−1} − round((A_{k−1} − 1)·h_k)`, `h_k` ∈ 0.13-0.25 (mean 0.19; phone 100 → 82 → 64 → … → 47); winners after the last level
  `W = 1 + clamp(2 + floor(10·(u1+u2)/2), …, A_{N−1} − 1)` (3-12, mean ≈ 7.5; phone 7); share = `floor(pool / W)` (5000/7 = 714 ✓).
  Pads show up to 2 rival portraits on the user's pad and 2 one pad behind (phone `088`).
- A failed level (not a paid continue) ends the run ("If you fail a level, you will fail the challenge!"); DECISION: a new run can start
  30 min later, at most 2 stage-1 runs per event day; stage 3 won → next event day.
- **Tuning result**: active user 329 stage wins a year (mean share 864 coins), casual 60 (688).

### 4.7 Claw Challenge (no opponents)

Weekly. Points per win = the multiplier (§4.2); a 20-step ladder, the bar resets with overflow carried when a step completes; the
step reward is claimed on the next home ("Congratulations! … Tap to Claim"). Known thresholds 1, 200, 300, 400, 300, 500 and rewards
(§1.1); steps 7-20 thresholds UNKNOWN → next phone session (the ladder's owner is SPEC-gameplay §11.2, CONSISTENCY V-9: step 7 = 500 VERIFIED); until then DECISION: 400, 500, 400, 600, 500, 700, 600, 800, 700, 900,
800, 1000, 900, 1200 (alternating like the known part) with the ladder rewards from `shots/021-025` where known. The fail flow's
second popup reads "You will lose <STEPS[step]> token and your streak!" while the Claw is active.

### 4.8 Presentation order (from the phone sequences; the meta/UI spec owns the exact flow)

After a win panel's Continue: (1) Sky Jump progress screen if a run is active ("Tap to Continue"), (2) home, then queued popups one at
a time: claims (Claw step, Sky Jump win "You win!" + share + "Tap to Claim", Rocket Race win, Weekly/Streak results with prize),
Rocket Race lost screen, then offers (Rocket Race, Sky Jump), then the daily Streak Race list. The win panel's bottom strip shows the
Rocket Race lanes while a race is running, else the Streak Race banner (phone `171` vs `196`). API: `pendingPresentations(at:)`.

### 4.9 Coins from events (for the economy owner; bench totals over 52 weeks)

| Profile | levels won | Levels (80/20/60/100) | Streak Race | Weekly | Rocket Race (coins only) | Sky Jump shares |
|---|---|---|---|---|---|---|
| active (~31 wins/day) | 11,387 | 364,280 | 221,692 | 22,000 | 516,500 | 284,190 |
| casual (~5 wins/day) | 1,684 | 53,740 | 88,806 | 16,500 | 51,000 | 41,280 |
| absent | 370 | 11,700 | 14,800 | 3,000 | 15,000 | 5,028 |

Events add about 2.9× (active) and 3.7× (casual) the coins earned from levels. The original's own numbers (continues 900 coins,
packs 1,000 for $1.99) suggest its prizes are generous too; every prize is a tunable in `Tuning/social.json` (defaults = the phone's
values where known) if the economy owner wants to scale them. Rocket stage 2-3 prizes are ours (D14) and dominate the active row —
the first knob to turn.

---

## 5. Time: the monotone social clock

- `simNow = max(deviceNow, highWater)`; `highWater` is persisted on every save and raised on every read. Setting the device clock back
  therefore freezes the simulation until real time catches up — no score, rank, race or countdown ever rewinds (the same rule as
  `Lives.swift`: "a clock set back never punishes", here "never rewinds").
- If `highWater − deviceNow > 30 days` (a clock that was far in the future and got repaired), accept a one-time **rebase**:
  `highWater = deviceNow`, settle open events with their stored state, log `social.clock.rebase`. The only case where displayed values
  may drop; tested.
- Forward jumps are accepted (events end early — the user's own doing).
- All event instances use `simNow`; `-pc.now` overrides `deviceNow` for tests/captures.

---

## 6. Persistence — `Application Support/Save/social.json` (PathCore `StateStore`: atomic write, `.prev` backup, migrations)

```jsonc
{
  "v": 1,
  "installSeed": "0x…",            // SecRandom at first launch
  "homeCountry": "TR", "homeOffsetMin": 180, "homeCulture": "tr",   // at first launch; LOCAL partition only if not in the table
  "createdAt": 1790294760.0,
  "highWater": 1790300000.0,
  "profile": { "username": null, "avatar": 0, "firstTryWins": 10, "weeklyContestWins": 0 },
  "streakStep": 3,
  "history": {                      // pace inputs, capped
    "wins": [[1790299000.0, 61, true], …],          // last 200: time, level won, first try
    "playWindows": [[1790298000.0, 1790299500.0], …] // last 10 sessions with ≥ 1 win
  },
  "weekly":  { "week": 21, "t0": …, "ref": 120.0, "windows": [[…],[…],[…]], "score": 14, "lastWin": …,
               "memberGids": [ … 49 ints … ],        // drift check only (recomputed on load; log if different)
               "settledWeek": 20, "pendingPrize": null },
  "streak":  { "day": 150, "t0": …, "ref": 20.0, "windows": […], "score": 2065, "lastWin": …, "settledDay": 149,
               "pendingPrize": null, "lastShownRank": 4, "lastShownAt": … },
  "rocket":  { "raceCounter": 7, "active": { "raceId": 7, "stage": 1, "t0": …, "spw": 105.0, "wins": [t, t, …] },
               "day": 150, "stage3DoneDay": null, "pendingPrize": null, "lastResult": "lost" },
  "sky":     { "attemptCounter": 4, "active": { "attemptId": 4, "stage": 2, "t0": …, "step": 3 }, "day": 150, "runsToday": 1,
               "cooldownUntil": null, "pendingShare": null },
  "claw":    { "week": 21, "points": 122, "step": 6, "pendingRewards": [] },
  "seen":    { "weeklyIntro": true, "rocketTutorial": true, "skyTutorial": true, "clawIntro": true, "streakIntro": true }
}
```
Everything about other players is derived: groups and rivals are recomputed from `(installSeed, instance id, t0, ref, windows)`.
Writes: on every win/fail (debounced with the player save), join/claim, and `applicationDidEnterBackground`.

---

## 7. Swift architecture (PathCore/Social)

```
Social/
  SocialHash.swift        h64, unit, below, perm (Feistel + cycle walk), floorDiv/posMod — UInt64 wrapping ops (&+ &* ^ >>)
  SocialCalendar.swift    EPOCH, eventDay/Week, localDayMinute, countdown text
  SocialClock.swift       highWater rule (§5)
  WorldConstants.swift    archetypes, countries, buckets, diurnal tables, pattern constants — generated from data.py, pinned by fixtures
  NameData.swift          loads Resources/Social/social_names.json once (lazy; 0.5 MB JSON)
  NameGenerator.swift     decode(style:slot:culture:), number(r:key:), defaultName, isBlocked, tokens
  World.swift             cohort table (append-only; built off-main at launch — Python builds 2.6k cohorts in 0.3 s), member(), sessions() with an
                          LRU (4096 cohort-days), lcum(), progress(), level(), name(), avatar(); frozen cohorts cache min/max level
  WorldQueries.swift      countAtLeast, rank, top, neighbours, gidLimit, find
  Matchmaking.swift       sampleMembers, expectedDaily, playingAt, bands
  GroupContest.swift      WeeklyContest, StreakRace
  RocketRace.swift, SkyJump.swift, ClawChallenge.swift, WinStreak.swift
  SocialState.swift       Codable schema §6 + migrations
  SocialService.swift     façade (actor): onLaunch/onForeground/onBackground, onLevelWon(level:firstTry:at:), onLevelFailed,
                          onContinuePurchased, leaderboard(tab:at:), streakRace(at:), rocketRace(at:), skyJump(at:), claw(at:),
                          join(_:), claim(_:), pendingPresentations(at:), profile/setUsername/setAvatar
```
**Exactness rules** (so Swift == Python bit for bit): only `+ − × ÷` and comparisons on `Double`; no `exp/log/pow/sin/cos/sqrt`, no
`-Ofast`, no FMA (`a*b+c` is fine in Swift, which does not contract; never call `.addingProduct`); floor via `.rounded(.down)` on a
Double, integer floor-division/modulo through helpers (Swift `/` and `%` truncate toward zero); `local day = floorDiv(Int(ls.rounded(.down)), 86400)`
(never `floor(ls/86400)` in Double); sums in table order; `interp` exactly as `core.py`; `round` = `floor(x + 0.5)`. Hash arguments that
are negative are passed as their two's-complement `UInt64(bitPattern:)`.

**Threading.** `SocialService` is an actor; world queries run on its executor; the UI reads immutable snapshot structs published to the
main actor. Warm-up at launch (behind Loading): build the cohort table, load names, compute the home badges' state.

**Tuning.** World constants are code (changing them changes the shared world and breaks the fixtures on purpose). Event tunables live in
`App/Resources/Tuning/social.json`: unlock levels, prizes, bands, hold/δ, Sky hazards, cooldowns, run caps, refresh period.

**Launch args** (`-pc.` prefix): `-pc.socialSeed <u64>` (install seed), `-pc.socialCountry <ISO>`, `-pc.socialScenario <name>`
(preset states for UI tests/captures: `weeklyLocked`, `weeklyFresh`, `weeklyPodium`, `streakList4th`, `rocketMid`, `rocketLost`,
`rocketWon`, `skyMatch`, `skyStep4`, `skyWin`, `skyFail`, `clawStep`), plus the global `-pc.now`.

---

## 8. Tests

1. **Golden** (`SocialGoldenTests`, fixtures copied into the test bundle): `core.json` (h64, unit, perm, calendar, local day/minute),
   `names.json` (decode per style/culture/slot, numbers, blocklist verdicts), `world.json` (60 cohorts' every field, sessions of 15
   cohort-days, 800 progress/level values, 120 names/avatars), `queries.json` (counts, ranks, neighbour gids, top-25 for World/TR at
   three dates), `events.json` (weekly members/arrivals/bases/standings, streak group/scores/standings, rocket rivals/holds/deltas/
   natural finishes/progress, Sky Jump curves). Exact equality; doubles parsed from Python `repr`. **Never edit a fixture to pass.**
2. **Properties** (`SocialPropertyTests`, = `tests.py`, **18/18 pass**): perm bijection; monotone in u; monotone in t; midnight
   continuity; session validity; count = brute force (TR); top = brute force; neighbours consistent; nickname uniqueness (60k) + no
   blocked name; `player_` names one bijection with disjoint ranges; LOCAL partition leaves the shared world identical; Sky Jump curve;
   Rocket monotone + past-stable; group contests monotone/sorted/growing; clock set back never rewinds + one rebase; streak ladder;
   event day/week boundaries. Plus Swift-only: state round-trip + migration; `SocialService` flows (win/fail/claim sequences).
   The whole-world nickname audit (`name_audit.py`, 4.9 M players, 0 duplicates, ~3 min) stays a Python-side check.
   (SOC1c, shipped model: nickname uniqueness → "0 blocked, 0 longer than 16, repeats at the phone's rate", §15.3.)
3. **Bench** (`SocialBenchTests`, device + simulator, not in the default run): the query budgets of §3.2 on a 3-year world
   (`-pc.now 2029-09-25`), 1,000 queries each, p95.
4. **UI tests** via `-pc.socialScenario`: tabs, lock text, auto-scroll + Top pill, podium, Streak list auto-scroll, Rocket lanes/lost,
   Sky Jump map/progress/win, Claw claim; screenshots for the UI comparison with the reference shots.

---

## 9. Bench (`tools/bench.py`, 52 weeks from 5 Oct 2026, one user each)

Profiles: **active** (TR, plays 97 % of days, 2-4 sessions of 12-35 min, first-try 88 %/72 % hard), **casual** (US, 62 % of days,
1-2 sessions of 6-16 min, 80 %/60 %), **absent** (GB, 3 weeks active, 4 away, 1 back, 6 away, then one day a fortnight). Lives model
(5, 20 min refill), Hard/Super Hard pacing, every event joined when offered.

| Metric | active | casual | absent |
|---|---|---|---|
| Final level / wins / fails | 11,391 / 11,387 / 1,946 | 1,688 / 1,684 / 516 | 374 / 370 / 118 |
| Final World rank (of 1.18 M) / Country rank | 19,860 / 512 (TR) | 131,937 / 41,168 (US) | 277,169 / 20,461 (GB) |
| Weekly: win / podium / median rank (weeks) | 9.8 % / 43.1 % / 4 (51) | 6 % / 34 % / 6 (50) | 4.3 % / 13 % / 20 (23) |
| Streak Race: 1st / top-3 / median rank / coins·day⁻¹ | 16.2 % / 47.6 % / 4 / 632 | 5.1 % / 33.6 % / 5 / 378 | 10.3 % / 28.2 % / 5 / 380 |
| Rocket Race win, stage 1 / 2 / 3 (races) | 63.6 % / 64.2 % / 53.6 % (908) | 33.5 % / 10.8 % / 0 % (343) | 50 % / 31 % / 20 % (53) |
| Sky Jump stage wins / runs, mean share | 329 / 848, 864 | 60 / 311, 688 | 7 / 51, 718 |
| Returns where someone passed the user (Country ±10) | 74.7 % (2.0 players) | 91.6 % (2.5) | 64.3 % (1.6) |
| Rows (of 20 around the user) that moved while away | 9.9 | 5.0 | 3.7 |
| Sessions where Weekly members scored during the session | 72.2 % | 21.7 % | 40 % (5) |
| World top-100: new entries per 4 weeks / #1 level after 1 y | 2-6 / 62k | same world | same world |
| Invariant checks: backwards jumps / duplicate rows / country rank > world rank | **0 / 0 / 0** (268 views) | **0 / 0 / 0** (190) | **0 / 0 / 0** (54) |

Honest limits: (1) players passing the user *during* one session on World/Country are rare (0-1 %) because everyone plays at a human
pace; the live duels are the Rocket Race (rivals move while you play, always) and the Weekly/Streak groups. (2) The very-active profile
(31 wins/day, every day) is extreme; its event income is large (§4.9). (3) Sky Jump/Rocket stage 2-3 are hard for casual sessions
(7-9 levels in one sitting), as in the original.

---

## 10. UI inventory (for the UI spec writer — measure from these; every string below is the original's unless marked NEW)

| Screen / component | References | Captured? | Dynamic data from the simulation |
|---|---|---|---|
| Leaderboard: header, tabs Weekly/World/<Country>, nav bar with raised "Leaderboard" | phone `132`; V2 `full/V2_t0029.50, 31.50, 33.50` | yes | tab label = localized country name of `homeCountry` |
| Weekly locked text | V2 29.5 s | yes | — |
| Weekly board: countdown chip, "Weekly Contest" banner + (i), podium (3 blocks, rank hexagons, avatars, names, coin prizes, "Score : n"), rows "Score" | phone `132`, `web/yt_frames/gamemobie_L50_leaderboard-weekly.jpg` | yes ((i) popup NO) | group standings, live |
| Weekly unlock: intercepted Play, arrow to trophy, intro page | phone `130`, `131` | yes | — |
| Weekly result popup | — | **NO** | rank, prize (DECISION: "Weekly Contest" ribbon + rank badge + "You finished #n!" (NEW) + coin plate + "Tap to Claim") |
| World rows (star badges 1-3, plain 4+, avatar, name, "Level" n) | V2 31.5 s | yes | top 100 + user window |
| Country rows + green user row + "Top" pill | V2 33.5 s | yes | continuous / windowed |
| Profile, Enter Username, Edit Profile (3×3 grid), stats | V2 50-70 s, `ref/V2_edit_profile_avatar_grid.png` | yes (v552 skin NO) | First Try Wins, Weekly Contest Wins |
| Streak Race list popup (header art, logo, subtitle, chips, countdown, rows with prize plate + token score, green user row) | phone `203`, store `iphone-6`, `web/yt_frames/gamemobie_L76_streak-race-popup.jpg` | yes (rank-1 row, (i) NO) | 20-player standings, live |
| Streak Race banner under win/fail panels | phone `020`, `015`, `196` | yes | chip lit, countdown |
| Streak Race result | — | **NO** | DECISION: the list in final state + "Continue", then the claim overlay if a prize |
| Claw Challenge screen, ladder, (i), home bar, claims | phone `021-025`, `026`, `035`, `101`, `172-173`, `204` | yes (steps 7-16 NO) | points, step, rewards |
| Sky Jump offer, matching, tutorial, map, progress, win, stage-2 offer, home badge | phone `065-070`, `074-080`, `084`, `088`, `094-096`, `101` | yes | step, Players, portraits, share |
| Sky Jump fail / expired | — | **NO** | DECISION: map with the user's pad cracked + "You failed the challenge!" (NEW) + Continue |
| Rocket Race offer, join claim, tutorial, race, lost, re-offer, win-panel strip, home badge | phone `163-168`, `171`, `176`, `178`, `183-184`, `189` | yes | lanes, n/N, ranks |
| Rocket Race won | — | **NO** | DECISION: same screen, "You won the race!" (NEW), the user's lane topped by the gold "1" chest, Continue → claim overlay |
| Trophy tab "!" badge | phone `204` | yes (trigger NO) | §3.4 |
| Home event column: Streak badge (flags + countdown), Rocket badge (hexagon with the user's race rank + countdown / "Join"), Sky Jump badge (pink drum with the step / "Join"), Claw bar (hex icon, points/threshold, reward, multiplier badge, countdown chip) | phone `026`, `070`, `101`, `168`, `173`, `204`; `design/ui-measure.md` home.* | yes | race rank, step, points, timers |
| (i) info popups: Weekly, Streak Race, Rocket Race, Sky Jump (Claw's is `025`) | — | **NO** (Claw yes) | static text |

Strings (EN from the original; TR proposed, the strings lane decides):

| Key | EN | TR (proposal) |
|---|---|---|
| lb.title | Leaderboard | Sıralama |
| lb.weekly / lb.world | Weekly / World | Haftalık / Dünya |
| lb.locked | Reach level 50\nto compete in\nWeekly Contest! | Haftalık Yarışmaya\nkatılmak için\n50. seviyeye ulaş! |
| lb.level / lb.score / lb.podiumScore | Level / Score / Score : %d | Seviye / Puan / Puan : %d |
| lb.top | Top | Başa |
| weekly.title | Weekly Contest | Haftalık Yarışma |
| weekly.intro.* | Beat Levels! · Contest with others! · Win Rewards! · Compete against your friends!\nThere is a new contest every week! · Tap to Continue · Tap to compete in Weekly Contest! | Seviyeleri Geç! · Diğerleriyle yarış! · Ödülleri Kazan! · Arkadaşlarınla yarış!\nHer hafta yeni bir yarışma var! · Devam etmek için dokun · Haftalık Yarışmaya katılmak için dokun! |
| weekly.result (NEW) | You finished #%d! | %d. oldun! |
| streak.title / streak.sub | Streak Race / Beat levels without fail to get more rewards! | Seri Yarışı / Daha fazla ödül için seviyeleri hatasız geç! |
| fail.streak / fail.token | You will lose your streak! / You will lose %d token and your streak! | Serini kaybedeceksin! / %d jetonu ve serini kaybedeceksin! |
| claw.title / claw.info | Claw Challenge / Beat levels without losing! · Increase your score multiplier! | Pençe Mücadelesi / Seviyeleri kaybetmeden geç! · Puan çarpanını artır! |
| common.congrats / claim / continue | Congratulations! / Tap to Claim / Continue | Tebrikler! / Almak için dokun / Devam |
| sky.title / sky.offer | Sky Jump / Pass %d Levels in a row on first try and advance to next stages! | Gökyüzü Zıplayışı / %d seviyeyi ilk denemede art arda geç, sonraki aşamalara ilerle! |
| sky.finding | Finding players on your level. | Seviyene uygun oyuncular aranıyor. |
| sky.tut.* | Start with 100 players! · Beat %d levels! · Win your share of %d coins! · Advance to next stages for greater prizes! · If you fail a level, you will fail the challenge! | 100 oyuncuyla başla! · %d seviye geç! · %d altından payını kazan! · Daha büyük ödüller için sonraki aşamalara ilerle! · Bir seviyede kaybedersen mücadeleyi kaybedersin! |
| sky.map | Stages · Levels · Players · PRIZE | Aşamalar · Seviyeler · Oyuncular · ÖDÜL |
| sky.win / sky.share | You win! / You are sharing the reward with %d other winners! | Kazandın! / Ödülü %d diğer kazananla paylaşıyorsun! |
| sky.fail (NEW) | You failed the challenge! | Mücadeleyi kaybettin! |
| rocket.title / rocket.offer / rocket.race | Rocket Race / Beat %d Levels before others to win and advance to next stages for greater prizes! / Beat %d levels before others to finish the race | Roket Yarışı / Kazanmak için %d seviyeyi herkesten önce geç ve daha büyük ödüller için ilerle! / Yarışı bitirmek için %d seviyeyi herkesten önce geç |
| rocket.tut.* | Beat levels! · Finish race before others! · Win amazing rewards! · Advance to next stages for greater prizes! | Seviyeleri geç! · Yarışı herkesten önce bitir! · Harika ödüller kazan! · Daha büyük ödüller için sonraki aşamalara ilerle! |
| rocket.lost / rocket.won (NEW) | You lost the race! Try again to win amazing rewards! / You won the race! | Yarışı kaybettin! Harika ödüller için tekrar dene! / Yarışı kazandın! |
| stage / join / start | Stage %d / Join / Start | Aşama %d / Katıl / Başla |
| profile.* | Profile · Enter Username · Create your username: · Edit Profile · Save · General Stats · First Try Wins · Weekly Contest Wins | Profil · Kullanıcı Adı · Kullanıcı adını oluştur: · Profili Düzenle · Kaydet · Genel İstatistikler · İlk Denemede Kazanılan · Haftalık Yarışma Birincilikleri |

---

## 11. Open questions and the next phone session (social checklist)

Not answerable from the evidence so far — each has a DECISION above that the capture would confirm or replace:

1. **Streak Race list**: scroll to the TOP (rank-1 prize; our guess 2000) and to the BOTTOM (group size; our guess 20); after a win at a
   known chip, reopen to confirm the score delta = the chip value before the win; at 10:00 TRT capture the result/claim popup and the
   next day's first list (do all rows start at 0 or with points?).
2. **Weekly board**: scroll the whole list (group size; ours 50) at join and again after a few hours (does it grow? score deltas of the
   top rows per hour = rival pace); the (i) popup; the Monday 10:00 TRT result popup and prize claim.
3. **World and Turkey tabs**: top rows (names, levels — compare with our 18.8k/10.4k for top-1/#100 in Sep 2026), the scroll end (does
   World stop at 100? does it show the player's row?), the player's Turkey rank at L62+ (ours ≈ #3.2k for L60) and whether the list is
   continuous up to the player.
4. **Rocket Race**: a race won (result screen, prize claim, the stage-2 offer: levels and prize); a lost race's timeline with a shot every
   2 min (rival pacing, does the leader wait at 4/5?); whether a lost race can be retried immediately and how many times per day.
5. **Sky Jump**: a failed run (screen text), whether it can be rejoined the same day; stage 2 survivor counts and winners; stage 3 levels
   and prize; the (i) popup.
6. **Claw Challenge**: the whole 20-step ladder (scroll slowly) and each step's threshold (the bar after each claim).
7. **Profile (v552 skin)**: the Profile page, the avatar grid (v552 portraits), Weekly Contest Wins display.
8. **Trophy "!" badge**: when does it appear and clear?
9. **Unlock levels** of the Streak Race and Claw on a fresh account (owner's old iPhone 11 if ever available).

---

## 12. Decisions (all tunable; defaults = phone values where known)

| # | Decision | Why |
|---|---|---|
| D1 | One shared world from `WORLD_SEED`; install seed only for the user's groups/rivals | consistent across devices, like a real server |
| D2 | Event day = 07:00 UTC, week = Monday 07:00 UTC | 12 countdowns on the phone (§1.2); UTC over local |
| D3 | Events run every day/week forever (no rotation) | no server to rotate them; never updated |
| D4 | World epoch 2026-04-27 07:00 UTC; joins formula §2.1 | the original's launch; world size plausible for a top-200 puzzle game |
| D5 | Countries §2.3; home country frozen at first launch; LOCAL partition for countries not in the table | "user's country always populated" without breaking the shared world |
| D6 | Archetypes §2.4 | calibrated to V2 World top-8 and the FTUE speed |
| D7 | Lapsed players come back ~1 play-day in 6 at half volume for months | a board that moves while you are away |
| D8 | Nickname styles and weights §2.8; first-come unique names; 16 cultures (SHIPPED: drawn names, duplicates allowed, §15) | evidence styles; uniqueness proven over 4.9 M (reference); the original's two "Bobby" (shipped) |
| D9 | World list = top 100 + separator + user ±10; Country continuous to the user if rank ≤ 300 (shipped 600, §13.3) | original shows top rows and the user's neighbourhood; ranks reach 10^6 |
| D10 | User first among equal levels (World/Country); last among equal weekly scores when just joined | V2 Country / phone Weekly evidence |
| D11 | Unlocks L30 Streak Race, L33 Claw, L40 Sky Jump, L50 Weekly, L55 Rocket | phone first appearances (§1.3) |
| D12 | Weekly group 50, stratified bands, arrivals; prizes 2000/1000/500 (shipped: 10, §13.3) | phone podium; group size unknown |
| D13 | Streak Race group 20, bands, arrivals by elapsed day; points = chip before the win; prizes 2000/1000/500/100×7 (shipped: 50 rows, §13.3) | phone list (2065 reconstruction) |
| D14 | Rocket stages 5/7/9, prizes 500+45m / 1000+90m / 2000+3h, hold 14-40 min + δ, no cooldown | phone stage 1 + lost race timeline |
| D15 | Sky Jump stages 5/7/9 (SHIPPED 5/7/10, §15), pools 5000/7000/10000, survivors by the user's step, 30 min / 2 runs per day | phone stage 1-2 + Lava-Quest-like rule; stage 3 = 10 levels VERIFIED (phone S2/S3) |
| D16 | Claw thresholds 7-20 alternating 400…1200 until captured (superseded: SPEC-gameplay §11.2 owns the ladder, V-9) | phone steps 1-6 |
| D17 | Monotone social clock with a one-time 30-day rebase | never rewind (§5) |
| D18 | No network, no analytics; all social data local | owner: offline; app-factory "no server" rule still holds |

Risk note for the owner (not a decision): the screens copy the original's wording ("Compete against your friends!", "Finding players
on your level."), which presents simulated players as other people. That is the owner's explicit request; if the game is ever submitted,
the store description must not claim online multiplayer.

---

## 13. Build alignment and the shipped calibration (SOC1, 2026-09-25)

The owner's rule (02:55): where the phone (v552) and a spec disagree, the phone wins. The research after this spec was written
(research/meta.md §5.1, §7; phone-meta-progress 04:31-06:39) showed the leaderboards and events of the owner's own account, and
CONSISTENCY §13/§21 ruled on the group sizes, avatars and lists. The Swift port (Packages/PathCore/Sources/PathCore/Social) is the
SAME model code with two pinned parameter sets: **`reference`** = §2-§4 exactly (bit for bit with design/social/fixtures) and
**`v552`** = the SHIPPED world, bit for bit with Packages/PathCore/Tests/Fixtures/soc_v552_*.json, which this document's Python
reference writes when run with the overrides of Packages/PathCore/Tests/tools/soc_model.py (parameters only; no new code paths).

### 13.1 World and Turkey on 25 Sep 2026 01:31 UTC (the phone's leaderboard shots)

| Board | Phone (v552) | `reference` | `v552` (shipped) |
|---|---|---|---|
| World #1-#7 | 14669, 13344, 13115, 12699, 12003, 11536, 11386 | 18848, 17508, 14170, 13998, 13984, 13807, 13804 | 15286, 14491, 12412, 11692, 11682, 11613, 11155 |
| World #24 / #89 / #132 / #278 | ≈8.4k / 5154 / ≈4.3k / 3096 | 12188 / 10638 / 10079 / 9081 | 8365 / 4805 / 4287 / 3331 |
| Turkey: rank of a Level-62 player | **455** | 3042 | **423** |
| Turkey #1-#7 | 10824 (a lone outlier), 3323, 3193, 2575, 2401, 1604, 1349 | 9570, 9533, 9169, 8819, 8518, 8479, 8126 | 4739, 3731, 3164, 2911, 2598, 2199, 1685 |
| Players joined (world) | — | 331k | 331k (same size: the shares still sum to 1) |

The reference world (fitted to the V2 video of an older build) had ~30× too many heavy players. `SocialCalibrationTests` keeps the
shipped world within 10-15 % of every World number above, within 15 % of the Turkey rank and within 40 % of Turkey #2-#7.

### 13.2 `v552` parameters (everything else = §2-§4)

| Item | reference | v552 | why |
|---|---|---|---|
| TR country weight | 2.0 | 0.5 | Turkey rank 455 at L62; store ratings US 1,435 vs TR 30 |
| tourist share | 0.40 | 0.4844 | keeps the world's size (shares sum to 1) with fewer committed players |
| dabbler λ / life / lapse | 6→30 / 1.5→12 d / 20→90 d | 5→18 / 1→8 d / 10→45 d | fewer players reach L60+ |
| casual share / λ / life / lapse | 0.18 / 5,10,18,25 / 12,35,90 / 45→200 | 0.16 / 4,8,14,20 / 10,30,80 / 30→150 | idem |
| regular share / λ / life | 0.11 / 10,18,32,45 / 40,140,400 | 0.09 / 6,10,16,22 / 30,90,300 | World #89-#278 |
| enthusiast share / λ / life | 0.045 / 20,35,58,75 / 150,500,1600 | 0.006 / 10,20,32,42 / 60,200,600 | World #24-#132 |
| grinder share / λ | 0.006 / 42,60,79,93,128 | 0.0006 / 25,50,88,100,108 | World #1-#7 |
| nickname length | any | ≤ 16 (longer → a fallback `player_` name, 0.06 %) | the player's own username rule (CONSISTENCY V-26) |
| avatars | 1…14 | 1…8 | the 8 shipped portraits (CONSISTENCY V-24) |
| nickname stems | the name data's blocklists | + "maze" | the original's title word stays out of every shipped nickname (`mazerunner7` existed) |

### 13.3 Events and lists (App/Resources/Tuning/social.json)

- **Weekly Contest = 10 players** (phone meta §7: rows 1-10; at the join the list already ended at the player, rank 10, score 0;
  CONSISTENCY V-6). All 9 members arrived within the 15 min before the player (`early` 1.0, `earlyHours` 0.25) and, except the
  idle band, are matched among players PLAYING around the join (−30 … +90 min; the reference's same-hours rule applied to the join
  window): the phone saw 7 of 9 rivals move within 2 h, the leader +23 in 85 min and +43 in 3.5 h. Bands [count, r_lo, r_hi]:
  [1, 1.10, 1.80], [2, 0.90, 1.20], [2, 0.65, 0.90], [2, 0.40, 0.65] (online), [2, 0.08, 0.40]. Prizes 2000/1000/500.
- **Streak Race = 50 rows** (phone meta §5.1; CONSISTENCY V-5): bands [5, 1.0, 1.8], [10, 0.75, 1.0], [14, 0.5, 0.75],
  [12, 0.25, 0.5] among players who PLAY that event day (the same-hours rule applied to the day), + [8, 0.02, 0.25] idle; r = the
  member's levels per PLAYED day (expected daily / ρ) over the player's wins per ACTIVE day, floored at 4 (the reference compared
  a per-active-day reference with per-calendar-day members and floored at 8, which pitted a 5-wins-a-day player against 8+);
  the elapsed share of the day already there, the rest arriving front-loaded by 12 h before the day ends (the phone's list was
  complete at 18.8 h) and never after their first win of the day. At ~19 h into a day an active player's list shows 7-17 zero
  rows and 28-38 rows past one full climb (141) — the phone: 9 and 35. Points per win = the multiplier lit before it; prizes
  2000/1000/500/100×7.
- **Country list** continuous while the player's rank R ≤ 600 (the phone's Turkey list ran continuously from #1 to the player at
  #455, meta-026..028/107-108; CONSISTENCY V-20). World: 1-100 + separator + R±10 (V-19); pinned rows per SPEC-ui (V-21).
- **Claw thresholds**: SPEC-gameplay §11.2 (V-9). **Profile stats**: six (V-35).

### 13.4 The 52-week bench on the shipped world (Swift, `SocialBenchTests`; build/soc1/bench)

| Metric | active (TR) | casual (US) | absent (GB) |
|---|---|---|---|
| Final level / World rank / Country rank (of 1.18 M) | 11,310 / 787 / 5 | 1,600 / 49,774 / 15,795 | 380 / 149,195 / 11,115 |
| Weekly (10): win / podium / median rank | 11.8 % / 58.8 % / 3 | 14 % / 38 % / 4 | 0 % / 0 % / 7 |
| Streak Race (50): 1st / top-3 / median rank / coins a day | 14.7 % / 31.4 % / 6 / 454 | 0.5 % / 4.2 % / 16 / 58 | 0 % / 2.4 % / 18 / 38 |
| Rocket Race stage 1 / 2 / 3 wins | 73 % / 69 % / 57 % | 40 % / 17 % / 13 % | 71 % / 19 % / 0 % |
| Returns where someone passed the player (Country ±10) | 4.9 % (the player is Turkey's #5-#8 all year) | 89.5 % | 78.6 % |
| Weekly rivals' leader after the join: median gain 85 min / 3.5 h (phone +23 / +43) | 15 / 19 | 6 / 7 | 6 / 7 |
| Invariants: backwards / duplicate rows / country rank > world rank / bad pages | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

### 13.5 Seen on the phone, not modelled

- The Streak Race scores did not move for 1 h 42 min (04:46 → 06:28 TRT) while the Weekly rivals did. One observation, cause
  unknown (the original may refresh that list only on the player's own progress); here the members move on their own clock.
- The phone's Weekly rivals were faster than our median group (+43 in 3.5 h for the leader); ours move ~15-20 levels in that time for an
  active player, less for a casual one (their bands follow the player's own pace).
- A casual player (≈5 wins on a play day) rarely reaches the Streak Race podium among 49 people who play that day (4 %); it wins a
  top-10 plate (100) on about a third of its race days. The reference's 20-player race gave it 34 % top-3: a tunable
  (`matchmaking.streak.bands`) if the owner wants the race easier.

---

## 14. SOC1b — the recalibration to phone session 2 (2026-09-25)

Phone session 2 watched the original for ~2.5 h (research/social-dynamics.md §A-§I: the Weekly group ×7, World top 15-31, Turkey top 7 +
the player's rank ×7, the Streak Race's 50 rows ×7, Rocket Race ×3, Sky Jump stages 2-3, reset times, a name-style breakdown of ~113
names). The before/after table of every observable is **build/soc1b/calibration.md** (generated by `tools/calib_table.py` from
`tools/calib_s2.py`, which measures the SAME scenarios on SOC1's parameters and on the new ones). This section wins over §13.

### 14.1 Where the shipped model lives now

`design/social/tools/socialsim/shipped.py` = the shipped parameter set as a patch over the prototype (moved from SOC1's
Tests/tools/soc_model.py, which now only delegates to it). New mechanisms were added to the reference modules **switched off by
default**, so the prototype is byte-identical (design/social/fixtures regenerate unchanged; `tests.py` 18/18) and `shipped.apply()`
switches them on. The Swift port matches bit for bit again: Tests/Fixtures/soc_{reference,v552}_*.json (76,076 values compared per
run, Debug and -O).

| mechanism (reference module) | what it does | Swift |
|---|---|---|
| honeymoon — archetype key `honey = (β, days)` (population.py) | members play (1 + β) × their daily volume until `days` after the END of their cohort's join window (capped by each member's T1); session windows of those local days are sized for the bigger share. One end per cohort keeps containment: a higher-u member joined earlier, so its honeymoon [J, hE] contains a lower one's, and increments over an interval never fall with λ ⇒ level stays monotone in u and t (tests 2-4). | `SocialArchetype.honey`, `SocialCohort.hb/hE/hDL` |
| `names.VARIANTS` + style `'leet'` (names.py) | case variants (invented lower/UPPER, first names in UPPER, name+suffix lower) never collide because uniqueness is case-insensitive; `compoundDigits` swaps round 0 with one hashed 2-digit round per token (a transposition of a bijection); `'leet'` = procedural L8M / K710 / 0xBK handles (a digit before a letter, or one letter + exactly 3 digits: no other style can make them) | `SocialNameStyle`, `SocialNames.decode(…, variants:)` |
| `GroupContest.TIE_BY_NAME` (events.py) | equal scores ordered by the name's key (code-point order), then the reach moment | `SocialGroupSpec.tieByName`, `standings(…, userName:)` |
| `StreakRace.FAIL_Q` | a member's fail chance per win = lo + span × u01 (reference 0.06 + 0.24 u) | `SocialGroupSpec.failQ` |
| `RocketRace.ROLES / HOLD_BY_ROLE / SPRINT_MINUTES` | lane roles incl. `sprint` (beats N levels within 15 min × N/5 at its own pace) and `steady` (1-3 levels in 20 min); a hold range per role | `SocialRocketSpec.roles/holdByRole/sprintMinutes` |
| `events.SKY_DROPS` | Sky Jump: a per-run drop d ∈ [lo, hi] per level (each step d ± 1) from the player's step `first`; winners ∈ [wlo, whi] | `SocialSkySpec.drops` |

### 14.2 The shipped values (v552 = SOC1 + these)

| item | SOC1 | SOC1b | phone evidence |
|---|---|---|---|
| custom nickname share | the reference's (tourist .15 … grinder .86) → 42 % `player_` on the boards | tourist .08, dabbler .80, casual .84, regular .86, enthusiast .88, grinder .90, returner .84 → **16 %** on the boards | 14-18 % (Streak Race 9/49, Weekly 1/9, World top 2/23, Turkey 3/20) |
| style mix among custom names | given .34 word .07 compound .19 invented .14 caps .04 underscore .10 initials .05 mixed .07 | given .12 word .01 compound .20 invented .28 caps .02 underscore .005 initials .005 mixed .33 leet .03; invented 45 % lower / 8 % UPPER, first names 8 % UPPER, compound 35 % with 2 digits, name+suffix 25 % lower | first names/capitalised ~48 %, lowercase ~15 %, CamelCase ~12-20 % (a third with 2 digits), ALL CAPS ~4 %, short/leet ~7 % |
| honeymoon | — | dabbler/casual/regular/returner 2× for 5 days after the join week | Turkey rank −3.6 places per level won at L62-L84 |
| sessions per play day | reference (1-2 / 1-3 / 2-4 / 3-6) | dabbler 1-4, casual 1-4, regular 2-5, enthusiast 3-6, returner 1-3; grinder **1-3** | Weekly rivals in bursts, ~40 % idle all day; World top rows static for hours, a few climbing ~35 levels/h |
| Turkey weight | 0.5 | 0.30 (a country is whole cohorts: 0.29 → rank 346, 0.30 → 430, 0.32 → 527 at L62) | rank 455 at L62 … 375 at L84 |
| Weekly idle band | not online | online at the join | Boo +6, Mema +4 in the first 85 min, then nothing all day |
| Streak Race members | arrive over the day (elapsed share, the rest by 12 h before the end), play that day | **all arrive at the join with 0**, matched among players who win within 2 h after the join (+ 8 idle), bands (5, 1.2-2.2) (10, .75-1.2) (14, .4-.75) (12, .1-.4) (8, .02-.1), fail chance 2-12 % per win, **ties alphabetical** | all 49 at 0 at the join, alphabetical; 17 still 0 at +69 min, 11 at +4 h; leaders 4081 / 3645 / 3573 at +3.7 h |
| Rocket lanes | hot, hot, warm, idle; hold 14-40 min | **sprint** (hold 6-19 min), hot, steady, steady (hold 14-40) | one rival finished 5 levels 6, 8, 15-20, 19 min after the join; others at [3,2,1] [3,1,1] [4,3,1]; the slow player lost 4/4 |
| Sky Jump curve | proportional hazard 13-25 % per step, 3-12 winners | per stage [drop lo, hi, first step, winners lo, hi]: [10, 16, 1, 5, 10], [11, 14, 2, 12, 18], [7.5, 10, 2, 14, 24] | stage 1: 100 82 64 ? 47 → 7; stage 2: 100 100 88 75 62 49 36 → 15 (7000/15 = 466); stage 3: 100 100 91 82 74 65 57 … |
| reset times | event day 07:00 UTC, week Monday 07:00 UTC, Sky 24 h | unchanged — VERIFIED again (Weekly "2d 21h" at Fri 12:08 TRT, Streak/Rocket 10:00 TRT) | |

### 14.3 Results (build/soc1b/calibration.md has every number, before and after)

- **Names on the phone's boards:** `player_` 42 % → **16 %** (phone 14 %); lowercase 0.3 % → 14 % (15 %); CamelCase 11 → 16 % (12 %);
  ALL CAPS 0.1 → 1.4 % (3.5 %); digits 30 → 24 % (7 %); plain first names 0.7 → 0.5 % (14 %). Whole world to 2031: 4,875,040 nicknames,
  **0 duplicates, 0 blocked, 0 longer than 16** (design/social/bench/name_audit_v552_2031-09-25.json).
- **World:** the level calibration is SOC1's (#1 15.3k vs 14.7k …). Top 15 over 1.9 h: median 12 of 15 static (phone 9), the biggest
  climber median 42 levels (max 66; phone 66 and 40); SOC1: 10 static, 31.
- **Turkey:** ranks at L62/64/68/72/77/80/84 = 430/428/422/410/395/377/355 (phone 455/448/438/412/396/386/375; SOC1 423 … 306);
  **3.4 places per level** (phone 3.6; SOC1 5.3).
- **Weekly** (a ~35-wins-a-day player, the phone's pace: ref 175): idle from +3.5 h to +11.2 h after the join 56 % at the phone's hour
  / 46 % over 8 join hours (phone 44 %; SOC1 71 / 61 %); 3.2-4.1 rivals moving in +3.5 → +9 h (5; SOC1 2.2-3.0); the group's progress
  shares .30 .19 .14 .12 .10 .07 .05 .03 .01 (phone .31 .18 .11 .11 .09 .09 .07 .02 .02).
- **Streak Race:** 49 of 49 at 0 at the join, listed alphabetically; ~21 rows at 0 after 69 min (17), ~11 after 3 h (11); 52-55 % static
  from +69 min to +3 h (47 %; SOC1 88 %); leaders at +3 h ~2.7-3.8k / 2.4-2.8k / 1.8-2.2k (phone 4081 / 3633 / 3556).
- **Rocket:** first rival finish median 13 min (q1 10.5, q3 15.5; phone 6-19; SOC1 28); the others then at [3, 2, 0] ([3-4, 1-3, 1]);
  a player at 6 min a level (the phone's) loses every race, at 2 min a level wins 62 % (SOC1 82 %).
- **Sky Jump:** stage 2 = 100 100 88 77 66 53 42 → 12-18 winners (median share 466, the phone's exact 7000/15); stage 1 winners 5-10
  (share 714 median = the phone's 5000/7).

### 14.4 Limits (honest)

1. **Plain first names are rare.** Every nickname is unique (case/accent-insensitive; the original is not: two "Bobby" in its World
   top 15) and the first-name lists hold ~3.3k tokens, so a first name met on a board almost always carries a number (Kate23) — that is
   most of our 24 % digits against the phone's 7 %. Lifting it means either duplicate names (a rule this build keeps) or far bigger
   name lists (a data change to design/social/data). → **RESOLVED by SOC1c (§15): duplicates allowed.**
2. **Absolute Weekly volumes** are about half the phone's at the phone's hour: the phone's player was the runner's bot (~2× a ref-175
   player) and its rivals were proportionally heavy; the group's shape and burst/idle structure match.
3. **Streak Race leaders** reach 70-90 % of the phone's; the original's leaders jumped +2583 in 28 min and then crept up ~1 point a
   minute, which no human-paced, win-based ladder produces. In the phone-hour sample our leaders keep gaining more between +97 min and
   +3 h (median +1.8k vs +111); over other join hours they stop (median +0).
4. **World top-15 movers:** a bit more static (12 vs 9 of 15) with bigger bursts; the phone's small +1/+4 movers are rare here.
5. **Rocket:** fast players (1.5-2 min a level) win 62-95 % of stage-1 races; the phone's player (slow) lost 4/4 as ours would.
6. **Turkey moves in lumps** (whole cohorts): rank 430 at L62 (−5 %), 355 at L84 (−5 %).
7. **Sky Jump stage 3 = 10 levels / PRIZE 10000 on the phone** (§I-E, VERIFIED twice); C3's `EventRules.skyJump.levels` ships
   [5, 7, 9]. The opponents' curve follows whatever levels the config carries; adding `"events": {"skyJump": {"levels": [5, 7, 10]}}`
   to social.json would switch C3 and SOC together — an owner/orchestrator call (C3's layout), not made here. → **DONE by SOC1c
   (§15) on the orchestrator's call.**

### 14.5 The 52-week bench and the budgets

Swift SocialBenchTests on the shipped world (build/soc1b/bench; before = SOC1's §13.4), active / casual / absent:

| metric | SOC1 | SOC1b |
|---|---|---|
| Weekly win / podium | 12 / 59 %, 14 / 38 %, 0 / 0 % | 20 / 65 %, 6 / 44 %, 0 / 0 % |
| Streak Race 1st / top 3 / median rank | 15 / 31 % / 6, 0 / 4 % / 16, 0 / 2 % / 18 | 2 / 16 % / 10, 5 / 17 % / 10, 2 / 10 % / 15 (the phone's bot player sat at #7-#11) |
| Streak Race coins a day | 453, 58, 38 | 183, 227, 123 |
| Rocket stage 1 / 2 / 3 win | 73 / 69 / 57 %, 40 / 17 / 13 %, 71 / 19 / 0 % | 47 / 47 / 39 %, 29 / 8 / 0 %, 46 / 18 / 0 % (the phone's player lost 4/4) |
| invariants (backwards / duplicate rows / country > world / bad pages) | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

Query budgets (SocialPerfTests -O, p95): every gate passes in the final run, within noise of SOC1 (3-year World rank 1.17 → 1.20 ms,
budget 8; a 3-year World page 1.28 → 1.20 ms, guard 2). One earlier full run under load (~5, right after the bench) measured that page
at 2.21 ms p95 (p50 1.12) — over its 2 ms guard; standalone reruns 1.14 / 1.13 ms. The guard has ~40 % headroom on this Mac, so it can
flake on a busy machine; the phone decides (SPEC §5.3). All social computation stays off the main thread (SocialEngine behind its
lock; the UI reads snapshots), as SOC1 built it.

### 14.6 Tests and mutations

- Python: `tests.py` 18/18 on `reference` AND `v552`; design/social/fixtures regenerate byte-identical (the prototype is untouched);
  `name_audit.py 2031-09-25 --v552` 0 duplicates in 4.9 M.
- Swift (build/soc1b/iso.sh, only the Social test files, Debug and -O): Social suites 59/59; 76,076 golden values compared bit for bit per run:
  every soc_* fixture (the v552 set now also pins 432 nickname decodings with the variants and 'leet', the Streak Race's name-ordered
  standings from the join, 24 Rocket races — 18 of them stages 2-3 — and the new Sky curves). New checks: SocialCalibrationTests
  `testTurkeyRankSlope`, `testBoardNameMix`, `testWeeklyBurstiness`, `testStreakRaceStartsAtZeroAlphabetical`, `testRocketSprinter`,
  `testSkyJumpStageTwo`; SocialPropertyTests: the shipped Sky curve, Rocket roles, name-ordered standings.
- Mutations (Tests/tools/soc_mutations.py → build/soc1b/mutations.txt): SOC1's 7 + 6 new (honeymoon session sizing, honeymoon rate,
  ties by reach instead of name, a shifted leet digit, Sky drops from step 1, the sprint window without its N/5 scaling): **13/13 CAUGHT**.
  The sprint-window mutation was MISSED on the first run (the fixture's two stage-2/3 races picked the same sprinters either way); the
  fixture gained 16 stage-2/3 races and it is now caught (165 assertions).

---

## 15. SOC1c — drawn nicknames (duplicates allowed) and Sky Jump stage 3 = 10 levels (2026-09-25)

The orchestrator's two changes (after SOC1b): **(1)** allow DUPLICATE display names like the real game (two "Bobby" in its World top
15), so plain first names reach the phone's ~14 % and names with digits drop toward its ~7 %; the player's identity stays its index
(gid), never the name; blocklists, length rules and determinism kept; the whole-world and 100k audits become "0 blocked, 0 longer
than 16, duplicates allowed at the observed rate". **(2)** Sky Jump stage 3 = the phone's 10 levels with PRIZE 10000 (sessions 2 and
3), in social.json so C3's EventRules and the opponents' curves switch together. Before/after table: **build/soc1c/calibration.md**
(`tools/calib_table_soc1c.py` from `tools/calib_s2.py`, run on SOC1b's parameters with `--soc1b` and on the new ones). This section
wins over §14 and over §2.8 / §4.6 for the shipped model; the reference is untouched (design/social/fixtures and
Tests/Fixtures/soc_reference_* regenerate byte for byte, and SOC1b's parameters still reproduce SOC1b's soc_v552_* byte for byte).

### 15.1 Drawn nicknames (`names.DRAW`, `names.drawn`, population `'nick'`; Swift `SocialNameStyle.draw`, `SocialNames.drawn`)

- A player keeps its style from the cohort's exact per-style counts (unchanged). A **custom** name is no longer the next dense slot of
  its (style, culture): it is drawn by `key = h64(WORLD_SEED, "nick", gid)`, **with replacement**, so two players can show the same
  name. `player_xxxxxxx` defaults (and the blocklist / length fallbacks) stay one bijection of 36⁷ — unique.
- **First-name styles** (given, name+suffix, name_suffix) draw the name by popularity: the per-culture lists are ordered most common
  first (SSA counts for 'en'; curated order elsewhere). `headP` = 40 % of the draws pick one of the `headN` = 50 most common names
  uniformly, the rest `index = ⌊n·u²⌋` over the whole list (P(index < k) = √(k/n)); the suffix uniformly. Result: 'James' ≈ 1 % of
  the first names met, the 50 most common ≈ half — the concentration real first names have. **Other styles** draw uniformly over
  their grid (40k invented handles, 46k Adjective+Noun pairs, …).
- A number is appended on **5 %** of the drawn handles (`numberP`, all styles but compound — which keeps its 35 % two-digit variant —
  and leet), 2 digits 75 % of the time (`twoDigitP`), else 3 (the phone: Caco17, Alex56k, Stacx251, vidboy120, quints375).
- Case / spelling variants (lowercase, ASCII fold, UPPER) are keyed per player (`vr = h64(key, "var") & 0x7FFFFFFF`), so two
  players drawing 'Bobby' may show 'Bobby' and 'bobby'. `build(style, i, r, culture, vr)` is the reference's decode body with the
  variant key made explicit (the reference passes vr = r: byte-identical).
- The style mix moves back to first names (no uniqueness to protect): given .24, word .01, compound .14, invented .36, caps .02,
  underscore .005, initials .005, name+suffix .19, leet .03; variants invented 25 % lower / 8 % UPPER, first names 8 % UPPER,
  compound 35 % two digits, name+suffix 17 % lower.
- **Per-cohort style counts (SOC1c; found on the resume, 20:10).** The reference (and SOC1b) gives a cohort exact style counts by
  rounding each style on its own (⌊C·w_i + u_i⌋, clipped by what is left) and handing the LAST style the remainder. That is fair on
  average only in big cohorts: in a cohort of a few players the remainder is several times the last style's weight. SOC1b put 'leet'
  (3 %) last, so cohorts under 10 players carried ~10 % leet and ~14 % name+suffix (weight 19 %); the World top is made of such
  cohorts (median size 3: the rare grinders), so every install's World top 10 showed three leet handles (S150 #1, F689 #2, Y775
  #10; 12 of the top 100). The shipped model apportions systematically (`population.STYLE_SYSTEMATIC`, Swift
  `SocialNameStyle.systematic`, hash label 'nsys'): one offset u per cohort, count_i = ⌊C·W_i + u⌋ − ⌊C·W_(i−1) + u⌋ over the
  cumulative weights W — every style's expected count is exactly C·w_i at every cohort size, the counts sum to C, nothing is
  clipped. Only which style a member has changes (levels, ranks, groups, events: identical); the reference keeps its rounding.
- Ties on a Streak Race board are ordered by the name's key, then the reach moment, then the member index (already so): two equal
  names at an equal score still have a fixed order. Every board row is one player (gid); the 52-week bench's "duplicate rows"
  invariant is now "the same player twice" (gid) — a repeated NAME is a statistic, not a defect.

### 15.2 Sky Jump stage 3

social.json gains `"events": {"skyJump": {"levels": [5, 7, 10], "pools": [5000, 7000, 10000]}}` — C3's layout. C3's
`EventRules.load(social:)` (via `EconomyRules.load`, AppModel / ShopEconomy) and SOC's `SocialConfig` both read it, so the run's
level count and the opponents' survivor curve change together; `SocialConfig.encode` now writes that block (the file = the compiled
defaults, SocialNamesTests). Stage-3 curve (`skyBots.drops[2]`): drop 7.5-9.5 per level from the 2nd win (phone 8-9), winners 5-9
(phone 7; share 10000/7 = 1428, the phone's). C3's compiled default (`EventRules.SkyJump.levels`, used only when social.json is
missing or broken) still reads [5, 7, 9]: a one-line request to C3 (build/soc1c report), not edited here.

### 15.3 Results (build/soc1c/calibration.md)

- **Names on the phone's boards** (pooled, calib_s2 classes; phone / SOC1b / SOC1c): player_ 14 / 16 / 16 %; plain first names
  14 / 0.5 / 15 %; other capitalised 34 / 27 / 32 %; lowercase 15 / 14 / 15 %; CamelCase 12 / 16 / 12 %; ALL CAPS 4 / 1 / 4 %;
  digits/leet 7 / 24 / 6 %. Per board: World top 23 digits 9 % (phone 13 %) but plain first names 9 % (phone 30 %: 7 of its 23,
  one board); Streak 14 % first names / 5 % digits; Weekly 16 % / 8 %.
- **Style counts by cohort size** (§15.1): 'leet' in cohorts under 10 players 9.8 % (SOC1b) → 2.1 %, name+suffix 28.0 → 20.4 %
  (SOC1c weight 19 %); every style within its binomial noise of its weight at every size; the World top 100 carries 4 leet
  handles (SOC1b 10, the pre-fix SOC1c draw 12) and 21 plain first names (10). World top 15 after: Snaysan, Klaizex, Flap, Thuso,
  Truris, NavySun46, player_gknynta, dreypar, lisa, women, Dennistastic, Klaypor58, Zhivik, NobleCactus, Joel.
- **Repeats:** the phone's boards held 1 repeated pair (Bobby #9 / Bobby #15) in 1,721 row pairs — rate 5.8e-4, 95 % interval
  1.5e-5 … 3.2e-3 (one event). Ours: 4.5e-5 inside Streak Race boards (9 pairs in 162 boards of 50; ~6 % of boards show one), 7.1e-5
  for any two board-like names (60k different players), 7.2e-5 over the whole world to 2031, 1.5e-4 pooled over every board the
  three 52-week bench users saw (62 pairs in 410,143 row pairs; the slowly changing top 100s count one lasting pair many times) —
  inside the interval, at the concentration real first names have (a stronger head would push 'James' past ~2 % of first names,
  which the phone's diverse first names do not show). The World top 23 at 12:09 shows no repeat in our 61 windows (phone: 1).
- **Whole world to 2031-09-25** (`name_audit.py --v552`): 4,875,040 players, 2,903,352 distinct names, **0 blocked, 0 longer than 16**,
  board-like pair rate 7.2e-5 → verdict PASS (the rule is no longer 0 duplicates); leet 3.0 % of the custom names. 100k Swift
  sample: 0 blocked, 0 bad length, every sampled player a different gid.
- **Sky Jump stage 3:** 100 100 92 84 77 68 60 52 44 36 → 5-9 winners (median 7, share 1428); phone 100 100 91 83 75 66 57 48 40 32 → 7.
- Nothing else moved (World levels, Turkey ranks, Weekly, Streak, Rocket: the same numbers as SOC1b; the 52-week bench's levels,
  ranks, event results and invariants 0 / 0 / 0 / 0 on all three users; only the Sky Jump shares follow the new stage 3).
- Tests: Python `tests.py` 19/19 on both models (test 9 = uniqueness for the reference, drawn-at-the-phone's-rate for v552; + a length
  check); design/social/fixtures + Tests/Fixtures/soc_reference_* regenerate byte for byte, soc_v552_* regenerated (+ the
  `styleSystematic` flag); Swift Social suites Debug + -O 62 tests green, 78,681 golden values bit for bit; new tests: style shares
  independent of the cohort size (SocialNamesTests), the bench's pooled name-repeat rate inside the phone's interval
  (SocialBenchTests; 0 for the reference); mutations m14-m20 on the draw, the style counts and stage 3 (build/soc1c/mutations.txt).
