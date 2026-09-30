import UIKit
import SwiftUI
import PathCore

// SHELL S2 (SPEC-ui §2.3.3 freeze booster UI, VERIFIED meta-065; SPEC-motion-audio §3.10.2-§3.10.3, anchor B = the hourglass
// booster's release; ui.json `freeze.*`). The HUD half of the Time Freeze, Core Animation on the FX host (screen space, over the
// board and the HUD, under the popups), played by GAME's BoosterDirector as `fx.play(.custom(id: "freeze", params:
// ["seconds": 10]))` at B. `fx.finished(handle)` returns when the freeze ends (B + 1.60 + seconds); `fx.stop(handle)` ends it at
// once (level left). Beats:
//   B          the icy hourglass (`boosterFreeze`, ≈ 90 × 100 pt) pops at (192, 612): 0.3 → 1.0, 0.12 s, easeOutBack(1.70)
//   B + 0.10   it rises to y 405 (0.83 s, easeOutCubic) rocking ±4° (period 0.6 s)
//   B + 0.98   it flies on an arc (194, 400) → the stopwatch (107, 94) via (175, 200), 1.0 → 0.35, 0.40 s easeInQuad, then hides
//   B + 1.38   the stopwatch ices over (a snow cap + icicles drawn in code: `iconStopwatchIced` is a UI-ART request), 0.25 s
//   B + 1.60   the frost vignette (edges #6BD4F8 → white: ≈ 30 pt at the sides, ≈ 88 pt top and bottom) fades in 0.20 s; the
//              countdown tray 93 · 118 · 92 × 25 slides out from under the timer pill (0.20 s, easeOutBack): the digit "10" … "1"
//              (ceil of the remaining seconds) and the blue bar 100 % → 0 % over `seconds`
//   B + 1.60 + seconds   frost + icing fade (0.30 s), the tray slides back up (0.15 s): the freeze has ended (the timer resumes)
// The level timer freezes at B (the session's `freezeStarted`); this effect only draws. Silent after the button's click.
// FIX-A2 (G2's request "freeze HUD effect pausable"): the effect stands still while the session's clock is held (Pause, popups,
// offers, a tutorial with holdTimer, the background) — `hold(_:_:)` stops the root layer's own time (speed 0 at its current
// local time; every part's animations live in that time) and resumes it where it stood; the frost (FreezeHUDState) shifts its
// schedule by the held time. `-pc.uitest` exposes the tray as `hud.freeze.tray` (value computed when queried, 0 per frame).

@MainActor enum HUDFreezeFX {
    struct Spec {
        var spawn = CGPoint(x: 192, y: 612), spawnDur = 0.12, riseFrom = 0.10, riseDur = 0.83, riseTo = 405.0, rockDeg = 4.0
        var flyFrom = 0.98, flyDur = 0.40, flyControl = CGPoint(x: 175, y: 200), target = CGPoint(x: 107, y: 94), flyEndScale = 0.35
        var iceFrom = 1.38, iceDur = 0.25, frostFrom = 1.60, frostDur = 0.20, frostColor = UIColor(rgb: Skin.hudHudFreezeSpecFrostColor)
        var frostSides = 30.0, frostTopBottom = 88.0, tray = CGRect(93, 118, 92, 25), trayIn = 0.20, trayOut = 0.15, endFade = 0.30

