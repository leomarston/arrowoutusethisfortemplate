# PLAN-P — Arrow Out: from today to "submitted for review"

Planner, 2026-09-28 00:40 +03. Inputs: PLAN.md (OWNER 2026-09-28 PUBLISH list, 15 items, binding), SPEC.md rulings 1–38
(37 = PUBLISH, 38 = the orchestrator's P1 decisions) and the six P1 docs in this folder: `motion-catalog.md`, `events.md`,
`art-direction.md`, `release-plan.md`, `level-reorder.md`, `social-intl.md`. Tags: **VERIFIED** means seen in a file, clip or
API read-back (by the P1 investigator, or by me, marked "planner"). **INFERRED** covers every estimate, suspect and duration.
No code, simulator, build, render or phone was used to write this plan.

## 0. Summary

- **Scope.** The 15 owner items map to 30 build packages and 8 verification/store packages (§2, §4). They run in four lanes:
  **T** (light: text, Python, API), **R** (art renders), **slot A** and **slot B** (Xcode/PathCore). The phone has its own
  plan (§7).
- **Critical path (INFERRED).** Art (R2 → R3 → R8) → art integration and palette codemod (A4, A5) → verification (V) → store
  screenshots in 13 locales → submit. That chain is about 4–5 working days from the moment build-4 frees slot A. The social
  rework (T6 → B2, about 3 days) runs almost as long, so it starts in Wave 0.
- **The owner has to act only 3 times:**
  - (1) `fastlane spaceauth` with 2FA. This is the only hard block: create_app, the IAPs and App Privacy all wait on it.
  - (2) Create one sandbox tester, or confirm TestFlight internal, for the purchase test.
  - (3) Phone sessions: plug in and unlock, then the haptic feel checklist, a listening pass and the final acceptance.

  Every **decision** has a default (§6), so no work waits on an answer.
- **Starts now (Wave 0, light only).** Nothing heavy may run while build-4 is timing, and nothing may write under
  App/, Packages/, Tests/, UITests/ or project.yml until build-4's V1-FINAL finishes and the build is installed on the phone.
  Packages allowed now: translations to a staging folder, store text, factory scripts, the Python social model plus name data, the
  events reference, level tooling, the audio re-synthesis, the gate tools.
- **Time-critical (planner, VERIFIED clock).** Today is Monday. The weekly event reset is **today 10:00 TRT** (07:00 UTC). If the
  phone is up, record the original's home before 09:55 and after 10:05 (PH-0a). If this is missed, the next chance is Monday
  2026-10-05.

## 1. Facts that shape the plan

| fact | tag | consequence |
|---|---|---|
| build-4 still runs: V3 perf on slot A, then V1-FINAL twice-green, then the install on the phone (install over the old build, progress kept) | VERIFIED PLAN NOW | Wave 1 starts when build-4 closes. Until then, no heavy job and no write to the app tree |
| Ruling 38 already decided art D1, boss minimal set, icon IC-1, logo restyle, the name, 13 locales, iPhone-only, no CN, 12 consumables, STARTER label, rotation shape, Balloon Rise, social epoch/names/aliases | VERIFIED SPEC §38 | §6 only lists what is still open. Ruling 38 choices proceed unless the owner overrides |
| The original on the phone auto-updated to v582, and Balloon Rise is present | VERIFIED PLAN 00:35 | PH-0b records it, so B1 can build it from the phone instead of the inferred rules |
| Release builds use the FakeStore (free coins). Also missing: PrivacyInfo.xcprivacy, the RevenueCat package, version 1.0.0 | VERIFIED release §1 + planner (`StoreService.swift:170`) | A0 and A1 are P0 |
| The Apple web session expired on 2026-09-20. There is no ASC app record and no RevenueCat app yet | VERIFIED release §1 | OA1 (2FA) must be asked for as early as possible. The name is only reserved at create_app |
| The shipped bundle carries provenance. "v552" appears in 10 resource files (ui.json, social.json, Localizable.xcstrings, 2 levels…). "research/" appears in 108 files and "phone" in 21. `SocialWorldModel(name: "v552")` and `worldModel = "v552"` are in Swift. The blocklist `block_names.txt` holds "mazeout" and "grandgames" as plain text | VERIFIED planner grep (sources; the compiled .app is not checked yet) | New package B0 + gate G4c. The brand stems in the blocklist ship hashed |
| The original is silent during levels and at the win. v552 plays sound only for the UI click, the home-return cues and the unlock chime (9 cues) | VERIFIED research/sounds.md | Item 6 is about **quality**, not new moments (default in §6, OD1) |
| Our sounds are 9 WAVs made by a 318-line `sfx.py`. The matchfactory kit's `sfx.py` is 1,019 lines | VERIFIED planner | T9 rebuilds the cues on the full kit |
| Contracts that need an amendment: `Haptic` (AudioContract), `UnlockBeats` default (ShellContract), `EventOutcome` + `EventScreen.balloonRise` | VERIFIED motion §5.2/§6.7, events §8.1 | One bundled contract amend 4 in A0, re-hashed once |

## 2. Owner items → packages

| # | owner item (short) | packages | gate |
|---|---|---|---|
| 1 | characters: new, art-grade (not dough), pink boss clearly different | R1, R2, A4 | G4 |
| 2 | smooth sliding sub-pages | A2 (tab push-slide 0.50 s), PH-0c R2 | G3 |
| 3 | win logo not skippable | A2 (remove CelebrationSkip, re-state 4 tests), PH-0c R3 | G3 |
| 4 | arrows under the boss go into each other | R3 (mounted Signpost centrepiece + overlap gate), A4 | G4 |
| 5 | one-frame glitches (arrow tap, pause, quit → home) | T10 (blipscan), A3, PH-2, PH-3 | G5 |
| 6 | sounds feel cheap; use the kit | T9, A4 (files in), V3 (in-app measure) | G6 |
| 7 | vibrations on the logo, Play, pause… | A0 (Haptic cases), A2 (haptic map), H checklist | G3 |
| 8 | everything alive: pause punch, rockets moving, menu from top | A2 (punch, claims, unlock), A4 (badge loops on new art), PH-0c R1 | G3 |
| 9 | remove watch-video offers | T1 (string), A1 (UI + EconomyRules + test) | G8 |
| 10 | ASC + RevenueCat + locales + local prices, ready for review | T2, T3, T4, T5, A0, A1, B3, S1–S4, PH-4 | G7, G8, G10, G12 |
| 11 | real icon, not copied; never "Maze Out" in store text | R5, T3 (brand ban) | G4, G12 |
| 12 | re-order levels without breaking obstacle teaching | T8, B0 | G1 |
| 13 | the international social world feels online everywhere | T6, B2 | G9 |
| 14 | events come and go weekly | T7, B1, R8 | G1, G3 |
| 15 | original art at the same quality | R1–R9, A4, A5 | G4 |
| 09-27 | "send it to my phone" (install over, keep progress) | PH-1 (build-4), PH-5 (release candidate) | G11 |

## 3. Resource rules (every agent, on top of PLAN §6 machine rules)

| rule | value |
|---|---|
| Heavy jobs | These count as heavy: xcodebuild or xctest on a simulator; `swift test`, `core.sh` or lvtool compiles; app captures; 3-D renders (mfrender / art_batch fur); translation runs over 3 min of CPU. |
| Heavy concurrency | **≤ 2 at once** of {slot A job, slot B job}. PathCore `swift test` runs as slot B's job (`-j 2`). Only 2 simulators: "Maze A" and "Maze B". For the iPad audit, slot B shuts Maze B down and uses a created "Maze iPad" |
| Render lane R | One render at a time. Each batch starts only if free swap is ≥ 1 GB and memory_pressure is normal. R **pauses** during any timing run (V3-P, A2/A3 FrameProbe runs, D1b feeds). SVG batches are light and may run at any time. |
| Light lane T | ≤ 3 agents, `nice -n 10`, each command under 4 min (longer runs go to the background with a log) |
| Wave 0 fence | Until build-4 closes: no heavy job, and no write to App/**, Packages/**, Tests/**, UITests/** or project.yml. Wave 0 writes go to design/**, tools/** (new files), scripts/** (factory, additive), build/p/** |
| Hot files (sequence, never edit concurrently) | `App/Shell/Home/{HomeView,HomeScene,EventBadges}.swift`: A2 → B1 → A4 → A5. `SocialConfig.swift` / `social.json`: B1 → B2. `strings.tsv` / xcstrings: one editor at a time, claimed in `build/p/claims.txt`. Frozen ◆ contracts: A0 only |
| Palette codemod A5 | An exclusive window over App/**. Slot B runs PathCore-only or capture work meanwhile |
| Evidence | `build/p/<WP>/` (gitignored). Gate summaries go to `design/publish/verify/<gate>.json` and are committed by the orchestrator |
| Honesty | Never weaken a test. A requirement change (items 3 and 9, the re-order) re-states the test and logs it in PLAN.md with its ruling |

## 4. Work packages

Estimates are INFERRED agent wall-clock hours. "Tok" is the heavy token the package holds: A, B, R or – (light).

### 4.1 Lane T: light (Wave 0 onward)

| WP | item | what | files / owner | deps | acceptance (evidence) | tok | h |
|---|---|---|---|---|---|---|---|
| T0 DEC | all | Send the §6 sheet to the owner at their first wake. Defaults apply at each package start | PLAN.md Decisions | – | Each answer, or "default applied <time>", logged in PLAN.md | – | 0.5 |
| T1 EN | 9, 10, 13, 14 | Freeze English: drop "Video not available"; "Compete against your friends!" → a neutral line; "90% OFF" → "STARTER"; the RevenueCat Privacy ¶ (S-7); about 23 event and Balloon strings; our 6 event names; 2 notification strings | staged `design/publish/l10n/en.tsv` → tools/strings in W1 | – | `build.py --check` green after the merge; 0 hits of the ad string; brand ban clean; key list frozen (`build/p/T1/keys.sha`) | – | 2 |
| T2 L10N | 10 | 12 new languages (de fr es it pt-BR ja ko zh-Hans pl sk sl; tr reviewed). Batch 1 = the existing keys; batch 2 = the new T1 keys. Each language gets a native pass, then an adversarial review. Also a jargon glossary, plural-safe Slavic phrasing and positional `%1$@` | `design/publish/l10n/strings.<lang>.tsv` → strings pipeline in B3 | T1 | coverage 100 % × 13; 0 specifier-type/order errors; 0 unbalanced `**`; 0 brand hits; per-language reviewer verdict in `build/p/T2/review-<lang>.json` | – | 8 |
| T3 STORE | 10, 11 | Keywords researched per storefront (13), never translated. Name "Arrow Out: Arrow Escape Puzzle". Subtitle (OD6). Description, promo. IAP texts 12 × 13 (≤ 35/55). Captions 5 × 13 (= keywords 1–5). Review notes. `tools/release/{loc,meta}.py` | `design/keywords.json`, `design/captions/`, `design/publish/iap.json`, `tools/release/` | T1 | `meta.py audit`: limits 30/30/170/4000 checked after the URLs; 0 hits of maze/grand/jam/"tap away"/online/multiplayer/friends; no keywords.txt; iap.json == rules.json:shop == ArrowOut.storekit (self-check) | – | 6 |
| T4 SCRIPTS | 10 | New `scripts/asc_consumables.py` and `scripts/rc_consumables.py`. `--bundle` on `asc_submit.py` / `signing_setup.py`. `inAppPurchaseVersion` review items, and exit if any IAP is not READY_TO_SUBMIT | scripts/ (shared by 30+ apps: additive only) | – | `--dry-run` on com.manycode.arrowout makes read-only GETs only; without `--bundle` the derivation equals the old formula (asserted); an adversarial diff review | – | 5 |
| T5 ASC-RC | 10 | Scaffold `fastlane/` from the template (delete keywords.txt; no release_notes). `create_app` **early** (reserves the name). Signing. 12 IAPs: 13 locales, USA price only, all territories except CHN. RevenueCat: app + both keys + 12 consumables + offering `arrowout_shop` (never current). The `appl_` key goes into `StoreConfig.swift` in W1 | apps/mazeout/fastlane, ASC, RC | **OA1**, T3, T4 | `GET app by bundle` = 1; per IAP: 13 localizations, USA = table, `automaticPrices` total ≥ 170, TUR = the golden TRY column; RC key flags both true, 12 consumables (`build/p/T5/{asc,rc}-readback.json`). READY_TO_SUBMIT comes after the review screenshot (S1) | – | 4 |
| T6 SOC-PY | 13 | Python model M1–M8 behind switches: per-member country blocks, quantile jitter, country table v2 (about 250 rows + aliases, documented weights), LOCAL partition only for unknown codes, per-member culture, native-script shares, head scaling, **world epoch constant** (OD9). Name data: ≥ 300 names × about 25 cultures (Wikidata CC0 / statistics offices, SOURCES.md), native pairs, blocklists for the new languages. TR re-fit to about 0.39 | `design/social/**` (fixture regen into Packages goes to B2) | – | `tests.py` green; `make_fixtures.py` + `soc_fixtures.py reference` → empty git diff. Guards per country ≥ 1,000 players: dead daytime hours ≤ 20/112, ≤ 8/19 same-cohort pairs in the top 20, no equal-gap run > 3, top first name ≤ 4 %. TR rank at L62 = 455 ± 15 %. `name_audit` finds 0 blocked names to 2031. Every `isoRegions` code resolves (`build/p/T6/calib.json`) | – | 16 |
| T7 EV-REF | 14 | `rotation_ref.py` final (seed, epoch, pins). Balloon rules from PH-0b if recorded before B1's Balloon step, else events.md §5. A 1,044-week fixture | design/publish/tools | PH-0b (soft) | properties A2 hold over 1,043 weeks; two runs byte-identical | – | 3 |
| T8 LV-TOOLS | 12 | An apply tool with a sha guard (refuses a stale `design/levels.json`). The provenance-strip tool for shipped files. Re-point the 6 tools that look boards up by number (validator_selftest, c4b_bot_replay.py, render.py, replay_bundle.py, overlay_recast.py, levels_report.py) | design/tools, tools/levels | – | on a scratch copy: order byte-identical ×2; validator 0 errors + the same L6 warning; repeats 0; negative controls 20/20 CAUGHT; stripped copy has 0 hits of `research/|phone|v552|L0\d\d` | – | 4 |
| T9 AUDIO-2 | 6 | Rebuild the 9 cues on the full matchfactory kit (layered modal bells, transient + body, room, careful envelopes). Same SoundIDs, so no contract change. Same beats and pitches as sounds.md §2. Make a listening MP4 (home-return sequence, clicks, unlock) for the owner | tools/audio, `build/p/T9/wav/` → App/Resources/Sounds in A4 | – | `check.py` all pass; `check_selftest.py` catches every mutation; spectrogram next to v552's event-locked medians: bands within ±3 dB, attack/decay within ±20 ms (comparison only, never derivation); owner OK by ear, or OD1's default at A4 | – | 6 |
| T10 GATES | 5, 15, 2/8 | `tools/blipscan.py`: one-frame anomaly = frame i ≠ i−1 and ≠ i+1 while i−1 ≈ i+1, per region. `tools/copygate.py`: SSIM on blurred thumbnails + chroma-histogram overlap vs the v552 pair. `tools/feelstrip.py`: ours-vs-v552 frame strips at the measured beats | tools/ | – | blipscan self-test: 100 % of synthetic 1-frame blips caught, 0 false positives on 5 clean v552 clips. copygate reproduces art §2.1's numbers (Paused 0.93/0.88, home 0.53/0.84) | – | 5 |

### 4.2 Lane R: art (renders start only after build-4 closes)

| WP | item | what | deps | acceptance (evidence) | h |
|---|---|---|---|---|---|
| R1 CONCEPTS | 1, 11, 15 | Concept pack, drafts (about 10–20 min of renders). Per direction: a boss-v2 head next to today's, a crew hero with a 1/3-size thumbnail, an icon draft, a palette mock (Paused + HUD), a logo sketch. Sheets go to the owner; **D1 proceeds at once** (ruling 38) | build-4 closed | `art/review/concepts/*.png` looked at; copygate recalibrated on these renders (thresholds, default SSIM < 0.30 and overlap < 0.55, written to `copygate.json`) | 1.5 |
| R2 CAST | 1, 15 | Boss v2 rig (`char_boss.py`: horns, blush muzzle, amber eyes, snaggle tooth, new outfit and station), 2 Digger crew home rigs (velvet fur), 5–6 loading figures, 8 avatars, event figures. Same rig layer groups and pivots, or one mapping step for `char_sci_home_rig` / `char_wk_home{L,R}_blue_rig` | R1 | A-bar R1–R8 for each character; director grades `art/review/grades-director-v2.json` = **100 % A on heroes**, ≥ 70 % A overall; composed proofs pass copygate; rig and idle proofs run | 8 |
| R3 HOME | 4, 15 | Backdrop, station, **Signpost centrepiece** (each arrow on its own mount; sway, flip-in refill tracks), nav icons ×3, the 3 event badges **as layers** (body / moving part / smoke) for the idle loops | R2 (draft poses are enough) | pairwise mesh overlap in the centrepiece = 0; UI rects unchanged (LEVEL plate, Play, pills; diff = 0 pt); composed home vs v552 home passes copygate | 5 |
| R4 LOADING | 15 | Loading backdrop + cast; `arrowGlossy*` recoloured | R2 | copygate vs v552 Loading; looked at | 2 |
| R5 ICON | 11 | IC-1 "Out the Door", drafted at 512 px, final at 1024 with no alpha; iOS 26 dark and tinted variants; a 60/40 pt legibility strip | R2 | director A; copygate vs the original's store icon; the owner's look on the phone (PH-2) | 3 |
| R6 LOGO | 1, 15 | Restyle "ARROW OUT!" in `gen_icons.py`, 40 parts with the same layer contract; a new OFL display face for logo and titles; LOGO-SPEC tables **regenerated**, not re-measured | R1 | the ruling-35/36 art checks (OUT! peak p99 ≤ 6/255, 0 px > 41, per-frame spread, Flat swaps) pass; copygate vs the v552 logo | 4 |
| R7 BOARD-UI | 15 | Reskin tape, doors, locks, keys, pipes, boxes, corners (`corner.py`, including the `cornerWedge` id); unlock icons ×7, `pageBgPattern`, tutorial hand, pointers; 2 engine colours | R1 | hit geometry identical (anchor and bbox diff = 0 per id); `pclevels validate --sprites` 0 errors; in-place proofs on 6 levels | 4 |
| R8 EVENT-ART | 14, 15 | Headers and backdrops for 6 events (Balloon Rise new), the Claw/Balloon bars, NEW ribbon, ×2 gem; no baked text | R2, T7 | copygate vs each v552 event page; `grep` of MANIFEST: 0 stand-ins shipped | 5 |
| R9 PALETTE-MAP | 15 | `tools/palette_map.py`: scan (1,572 hex in 57 Swift files, about 436 in ui.json, SVG constants), classify by family, map to D1 keeping L\* and relative chroma. Produces a review CSV and a swatch sheet | R1 | every literal classified or explicitly excluded (0 unclassified); swatch sheet looked at | 3 |

### 4.3 Slot A: "Maze A" (App)

| WP | item | what | deps | acceptance (evidence) | h |
|---|---|---|---|---|---|
| A0 LEAD-P | 7, 8, 10, 14 | **Contract amend 4**, re-hashed once: `Haptic` += logoLetter, logoBounce, firework, rewardPop, logoSwell, keyTurn, play; `UnlockBeats` += contentCut / 0.233 s; `EventOutcome` += balloon cases; `EventScreen.balloonRise`. **project.yml** via tools/gen.sh: RevenueCat SPM pinned to an exact 5.x, MARKETING_VERSION 1.0.0 / build 1, `PrivacyInfo.xcprivacy` (CA92.1, 35F9.1, PurchaseHistory not linked), 13 knownRegions. A compile probe for `recordPurchase` | build-4 closed | frozen-contracts N/N; Debug + Release build; unit suite green; the probe compiles (`build/p/A0/`) | 3 |
| A1 STORE-APP | 9, 10 | S-1…S-8: StoreKit 2 + RC **observer mode** in Release; FakeStore only for DEBUG/tests; no chip; no dollar fallback (ShopView:328); StoreConfig. The ad removal of release §4.2 in one change: UI, `EconomyRules.rewardedAd` + rules.json + fixture + SPEC §15, art id, test re-stated as `testMoreLivesRefill`. STARTER label | A0, T1 | new tests green (Release store selection; no dollar fallback; recordPurchase once; grant survives a kill); `strings` of the Release .app has 0 "Test store" / "Video not available" / iconVideoAd / AdSlot / rewarded; More Lives looked at next to BoosterBuy in EN and DE (`build/p/A1/shots`) | 6 |
| A2 FEEL-P | 2, 3, 7, 8 | **Tab push-slide**: one strip, 0.50 s, bezier (0.372, 0.952, 0.716, 1.0), render-server animation, nav still. **Popup punch** (1.022 → 0.969 → 0.967 → 1.0 over 0.133 s, per-id flags, OD2); the band entrance per R1 (V2 punch until then). **Celebration unskippable**: remove CelebrationSkip / skip(fromTap:); keep a `celebration.running` marker; 4 tests re-stated. **Haptic map** §5 (phase 1 + 2): win beats in ui.json, button rigid 0.60, Play 0.75, the toggle order fix. **Unlock dismiss**: content cut + 0.233 s linear dim (2 pins). **Claim staging** (letters, island, linear count at +1.38) | A0, PH-0c (soft) | 20 tab slides + 20 punches, 0 frames > 20 ms (sim, advisory; the phone decides). feelstrip vs v552: slide curve within ±2 pt at u = 0.1…1.0, punch keys within ±0.005, claim beats within ±1 frame. UI test: taps at W+0.2 and W+1.30 are ignored, panel at W+4.034 ± 1 frame. HapticArbiter log: 14 win beats at the ui.json times within ±1 frame. Touched suites ×2 | 10 |
| A3 GLITCH | 5 | Scripted sim recordings: 300 arrow taps over 10 boards (plain, bump, door+key, pipe, box, corner, tape, elevator, linked); pause open/close ×20; quit → home ×20; win → home ×10; 30 tab switches; every popup ×10. Run blipscan, root-cause, fix. **Suspects (INFERRED):** FIX-A1's parked home/level layers showing for one frame when their opacity and the screen swap commit in different transactions; the arrow-exit teardown drawing a start-state or red/✖ frame; the popup dim leading its panel. Also the build-4 carry-overs: Play → intro 24–52 ms, home arrival after a win 22–47 ms | A2 | blipscan: 0 anomalies in the scripted run, twice (`build/p/A3/blips.json`); both carry-overs < 20 ms on the sim; the 5 FIX-A1 tests still green; the phone confirms in PH-2/PH-3 | 8 |
| A4 ART-INTEG | 1, 4, 6, 8, 15 | `sync_art.sh` + `uiart_gen.py`; grep Tests/ and UITests/ before removing a case (PLAN 00:18 pitfall). `HomeCentrepiece` replaces ArrowPileView (refill + haptic tick). Rig mapping. ui.json puppet tracks for the new layers. **Badge idle loops** (flags, rocket lift-off, hop; §6.4 timing, staggered). Logo v2 into WinLogoSequence. UIArt / logo pins re-measured, with the reasons logged. T9 WAVs into App/Resources/Sounds | R2–R8, T9, A2 | logo colour composite every 1/60 s frame W+0.60…1.95 passes; 0 frames > 20 ms in 11 Release celebrations; sprite check 0 errors; 0 NOT-SHIPPED ids referenced; unit + UI ×2 | 8 |
| A5 CODEMOD | 15 | Apply R9's map (exclusive window). Re-run `art_batch --svg` for rasters that bake colour. Ribbon and title-plate component changes | A4, R9 | capture of V2's 50-screen list in EN; copygate on every screen passes (`build/p/A5/copygate.json`); the hue check finds 0 px of the old chrome-blue family outside the allowed families; looked at | 6 |

### 4.4 Slot B: "Maze B" (PathCore + App)

| WP | item | what | deps | acceptance (evidence) | h |
|---|---|---|---|---|---|
| B0 LEVELS-P | 12 | Apply the order: L34–L105 permuted, L1–L33 + L70 frozen (OD8). `pin_fixtures.py`; regenerate c4b_bot_replay and the negative controls; 4 Swift call sites follow their board; sample lists mapped; `lv.sh bundle` (67 files). **Provenance strip** in shipped levels, CurveSpec `_about` (text re-pin only), the SocialWorldModel/`worldModel` "v552" name (if it feeds a seed, it waits for B2's reshuffle) | T8 | core.sh green; mutations all CAUGHT; PC_C4_FULL 8/8; LevelsBundleTests green; lvtool self-tests all CAUGHT; `grep -rE "research/|phone|v552" App/Resources/Levels` = 0 | 4 |
| B1 EVENTS-P | 14 | C3: `EventRotation` + `EventRules.Rotation` (compiled default off; all-on under uitest/capture), Balloon Rise state machine + save, hooks (`onWin` / `refresh` / joins `.notLive`), SocialConfig round-trip. S3: bar switch, NEW ribbon, ×2 gem, red last-day pulse, arrival spring. G2: week-start pages (≤ 2 per visit), notifications eventStart/eventEnding (≤ 1/24 h, 10–21 local), payout balloon segment, SocialLab week picker | A0, T7, T1; R8 for final art | events.md §8.4 A1–A9 + A11 green (A10 is on the phone); every existing suite unchanged and green | 12 |
| B2 SOCIAL-P | 13 | Swift port of M1–M8 (Population, Leaderboards, Names, SocialWorldModel v2 + aliases, LOCAL at launch); fixtures from T6; App: CountryName in the app's language (the Turkey override for EN only; countryShort × 13), validateUsername ≥ 2 characters for Han/Hangul/kana, makeWorld passes the home country. Then **freeze** the world | T6, B1 | goldens bit-exact in Debug and -O; SocialPropertyTests 1:1 with tests.py; new calibration guards; SocialPerfTests: World ≤ 8 ms, Country ≤ 2 ms, top-100 ≤ 10 ms + memory; soc_mutations CAUGHT; `design/social/FROZEN` sha written | 12 |
| B3 L10N-APP | 10 | Merge the 13 languages into strings.tsv → xcstrings. Bold fallback cascade for PC Display (Hiragino Sans W8, Apple SD Gothic Neo Heavy, PingFang SC Semibold; Geeza/Thonburi/Arial Hebrew/Greek for names); outline and shadow follow the fallback. **Fit sweep**: every screen × 13 languages (`-AppleLanguages`), the `tr_review` fit rule generalised; failing rows get shorter phrasings from T2. Country tab × 13 languages × {SK, SI, CN, JP, KR, TR, XK, IC} | T2, B2 | 13 `.lproj` in the .app, plutil OK; fit 0 failures (`build/p/B3/fit.json`); CJK Pause/Shop/Win/Leaderboard/Claw/unlock looked at in ja/ko/zh-Hans | 8 |

### 4.5 Verification and store (Waves 3–4)

| WP | what | tok | deps | acceptance → gate |
|---|---|---|---|---|
| V1-P | All suites **twice**: core.sh (+ PC_C4_FULL, all mutation scripts, frozen N/N) on B; app unit + full UI on A | A+B | all build WPs | G1 |
| V2-P | FEEL fidelity strips (G3) + copygate on every screen + an adversarial "copied?" review (G4) + blipscan re-run (G5); captures on B | B | V1-P | G3, G4, G5 |
| V3-P | Release perf bench on an idle machine with R paused: soak + tab slides + punches + celebrations + week-start page + badge loops; in-app audio measured (G6) | A | V1-P | G2, G6 |
| D1b-P | Phone PH-3: FrameProbe on the same list, glitch scan, haptics | phone | V3-P | G2, G5 |
| S1 CAPTURES | 1179×2556 raw frames × 13 locales (`-AppleLanguages`, `-pc.now` on a Claw + Double week, OD12) + the IAP review Shop shot (Release store, no chip) + the iPad compat-mode audit on "Maze iPad" | B | V2-P, B3 | 65 frames + 1 shop shot looked at; iPad layout holds |
| S2 UPLOAD | `df -h`; `fastlane upload_build`; poll `/v1/builds` until VALID (never bump on "already used"); **Release IPA gates G8** | A | V1-P, T5 | G8 |
| S3 META | `meta.py` → `upload_meta_only` → `asc_keywords.py`; `make_screenshots.py` → **look at all 65** → `asc_screenshots.py`; IAP review screenshot → 12 × READY_TO_SUBMIT; age rating PATCH (4+), availability without CHN | – | S1, S2, T5 | G12 (metadata part) |
| S4 SUBMIT | `upload_privacy` (OA1 session; the Meta label: tracking, 5 types) → `asc_submit.py --bundle … --uses-idfa` (RFIX 09-29: usesIdfa=true before the submission) with the IAP items → read back → re-poll 15 min → PROJECT_LOG line + memory `arrowout-build-state` + orchestrator commit | – | S3, G1–G11 | G12 |

## 5. DAG and waves (INFERRED times; T0 = build-4 closed, expected on the morning of 09-28)

```
Wave 0 (now → T0, light only)  T0 DEC · T1 EN · T2 batch1 · T3 STORE · T4 SCRIPTS · T6 SOC-PY · T7 EV-REF · T8 LV-TOOLS · T9 AUDIO-2 · T10 GATES
                               [phone if up: PH-0a before 09:55 + after 10:05 TRT, PH-0b Balloon, PH-0c R1-R3, H]   [owner: OA1 2FA → T5]
Wave 1 (T0 → T0+1 d)   A: A0 ─► A1 ─► A2                    B: B0 ─► B1              R: R1 ─► R2 ─► R3 (R5 icon in bg)
                       T: T5 (after OA1) · T2 batch2 · T6 cont.                      phone: PH-1 install (build-4)
Wave 2 (T0+1 → +2.5 d) A: A3 ─► A4 ─► A5 (exclusive)        B: B2 ─► B3              R: R4 · R6 · R7 · R8 · R9 (SVG)
                       phone: PH-2 (glitch hunt, icon, P3 colour) after A3 + R5
Wave 3 (+2.5 → +3.5 d) A: V1-P(app ×2) ─► V3-P              B: V1-P(core ×2) ─► V2-P   phone: PH-3 (D1b-P), PH-4 (purchase), PH-5 (owner)
                       fix round ≤ 2 (any red gate → its owner WP, then V re-runs the gate)
Wave 4 (+3.5 → +4.5 d) B: S1 ─► (T) S3                      A: S2                      T: S4 submit + 15-min re-poll
```

Critical path: R1 → R2 → R3/R8 → A4 → A5 → V2-P → S1 → S3 → S4. Near-critical: T6 → B2 → B3 → S1.

| edge | why |
|---|---|
| A0 → A1, A2, B1 | contract amend 4 + project.yml first, re-hashed once |
| T1 → T2 batch 2, T3, A1 | the English freeze precedes translation and the store text |
| T8 → B0; T7 → B1; T6 → B2 → B3 | Python reference first, then the Swift port (bit-exact) |
| B1 → B2 | both touch SocialConfig; the events blocks land first, the world model merges on top |
| R2 → R3/R4/R5/R8 → A4 → A5 | art before integration; the codemod last, in an exclusive window |
| A2 → A3 | the glitch hunt runs on the new transitions, not the old ones |
| OA1 → T5 → S3/S4 | the Apple ID session gates create_app, the IAPs and App Privacy |
| every build WP → V1-P → V2-P/V3-P → S1/S2 | the store captures show the final build |

## 6. Owner decisions (surface at first wake; the default applies when the dependent WP starts)

### 6.1 Open

| # | decision | default (applies automatically) | alternative | blocks (soft) |
|---|---|---|---|---|
| OD1 | Sound (item 6) | Remake v552's 9 cues at kit quality. Levels and the win stay **silent**, as in v552 (VERIFIED) | + our own subtle win sting and a tab/popup whoosh (a deviation from v552) | T9 scope |
| OD2 | Popup punch reach | Punch every boxed or band popup; keep v552's instant ones instant (Out of Time/Lives, win panel, Settings, Profile) | punch everything | A2 |
| OD3 | Settings / Profile / event pages | Keep the 1-frame cut (1:1) | the same push-slide as the tabs | A2 |
| OD4 | Haptic strength | 5 rising letter clicks (0.55 → 0.70); buttons rigid 0.60; Play 0.75; slam heavy 1.0 | one click per word | A2 |
| OD5 | Badge idle loops | Yes, with the measured timing | static | A4 |
| OD6 | Subtitle ("Tap Away" is vetoed by ruling 38) | "Tap Arrows, Beat the Clock" (26 characters) | T3's research picks | T3 |
| OD7 | "Go" button colour | D1 sunflower-orange (ruling 38 palette) | keep green | R9/A5 |
| OD8 | Re-order range | L34–L105 re-ordered; L1–L33 + L70 frozen; L71 = the candidate (the v552 L80 board); provenance stripped; no mirroring | also mirror boards, or freeze to L50 | B0 |
| OD9 | World epoch constant | Monday **2026-09-07 07:00 UTC**, i.e. the expected live Monday 10-05 minus 4 weeks. A slip only ages the world | the original's 2026-04-27 | T6 |
| OD10 | Purchased coins after a reinstall | Accept the loss in 1.0 (one line on the support page) | iCloud key-value backup (Apple's service, about +0.5 d) | A1 |
| OD11 | Balloon Rise rules | From the phone capture (PH-0b) if it lands before B1's Balloon step, else events.md §5 | skip Balloon in 1.0 | B1 |
| OD12 | Launch week | No pinned week; screenshots staged with `-pc.now` on a Claw + Double week | pin the release week | S1 |
| OD13 | Crew and boss names | None in the 1.0 UI | owner names them | – |

### 6.2 Already decided (ruling 38; proceeds unless the owner overrides)

Art D1 "Burrow Works"; boss v2 minimal set; icon IC-1; logo keeps "ARROW OUT!" with a restyled look and a new OFL display face;
board reskin with identical rules; D1 palette; name "Arrow Out: Arrow Escape Puzzle"; 13 locales; iPhone-only 1.0 plus an
iPad compat audit; China mainland excluded; 12 consumables at v552's US price points (StoreKit `displayPrice`); STARTER instead
of "90% OFF"; no Restore button (review note explains); review note "leaderboards and events run on the device"; rotation
(Streak + Weekly always, Claw ⇄ Balloon, Rocket ⇄ Sky, ~1/7 double); our own event names; Balloon built; event notifications on;
native-script name shares; ~200 country rows + aliases; drop "Compete against your friends!"; one-time board reshuffle.

### 6.3 Owner actions (not decisions)

| # | action | when | unblocks |
|---|---|---|---|
| OA1 | `fastlane spaceauth -u esaridogann@gmail.com` (password + 2FA on the trusted device) | **first wake**; the session lasts 30 days | T5 create_app (name reservation), the IAPs, App Privacy, submit |
| OA2 | Create 1 sandbox tester (region Turkey) in ASC, or confirm the phone's Apple ID for TestFlight internal | before Wave 3 | PH-4 |
| OA3 | The phone plugged in and unlocked, Auto-Lock Never, Dev Mode + UI Automation on | PH sessions (§7) | all PH |
| OA4 | Feel the **original's** haptics with the motion §5.4 checklist; later, our build's | PH-0 / PH-5 | A2 tuning, G3 |

## 7. The phone plan (orchestrator holds `/tmp/phonedriver.lock`; the phone is not available now)

| session | when | what | on | feeds | P |
|---|---|---|---|---|---|
| PH-0a | **Today, before 09:55 and after 10:05 TRT** (else 10-05) | Home shots of the original across the Monday reset: which events appear or disappear; does Balloon take the Claw bar or a badge; does everything run at once in v582 | original v582 | T7, B1 | P0 |
| PH-0b | first session | Balloon Rise without spending: entry, first open, (i) text verbatim, layout, step goals and rewards, what a fail does, duration, unlock level, rivals | original | T7, OD11 | P0 |
| PH-0c | first session, before A2 | motion R1 (Quit / Continue band entrance), R2 (tab slide from its first frame + the 2-page jump), R3 (4 taps during a win: no skip? ripple? click?); then R4–R7 (P1), R8–R10 (P2) | original | A2 | P0/P1 |
| H | any owner session | the haptic checklist on the original (arrow tap, bump, heart, Play, pause, X, toggles, tabs, boosters, win beats, coins, claim, unlock) | original | A2 (OD4) | P0 |
| PH-1 | when build-4 closes | install the Release build **over** the old one (progress kept) — already authorised | ours (build-4) | owner | P0 |
| PH-2 | after A3 + R5 | glitch hunt on our build: 60 Hz recordings of 300 taps, pause/quit ×20, tabs → blipscan; the candidate icon on the home screen (light, dark, tinted); P3 colour of the palette and scenes | ours (test build) | A3, R5, R9 | P0 |
| PH-3 | after V3-P | **D1b-P**: FrameProbe on tab slides, punches, badge loops, the week-start page (SocialLab picker), win logo + haptics, soak; tap → motion ≤ 1 frame; blipscan again | ours (RC) | G2, G5 | P0 |
| PH-4 | after S2 (TestFlight or a Release-signed dev build) | Sandbox purchase: Special Offer + one pack; grant exactly once; a kill during the sheet still grants on relaunch; the RC API shows the transaction; TL prices, and the longest one fits | ours (RC) | G10 | P0 |
| PH-5 | before S4 | Owner acceptance: install over, look at the art at real size, feel the haptics against the original, listen to the sounds | ours (RC) | G11 | P0 |

## 8. Final verification gates (all green before S4; evidence under `design/publish/verify/`)

| gate | pass criterion (measurable) | evidence |
|---|---|---|
| G1 TESTS ×2 | core.sh green twice (with PC_C4_FULL); every mutation script (core, content, audio, social, events, validator) all CAUGHT; frozen contracts N/N; app unit + full UI green **twice** in a row; Release build green; skips = only the documented environment skips | `verify/G1.json` + logs in build/p/V1 |
| G2 PERF | sim Release (idle machine, R paused) **and** iPhone 15: 0 frames > 20 ms over the soak, 20 tab slides, 20 punches, 11 celebrations, the week-start page, 60 s of badge loops; tap → first motion ≤ 1 frame; Play → intro < 20 ms | `verify/G2.json`, FrameProbe dumps |
| G3 FEEL vs v552 | feelstrip for tab slide, Pause punch, band entrance (per R1), badge loops, unlock dismiss, claim staging, HUD drop, win-logo beats (A1b rows regenerated): all within ±1 frame / ±2 pt / ±0.005 scale of the measured tables. Celebration unskippable (UI test). Haptic beat log matches the map. The owner's feel checklist (H, PH-5) is signed | `verify/G3.json` + strips |
| G4 ART COPY-DISTANCE | (a) copygate on **every** screen, the icon and the logo vs its v552 pair: SSIM < 0.30 **and** chroma overlap < 0.55 (thresholds from R1's recalibration). (b) An adversarial reviewer agent, shown only the pairs, answers "copied?" = no for every pair. (c) Brand/provenance scan of the **compiled** Release .app + bundle: 0 hits of `maze ?out`, `grand ?games`, `arrowjam`, `v552`, `research/`, `simulat` (blocklist stems stored hashed). (d) 100 % A on heroes | `verify/G4.json` + sheets |
| G5 GLITCH | blipscan = 0 anomalies over the scripted run (sim ×2) and PH-2/PH-3 on the phone | `verify/G5.json` |
| G6 AUDIO | `check.py` all pass + self-test all caught; in-app bus level within ±1 dB of the file and onset ≤ 1 frame after its visual beat; **silence asserted by signal** during levels and the win (v552 parity); owner OK or OD1 default | `verify/G6.json` |
| G7 L10N | 13 languages at 100 % coverage; `build.py --check` 0 errors; fit sweep 0 failures; CJK and Country-tab shots looked at; store text in 13 locales passes `meta.py audit` | `verify/G7.json` |
| G8 RELEASE BINARY | no FakeStore/"Test store" in Release; `PrivacyInfo.xcprivacy` present; 13 `.lproj`; version 1.0.0 (1); portrait; no ad strings; `otool -L` shows no ad framework; the real icon (not the 4.5 KB placeholder; 1024 with no alpha); iPad compat audit holds; CLAUDE.md gates that fit a coin game (empty states, rating after L34, Contact Support) | `verify/G8.json` |
| G9 SOCIAL | T6/B2 guards green; perf budgets met; world frozen (`design/social/FROZEN` sha == the shipped data) | `verify/G9.json` |
| G10 PAYMENTS | ASC: 12 IAPs × 13 localizations, USA prices, automatic prices ≥ 170, TUR golden. RC: 12 consumables, both keys. PH-4 sandbox purchase passes | `verify/G10.json` |
| G11 OWNER | PH-5 accepted on the phone (install over, progress kept) | PLAN.md line |
| G12 SUBMIT | read back independently: reviewSubmission WAITING_FOR_REVIEW; the version's build = ours; 12 IAP versions WAITING_FOR_REVIEW; keywords non-empty ×13; screenshots 5/5 ×13 via the API **and** each uploaded frame opened; copyright "2026 Manycode Apps"; re-poll 15 min with no INVALID_BINARY | `verify/G12.json` |

## 9. Risks (top 10)

| # | risk | tag | mitigation |
|---|---|---|---|
| 1 | Art quality is taste-gated and fur-heavy (about 3–3.5 h of renders plus iterations); the critical path | INFERRED | concept pack first; 100 %-A heroes gate; R runs in parallel with every slot-A/B WP |
| 2 | A 4.1 copycat reading or a content dispute (Maze Out! → Arrow Out, 1:1 flows) | INFERRED | G4 (copygate + adversarial review + provenance strip) |
| 3 | The owner's 2FA is late → no name reservation, and the name may be taken (about 15 live "Arrow Out" titles) | VERIFIED (session expired) | ask for OA1 first; T5 runs create_app first; fall back to release §6.2's names |
| 4 | Social rework is long (≥ 300 names × about 25 cultures; native review) | INFERRED | starts in Wave 0; the model freezes before S1 |
| 5 | The CJK fallback look under outlined 1000-weight text is unverified | VERIFIED gap | B3 shots; bundle OFL black CJK fonts only if the cascade fails |
| 6 | New consumable tooling rests on INFERRED API points (v1 vs v2 IAP localizations, RC `consumable`, `recordPurchase`, IAPs in the first submission) | INFERRED | read back every step; compile probe in A0; dry-run first |
| 7 | Collisions in the Home files / SocialConfig / strings | INFERRED | §3 hot-file order + claims file |
| 8 | UI suites slow down: each win +3.6 s (unskippable) | VERIFIED motion §6.5 | re-budget V1-P time; no test removed |
| 9 | Provenance leaks in the bundle (v552, research/, phone, blocklist brands) | VERIFIED planner (sources) | B0 strip + hashed blocklist + G4c on the compiled .app |
| 10 | Coin inflow swings 2.5× between Claw and Balloon weeks | VERIFIED events §9 numbers | bench A9; tune social.json before the freeze |

Also: `apps/arrows` (a parked copy of another arrow game) must never ship on this account next to Arrow Out (4.3). The release doc
flags it; nothing in this plan touches it.
