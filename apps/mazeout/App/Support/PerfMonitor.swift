import Foundation
import Darwin

// WP0 → B1 (SPEC-architecture §3.2, §10.3 item 1). Working basics written by the LEAD (MF's PerfMonitor, adapted to the
// 20 ms hitch budget); BOARD owns it from B1 on. The board's single CADisplayLink feeds `record(frameDT:)` every
// presented frame (a missed vsync shows as ≥ 33 ms); readers take `snapshot()` for lab-perf.json, bench JSONs and the
// debug overlay (§9.6).

@MainActor final class PerfMonitor {
    /// Keys follow lab-perf.json (§9.5).
    struct Snapshot: Codable, Equatable {
        var frames: Int
        var fps: Double
        var p50_ms: Double
        var p95_ms: Double
        var p99_ms: Double
        var max_ms: Double
        var over20: Int
        var footprint_mb: Double
        /// D1a F3: the process's phys_footprint HIGH-WATER mark (task_vm_info.ledger_phys_footprint_peak) and the
        /// thermal state at the snapshot (nominal | fair | serious | critical).
        var footprint_peak_mb: Double = 0
        var thermal: String = ""
    }

    let hitchMs: Double
    private var samples: [Double]
    private var head = 0
    private var filled = 0
    private(set) var totalFrames = 0
    private(set) var framesOverBudget = 0
    private(set) var worstMs = 0.0

    init(capacity: Int = 600, hitchMs: Double = 20) {
        samples = Array(repeating: 0, count: max(capacity, 1))
        self.hitchMs = hitchMs
    }

    /// Records one presented frame's interval (seconds). Returns true when it exceeded the hitch budget.
    @discardableResult
    func record(frameDT: Double) -> Bool {
        samples[head] = frameDT
        head = (head + 1) % samples.count
        filled = min(filled + 1, samples.count)
        totalFrames += 1
        let ms = frameDT * 1000
        worstMs = max(worstMs, ms)
        if ms > hitchMs { framesOverBudget += 1; return true }
        return false
    }

    func reset() { head = 0; filled = 0; totalFrames = 0; framesOverBudget = 0; worstMs = 0 }

    /// Percentiles over the last `capacity` frames; counts since the last reset.
    func snapshot() -> Snapshot {
        let window = Array(samples.prefix(filled)).sorted()
        func pct(_ p: Double) -> Double {
            guard !window.isEmpty else { return 0 }
            return window[min(window.count - 1, Int((Double(window.count - 1) * p).rounded()))] * 1000
        }
        let mean = window.isEmpty ? 0 : window.reduce(0, +) / Double(window.count)
        return Snapshot(frames: totalFrames, fps: mean > 0 ? 1 / mean : 0, p50_ms: pct(0.5), p95_ms: pct(0.95),
                        p99_ms: pct(0.99), max_ms: worstMs, over20: framesOverBudget, footprint_mb: Self.footprintMB(),
                        footprint_peak_mb: Self.footprintPeakMB(), thermal: Self.thermalState())
    }

    /// The phys_footprint high-water mark of the process in MB (`task_vm_info.ledger_phys_footprint_peak`).
    nonisolated static func footprintPeakMB() -> Double {
        var info = task_vm_info_data_t()
        var count = mach_msg_type_number_t(MemoryLayout<task_vm_info_data_t>.size / MemoryLayout<natural_t>.size)
        let kr = withUnsafeMutablePointer(to: &info) {
            $0.withMemoryRebound(to: integer_t.self, capacity: Int(count)) {
                task_info(mach_task_self_, task_flavor_t(TASK_VM_INFO), $0, &count)
            }
        }
        return kr == KERN_SUCCESS ? Double(info.ledger_phys_footprint_peak) / 1_048_576 : 0
    }

    /// `ProcessInfo.thermalState` as a word (D1a F3: the 30 Hz episodes after the soak).
    nonisolated static func thermalState() -> String {
        switch ProcessInfo.processInfo.thermalState {
        case .nominal: return "nominal"
        case .fair: return "fair"
        case .serious: return "serious"
        case .critical: return "critical"
        @unknown default: return "unknown"
        }
    }

    /// Physical footprint in MB (`task_vm_info.phys_footprint`: what the memory budget and jetsam count).
    nonisolated static func footprintMB() -> Double {
        var info = task_vm_info_data_t()
        var count = mach_msg_type_number_t(MemoryLayout<task_vm_info_data_t>.size / MemoryLayout<natural_t>.size)
        let kr = withUnsafeMutablePointer(to: &info) {
            $0.withMemoryRebound(to: integer_t.self, capacity: Int(count)) {
                task_info(mach_task_self_, task_flavor_t(TASK_VM_INFO), $0, &count)
            }
        }
        return kr == KERN_SUCCESS ? Double(info.phys_footprint) / 1_048_576 : 0
    }
}
