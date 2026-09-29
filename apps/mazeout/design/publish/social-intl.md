# Arrow Out: international social-world audit (owner item 13)

Author: PUBLISH P1 social-intl agent, 2026-09-28 00:25 +03. Status: investigation + fix plan. Nothing under App/, Packages/,
Tests/ or UITests/ was edited. No simulator, no xcodebuild and no phone were used. All the numbers come from the shipped (`v552`)
Python reference run at low priority (`nice -n 19`, about 5 CPU-minutes in total).

Owner, 2026-09-28, item 13 (verbatim): *"Make sure the international system works very good and everything %100 feels like online
and works logically and perfectly, and not just for turkey, but all countries"*. SPEC.md ruling 37(f): "The social world works for
every country; events rotate weekly." (Weekly event rotation is covered in `design/publish/events.md`, not here.)

Evidence tags:
- **VERIFIED (run):** measured by running the Python reference in this audit. The Swift port matches the reference bit for bit
  (78,681 golden values, SPEC-social §15.3), so the app shows the same boards. The Swift itself was **not** run here.
- **VERIFIED (code):** read in the Swift or Python source, with file and line cited.
- **VERIFIED (phone):** from `research/social-dynamics.md` (the owner's phone, v552 of the original).
- **INFERRED:** my reasoning, not measured.

Reproduction: `design/publish/tools/social_intl/*.py` (read-only users of `design/social/tools/socialsim` via
`Packages/PathCore/Tests/tools/soc_model.py`). Their results are in the same folder: `boards_15_countries.json`, `week_activity.json`
and `blocks_before_after.json`.

---

## 0. Verdict

The large, English-first boards (US, GB, CA, AU, BR, IN, DE) behave like a real online game: they have clear day and night
cycles, many independent players and no structural patterns that give the simulation away. The simulation falls apart for most
other countries, and that includes several of our 13 launch locales:

1. **A country is made of whole cohorts.** In every cohort (players who joined in the same week, same bucket, same archetype),
   the members sit at evenly spaced quantiles and share one session schedule. A small country's board is therefore built from a
   handful of cohorts. It shows evenly spaced "ladders" of levels (Spain's top 4: 6022, 5630, 5229, 4829; the Netherlands:
   1834, 1821, 1808, 1795, 1783…). Rows move in lockstep. Hungary's and Peru's top 50 **never change order**, and Peru's top
   sits frozen at L299-300 for a whole month.
2. **Every country outside the 49-row table gets the same generic LOCAL board.** That covers Slovakia, Slovenia and China (the
   home markets of the sk, sl and zh-Hans launch locales) and about 200 other regions. The board has identical levels and
   identical non-first-name players for every such country. It runs on UTC because the app never passes the home offset, so the
   Chinese board peaks at 7 am. It also uses the wrong names: Slovakia gets Polish names, Slovenia gets Czech, Romanian,
   Hungarian and Greek names, and China gets English names.
3. **The first-name lists are too small** (39 Korean, 51 Polish, 59 Italian, 60 Japanese names), so a few names flood the boards:
   Minjun appears 11 times in Korea's top 200, Marco 11 times in Italy's and João 10 times in Brazil's. There are no
   native-script names at all.

All three have to be fixed **before v1.0**. After release, any change to the world model rewrites every board that players have
already seen, and that is the one thing a simulated "online" world must never do (§4, P0-3). The fix plan in §6 keeps the
Python reference as the source of truth and restores bit-exact parity by regenerating the `v552` fixtures. The `reference`
fixtures stay byte-identical, which is the same procedure SOC1b and SOC1c followed.

---

## 1. How the international system works today

| Piece | Where | What it does |
|---|---|---|
| Home country | `App/Shell/Social/SocialModel.swift:179-189`, `SocialState.setHomeIfNeeded` (`Packages/.../SocialState.swift:116`) | `Locale.current.region?.identifier`, uppercased. Any 2-letter code is accepted, anything else (nil, UN M.49 numerics such as "419") falls back to `social.json fallbackCountry` = "US". It is frozen at the first `SocialModel.install`, which happens effectively at first launch because the Leaderboard page is pre-rendered behind Loading (INFERRED). `-pc.socialCountry` overrides it for tests. The device UTC offset is stored in `offsetMinutes` and **never read** (VERIFIED code). |
| Country table | `design/social/data/countries.tsv` (= `App/Resources/Social/countries.tsv`, identical), Swift copy `SocialModel.swift referenceCountryTuples` | 49 ISO codes (US has two rows), each with a weight, a **fixed standard UTC offset**, one culture and one of 9 timezone buckets. Shipped TR weight 0.30 (§14.2). |
| Cohorts | `socialsim/population.py _add_period/_add_cohort`, Swift `Population.swift:150-200` | Per join week p, bucket b and archetype a (tourists per day): one cohort of n players. **The cohort's single country is picked from its bucket's rows by one hash (`ccountry`).** All members share that country, culture, offset and daily session windows. Member j sits at u = (j + v)/n, so levels are monotone in j and every query is a per-cohort binary search. |
| Not in the table | `population.py LOCAL_SHARE = 0.003`, Swift `SocialEngine.population(for:)` (`Leaderboards.swift:55-66`) | A device-only LOCAL partition: +0.3 % of the world as extra cohorts in a 10th bucket, with culture from `EXTRA_CULTURE` (default 'en'). The offset is `config.homeOffsetMinutes` if `config.homeCountry == iso`, else **0**. The app never sets either field (VERIFIED code: `grep homeOffsetMinutes` finds only the declaration, `Leaderboards.swift:60` and one test). The LOCAL population is a **second full copy** of the world (all shared buckets + LOCAL), built lazily on the first query. `warmUp` only warms `shared` (`Leaderboards.swift:437-441`). |
| Names | `names.py drawn()` (shipped SOC1c), `data/social_names.json` | 80-90 % of non-tourist players have a custom name. The culture-dependent styles (given .24, name+suffix .19, underscore .005 of custom names) draw from the cohort culture's list by popularity (40 % uniform over the head, else index ⌊n·u²⌋). Every list is Latin-script; JP, KR, AR, IN and SEA names are romanised. |
| Blocklist | `data/blocklist_*.txt`, `block_names.txt` → `social_names.json` | Stems in EN TR DE FR ES PT IT NL only. |
| Clock and events | `SocialClock.swift`, `SocialCalendar`, `core.py` | Event day = 07:00 UTC, week = Monday 07:00 UTC (VERIFIED phone, 12 countdowns). `simNow = max(device, highWater)`, with a one-time rebase when the clock is more than 30 days behind. All model times are epoch seconds. The device time zone is never used (VERIFIED code). |
| UI | `App/Shell/Pages/SocialShells.swift:160-181` `CountryName` | Tab label = `Locale.current.localizedString(forRegionCode:)`. Any non-Turkish UI gets the English override "Turkey". It falls back to the `ui.json lb.countryShort` short name, which has EN and TR entries only, and then to the ISO code. Rows show rank, avatar, name and value, with **no flags**. That matches the original (VERIFIED phone, V2 31.5 s / 33.5 s). |
| World epoch | `core.py EPOCH = 2026-04-27 07:00 UTC` | This is the original's launch day, not ours. |

---

## 2. What was run

- `intl_sample.py`: builds the shipped world plus LOCAL partitions and samples 15 countries (US DE FR ES IT BR TR JP KR CN PL
  SK SI IN SA) at **local 03:00 and 20:00 on Mon 2026-09-28**, using the real DST offsets of that date (US −4, EU +2, BR −3,
  TR/SA +3, IN +5:30, CN +8, JP/KR +9). For each it records board size, top 10, the ±10 window around an L60 and an L250 player,
  how many of the top 100 moved in the hour before and after, style and culture mix, 24-hour activity curves, World top 100 by
  country, Weekly and Streak groups, and country sizes to 2029. For LOCAL countries (CN SK SI) it samples both the app's
  current offset 0 and the intended offset.
- `intl_week.py`: a whole week, local 08:00-23:00 (112 daytime hours) for 22 countries. It counts **dead hours** (no top-100
  row moved during the hour), the median number of movers and how many cohorts the top 100 comes from.
- `order.py`: whether the top-50 order changes over 1, 7 and 30 days, and which archetypes make it up.
- `ladder.py`: same-cohort adjacent pairs in each Country top 20. A pair from one cohort is an evenly spaced ladder step.
- `rep.py`: the most repeated first names in each Country top 200.
- `blocks_proto.py`, `jitter.py` (scratch prototypes of the fixes, not shipped): they measure the same metrics with per-member
  country blocks and with stratified u-jitter.
- `age.py`: the world's size and top levels by world age.

---

## 3. What already works (VERIFIED unless noted)

- **The event clock is global and time-zone proof.** Days and weeks anchor to UTC (07:00, Monday 07:00), as a real server's do.
  Changing the device time zone or crossing a DST switch changes nothing: every model time is an epoch second, and the device
  zone is never read (code). Countdowns are durations (code).
- **Monotone and bounded.** There were 0 level decreases in 300 cohorts × 3 times, with or without the proposed jitter
  (`jitter.py`). A member's pace is capped at 0.40-0.65 levels per minute inside session windows, and the day budget
  (1,200 min) is never reached by the shipped archetypes. The biggest cohort-day is about 190 levels (grinder 108 × a peak
  volume day of about 1.75), against more than 480 needed to reach the cap even at the slowest pace (INFERRED from
  `population.py sessions()`). There are no impossible jumps.
- **Big boards look alive.** Dead daytime hours in a week: US 2 of 112, GB 1, BR 1, IN 3, DE 12. Board activity follows local
  evening peaks: KR 20:00 → 76 of the top 100 move in the next hour, DE 76, FR 77, while US/FR/ES/IT/JP/KR at 03:00 → 0-10.
- **World and group mixes are plausible for a global game.** World top 100: US 29-30, DE 12, GB 9, CA 8, then HK, AU, FR, ES 4
  each, JP 2, KR 2… Weekly groups and Streak Races are matched among players online around the join, so a Japanese player
  joining at 03:00 JST meets Americans and Europeans, and at 20:00 JST meets a mix (RU, DE, US, PH, NL, JP, BR).
- **Scripts that the display font covers:** PCDisplay-Black has glyphs for Latin-Extended including every Slovak and Slovene
  letter (ľ ĺ ŕ ô ä ď ť ň š ž č), Turkish, Polish, Cyrillic and Vietnamese. It is **missing** Greek, Hiragana, Katakana, Han,
  Hangul, Arabic, Devanagari and Thai (checked with fontTools).
- **Flags:** none on any row, as in the original. Nothing to fix.

---

## 4. Findings

### P0: must be fixed before submission

**P0-1: small and mid-size countries are built from a few whole cohorts, so their boards show evenly spaced ladders,
move in lockstep and never reorder.** VERIFIED (run).

Root cause: each cohort takes one country (`population.py:_add_cohort`, "pick one row of the bucket"). The committed
archetypes (regular, enthusiast, grinder) produce 3 cohorts per bucket per week, so a country with 5-20 % of its bucket's weight
gets one committed cohort every 1-7 weeks. Inside a cohort, u = (j + v)/n is evenly spaced, λ(u) is piecewise-linear and the
session windows are shared. Neighbouring members of one cohort therefore stand an equal number of levels apart forever, move in
the same minutes and can never overtake each other. That is the containment property the binary search relies on (§2.5).

| Country | board (28 Sep) | top-100 made of N cohorts | same-cohort pairs in top 20 | dead daytime hours / 112 | top 5 levels |
|---|---|---|---|---|---|
| Peru | 965 | **1** (one dabbler cohort) | 19/19 | **112** | 300, 300, 299, 299, 299 (frozen for 30 days) |
| Hungary | 2,111 | **1** (one casual cohort) | 19/19 | **112** | 1114, 1110, 1107, 1104, 1101 (order never changes; all +16 in 30 d) |
| Netherlands | 5,209 | 3 | 19/19 | 84 | 1834, 1821, 1808, 1795, 1783, 1770 (−13 each) |
| Czechia | 1,470 | 3 | – | 75 | 5099, 2434, 1731, 1714, 1696 |
| Portugal | 1,990 | 8 | – | 58 | 3674, 2246, 2194, 2142, 2090 (−52 each) |
| **Spain** (es) | 6,233 | 4 | **14/19** | 43 | 6022, 5630, 5229, 4829 (−392, −401, −400) |
| **Korea** (ko) | 2,672 | 7 | **14/19** | 42 | 8343, 5440, 3331, 2774, 2393 |
| **Turkey** (tr) | 1,662 | 5 | **12/19** | 48 | 4744, 3691, 3050, 3025, 2426 |
| **France** (fr) | 13,577 | 8 | **10/19** | 48 | 10025, 9890, 4971, 4910 (pairs) |
| **Italy** (it) | 6,433 | 6 | 8/19 | 37 | 6052, 5135, 4443, 4096 |
| **Poland** (pl) | 5,427 | 4 | 5/19 | 38 | 4291, 4246, 3705, 3654 |
| **Japan** (ja) | 5,934 | 10 | 6/19 | 19 | 12066, 5878, 4351, 3769 |
| Germany (de) | 14,767 | 16 | 1/19 | 12 | healthy |
| US / GB / BR / IN (en, pt-BR) | 110k / 25k / 14k / 7k | 34 / 27 / 25 / 26 | 0-1/19 (GB not measured) | 1-3 | healthy |

A quiet top is realistic in itself. The phone's real Turkey top 7 barely moved in 12 hours: #1 Caco17 climbed steadily, two
others moved once (+5, +6) and four never moved (VERIFIED phone, social-dynamics §C and §I-B). What gives the simulation away is the ladder and the lockstep: real players at the top of a
board never stand at exact equal steps, and a whole board never freezes in one order for a month. The Peru, Hungary and
Netherlands boards would read as fake to anyone who looks twice. Spain, Korea, Turkey and France (launch locales) show the same
pattern in their top 20.

**P0-2: every region missing from the 49-row table gets one shared, mis-timed, mis-named LOCAL board.** This covers three
launch-locale home markets (SK, SI, CN) and about 200 other regions. VERIFIED (run + code).

- **Identical skeleton.** LOCAL cohort keys and gids do not include the ISO code, so every LOCAL country gets the same cohorts,
  levels and non-culture names. The Slovak and Slovene boards at the same instant (03:00 CEST) match row for row:

  | # | SK (LOCAL, culture 'pl') | SI (LOCAL, culture 'easteu') | CN (LOCAL, culture 'en', another instant) |
  |---|---|---|---|
  | 1 | kinga 3269 | KATERINA 3269 | Angela 3264 |
  | 2 | Kamil 2669 | IONUT 2669 | toni 2583 |
  | 3 | Kinga 2519 | Daria 2519 | Nola 2519 |
  | 4 | Piotr 2476 | Jiří 2476 | James 2488 |
  | 5 | przemysław 2451 | Radu 2451 | Joshua 2420 |
  | 6 | **W610 2238** | **W610 2238** | **W610 2238** |
  | 8-10 | **player_ordaisd 1816, player_2gr5ypb 1814** | same | **player_2gr5ypb 1824, player_ordaisd 1816** |

  Every LOCAL board also has 1,024 players on 28 Sep, whether the country is Iceland, Slovenia or China. The size does not depend
  on the country.
- **Wrong clock.** The app never sets `config.homeCountry` or `homeOffsetMinutes`, so `population(for:)` builds every LOCAL
  partition at offset 0 (UTC). China's board peaks at local 07:00 (17 movers) and is quiet at 19:00-20:00 (2-6). Slovenia's
  peaks around 01:00. Hourly curves: CN@0 is CN@+480 shifted by about 8 hours (`boards_15_countries.json` → `hourly`). The
  only test of this path, `SocialWorldAPITests.testLocalCountry`, uses Iceland at offset 0, the one country where the bug cannot
  show.
- **Wrong names.** `EXTRA_CULTURE` maps SK to Polish (przemysław, Krzysztof, Grzegorz), SI to 'easteu' (a mix of Czech,
  Romanian, Hungarian, Greek and Ukrainian names: KATERINA, IONUT, Jiří, Laszlo, Zsófia) and CN to English (Angela, James,
  Joshua, Bernadette). A Slovene sees no Slovene name and a Slovak no Slovak name.
- **Rule 1 broken.** On an SK device the World board contains about 1k extra LOCAL players that no other device has, so World
  ranks differ between two friends (by up to about 0.3 %).
- **Cost.** It keeps a second full world in memory. The first leaderboard open for these users builds it cold, off the main
  thread, because it is never warmed (INFERRED cost; not measured on device).
- Territories iOS offers as a region (IC Canary Islands, EA Ceuta & Melilla, AX, GG, JE, IM, GU, PR, RE, GL, CW, XK, AQ, PN…)
  also land here. The Canary Islands get an English-named "Canary Islands" board of 1,024 players; Pitcairn (about 50 people)
  gets one of the same size.

**P0-3: the world model has to be final at v1.0.** INFERRED from rule 3, which is binding (SPEC-social §0).

Every level, name and country is a pure function of the model constants. Any later change, whether a new table row, a weight,
a culture, a name list or the epoch, moves every existing player at once: values jump both up and down and names change.
Rewinding is the one thing the simulated server must never do. So P0-1, P0-2 and the P1 data items below must land in **one**
model revision before submission. After release, evolution has to be append-only: new parameters may apply only to join periods
p ≥ the change's period, which is possible because cohorts are per period and never touch existing players. One consequence for
the owner: the current dev install on the phone will see its boards reshuffle once when the new model lands (pre-release only).

### P1: needed for "feels online" in every launch locale

**P1-1: first-name lists are too small, so the same names repeat.** VERIFIED (run, `rep.py`, Country top 200):

| Country | list size | most repeated first names in the top 200 |
|---|---|---|
| KR | 39 | Minjun **11**, Minho 5, Siwoo 3 |
| IT | 59 | Marco **11**, Giovanni 4 |
| BR | 62 | João **10**, Ricardo 4 |
| SE | 71 | Axel **9**, Erik 7 |
| DE | 100 | Lukas 7, Niklas 4 |
| JP | 60 | Haruto 7, Yuki 6 |
| NL | 54 | Daan 7 |
| FR / ES / PL / TR / IN / SA | 87 / 93 / 51 / 121 / 79 / 53 | 5-6 each |
| US | 2,207 | James 3 |

The draw gives the #1 name of a 39-name list about 10.6 % of first-name draws (0.4/39 + 0.6·√(1/39)), against about 2 % for 'en'.
The lists also skew to baby names (Minjun and Haruto are top names of the 2010s), while the players are adults (INFERRED).
Fix: at least 300 names per culture with adult-age distributions, from Wikidata (CC0, the source SOURCES.md already approves) or
national statistics offices, and a popularity head scaled to the list size.

**P1-2: mixed culture pools, and one culture per country.** VERIFIED (data). 'easteu' gives CZ, HU, RO, GR, UA and RU (plus SI,
HR, RS, BG, LT, LV, BY and KZ through LOCAL) one shared pool, so a Russian board shows Zsófia, Ionuț and Eleni. 'sea' gives PH,
ID, MY, TH, VN and SG one pool (Jhon, Rodel, Budi, Minh, Wei). Bilingual countries use one language: BE → Dutch only (French
speakers are about 40 %), CH → German only, CA → English only (Québec), IL/TW/HK → English, and PT gets Brazilian-specific names
(Wellington, Rogério). The fix is a culture per language (sk, sl, cs, hu, ro, el, ru, uk, bg, hr/sr, th, vi, id/ms, tl, zh, he,
…) and a per-row culture mix (e.g. BE nl .6 / fr .4) drawn per member.

**P1-3: there are no native-script names.** VERIFIED (data), with impact INFERRED. The JP, KR, SA and IN boards are 100 %
Latin, and CN would be English. On global casual games many Japanese, Korean and Chinese players use kana, kanji, Hangul or Han
nicknames (INFERRED; there is no phone evidence for these countries, and the original's global boards showed 0 CJK names in
about 150, which fits boards dominated by US and TR players). The data format already supports it: each given-name token is
`[native, folded]` and 70 % of draws use the native spelling. The display font lacks these scripts, so rows would render through
CoreText fallback glyphs inside GameText's outlined path renderer (`GameText.swift:108-140`, `SocType.swift:110-125`). That
should work, since fallback runs are converted to paths, but it is **unverified**, and the fallback weight will not match Nunito
Black without an explicit bold cascade list. The same applies to the ja, ko and zh-Hans Country tab labels (日本, 대한민국, 中国)
and to users typing native-script usernames. The share of native script is an owner decision (§7).

**P1-4: vulgar invented handles in the new launch languages.** VERIFIED (data scan of the 40,000 invented handles). Found:
**Jeba, Jebi, Jebin, Jebos, Jebyr, Jebyx** ("jebi" is an imperative obscenity in Slovene, Croatian and Serbian; the Polish verb
shares the root), **Drekes/Drekir/Drekor/Drekos** (Slovene "drek" = crap), Zhope/Zhopak/Zhopax… (Russian жопа, "arse"), Sukax
(Slavic "suka"), Chutas/Chuter/Chuto/Chutyk (Hindi vulgar), Kusok (Japanese "kuso"), Shabin (Chinese "shabi"). The blocklist
covers EN TR DE FR ES PT IT NL only. Each handle is rare (about 7.6 × 10⁻⁶ of players), but "Jebi" on a Slovene board is a real
embarrassment. The fix is stems for SL, HR, SR, SK, CS, PL, RU, UK, JA and KO romanisation, ZH pinyin, AR romanisation and HI,
plus native-script stems once P1-3 adds those scripts. Use token rules where a substring would hit real names (e.g. "suka" is
inside "Asuka").

**P1-5: the world is about 5 months older than our app.** VERIFIED (run, `age.py`). The epoch is the original's launch
(27 Apr). On our release day (about mid-October, world age about 170 days) the World #1 is around L17,000 and a L60 player ranks
about 140,000th. A top player at 17k levels in a game that came out yesterday does not "work logically":

| world age | players | World #1 | #100 | a L60 player's World rank |
|---|---|---|---|---|
| 1 d | 4,285 | L100 | L53 | 24 |
| 28 d | 82,408 | L2,861 | L941 | 27,563 |
| 56 d | 139,335 | L5,672 | L1,389 | 52,360 |
| 154 d | 338,258 | L15,652 | L4,758 | 131,678 |
| 365 d | 803,827 | L37,007 | L14,976 | 318,637 |

This is an owner decision (§7). My recommendation is a shipped-model epoch equal to our release Monday minus 4 weeks (a "soft
launch" story: about 80k players and a #1 near L2.9k on day 1). The reference EPOCH stays. The event anchor (Monday 07:00 UTC)
is unaffected by the choice.

**P1-6: wording that claims real people.** VERIFIED (strings, SPEC-social §10/§12 risk note). "Compete against your friends!"
(there is no friends feature) and "Finding players on your level." present simulated players as people. The store text must
never claim online or multiplayer play, and the in-app "friends" line is the weakest point with App Review (Guideline 2.3.1,
accurate metadata; INFERRED risk). The owner decides (§7).

### P2: polish

- **P2-1 Country tab name.** (a) It uses `Locale.current` (device) rather than the app's resolved language, so with a per-app
  language set to Deutsch on an English device the tab says "Germany". (b) The `englishNames["TR"] = "Turkey"` override applies
  to every non-Turkish UI, so German shows "Turkey" instead of "Türkei" and Japanese shows "Turkey" instead of トルコ. (c)
  `lb.countryShort` has EN/TR pairs only. VERIFIED code (`SocialShells.swift:166-181`).
- **P2-2 DST.** The model uses fixed standard offsets, so for about 8 months a year the US and EU evening peaks run 1 hour late
  against real clocks. This is invisible in practice. **Never model DST by switching offsets:** the autumn switch replays local
  minutes, and progress could go backwards (INFERRED from `lcum`). Keep the fixed offsets.
- **P2-3 Clock set back.** The whole world freezes until real time catches up, and countdown timers stop. The user caused it and
  it is safe, but it is a visible tell. Optional: while the wall clock is behind the high-water mark, advance simNow by the
  device's continuous (monotonic) time since the mark within the same boot, and freeze only after a reboot.
- **P2-4 Username length.** At least 3 characters rejects the normal 2-character CJK and Hangul names (민수, 小明, 太郎). The
  rule should be at least 2 characters for Han, Hangul and kana (`Names.swift:447-456`).
- **P2-5 Pace reference at the day boundary (INFERRED).** For US-west players the 07:00 UTC day starts at local 00:00 (23:00 in
  winter). An evening session that crosses it counts as two "active days", which halves the Streak Race reference so rivals are
  weaker.
- **P2-6 Dead code and state.** `data.py HOME_FLOOR_SHARE` is unused. `SocialState.offsetMinutes` is stored and never read.
- **P2-7 Groups are global.** Weekly and Streak rivals are drawn from the whole world by who is online (§3). That is correct for
  a global game, and the original's matchmaking is unknown. A home-region bias is possible but not recommended.

---

## 5. The 15 sampled boards (local 03:00 / 20:00, Mon 2026-09-28; VERIFIED run)

"moved" = top-100 rows whose level rose in the hour before the sample; "next" = in the hour after it. Culture = the name pool
the board draws from.

| Country | players | culture | moved 03:00 / 20:00 | next after 20:00 | L60 rank | L250 rank | sample names (top 10 at 20:00) |
|---|---|---|---|---|---|---|---|
| US | 110,822 | en | 9 / 23 | 7 | 44,399 | 17,859 | Klaizex 14994, dreypar, Klaypor58, Kaylietron, Zhobas, Jamalking, Arlene |
| DE | 14,821 | de | 22 / 34 | 76 | 6,121 | 2,198 | Snaysan 15671, lisa, Dennistastic, FluffyLion, T8C, Dieterfan, julian |
| FR | 13,634 | fr | 0 / 2 | 77 | 5,865 | 1,410 | NobleCactus 10025, Ambre, lucaszor51, senun, ShadowCaptain, Benoît, Lina |
| ES | 6,241 | es | 0 / 0 | 36 | 1,571 | 1,219 | Bleezux 6022, Proony, flayzes, josé, Veronica, Alejandro, ivan, ALEJANDRO |
| IT | 6,477 | it | 0 / 75 | 62 | 1,742 | 656 | Salvatorequeen 6052, Federicabot, Heem, stefanogamer, Giovanni, Nicolò |
| BR | 14,033 | pt | 0 / 14 | 6 | 4,847 | 1,872 | neymor 8642, blykux, faysek, fibon32, Wellington, Ricardo, rogerio |
| TR | 1,672 | tr | 0 / 6 | 6 | 432 | 87 | Yusuftron 4737, Stesyn, Plyti, Kemal, eren_q, ScarletChef, Canlicious |
| JP | 5,988 | jp (Latin) | 0 / 14 | 25 | 1,971 | 837 | Truris 12046, Haruto, Ringamer, LazyTiger27, Aoixo, Diris, N632, Kaori |
| KR | 2,672 | kr (Latin) | 0 / 7 | 76 | 904 | 510 | Minjunking 8265, WildScout, Siwoo, HyperSage, Siwoopro, Minjuninator, Minjun |
| CN (LOCAL, app = UTC) | 1,027 | **en** | **10** / 6 | 12 | 388 | 163 | Angela 3268, toni, Nola, James, Joshua, W610, Jamesxo |
| CN (LOCAL, +8 intended) | 1,027 | en | 0 / 5 | 6 | 391 | 162 | same skeleton |
| PL | 5,427 | pl | 0 / 17 | 17 | 1,459 | 885 | treelo 4291, Plesar, jaroslawwolf, LoudRunner, Piotr, Marcin |
| SK (LOCAL) | 1,028 | **pl** | 0 / 5 (+2) · 2 / 2 (UTC) | 6 | 389 | 164 | kinga, Kamil, Kinga, Piotr, przemysław, W610 |
| SI (LOCAL) | 1,028 | **easteu** | 0 / 5 (+2) · 2 / 2 (UTC) | 6 | 389 | 164 | KATERINA, IONUT, Daria, Jiří, Radu, W610 |
| IN | 7,124 | in | 0 / 19 | 11 | 2,633 | 927 | player_jrour7j 8021, Rajeshwolf, Glera, Naveenxo680, Karantastic |
| SA | 2,902 | ar (Latin) | 0 / 2 | 9 | 1,231 | 424 | rashidzilla15 9945, ShadowGrandpa15, Hudainator, Hani, huda |

24-hour activity curves (top 100 + the L60 window, movers in the previous hour, local hours 0-23):

```
US@-4   34 34 13  9 11  3  2  0  7 12  3  8 23 16 19 10 20 10 19  9 23  7 36 45
JP@+9   20  0  5  0  0 19  0  0 24 41 31 31 32 10  6 16 19 39 20 21 14 25 39  4
BR@-3    4  5  2  0  0  0  7  2  3  7 19  4 14 12 24 23 11 12 19 25 14  9 17 19
TR@+3   36  0  0  0  0  0  0  0  0  0  0  0  0  0  0 17 37  2 39  6  6  6  1 39   <- lumps of 5 cohorts
IN@+5:30 14 6  6  0  0  1  0  7  2  7  7  3 25 17 12  9  5  4  1 27 21 12 20 21
CN@UTC   2  5  7 10  3  7 10 17  4  2  2  0  0  3  1  5  1  4 13  2  6 12  2  7   <- today's app: peak 07:00
CN@+8    4  2  2  0  0  3  1  6  2  3 13  2  6 12  2  7  6  8  3 12  5  6 16  9
SK@+2 = SI@+2 (identical)
```

Weekly and Streak groups (seed 777; each install has its own seed): a JP player at 03:00 gets Weekly rivals from US, CA, PL, FR,
ZA and SA, and a Streak Race of US 23 / GB 6 / DE 4 / … with 21 of 49 scoring in the first hour. At 20:00 the rivals come from
RU, DE, US, PH, NL, JP and BR. This is plausible for a global game. Country sizes grow from 28 Sep 2026 to 2029: US 110k → 953k,
TR 1.7k → 12k, KR 2.7k → 31k, LOCAL 1.0k → 8.9k (`boards_15_countries.json` → `sizes`).

---

## 6. Fix plan (data + code, bit-exact with the Python reference)

Procedure (the SOC1b/SOC1c pattern): every new mechanism goes into the reference modules **switched off by default** and is
switched on in `design/social/tools/socialsim/shipped.py apply()`. The prototype stays byte-identical: `design/social/fixtures/*`
and `Tests/Fixtures/soc_reference_*` regenerate with an empty git diff, which proves it. Then the `v552` fixtures are regenerated
and the Swift is changed until the goldens match bit for bit (Debug and -O). Never edit a fixture by hand.

### 6.1 Model (Python first, then Swift)

| # | Change | Python | Swift | Fixes |
|---|---|---|---|---|
| M1 | **Per-member country blocks.** Each shared cohort splits its n members into contiguous index blocks, one per row of its bucket, sized by systematic apportionment of the row weights (one offset u per cohort, label `cblk`), in a per-cohort hashed row order (label `cord`). A member's iso and culture come from its block. Sessions, levels and gids are unchanged, so the **World board's levels do not change**; only country membership and culture-styled names do. Country queries: `count = max(0, e − max(boundary, s))` per (cohort, block); `top` and `neighbours` merge (cohort, block) units. | `population.COUNTRY_BLOCKS` (+ `blocks(c)`, `count_ge/top/neighbours/boundary` with an iso filter over blocks), `shipped.apply()` sets it | `Population.swift` (cohort `blocks`, iso to [(cohort, block)] index built in `extend`), `Leaderboards.swift` level boards | P0-1 |
| M2 | **Stratified quantile jitter.** u_j = (j + u01(S,'uj',ck,j))/n replaces (j + v)/n. u stays strictly increasing in j, so monotonicity, containment and the binary search stay exact. It breaks the equal-step ladders. | `population.U_JITTER` in `u_of` | `member()` / `u(of:)` | P0-1 |
| M3 | **Country table v2.** Every region `Locale.Region.isoRegions` can report (about 250) gets a row or an **alias** (IC/EA→ES, AX→FI, GG/JE/IM→GB, GU/VI/AS/MP→US, RE/GP/MQ/GF/YT/PM/BL/MF/NC/PF/WF→FR, CW/AW/SX/BQ→NL, GL/FO→DK, SJ/BV→NO, uninhabited AQ/HM/TF/UM/IO/PN→a documented fallback). Columns: iso, weight, standard offset, **culture mix**, bucket. The existing 49 weights stay; new rows get proxy weights (§7-4) and TR is re-fitted under M1. Buckets are split so every row is within ±60 min of its cohorts' schedule offset (NZ/Pacific gets its own bucket; AE joins the +180 group). | `data/countries_v2.tsv`, `data.REGION_ALIAS`, `data.COUNTRIES_V2` switch | `SocialWorldModel` v2 tuples + alias map (a test compares them row for row with the TSV, as today) | P0-2 |
| M4 | **LOCAL partition only for unknown codes**, keyed by the ISO (LOCAL `ck` and gid base salted with the 16-bit ISO code), offset from the static table / alias parent, **never the device**. It is warmed at launch together with `shared`. | `population.World(local=…)` salt | `population(for:)`, `warmUp(to:country:)`, `AppModel.makeWorld` passes the home country | P0-2 |
| M5 | **Per-member culture** drawn from the row's culture mix (label `mcul` on the gid). New cultures are **appended** to `CULTURES`, so the token keys (`_tokkey` uses the culture index) of the existing 16 stay stable. | `names`, `data.CULTURES` | `SocialWorldModel.cultures`, `Names.swift` | P1-2 |
| M6 | **Native-script share per culture** (owner decision §7-2): `VARIANTS['nativeP'][culture]` replaces the global 70 % for cultures whose native form is non-Latin. The name+suffix and underscore styles keep using the Latin `mixedTokens`. | `names.build` | `SocialNames.build` | P1-3 |
| M7 | **Popularity head scaled to the list size** (`headN = min(50, n/6)`, `headP` lower for short lists) as a safety net for lists that stay small. | `names.drawn` | `SocialNames.drawn` | P1-1 |
| M8 | **Epoch** (if the owner agrees, §7-1): `shipped.WORLD_EPOCH` for the world only; the event calendar keeps any Monday 07:00 UTC. | `core`/`population` use `W.epoch` | `SocialCalendar` world epoch vs event anchor | P1-5 |

### 6.2 Data

- `design/social/data/given_*.txt`: at least 300 adult-age names for each of about 25 cultures (en kept; new sk sl cs hu ro el ru
  uk bg hr sr th vi id ms tl zh he; existing jp kr ar pl it pt-BR/pt-PT es fr de nl nordic in tr expanded). Sources: Wikidata
  (CC0) and national statistics offices (SK ŠÚ SR, SI SURS, CZ ČSÚ, …: public factual data). Record the queries and dates in
  `design/social/SOURCES.md`. Native forms for jp, kr, zh, ar, ru, uk, bg, el, th and he as `[native, latin]` pairs, so the
  Latin form is an explicit romanisation (NFKD cannot romanise kana).
- Blocklists: add stems for SL, HR, SR, SK, CS, PL, RU, UK, JA romaji, KO romanisation, ZH pinyin, AR and HI romanisation, plus
  native-script stems for every added script. At minimum: `jeba jebi jebe jebo jebu zhop kurw chuj pizd kokot kurac kurc blyat
  blyad chutiy madarch bhench bhosd sharmout sibal ssibal shibal caonima shabi`, with token-only rules for `suka drek chut kuso
  nima` (they occur inside real names).
- `tools/build_name_data.py` regenerates `data/social_names.json`. Copy it to `App/Resources/Social/social_names.json`; both
  copies must be byte-identical, and so must the `countries*.tsv` copies. Python and Swift read the same JSON, so name parity
  holds by construction.
- `name_audit.py --v552` over the whole world to 2031: 0 blocked, 0 longer than 16, repeat rate inside the phone's interval.

### 6.3 Tests (Python `tests.py` → Swift `SocialPropertyTests` 1:1, plus goldens)

1. Country count = brute force over blocks for 10 countries × 3 dates. Top and neighbours per country = brute force.
2. Monotone in u and t with jitter (the existing tests 2-4 keep passing unchanged).
3. Two LOCAL ISO codes give different skeletons; the shared world stays byte-identical with and without a LOCAL partition
   (test 10).
4. **Every** `Locale.Region.isoRegions` code resolves to a table row or an alias (a Swift test on the macOS host; Python gets the
   list as a fixture).
5. No board-visible name contains a blocked stem in any of the 13 launch languages. A native-script sample of names round-trips
   through `validateUsername` rules.
6. New calibration guards (SocialCalibrationTests): for every country with at least 1,000 players, dead daytime hours ≤ 20/112
   in the reference week and at most 8/19 same-cohort adjacent pairs in the top 20, with no equal-gap run longer than 3; the
   most repeated first name ≤ 4 % of the first-name rows of any Country top 200. The existing phone guards stay (World #1-#7,
   #24/#89/#132/#278 within 10-15 %; **Turkey rank at L62 = 455 ± 15 %**; the prototype gives 354 at weight 0.30, so re-fit TR
   to about 0.39).
7. Goldens: `python3 Packages/PathCore/Tests/tools/soc_fixtures.py v552` regenerates `soc_v552_{world,events}.json`, with new
   sections for blocks (40 cohorts), per-member cultures, native/Latin draws, the alias map and two LOCAL codes.
   `soc_fixtures.py reference` and `design/social/tools/make_fixtures.py` must regenerate **unchanged**.
8. Mutations (`Tests/tools/soc_mutations.py`): block order label, apportion offset, jitter label, culture-mix label, an alias
   entry and the LOCAL salt must each be **CAUGHT**.
9. Perf (SocialPerfTests, -O, 3-year world): World rank ≤ 8 ms, Country ≤ 2 ms (now iterating the bucket's cohorts instead of
   the country's), top-100 ≤ 10 ms, plus cohort-table memory before and after (not measured today). The bench (SocialBenchTests,
   52 weeks) keeps 0/0/0/0 invariants.

Before and after, measured with the M1 prototype only (`blocks_proto.py`, no jitter, no re-fit; VERIFIED run):

| Country | dead daytime h/112 | median movers/h | top-100 cohorts | same-cohort pairs top 20 | rank at L62 |
|---|---|---|---|---|---|
| TR | 48 → **15** | 3 → 6 | 5 → 33 | 12 → 6 | 430 → 354 (re-fit weight) |
| FR | 48 → **10** | 2 → 10 | 8 → 14 | 10 → 1 | |
| ES | 43 → **11** | 10 → 9 | 4 → 23 | 14 → 2 | |
| IT | 37 → 12 | 3 → 6 | 6 → 13 | 8 → 8 | |
| PL | 38 → **6** | 14 → 12 | 4 → 28 | 5 → 6 | |
| KR | 42 → **5** | 1 → 6 | 7 → 21 | 14 → 2 | |
| JP | 19 → 4 | 10 → 7 | 10 → 25 | 6 → 1 | |
| NL | 84 → 6 | 0 → 9 | 3 → 21 | 19 → 5 | |
| HU | 112 → 4 | 0 → 9 | 1 → 34 | 19 → 8 | |
| PE | 112 → 15 | 0 → 5 | 1 → 28 | 19 → 10 | |
| DE / US | 12 → 8 / 2 → 4 | ≈ | ≈ | ≈ | |

M1 alone does not remove every ladder (IT, SA and PE keep 8-10 same-cohort pairs, because a committed cohort's block is
contiguous). M2 removes the equal steps: NL 1834, 1821, 1808, 1795, 1783 (−13 each) became 1826, 1819, 1798, 1791, 1777 with
0 monotonicity violations (`jitter.py`). The two together are the fix.

### 6.4 App (after the model; the owner of App/** does these)

- `SocialShells.swift CountryName`: resolve the name with `Locale(identifier: Bundle.main.preferredLocalizations.first)`; apply
  the "Turkey" override only to an English UI; add `lb.countryShort` entries for the 13 languages, falling back to the ISO code.
- `GameTextLayout` / `SocType`: an explicit bold fallback cascade (`kCTFontCascadeListAttribute`: Hiragino Sans W7/W8, PingFang
  SC Semibold, Apple SD Gothic Neo Heavy, Geeza Pro Bold, Kohinoor Bold, Thonburi Bold, Arial Hebrew Bold) so fallback glyphs
  match Nunito Black. Verify that the outline and drop shadow follow the fallback paths.
- `validateUsername`: at least 2 characters when the name contains Han, Hangul or kana.
- `AppModel.makeWorld` / `warmUp`: pass the frozen home country, so an unknown-code LOCAL partition (if any remains) is built
  behind Loading.
- Optional P2-3: continuous-time extrapolation of simNow while the wall clock is behind the high-water mark.

### 6.5 Order and effort (INFERRED)

1. Owner decisions §7 (epoch, native-script share, CN storefront, territories, wording).
2. Python M1 + M2 + M4 and the tests (about half a day). Data M3/M5/M6 + names + blocklists (about a day; the name lists are
   the long pole). Re-calibration with `calib_s2.py` and the new guards (about half a day).
3. Fixtures, then the Swift port until the goldens and properties pass Debug and -O (about 1-1.5 days). Perf and memory gates.
4. App polish (§6.4), then simulator screenshots of the Country tab in all 13 languages for SK, SI, CN, JP, KR, XK and IC (the
   `-pc.socialCountry` and AppleLanguages arguments).
5. **Freeze the world model** (P0-3) before the submit build. It must land before the events-rotation work (`design/publish/events.md`)
   is finalised, because both touch `social.json` / `SocialConfig`.

---

## 7. Decisions for the owner

1. **World age (P1-5).** Keep the original's epoch (on our release day the world already has players at L17k), or anchor to our
   release Monday minus 4 weeks (recommended: about 80k players and #1 near L2.9k on day 1, growing from there).
2. **Native-script names (P1-3).** Recommended shares of first-name rows: ja 45 %, ko 50 %, zh 60 %, ar 30 %, ru/uk/bg 35 %,
   el 30 %, th 30 %, he 25 %, with the rest as Latin handles. The alternative is Latin-only everywhere: safer to render, less
   authentic.
3. **China mainland.** Games with in-app purchases need an ISBN licence on the China storefront. My recommendation is to exclude
   mainland China from sale (a release-plan item). The zh-Hans locale still serves SG, MY and others, and a CN row stays in the
   table (small weight) for devices set to that region.
4. **Weights for the about 200 new rows.** A documented proxy (population × iPhone share × casual-English-game affinity) with the
   launch-locale markets nudged up (e.g. SK 0.25, SI 0.12, HR 0.2), and territories aliased to their parent country's board
   (recommended) rather than given tiny boards of their own.
5. **Wording (P1-6).** Drop "Compete against your friends!", which describes a feature we do not have, in favour of a neutral
   line. Store text never claims online or multiplayer play.
6. **Freeze.** Accept that the dev install's boards reshuffle once when the new model lands, and that after v1.0 the world only
   evolves append-only (new join periods).
7. **Group matchmaking** stays global, with no home-country bias (recommended; it matches a global server).

## 8. What needs the phone (it is not available now)

1. Final look of fallback-script rows and the Country tab (CJK, Hangul, Arabic, Greek) on the iPhone 15, after the simulator pass.
2. An install-over test after the model change: the dev save (`social.json` v1: home country, highWater, week/day group keys)
   loads, the current Weekly and Streak groups re-derive without a crash, and the boards open on the player's row.
3. Optional calibration research on the original: the Turkey board's top 100 and the neighbourhood around the player's rank at
   morning hours (08:00-12:00 TRT) and at 02:00-04:00. Current evidence covers 04:31-06:38 and 12:11-16:38 only, and it would
   set the dead-hours target that §6.3-6 currently assumes.

Needs a simulator (not the phone): the 13 languages × {SK, SI, CN, JP, KR, TR, XK, IC} Country tab and board screenshots; the
username flow with 2-character Hangul and kanji names.

## 9. Limits of this audit

- The Swift and the app were not run. Every board number is from the Python reference (bit-exact with Swift per the goldens).
  The LOCAL offset bug and the tab-label issues are from code reading.
- "Feels online" targets (dead hours ≤ 20/112, ≤ 8/19 ladder pairs, ≤ 4 % top name) are my DECISION, informed by one phone
  observation (the real Turkey top 7 is mostly static, so the targets allow quiet tops but forbid ladders and frozen orders).
- The M1 prototype is a scratch script: no jitter, no re-fit and no bucket split. It shows the direction and size of the effect,
  not the final numbers.
- The perf and memory cost of M1 + M3 at 3 years is unmeasured. The existing p95s (World rank 1.2 ms against an 8 ms budget)
  leave headroom, but the Country query now scans the bucket's cohorts.
- Native-script share and country weights are INFERRED. There is no phone evidence for non-TR boards of the original.
