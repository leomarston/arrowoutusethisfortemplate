import SwiftUI
import UIKit
import PathCore

// SHELL S3 (SPEC-architecture §6.4 item 7; SPEC-motion-audio §8.3 segments A/B/C + §8.5, anchor H = home's arrival; SPEC-ui
// §2.2.7; CONSISTENCY W-16..W-21). The home-return queue after a win, played once per home arrival that has something to show:
//   A  Claw token  (the win added m Claw points: `EventOutcome.clawPoints`) — the home dims to 0.50, the purple hex token pops at
//      the capsule machine with "+1", the multiplier badge (xm) merges into it (a white burst), the label becomes "+m", the token
//      flies to the Claw bar's hex, the bar counts up in n = min(7, m) steps of 0.057 s (♪ clawToken / clawMerge / clawTick /
//      clawComplete)
//   B  Streak strip (the multiplier moved: `EventOutcome.multiplier`) — the chip tray slides out under the Claw bar with the
//      previous chip lit, a green flag "+m" flies to the Streak badge, the lit chip moves to the new multiplier (♪ streakPop ×3),
//      the badge label swaps under a flash, the tray retracts
//   C  coins (every win; the FTUE's first home pays the banked 80 + 20 + 20 = 120): "+N" + the coin pile, 5 coins fly to the
//      top-bar coin icon, each landing adds N/5 to the pill with a sparkle burst and ◉ coinLand; ♪ coinCollect 0.35 s before C0
// C0 = H + 0.35 alone, A-end + 0.40 after A only, B0 + 1.25 after B. Every start/duration is `ui.json homeReturn.*` (MA §13.2).
// Motion = Core Animation layers on the FX host built ONCE at H with their begin times (render server); the main thread runs
// only the scheduled beats (cues, haptics, the pill / bar numbers: ≤ 15 small writes per sequence) and logs each one:
//   [PC][payout] <beat> planned H+<s> at H+<s>
// The coins are already banked in `PlayerState.coins` (kill-safe, GP §9.1); `CoinPillDisplay` hides the part still in flight.

/// What the home coin pills show: the banked coins minus what has not landed yet (`pendingCoinFly` before the sequence takes
/// it, then the coins still flying).
@MainActor @Observable final class CoinPillDisplay {
    static let shared = CoinPillDisplay()
    var flying = 0
    func shown(_ s: PlayerState) -> Int { max(0, s.coins - max(0, s.pendingCoinFly) - flying) }
}

struct HomeReturnTiming {
    var clawDimIn = (0.03, 0.13), clawDim = 0.50, tokenAt = 0.03, tokenDur = 0.10, flashAt = 0.23, badgeAt = 0.23
    var badgeSlide = (0.53, 0.15), burstAt = 0.68, labelAt = 0.88, dimOut = (1.33, 0.20), flyAt = 1.43, flyDur = 0.30
    var iconFlashAt = 1.73, countAt = 1.74, tickStep = 0.057, maxTicks = 7, x1Shift = -0.73
    var trayIn = (0.0, 0.22), flagAt = 0.02, flagFly = (0.57, 0.17), chipAt = 0.72, chipDur = 0.10
    var pops = [0.77, 0.92, 1.14], badgeFlashAt = 1.20, trayOut = (1.99, 0.18), coinsAfterStreak = 1.25
    var aloneStart = 0.35, afterClawOnly = 0.40
    var coins = CoinFlySpec()

    init() {}

    init(_ t: Tokens) {
        let f = t.file
        func d(_ k: String, _ v: Double) -> Double { f.double("homeReturn." + k, v) }
        func pair(_ k: String, _ v: (Double, Double)) -> (Double, Double) {
            let a = f.doubles("homeReturn." + k, [])
            return a.count == 2 ? (a[0], a[1]) : v
        }
        clawDimIn = pair("claw.dimIn", clawDimIn); clawDim = d("claw.dim", clawDim); tokenAt = d("claw.tokenAt", tokenAt)
        tokenDur = d("claw.tokenDur", tokenDur); flashAt = d("claw.flashAt", flashAt); badgeAt = d("claw.badgeAt", badgeAt)
        badgeSlide = pair("claw.badgeSlide", badgeSlide); burstAt = d("claw.burstAt", burstAt); labelAt = d("claw.labelAt", labelAt)
        dimOut = pair("claw.dimOut", dimOut); flyAt = d("claw.flyAt", flyAt); flyDur = d("claw.flyDur", flyDur)
        iconFlashAt = d("claw.iconFlashAt", iconFlashAt); countAt = d("claw.countAt", countAt); tickStep = d("claw.tickStep", tickStep)
        maxTicks = Int(d("claw.maxTicks", Double(maxTicks))); x1Shift = d("claw.x1Shift", x1Shift)
        trayIn = pair("streak.trayIn", trayIn); flagAt = d("streak.flagAt", flagAt); flagFly = pair("streak.flagFly", flagFly)
        chipAt = d("streak.chipAt", chipAt); chipDur = d("streak.chipDur", chipDur)
        pops = f.doubles("homeReturn.streak.pops", pops); badgeFlashAt = d("streak.badgeFlashAt", badgeFlashAt)
        trayOut = pair("streak.trayOut", trayOut); coinsAfterStreak = d("streak.coinsAt", coinsAfterStreak)
        aloneStart = d("aloneStart", aloneStart); afterClawOnly = d("afterClawOnly", afterClawOnly)
        coins = CoinFlySpec(t)
    }
}

