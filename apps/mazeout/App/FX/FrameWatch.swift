import UIKit

// F3-A (SPEC.md ruling 52(a)): measurement only — compiled into Debug and the Measure configuration (Release's settings +
// PC_MEASURE), never into the Release (store) build; FXOverlay logs an error when `-pc.frameWatch` reaches a store build.
#if DEBUG || PC_MEASURE
// FEEL (SPEC-architecture §10.2 "frames in the shell: 0 frames > 20 ms after warm-up", §10.3 item 1). The board's PerfMonitor
// only sees frames while the board is in a window (a level); Loading, home, popups over home and the first-launch chain are
// not covered. `-pc.frameWatch 1` (measurement only; off by default: an always-running display link would keep an idle app
// at 60 Hz) runs one more main-run-loop CADisplayLink from the app's start and logs every presented frame interval over
// 20 ms with the screen it happened on:
//     `[PC][frame] hitch <ms> ms <screen> cpu <ms>`   (the same grammar as the board's `hitch` mark, category `frame`; A3:
//                                                      + the main thread's CPU time over that interval — a long frame with
//                                                      little CPU is the machine's load, not the app's work)
//     `[PC][frame] summary <screen>: frames <n> over20 <k> max <ms>`   (every 10 s, and when the screen changes)
// The display link pauses nothing and allocates nothing per frame.

@MainActor final class FrameWatch: NSObject {
    static private(set) var shared: FrameWatch?

    /// Starts the watch once (FXOverlay's init, when `-pc.frameWatch` is set). `screen` names the current screen.
    static func start(screen: @escaping @MainActor () -> String) {
        guard shared == nil else { return }
        let w = FrameWatch(screen: screen)
        shared = w
        Log.mark("frame", "watch on (every presented frame > 20 ms is logged)")
    }

    private let screen: @MainActor () -> String
    private var link: CADisplayLink?
    private var last: CFTimeInterval = 0
    private var frames = 0
    private var over = 0
    private var maxMs = 0.0
    private var lastScreen = ""
    private var lastSummary: CFTimeInterval = 0
    private var lastCPU: UInt64 = 0                         // A3: CLOCK_THREAD_CPUTIME_ID of the main thread at the last tick

    private init(screen: @escaping @MainActor () -> String) {
        self.screen = screen
        super.init()
        let l = CADisplayLink(target: self, selector: #selector(tick(_:)))
        l.preferredFrameRateRange = CAFrameRateRange(minimum: 60, maximum: 120, preferred: 120)
        l.add(to: .main, forMode: .common)
        link = l
    }

    @objc private func tick(_ l: CADisplayLink) {
        let ts = l.timestamp
        let cpu = clock_gettime_nsec_np(CLOCK_THREAD_CPUTIME_ID)
        defer { last = ts; lastCPU = cpu }
        guard last > 0 else { lastSummary = ts; return }
        let ms = (ts - last) * 1000
        let cpuMs = Double(cpu &- lastCPU) / 1e6
        let s = screen()
        if s != lastScreen {
            if !lastScreen.isEmpty { summary(lastScreen) }
            lastScreen = s
            lastSummary = ts
        }
        frames += 1
        maxMs = max(maxMs, ms)
        if ms > 20 {
            over += 1
            Log.mark("frame", String(format: "hitch %.1f ms %@ cpu %.1f", ms, s, cpuMs))
        }
        if ts - lastSummary >= 10 {
            summary(s)
            lastSummary = ts
        }
    }

    private func summary(_ s: String) {
        Log.mark("frame", String(format: "summary %@: frames %d over20 %d max %.1f", s, frames, over, maxMs))
        frames = 0
        over = 0
        maxMs = 0
    }
}
#endif
