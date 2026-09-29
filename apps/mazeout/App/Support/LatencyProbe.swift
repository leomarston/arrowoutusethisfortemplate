import Foundation
import QuartzCore

// WP0 → B1 (SPEC-architecture §3.2, §8.2, §10.3 item 3). Working basics written by the LEAD; BOARD owns it from B1 on.
// Measures one tap end to end:
//   touch.timestamp (the release) → handler (`beginTap`, CACurrentMediaTime at the top of the release handler)
//   → commit (a run-loop observer ordered AFTER Core Animation's own commit observer, 2_000_000, on BeforeWaiting)
//   → the first display-link frame after the commit (`frame(targetTimestamp:)`: its target vsync).
// Every clock is CACurrentMediaTime's (UITouch.timestamp uses the same mach time base). Logged by the caller as
// `[PC][perf] tap L<n> a<id> touch→handler <ms> handler→commit <ms> commit→vsync <ms>` (§9.3).

@MainActor final class LatencyProbe {
    struct Sample: Codable, Equatable {
        var touchToHandlerMs: Double
        var handlerToCommitMs: Double?
        var commitToVsyncMs: Double?
    }

    private(set) var last: Sample?
    private(set) var samples: [Sample] = []
    private let capacity: Int
    private var current: Sample?
    private var handlerTime: CFTimeInterval?
    private var commitTime: CFTimeInterval?
    private var observer: CFRunLoopObserver?
    /// Called when a sample completes (the caller logs it).
    var onSample: ((Sample) -> Void)?

    init(capacity: Int = 200) { self.capacity = capacity }

    /// The top of the release handler.
    func beginTap(touchTimestamp: TimeInterval) {
        let now = CACurrentMediaTime()
        current = Sample(touchToHandlerMs: (now - touchTimestamp) * 1000, handlerToCommitMs: nil, commitToVsyncMs: nil)
        handlerTime = now
        commitTime = nil
        installObserver()
    }

    /// Every display-link tick: the first one after the commit completes the sample.
    func frame(targetTimestamp: CFTimeInterval) {
        guard var s = current, let c = commitTime else { return }
        s.commitToVsyncMs = max(0, (targetTimestamp - c) * 1000)
        finish(s)
    }

    /// p-th percentile (0…1) of a field over the stored samples.
    func percentile(_ p: Double, _ field: KeyPath<Sample, Double?>) -> Double {
        percentile(p) { $0[keyPath: field] }
    }

    /// p-th percentile (0…1) of any per-sample value (nil = skipped), e.g. touch→commit = touch→handler + handler→commit.
    func percentile(_ p: Double, of value: (Sample) -> Double?) -> Double {
        let v = samples.compactMap(value).sorted()
        guard !v.isEmpty else { return 0 }
        return v[min(v.count - 1, Int((Double(v.count - 1) * p).rounded()))]
    }

    /// Forgets the stored samples (a lab starts its measurement window).
    func resetSamples() { samples = [] }

    private func markCommit() {
        guard var s = current, let h = handlerTime, commitTime == nil else { return }
        let now = CACurrentMediaTime()
        s.handlerToCommitMs = (now - h) * 1000
        current = s
        commitTime = now
    }

    private func finish(_ s: Sample) {
        last = s
        samples.append(s)
        if samples.count > capacity { samples.removeFirst(samples.count - capacity) }
        current = nil; handlerTime = nil; commitTime = nil
        onSample?(s)
    }

    private func installObserver() {
        guard observer == nil else { return }
        let obs = CFRunLoopObserverCreateWithHandler(kCFAllocatorDefault, CFRunLoopActivity.beforeWaiting.rawValue, true,
                                                     2_000_001) { [weak self] _, _ in
            MainActor.assumeIsolated { self?.markCommit() }
        }
        CFRunLoopAddObserver(CFRunLoopGetMain(), obs, .commonModes)
        observer = obs
    }
}