        init(_ f: TuningFile) {
            func pt(_ k: String, _ d: CGPoint) -> CGPoint { let v = f.doubles(k, []); return v.count == 2 ? CGPoint(x: v[0], y: v[1]) : d }
            spawn = pt("freeze.spawn", spawn); spawnDur = f.double("freeze.spawnDur", spawnDur)
            riseFrom = f.double("freeze.riseFrom", riseFrom); riseDur = f.double("freeze.riseDur", riseDur)
            riseTo = f.double("freeze.riseTo", riseTo); rockDeg = f.double("freeze.rockDeg", rockDeg)
            flyFrom = f.double("freeze.flyFrom", flyFrom); flyDur = f.double("freeze.flyDur", flyDur)
            flyControl = pt("freeze.flyControl", flyControl); target = pt("freeze.target", target)
            flyEndScale = f.double("freeze.flyEndScale", flyEndScale); iceFrom = f.double("freeze.iceFrom", iceFrom)
            iceDur = f.double("freeze.iceDur", iceDur); frostFrom = f.double("freeze.frostFrom", frostFrom)
            frostDur = f.double("freeze.frostDur", frostDur)
            if let c = UIColor(hexString: f.string("freeze.frostColor", Skin.hudHudFreezeFreezeFrostColorHex)) { frostColor = c }
            frostSides = f.double("freeze.frostDepthSidesPt", frostSides); frostTopBottom = f.double("freeze.frostDepthTopBottomPt", frostTopBottom)
            let t = f.doubles("freeze.tray", []); if t.count == 4 { tray = CGRect(t[0], t[1], t[2], t[3]) }
            trayIn = f.double("freeze.trayIn", trayIn); trayOut = f.double("freeze.trayOut", trayOut); endFade = f.double("freeze.endFade", endFade)
        }
    }

    /// The parts a countdown needs after the build (SPEC.md ruling 30: used before the first tap, the tray HOLDS "10" with a
    /// full bar until the first board tap starts the countdown).
    struct Parts {
        let root: CALayer
        let ice: CALayer
        let tray: CALayer
        let fill: CALayer
        let digit: CALayer
        let host: CALayer
        let trayHeight: CGFloat
        let t0: CFTimeInterval
        let seconds: Double
        let spec: Spec
    }

    /// Builds the layers under `host` (the FX host layer) with animations in the host's local time from `t0` (= B).
    /// `hold` (ruling 30): the flight, the icing and the tray (at B + 1.60) as usual, but the countdown — digit, bar, the tray's
    /// and the frost's end — waits for `startCountdown`.
    static func build(host: CALayer, t0: CFTimeInterval, seconds: Double, ui: UITuning, safeTop: CGFloat) -> CALayer {
        build(host: host, t0: t0, seconds: seconds, ui: ui, safeTop: safeTop, hold: false).root
    }

