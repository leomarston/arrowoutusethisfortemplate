import SwiftUI
import UIKit
import PathCore

// SHELL S3 (SPEC-architecture §6.4 item 1; SPEC-ui §2.2.1, §2.2.8 + correction C4; CONSISTENCY U-16, W-23) + A4 ART-INTEG (owner
// item 4, ruling 46; R3 HOME art/lanes/home.handoff.json "signpost"). The home centrepiece in front of the cabinet: was a tangled
// arrow pile (`homeArrowPile*` + dropping `arrowGlossy*`, where the owner saw "the arrows under the pink monster going into each
// other"); now R3's SIGNPOST — five painted arrow boards, each on its own hinge on one post (no board touches another: R3's
// pairwise overlap gate), a lantern on a hook. Same place and role (home.scene.arrowPile = the rig's frame), same trigger:
//   idle    the boards sway ±2° about their hinges and the lantern ±3° (ui.json puppet.home_signpost_rig, a 36 s PuppetStage
//           loop on the render server: 0 main-thread work at rest);
//   refill  when home re-appears from an event page or a popup flow that replaced it (Sky Jump join 070, the Rocket Race page 168,
//           Rocket lost 184, the Streak Race page 204) the boards hide and flip back in top → bottom (scaleX 0 → 1.06 → 1 about
//           each hinge, 0.15 s, 0.18 s apart) with a light haptic tick on each board's landing frame, then the post knocks (1.2 pt);
//           1.2 s in total (ui.json home.pileRefill). Whoever leaves home for an event page calls `HomeScene.requestRefill()`
//           (the event page shell's close does; SOC2's popup flows may).

@MainActor enum HomeScene {
    private(set) static var refillPending = false
    static func requestRefill() { refillPending = true }
    static func takeRefill() -> Bool { defer { refillPending = false }; return refillPending }
}

/// The signpost refill's steps (ui.json `puppet.home_signpost_rig.refill`, R3's data): one-shot keyframes on the rig's layers.
struct SignpostRefill {
    struct Step {
        let layer: String
        let prop: String
        let begin: Double
        let duration: Double
        let values: [Double]
        let keyTimes: [Double]
        let curve: String
        /// The tick on the board's landing frame: (offset from the refill's start, intensity).
        let haptic: (at: Double, intensity: Double)?
    }

    var hiddenAtStart: [String] = []
    var steps: [Step] = []

    static let none = SignpostRefill()

    init() {}

    init(_ file: TuningFile, rig: String) {
        let base = "puppet." + rig + ".refill"
        hiddenAtStart = file.strings(base + ".hiddenAtStart", [])
        var raw = file.value(base + ".steps") as? [[String: Any]] ?? []
        if let knock = file.value(base + ".knock") as? [String: Any] { raw.append(knock) }
        steps = raw.compactMap { item -> Step? in
            guard let layer = item["layer"] as? String, let prop = item["prop"] as? String,
                  let begin = (item["begin"] as? NSNumber)?.doubleValue, let dur = (item["duration"] as? NSNumber)?.doubleValue,
                  let v = item["values"] as? [NSNumber], let k = item["keyTimes"] as? [NSNumber], v.count == k.count, v.count > 1
            else { return nil }
            var haptic: (Double, Double)?
            if let h = item["haptic"] as? [String: Any], let at = (h["at"] as? NSNumber)?.doubleValue {
                haptic = (at, (h["intensity"] as? NSNumber)?.doubleValue ?? 0.45)
            }
            return Step(layer: layer, prop: prop, begin: begin, duration: dur, values: v.map(\.doubleValue),
                        keyTimes: k.map(\.doubleValue), curve: (item["curve"] as? String) ?? "easeOut", haptic: haptic)
        }
    }
}

/// The signpost at its frame on the scene canvas (put it inside `SceneLayer`). `refill`: a token — non-zero at creation, or a
/// new value later (home is persistent, FIX-A1: each refilling arrival brings a new token), plays the refill once.
struct HomeCentrepiece: UIViewRepresentable {
    let rig: PuppetRig
    let motion: PuppetMotion
    let steps: SignpostRefill
    let refill: Int
    let clock: MotionClock
    let animate: Bool
    let freezeAt: Double?
    /// A board's landing tick (the haptic, intensity).
    let tick: @MainActor (Double) -> Void