/// What one home arrival plays (derived from the entry's WinSummary outcomes and the banked coins).
struct PayoutPlan: Equatable {
    struct Claw: Equatable { var added: Int; var total: Int; var target: Int; var multiplier: Int }
    struct Streak: Equatable { var from: Int; var to: Int; var flags: Int }
    var claw: Claw?
    var streak: Streak?
    var coins: Int

    var isEmpty: Bool { claw == nil && streak == nil && coins <= 0 }

    /// The segment anchors from H (SPEC-motion-audio §8.3): A ends 0.01 s after its last tick's +0.02 (H + 2.11 for n = 7); B0 =
    /// A's end, or H + 0.10 without A; C0 = B0 + 1.25 after B, A-end + 0.40 after A only, H + 0.35 alone. An x1 token (m = 1)
    /// skips the badge merge and shifts A7… by −0.73 s.
    struct Timeline: Equatable { var clawShift: Double; var aEnd: Double; var b0: Double?; var c0: Double }

    func timeline(_ tm: HomeReturnTiming) -> Timeline {
        let shift = claw != nil && (claw?.added ?? 0) <= 1 ? tm.x1Shift : 0
        var aEnd = 0.0
        if let c = claw {
            let n = max(1, min(tm.maxTicks, c.added))
            aEnd = tm.countAt + shift + Double(n - 1) * tm.tickStep + 0.02 + 0.01
        }
        let b0: Double? = streak == nil ? nil : (claw == nil ? 0.10 : aEnd)
        let c0 = b0.map { $0 + tm.coinsAfterStreak } ?? (claw == nil ? tm.aloneStart : aEnd + tm.afterClawOnly)
        return Timeline(clawShift: shift, aEnd: aEnd, b0: b0, c0: c0)
    }

    static func make(entry: HomeEntry, pending: Int, clawRunning: Bool, streakRunning: Bool) -> PayoutPlan {
        var summary: WinSummary?
        switch entry {
        case .afterWin(let w), .firstHome(let w): summary = w
        default: summary = nil
        }
        let outcomes = summary?.outcomes ?? []
        var claw: Claw?, streak: Streak?
        var from = 1, to = 1, flags = 0, movedMultiplier = false
        for o in outcomes {
            switch o {
            case .multiplier(let a, let b): from = a; to = b; movedMultiplier = true
            case .streakRaceScore(let n): flags = n
            default: break
            }
        }
        for o in outcomes {
            if case .clawPoints(let added, let total, let target) = o, added > 0, clawRunning {
                claw = Claw(added: added, total: total, target: target, multiplier: added)
            }
        }
        if streakRunning, movedMultiplier || flags > 0 { streak = Streak(from: from, to: to, flags: max(flags, from)) }
        return PayoutPlan(claw: claw, streak: streak, coins: pending > 0 ? pending : 0)
    }
}

@MainActor enum PayoutSequence {
    private(set) static var running = false
    private static var generation = 0
    /// The last sequence's measured beats (tests, the S3 lab / report): name → (planned, actual) offsets from H.
    private(set) static var lastBeats: [(String, Double, Double)] = []

    /// Called by home's first appearance (`HomeView`, tab home). H = the first frame home is fully visible: after a hard cut
    /// (a win's Continue) that is the next frame; out of Loading it is the end of the cross-fade. Then the banked coin fly is
    /// taken out of the save (the coins are already in `coins`; only the flight is pending) and the queue plays.
    static func arrive(app: AppModel, entry: HomeEntry, metrics m: ShellMetrics) {
        guard !running, !arriving else { return }
        let pending = app.store.state.pendingCoinFly                 // C3 banks every win's coins here until they fly (GP §9.1)
        let rules = ShellEconomy.rules(app)
        let status = Events.status(app.store.state, now: app.clock.wallClock(), rules: rules)
        let plan = PayoutPlan.make(entry: entry, pending: pending, clawRunning: status.claw != nil,
                                   streakRunning: status.streakRace != nil)
        guard !plan.isEmpty else { return }
        arriving = true
        let gen = generation
        Task { @MainActor in
            defer { arriving = false }
            await FrameWaiter.frames(1)
            var waited = 0
            while let r = app.router as? Router, r.isTransitioning || !r.firstScreenShown, waited < 120 {
                await FrameWaiter.frames(1)
                waited += 1
            }
            await FrameWaiter.frames(1)
            guard gen == generation, app.router.screen.isHome || app.router.screen == .lab(.shelllab) else { return }
            play(plan, app: app, metrics: m, status: status)
        }
    }

    private static var arriving = false