    static func build(host: CALayer, t0: CFTimeInterval, seconds: Double, ui: UITuning, safeTop: CGFloat, hold: Bool) -> Parts {
        let spec = Spec(ui.file)
        let b = host.bounds
        let s = min(1, b.width / 393)
        func screen(_ p: CGPoint, top: Bool) -> CGPoint {
            // top-anchored (the HUD) or centre-anchored (the lower half: the spawn and the rise), SPEC-ui §1.1
            let x = b.width / 2 + (p.x - 196.5) * s
            return CGPoint(x: x, y: top ? safeTop + (p.y - 59) * s : b.height / 2 + (p.y - 426) * s)
        }
        let root = CALayer()
        root.frame = b

        // the frost vignette is drawn by HUDView UNDER the HUD (VERIFIED meta-065: the HUD's parts stay crisp over it):
        // FreezeHUDState schedules it on the MotionClock (its end comes with the countdown)
        FreezeHUDState.shared.schedule(frostAt: spec.frostFrom, until: nil, fadeIn: spec.frostDur, fadeOut: spec.endFade)

        // the iced stopwatch (over the HUD's stopwatch 92.1 · 82.1 · 30.7 × 33)
        let watch = screen(CGPoint(x: 107.5, y: 98.6), top: true)
        let ice = iceLayer(size: CGSize(width: 34 * s, height: 36 * s))
        ice.position = watch
        ice.opacity = 0
        ice.add(keyframes("opacity", [0, 0, 1], [0, spec.iceFrom, spec.iceFrom + spec.iceDur], begin: t0, fns: [lin, outQuad]),
                forKey: "iceIn")
        root.addSublayer(ice)

        // the countdown tray under the timer pill
        let trayRect = CGRect(origin: screen(spec.tray.origin, top: true), size: CGSize(width: spec.tray.width * s, height: spec.tray.height * s))
        let clip = CALayer()
        clip.frame = CGRect(x: trayRect.minX - 2, y: trayRect.minY, width: trayRect.width + 4, height: trayRect.height + 4)
        clip.masksToBounds = true
        let (tray, fill, digit) = trayLayer(size: trayRect.size, seconds: seconds, ui: ui, scale: s)
        tray.frame = CGRect(x: 2, y: 0, width: trayRect.width, height: trayRect.height)
        let slide = keyframes("position.y", [-trayRect.height / 2, -trayRect.height / 2, trayRect.height / 2],
                              [0, spec.frostFrom, spec.frostFrom + spec.trayIn], begin: t0,
                              fns: [lin, CAMediaTimingFunction(controlPoints: 0.333, 1.567, 0.667, 1)])
        tray.add(slide, forKey: "slideIn")
        clip.addSublayer(tray)
        root.addSublayer(clip)

        // the flying hourglass
        let glass = CALayer()
        if let img = ArtStore.image(.boosterFreeze)?.cgImage { glass.contents = img }
        let gs = CGSize(width: 106 * s, height: 106 * s)           // the 56 pt canvas whose ink is ≈ 90 × 100 at this size
        glass.bounds = CGRect(origin: .zero, size: gs)
        glass.opacity = 0
        let p0 = screen(spec.spawn, top: false), p1 = screen(CGPoint(x: spec.spawn.x, y: spec.riseTo), top: false)
        let tgt = screen(spec.target, top: true), ctl = screen(spec.flyControl, top: true)
        glass.position = p0
        let path = CGMutablePath()
        path.move(to: p1); path.addQuadCurve(to: tgt, control: ctl)
        let pop = keyframes("transform.scale", [0.3, 0.3, 1.0, 1.0, spec.flyEndScale],
                            [0, 0.0001, spec.spawnDur, spec.flyFrom, spec.flyFrom + spec.flyDur], begin: t0,
                            fns: [lin, CAMediaTimingFunction(controlPoints: 0.333, 1.567, 0.667, 1), lin, CAMediaTimingFunction(controlPoints: 0.333, 0, 0.667, 0.333)])
        glass.add(pop, forKey: "scale")
        let rise = CABasicAnimation(keyPath: "position")
        rise.fromValue = NSValue(cgPoint: p0); rise.toValue = NSValue(cgPoint: p1)
        rise.beginTime = t0 + spec.riseFrom; rise.duration = spec.riseDur
        rise.timingFunction = outCubic
        rise.fillMode = .both; rise.isRemovedOnCompletion = false
        glass.add(rise, forKey: "rise")
        let fly = CAKeyframeAnimation(keyPath: "position")
        fly.path = path
        fly.beginTime = t0 + spec.flyFrom; fly.duration = spec.flyDur
        fly.timingFunction = CAMediaTimingFunction(controlPoints: 0.333, 0, 0.667, 0.333)
        fly.fillMode = .forwards; fly.isRemovedOnCompletion = false
        glass.add(fly, forKey: "fly")
        let rock = CAKeyframeAnimation(keyPath: "transform.rotation.z")
        let r = spec.rockDeg * .pi / 180
        rock.values = [0, r, 0, -r, 0]
        rock.keyTimes = [0, 0.25, 0.5, 0.75, 1]
        rock.duration = 0.6
        rock.repeatCount = Float((spec.flyFrom - spec.riseFrom) / 0.6)
        rock.beginTime = t0 + spec.riseFrom
        glass.add(rock, forKey: "rock")
        glass.add(keyframes("opacity", [0, 1, 1, 0], [0, spec.spawnDur, spec.flyFrom + spec.flyDur - 0.02, spec.flyFrom + spec.flyDur],
                            begin: t0, fns: [lin, lin, lin]), forKey: "show")
        root.addSublayer(glass)
        let parts = Parts(root: root, ice: ice, tray: tray, fill: fill, digit: digit, host: host, trayHeight: trayRect.height, t0: t0,
                          seconds: seconds, spec: spec)
        if !hold { startCountdown(parts, at: t0 + spec.frostFrom) }
        return parts
    }

