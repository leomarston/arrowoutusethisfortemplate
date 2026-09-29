import SwiftUI
import QuartzCore

// SHELL S1 (SPEC-architecture §6.1 transition table). The timings are data (ui.json):
//   launch → Loading          the launch-screen colour, then the SwiftUI Loading screen on the first frame (GameApp/AppModel)
//   Loading → first board     cross-fade `transition.loadingToBoard` 0.13 s (VERIFIED 0.1–0.16 s, tutorials §1, motion §6.4)
//   Loading → home            cross-fade `transition.loadingToHome` 0.3 s (PENDING-ui)
//   home → level              HARD CUT (VERIFIED motion §5.1); the board build-in + HUD drop are GAME/BOARD's
//   win Continue → home       HARD CUT (VERIFIED vflows §6, motion §6.3), then the payout on home (S3)
//   level → level             HARD CUT (the FTUE chain L5 → L6, Try Again)
//   home tabs                 PUSH-SLIDE `transition.tabSlide` 0.488 s, D·(1 − u)^2.51 (A2, VERIFIED v582; HomeTabStrip)
//   popups                    instant; the dim reaches its alpha in `popup.dimFadeIn` (0–0.1 s VERIFIED motion §5.3)

struct ShellTiming {
    let loadingToBoard: Double
    let loadingToHome: Double
    let ui: UITuning

    init(ui: UITuning) {
        loadingToBoard = ui.loadingToBoardFade
        loadingToHome = ui.loadingToHomeFade
        self.ui = ui
    }

    /// The cross-fade out of Loading into `target`.
    func fromLoading(to target: Screen) -> Double {
        if case .level = target { return loadingToBoard }
        return loadingToHome
    }
}

/// One full-screen state in the router's stack (bottom → top); the top one is being faded in. A parked home is a layer at
/// opacity 0 under the others (Router `cutLayers`, FIX-A1); `arrival` changes each time home is shown again (0 = built,
/// never shown).
struct ScreenLayer: Identifiable, Equatable {
    let id: Int
    var screen: Screen
    var opacity: Double
    var arrival: Int = 0
}

extension Screen {
    var isLevel: Bool { if case .level = self { return true }; return false }
    var isHome: Bool { if case .home = self { return true }; return false }
    var homeTab: HomeTab? { if case .home(_, let tab) = self { return tab }; return nil }
    /// Same screen kind with another home tab or entry (no re-mount: a tab switch keeps HomeView's identity).
    func sameKind(_ other: Screen) -> Bool {
        switch (self, other) {
        case (.home, .home), (.loading, .loading), (.profile, .profile): return true
        case (.event(let a), .event(let b)): return a == b
        case (.lab(let a), .lab(let b)): return a == b
        default: return false
        }
    }
}

/// Awaits presented frames: a CADisplayLink fires at each vsync after the commit that carried the change, so
/// `frames(2)` returns once the new content has been on screen for a frame (the §9.3 "visible" marks, capture readiness).
@MainActor final class FrameWaiter: NSObject {
    private var link: CADisplayLink?
    private var remaining = 0
    private var continuation: CheckedContinuation<Void, Never>?

    static func frames(_ n: Int) async {
        let w = FrameWaiter()
        await w.wait(n)
    }

    private func wait(_ n: Int) async {
        await withCheckedContinuation { (cont: CheckedContinuation<Void, Never>) in
            continuation = cont
            remaining = max(1, n)
            let l = CADisplayLink(target: self, selector: #selector(tick))
            l.add(to: .main, forMode: .common)
            link = l
        }
    }

    @objc private func tick() {
        remaining -= 1
        guard remaining <= 0 else { return }
        link?.invalidate(); link = nil
        continuation?.resume(); continuation = nil
    }
}

/// Records presented-frame intervals for a while (a CADisplayLink on the main run loop) and logs the worst one:
/// `[PC][perf] <label> frames <n> max <ms> ms over20 <k>` — S1's check that a popup or page opens without a dropped frame
/// (SPEC-architecture §10.2 "frames in the shell"). Debug hook only: started by `-pc.popupDelay`.
@MainActor final class FrameProbe: NSObject {
    private var link: CADisplayLink?
    private var last: CFTimeInterval = 0
    private var intervals: [Double] = []
    private let label: String

    init(_ label: String) { self.label = label }

    func start() {
        let l = CADisplayLink(target: self, selector: #selector(tick(_:)))
        l.add(to: .main, forMode: .common)
        link = l
    }

    private var t0: CFTimeInterval = 0
    private var long: [String] = []

    /// A3: the main thread's CPU time per frame (CLOCK_THREAD_CPUTIME_ID): a long frame with little CPU is the machine's load.
    private var cpuLast: UInt64 = 0
    private var cpuMax = 0.0
    private var cpuTotal = 0.0

    @objc private func tick(_ l: CADisplayLink) {
        let cpu = clock_gettime_nsec_np(CLOCK_THREAD_CPUTIME_ID)
        if t0 == 0 { t0 = l.timestamp }
        if last > 0 {
            let dt = (l.timestamp - last) * 1000
            let c = Double(cpu &- cpuLast) / 1e6
            cpuMax = max(cpuMax, c)
            cpuTotal += c
            intervals.append(dt)
            if dt > 20 { long.append(String(format: "%.0f ms (cpu %.1f) at +%.3f", dt, c, l.timestamp - t0)) }   // A2 (+ A3 cpu)
        }
        last = l.timestamp
        cpuLast = cpu
    }

    func stop() { _ = stopResult() }

    /// Stops, logs, and returns (frames, worst interval ms, intervals over 20 ms) — A2's loops sum them.
    @discardableResult
    func stopResult() -> (frames: Int, max: Double, over20: Int) {
        link?.invalidate(); link = nil
        let over = intervals.filter { $0 > 20 }.count
        Log.mark("perf", "\(label) frames \(intervals.count) max \(String(format: "%.1f", intervals.max() ?? 0)) ms over20 \(over)"
                 + String(format: " cpu max %.1f total %.1f", cpuMax, cpuTotal)
                 + (long.isEmpty ? "" : " (" + long.joined(separator: ", ") + ")"))
        return (intervals.count, intervals.max() ?? 0, over)
    }
}
