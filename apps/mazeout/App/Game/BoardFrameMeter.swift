import Foundation
import QuartzCore
import PathCore

// Template phase 5 (docs/architecture/PUZZLE-MODULE.md §8c). The Play's frame meter for a board that does not meter its own
// frames (`PuzzleBoard.metersFrames` false: every board but ArrowEscape's engine, whose display link has always fed
// PerfMonitor / LatencyProbe and logged its hitches and tap latency itself). Fed only by the generic contract: the delegate's
// `boardFrame` (every display-link frame of the board while a Play runs) and `boardInput` (the top of the board's release
// handler), so any module's board gets the same frame statistics (bench JSON, the debug overlay) with no code of its own.
// Log lines keep the engine's formats (`[PC][board] hitch …`, `[PC][perf] tap L<n> a<target> …`: tools/bench/bench.py).

@MainActor final class BoardFrameMeter {
    let perf: PerfMonitor
    let latency: LatencyProbe
    /// The last frame's timestamp (0 = none yet).
    private var last: CFTimeInterval = 0
    private(set) var frames = 0
    private(set) var hitches = 0
    /// Logs every hitch and every completed tap sample (`-pc.bench`, `-pc.hud debug`, `-pc.logTaps`), like the engine.
    let logs: Bool
    /// The level and the target of the last tap (the latency line).
    var tapLabel: (level: Int, target: String) = (0, "-")

    init(perf: PerfMonitor, latency: LatencyProbe, logs: Bool) {
        self.perf = perf
        self.latency = latency
        self.logs = logs
    }

    /// One display-link frame: the interval since the last one goes to PerfMonitor (nil on the first frame or a repeated
    /// timestamp), then LatencyProbe gets the frame's target vsync (the first frame after a tap's commit ends its sample).
    @discardableResult
    func frame(timestamp: CFTimeInterval, targetTimestamp: CFTimeInterval,
               context: @autoclosure () -> String) -> (dt: Double, over: Bool)? {
        var out: (dt: Double, over: Bool)?
        if last > 0, timestamp > last {
            let dt = timestamp - last
            frames += 1
            let over = perf.record(frameDT: dt)
            if over {
                hitches += 1
                if logs { Log.mark("board", String(format: "hitch %.1f ms %@", dt * 1000, context())) }
            }
            out = (dt, over)
        }
        last = timestamp
        latency.frame(targetTimestamp: targetTimestamp)
        return out
    }

    /// The top of the board's release handler (`boardInput`): LatencyProbe's first mark.
    func beginTap(touchTimestamp: TimeInterval) {
        latency.beginTap(touchTimestamp: touchTimestamp)
    }

    /// The engine's tap-latency line for a completed sample.
    func log(_ s: LatencyProbe.Sample) {
        guard logs else { return }
        Log.mark("perf", String(format: "tap L%d a%@ touch→handler %.2f handler→commit %.2f commit→vsync %.2f", tapLabel.level,
                                tapLabel.target, s.touchToHandlerMs, s.handlerToCommitMs ?? -1, s.commitToVsyncMs ?? -1))
    }
}