    /// The countdown from host time `c` (B + 1.60 normally; ruling 30: the first board tap, never before B + 1.60): the digit
    /// "10" … "1", the bar 100 % → 0 %, then at c + seconds the frost and icing fade and the tray slides back up.
    static func startCountdown(_ p: Parts, at c: CFTimeInterval) {
        let spec = p.spec, secs = p.seconds
        CATransaction.begin(); CATransaction.setDisableActions(true)
        if let shrink = p.fill.value(forKey: "freeze.shrink") as? CABasicAnimation {
            let a = shrink.copy() as! CABasicAnimation
            a.beginTime = c
            p.fill.add(a, forKey: "bar")
        }
        if let swap = p.digit.value(forKey: "freeze.swap") as? CAKeyframeAnimation {
            let a = swap.copy() as! CAKeyframeAnimation
            a.beginTime = c
            p.digit.add(a, forKey: "count")
        }
        let end = c + secs
        let h = p.trayHeight
        // the end tracks start AT the end with no backwards fill, so until then the entrance tracks' forward fill holds the
        // tray out and the icing on (a later-added animation on the same key wins while it is active)
        let out = keyframes("position.y", [h / 2, -h / 2], [0, spec.trayOut], begin: end,
                            fns: [CAMediaTimingFunction(controlPoints: 0.333, 0, 0.667, 0.333)])
        out.fillMode = .forwards
        p.tray.add(out, forKey: "slideOut")
        let melt = keyframes("opacity", [1, 0], [0, spec.endFade], begin: end, fns: [lin])
        melt.fillMode = .forwards
        p.ice.add(melt, forKey: "iceOut")
        CATransaction.commit()
        FreezeHUDState.shared.setEnd(inSeconds: end - localTime(p))
    }

    /// The parts' own time (FIX-A2): the root layer's local time, which stops while the freeze is held; before the root is
    /// in the tree, the host's (they are equal at the build).
    static func localTime(_ p: Parts) -> CFTimeInterval {
        let now = CACurrentMediaTime()
        return p.root.superlayer != nil ? p.root.convertTime(now, from: nil) : p.host.convertTime(now, from: nil)
    }

    /// FIX-A2: holds (`on`) or resumes the whole effect — flight, icing, tray, digit and bar — at the instant it stands at
    /// (QA1673: speed 0 with the current local time as the offset; the resume shifts `beginTime` by the held span). The frost
    /// is SwiftUI's (FreezeHUDState.hold).
    static func hold(_ p: Parts, _ on: Bool) {
        let root = p.root
        CATransaction.begin(); CATransaction.setDisableActions(true)
        if on, root.speed != 0 {
            let t = root.convertTime(CACurrentMediaTime(), from: nil)
            root.speed = 0
            root.timeOffset = t
        } else if !on, root.speed == 0 {
            let paused = root.timeOffset
            root.speed = 1
            root.timeOffset = 0
            root.beginTime = 0
            root.beginTime = root.convertTime(CACurrentMediaTime(), from: nil) - paused
        }
        CATransaction.commit()
    }

    private static let lin = CAMediaTimingFunction(name: .linear)
    private static let outCubic = CAMediaTimingFunction(controlPoints: 0.333, 1, 0.667, 1)
    private static let outQuad = CAMediaTimingFunction(controlPoints: 0.333, 0.667, 0.667, 1)

    /// A keyframe animation over absolute offsets from `begin` (values held before the first and after the last key).
    static func keyframes(_ path: String, _ values: [Double], _ times: [Double], begin: CFTimeInterval,
                          fns: [CAMediaTimingFunction]) -> CAKeyframeAnimation {
        let a = CAKeyframeAnimation(keyPath: path)
        let total = max(times.last ?? 1, 0.001)
        a.values = values
        a.keyTimes = times.map { NSNumber(value: $0 / total) }
        a.timingFunctions = fns
        a.beginTime = begin
        a.duration = total
        a.fillMode = .both
        a.isRemovedOnCompletion = false
        return a
    }

