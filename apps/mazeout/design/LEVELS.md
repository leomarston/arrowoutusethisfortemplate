# Arrow Out — the level list (LEVELS.md)

Companion to `design/SPEC-gameplay.md` §14 and `design/levels.json` (the content, L1–L150). Gameplay spec writer, 2026-09-25;
CONTENT RECAST 2026-09-25 (phone session 2: v552 L62–L83 recorded; evidence build/recast/); CONTENT RECAST 2 2026-09-25
(phone session 3: v552 L84–L105 recorded, the DEDUP rule of SPEC.md §5 item 28 with rotations and mirrors, the curve refitted
to L32–L105, designed L106–L150; evidence build/recast2/).
Tags: VERIFIED (source) / INFERRED / DECISION / ORCH n (SPEC.md §5 item n). The tables between `<!-- BEGIN:x -->` and
`<!-- END:x -->` are generated from `design/levels.json` by `design/tools/levels_report.py`; the rest is prose.

## 0. Rebuild, from the research files to the validated content
```
python3 design/tools/reveal_backfill.py            # doors + v552 elevators: hidden arrows/keys/tapes/pipes from the bot's round
                                                   #   shots -> tools/work/reveals/ (~6 min; `... 86 89 93 98 100 101 102 103` = session 3)
python3 design/tools/import_research.py            # research JSONs L1-L105 (+ curation, reveals, corner facings) -> tools/work/imported*.json
python3 design/tools/replay_log.py                 # rules check: the phone bot's winning taps on L62-L105 must all exit (0 bumps)
python3 design/tools/repeats.py --order            # the repeat detector over OUR order (offset-free, rotations, mirrors)
python3 design/tools/build_levels.py curve         # the generator curve fitted to L30-L105 -> tools/work/curve.json
python3 design/tools/build_levels.py designed      # L106-L150 (validator-gated) + the stand-ins of the repeated slots L81, L83,
                                                   #   L86, L100, L101, L103 -> work/designed.json, work/substitutes.json (~3 min)
python3 design/tools/build_levels.py assemble      # -> design/levels.json (our order, repeats -> V2 boards / stand-ins, unlock cards, metrics)
python3 design/tools/validate_levels.py            # must print 0 errors
python3 design/tools/repeats.py                    # must print 0 repeats (design/levels.json L1-L150)
python3 design/tools/validator_selftest.py         # must print 20/20 caught (~5 min)
python3 design/tools/levels_report.py              # refreshes the tables in this file
python3 design/tools/render_levels.py design/levels.json 33 62 99 --out /tmp/sheet.png   # a contact sheet to LOOK at
tools/levels/lv.sh bundle design/levels.json App/Resources/Levels   # the bundle (CONTENT L1's lvtool; --check compares)
python3 design/tools/overlay_recast.py --levels 62,...,105 --out build/recast2/overlay [--reveals] [--elevators] [--negative]  # overlay proof
python3 design/tools/pin_fixtures.py               # pin the content the PathCore tests read (Tests/Fixtures/content)
python3 Packages/PathCore/Tests/tools/c4_reference.py negatives    # + `rows`/`runtime` for c4_runtime_reference.json
python3 Packages/PathCore/Tests/tools/c4b_bot_replay.py         # the bot-replay pin (content sha256 + replay_log's verdict)
```
Everything is deterministic: the same inputs give the same bytes (the generator draws every number from `pathrandom.py`, the
bit-exact mirror of PathCore's PathRandom; two runs of L62 are identical, checked).
Python 3 with numpy, scipy and Pillow (the reveal step reuses `research/bot/bot.py`, read-only).

## 1. The list
Origin: `video V1/V2` = the owner's videos (verified 31/31 by `research/video-levels.md`); `phone v552` = recorded on the owner's
phone; `V2-L03x (substitute)` = the video build's boards that v552 does not have, in a slot whose phone board repeats an earlier
one (ORCH 19, §2.3–§2.4); `designed (stand-in for a repeat of Ln)` = a generated board in a slot whose phone board repeats Ln
(ORCH 26/28, §2.4); `designed` = `gen_levels.py`. Units = tap targets (a tape bundle is one). Waves = dependency depth (every free unit removed per wave).
Bot s left = timer − 0.6 s × units − 1.14 s × doors.
<!-- BEGIN:levels -->
| L | origin | tag | timer | grid | arrows (+hidden) | units | obstacles (counters) | unlock | waves | free | bot s left |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | video V1 | - | 3:00 | 3x4 | 3 | 3 | - |  | 1 | 3 | 178 |
| 2 | video V1 | - | 3:00 | 6x6 | 6 | 6 | - |  | 4 | 1 | 176 |
| 3 | video V1 | - | 3:00 | 10x9 | 8 | 8 | - |  | 3 | 2 | 175 |
| 4 | video V1 | - | 3:00 | 9x14 | 8 | 8 | - |  | 4 | 1 | 175 |
| 5 | video V1 | - | 3:00 | 12x14 | 17 | 17 | - |  | 8 | 6 | 170 |
| 6 | video V1 | - | 3:00 | 27x22 | 29 | 29 | - |  | 10 | 11 | 163 |
| 7 | video V1 | - | 3:00 | 10x15 | 18 | 14 | tape 2+2+2+2 | linked | 9 | 3 | 172 |
| 8 | video V1 | - | 3:00 | 12x17 | 19 | 17 | tape 2+2 |  | 7 | 3 | 170 |
| 9 | video V1 | - | 3:00 | 14x19 | 27 | 27 | - |  | 10 | 7 | 164 |
| 10 | video V1 | - | 3:00 | 20x22 | 47 | 38 | tape 4+4+4 |  | 14 | 9 | 157 |
| 11 | video V2 | - | 3:00 | 10x20 | 14 | 14 | box 8/13 | box | 5 | 6 | 172 |
| 12 | video V2 | - | 3:00 | 15x21 | 24 | 24 | box 8/16/23 |  | 10 | 4 | 166 |
| 13 | video V2 | - | 3:00 | 14x18 | 33 | 29 | tape 3+3, box 4/28 |  | 12 | 4 | 163 |
| 14 | video V2 | - | 3:00 | 13x16 | 15 | 15 | - |  | 5 | 5 | 171 |
| 15 | video V2 | - | 3:00 | 20x25 | 48 | 48 | box 26/41 |  | 11 | 8 | 151 |
| 16 | video V2 | - | 3:00 | 13x15 | 24 | 24 | - |  | 10 | 4 | 166 |
| 17 | video V2 | - | 3:00 | 19x24 | 54 | 48 | tape 3+3+3 |  | 14 | 7 | 151 |
| 18 | video V2 | - | 3:00 | 14x17 | 22 | 22 | - |  | 10 | 4 | 167 |
| 19 | video V2 | Hard | 3:00 | 20x31 | 62 | 62 | box 13/20/25 |  | 25 | 11 | 143 |
| 20 | video V2 | - | 3:00 | 14x20 | 20 | 20 | - |  | 9 | 5 | 168 |
| 21 | video V2 | - | 3:00 | 12x18 | 20 | 20 | pipe 2 | pipe | 10 | 1 | 168 |
| 22 | video V2 | - | 3:00 | 14x23 | 29 | 29 | pipe 1/1 |  | 10 | 6 | 163 |
| 23 | video V2 | - | 3:00 | 16x22 | 41 | 37 | tape 3+3, pipe 3/3 |  | 18 | 7 | 158 |
| 24 | video V2 | - | 3:00 | 17x27 | 37 | 29 | tape 3+3+3+3 |  | 10 | 7 | 163 |
| 25 | video V2 | Hard | 3:00 | 19x30 | 61 | 61 | pipe 3/3, box 24/57/36 |  | 24 | 10 | 143 |
| 26 | video V2 | - | 3:00 | 15x19 | 26 | 26 | - |  | 12 | 4 | 164 |
| 27 | video V2 | - | 3:00 | 16x26 | 40 | 40 | box 32/25/18 |  | 16 | 7 | 156 |
| 28 | video V2 | - | 3:00 | 19x24 | 51 | 43 | tape 3+3+3+3, box 10/38 |  | 14 | 7 | 154 |
| 29 | video V2 | Super Hard | 3:00 | 20x32 | 68 | 68 | pipe 3/3/3 |  | 29 | 13 | 139 |
| 30 | video V2 | - | 3:00 | 16x16 | 25 | 25 | - |  | 7 | 9 | 165 |
| 31 | video V2 | - | 3:00 | 16x17 | 28 (+7) | 35 | elevator x1 (+7 hidden) | elevator | 12 | 8 | 159 |
| 32 | phone v552 | - | 3:00 | 20x20 | 53 | 41 | tape 4+4+4+4 |  | 12 | 10 | 155 |
| 33 | phone v552 | - | 3:00 | 20x20 | 20 (+30) | 50 | door x5 (keys 5) | door | 23 | 2 | 144 |
| 34 | phone v552 L54 | Hard | 3:00 | 26x34 | 72 (+30) | 102 | door x1 (keys 1) |  | 44 | 16 | 118 |
| 35 | V2-L032 (substitute) | - | 3:00 | 17x21 | 29 (+11) | 40 | elevator x1 (+11 hidden) |  | 17 | 4 | 156 |
| 36 | phone v552 L40 | - | 2:30 | 20x27 | 42 | 42 | - |  | 13 | 8 | 125 |
| 37 | phone v552 L47 | - | 3:00 | 20x30 | 29 (+28) | 55 | tape 2+2, door x2 (keys 2) |  | 18 | 3 | 145 |
| 38 | phone v552 L42 | - | 3:00 | 22x30 | 45 | 45 | pipe 4/4/3/3 |  | 23 | 10 | 153 |
| 39 | phone v552 L49 | Super Hard | 2:30 | 24x36 | 59 (+10) | 69 | door x1 (keys 1), pipe 4/4/3/3/3 |  | 30 | 12 | 108 |
| 40 | phone v552 L43 | - | 3:00 | 20x32 | 27 (+32) | 59 | door x2 (keys 2) |  | 19 | 1 | 142 |
| 41 | phone v552 L38 | - | 3:00 | 20x22 | 42 | 39 | tape 2+2+2, pipe 4 |  | 15 | 6 | 157 |
| 42 | phone v552 L48 | - | 2:30 | 20x24 | 47 | 47 | pipe 4/4/4 |  | 20 | 6 | 122 |
| 43 | phone v552 L36 | - | 3:00 | 16x23 | 31 | 31 | pipe 1/1 |  | 14 | 8 | 161 |
| 44 | phone v552 L34 | Hard | 3:30 | 25x35 | 76 (+40) | 116 | door x4 (keys 4) |  | 42 | 5 | 136 |
| 45 | phone v552 L41 | - | 2:30 | 20x26 | 27 (+21) | 48 | door x1 (keys 1), pipe 3/3 |  | 19 | 8 | 120 |
| 46 | V2-L035 (substitute) for phone L52 | - | 3:00 | 20x32 | 57 (+39) | 96 | pipe 3, elevator x1 (+39 hidden) |  | 44 | 8 | 122 |
| 47 | phone v552 L37 | - | 3:00 | 22x30 | 14 (+35) | 49 | door x3 (keys 3) |  | 23 | 5 | 147 |
| 48 | V2-L034 (substitute) for phone L51 | - | 3:00 | 18x23 | 40 | 32 | tape 3+3+3+3 |  | 13 | 5 | 161 |
| 49 | phone v552 L39 | Super Hard | 3:00 | 24x34 | 102 | 102 | - |  | 38 | 10 | 119 |
| 50 | phone v552 L60 | - | 3:00 | 20x20 | 34 | 34 | - |  | 7 | 5 | 160 |
| 51 | phone v552 L55 | - | 2:30 | 20x27 | 48 | 48 | - |  | 22 | 6 | 121 |
| 52 | V2-L033 (substitute) for phone L45 | - | 2:30 | 17x23 | 36 (+17) | 53 | box 41/28/18/13, elevator x2 (+17 hidden) |  | 22 | 8 | 118 |
| 53 | phone v552 L56 | - | 3:00 | 24x32 | 60 | 60 | pipe 5/5/4/3, box 47/18 |  | 23 | 10 | 144 |
| 54 | phone v552 L44 | Hard | 3:00 | 25x36 | 91 | 83 | tape 3+3+3+3, pipe 8/3 |  | 33 | 6 | 130 |
| 55 | phone v552 L46 | - | 3:00 | 24x32 | 56 (+46) | 102 | door x4 (keys 4) |  | 37 | 13 | 114 |
| 56 | phone v552 L63 | - | 2:30 | 22x28 | 38 (+22) | 60 | door x1 (keys 1), pipe 3/3 |  | 25 | 9 | 113 |
| 57 | phone v552 L50 | - | 3:00 | 10x18 | 16 | 16 | box 10 |  | 9 | 2 | 170 |
| 58 | phone v552 L62 | - | 3:00 | 26x34 | 44 (+35) | 72 | tape 3+3+4, door x2 (keys 2), box 23/66/34 |  | 30 | 11 | 134 |
| 59 | phone v552 L69 | Super Hard | 2:00 | 26x34 | 58 (+41) | 99 | door x4 (keys 4), pipe 2/4/3 (3 under doors) |  | 36 | 9 | 56 |
| 60 | phone v552 L57 | - | 3:00 | 20x24 | 42 | 38 | tape 2+2+2+2, box 40/37/26/22 |  | 13 | 13 | 157 |
| 61 | phone v552 L66 | - | 2:30 | 20x20 | 13 (+12) | 25 | door x1 (keys 1) |  | 12 | 5 | 134 |
| 62 | phone v552 L65 | - | 3:00 | 26x34 | 23 (+42) | 65 | door x2 (keys 2), box 22/52 |  | 21 | 6 | 139 |
| 63 | phone v552 L53 | - | 2:30 | 20x30 | 30 (+31) | 61 | door x2 (keys 2), box 39/21 |  | 24 | 6 | 111 |
| 64 | phone v552 L84 | Hard | 2:00 | 26x33 | 87 | 87 | - |  | 44 | 15 | 68 |
| 65 | phone v552 L68 | - | 3:00 | 20x31 | 59 | 50 | tape 4+4+4, pipe 6/3 |  | 19 | 8 | 150 |
| 66 | phone v552 L61 | - | 2:30 | 20x20 | 39 | 35 | tape 2+2+2+2 |  | 9 | 6 | 129 |
| 67 | phone v552 L58 | - | 2:30 | 22x24 | 27 (+34) | 61 | door x1 (keys 1) |  | 26 | 5 | 112 |
| 68 | V2-L038 (substitute) for phone L75 | - | 2:30 | 16x20 | 34 | 34 | pipe 3/3 |  | 12 | 6 | 130 |
| 69 | phone v552 L59 | Super Hard | 2:00 | 26x34 | 85 | 85 | - |  | 34 | 16 | 69 |
| 70 | phone v552 | - | 3:00 | 17x18 | 22 | 22 | corner x2 | corner | 6 | 7 | 167 |
| 71 | phone v552 L80 | - | 3:00 | 22x24 | 42 | 42 | corner x4 |  | 18 | 6 | 155 |
| 72 | V2-L036 (substitute) | - | 3:00 | 20x23 | 36 | 36 | - |  | 14 | 3 | 158 |
| 73 | phone v552 L76 | - | 3:00 | 24x26 | 56 | 56 | corner x6 |  | 18 | 6 | 146 |
| 74 | phone v552 L64 | Hard | 1:40 | 24x30 | 75 | 75 | - |  | 33 | 13 | 55 |
| 75 | phone v552 L78 | - | 3:00 | 18x28 | 37 | 37 | - |  | 15 | 8 | 158 |
| 76 | phone v552 L82 | - | 2:30 | 21x29 | 60 | 60 | pipe 6/6/6, corner x2 |  | 27 | 10 | 114 |
| 77 | phone v552 L67 | - | 2:30 | 20x20 | 37 | 37 | box 25/21/14/9 |  | 16 | 4 | 128 |
| 78 | V2-L037 (substitute) for phone L77 | - | 3:00 | 20x33 | 55 | 55 | box 52/35 |  | 23 | 7 | 147 |
| 79 | phone v552 L99 | Super Hard | 3:00 | 26x32 | 85 | 85 | - |  | 25 | 17 | 129 |
| 80 | phone v552 L71 | - | 3:00 | 18x18 | 25 | 25 | corner x2 |  | 11 | 2 | 165 |
| 81 | designed (stand-in for a repeat of L66) for phone L86 | - | 2:30 | 20x20 | 23 (+10) | 33 | door x1 (keys 1) |  | 13 | 6 | 129 |
| 82 | phone v552 L73 | - | 2:30 | 20x26 | 61 | 61 | box 46/58, corner x1 |  | 19 | 9 | 113 |
| 83 | designed (stand-in for a repeat of L63) | - | 2:30 | 22x28 | 47 (+24) | 71 | door x1 (keys 1), pipe 4/4 |  | 25 | 7 | 106 |
| 84 | phone v552 L74 | Hard | 3:00 | 26x36 | 113 | 113 | - |  | 43 | 13 | 112 |
| 85 | phone v552 L91 | - | 2:30 | 20x20 | 38 | 38 | corner x3 |  | 18 | 6 | 127 |
| 86 | designed (stand-in for a repeat of L61) for phone L81 | - | 2:30 | 20x20 | 37 | 34 | tape 4 |  | 9 | 4 | 130 |
| 87 | phone v552 L92 | - | 2:30 | 18x22 | 40 | 40 | pipe 3/3, box 15 |  | 19 | 4 | 126 |
| 88 | phone v552 L98 | - | 2:30 | 24x30 | 42 (+44) | 74 | tape 4+4+4+4, door x2 (keys 2) |  | 31 | 7 | 103 |
| 89 | phone v552 L79 | Super Hard | 3:00 | 24x30 | 74 | 74 | corner x5 |  | 28 | 14 | 136 |
| 90 | phone v552 L95 | - | 2:30 | 20x26 | 41 | 41 | - |  | 14 | 6 | 125 |
| 91 | phone v552 L88 | - | 2:30 | 24x30 | 76 | 68 | tape 3+3+3+3, pipe 3/3 |  | 21 | 9 | 109 |
| 92 | phone v552 L87 | - | 3:00 | 18x26 | 43 | 43 | box 17/34/40 |  | 23 | 7 | 154 |
| 93 | phone v552 L85 | - | 2:30 | 20x26 | 49 | 45 | tape 2+2+2+2, corner x2 |  | 14 | 6 | 123 |
| 94 | phone v552 L104 | Hard | 3:00 | 25x36 | 83 | 83 | - |  | 34 | 1 | 130 |
| 95 | phone v552 L90 | - | 2:30 | 20x20 | 33 | 33 | - |  | 14 | 5 | 130 |
| 96 | phone v552 L93 | - | 2:30 | 21x26 | 36 (+28) | 64 | door x3 (keys 3), corner x2 |  | 19 | 7 | 108 |
| 97 | phone v552 L102 | - | 2:30 | 20x27 | 58 (+22) | 80 | elevator x1 (+22 hidden), corner x2 |  | 31 | 13 | 102 |
| 98 | phone v552 L105 | - | 3:00 | 16x20 | 34 | 34 | pipe 3/3 |  | 16 | 6 | 160 |
| 99 | phone v552 L89 | Super Hard | 2:30 | 26x36 | 65 (+34) | 99 | door x2 (keys 2), corner x3 |  | 36 | 9 | 88 |
| 100 | designed (stand-in for a repeat of L31) | - | 3:00 | 16x17 | 34 (+5) | 39 | elevator x1 (+5 hidden) |  | 12 | 8 | 157 |
| 101 | designed (stand-in for a repeat of L45) for phone L103 | - | 3:00 | 17x23 | 45 (+4) | 49 | box 25, elevator x1 (+4 hidden) |  | 18 | 8 | 151 |
| 102 | phone v552 L97 | - | 2:30 | 22x26 | 48 | 48 | box 21, corner x4 |  | 25 | 6 | 121 |
| 103 | phone v552 L96 | - | 2:30 | 20x22 | 32 | 32 | pipe 3 |  | 12 | 5 | 131 |
| 104 | phone v552 L94 | Hard | 2:30 | 26x36 | 104 | 104 | - |  | 38 | 13 | 88 |
| 105 | designed (stand-in for a repeat of L35) for phone L101 | - | 3:00 | 17x21 | 33 (+2) | 35 | elevator x1 (+2 hidden) |  | 14 | 4 | 159 |
| 106 | designed | - | 2:30 | 20x20 | 26 | 26 | pipe 4 |  | 11 | 2 | 134 |
| 107 | designed | - | 2:30 | 20x20 | 30 (+4) | 34 | box 6, elevator x1 (+4 hidden) |  | 15 | 4 | 130 |
| 108 | designed | - | 3:00 | 20x31 | 55 | 55 | - |  | 19 | 10 | 147 |
| 109 | designed | Super Hard | 2:00 | 26x34 | 101 | 101 | box 55 |  | 33 | 8 | 59 |
| 110 | designed | - | 3:00 | 17x18 | 22 | 22 | corner x3 |  | 6 | 7 | 167 |
| 111 | designed | - | 3:00 | 18x18 | 26 | 26 | - |  | 10 | 4 | 164 |
| 112 | designed | - | 3:00 | 13x16 | 16 | 16 | corner x1 |  | 5 | 5 | 170 |
| 113 | designed | - | 2:30 | 20x26 | 63 | 56 | tape 3+3+3+2 |  | 20 | 9 | 116 |
| 114 | designed | Hard | 3:00 | 26x36 | 88 (+31) | 119 | door x1 (keys 1) |  | 35 | 14 | 108 |
| 115 | designed | - | 2:30 | 20x27 | 53 | 49 | tape 3+3, box 24/25/28/29 |  | 19 | 6 | 121 |
| 116 | designed | - | 3:00 | 24x26 | 62 | 62 | pipe 3, corner x5 |  | 17 | 5 | 143 |
| 117 | designed | - | 3:00 | 20x24 | 23 (+15) | 38 | door x1 (keys 1), corner x3 |  | 13 | 7 | 156 |
| 118 | designed | - | 3:00 | 18x28 | 39 | 39 | - |  | 15 | 8 | 157 |
| 119 | designed | Super Hard | 3:00 | 24x30 | 75 | 75 | - |  | 26 | 14 | 135 |
| 120 | designed | - | 3:00 | 22x24 | 42 (+3) | 45 | box 27, elevator x1 (+3 hidden) |  | 18 | 4 | 153 |
| 121 | designed | - | 2:30 | 20x20 | 18 (+15) | 33 | door x1 (keys 1) |  | 10 | 6 | 129 |
| 122 | designed | - | 2:30 | 21x30 | 63 | 63 | - |  | 28 | 10 | 112 |
| 123 | designed | - | 2:30 | 22x29 | 62 | 62 | corner x3 |  | 22 | 8 | 113 |
| 124 | designed | Hard | 2:00 | 26x34 | 64 (+31) | 95 | door x1 (keys 1) |  | 21 | 12 | 62 |
| 125 | designed | - | 2:30 | 20x27 | 48 | 48 | - |  | 14 | 6 | 121 |
| 126 | designed | - | 2:30 | 20x20 | 28 | 28 | - |  | 12 | 5 | 133 |
| 127 | designed | - | 3:00 | 18x27 | 51 | 51 | - |  | 23 | 7 | 149 |
| 128 | designed | - | 2:30 | 24x31 | 88 | 88 | pipe 3/2, corner x1 |  | 21 | 12 | 97 |
| 129 | designed | Super Hard | 2:30 | 26x36 | 112 | 112 | pipe 5, box 17/19/20/22 |  | 34 | 8 | 83 |
| 130 | designed | - | 2:30 | 21x21 | 38 | 34 | tape 3+3, box 13 |  | 13 | 5 | 130 |
| 131 | designed | - | 2:30 | 21x21 | 35 | 35 | box 34, corner x1 |  | 20 | 6 | 129 |
| 132 | designed | - | 2:30 | 19x23 | 38 | 38 | corner x4 |  | 19 | 5 | 127 |
| 133 | designed | - | 2:30 | 22x27 | 64 | 64 | - |  | 20 | 7 | 112 |
| 134 | designed | Hard | 2:30 | 26x36 | 118 | 118 | - |  | 39 | 13 | 79 |
| 135 | designed | - | 2:30 | 21x27 | 40 | 40 | - |  | 14 | 7 | 126 |
| 136 | designed | - | 2:30 | 21x23 | 35 (+7) | 42 | elevator x1 (+7 hidden), corner x1 |  | 13 | 6 | 125 |
| 137 | designed | - | 2:30 | 23x27 | 56 | 56 | - |  | 26 | 7 | 116 |
| 138 | designed | - | 2:30 | 25x31 | 89 | 87 | tape 3 |  | 28 | 8 | 98 |
| 139 | designed | Super Hard | 3:00 | 26x33 | 96 | 96 | - |  | 26 | 17 | 122 |
| 140 | designed | - | 3:00 | 17x17 | 25 (+2) | 27 | elevator x1 (+2 hidden), corner x2 |  | 8 | 3 | 164 |
| 141 | designed | - | 3:00 | 17x18 | 32 | 32 | - |  | 12 | 7 | 161 |
| 142 | designed | - | 3:00 | 21x21 | 42 | 42 | corner x2 |  | 12 | 10 | 155 |
| 143 | designed | - | 3:00 | 21x21 | 58 | 58 | pipe 5/4 |  | 20 | 5 | 145 |
| 144 | designed | Hard | 3:30 | 26x36 | 119 | 119 | box 60, corner x3 |  | 35 | 10 | 139 |
| 145 | designed | - | 3:00 | 12x19 | 22 | 22 | pipe 1/2, corner x3 |  | 15 | 3 | 167 |
| 146 | designed | - | 3:00 | 17x24 | 33 | 33 | corner x2 |  | 15 | 7 | 160 |
| 147 | designed | - | 3:00 | 23x31 | 61 | 61 | pipe 5, corner x1 |  | 22 | 5 | 143 |
| 148 | designed | - | 3:00 | 21x23 | 42 | 42 | pipe 3, corner x2 |  | 11 | 5 | 155 |
| 149 | designed | Super Hard | 3:00 | 25x35 | 106 | 103 | tape 2+2+2, corner x1 |  | 40 | 12 | 118 |
| 150 | designed | - | 2:30 | 21x28 | 48 | 48 | corner x1 |  | 15 | 8 | 121 |
<!-- END:levels -->

### 1.1 The level re-order (PUBLISH item 12; SPEC.md rulings 37e + 39 OD8)
L34–L105 are permuted by `design/tools/reorder_levels.py` (plan `design/level-order.json`; algorithm and constraints:
`design/publish/level-reorder.md`); L1–L33 and the Corner card L70 are frozen, L106–L150 are untouched. The prose below names
boards by their RESEARCH number (the level they were read as, e.g. "v552 L69"); this table says where each moved board ships.
The shipped bundle (`App/Resources/Levels`) is the publish form: no capture, no "_" notes (`lvtool bundle --publish`).
<!-- BEGIN:order -->
| L | tag | board (origin) | timer | obstacles | units/waves | from |
|---|---|---|---|---|---|---|
| 34 | H | v552 L54 | 3:00 | door | 102/44 | +20 |
| 36 |  | v552 L40 | 2:30 | - | 42/13 | +4 |
| 37 |  | v552 L47 | 3:00 | door+tape | 55/18 | +10 |
| 38 |  | v552 L42 | 3:00 | pipe | 45/23 | +4 |
| 39 | SH | v552 L49 | 2:30 | door+pipe | 69/30 | +10 |
| 40 |  | v552 L43 | 3:00 | door | 59/19 | +3 |
| 41 |  | v552 L38 | 3:00 | pipe+tape | 39/15 | -3 |
| 42 |  | v552 L48 | 2:30 | pipe | 47/20 | +6 |
| 43 |  | v552 L36 | 3:00 | pipe | 31/14 | -7 |
| 44 | H | v552 L34 | 3:30 | door | 116/42 | -10 |
| 45 |  | v552 L41 | 2:30 | door+pipe | 48/19 | -4 |
| 46 |  | V2-L035 | 3:00 | elevator+pipe | 96/44 | +6 |
| 47 |  | v552 L37 | 3:00 | door | 49/23 | -10 |
| 48 |  | V2-L034 | 3:00 | tape | 32/13 | +3 |
| 49 | SH | v552 L39 | 3:00 | - | 102/38 | -10 |
| 50 |  | v552 L60 | 3:00 | - | 34/7 | +10 |
| 51 |  | v552 L55 | 2:30 | - | 48/22 | +4 |
| 52 |  | V2-L033 | 2:30 | box+elevator | 53/22 | -7 |
| 53 |  | v552 L56 | 3:00 | box+pipe | 60/23 | +3 |
| 54 | H | v552 L44 | 3:00 | pipe+tape | 83/33 | -10 |
| 55 |  | v552 L46 | 3:00 | door | 102/37 | -9 |
| 56 |  | v552 L63 | 2:30 | door+pipe | 60/25 | +7 |
| 57 |  | v552 L50 | 3:00 | box | 16/9 | -7 |
| 58 |  | v552 L62 | 3:00 | box+door+tape | 72/30 | +4 |
| 59 | SH | v552 L69 | 2:00 | door+pipe | 99/36 | +10 |
| 60 |  | v552 L57 | 3:00 | box+tape | 38/13 | -3 |
| 61 |  | v552 L66 | 2:30 | door | 25/12 | +5 |
| 62 |  | v552 L65 | 3:00 | box+door | 65/21 | +3 |
| 63 |  | v552 L53 | 2:30 | box+door | 61/24 | -10 |
| 64 | H | v552 L84 | 2:00 | - | 87/44 | +20 |
| 65 |  | v552 L68 | 3:00 | pipe+tape | 50/19 | +3 |
| 66 |  | v552 L61 | 2:30 | tape | 35/9 | -5 |
| 67 |  | v552 L58 | 2:30 | door | 61/26 | -9 |
| 68 |  | V2-L038 | 2:30 | pipe | 34/12 | +7 |
| 69 | SH | v552 L59 | 2:00 | - | 85/34 | -10 |
| 71 |  | v552 L80 | 3:00 | corner | 42/18 | +9 |
| 73 |  | v552 L76 | 3:00 | corner | 56/18 | +3 |
| 74 | H | v552 L64 | 1:40 | - | 75/33 | -10 |
| 75 |  | v552 L78 | 3:00 | - | 37/15 | +3 |
| 76 |  | v552 L82 | 2:30 | corner+pipe | 60/27 | +6 |
| 77 |  | v552 L67 | 2:30 | box | 37/16 | -10 |
| 78 |  | V2-L037 | 3:00 | box | 55/23 | -1 |
| 79 | SH | v552 L99 | 3:00 | - | 85/25 | +20 |
| 80 |  | v552 L71 | 3:00 | corner | 25/11 | -9 |
| 81 |  | stand-in for phone L86 | 2:30 | door | 33/13 | +5 |
| 82 |  | v552 L73 | 2:30 | box+corner | 61/19 | -9 |
| 84 | H | v552 L74 | 3:00 | - | 113/43 | -10 |
| 85 |  | v552 L91 | 2:30 | corner | 38/18 | +6 |
| 86 |  | stand-in for phone L81 | 2:30 | tape | 34/9 | -5 |
| 87 |  | v552 L92 | 2:30 | box+pipe | 40/19 | +5 |
| 88 |  | v552 L98 | 2:30 | door+tape | 74/31 | +10 |
| 89 | SH | v552 L79 | 3:00 | corner | 74/28 | -10 |
| 90 |  | v552 L95 | 2:30 | - | 41/14 | +5 |
| 91 |  | v552 L88 | 2:30 | pipe+tape | 68/21 | -3 |
| 92 |  | v552 L87 | 3:00 | box | 43/23 | -5 |
| 93 |  | v552 L85 | 2:30 | corner+tape | 45/14 | -8 |
| 94 | H | v552 L104 | 3:00 | - | 83/34 | +10 |
| 95 |  | v552 L90 | 2:30 | - | 33/14 | -5 |
| 96 |  | v552 L93 | 2:30 | corner+door | 64/19 | -3 |
| 97 |  | v552 L102 | 2:30 | corner+elevator | 80/31 | +5 |
| 98 |  | v552 L105 | 3:00 | pipe | 34/16 | +7 |
| 99 | SH | v552 L89 | 2:30 | corner+door | 99/36 | -10 |
| 101 |  | stand-in for phone L103 | 3:00 | box+elevator | 49/18 | +2 |
| 102 |  | v552 L97 | 2:30 | box+corner | 48/25 | -5 |
| 103 |  | v552 L96 | 2:30 | pipe | 32/12 | -7 |
| 104 | H | v552 L94 | 2:30 | - | 104/38 | -10 |
| 105 |  | stand-in for phone L101 | 3:00 | elevator | 35/14 | -4 |

67 boards moved; the other 83 levels hold the board of their research slot.
<!-- END:order -->

## 2. Provenance

### 2.1 L1–L31: the owner's videos (source "video")
`research/levels/L001–L031.json` (V1 for L1–10, V2 for L11–31, V1 = V2 cell for cell on L11–20), imported as they are:
arrows, ties, boxes with counters, pipes with mouths and counters (batch C/D's mouth fixes included), the L31 elevator with its
7 layer-2 arrows. The video verifier's verdict: 1,527/1,527 arrows, 84/84 obstacles, 74/74 hidden-layer arrows, 0 replay
contradictions, overlays looked at 31/31 (`research/video-levels.md` §1.1). Timers 3:00 and tags as the videos show them (ORCH 19).
Pipe badges: batch C's notes where given (L25, L29), else the default (between the first mouth and its tube neighbour).

### 2.2 L32–L61: the phone (source "recorded") and what was completed
`research/levels/L032–L061.json` (the bot's reads of the start shots, 0 anomalies). The phone schema lacks some content; it was
completed as follows (every value cited):

| level | completed | source |
|---|---|---|
| 35 | pipe counter 2 | levels.md L35 (2 → 1 → 0 seen) |
| 36 | pipe counters 1, 1 | levels.md L36 |
| 38 | pipe counter 4 | levels.md L38 |
| 41 | pipe counters 3, 3 | levels.md L41 |
| 42 | pipe counters 4, 4 (top) and 3, 3 (bottom) | levels.md L42 |
| 44 | pipe counters 8 (left half) and 3 (right half) | levels.md L44 |
| 48 | three ∩ pipes: mouths from the tube shape (both facing DOWN, as levels.md says), counters 4, 4, 4 | the reader wrote no `pipes[]` since L47; shape = the blob cells |
| 49 | five U pipes: mouths from the tube shapes, counters 4 (top-right), 4 (left), 3, 3, 3; the key/counter-box pixels glued to the left pipe's blob (cells (1,11),(2,11)) dropped; the two empty-cell key blobs of the start JSON dropped (the real key rides arrow 58) | levels.md L49 (reader note) |
| 50 | box counter 10 | levels.md L50 |
| 53 | box counters 39 (top), 21 (bottom) | levels.md L53 |
| 56 | box counters 47 (top-left), 18 (bottom-right); pipe counters 5 (top-right), 5 (left-upper), 4 (right-lower), 3 (left-lower) | levels.md L56 + shots/174 read by eye |
| 57 | the four touching boxes (read as one 150-cell blob) split into 5×3, 5×6, 5×9, 5×12 with counters 40, 37, 26, 22 left → right | shots/179 read by eye (the blob bbox and cell count 150 = 15 + 30 + 45 + 60 agree) |
| every door level | door rectangles, opening order, keys (start + hidden), the arrows and tapes hidden under the doors | §3 |
| every pipe | `counter_at` = the orange counter face detected on the start shot (centroid in cell units, rounded to ½ cell); L56's four agree with the eye reading | `import_research.detect_badges` |

The four phone levels whose boards are the video's L21/L26/L12/L14 do not ship (§2.3), so their completions are unused.

### 2.3 Duplicates and substitutes (ORCH 19)
The video build and v552 share four boards at other numbers, identical in every arrow and obstacle (VERIFIED
`research/video-levels.md` §1.3): phone L35 = video L21, L45 = L26, L51 = L12, L52 = L14. The video keeps its slots; the four phone
slots take, in order, the video build's authored boards that v552 does not have: **L35 ← V2-L032** (elevator), **L45 ← V2-L033**
(4 boxes + 2 elevators), **L51 ← V2-L034** (4 tapes), **L52 ← V2-L035** (pipe + a 320-cell elevator), each with its slot's v552
timer and tag (L45 2:30; the others 3:00, normal). Source "video", capture = the V2 frame, `_from` says what it replaces.
These boards were extracted and verified with the rest (`research/video-levels-D.md`; 0 contradictions, both solvers clear them).

### 2.4 Phone session 2 repeats five boards; the spares (ORCH 19)
v552 REPEATS boards 20 levels later, cell for cell and head for head (every arrow and obstacle; `build_levels.phone_duplicates`
finds them offset-free and `assemble` stops if the list changes): **L72 = L52 (= video L14)**, **L75 = L55**, **L77 = L57**,
**L81 = L61**, **L83 = L63** (L63/L83 even reconstruct the same 22 hidden arrows from two independent bot runs). ORCH 19's rule
for duplicates applies: the phone slot keeps its v552 timer and tag and takes, first, the video build's unused authored boards,
in slot order and matched by kind — **L72 ← V2-L036** (plain; its repeat was plain), **L75 ← V2-L038** (pipes), **L77 ←
V2-L037** (boxes; its repeat had boxes) — then, for the slots left, a **generated board built to the repeated board's own
size, units, waves, free arrows, timer and obstacle kinds** (ORCH 19's fallback "a generated level of the same size/tag"):
L81 (tape, 2:30) and L83 (door + pipe, 2:30), `gen_levels.generate(target=, kinds=)`, validator-gated.
RECAST DECISION (accepted as SPEC.md §5 item 26): the spares fill the repeated slots, not the slots after L83.

**The DEDUP rule (SPEC.md §5 item 28, content recast 2).** No board may appear twice in L1–L150; the FIRST occurrence in OUR
order wins; every later duplicate slot gets a generated stand-in built to the repeated board's size, units, waves, free
arrows, timer, tag and obstacle kinds. `build_levels.plan_slots` walks our order slot by slot and places each slot's research
board unless it repeats a board already placed (then: its ORCH 19 V2 substitute, its ORCH 26 spare, or a stand-in).
`repeats.py` decides what "repeats" means: the arrows' cells and heads, offset-free, under all 8 symmetries of the square
(4 rotations × mirror), on the start-visible layer OR on every layer (so a board whose hidden layer is incomplete in one
read is still caught); obstacles are not part of the key. `plan_slots` stops the build when the repeats found differ from
`EXPECTED_REPEATS`. Phone session 3 adds four repeats, all identical boards (no rotated or mirrored ones exist in the corpus):
**L86 = L66** (a door level), **L100 = L31** (v552's L100 is the older build's V2-L031 = our video L31: the elevator debut),
**L101 = L35** (v552 L101 is V2-L032, which ORCH 19 already ships at L35), **L103 = L45** (v552 L103 is V2-L033, shipped at
L45). Since L35 and L45 come first in our order they keep the V2 boards and L101/L103 get stand-ins. All six stand-ins (L81,
L83 regenerated on the refitted curve; L86 door; L100 elevator; L101 elevator; L103 elevator + boxes) keep the slot's v552
timer and tag. The detector over our order before the stand-ins finds exactly these six (`repeats.py --order`,
build/recast2/repeats-order.txt), the raw research corpus 13 repeats (every ORCH 19/26/28 case, build/recast2/
repeats-raw-corpus.txt), and the shipped L1–L150 none (`repeats.py`, build/recast2/repeats.txt); no near repeat (same arrow
cells with other heads) anywhere. The validator enforces it (`L%d repeats L%d`, rotations and mirrors included).
The spares are byte-identical to the boards CONTENT L1 overlay-proved at L62-L64 (`build/l1/overlay.log`: tol1 0.9998 /
0.9983 / 0.9996); the V2 frames themselves are no longer on disk.

### 2.5 L62–L83: phone session 2 (source "recorded") and what was completed
`research/levels/L062–L083.json` (+ `-openK` states; `research/levels.md` "Phone session 2"; the ledger
`research/phone-session2-progress.md`). Completed (every value cited):

| level | completed | source |
|---|---|---|
| 62 | boxes 23 (top-right), 66 (middle), 34 (bottom-left); 2 doors (bottom-right opens first), 35 hidden arrows, the second key under the first door; the 53-cell key arrow under the bottom door humps twice over its top frame (row 20: the two head-less "U" stubs of the start read) | counters_note; reveals from bot/tmp/L062-111843 (the winning run; its start lacks 5 latency taps, so only its revealed arrows are used); L062-open2 = the same 16 arrows |
| 63 | pipe counters 3, 3; 1 door, 22 hidden arrows | bot/tmp/L063-112956-r01; reveals = L083's run arrow for arrow |
| 65 | the 767-cell "door" blob split into 2 doors (left 13×34, right-middle 13×10) + 2 boxes (22 top 13×7, 52 bottom 13×8); 42 hidden arrows, the second key under the first door | shots/421 (the blob count 442 + 130 + 91 + 104 = 767 agrees); reveals bot/tmp/L065-122221 |
| 66 | the key on the long row-5 arrow (override L066) spans (6,5)-(7,5) (the read kept one cell) | research/bot/overrides/L066.json |
| 67 | boxes 25 / 21 / 14 / 9 on the anti-diagonal (top-right → bottom-left); the 3 override arrows are in the start JSON | counters_note, overrides/L067.json |
| 68 | pipe counters 6 (top), 3 (bottom) | counters_note |
| 69 | FOUR doors (top; three side by side at the bottom, frames at x 7.5 / 17.5 on shots/450); 4 keys (3 at the start + 1 under the bottom-left door on the col-0 arrow, override L069); **three pipes UNDER doors** (bottom-left 2, bottom-right 4, top 3), badges detected on the round shot where each door is first open | reveals bot/tmp/L069-124510 + -124847; counters by eye |
| 70, 71, 73, 76, 79, 80, 82 | corners: `facing` (the plate's diagonal) → `turn` (SPEC-gameplay §3.9; `import_research.FACING_TURN`, selftested against research/bot/corners.py for all 16 pairs) | research JSON |
| 73 | boxes 46 (top-right), 58 (bottom-right) | counters_note |
| 82 | pipe counters 6, 6, 6 | shots/533 read by eye |
| 72, 75, 77, 81, 83 | imported like the rest (L77's staircase split as L57's), but they repeat earlier boards and do not ship (§2.4) | |

Rules check (`design/tools/replay_log.py`, build/recast/replay-log.txt): the phone bot's winning taps on every L62–L83 level it
played (1,108 logged taps: 1,101 exit, 7 are units the bot misread) replayed in order under arrowcore: **0 bumps** — the corner levels L73/L76/L79/L80/L82 (18 corners),
L69's pipes under doors and all door/key orders included (the 7 misread units match no arrow; hand taps —
the latency agent's, the clips', the hit-tolerance probe's — are removed first).

### 2.6 L84–L105: phone session 3 (source "recorded") and what was completed
`research/levels/L084–L105.json` (+ `-open1` states; `research/levels.md` "L84 (phone session 3)"; the ledger
`research/phone-session3-progress.md`). v552's timers and tags as recorded: Hard L84 2:00, L94 2:30, L104 3:00; Super Hard L89
2:30, L99 3:00; normals 2:30 (L85, L86, L88, L90–L98, L102) and 3:00 (L87, L100, L101, L103, L105). Completed (every value
cited):

| level | completed | source |
|---|---|---|
| 85, 89, 91, 93, 97, 102 | corner facings: the session-3 start reads carry no `facing`; read from the start shot by research/bot/corners.py (`import_research.corner_facings`, same frame as the JSON; the reader gives L70/L73's recorded facings back exactly) | shots/615, 644, 657, 670, 699, 727 |
| 86 | = L66 (start board pixel-identical): the key spans (6,5)-(7,5) as on L66; 1 door, 12 hidden arrows (the same 12 as L66's reveal) | override L086.json; reveals bot/tmp/L086-145847 |
| 87 | three 6×6 boxes on the right, counters 17 / 34 / 40 top → bottom | levels.md L87, shots/631 |
| 88 | two ∩ pipes, counter 3 each (badge at the right mouth) | levels.md L88, shots/638 |
| 89 | TWO doors side by side: 14×13 (cols 0–13) and 12×13 (cols 14–25; the frame at x 13.5 cells; a hidden U runs up col 13), 34 hidden arrows; 2 keys at the start; its top-left CORNER lies UNDER the left door | shots/644; reveals bot/tmp/L089-150741 |
| 92 | the 18×3 box along the top, counter 15; two U pipes, counter 3 each | levels.md L92 |
| 93 | three doors in a rising staircase (7×7 / 7×10 / 7×13), 28 hidden arrows; 1 key at the start + one key under each of the first two doors to open | shots/670; reveals bot/tmp/L093-152916 |
| 96 | one 58-cell zig-zag pipe, counter 3 | levels.md L96 |
| 97 | the 4×26 pillar box, counter 21 | levels.md L97 |
| 98 | two 12×16 doors side by side, 44 hidden arrows; 1 key at the start + 1 under the first door | shots/703; reveals bot/tmp/L098-155420 |
| 100, 101, 103 | ARE the older build's V2-L031 / V2-L032 / V2-L033 in the same cell frame (visible 28/28, 29/29, 36/36 with the same heads; platforms equal; every arrow the phone revealed under the platform, 7/7, 11/11, 15/15, is in the V2 hidden layer): imported from the V2 file with v552's timer and tag; L103's `-open1` dump holds 8 of 17 hidden arrows (taken while the second elevator was still opening), so its hidden layer is V2-L033's | `import_research.import_phone_v2` |
| 102 | a new elevator board: the platform = the start read's 260 lavender cells (24 arrows on it), the hidden layer = 22 arrows from the bot's `-open1` dump, confirmed by every later round shot | reveals (elevator) bot/tmp/L102-162126 + -162556 |
| 105 | two C pipes on the left edge, counter 3 each | levels.md L105 |

Every L84–L105 board validates as recorded (0 errors). Rules check (`replay_log.py`, build/recast2/replay-log.txt): the phone
bot's logged taps on every session-3 level that ships as recorded, and on L86/L100/L101, replayed under arrowcore: **0 bumps,
0 ignored taps** (8 units the bot misread during the elevator animations match no arrow, as in session 2). Session 3 needed
three replay refinements, none of them a rule change: a per-round frame shift (the bot's free grid fit lands on another
origin while an elevator animates), hand taps (clips, the hit-tolerance probe) removed whenever a logged tap would not exit,
and the elevator clip's unlogged round replayed with the platform's arrows last (the clip stops right after the tap that
empties the platform). L103 is not replayable (its log repeats the cells of two platform arrows after they left; the board is
V2-L033, verified by the video pipeline, and does not ship: build/recast2/replay-L103.txt). The refinements are `replay(level,
refined=True)` (what `replay_log.py` runs); `replay(level)` keeps content recast 1's mapping (one shift per level, hand taps
removed once, first), because PathCore's BotReplayTests implements that mapping and checks itself against the verdict
`Packages/PathCore/Tests/tools/c4b_bot_replay.py` pins with it (Fixtures/c4b_bot_replay.json: L69 + the corner levels; the
legacy mode equals recast 1's `replay_log.py` on every L62–L105 level, checked). On those six levels only L73 reads
differently: one round the bot read in another frame gives 57 exits + 4 unmatched units with one shift, 61/61 exits with
per-round shifts.

### 2.7 What the art must draw (generated)
Doors at any size come from the door generator (`art/tools/manifest.py add-door W H`); boxes need a sprite (or 9-slice) per size;
elevators are code-drawn (`elevatorPlatform`); tapes use the six `tape{H,V}{2,3,4}` sprites (V = a vertical band across horizontal
arrows, as L32's top-left bundle); corners use `cornerWedge` rotated per `turn` (the plate faces: downRight = up-right, downLeft =
up-left, upRight = down-right, upLeft = down-left). A pipe under a door (L69) is drawn only from that door's burst on.
<!-- BEGIN:art -->
| kind | sizes (cells W x H or sprite id): levels |
|---|---|
| door (34 sizes) | W10H15: 37,63; W20H8: 40,61,81; W7H7: 55,96; W11H10: 47; W12H16: 88; W20H9: 117,121; W24H7: 39,55; W26H12: 34,124; W5H17: 44; W8H8: 59; W10H8: 59; W12H13: 99; W13H10: 62; W13H34: 62; W13H4: 44; W14H13: 99; W14H4: 44; W16H7: 59; W17H11: 58; W17H13: 58; W20H10: 45; W22H10: 47; W22H11: 83; W22H13: 67; W24H6: 55; W26H11: 114; W4H12: 33; W4H16: 33; W4H20: 33; W4H4: 33; W4H8: 33; W7H10: 96; W7H13: 96; W9H28: 56 |
| box (26 sizes) | W3H3: 11,15,28,101,120; W3H4: 13,25,27,131; W5H3: 12,60,129; W4H4: 63,82; W5H5: 77; W6H3: 52; W6H6: 92,130; W3H5: 19; W7H7: 58; W10H9: 53; W4H3: 27,115; W4H7: 78; W5H12: 60,129; W5H6: 60,129; W5H9: 60,129; W10H3: 57; W13H7: 62; W13H8: 62; W18H3: 87; W26H3: 144; W4H12: 115; W4H26: 102; W4H6: 115; W4H9: 115; W7H5: 109; W8H4: 107 |
| elevator (11 sizes) | W6H13: 52; W8H5: 105,136; W12H4: 100; W12H7: 31; W20H13: 97; W20H16: 46; W7H5: 140; W7H7: 120; W8H13: 35; W8H4: 101; W9H7: 107 |
| tape (6 sizes) | tapeH3: 17,23,24,28,48,58,91,113,115,130; tapeH2: 7,41,60,66,113,149; tapeV3: 13,24,28,54,58,113,115,138; tapeH4: 10,32,58,65,86,88; tapeV2: 8,37,66,93,149; tapeV4: 10,32 |
| corner (4 sizes) | cornerWedge (downRight): 70,71,73,80,85,89,93,99,102,110,117,131,140,142,145,147,150; cornerWedge (upRight): 71,73,82,89,96,97,99,102,116,132,136,144,145,148; cornerWedge (upLeft): 71,73,76,85,89,93,96,97,102,110,112,116,123,132,140,146; cornerWedge (downLeft): 71,73,76,80,85,89,99,102,116,117,123,128,146,149 |
<!-- END:art -->

## 3. The doors: what they hide (reconstructed; `design/tools/reveal_backfill.py`)
The phone start JSONs hold only what is visible at the start. The phone bot won every door level and saved a lossless shot before
every round (`research/bot/tmp/Lnnn-<run>-rNN.png`, the winning run per `research/levels.md`). The tool re-reads those shots with
the bot's own reader and tracks, in the START json's cell frame (the shift comes from `origin_pt`, as `bot.dump_level` does for its
`-open` files): the door cells that vanish between two clean reads (one door each, in opening order), the arrows that appear (the
hidden ones, each inside the rectangle that opened), the keys and their arrows, and the tapes that appear. Only clean reads are used
(guard ok, 0 reader anomalies).

**Cross-checks.** (1) Every unit the bot TAPPED in that run (`research/bot/log.jsonl`) is mapped to the start frame by the best
integer shift and must equal a start or a reconstructed arrow: every level matches (a few "never tapped" arrows are the second
members of tape bundles, which the log records by one member, or a start arrow whose logged cells were a misread; the only hidden
one, L33 #22, was confirmed by eye: present on r05, gone on r06). (2) On the seven levels that already had `-open` files
(L47, L49, L53, L54, L56-L58 by `reveal.py`), the reconstruction equals them arrow for arrow (L47 28/28, L49 10/10, L53 31/31, L54
30/30, L58 34/34). (3) Every hidden arrow lies wholly inside its door; every door is a rectangle; keys = doors on every level.
(4) The validator solves every door level with the doors' rules (§5).

**Result: 11 of 11 door levels complete, none left unreconstructed.** 337 hidden arrows, 26 doors, 26 keys (16 visible at the start,
10 under doors), 2 tapes under a door (L47). (The table counts L49's key as "0 + 1": its start-JSON key blobs have no cells, so the
tool first sees it on round 1; it is visible from the start, on arrow 58.)
<!-- BEGIN:reveals -->
| L | round shots (clean reads) | start arrows | hidden arrows | doors (opening order: rect c0,r0-c1,r1) | keys (start + hidden) | tapes under doors | bot-log check |
|---|---|---|---|---|---|---|---|
| 33 | 16 (12) | 20 | 30 | 0,16-3,19; 4,12-7,19; 8,8-11,19; 12,4-15,19; 16,0-19,19 | 2 + 3 | 0 | 49/50 taps matched; never tapped: 22 |
| 34 (ships at L44) | 12 (10) | 76 | 40 | 6,31-19,34; 0,9-4,25; 20,9-24,25; 6,0-18,3 | 2 + 2 | 0 | 116/116 taps matched; never tapped: none |
| 37 (ships at L47) | 19 (12) | 14 | 35 | 0,10-10,19; 11,10-21,19; 0,0-21,9 | 1 + 2 | 0 | 49/49 taps matched; never tapped: none |
| 41 (ships at L45) | 15 (10) | 27 | 21 | 0,8-19,17 | 1 + 0 | 0 | 48/48 taps matched; never tapped: none |
| 43 (ships at L40) | 10 (6) | 27 | 32 | 0,24-19,31; 0,16-19,23 | 1 + 1 | 0 | 59/59 taps matched; never tapped: none |
| 46 (ships at L55) | 20 (10) | 56 | 46 | 0,19-23,24; 0,12-6,18; 17,12-23,18; 0,0-23,6 | 4 + 0 | 0 | 101/102 taps matched; never tapped: 43 |
| 47 (ships at L37) | 12 (9) | 29 | 28 | 0,0-9,14; 10,15-19,29 | 1 + 1 | 2 | 55/55 taps matched; never tapped: 40, 54 |
| 49 (ships at L39) | 25 (7) | 59 | 10 | 0,0-23,6 | 0 + 1 | 0 | 69/69 taps matched; never tapped: none |
| 53 (ships at L63) | 13 (5) | 30 | 31 | 0,0-9,14; 0,15-9,29 | 1 + 1 | 0 | 60/61 taps matched; never tapped: 18 |
| 54 (ships at L34) | 16 (12) | 72 | 30 | 0,0-25,11 | 1 + 0 | 0 | 102/102 taps matched; never tapped: none |
| 58 (ships at L67) | 11 (7) | 27 | 34 | 0,11-21,23 | 1 + 0 | 0 | 61/61 taps matched; never tapped: none |
| 62 (ships at L58) | 14 (12) | 44 | 35 | 9,21-25,33; 0,0-16,10 | 1 + 1 | 0 | session 2: replay_log.py (every logged tap exits) |
| 63 (ships at L56) | 17 (17) | 38 | 22 | 13,0-21,27 | 1 + 0 | 0 | session 2: replay_log.py (every logged tap exits) |
| 65 (ships at L62) | 14 (12) | 23 | 42 | 13,7-25,16; 0,0-12,33 | 1 + 1 | 0 | session 2: replay_log.py (every logged tap exits) |
| 66 (ships at L61) | 6 (4) | 13 | 12 | 0,6-19,13 | 1 + 0 | 0 | session 2: replay_log.py (every logged tap exits) |
| 69 (ships at L59) | 19 (17) | 58 | 41 | 0,26-7,33; 18,26-25,33; 5,0-20,6; 8,26-17,33 | 3 + 1 | 0 | session 2: replay_log.py (every logged tap exits) |
| 83 | 16 (14) | 38 | 22 | 13,0-21,27 | 1 + 0 | 0 | session 2: replay_log.py (every logged tap exits) |
| 86 (ships at L81) | 7 (4) | 13 | 12 | 0,6-19,13 | 1 + 0 | 0 | session 3: replay_log.py (every logged tap exits) |
| 89 (ships at L99) | 13 (12) | 65 | 34 | 0,0-13,12; 14,0-25,12 | 2 + 0 | 0 | session 3: replay_log.py (every logged tap exits) |
| 93 (ships at L96) | 14 (10) | 36 | 28 | 14,13-20,25; 7,16-13,25; 0,19-6,25 | 1 + 2 | 0 | session 3: replay_log.py (every logged tap exits) |
| 98 (ships at L88) | 12 (8) | 42 | 44 | 0,7-11,22; 12,7-23,22 | 1 + 1 | 0 | session 3: replay_log.py (every logged tap exits) |
<!-- END:reveals -->
Notes. L37's start JSON reads 2 doors (touching blobs); the shots show 3 (two side by side below one wide door, as levels.md says).
L46's reads 2; it has 4 (levels.md). L49's two key blobs with empty cells are the reader splitting one key; the real key rides the
override arrow 58 (bot/overrides/L049.json). Door order is data: the recorded doors did not always open "lowest first" (L47 opened
its top-left door first, L53 its upper door first), so each level stores the observed order.

**Phone session 2 (L62, L63, L65, L66, L69; L83 = L63 as a cross-check), `reveal_backfill.backfill_s2`.** The session-2 start reads
merge touching doors (L69's three bottom doors read as one 26×8 blob) and doors touching boxes (L65: one 767-cell blob), so the
door RECTANGLES are curated (`DOOR_RECTS_S2`, measured on the start shots) and a door counts as open on the first round shot
where its rectangle holds no door/box ink; reads apply the session-2 overrides and are kept despite reader anomalies (nearly
every S2 read has one), with every addition cross-checked: a new arrow must lie inside a door that is open (or poke out of it
only onto the start read's head-less stubs, L62), overlaps are refused, the bot's own `-open` dumps must be explained (L62-open2,
L63-open1, L65-open1, L66-open1, L69-open1, L83-open1: 0 unexplained arrows), and the overlay proof checks every door's ink
(`overlay_recast.py --reveals`: 10 doors, 152 hidden arrows, all pass, min tol1 0.9976; 30/30 of its negative controls caught).
L63 and L83 (the same board, two runs) reconstruct the same 22 hidden arrows. New in S2: **pipes under doors** (L69, SPEC-gameplay
§3.5) and a hidden arrow that **pokes out of its door** (L62's key arrow humps over the bottom door's top frame; the validator
allows it only where no ray can reach those cells while the door is shut).

**Phone session 3 (L86, L89, L93, L98), `reveal_backfill.backfill_s3`.** The session-2 method with curated rectangles
(`DOOR_RECTS_S3`, which must tile the start read's door blob; its only extra cells may be key cells), plus: every round shot
is read on the START shot's grid (as research/bot/go3.py --fit-from does) and with research/bot/corners.py's reader (L89/L93
carry corners); reads taken mid-animation (more than 3 reader anomalies: a door bursting) are skipped, and a key must span
2 cells (1-cell "keys" are burst debris). Cross-checks: every arrow in the bot's own `-open1` dump that is not a start arrow
is a reconstructed hidden arrow (L86 12/12, L89 34/34, L93 13/13, L98 35/35), keys = doors on every level, L86 reconstructs
L66's 12 hidden arrows exactly, and the overlay proof checks every door's ink (§6). New in S3: **a corner under a door**
(L89's top-left corner, drawn under the left door's frame; it turns rays once the door has opened, SPEC.md §5 item 26).

**Elevators (v552's debut at L100), `reveal_backfill.backfill_elevator`.** The platform = the start read's lavender
`elevator` cells; its arrows = the start arrows wholly on it; the hidden layer = the arrows that appear wholly on it in the
bot's `-open1` dump (research/bot/go3.py --elevator dumps right after the platform's last arrow left) and on every later round
shot of the run. L100/L101/L103 match the older build's V2-L031/032/033 hidden layers (§2.6); L102 ships (22 hidden arrows).
<!-- BEGIN:elevators -->
| L | platform cells | platform arrows (start) | hidden arrows | read from | problems |
|---|---|---|---|---|---|
| 100 | 84 | 9 | 7 | L100-open1.json | none |
| 101 (ships at L105) | 104 | 8 | 11 | L101-open1.json | none |
| 102 (ships at L97) | 260 | 24 | 22 | L102-open1.json | none |
| 103 (ships at L101) | 156 | 17 | 15 | L103-163321-r07.png, L103-open1.json | hidden arrows first read on round shots after the open dump: ['L103-163321-r07.png'] |
<!-- END:elevators -->

## 4. The curve: L106–L150 against the recorded levels
`gen_levels.py` (SPEC-gameplay §14.3) takes each level's targets from the recorded level at the same position of a ten-level cycle
(content recast 2: L3p … L9p in rotation, `curve.slots` 7, i.e. every recorded decade L30–L99; p 4 = Hard, p 9 = Super Hard,
the phone's cadence L34 … L94 and L39 … L99), grows them 2 % per decade from L100 (was L80; capped at 25 %, reached at
L230), takes the template's own v552 timer (`timers.fromTemplate`: Hard 1:40 … 3:30, Super Hard 2:00 … 3:00 as recorded;
session 3 adds Hard 2:00 (L84) and 2:30 (L94)), draws the obstacle mix from each kind's share of v552 L40–L105 since its
unlock in our order (door 27 %, pipe 23 %, box 21 %, tape 17 %, corner 36 %: 13 of L70–L105; the elevator is now fitted like
the others — v552's L100–L103 — and gives 6 %, the value it was held at while it was video-only; kinds per level 0/1/2 =
26/36/38 %), lays corners on empty margin lines (one side or two adjacent sides, 1–3 each), and keeps the best of 10
solver-proved candidates that pass the validator (the gate: only L136 needed it). The previous fit (templates L30–L79, growth
from L80, the L84–L150 designed range) is replaced; the endless levels past L150 follow the new curve (curve.json in the
bundle; `CurveSpec.default` must be updated to it by CORE: see the recast-2 report).
<!-- BEGIN:curve -->
| range | tag | levels | units | waves | free at start | arrows | mean length | grid cols | grid rows | timers |
|---|---|---|---|---|---|---|---|---|---|---|
| video L1-31 | normal | 28 | 3-48 (median 25) | 1-18 (median 10) | 1-11 (median 6) | 3-54 (median 25) | 9.5 | 3-27 (median 14) | 4-27 (median 19) | 3:00 x28 |
| video L1-31 | hard | 2 | 61-62 (median 62) | 24-25 (median 25) | 10-11 (median 11) | 61-62 (median 62) | 8.8 | 19-20 (median 20) | 30-31 (median 31) | 3:00 x2 |
| video L1-31 | superHard | 1 | 68-68 (median 68) | 29-29 (median 29) | 13-13 (median 13) | 68-68 (median 68) | 8.9 | 20-20 (median 20) | 32-32 (median 32) | 3:00 x1 |
| phone+substitutes L32-61 | normal | 24 | 16-102 (median 48) | 7-44 (median 19) | 1-13 (median 6) | 16-102 (median 48) | 9.2 | 10-24 (median 20) | 18-32 (median 24) | 3:00 x16, 2:30 x8 |
| phone+substitutes L32-61 | hard | 3 | 83-116 (median 102) | 33-44 (median 42) | 5-16 (median 6) | 91-116 (median 102) | 8.1 | 25-26 (median 25) | 34-36 (median 35) | 3:30 x1, 3:00 x2 |
| phone+substitutes L32-61 | superHard | 3 | 69-102 (median 85) | 30-38 (median 34) | 10-16 (median 12) | 69-102 (median 85) | 9.8 | 24-26 (median 24) | 34-36 (median 34) | 3:00 x1, 2:30 x1, 2:00 x1 |
| phone+substitutes L62-83 | normal | 18 | 22-72 (median 50) | 6-30 (median 18) | 2-11 (median 7) | 22-79 (median 55) | 9.5 | 16-26 (median 20) | 18-34 (median 26) | 3:00 x10, 2:30 x8 |
| phone+substitutes L62-83 | hard | 2 | 75-113 (median 113) | 33-43 (median 43) | 13-13 (median 13) | 75-113 (median 113) | 8.8 | 24-26 (median 26) | 30-36 (median 36) | 3:00 x1, 1:40 x1 |
| phone+substitutes L62-83 | superHard | 2 | 74-99 (median 99) | 28-36 (median 36) | 9-14 (median 14) | 74-99 (median 99) | 8.8 | 24-26 (median 26) | 30-34 (median 34) | 3:00 x1, 2:00 x1 |
| phone+stand-ins L84-105 | normal | 17 | 32-80 (median 41) | 12-31 (median 18) | 4-13 (median 6) | 32-86 (median 41) | 9.4 | 16-24 (median 20) | 17-30 (median 23) | 3:00 x5, 2:30 x12 |
| phone+stand-ins L84-105 | hard | 3 | 83-104 (median 87) | 34-44 (median 38) | 1-15 (median 13) | 83-104 (median 87) | 9.4 | 25-26 (median 26) | 33-36 (median 36) | 3:00 x1, 2:30 x1, 2:00 x1 |
| phone+stand-ins L84-105 | superHard | 2 | 85-99 (median 99) | 25-36 (median 36) | 9-17 (median 17) | 85-99 (median 99) | 8.8 | 26-26 (median 26) | 32-36 (median 36) | 3:00 x1, 2:30 x1 |
| designed L106-150 | normal | 36 | 16-88 (median 42) | 5-28 (median 15) | 2-12 (median 6) | 16-89 (median 42) | 10.7 | 12-25 (median 20) | 16-31 (median 24) | 3:00 x17, 2:30 x19 |
| designed L106-150 | hard | 4 | 95-119 (median 119) | 21-39 (median 35) | 10-14 (median 13) | 95-119 (median 119) | 8.0 | 26-26 (median 26) | 34-36 (median 36) | 3:30 x1, 3:00 x1, 2:30 x1, 2:00 x1 |
| designed L106-150 | superHard | 5 | 75-112 (median 101) | 26-40 (median 33) | 8-17 (median 12) | 75-112 (median 101) | 8.4 | 24-26 (median 26) | 30-36 (median 34) | 3:00 x3, 2:30 x1, 2:00 x1 |
<!-- END:curve -->
Obstacle mix per level (a level can have two kinds):
<!-- BEGIN:mix -->
| range | levels | none | tape | door | pipe | box | elevator | corner | two kinds |
|---|---|---|---|---|---|---|---|---|---|
| video L1-31 | 31 | 13 (42 %) | 8 (26 %) | 0 (0 %) | 5 (16 %) | 8 (26 %) | 1 (3 %) | 0 (0 %) | 4 (13 %) |
| L32-61 (as shipped) | 30 | 5 (17 %) | 7 (23 %) | 11 (37 %) | 9 (30 %) | 5 (17 %) | 3 (10 %) | 0 (0 %) | 10 (33 %) |
| L62-83 (as shipped) | 22 | 4 (18 %) | 3 (14 %) | 6 (27 %) | 6 (27 %) | 5 (23 %) | 0 (0 %) | 7 (32 %) | 8 (36 %) |
| L84-105 (as shipped) | 22 | 6 (27 %) | 3 (14 %) | 4 (18 %) | 4 (18 %) | 4 (18 %) | 4 (18 %) | 6 (27 %) | 9 (41 %) |
| L70-105 (as shipped, corners unlocked) | 36 | 9 (25 %) | 4 (11 %) | 5 (14 %) | 7 (19 %) | 6 (17 %) | 4 (11 %) | 13 (36 %) | 12 (33 %) |
| designed L106-150 | 45 | 14 (31 %) | 5 (11 %) | 4 (9 %) | 8 (18 %) | 8 (18 %) | 4 (9 %) | 18 (40 %) | 16 (36 %) |
<!-- END:mix -->
Arrow shape (the generator samples lengths from the recorded histogram and was tuned to the recorded turn rate):
<!-- BEGIN:lengths -->
| range | arrows | mean | p10 | p25 | p50 | p75 | p90 | p99 | max | turns per interior cell |
|---|---|---|---|---|---|---|---|---|---|---|
| phone L32-105 (recorded only) | 3662 | 9.0 | 3 | 4 | 6 | 10 | 20 | 44 | 118 | 0.35 |
| designed L106-150 | 2560 | 9.5 | 2 | 4 | 6 | 12 | 21 | 44 | 58 | 0.40 |
<!-- END:lengths -->
Reading the fit (content recast 2):
- Units, grid sizes, free-at-start, arrow lengths and turns sit in the recorded bands; the video range L1–L31 is lighter, as the
  original's early game is.
- **Waves** of designed normals (median 15) sit a little under the phone's (18 in L62–L83 and in L84–L105); arrows are a
  little longer (mean 9.5 cells vs 9.0, turns 0.40 vs 0.35 per interior cell). Some designed Hard levels with doors stay
  shallower than their templates (L124, door band, 21 waves against the 45 of its template, v552's L84); the plain ones hit
  their targets. Difficulty still peaks on every x4/x9 level (75–119 units).
- **Timers** (the template's): designed normals 3:00 ×17 / 2:30 ×19 (phone L84–L105: 5 / 12 — v552 shortened its normals
  after L83); Hard 3:30 (L144 ← L34), 3:00 (L114 ← L74), 2:30 (L134 ← L94), 2:00 (L124 ← L84); Super Hard 3:00 (L119 ← L79,
  L139 ← L99, L149 ← L39), 2:30 (L129 ← L89), 2:00 (L109 ← L69).
- **Corners** appear beside the block on an empty margin line, never on two opposite sides (no ray can loop): designed 40 %
  against v552's 36 % since L70. The elevator (unlocked at L31 by the videos, at L100 on v552) keeps appearing (9 %), so it
  is never a dead-end mechanic (the verifier's concern 3).
- **Pipe counters**: each designed pipe gets 2–5 "feeder" arrows lined up in front of one mouth (the recorded pattern), so its
  counter lands where the recorded ones do (table below; session 3's seven pipes all read 3).
- **Difficulty bands** (SPEC.md §5 item 27; `DifficultyBands.designed` = the designed range's envelope widened by 25 % of its
  width): the designed L106–L150 give units 0.842–1.239, waves 0.467–1.500, free −6…+5 against their targets → bands units
  0.743…1.339, waves 0.208…1.758, free −9…+8 (build/recast2/bands.txt; CORE updates the constants, see the report).
<!-- BEGIN:pipes -->
| range | pipes | counters (value x count) |
|---|---|---|
| video L1-31 | 10 | 1 x2, 2 x1, 3 x7 |
| L32-61 (as shipped) | 24 | 1 x2, 3 x10, 4 x9, 5 x2, 8 x1 |
| L62-83 (as shipped) | 14 | 2 x1, 3 x6, 4 x3, 6 x4 |
| L84-105 (as shipped) | 7 | 3 x7 |
| designed L106-150 | 11 | 1 x1, 2 x2, 3 x3, 4 x2, 5 x3 |
<!-- END:pipes -->
- Beyond L150 the same algorithm runs at runtime (C4): growth reaches its 25 % cap at L230 and the distribution is stationary after.

## 5. Validation (`design/tools/validate_levels.py`)
Per level: the bundle schema (unknown keys, required keys, value ranges: timer 60–600 s, hearts 3, tags); structure (ids, ≥ 2 cells,
orthogonal steps, `dir` = the last step, no shared cells per layer, in the grid, no ray over the arrow's own body — straight and
through pipes); obstacles (tape ties = the cell behind each member's head, members straight/parallel/equal; doors, boxes and
platforms rectangles; `reveals` = the arrows hidden by it; keys on their rider, keys = doors, door orders 0…n−1; pipes an ordered
path with its mouths at the ends and `out` continuing the tube, counters 1–9, `counter_at` on the tube; box counters 1…arrows−1;
the elevator's platform list = every layer-1 arrow inside it); nothing covering a visible arrow; **solved by the greedy solver**
(DFS reported when greedy fails); every pipe passed, every box broken, every door opened, every elevator activated in that
solution; **no dead end in 40 seeded random play orders** (pipe/elevator/corner levels); no ray that loops through pipes/corners;
an obstacle may lie wholly inside a door (under it; L69) and a door-hidden arrow may poke out of its door only where no ray can
reach it (L62); the bot at 0.6 s per tap keeps ≥ 20 % of the timer; `metrics` equal the recomputed ones. Across levels: numbers
1…150; each unlock card exactly at the feature's first appearance and nowhere else; sessions and tutorials point at real levels
and arrows; no two boards identical (`repeats.py`: offset-free, under the 8 rotations/mirrors of the square, on the
start-visible arrows or on every layer; the message names the first occurrence).

Result on `design/levels.json`: **150 levels, 0 errors, 1 warning** (L6, 27 columns: fit pitch 13.55 pt, below the 14.04 pt zoom
floor; VERIFIED, the video shows it at 13.56 pt). First appearances: Linked L7, Box L11, Pipe L21, Elevator L31, Door L33,
Corner L70 (the Corner card, the original's text).

Negative controls (`design/tools/validator_selftest.py`): L13 box 28 → 29 (a tight counter), L29 arrow 67 reversed, L7's unlock
removed, L21 pipe counter 0, L33 door `reveals` one short, L47's hidden key removed, L32 tie moved off its cell, L35 given back its
phone board (= L21), L62 box counter = its arrow count (was L64, now a plain Hard board), L31 platform list one short; recast:
L70's corners turned away, an L69 pipe moved half out of its door, L62's poking key arrow made visible, L72 given back its
phone board (= L14), L70's Corner card removed; recast 2: L86 given back its phone board (= L66), L134 given L94's board
mirrored left-right (a mirrored repeat: only the symmetry-aware check sees it), L101 given back its phone board (= V2-L032,
shipped at L35), L93's key hidden under its first door removed (the staircase never opens), L102's platform list one short:
**20/20 caught** (build/recast2/selftest.txt; the same 20 with the Python messages in
Packages/PathCore/Tests/Fixtures/c4_negative_controls.json).

## 6. Notes for the build
- `design/levels.json` keeps research ids: start arrows 0…n−1 as read, hidden arrows after them (C2's golden-rounds test maps by
  cell set anyway). Designed levels number visible arrows in reading order of their heads, then the hidden ones by hider.
- `mask` is null everywhere: the silhouette is the set of arrow cells (the dots appear only where arrows were; VERIFIED on the L6
  heart, `research/video-levels-A.md` §6).
- `_from` (a comment key, ignored by the decoder) explains the thirteen substituted levels (L35, L45, L51, L52, L72, L75, L77 =
  V2 boards; L81, L83, L86, L100, L101, L103 = designed stand-ins).
- CONTENT's overlay proof applies to source "recorded" (IoU ≥ 0.99) and "video" (≥ 0.97) levels, including the seven V2 boards
  (proved by L1 at 11:32; their frames were later removed from research/video-frames/V2/). Recast: 17/17 recorded L62–L82 pass
  (min tol1 0.9924, `build/recast/overlay.log`; `overlay_recast.py` adds the corner art and L62's poking cells to the excluded
  obstacle art). Recast 2: the 18 boards of L84–L105 that ship as recorded (the stand-in slots L86, L100, L101, L103 do
  not) pass, min tol1 0.9931 (L102), 54/54 negative controls caught (`build/recast2/overlay.log`, sheets
  `build/recast2/overlay/sheet-0{0,1,2}.png`); what the session-3 doors hide (L89, L93, L98: 7 doors, 106 hidden arrows, each
  on the round shot where its door is first open) passes, min tol1 0.9972, 21/21 negatives caught
  (`build/recast2/overlay-reveals.log`); L102's elevator (22 layer-2 arrows on the shot of the bot's `-open1` dump) passes,
  tol1 0.9989, 3/3 negatives caught (`build/recast2/overlay-elevators.log`).
- The PathCore content tests read PINNED copies (Packages/PathCore/Tests/Fixtures/content: levels.json, designed.json;
  `design/tools/pin_fixtures.py`, `--check`); re-pin after every content change.