    /// Plays a plan now (home arrival, the S3 lab's replays).
    static func play(_ plan: PayoutPlan, app: AppModel, metrics m: ShellMetrics, status: Events.Status?) {
        running = true
        generation += 1
        let gen = generation
        let h0 = CACurrentMediaTime()                                  // H: the CA layers and the beats share it
        let t = app.tuning.ui.tokens
        let tm = HomeReturnTiming(t)
        let coinsDisplay = CoinPillDisplay.shared
        let clawDisplay = ClawBarDisplay.shared
        // take the banked fly now (saved at once: a kill after this point keeps the coins, only the flight is lost)
        if plan.coins > 0 {
            let taken = app.store.mutateAndSave { Economy.takeCoinFly(&$0) }
            coinsDisplay.flying = max(taken, plan.coins)
            HomeLive.shared.sync()                                     // FIX-A1: home reads HomeLive; same turn as `flying`
        }
        if let c = plan.claw {
            clawDisplay.points = max(0, c.total - c.added)
            clawDisplay.multiplier = plan.streak?.from ?? status?.multiplier
        } else if let s = plan.streak {
            clawDisplay.multiplier = s.from
        }

        // the timeline (seconds from H)
        var beats: [(String, Double, () -> Void)] = []
        let line = plan.timeline(tm)
        let clawShift = line.clawShift, aEnd = line.aEnd, b0 = line.b0, c0 = line.c0

        func cue(_ moment: String) -> () -> Void {
            { if let s = app.tuning.audio.cue(moment) { app.audio.play(s, gain: Float(app.tuning.audio.gain(s))) } }
        }

        // A2 (motion-catalog §5.1 row 20, contract amend 4 `rewardPop`): the home reward beats vibrate on their visual frame —
        // the Claw token pops (H + 0.03), the multiplier merge burst (H + 0.68, a notch stronger), the Streak flag lands (B0 + 0.74)
        func pop(_ intensity: Double? = nil) -> () -> Void {
            { if let intensity { app.haptics.play(.rewardPop, intensity: intensity) } else { app.haptics.play(.rewardPop) } }
        }

        // segment A (the Claw token)
        if let c = plan.claw {
            beats.append(("clawToken", tm.tokenAt + 0.025, cue("clawToken")))
            beats.append(("tokenPop", tm.tokenAt, pop()))
            if c.added > 1 {
                beats.append(("clawMerge", tm.burstAt - 0.045, cue("clawMerge")))
                beats.append(("mergePop", tm.burstAt, pop(t.number("homeReturn.claw.mergeHaptic", 0.50))))
            }
            let n = max(1, min(tm.maxTicks, c.added))
            let start = c.total - c.added
            beats.append(("iconFlash", tm.iconFlashAt + clawShift, { clawDisplay.iconFlash += 1 }))
            for k in 0..<n {
                let v = start + Int((Double(c.added) * Double(k + 1) / Double(n)).rounded())
                beats.append(("clawTick\(k)", tm.countAt + clawShift + Double(k) * tm.tickStep, {
                    clawDisplay.points = v
                    cue("clawTick")()
                }))
            }
            beats.append(("clawComplete", aEnd - 0.01, cue("clawComplete")))
        }
        // segment B (the streak strip)
        if let s = plan.streak, let b0 {
            for (i, p) in tm.pops.enumerated() { beats.append(("streakPop\(i)", b0 + p, cue("streakPop"))) }
            beats.append(("flagPop", b0 + tm.flagFly.0 + tm.flagFly.1, pop()))                   // A2: the flag lands
            beats.append(("badgeFlash", b0 + tm.badgeFlashAt, {
                clawDisplay.multiplier = s.to
                clawDisplay.badgeFlash += 1
            }))
        }
        // segment C (coins)
        if plan.coins > 0 {
            let spec = tm.coins
            beats.append(("coinCollect", c0 - 0.35, cue("homePayout")))
            let shares = spec.shares(plan.coins)
            let icon = m.point(spec.target, .top)
            for (k, share) in shares.enumerated() {
                beats.append(("coinLand\(k)", c0 + spec.landing(k), {
                    coinsDisplay.flying = max(0, coinsDisplay.flying - share)
                    app.haptics.play(.coinLand)
                    app.fx.play(.sparkles(at: icon))
                }))
            }
        }
        let end = max(c0 + (plan.coins > 0 ? tm.coins.labelFadeAt + tm.coins.labelFadeDur : 0),
                      b0.map { $0 + tm.trayOut.0 + tm.trayOut.1 } ?? 0, aEnd)
        beats.append(("end", end + 0.02, {}))

        // the CA layers, built now with begin times on the FX host's clock
        let fx = app.fx as? FXOverlay
        var layers: [CALayer] = []
        if let host = fx?.hostView.layer {
            let t0 = host.convertTime(h0, from: nil)
            CATransaction.begin(); CATransaction.setDisableActions(true)
            if let c = plan.claw { layers += HomeReturnLayers.claw(c, timing: tm, shift: clawShift, m: m, t0: t0) }
            if let s = plan.streak, let b0 { layers += HomeReturnLayers.streak(s, timing: tm, b0: b0, m: m, t0: t0) }
            if plan.coins > 0 {
                let spec = tm.coins
                layers += CoinFly.layers(amount: plan.coins, spec: spec, from: m.point(spec.origin, .top), to: m.point(spec.target, .top),
                                         control: m.point(spec.control, .top), labelCentre: m.point(spec.labelCentre, .top),
                                         scale: m.s, t0: t0 + c0)
            }
            for l in layers { host.addSublayer(l) }
            CATransaction.commit()
        }
        HomeReturnDimState.shared.schedule(plan.claw == nil ? nil : tm, shift: clawShift)

        Log.mark("payout", "H: claw \(plan.claw.map { "+\($0.added) \($0.total - $0.added)→\($0.total)/\($0.target)" } ?? "-") "
                 + "streak \(plan.streak.map { "x\($0.from)→x\($0.to) +\($0.flags)" } ?? "-") coins +\(plan.coins) "
                 + "C0 H+\(String(format: "%.3f", c0))")
        // the beats: fired by a display link in the frame that PRESENTS at or after each planned time (the render clock the CA
        // layers run on; a GCD timer drifts 50-70 ms late under its default leeway). A freeze or a new sequence drops the rest.
        lastBeats = []
        let freeze = app.clock.freezeAt.flatMap { $0.sequence == "coinFly" || $0.sequence == "payout" ? $0.t : nil }
        var queue = beats.sorted(by: { $0.1 < $1.1 })
        if let freeze { queue.append(("freeze", freeze, { _ = app.clock.sequenceTime("coinFly", freeze + 1) })) ; queue.sort { $0.1 < $1.1 } }
        let h = h0
        BeatClock.start(origin: h) { target in
            guard gen == generation else { return false }
            while let next = queue.first, next.1 <= target - h + 0.001 {
                queue.removeFirst()
                if app.clock.isFrozen && next.0 != "freeze" { continue }
                next.2()
                lastBeats.append((next.0, next.1, target - h))
                Log.mark("payout", "\(next.0) planned H+\(String(format: "%.3f", next.1)) shown H+\(String(format: "%.3f", target - h)) "
                         + "(handler H+\(String(format: "%.3f", CACurrentMediaTime() - h)))")
                if next.0 == "end" { finish(gen, layers: layers); return false }
            }
            return !queue.isEmpty
        }
    }