    /// The tray: the HUD panel's material (#BDDCFF, a lower lip #517CC9 → #83A9EB), the digit and the blue bar (VERIFIED meta-065).
    /// The bar's and the digit's countdown tracks are built here and parked on their layers (`freeze.shrink`, `freeze.swap`);
    /// `startCountdown` adds them with their begin time. Until then the tray shows "10" and a full bar.
    private static func trayLayer(size: CGSize, seconds: Double, ui: UITuning, scale s: CGFloat) -> (CALayer, CALayer, CALayer) {
        let tray = CALayer()
        tray.bounds = CGRect(origin: .zero, size: size)
        let face = CAGradientLayer()
        face.frame = tray.bounds
        face.colors = [UIColor(rgb: Skin.hudHudFreezeHudFreezeFXTrayLayerFaceColors0).cgColor, UIColor(rgb: Skin.hudHudFreezeHudFreezeFXTrayLayerFaceColors1).cgColor, UIColor(rgb: Skin.hudHudFreezeHudFreezeFXTrayLayerFaceColors2).cgColor, UIColor(rgb: Skin.hudHudFreezeHudFreezeFXTrayLayerFaceColors3).cgColor]
        face.locations = [0, 0.7, 0.85, 1]
        face.cornerRadius = 8 * s
        face.maskedCorners = [.layerMinXMaxYCorner, .layerMaxXMaxYCorner]
        tray.addSublayer(face)
        // the bar: track 119.4 · 125.4 · 59.7 × 10 (rr 4.7, #6C94DC), fill 57.7 wide × 7, #2AA1FC → #0D48D3
        let track = CALayer()
        track.frame = CGRect(x: 26.4 * s, y: 7.0 * s, width: 59.7 * s, height: 10 * s)
        track.cornerRadius = 4.7 * s
        track.backgroundColor = UIColor(rgb: Skin.hudHudFreezeHudFreezeFXTrayLayerTrackBackgroundColor).cgColor
        tray.addSublayer(track)
        let fill = CAGradientLayer()
        fill.colors = [UIColor(rgb: Skin.hudHudFreezeHudFreezeFXTrayLayerFillColors0).cgColor, UIColor(rgb: Skin.hudHudFreezeHudFreezeFXTrayLayerFillColors1).cgColor, UIColor(rgb: Skin.hudHudFreezeHudFreezeFXTrayLayerFillColors2).cgColor]
        fill.locations = [0, 0.5, 1]
        fill.anchorPoint = CGPoint(x: 0, y: 0.5)
        fill.bounds = CGRect(x: 0, y: 0, width: 57.7 * s, height: 7 * s)
        fill.position = CGPoint(x: 27.4 * s, y: 12.0 * s)
        fill.cornerRadius = 3.5 * s
        let shrink = CABasicAnimation(keyPath: "bounds.size.width")
        shrink.fromValue = 57.7 * s; shrink.toValue = 0
        shrink.duration = seconds
        shrink.fillMode = .both; shrink.isRemovedOnCompletion = false
        fill.setValue(shrink, forKey: "freeze.shrink")
        tray.addSublayer(fill)
        // the digit: ceil(remaining) swapped each second (a discrete keyframe of pre-rendered GameText images)
        let digit = CALayer()
        digit.bounds = CGRect(x: 0, y: 0, width: 24 * s, height: 20 * s)
        digit.position = CGPoint(x: 14.6 * s, y: 11.8 * s)
        digit.contentsGravity = .center
        digit.contentsScale = UIScreen.main.scale
        let n = max(1, Int(seconds.rounded(.up)))
        let style = ui.tokens.text("hudFreeze.digit", .s2(15, -0.5, [Skin.hudHudFreezeHudFreezeDigit0], outline: Skin.hudHudFreezeHudFreezeDigitOutline, 1.0, drop: 0.8)).sized(15 * s)
        let images: [CGImage] = (1...n).reversed().compactMap { digitImage("\($0)", style: style) }
        if images.count == n {
            digit.contents = images.first
            let swap = CAKeyframeAnimation(keyPath: "contents")
            swap.values = images                                                  // discrete: n values, n + 1 key times
            swap.keyTimes = (0..<n).map { NSNumber(value: Double($0) / Double(n)) } + [1]
            swap.calculationMode = .discrete
            swap.duration = seconds
            swap.fillMode = .both; swap.isRemovedOnCompletion = false
            digit.setValue(swap, forKey: "freeze.swap")
        }
        tray.addSublayer(digit)
        return (tray, fill, digit)
    }

