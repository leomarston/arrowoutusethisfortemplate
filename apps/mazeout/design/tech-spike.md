# Maze Out board engine: tech spike

Date: 2026-09-25, 00:24–01:35 (+03). This was a throwaway prototype. Source: `apps/mazeout/build/spike/`, about
2,000 lines. The folder is gitignored and DerivedData is already deleted. It builds with xcodegen as an iOS 18
SwiftUI app hosting a UIKit board.

It ran in Release on the **"Maze A"** simulator: 177520B6-4889-46C2-BDD9-155813D2B175, iPhone 16, 393x852 pt
(the same point size as the owner's iPhone 15), iOS 26.0, 60 Hz, on the Apple M2 Mac.

**Where the numbers come from:**
- Timers inside the app: a `CADisplayLink` histogram, `task_vm_info.phys_footprint`, and `CACurrentMediaTime`.
- `simctl io screenshot` captures at 3 px/pt, measured with numpy.
- One XCUITest run with real touches.
- Raw results: `design/spike-results/*.json`. Screenshots: `design/spike-shots/`.

**Tags:** VERIFIED = measured here. INFERRED = my reading. PHONE = must be verified again on the iPhone 15.
Nothing here used the phone. It was in use by another agent.

## Verdict

**GO: UIKit + Core Animation, one `CAShapeLayer` stroke plus one head layer per arrow, inside a `UIScrollView`,
hosted in the SwiftUI shell.** Every checklist point passed on the simulator:

| # | Question | Result |
|---|---|---|
| 1 | Board from JSON | The phone player's `research/levels/L032.json` loads as-is: 53 arrows, 20x20, 4 tapes. My independent extractor (`build/spike/tools/extract_l32.py`) produced the **identical** 53 arrows. The synthetic 40x40 heart silhouette has **304 arrows** / 873 cells, solvable by construction. |
| 1b | Our L32 render vs the original shot 003 (same 393x852 pt screen) | Board lands on the same pixels; the best shift is 0/1 px. Black-ink IoU is **0.909** with the tape areas excluded, and total ink coverage is within **0.6 %**. Measured widths: stroke 12.02 px vs 12.0, dot Ø 10.27 px vs 10.3, dot colour #C5E1FF exact. Sheets: `spike-shots/l32-fit-sbs.png` and `l32-fit-vs-ref-diff.png`. |
| 2 | Zoom from 0.75x to 3x of fit, crisp | `minimumZoomScale 0.75` and `maximumZoomScale 3` (launch-arg tunable). A real pinch (XCUITest) clamped at **3.00** and **0.75**. Strokes stay vector-sharp: **2 partially covered px per stroke** (one per edge) at 3x, where the width is 18.89 px (expected 18.87). Also sharp mid-exit at 3x for the solid, gradient-masked and dashed painters. No `contentsScale` fix was needed. |
| 3a | Hit test by grid maths | The touched cell's owner, else the nearest centreline within max(½ cell, 14 screen pt) among the owners of the 5x5 neighbouring cells. **0 wrong** out of 873 + 399 jittered in-cell points. Cost **0.35 µs** per query (synthetic board, 100k random points) and 0.007 µs on L32. |
| 3b | Tap fires on RELEASE, even after a long hold (the original fires after a 5 s press) | `UITapGestureRecognizer` **did not fire** after a real 2 s hold (XCUITest run 1). A custom `ReleaseTapRecognizer` did (run 2: the hold removed the arrow; hearts unchanged). |
| 3c | Exit: the body snakes along its path, then out along the head ray at constant speed v | strokeStart/strokeEnd plus the head position share one `CATransaction` with exact linear keyframes. v is tunable, in screen or board space. Screens: `trail-solid-l32.png` and `tape-carry-l32.png`. |
| 3d | Vacated-cell dots | ONE dashed `[0, pitch]` round-capped stroke per departed arrow, revealed by strokeEnd behind the tail. All **399/399** L32 dots are present after autoplay (`autoplay-l32.png`), once the end-of-path pitfall was fixed (P3). |
| 3e | Rainbow trail (store shots 1 and 5) | Two techniques proven, both crisp at 3x. **(A) Gradient runs**: one axial `CAGradientLayer` per straight run, stops at every palette step along the arc length, masked by the trimmed stroke plus the moving head. It is smooth. **(B) Dash steps**: N dashed hue layers; 24 steps still show banding at 3x. Star confetti is a `CAEmitterLayer` that follows the tail, coloured by the band under the tail. Screens: `trail-gradient-l32.png`, `trail-gradient-synth-z3.png`, `trail-dash-*.png` and `trail-gradient-live-slow.png` (live, stars along the path). |
| 3f | Bump: forward to the blocker, back, red from the contact frame | The heart is taken at the contact callback (3 → 2). Colour keyframes run black → red at contact, then red → black over 0.35 s (tunable, or persist). Frames: `bump-synth-f0.9.png` (before contact, black), `f1.25` (at contact, red #FF3B3B), `f2.4` (returning). |
| 4 | 60 fps with 300 arrows at MAX zoom while 5 exit at once | **0 frames > 20 ms** in every run (table below). The 3x runs include up to 13 concurrent movers, and the stress run 67 concurrent gradient movers (1,028 layers). Memory 22–26 MB. First frame 0.37–0.43 s after process start (warm) and 1.06 s on the first cold launch. |

**Default exit look = solid light blue #10A2EF.** That is what the phone shows on L32 (shots/010, measured). The
rainbow of the store shots is a second look: a skin, event or reward (UNKNOWN). The gradient-runs painter is the
recommended implementation for it.

## Measured reference geometry (phone shot 003, 1178x2556 px; pt = px·393/1178)

| | px | ratio of pitch | pt at fit (L32) |
|---|---|---|---|
| Cell pitch (20x20 board) | 53.5 | 1 | 17.85 |
| Stroke: #000000, round caps and joins | 12.0 (coverage integral) | 0.224 | 4.0 |
| Corner | outer radius = half-width, inner sharp = a plain round join on a sharp polyline | — | — |
| Head apex, ahead of the head-cell centre | 20.25 | 0.378 | 6.75 |
| Head base, behind the head-cell centre | 11.25 | 0.210 | 3.75 |
| Head base width, slightly rounded corners | 33.0 | 0.617 | 11.0 |
| Tail | round cap centred on the tail-cell centre | — | — |
| Vacated-cell dot, #C5E1FF | Ø 10.3 | 0.192 | 3.4 |
| Exiting arrow (shots/010) | #10A2EF, the head too | — | — |
| Tape obstacle | #FF6298 | — | — |

- **Fit rule:** pitch = min(W/(cols+2), H/(rows+2)). That gives 393/22 = 17.86 pt against 17.85 measured. The board
  is centred in the play area between the HUD bottom (122 pt) and the booster bar top (755 pt).
- **Vertical head offset (INFERRED: a sprite pivot).** Up and down heads both sit about 4 px (0.075 pitch) lower
  on screen than horizontal-head symmetry predicts:
  - up: apex 15.7 px, base 16.3 px;
  - down: apex 24 px, base 8 px.

  The spike does not copy it. Confirm it on a second level, then add a `headVerticalNudge` constant.
- **Zoom:** research measured the pinch-out at 0.786x of fit; the spike's minimum is 0.75. The maximum is UNKNOWN,
  and the spike uses 3.

## Frame times (the main-thread `CADisplayLink` sees every presented frame; simulator 60 Hz, budget 16.67 ms)

All runs use the synthetic 40x40 board: 304 arrows, fit pitch 9.36 pt, 3x pitch 28 pt. Each exit5 run is 4 waves
of 5 simultaneous exits, 0.7 s apart, measured for 3.5 s. Each stress run is 10 waves of 10, 0.2 s apart.

| Run | Frames | Max ms | > 20 ms | Wave start cost, main thread | Peak movers / layers | Footprint MB | backboardd, Mac CPU % per 1-s sample |
|---|---|---|---|---|---|---|---|
| idle, fit | — | 16.7 | 0 | — | 0 / 614 | 23.1 | 0–5 |
| exit5 solid, z1 | 211 | 16.7 | 0 | 0.8–3.3 ms | 7 / 629 | 22.7 → 23.0 | ≤ 15 |
| exit5 gradient, z1 | 212 | 16.7 | 0 | 2.9–4.4 ms | 7 / 651 | 22.6 → 23.2 | ≤ 24 |
| exit5 dash, z1 | 219 | 16.7 | 0 | 6.7–7.9 ms | 7 / 730 | 22.8 → 24.0 | ≤ 25 |
| **exit5 solid, z3 (max)** | 218 | 16.7 | **0** | 1.2–2.1 ms | 12 / 654 | 22.9 → 23.0 | ≤ 18 |
| **exit5 gradient + stars, z3** | 219 | 16.7 | **0** | 2.3–6.3 ms | 13 / 688 | 22.4 → 23.4 | ≤ 25 |
| exit5 dash + stars, z3 | 219 | 16.7 | 0 | 6.4–9.7 ms | 13 / 958 | 22.5 → 24.5 | ≤ 33 |
| stress solid, z1 (100 exits in 2 s) | 212 | 16.7 | 0 | 0.8–3.8 ms per 10 | 38 / 699 | 22.4 → 23.1 | ≤ 34 |
| stress gradient + stars, z3 | 209 | 16.7 | 0 | 3.1–10.2 ms per 10 | 67 / 1,028 | 22.8 → 25.7 | ≤ 36 |
| zoom ramp 1 → 3 → 0.75 → 1 in 6 s, zoomScale set every frame | 363 | 16.7 | 0 | — | — | — | 31–34 |
| autoplay L32 (53 taps, 0.12 s apart, tapes included) | 519 | 16.7 | 0 | — | 9 / — | 22.3 | — |
| autoplay synthetic (304 taps, gradient) | 1,076 | 16.7 | 0 | — | 14 / — | 23.9 | — |

- **Build and memory:** layers for 304 arrows build in **1.6 ms** (614 layers). The footprint is 22–23 MB after the
  build and at most 26 MB under stress.
- **Autoplay:** both boards cleared with **0 bumps** and 3/3 hearts. No movers were left and no layer leaked: after
  clearing, only the dot layers remain (1 per arrow).
- **Bump timing:** L32 is so dense that all 40 blocked arrows at the start have gap 0, so the contact comes after
  9.1 pt, which is 10 ms at the placeholder v. The analyst's real bump timing therefore matters more than the
  contact geometry.

**Caveat.** On the simulator the render server runs on the Mac GPU, so these rows prove what the spike can prove:
- the main thread stays free (0 hitches, tap cost ≤ 10 ms even for 10 gradient exits at once);
- the layer tree stays small;
- memory is flat.

They do **not** prove the iPhone GPU cost. The backboardd CPU column is only a relative indicator: solid is
cheapest, gradient-masked about 1.5x, dash about 2x, and the zoom ramp is the most expensive.

## Must be verified again on the iPhone 15 (60 Hz, A16) — PHONE

1. **Render-server cost of the worst case:** L32-size and 40x40 boards at 3x, with 5 simultaneous exits using the
   gradient mask plus stars. Use Instruments "Animation Hitches", or on-device `CADisplayLink` stats (build the
   same `Bench` in).
   - Each gradient exit is an offscreen mask pass.
   - Budget: 0 hitches at 60 Hz.
2. **Tap-time main-thread cost** on the A16: gradient exits cost 2–6 ms per 5 on the M2 simulator.
   - If the phone is slower, cache the per-arrow gradient runs at level load, or build them on the first frame
     after the tap.
3. **Real pinch, pan and tap feel.**
   - Tap slop (10 pt) and hold-then-release (verified here with synthetic XCUITest touches only).
   - Whether a 2-finger pinch that starts on an arrow ever fires a tap.
4. **First frame and memory on the device** (simulator: 0.4 s and 23 MB).
5. **Exit speed at 1x and 3x:** it tells whether the original's speed is in screen space (as in the spike) or in
   board space.

## Code that worked (excerpts from `build/spike/App`; the logic is unchanged)

### Rest layers: body stroke + head; the frame hugs the path so off-screen arrows are culled at 3x

```swift
struct LocalPath {                                   // path in its own tight frame
    let frame: CGRect, path: CGPath
    init(_ path: CGPath, pad: CGFloat) {
        let box = path.boundingBoxOfPath.insetBy(dx: -pad, dy: -pad).integral
        frame = box
        var t = CGAffineTransform(translationX: -box.minX, y: -box.minY)
        self.path = path.copy(using: &t) ?? path
    }
    func local(_ p: CGPoint) -> CGPoint { CGPoint(x: p.x - frame.minX, y: p.y - frame.minY) }
}
// ArrowNode.init: body = CAShapeLayer(frame: LocalPath(restPath).frame, lineWidth 0.224p, round cap+join, black)
//                 head = CAShapeLayer(bounds ±p, path headPath(pitch), position headCentre, rotation dirAngle)
```

### Geometry: sharp polyline through the cell centres, so arc length is exact (tail passes cell i at travel i·p)

```swift
var bodyLength: CGFloat { CGFloat(cellCount - 1) * pitch }
func exitPath(ray: CGFloat) -> CGPath { let p = CGMutablePath(); p.addLines(between: corners + [headPosition(ray)]); return p }
func strokeStart(_ s: CGFloat, ray: CGFloat) -> CGFloat { s / (bodyLength + ray) }
func strokeEnd(_ s: CGFloat, ray: CGFloat) -> CGFloat { (s + bodyLength) / (bodyLength + ray) }
func headPosition(_ s: CGFloat) -> CGPoint { CGPoint(x: headCentre.x + dir.dx * s, y: headCentre.y + dir.dy * s) }
func exitTravel(leaving visible: CGRect) -> CGFloat {      // tail cap fully outside `visible`
    let h = headCentre
    let toEdge = dir.dx > 0 ? visible.maxX - h.x : dir.dx < 0 ? h.x - visible.minX
               : dir.dy > 0 ? visible.maxY - h.y : h.y - visible.minY
    return bodyLength + max(0, toEdge) + width
}
func contactTravel(gap: Int) -> CGFloat {                  // apex touches the blocker's stroke
    max(0.05 * pitch, (CGFloat(gap + 1) - Metrics.headApexRatio) * pitch - width / 2)
}
// BoardView.startExit: far = visible ∪ content inset by -25 % of the screen (survives a zoom-out mid-exit);
// travel = exitTravel(leaving: far); ray = travel - bodyLength + pitch; v = speed / zoom (screen space)
```

### Exit: every layer's keyframes, and the `addSublayer`, in ONE transaction with actions disabled

```swift
func keyframes(_ keyPath: String, _ values: [Any], _ track: Track) -> CAKeyframeAnimation {
    let a = CAKeyframeAnimation(keyPath: keyPath)
    a.values = values; a.keyTimes = track.keyTimes; a.timingFunctions = track.fns  // nil = exact linear
    a.duration = track.duration
    a.preferredFrameRateRange = CAFrameRateRange(minimum: 60, maximum: 120, preferred: 120)
    return a
}
CATransaction.begin(); CATransaction.setDisableActions(true)
root.frame = exit.frame; parent.addSublayer(root)          // inside: see pitfall P1
node.body.isHidden = true; node.head.isHidden = true
let body = trimmedStroke(color: exitColor)                 // model = final values, then:
body.add(keyframes("strokeStart", track.travel.map { g.strokeStart($0, ray: ray) }, track), forKey: "s0")
body.add(keyframes("strokeEnd",   track.travel.map { g.strokeEnd($0, ray: ray) },   track), forKey: "s1")
head.add(keyframes("position", track.travel.map { NSValue(cgPoint: exit.local(g.headPosition($0))) }, track), forKey: "p")
// + dots, + stars, + a 1→1 opacity "end" animation whose delegate removes the layers
CATransaction.commit()
```

### Rainbow painter A (recommended): gradient runs under a trimmed-stroke mask; the bands are fixed on the path

```swift
for (k, (a, b, u0)) in g.runs(ray: ray).enumerated() {          // straight runs incl. the ray
    let wide = k >= runs.count - 2                                // last body run + ray carry the head's width
    let half = wide ? headHalfWidth + 1 : width / 2 + 1
    let pad  = wide ? headApex + 1 : width / 2 + 1
    let ua = u0 - pad, ub = u0 + len + pad
    let gl = CAGradientLayer(); gl.frame = runRect                // along the run, thickness 2·half
    // stops: ua, every palette step (period/7) inside, ub; colour = palette(u / period) wraps
    gl.startPoint/endPoint along the run direction
    content.addSublayer(gl)
}
let mask = CALayer(); mask.addSublayer(trimmedStroke(black)); mask.addSublayer(movingHead(black))
content.mask = mask
```

Measured palette (store shot 1, hue rising toward the head): magenta, red, orange, yellow, green, cyan, blue, with
linear RGB between them. Period ≈ 5.6 cells.

### Dots: one layer per departed arrow

```swift
let dotsPath = CGMutablePath(); dotsPath.addLines(between: g.corners + [g.headPosition(1)])  // +1 pt: pitfall P3
dots.lineCap = .round; dots.lineWidth = 0.192 * pitch; dots.strokeColor = #C5E1FF
dots.lineDashPattern = [0.01, NSNumber(value: Double(pitch - 0.01))]
dots.add(keyframes("strokeEnd", clampedTrack.travel.map { min(1, ($0 + 0.02) / (bodyLength + 1)) }, clampedTrack), ...)
```

### Stars: one emitter per exit, following the tail

```swift
em.beginTime = fxParent.convertTime(CACurrentMediaTime(), from: nil)   // pitfall P2
em.add(sampledKeyframes("emitterPosition", samples(1/60 s + every corner).map { g.point(along: s) }), ...)
em.add(sampledKeyframes("emitterCells.star.color", samples(1/20 s).map { palette(s / period) }), ...)  // works
// cell: our own 5-point star drawn in code (96 px, white, tinted), lifetime 0.9 s, scaleSpeed < 0, alphaSpeed = -1/life
```

### Bump colour: red from the contact frame; the heart is taken in the contact callback

```swift
let total = track.duration + (persist ? 0 : 0.35)
a.values   = [black, black, red, red, persist ? red : black]
a.keyTimes = [0, (tc - 0.001) / total, tc / total, track.duration / total, 1]  // tc = profile.time(toReach: contact)
contactMark = CABasicAnimation(opacity 1→1, duration tc), delegate → hearts -= 1
```

### Input: fire on release, and grid-maths hit test

```swift
final class ReleaseTapRecognizer: UIGestureRecognizer {     // UITapGestureRecognizer drops long holds
    var slop: CGFloat = 10; private var start: CGPoint = .zero
    override func touchesBegan(_ t: Set<UITouch>, with e: UIEvent) {
        if (e.allTouches?.count ?? t.count) > 1 { state = .failed; return }
        start = t.first!.location(in: view)
    }
    override func touchesMoved(_ t: Set<UITouch>, with e: UIEvent) {
        let p = t.first!.location(in: view); if hypot(p.x - start.x, p.y - start.y) > slop { state = .failed }
    }
    override func touchesEnded(_ t: Set<UITouch>, with e: UIEvent) { state = state == .possible ? .ended : .failed }
    override func touchesCancelled(_ t: Set<UITouch>, with e: UIEvent) { state = .cancelled }
}
// tap.require(toFail: scroll.panGestureRecognizer); if let p = scroll.pinchGestureRecognizer { tap.require(toFail: p) }
func arrow(at p: CGPoint) -> Int? {                         // p in content (board) space
    let c = layout.cell(at: p)
    if let o = state.owner(c) { return o }
    let tol = max(0.5 * layout.pitch, 14 / zoom)
    // nearest centreline segment among the owners of the (2·reach+1)² cells around c
}
```

### Freeze for deterministic screenshots

```swift
let t = stage.convertTime(CACurrentMediaTime(), from: nil); stage.speed = 0; stage.timeOffset = t
```

`stage.speed = 0.1` gives slow motion for live captures.

### Core rule, solver and generator (PathCore candidates, Foundation-only; verified on macOS with `swiftc`)

- **Occupancy:** a flat `[Int32]` (cols·rows, −1 = empty).
- **Blocking rule:** walk from head + dir to the grid edge; the first live cell of another arrow blocks. Dots never
  block.
- **Tape bundles:** `unit(of:)`. One tap sends all members out, but only if every member's ray is clear. The
  some-clear case is UNKNOWN on the original, and the spike returns `.blocked`.
- **Greedy solver:** each round removes every unit that is free at its start. Removing an arrow only frees cells,
  so greedy decides solvability.
  - L32: 12 rounds.
  - Synthetic board: 14 rounds.
- **Generator: reverse construction, centre outwards.**
  - Cells are ordered by their distance from the centre, plus noise.
  - A random snake grows from each free cell (60 % straight).
  - The head end is chosen so that its ray misses every arrow placed earlier; otherwise the snake is shortened.
  - Removing arrows in the reverse order of placement always works, so every board is solvable by construction.
  - Density: 304 arrows / 873 of 1,018 silhouette cells in 9 ms. Random fill plus repair had only reached
    105–184 arrows.

## Pitfalls found (new relative to apps/arrows/design/tech-spike.md)

- **P1. `addSublayer` has an implicit action too.**
  - Adding the mover's root layer outside `setDisableActions(true)` runs the default "onOrderIn" fade (0.25 s).
  - Every exit and bump was translucent for its first frames: measured 64 % and 83 % ink.
  - Put `addSublayer` inside the no-actions transaction.
- **P2. A `CAEmitterLayer` without `beginTime = now` bursts.**
  - The render server "catches up" the emitter from time 0, so dozens of stars pile up at the tail's first
    position.
  - Set `em.beginTime = parent.convertTime(CACurrentMediaTime(), from: nil)`.
- **P3. A zero-length dash exactly at the end of a path is dropped about half the time.**
  - The head-cell dot was missing on 27 of 53 L32 arrows.
  - Extend the dots path 1 pt past the head.
- **P4. Frames must hug their paths.**
  - Board-sized frames would keep all 300 layers "on screen" at 3x.
  - The rest path is body-only; the long ray path exists only while the arrow moves.
- **P5. `UITapGestureRecognizer` gives up on a long hold.** The original fires on release even after 5 s (see
  `ReleaseTapRecognizer`).
- **P6. The build environment is strict about two things:**
  - Swift 6-era actor isolation: a nested `func` inside a `@MainActor` method needs `@MainActor` itself.
  - Exclusivity: `getRed(&a[0], green: &a[1], …)` on one array is an error; use separate variables.
- **P7. Type-checker timeouts.**
  - A one-expression heart-curve closure hit "unable to type-check in reasonable time" after 180 s under swap.
  - Break long numeric expressions into typed `let`s.
- **P8. Stale UI-test hooks.**
  - A test hook must refresh continuously; the spike refreshes on a 0.25 s display-link tick under `-pc.uitest`.
  - The first XCUITest run tapped a stale point after the zoom bounce settled.
- **P9. Dense boards bump at gap 0.** On L32 every blocked arrow starts at gap 0, so a bump at the real speed is
  very short. Take the bump duration from the analyst, not from geometry.

## Recommended architecture for the real game

### Packages/PathCore (pure Swift: Foundation + CoreGraphics only; `swift test` on macOS, no simulator)

- **Model:**
  - `Cell`, `Dir`, `ArrowSpec`;
  - `Obstacle`: tape bundle, locked crate + key arrow, pipe with a numbered cap, linked arrows, corners; each added
    as research pins its rule;
  - `LevelSpec`, `LevelLibrary`.
- **Rules:**
  - `BoardState`: flat occupancy, alive bits, units (bundles), obstacle hooks.
  - `tap(_:) -> TapOutcome`, with cases `exits`, `exitsGroup`, `blocked(gap:)`, `ignored` and later obstacle
    outcomes.
- **Session state machine with one event stream:**
  - timer: 3:00 on L32; it seems to start at the first tap (research, to verify);
  - hearts: 3 per level; a bump costs 1;
  - win: board empty;
  - fail: time out or no hearts;
  - pause freezes the timer;
  - Add Time +30 s for 900 coins; Play On for 900 coins;
  - boosters: the bulb (hint = a free unit from the solver) and the crystal/magnet (rule UNKNOWN).
- **Geometry:**
  - `Metrics` ratios (table above);
  - `BoardLayout`: the fit rule and the play rect;
  - `ArrowGeometry`: corners, `strokeStart`/`strokeEnd`, `headPosition`, `point(along:)`, `runs`, `exitTravel`,
    `contactTravel`;
  - `TravelProfile`: v, acceleration.
  - Unit-test all of it against `motion.md` once the analyst writes it.
- **Solver:** the units-aware greedy solver. It covers:
  - solvability;
  - the hint;
  - dependency depth (= greedy rounds), the difficulty measure for the generator's curve;
  - a `HeadlessDriver` bot for V1/V2.
- **Generator:** the reverse construction above, plus:
  - silhouette masks (heart, crescent, square);
  - a length and turn distribution fitted to the recorded levels;
  - obstacle injection;
  - a difficulty target per level;
  - seeded `SplitMix64`/xoshiro streams.
- **Validator:** structure (orthogonal steps, no shared cells, head direction, the ray misses its own body),
  solvable, and for recorded levels a match with the extraction.
- **Level JSON:** keep the phone player's schema. The spike's decoder already reads both schemas:
  ```json
  {"level": 32, "cols": 20, "rows": 20, "timer_s": 180, "hearts": 3, "tag": null,
   "mask": null,                                   // or ["..##..", ...] rows of '#' = playable
   "arrows": [{"id": 0, "cells": [[0,0],[1,0],[2,0],[3,0]], "dir": "right"}],   // tail -> head
   "obstacles": [{"kind": "tape_pink", "cells": [[2,0],[2,1],[2,2],[2,3]]}],
   "source": "recorded", "shot": "research/shots/003-L32-start.png"}          // research-only extras ignored
  ```

### App/Board (UIKit + Core Animation; the only non-SwiftUI part)

- **`BoardView`**:
  - a `UIScrollView` with zoom limits from tunables (0.75 / 3 until measured) and `bouncesZoom`;
  - a content view that is board space at fit;
  - one `stage` layer holding `[dots, arrows, obstacles, moving, fx]`;
  - a `ReleaseTapRecognizer` that requires the scroll view's pan and pinch to fail;
  - the grid-maths hit test;
  - a tap ripple.
- **`ArrowNode`** (rest: 2 layers) and **`Mover`** (exit, bump, group exit with tape carry). Movers are built at
  tap time and removed by animation delegates, never by timers.
- **Painters:** `solid` (default #10A2EF), `gradientRuns` (rainbow skin) and star `Emitter`.
  - Pre-build the gradient runs at level load if the phone's tap cost says so.
- **`BoardController`** (the pattern from apps/arrows): a command queue between the SwiftUI shell and the board.
  - Its events: `tapped`, `contact`, `exitFinished`, `boardCleared`.
- **Render server:** every board motion runs there. That covers slide, bump, colour, dots reveal, stars, tape
  carry and ripple. The main thread only resolves taps (≤ ~2 ms solid, ~5 ms gradient per 5 arrows on the
  simulator) and answers the completion callbacks.

### SwiftUI shell

- It hosts `BoardView` in a `UIViewRepresentable`, edge to edge, with the HUD and booster bar overlaid.
- The board's play rect comes from the HUD bottom and booster top: 122 / 755 pt on 393x852.
- Beyond that:
  - HUD sync ≤ 10 Hz;
  - popups: Out of Time, Continue, Level Failed, Perfect;
  - Observation;
  - EN + TR strings from the TSV.

## Open questions for the motion analyst (the spike's placeholders are all tunable by launch argument)

- **Exit:**
  - v (spike: 900 screen pt/s), and whether it is screen or board space;
  - acceleration (spike: 0);
  - whether the exit ends when the arrow is off the screen or off the board;
  - whether it passes under or over the HUD.
- **Bump:**
  - distance: to contact or less;
  - out/back durations (spike: out at v, back 0.22 s ease-out);
  - tint colour and whether it persists (spike: #FF3B3B, fades over 0.35 s);
  - blocker jolt, haptic, sound.
- **Dots:** per cell as the tail passes (spike) or all at once, and any fade.
- **Trail:**
  - when the rainbow is used instead of solid blue;
  - stars: count, size, lifetime, colours; whether the bands move with the body (spike: fixed on the path, which
    the star colours in store shot 1 support).
- **Tape:** exact motion of the tape when its bundle leaves, and the some-rays-clear rule.
- **Zoom and details:** the maximum zoom; any reset on double-tap (research: no); the tap ripple's size and time;
  the vertical head nudge.

## How to reproduce (after booting "Maze A" only; about 1 min per build)

```sh
cd apps/mazeout/build/spike && ~/.local/bin/xcodegen generate
xcodebuild -project PathSpike.xcodeproj -scheme PathSpike -configuration Release \
  -destination id=177520B6-4889-46C2-BDD9-155813D2B175 -derivedDataPath $PWD/dd -jobs 4 -quiet build
xcrun simctl install 177520B6-4889-46C2-BDD9-155813D2B175 dd/Build/Products/Release-iphonesimulator/PathSpike.app
xcrun simctl launch --terminate-running-process 177520B6-4889-46C2-BDD9-155813D2B175 com.manycode.mazeout.spike \
  -pc.level synth -pc.scenario exit5 -pc.trail gradient -pc.zoom 3
```

- **Scenarios:** `idle`, `exit5`, `trail`, `bump`, `crisp`, `zoomramp`, `hittest`, `autoplay`.
- **Launch arguments:**
  - `-pc.freeze S`, `-pc.slowmo K`, `-pc.shotAfter S`;
  - `-pc.speed`, `-pc.accel`, `-pc.bumpBack`, `-pc.bumpPersist`;
  - `-pc.period`, `-pc.trailMoves`, `-pc.dashSteps`, `-pc.stars`;
  - `-pc.waves`, `-pc.perWave`, `-pc.waveGap`, `-pc.measure`;
  - `-pc.level synth | L032rec`, `-pc.seed`, `-pc.mean`;
  - `-pc.freezeOnGroup S` (autoplay), `-pc.minGap N` (bump), `-pc.uitest YES`.
- **Output:** results go to the app's own `tmp/` (`spike-<scenario>.json`, `ready-<tag>.txt`).
- **Harness:** `build/spike/tools/run.sh <label> <readytag> <timeout> [args]` launches the app, waits for the ready
  file, shoots with `simctl io` into `design/spike-shots/`, and copies the JSON.
- **macOS core check (no simulator):**
  `swiftc -O -o /tmp/coretest build/spike/tools/coretest_main.swift build/spike/App/Core/*.swift`
- **UI test:** `xcodebuild test` on the same scheme (`UITests/PinchTapTests.swift`), which passed.