    private static func finish(_ gen: Int, layers: [CALayer]) {
        guard gen == generation else { return }
        CATransaction.begin(); CATransaction.setDisableActions(true)
        for l in layers { l.removeAllAnimations(); l.removeFromSuperlayer() }
        CATransaction.commit()
        CoinPillDisplay.shared.flying = 0
        ClawBarDisplay.shared.reset()
        running = false
        Log.mark("payout", "done")
    }

    /// Leaving home mid-sequence (Play, a tab): the numbers jump to their final values, the layers go.
    static func cancel() {
        if arriving { generation += 1 }
        guard running else { return }
        generation += 1
        running = false
        CoinPillDisplay.shared.flying = 0
        ClawBarDisplay.shared.reset()
        HomeReturnDimState.shared.clear()
        Log.mark("payout", "cancelled (home left)")
    }
}

// MARK: - the home dim (A1 / A7): above the scene, under the token and the top bar

@MainActor final class HomeReturnDimState {
    static let shared = HomeReturnDimState()
    weak var layer: CALayer?
    fileprivate var pending: (HomeReturnTiming, Double)?

    func schedule(_ tm: HomeReturnTiming?, shift: Double) {
        guard let tm else { return }
        guard let layer else { pending = (tm, shift); return }
        animate(layer, tm, shift: shift)
    }

    func attach(_ l: CALayer) {
        layer = l
        if let (tm, shift) = pending { pending = nil; animate(l, tm, shift: shift) }
    }

    func clear() { layer?.removeAllAnimations(); pending = nil }

    private func animate(_ l: CALayer, _ tm: HomeReturnTiming, shift: Double) {
        let a = CAKeyframeAnimation(keyPath: "opacity")
        let inStart = tm.clawDimIn.0, inEnd = inStart + tm.clawDimIn.1
        let outStart = tm.dimOut.0 + shift, outEnd = outStart + tm.dimOut.1
        a.values = [0, tm.clawDim, tm.clawDim, 0]
        a.keyTimes = [0, NSNumber(value: (inEnd - inStart) / (outEnd - inStart)), NSNumber(value: (outStart - inStart) / (outEnd - inStart)), 1]
        a.duration = outEnd - inStart
        a.beginTime = l.convertTime(CACurrentMediaTime(), from: nil) + inStart
        a.fillMode = .removed
        l.add(a, forKey: "homeReturnDim")
        Log.mark("payout", "dim 0 → \(tm.clawDim) → 0 over H+\(inStart)…H+\(String(format: "%.2f", outEnd)) (layer in window: \(l.superlayer != nil))")
    }
}

/// A black layer at opacity 0 whose opacity the queue animates on the render server.
struct HomeReturnDimView: UIViewRepresentable {
    var clock: MotionClock?