    private static func digitImage(_ text: String, style: GameTextStyle) -> CGImage? {
        let l = GameTextLayout.make(text, postScriptName: style.postScriptName, size: style.size, tracking: style.tracking)
        let pad = style.outlineWidth + 2
        let size = CGSize(width: l.advance + 2 * pad, height: l.ascent + l.descent + 2 * pad + style.drop)
        return GameTextRaster.image(l, style: style, size: size, origin: CGPoint(x: pad, y: pad + l.ascent), scale: UIScreen.main.scale)
    }

    /// The icing over the stopwatch: a snow cap on its crown and a few icicles on the right (drawn in code).
    private static func iceLayer(size: CGSize) -> CALayer {
        let l = CAShapeLayer()
        l.bounds = CGRect(origin: .zero, size: size)
        let w = size.width, h = size.height
        let p = CGMutablePath()
        // the cap: a soft blob over the crown and the top of the ring
        p.addEllipse(in: CGRect(x: w * 0.18, y: h * 0.02, width: w * 0.64, height: h * 0.28))
        p.addEllipse(in: CGRect(x: w * 0.06, y: h * 0.16, width: w * 0.5, height: h * 0.2))
        p.addEllipse(in: CGRect(x: w * 0.44, y: h * 0.14, width: w * 0.5, height: h * 0.22))
        // icicles on the right side
        for (x, len) in [(0.80, 0.30), (0.88, 0.22), (0.72, 0.18)] as [(CGFloat, CGFloat)] {
            p.move(to: CGPoint(x: w * (x - 0.05), y: h * 0.3))
            p.addLine(to: CGPoint(x: w * (x + 0.05), y: h * 0.3))
            p.addLine(to: CGPoint(x: w * x, y: h * (0.3 + len)))
            p.closeSubpath()
        }
        l.path = p
        l.fillColor = UIColor(rgb: Skin.hudHudFreezeHudFreezeFXIceLayerFillColor).cgColor
        l.strokeColor = UIColor(rgb: Skin.hudHudFreezeHudFreezeFXIceLayerStrokeColor).cgColor
        l.lineWidth = 0.8
        l.shadowColor = UIColor(rgb: Skin.hudHudFreezeHudFreezeFXIceLayerShadowColor).cgColor
        l.shadowOpacity = 0.5
        l.shadowRadius = 0.6
        l.shadowOffset = CGSize(width: 0, height: 0.8)
        return l
    }
}

// MARK: - the frost vignette under the HUD

/// When the frost shows (MotionClock game time); HUDView's `FreezeFrost` observes it.
@MainActor @Observable final class FreezeHUDState {
    static let shared = FreezeHUDState()
    private(set) var on = false
    private(set) var fadeIn = 0.2
    private(set) var fadeOut = 0.3
    @ObservationIgnored private var token = 0

    /// Game time at which the frost fades out (nil: held until `setEnd`, ruling 30).
    @ObservationIgnored private var endAt: Double?
    /// FIX-A2: the freeze is held since this game time (nil: running); `heldTotal` = the finished holds since B.
    @ObservationIgnored private var heldSince: Double?
    @ObservationIgnored private var heldTotal = 0.0

    /// From now (B): the frost fades in at B + `frostAt` and out at B + `until` (nil: when `setEnd` says); both move later by
    /// every span the freeze is held (`hold`).
    func schedule(frostAt: Double, until: Double?, fadeIn: Double, fadeOut: Double) {
        token += 1
        let me = token
        self.fadeIn = fadeIn; self.fadeOut = fadeOut
        heldSince = nil; heldTotal = 0
        guard let clock = S2Hooks.app?.clock else { return }
        let b = clock.gameTime()
        endAt = until.map { b + $0 }
        Task { @MainActor in
            while me == self.token, self.running(since: b, clock) < frostAt { try? await Task.sleep(nanoseconds: 8_000_000) }
            guard me == self.token else { return }
            withAnimation(.timingCurve(0.333, 1, 0.667, 1, duration: fadeIn)) { self.on = true }
            while me == self.token, self.heldSince != nil || (self.endAt.map({ clock.gameTime() < $0 }) ?? true) {
                try? await Task.sleep(nanoseconds: 16_000_000)
            }
            guard me == self.token else { return }
            withAnimation(.linear(duration: fadeOut)) { self.on = false }
        }
    }

