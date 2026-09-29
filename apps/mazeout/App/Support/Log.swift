import Foundation
import os

// ◆ CONTRACT (SPEC-architecture §3.5, §9.3). Written by the LEAD in WP0 and FROZEN: any change goes through the
// orchestrator (build/wp0/frozen-contracts.sha256).
// The log grammar tools/bench/bench.py and tools/capture/capture.py parse:
//     "<systemUptime> [PC][<category>] <message>"           (Log.mark / Log.info)
//     "<systemUptime> [PC][<category>][ERROR] <message>"    (Log.error)
// to stdout (tools/run.sh captures it into build/run-<slot>.log) and to os.Logger, subsystem com.manycode.arrowout.
// The bench MARKS (§9.3 table) must be printed EXACTLY, e.g. `Log.mark("board", "ready L32: 53 arrows")`.

enum Log {
    static let subsystem = "com.manycode.arrowout"
    /// Frame-budget signposts (§10.3): `let s = Log.signposter.beginInterval("tap"); …; Log.signposter.endInterval("tap", s)`.
    static let signposter = OSSignposter(subsystem: subsystem, category: "frame")

    private static let lock = NSLock()
    nonisolated(unsafe) private static var loggers: [String: Logger] = [:]

    static func logger(_ category: String) -> Logger {
        lock.lock(); defer { lock.unlock() }
        if let l = loggers[category] { return l }
        let l = Logger(subsystem: subsystem, category: category)
        loggers[category] = l
        return l
    }

    /// One `[PC][<category>]` line (stdout + os.Logger).
    static func mark(_ category: String, _ message: String) {
        logger(category).info("\(message, privacy: .public)")
        emit("[PC][\(category)] \(message)")
    }

    /// Same as `mark` (the name MF-derived code uses).
    static func info(_ category: String, _ message: String) { mark(category, message) }

    /// One `[PC][<category>][ERROR]` line (stdout + os.Logger error).
    static func error(_ category: String, _ message: String) {
        logger(category).error("\(message, privacy: .public)")
        emit("[PC][\(category)][ERROR] \(message)")
    }

    /// os.Logger only (not in the run log).
    static func debug(_ category: String, _ message: String) {
        logger(category).debug("\(message, privacy: .public)")
    }

    private static func emit(_ line: String) {
        let stamp = String(format: "%.3f", ProcessInfo.processInfo.systemUptime)
        lock.lock(); defer { lock.unlock() }
        print("\(stamp) \(line)")
        fflush(stdout)
    }
}