    func makeUIView(context: Context) -> UIView {
        let v = UIView()
        v.isUserInteractionEnabled = false
        v.backgroundColor = .black
        v.layer.opacity = 0
        HomeReturnDimState.shared.attach(v.layer)
        // capture freezes / slow motion hold the dim with the FX layers (the FX host's recipe)
        clock?.observeTimeScale { [weak v] k in
            guard let l = v?.layer else { return }
            let local = l.convertTime(CACurrentMediaTime(), from: nil)
            l.beginTime = CACurrentMediaTime()
            l.timeOffset = local
            l.speed = Float(k)
        }
        return v
    }
    func updateUIView(_ uiView: UIView, context: Context) {}
}

// MARK: - segment A / B layers

@MainActor enum HomeReturnLayers {
    /// A2-A8: the token (+ "+1" → "+m"), the multiplier badge merging in, the flash and burst, the flight to the bar's hex.
    static func claw(_ c: PayoutPlan.Claw, timing tm: HomeReturnTiming, shift: Double, m: ShellMetrics, t0: CFTimeInterval) -> [CALayer] {
        var out: [CALayer] = []
        let centre = m.point(CGPoint(x: 198, y: 450), .top)
        let hex = m.point(CGPoint(x: 49, y: 128), .top)
        let control = m.point(CGPoint(x: 180, y: 180), .top)
        let size = 64 * m.s
        let end = t0 + tm.flyAt + shift + tm.flyDur
        // the token: pop, hold, fly (position along the quad curve, scale 1 → 0.65)
        let token = CALayer()
        token.contents = ArtStore.image(.eventClawChallengeToken)?.cgImage
        token.contentsGravity = .resizeAspect
        token.bounds = CGRect(x: 0, y: 0, width: size * 40 / 37.3, height: size * 40 / 37.3)
        token.position = centre
        token.opacity = 0
        let life = CAKeyframeAnimation(keyPath: "opacity")
        life.values = [1, 1]; life.keyTimes = [0, 1]
        life.beginTime = t0 + tm.tokenAt; life.duration = end - (t0 + tm.tokenAt)
        token.add(life, forKey: "life")
        let pop = CABasicAnimation(keyPath: "transform.scale")
        pop.fromValue = 0.2; pop.toValue = 1.0
        pop.timingFunction = CAMediaTimingFunction(controlPoints: 0.34, 1.56, 0.64, 1)
        pop.beginTime = t0 + tm.tokenAt; pop.duration = tm.tokenDur; pop.fillMode = .backwards
        token.add(pop, forKey: "pop")
        let path = UIBezierPath(); path.move(to: centre); path.addQuadCurve(to: hex, controlPoint: control)
        let fly = CAKeyframeAnimation(keyPath: "position")
        fly.path = path.cgPath
        fly.timingFunction = CAMediaTimingFunction(controlPoints: 0.11, 0, 0.5, 0)
        fly.beginTime = t0 + tm.flyAt + shift; fly.duration = tm.flyDur; fly.fillMode = .forwards
        token.add(fly, forKey: "fly")
        let shrink = CABasicAnimation(keyPath: "transform.scale")
        shrink.fromValue = 1; shrink.toValue = 0.65
        shrink.beginTime = t0 + tm.flyAt + shift; shrink.duration = tm.flyDur; shrink.fillMode = .forwards
        shrink.timingFunction = fly.timingFunction
        token.add(shrink, forKey: "shrink")
        out.append(token)
        // the white flash on the token (A3)
        out.append(flash(at: centre, r: 30 * m.s, begin: t0 + tm.flashAt, dur: 0.12))
        // the multiplier badge beside it, sliding into the token (A4), then the burst (A5)
        if c.added > 1, let badge = flameImage(c.multiplier) {
            let b = CALayer()
            b.contents = badge.image; b.contentsScale = badge.scale
            b.bounds = CGRect(origin: .zero, size: CGSize(width: 50 * m.s, height: 52 * m.s))
            let from = CGPoint(x: centre.x + 42 * m.s, y: centre.y - 12 * m.s)
            b.position = from
            b.opacity = 0
            let show = CAKeyframeAnimation(keyPath: "opacity")
            show.values = [1, 1]; show.keyTimes = [0, 1]
            show.beginTime = t0 + tm.badgeAt; show.duration = tm.badgeSlide.0 + tm.badgeSlide.1 - tm.badgeAt
            b.add(show, forKey: "life")
            let appear = CABasicAnimation(keyPath: "transform.scale")
            appear.fromValue = 0; appear.toValue = 1
            appear.beginTime = t0 + tm.badgeAt; appear.duration = 0.08; appear.fillMode = .backwards
            b.add(appear, forKey: "appear")
            let bob = CABasicAnimation(keyPath: "position.y")
            bob.fromValue = from.y - 3 * m.s; bob.toValue = from.y + 3 * m.s
            bob.autoreverses = true; bob.duration = 0.075; bob.repeatCount = Float((tm.badgeSlide.0 - tm.badgeAt) / 0.15)
            bob.beginTime = t0 + tm.badgeAt
            b.add(bob, forKey: "bob")
            let slide = CABasicAnimation(keyPath: "position")
            slide.fromValue = NSValue(cgPoint: from); slide.toValue = NSValue(cgPoint: centre)
            slide.timingFunction = CAMediaTimingFunction(controlPoints: 0.11, 0, 0.5, 0)
            slide.beginTime = t0 + tm.badgeSlide.0; slide.duration = tm.badgeSlide.1; slide.fillMode = .forwards
            b.add(slide, forKey: "slide")
            out.append(b)
            out += burst(at: centre, radius: 45 * m.s, count: 10, begin: t0 + tm.burstAt, duration: 0.30, size: 12 * m.s)
        }
        // the "+1" → "+m" label above the token (A6), leaving with it
        for (i, text) in ["+1", "+\(c.added)"].enumerated() where i == 0 || c.added > 1 {
            guard let img = CoinFly.labelImage(text, size: 25 * m.s) else { continue }
            let l = CALayer()
            l.contents = img.image; l.contentsScale = img.scale
            l.bounds = CGRect(origin: .zero, size: img.size)
            l.position = CGPoint(x: centre.x, y: centre.y - 46 * m.s)
            l.opacity = 0
            let from = i == 0 ? tm.tokenAt : tm.labelAt
            let to = i == 0 && c.added > 1 ? tm.labelAt : tm.flyAt + shift + 0.10
            let a = CAKeyframeAnimation(keyPath: "opacity")
            a.values = [1, 1, 0]; a.keyTimes = [0, 0.9, 1]
            a.beginTime = t0 + from; a.duration = max(0.02, to - from)
            l.add(a, forKey: "life")
            out.append(l)
        }
        return out
    }

