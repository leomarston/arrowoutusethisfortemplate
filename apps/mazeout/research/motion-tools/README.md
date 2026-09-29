# motion-tools (Maze Out)

Copied from `apps/matchfactory/research/motion-tools/` on 2026-09-25 and adapted. Used to write `../motion.md`, `../sounds.md`
and `../clips-needed.md`. Python = `~/.venvs/mf3d/bin/python` (numpy, scipy, scikit-image, Pillow). Raw dumps go to `w/`
(gitignored), frame sheets to `../motion-frames/` (gitignored), audio snippets to `../sound-refs/` (gitignored).
Small text results of every script are kept in `out/` so the numbers in motion.md can be re-checked without re-running.

Build: `swiftc -O -o mfx mfx.swift` (the binary is gitignored).

## mfx (changed for the phone captures)
- The phone `rec` movies carry an edit list that starts at the first video sample; the old `mfx` clamped to
  `asset.duration` and set `reader.timeRange`. Both removed: `frames`/`raw` now decode every sample and filter by the
  decoded (presentation) timestamp. All times in motion.md are these presentation times (t = 0 at the clip's first frame).
- `mfx pts IN.mov` (new): every raw sample time + gaps > 30 ms. Use it right after a capture to see how many seconds of
  frames the movie really holds (S1-L32-intro asked for 10 s and holds 1.76 s).
- `mfx audio IN.mov OUT.wav [START END]`: decodes every audio sample; START/END cut in presentation time.
- `segs.swift` (`swiftc -O -o segs segs.swift`): prints each track's edit-list segments and raw sample PTS range.

## Scripts
| script | what |
|---|---|
| `mf.py` | helpers: `raw()` frames + real timestamps (numpy), `frames()`, `sheet()`, audio envelope/onsets/describe |
| `ovs.py CLIP STEP [S E WIDTH COLS x,y,w,h]` | contact sheet (STEP 0 = every real frame) -> `../motion-frames/ov_*.jpg` |
| `track1.py`, `headtrack.py` | exit-arrow extent along a row/column; `headtrack` subtracts a reference frame so the static HUD blue drops out |
| `exitfit.py` | the exit kinematics fit (data table inside, 5 exits, 3 zooms); `out/exitfit.txt` |
| `colourramp.py` | black -> exit-blue colour ramp near the head; `out/colourramp.txt` |
| `ripple.py CLIP X Y T0 T1` | tap ripple radial luminance profile; `out/ripple_*.txt` |
| `dots3.py` | vacated-cell dots: appearance time per dot; `out/dots_P02A.txt` |
| `keytrack.py` | key flight centroid / size / angle (L33); `out/keytrack_L33.txt` |
| `hud_intro.py`, `hudfit.py` | level-intro HUD slide-in, boosters, hearts; spring / easeOutBack fits; `out/hud_intro.txt`, `out/hudfit.txt` |
| `homeidle.py` | home idle bounding boxes (F01); `out/homeidle_F01.txt` |
| `taps.py`, `ov.py`, `spec.py`, `evavg.py`, `excess.py` | Match Factory originals (tray/outline specific, spectrograms, event-averaged spectra) kept for the sound pass |

## Gotchas found here
- Variable frame rate AND capture jitter: consecutive frames can be byte-identical duplicates (L32 intro 0.349/0.366) and
  some frames arrive late; fit curves, never differentiate two neighbouring frames.
- The host `.marks` times do not anchor onsets: the runner's latency from `action_start` to the visible tap varied
  0.43-2.3 s. Anchor on the tap RIPPLE frame (it appears on release, on the same frame the arrow starts to change).
- Every audio track recorded so far is digital silence (see ../sounds.md). Check `mf.audio()` levels before analysing.

## Added in pass 1 (2026-09-25, desk analyst) — the owner's two gameplay videos (YT-A L1-20, YT-B L11-38)
| script | what |
|---|---|
| `yt.py` | reader + contact sheets for the owner's mp4s (`yt.py sheet A|B START END STEP [WIDTH COLS x,y,w,h]`); sets `MFX_SEEK=1` |
| `mfx` `MFX_SEEK=1` | frames/raw seek with `reader.timeRange` (normal mp4s only — never the phone `rec` movies) |
| `sound_inv.py A|B` | every non-silent audio segment with level, centroid, pitch track → `out/sound_inv_*.txt` |
| `cues.py` | event-locked medians per cue class, partials over time, spectrogram PNGs → `out/cues.txt`, `../motion-frames/spec_*.png` |
| `bandtrace.py` | 0.1 s partial trace of a stretch (split overlapping cues) → `out/bandtrace.txt` |
| `hearts_scan.py A|B` | red-heart count in the HUD → heart-loss events → `out/hearts_scan_*.txt` |
| `bump_ytb.py` | bump vignette/heart/axis traces (YT-B 1235, 1249) → `out/bump_YTB.txt` |
| `hand_yta.py` | FTUE hand bbox → `out/hand_YTA.txt` |
| `exitscan.py A|B S E FPS` + `combofit.py` | exit colour census vs tap gaps; combo window fit → `out/exitscan_*.txt`, `out/combofit.txt` |
| `exitcolour.py` | PHONE round shots vs bot taps (first attempt; contaminated by static blue — kept for the record) → `out/exitcolour.txt` |
| `out/winscan_A.txt` | per-frame luminance / dark / panel flags for YT-A (win beat table) |
| `out/door_burst_L33.txt` | door-burst debris per frame (PHONE L33) |
Gotcha: `sound_inv` joins sounds < 0.15 s apart into one segment — the YT-A unlock chime hides inside the coin cue's segment
(use `bandtrace.py`).

## Added in pass 2 (2026-09-25 05:30) — player part 2's v552 clips + lossless start shots
| script | what |
|---|---|
| `phone_audio.py` | every phone clip's audio: presence, envelope, onsets, 50 ms partial trace, spectrogram → `out/phone_audio.txt`, `../sound-refs/phone_*.wav` |
| `phone_xcorr.py` | v552 click vs YT-A click (corr 0.993); YT-A coin / YT-B chime templates scanned over the home-return audio → `out/phone_xcorr.txt` (NCC after the 4.709 edit cut is garbage: zero-filled) |
| `phone_cues.py` | per-cue windows of S1-L50-win-seq-2-continue (level, span, partials start/mid/end, tick onsets) → `out/phone_cues.txt` |
| `bumptrack.py` | bumped arrow position ALONG ITS PATH (level JSON polyline + ray, board offset per clip), body/blocker colour, edge G, heart px → `out/bumptrack_v552.txt` |
| `bumpfx.py` | vignette colour/depth profile at the left edge + the breaking heart's red area/centroid/bbox → `out/bumpfx_v552.txt` |
| `exittrack.py` | exit head/tail along path + ray with an auto-fitted board offset; stops at the HUD/booster zone → `out/exittrack_*.txt` |
| `exitfit2.py` | pass-1 exits + the 6 new ones; exp model + linear T(d) → `out/exitfit2.txt` |
| `introzoom.py`, `introdraw.py`, `introfit.py`, `introdraw2.py` | v552 level intro: pipes-top landmark → zoom law (easeOutCubic 1.49→1, 1.35 s), per-arrow draw-in through the fitted zoom → `out/introzoom.txt`, `out/introdraw_L48.txt`, `out/introfit_L48.txt`, `out/introdraw2_L48.txt` |
| `hud_intro2.py` | `hud_intro.py` for any clip/time window → `out/hud_intro_L48.txt`; fits in `out/hudfit_L48.txt` (inline script, easeOutBack vs spring) |
| `winscan_v552.py` | per-frame win metrics (bg luminance, dot colour, sign/purple/white, panel, confetti) → `out/winscan_v552.txt` |
| `geom.py` | stroke width / tail cap / corner fillet / head profile from lossless start shots + JSONs → `out/geom.txt` |
| `pitchest.py SHOT…` | board pitch from ink periodicity (validated on start shots; used for the zoom limits) |
| `out/boxbreak_L50.txt`, `out/bulbhint_L62.txt`, `out/bumpfit_v552.txt` | inline measurements (box shards, bulb hint, bump kinematics fits) |
Gotchas: `mf.raw()` returns MOVIE time (edit list applied) — the same clock as `mfx audio`; a clip with two `vide` edit
segments has a hidden wall-clock hole at the join (`segs FILE`). The ripple (grey, L 180–250) and the ✖ badge contaminate
naive ink trackers: track the tail when the head is near a badge, and the head when the tail is inside a ripple.