    /// Game seconds since `b` that the freeze was not held.
    private func running(since b: Double, _ clock: MotionClock) -> Double {
        let now = clock.gameTime()
        return now - b - heldTotal - (heldSince.map { now - $0 } ?? 0)
    }

    /// The running freeze's frost fades out `s` seconds of running time from now (its countdown started).
    func setEnd(inSeconds s: Double) {
        guard let clock = S2Hooks.app?.clock else { return }
        endAt = (heldSince ?? clock.gameTime()) + max(0, s)
    }

    /// FIX-A2: the session's clock is held (`on`) or runs again: the frost's fade-in and fade-out move later by the held span.
    func hold(_ on: Bool) {
        guard let clock = S2Hooks.app?.clock else { return }
        let now = clock.gameTime()
        if on {
            if heldSince == nil { heldSince = now }
        } else if let since = heldSince {
            heldSince = nil
            heldTotal += now - since
            endAt = endAt.map { $0 + (now - since) }
        }
    }

    func cancel() { token += 1; on = false; heldSince = nil; heldTotal = 0 }
}

/// The frost: 4 edge gradients #6BD4F8 → white-transparent, ≈ 30 pt at the sides, ≈ 88 pt at the top and bottom (MA §3.10.3).
struct FreezeFrost: View {
    @Environment(AppModel.self) private var app
    @Environment(\.shellMetrics) private var m

    var body: some View {
        let st = FreezeHUDState.shared
        let f = app.tuning.ui.file
        let c = Color(hexString: f.string("freeze.frostColor", Skin.hudHudFreezeFreezeFrostColorHex)) ?? Color(hex: Skin.hudHudFreezeFreezeFrostC)
        let sides = CGFloat(f.double("freeze.frostDepthSidesPt", 30)) * m.s, tb = CGFloat(f.double("freeze.frostDepthTopBottomPt", 88)) * m.s
        let g = { (a: UnitPoint, b: UnitPoint) in
            LinearGradient(stops: [.init(color: c, location: 0), .init(color: c.opacity(0.55), location: 0.35), .init(color: .white.opacity(0), location: 1)],
                           startPoint: a, endPoint: b)
        }
        ZStack(alignment: .topLeading) {
            ZStack(alignment: .topLeading) {
                g(.top, .bottom).frame(width: m.size.width, height: tb)
                g(.bottom, .top).frame(width: m.size.width, height: tb).offset(y: m.size.height - tb)
                g(.leading, .trailing).frame(width: sides, height: m.size.height)
                g(.trailing, .leading).frame(width: sides, height: m.size.height).offset(x: m.size.width - sides)
            }
            .frame(width: m.size.width, height: m.size.height, alignment: .topLeading)
            .opacity(st.on ? 1 : 0)
            .accessibilityHidden(true)
            if app.args.exposesProbe { FreezeTrayProbe().frame(width: 2, height: 2) }   // FIX-A2: UI tests read the tray
        }
        .allowsHitTesting(false)
    }
}

/// FIX-A2 (`-pc.uitest` / probe runs only): the countdown tray as UI tests see it — `hud.freeze.tray`, whose value is
/// computed from the layers when XCUITest asks (`S2FX.freezeTrayProbe`), so it costs nothing per frame.
private struct FreezeTrayProbe: UIViewRepresentable {
    func makeUIView(context: Context) -> FreezeTrayProbeView { FreezeTrayProbeView() }
    func updateUIView(_ uiView: FreezeTrayProbeView, context: Context) {}
}

final class FreezeTrayProbeView: UIView {
    override init(frame: CGRect) {
        super.init(frame: frame)
        isUserInteractionEnabled = false
        backgroundColor = .clear
        isAccessibilityElement = true
        accessibilityIdentifier = "hud.freeze.tray"
        accessibilityLabel = "hud.freeze.tray"
        accessibilityTraits = .staticText
    }

    @available(*, unavailable) required init?(coder: NSCoder) { fatalError() }

    override var accessibilityValue: String? {
        get { S2FX.freezeTrayProbe() }
        set {}
    }
}