    /// B1-B7: the chip tray under the Claw bar, the lit chip moving, the green flag "+m" flying to the Streak badge.
    static func streak(_ s: PayoutPlan.Streak, timing tm: HomeReturnTiming, b0: Double, m: ShellMetrics, t0: CFTimeInterval) -> [CALayer] {
        var out: [CALayer] = []
        let steps = [5, 10, 25, 100]
        let tray = m.rect(CGRect(71.1, 141.8, 145.8, 42.0), .top)
        if let img = trayImage(steps: steps) {
            let l = CALayer()
            l.contents = img.image; l.contentsScale = img.scale
            l.frame = tray
            let mask = CALayer()
            mask.backgroundColor = UIColor.black.cgColor
            mask.anchorPoint = CGPoint(x: 0, y: 0.5)
            mask.bounds = CGRect(x: 0, y: 0, width: tray.width, height: tray.height)
            mask.position = CGPoint(x: 0, y: tray.height / 2)
            mask.transform = CATransform3DMakeScale(0.001, 1, 1)
            l.mask = mask
            let a = CAKeyframeAnimation(keyPath: "transform.scale.x")
            let total = tm.trayOut.0 + tm.trayOut.1
            a.values = [0.001, 1, 1, 0.001]
            a.keyTimes = [0, NSNumber(value: tm.trayIn.1 / total), NSNumber(value: tm.trayOut.0 / total), 1]
            a.timingFunctions = [CAMediaTimingFunction(controlPoints: 0.33, 1, 0.68, 1), CAMediaTimingFunction(name: .linear),
                                 CAMediaTimingFunction(controlPoints: 0.11, 0, 0.5, 0)]
            a.beginTime = t0 + b0 + tm.trayIn.0; a.duration = total
            mask.add(a, forKey: "tray")
            out.append(l)
            // the lit chip: from the previous multiplier's chip to the new one (B4)
            func chipCentre(_ v: Int) -> CGPoint {
                let i = steps.firstIndex(of: v) ?? -1
                return CGPoint(x: tray.minX + (i < 0 ? -10 * m.s : (22 + CGFloat(i) * 36.5) * m.s), y: tray.midY)
            }
            if let lit = litChipImage() {
                let c = CALayer()
                c.contents = lit.image; c.contentsScale = lit.scale
                c.bounds = CGRect(x: 0, y: 0, width: 38 * m.s, height: 34 * m.s)
                c.position = chipCentre(s.from)
                c.opacity = 0
                let life = CAKeyframeAnimation(keyPath: "opacity")
                life.values = [1, 1]; life.keyTimes = [0, 1]
                life.beginTime = t0 + b0 + tm.trayIn.1; life.duration = tm.trayOut.0 - tm.trayIn.1
                c.add(life, forKey: "life")
                let move = CABasicAnimation(keyPath: "position")
                move.fromValue = NSValue(cgPoint: chipCentre(s.from)); move.toValue = NSValue(cgPoint: chipCentre(s.to))
                move.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
                move.beginTime = t0 + b0 + tm.chipAt; move.duration = tm.chipDur; move.fillMode = .forwards
                c.add(move, forKey: "move")
                out.append(c)
            }
        }
        // the green flag "+m" at (133, 232) → the Streak badge (49, 231), apex 50 pt above (B2/B3)
        let from = m.point(CGPoint(x: 133, y: 232), .top), to = m.point(CGPoint(x: 49, y: 231), .top)
        let flag = CALayer()
        flag.contents = ArtStore.image(.iconFinishFlag)?.cgImage
        flag.contentsGravity = .resizeAspect
        flag.bounds = CGRect(x: 0, y: 0, width: 36 * m.s, height: 38 * m.s)
        flag.position = from
        flag.opacity = 0
        let life = CAKeyframeAnimation(keyPath: "opacity")
        life.values = [1, 1]; life.keyTimes = [0, 1]
        life.beginTime = t0 + b0 + tm.flagAt; life.duration = tm.flagFly.0 + tm.flagFly.1 - tm.flagAt
        flag.add(life, forKey: "life")
        let pop = CABasicAnimation(keyPath: "transform.scale")
        pop.fromValue = 0.2; pop.toValue = 1
        pop.timingFunction = CAMediaTimingFunction(controlPoints: 0.34, 1.56, 0.64, 1)
        pop.beginTime = t0 + b0 + tm.flagAt; pop.duration = 0.10; pop.fillMode = .backwards
        flag.add(pop, forKey: "pop")
        let path = UIBezierPath(); path.move(to: from)
        path.addQuadCurve(to: to, controlPoint: CGPoint(x: (from.x + to.x) / 2, y: min(from.y, to.y) - 100 * m.s))
        let fly = CAKeyframeAnimation(keyPath: "position")
        fly.path = path.cgPath
        fly.timingFunction = CAMediaTimingFunction(controlPoints: 0.11, 0, 0.5, 0)
        fly.beginTime = t0 + b0 + tm.flagFly.0; fly.duration = tm.flagFly.1; fly.fillMode = .forwards
        flag.add(fly, forKey: "fly")
        let shrink = CABasicAnimation(keyPath: "transform.scale")
        shrink.fromValue = 1; shrink.toValue = 0.5
        shrink.beginTime = fly.beginTime; shrink.duration = fly.duration; shrink.fillMode = .forwards
        flag.add(shrink, forKey: "shrink")
        out.append(flag)
        if let img = CoinFly.labelImage("+\(s.flags)", size: 22 * m.s) {
            let l = CALayer()
            l.contents = img.image; l.contentsScale = img.scale
            l.bounds = CGRect(origin: .zero, size: img.size)
            l.position = CGPoint(x: from.x + 34 * m.s, y: from.y)
            l.opacity = 0
            let a = CAKeyframeAnimation(keyPath: "opacity")
            a.values = [1, 1, 0]
            a.keyTimes = [0, NSNumber(value: (tm.flagFly.0 - tm.flagAt) / (tm.flagFly.0 + 0.2 - tm.flagAt)), 1]
            a.beginTime = t0 + b0 + tm.flagAt; a.duration = tm.flagFly.0 + 0.2 - tm.flagAt
            l.add(a, forKey: "life")
            out.append(l)
        }
        return out
    }

