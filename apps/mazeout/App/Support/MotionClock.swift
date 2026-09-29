import Foundation
import Observation

// ◆ CONTRACT (SPEC-architecture §3.5, §5.12, §9.1, §9.2). Written by the LEAD in WP0 and FROZEN: any change goes through
// the orchestrator (build/wp0/frozen-contracts.sha256).
// THE one game clock. Wall time is integrated × `timeScale` into `gameTime`; slow motion (-pc.slowmo N) and capture
// freezes (-pc.freezeAt <sequence>@<t>) act here, so SwiftUI sequences, the level timer and the board stop together:
//  - SwiftUI sequences: `let t = clock.sequenceTime("win", clock.gameTime(ctx.date) - start)` inside a TimelineView;
//  - dt-driven code (the session tick from the board's display link): `let dt = clock.scaled(frameDT)`;
//  - the board mirrors the scale onto its stage layer (`speed` / `timeOffset`, §5.12) through `observeTimeScale`.
// It also owns the WALL clock for lives, events and the social world (`-pc.now`, `-pc.clockOffset`, `-pc.clockRate`,
// and the fixed capture date).

@MainActor @Observable final class MotionClock {
    struct FreezePoint: Equatable { var sequence: String; var t: Double }

    /// 1 normally, 1/N with -pc.slowmo N.
    let baseTimeScale: Double
    /// The current scale: baseTimeScale, or 0 while a freeze holds.
    private(set) var timeScale: Double
    /// The requested capture freeze (-pc.freezeAt), if any.
    let freezeAt: FreezePoint?
    /// Set when `freezeAt` has been reached; captures wait for this.
    private(set) var frozenAt: FreezePoint?
    /// Game seconds since launch. Not observation-tracked (it advances inside TimelineView bodies); read it through
    /// `gameTime(_:)`.
    @ObservationIgnored private(set) var gameNow: Double = 0

    @ObservationIgnored private var lastDate: Date?
    @ObservationIgnored private let launchReal = Date()
    @ObservationIgnored private let clockStart: Date?
    @ObservationIgnored private let clockRate: Double
    @ObservationIgnored private let clockOffset: Double
    @ObservationIgnored private var scaleObservers: [@MainActor (Double) -> Void] = []

    init(args: LaunchArgs) {
        baseTimeScale = args.timeScale
        timeScale = args.timeScale
        freezeAt = args.freezeAt.map { FreezePoint(sequence: $0.sequence, t: $0.t) }
        clockStart = args.clockStart
        clockRate = args.effectiveClockRate
        clockOffset = args.clockOffset ?? 0
    }

    var isFrozen: Bool { timeScale == 0 }

    /// Integrates (date − last) × timeScale and returns the game time at `date`. Earlier dates return the current
    /// value (the clock never runs backwards); a stall adds at most 0.25 s.
    @discardableResult
    func gameTime(_ date: Date = Date()) -> Double {
        if let last = lastDate {
            let dt = date.timeIntervalSince(last)
            if dt > 0 { gameNow += min(dt, 0.25) * timeScale; lastDate = date }
        } else {
            lastDate = date
        }
        return gameNow
    }

    /// Scaled frame delta for dt-driven code: clamped to 1/20 s, 0 while frozen.
    func scaled(_ realDT: Double) -> Double { min(max(realDT, 0), 1.0 / 20) * timeScale }

    /// Local time inside a named sequence. When `-pc.freezeAt <sequence>@<t>` is reached the clock freezes and the
    /// sequence is held exactly at t.
    func sequenceTime(_ sequence: String, _ t: Double) -> Double {
        guard let f = freezeAt, f.sequence == sequence else { return t }
        if t >= f.t {
            if frozenAt == nil { frozenAt = f; freeze() }
            return f.t
        }
        return t
    }

    /// Stops game time (capture freeze).
    func freeze() { setScale(0) }

    /// Lifts a freeze (debug / tests).
    func resume() {
        frozenAt = nil
        setScale(baseTimeScale)
    }

    /// Slow motion at runtime (BoardLab, SoundBoard); 1 = real time.
    func setTimeScale(_ k: Double) { setScale(max(k, 0)) }

    /// `body` runs now and on every scale change (the board mirrors it onto its stage layer's speed).
    func observeTimeScale(_ body: @escaping @MainActor (Double) -> Void) {
        scaleObservers.append(body)
        body(timeScale)
    }

    /// The wall clock for lives, events, the social world and timestamps: the real time, or `-pc.now` / the capture
    /// date advancing at `-pc.clockRate` (0 in capture mode), plus `-pc.clockOffset`.
    func wallClock(_ real: Date = Date()) -> Date {
        let start = clockStart ?? launchReal
        return start.addingTimeInterval(real.timeIntervalSince(launchReal) * clockRate + clockOffset)
    }

    private func setScale(_ k: Double) {
        gameTime()
        guard k != timeScale else { return }
        timeScale = k
        for f in scaleObservers { f(k) }
    }
}