    func makeUIView(context: Context) -> SignpostView {
        let v = SignpostView(rig: rig, motion: motion, steps: steps, animate: animate, freezeAt: freezeAt, tick: tick)
        v.configure(refill: refill)
        clock.observeTimeScale { [weak v] k in v?.puppet.setTimeScale(k) }
        return v
    }

    func updateUIView(_ uiView: SignpostView, context: Context) {
        uiView.configure(refill: refill)
    }
}

final class SignpostView: PuppetFrameView {
    private let steps: SignpostRefill
    private let tick: @MainActor (Double) -> Void
    /// The refill token last configured; `pending` = its refill has not played yet (it plays once the view is in a window).
    private var token = 0
    private var pending = false
    private var generation = 0

    init(rig: PuppetRig, motion: PuppetMotion, steps: SignpostRefill, animate: Bool, freezeAt: Double?,
         tick: @escaping @MainActor (Double) -> Void) {
        self.steps = steps
        self.tick = tick
        super.init(PuppetView(rig: rig, motion: motion, animate: animate, freezeAt: freezeAt))
    }

    required init?(coder: NSCoder) { fatalError("built in code") }

    func configure(refill: Int) {
        guard refill != token else { return }
        token = refill
        guard refill != 0 else { return }
        pending = true
        if window != nil { playPending() }
    }

    override func didMoveToWindow() {
        super.didMoveToWindow()
        if window != nil { playPending() }
    }

    private func playPending() {
        guard pending else { return }
        pending = false
        play()
    }

    /// The boards flip in (render-server keyframes on the rig's layers, additive over the idle sway) and each landing ticks
    /// on the frame that presents it (the payout's display-link beat clock: a GCD timer drifts 50-70 ms late).
    private func play() {
        generation += 1
        let gen = generation
        let h0 = CACurrentMediaTime()
        let now = puppet.layer.convertTime(h0, from: nil)
        CATransaction.begin(); CATransaction.setDisableActions(true)
        for s in steps.steps {
            puppet.oneShot(layer: s.layer, prop: s.prop, values: s.values, keyTimes: s.keyTimes, curve: s.curve,
                           begin: now + s.begin, duration: s.duration, holdBefore: steps.hiddenAtStart.contains(s.layer),
                           key: "refill")
        }
        CATransaction.commit()
        var queue = steps.steps.compactMap { s in s.haptic.map { (s.layer, $0.at, $0.intensity) } }.sorted { $0.1 < $1.1 }
        let tick = self.tick
        if !queue.isEmpty {
            BeatClock.start(origin: h0, label: "signpost") { [weak self] target in
                guard let self, gen == self.generation else { return false }
                while let next = queue.first, next.1 <= target - h0 + 0.001 {
                    queue.removeFirst()
                    tick(next.2)
                }
                return !queue.isEmpty
            }
        }
        Log.mark("home", "signpost refill (\(steps.steps.count) steps, \(queue.count) ticks)")
    }
}

/// When home may build its hidden Shop / Leaderboard pages: 1.5 s after it appears and once no home-return queue or popup runs
/// (the build is main-thread work; the scene's animations run on the render server and do not drop a frame meanwhile). Not in
/// UI tests or captures (they open the pages themselves).
@MainActor enum HomeTabsPremount {
    static func wait(_ app: AppModel) async -> Bool {
        guard !app.args.quietUI else { return false }
        try? await Task.sleep(nanoseconds: 1_500_000_000)
        var waited = 0
        while (PayoutSequence.running || app.popups.isPresenting), waited < 40, !Task.isCancelled {
            try? await Task.sleep(nanoseconds: 250_000_000)
            waited += 1
        }
        // FIX-A1: home is parked (not torn down) while another screen shows: build only while home is the screen
        guard !Task.isCancelled, app.router.screen.isHome else { return false }
        return true
    }
}