    /// A5 / §10 "claw merge burst": `count` twinkles flying radially 0 → radius, scale 1 → 0, on the host clock.
    static func burst(at p: CGPoint, radius: CGFloat, count: Int, begin: CFTimeInterval, duration: Double, size: CGFloat) -> [CALayer] {
        (0..<count).map { i in
            let a = Double(i) / Double(count) * 2 * .pi
            let star = CAShapeLayer()
            star.path = Sparkles.starPath(size: size)
            star.fillColor = (i % 2 == 0 ? UIColor.white : UIColor(rgb: Skin.homePayoutSequenceHomeReturnLayersBurstFillColorNot20, alpha: 1)).cgColor
            star.position = p
            star.opacity = 0
            let move = CABasicAnimation(keyPath: "position")
            move.fromValue = NSValue(cgPoint: p)
            move.toValue = NSValue(cgPoint: CGPoint(x: p.x + CGFloat(cos(a)) * radius, y: p.y + CGFloat(sin(a)) * radius))
            let sc = CABasicAnimation(keyPath: "transform.scale")
            sc.fromValue = 1; sc.toValue = 0
            let op = CAKeyframeAnimation(keyPath: "opacity")
            op.values = [1, 1]; op.keyTimes = [0, 1]
            let g = CAAnimationGroup()
            g.animations = [move, sc, op]
            g.timingFunction = CAMediaTimingFunction(controlPoints: 0.5, 1, 0.89, 1)        // easeOutQuad
            g.beginTime = begin; g.duration = duration
            star.add(g, forKey: "burst")
            return star
        }
    }

    private static func flash(at p: CGPoint, r: CGFloat, begin: CFTimeInterval, dur: Double) -> CALayer {
        let l = CAShapeLayer()
        l.path = UIBezierPath(ovalIn: CGRect(x: -r, y: -r, width: 2 * r, height: 2 * r)).cgPath
        l.fillColor = UIColor.white.cgColor
        l.position = p
        l.opacity = 0
        let a = CAKeyframeAnimation(keyPath: "opacity")
        a.values = [0, 0.9, 0]; a.keyTimes = [0, 0.5, 1]
        a.beginTime = begin; a.duration = dur
        l.add(a, forKey: "flash")
        return l
    }

    private static func flameImage(_ multiplier: Int) -> CoinFly.LabelImage? {
        let scale = UIScreen.main.scale
        let tokens = S2Hooks.app?.tuning.ui.tokens ?? Tokens(TuningFile(name: "ui", json: [:]))
        guard let img = RasterCache.image("flameImg|\(multiplier)", size: CGSize(width: 50, height: 52), scale: scale, content: {
            MultiplierFlame(multiplier: multiplier, t: tokens)
        }) else { return nil }
        return .init(image: img, size: CGSize(width: 50, height: 52), scale: scale)
    }

    /// The tray x5 x10 x25 x100 (blue chevron chips on a navy strip; VERIFIED 035).
    private static func trayImage(steps: [Int]) -> CoinFly.LabelImage? {
        let scale = UIScreen.main.scale
        let size = CGSize(width: 145.8, height: 42)
        guard let img = RasterCache.image("streakTray", size: size, scale: scale, content: {
            ZStack(alignment: .topLeading) {
                RoundedRectangle(cornerRadius: 9.5).fill(Color(hex: Skin.homePayoutSequenceHomeReturnLayersTrayImageFill))
                RoundedRectangle(cornerRadius: 8.5).fill(Color(hex: Skin.homePayoutSequenceHomeReturnLayersTrayImageFillV2)).padding(1.2)
                ForEach(Array(steps.enumerated()), id: \.offset) { i, v in
                    let st = GameTextStyle.s2(16.5, -0.6, [Skin.homePayoutSequenceHomeReturnLayersTrayImageSt0], outline: Skin.homePayoutSequenceHomeReturnLayersTrayImageStOutline, 1.2, drop: 0.7)
                    ZStack {
                        ChevronChipShape().fill(LinearGradient(colors: [Color(hex: Skin.homePayoutSequenceHomeReturnLayersTrayImageColors0), Color(hex: Skin.homePayoutSequenceHomeReturnLayersTrayImageColors1)], startPoint: .top, endPoint: .bottom))
                        ChevronChipShape().stroke(Color(hex: Skin.homePayoutSequenceHomeReturnLayersTrayImageStroke), lineWidth: 1)
                        GameText(verbatim: "x\(v)", style: st, maxWidth: 32)
                    }
                    .frame(width: 36, height: 32)
                    .position(x: 22 + CGFloat(i) * 36.5, y: 21)
                }
            }
            .frame(width: size.width, height: size.height)
        }) else { return nil }
        return .init(image: img, size: size, scale: scale)
    }

    private static func litChipImage() -> CoinFly.LabelImage? {
        let scale = UIScreen.main.scale
        let size = CGSize(width: 38, height: 34)
        guard let img = RasterCache.image("streakLitChip", size: size, scale: scale, content: {
            ZStack {
                ChevronChipShape().fill(LinearGradient(colors: [Color(hex: Skin.homePayoutSequenceHomeReturnLayersLitChipImageColors0), Color(hex: Skin.homePayoutSequenceHomeReturnLayersLitChipImageColors1)], startPoint: .top, endPoint: .bottom))
                ChevronChipShape().stroke(Color(hex: Skin.homePayoutSequenceHomeReturnLayersLitChipImageStroke), lineWidth: 2)
            }
            .frame(width: size.width, height: size.height)
        }) else { return nil }
        return .init(image: img, size: size, scale: scale)
    }
}

/// A chevron chip (arrow-shaped: notched left edge, pointed right edge; SPEC-ui §1.6.17).
struct ChevronChipShape: Shape {
    func path(in r: CGRect) -> Path {
        let n = r.height * 0.28
        var p = Path()
        p.move(to: CGPoint(x: r.minX, y: r.minY))
        p.addLine(to: CGPoint(x: r.maxX - n, y: r.minY))
        p.addLine(to: CGPoint(x: r.maxX, y: r.midY))
        p.addLine(to: CGPoint(x: r.maxX - n, y: r.maxY))
        p.addLine(to: CGPoint(x: r.minX, y: r.maxY))
        p.addLine(to: CGPoint(x: r.minX + n, y: r.midY))
        p.closeSubpath()
        return p
    }
}

/// A display link that calls `tick(targetTimestamp)` every frame until it returns false (the payout's beat scheduler); it also
/// logs the frame intervals it saw ("[PC][perf] <label> frames n max x ms over20 k": the FEEL budget, 0 frames > 20 ms).
@MainActor final class BeatClock: NSObject {
    private var link: CADisplayLink?
    private var tick: ((CFTimeInterval) -> Bool)?
    private var last: CFTimeInterval = 0
    private var intervals: [Double] = []
    private var label = ""
    private static var live: Set<BeatClock> = []

    static func start(origin: CFTimeInterval, label: String = "payout", tick: @escaping (CFTimeInterval) -> Bool) {
        let c = BeatClock()
        c.tick = tick
        c.label = label
        let l = CADisplayLink(target: c, selector: #selector(step(_:)))
        l.add(to: .main, forMode: .common)
        c.link = l
        live.insert(c)
        _ = origin
    }

    @objc private func step(_ l: CADisplayLink) {
        if last > 0 { intervals.append((l.timestamp - last) * 1000) }
        last = l.timestamp
        if tick?(l.targetTimestamp) != true {
            l.invalidate()
            link = nil
            tick = nil
            Self.live.remove(self)
            let over = intervals.filter { $0 > 20 }.count
            Log.mark("perf", "\(label) frames \(intervals.count) max \(String(format: "%.1f", intervals.max() ?? 0)) ms over20 \(over)")
        }
    }
}
