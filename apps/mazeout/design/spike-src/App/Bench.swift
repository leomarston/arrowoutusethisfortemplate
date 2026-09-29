import UIKit

/// Measurement harness driven by launch arguments. Results go to the app's own tmp directory
/// (simulator: <data container>/tmp), never to the Mac's Downloads.
@MainActor
final class Bench {
    let board: BoardView
    let tun = Tunables.shared
    private var link: CADisplayLink?
    private var stamps: [CFTimeInterval] = []
    private var targets: [CFTimeInterval] = []
    private var recording = false
    private var firstFrameAfterBuild: Date?
    private var onTick: ((CFTimeInterval) -> Void)?
    var results: [String: Any] = [:]
    static let appInit = Date()

    init(board: BoardView) {
        self.board = board
        let l = CADisplayLink(target: self, selector: #selector(tick(_:)))
        l.add(to: .main, forMode: .common)
        link = l
    }

    @objc private func tick(_ l: CADisplayLink) {
        if firstFrameAfterBuild == nil, board.buildMs > 0 {
            firstFrameAfterBuild = Date()
            results["firstFrame_ms_since_process_start"] = firstFrameAfterBuild!.timeIntervalSince(Self.processStart()) * 1000
            results["appInit_ms_since_process_start"] = Self.appInit.timeIntervalSince(Self.processStart()) * 1000
        }
        if recording {
            stamps.append(l.timestamp)
            targets.append(l.targetTimestamp - l.timestamp)
        }
        onTick?(l.timestamp)
        if Self.uitest, l.timestamp - lastRefresh > 0.25 { lastRefresh = l.timestamp; onRefresh?() }
    }
    static let uitest = UserDefaults.standard.bool(forKey: "pc.uitest")
    private var lastRefresh: CFTimeInterval = 0
    var onRefresh: (() -> Void)?

    // MARK: recording

    private func startRecording() { stamps = []; targets = []; recording = true }
    private func stopRecording() -> [String: Any] {
        recording = false
        return Self.stats(stamps, budgets: targets)
    }

    static func stats(_ ts: [CFTimeInterval], budgets: [CFTimeInterval]) -> [String: Any] {
        guard ts.count > 2 else { return ["frames": ts.count] }
        let d = zip(ts.dropFirst(), ts).map { ($0 - $1) * 1000 }
        let s = d.sorted()
        func pct(_ p: Double) -> Double { s[min(s.count - 1, Int(Double(s.count - 1) * p))] }
        let edges: [Double] = [12, 18, 20, 25, 34, 50]
        var hist = [Int](repeating: 0, count: edges.count + 1)
        for v in d { hist[edges.firstIndex(where: { v < $0 }) ?? edges.count] += 1 }
        let names = ["<12", "12-18", "18-20", "20-25", "25-34", "34-50", ">=50"]
        return [
            "frames": d.count,
            "span_s": (ts.last! - ts.first!),
            "mean_ms": d.reduce(0, +) / Double(d.count),
            "p50_ms": pct(0.5), "p95_ms": pct(0.95), "p99_ms": pct(0.99), "max_ms": s.last!,
            "over20ms": d.filter { $0 > 20 }.count,
            "over34ms": d.filter { $0 > 34 }.count,
            "histogram_ms": Dictionary(uniqueKeysWithValues: zip(names, hist)),
            "budget_ms": (budgets.reduce(0, +) / Double(max(budgets.count, 1))) * 1000,
        ]
    }

    // MARK: environment

    static func processStart() -> Date {
        var info = kinfo_proc()
        var size = MemoryLayout<kinfo_proc>.stride
        var mib: [Int32] = [CTL_KERN, KERN_PROC, KERN_PROC_PID, getpid()]
        sysctl(&mib, u_int(mib.count), &info, &size, nil, 0)
        let tv = info.kp_proc.p_starttime
        return Date(timeIntervalSince1970: Double(tv.tv_sec) + Double(tv.tv_usec) / 1e6)
    }

    static func footprintMB() -> Double {
        var info = task_vm_info_data_t()
        var count = mach_msg_type_number_t(MemoryLayout<task_vm_info_data_t>.size / MemoryLayout<natural_t>.size)
        let kr = withUnsafeMutablePointer(to: &info) {
            $0.withMemoryRebound(to: integer_t.self, capacity: Int(count)) {
                task_info(mach_task_self_, task_flavor_t(TASK_VM_INFO), $0, &count)
            }
        }
        return kr == KERN_SUCCESS ? Double(info.phys_footprint) / 1_048_576 : -1
    }

    func write(_ name: String) {
        results["scenario"] = tun.scenario
        results["level"] = board.level.source ?? "\(board.level.id)"
        results["arrows"] = board.level.arrows.count
        results["cells"] = board.level.cellCount
        results["grid"] = "\(board.level.cols)x\(board.level.rows)"
        results["pitch_pt"] = board.layout.pitch
        results["zoom"] = board.zoom
        results["trail"] = tun.trail.rawValue
        results["stars"] = tun.stars
        results["buildMs"] = board.buildMs
        results["maxFPS"] = UIScreen.main.maximumFramesPerSecond
        results["footprintMB_now"] = Self.footprintMB()
        results["layers_now"] = board.layerCount
        let url = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent(name)
        if let data = try? JSONSerialization.data(withJSONObject: results, options: [.prettyPrinted, .sortedKeys]) {
            try? data.write(to: url)
        }
        NSLog("SPIKE wrote %@", url.path)
    }

    func ready(_ tag: String, info: [String: Any] = [:]) {
        results["ready_" + tag] = info
        write("spike-\(tun.scenario).json")
        let url = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("ready-\(tag).txt")
        try? "ok".write(to: url, atomically: true, encoding: .utf8)
    }

    private func after(_ s: Double, _ f: @escaping () -> Void) {
        DispatchQueue.main.asyncAfter(deadline: .now() + s, execute: f)
    }

    // MARK: picking

    private var boardCentre: CGPoint { CGPoint(x: board.layout.boardRect.midX, y: board.layout.boardRect.midY) }

    private func freeArrows() -> [Int] {
        (0..<board.level.arrows.count).filter { board.state.isFree($0) && board.movers[$0] == nil && board.nodes[$0] != nil }
    }

    private func nearest(_ ids: [Int], to p: CGPoint) -> [Int] {
        ids.sorted {
            let a = board.nodes[$0]!.geo.headCentre, b = board.nodes[$1]!.geo.headCentre
            return hypot(a.x - p.x, a.y - p.y) < hypot(b.x - p.x, b.y - p.y)
        }
    }

    // MARK: scenarios

    func run() {
        results["footprintMB_afterBuild"] = Self.footprintMB()
        results["layers_afterBuild"] = board.layerCount
        results["validate"] = BoardState.validate(board.level)
        let g = BoardState.greedy(board.level)
        results["greedy_stuck"] = g.stuck.count
        results["greedy_rounds"] = g.rounds
        switch tun.scenario {
        case "exit5": exit5()
        case "trail": trail()
        case "bump": bump()
        case "crisp": crisp()
        case "zoomramp": zoomRamp()
        case "hittest": hitTest()
        case "autoplay": autoplay()
        case "idle": after(1.5) { self.ready("idle") }
        default:
            if tun.initialZoom != 1 { board.setZoom(tun.initialZoom, centredOn: boardCentre) }
            after(1.0) { self.write("spike-none.json") }
        }
    }

    /// Waves of `perWave` simultaneous exits near an anchor, at the launch zoom; frame times before/during.
    private func exit5() {
        guard let anchorId = nearest(freeArrows(), to: boardCentre).first else { return }
        let anchor = board.nodes[anchorId]!.geo.headCentre
        board.setZoom(tun.initialZoom, centredOn: anchor)
        after(1.0) {
            self.startRecording()
            self.after(1.0) {
                self.results["idle"] = self.stopRecording()
                self.results["footprintMB_beforeWaves"] = Self.footprintMB()
                self.startRecording()
                var costs: [Double] = [], counts: [Int] = [], peakMovers = 0, peakLayers = 0
                for w in 0..<self.tun.waves {
                    self.after(Double(w) * self.tun.waveGap) {
                        let pick = Array(self.nearest(self.freeArrows(), to: anchor).prefix(self.tun.perWave))
                        let t0 = CACurrentMediaTime()
                        for i in pick { self.board.tapArrow(i) }
                        costs.append((CACurrentMediaTime() - t0) * 1000)
                        counts.append(pick.count)
                        peakMovers = max(peakMovers, self.board.movers.count)
                        self.after(0.25) { peakLayers = max(peakLayers, self.board.layerCount) }
                    }
                }
                self.after(self.tun.measureSeconds) {
                    self.results["active"] = self.stopRecording()
                    self.results["waveStartCost_ms"] = costs
                    self.results["waveCounts"] = counts
                    self.results["peakMovers"] = peakMovers
                    self.results["peakLayers"] = peakLayers
                    self.results["footprintMB_afterWaves"] = Self.footprintMB()
                    self.ready("exit5")
                }
            }
        }
    }

    /// The longest free snake (most bends) near the centre exits; freeze mid-exit for the trail screenshot.
    private func trail() {
        let free = freeArrows()
        let scored = free.map { i -> (Int, Int) in
            let g = board.nodes[i]!.geo
            let d = hypot(g.headCentre.x - boardCentre.x, g.headCentre.y - boardCentre.y) / board.layout.pitch
            return (i, g.cellCount * 3 + g.corners.count * 4 - Int(d))
        }
        guard let pick = scored.max(by: { $0.1 < $1.1 })?.0 else { return }
        let g = board.nodes[pick]!.geo
        board.setZoom(tun.initialZoom, centredOn: g.point(along: g.bodyLength / 2))
        after(0.8) {
            self.board.tapArrow(pick)
            if self.tun.freezeAfter >= 0 {
                self.after(self.tun.freezeAfter) {
                    self.board.freeze()
                    self.after(0.3) {
                        self.ready("trail", info: ["arrow": pick, "cells": g.cellCount, "corners": g.corners.count])
                    }
                }
            } else {
                let wait = UserDefaults.standard.string(forKey: "pc.shotAfter").flatMap(Double.init) ?? 3
                self.after(wait) { self.ready("trail", info: ["arrow": pick]) }
            }
        }
    }

    private func bump() {
        let blocked = (0..<board.level.arrows.count).filter { !board.state.isFree($0) }
        let withGap = blocked.compactMap { i -> (Int, Int)? in
            guard let b = board.state.firstBlocker(of: i) else { return nil }
            return (i, b.gap)
        }
        let minGap = UserDefaults.standard.string(forKey: "pc.minGap").flatMap(Int.init) ?? 1
        let pool = withGap.filter { $0.1 >= minGap }.map(\.0)
        results["bumpCandidates"] = ["gap>=\(minGap)": pool.count, "all": withGap.count]
        guard let pick = nearest(pool.isEmpty ? withGap.map(\.0) : pool, to: boardCentre).first else {
            ready("bump", info: ["error": "no blocked arrow"]); return
        }
        let g = board.nodes[pick]!.geo
        board.setZoom(tun.initialZoom, centredOn: g.headCentre)
        after(0.8) {
            let hearts0 = self.board.hearts
            self.board.tapArrow(pick)
            let contact = g.contactTravel(gap: self.board.state.firstBlocker(of: pick)!.gap)
            self.results["bump"] = ["arrow": pick, "contactTravel_pt": contact,
                                    "contactTime_s": self.board.profile.time(toReach: contact)]
            if self.tun.freezeAfter >= 0 {
                self.after(self.tun.freezeAfter) {
                    self.board.freeze()
                    self.after(0.3) { self.ready("bump", info: ["hearts0": hearts0, "hearts": self.board.hearts]) }
                }
            } else {
                self.after(1.5) { self.ready("bump", info: ["hearts0": hearts0, "hearts": self.board.hearts]) }
            }
        }
    }

    private func crisp() {
        board.setZoom(tun.initialZoom, centredOn: boardCentre)
        after(1.0) { self.ready("crisp", info: ["zoom": self.board.zoom]) }
    }

    /// Programmatic pinch proxy: zoomScale driven every frame 1 -> max -> min -> 1 over 6 s.
    private func zoomRamp() {
        after(1.0) {
            self.startRecording()
            let t0 = CACurrentMediaTime()
            let zmax = self.tun.zoomMax, zmin = self.tun.zoomMin
            self.onTick = { _ in
                let t = CACurrentMediaTime() - t0
                func ease(_ x: Double) -> CGFloat { CGFloat(0.5 - 0.5 * cos(.pi * min(max(x, 0), 1))) }
                let z: CGFloat
                if t < 2.5 { z = 1 + (zmax - 1) * ease(t / 2.5) }
                else if t < 5 { z = zmax + (zmin - zmax) * ease((t - 2.5) / 2.5) }
                else { z = zmin + (1 - zmin) * ease((t - 5) / 1) }
                self.board.setZoom(z, centredOn: self.boardCentre)
                if t > 6.05 {
                    self.onTick = nil
                    self.results["zoomRamp"] = self.stopRecording()
                    self.ready("zoomramp")
                }
            }
        }
    }

    /// Correctness + cost of the grid-maths hit test.
    private func hitTest() {
        var rng = SplitMix64(seed: 99)
        let p = board.layout.pitch
        var total = 0, wrong = 0
        for (i, a) in board.level.arrows.enumerated() {
            for c in a.cells {
                let o = board.layout.centre(c)
                let q = CGPoint(x: o.x + CGFloat.random(in: -0.45...0.45, using: &rng) * p,
                                y: o.y + CGFloat.random(in: -0.45...0.45, using: &rng) * p)
                total += 1
                if board.arrow(at: q) != i { wrong += 1 }
            }
        }
        let r = board.layout.boardRect
        let pts = (0..<100_000).map { _ in
            CGPoint(x: CGFloat.random(in: r.minX...r.maxX, using: &rng), y: CGFloat.random(in: r.minY...r.maxY, using: &rng))
        }
        let t0 = CACurrentMediaTime()
        var hits = 0
        for q in pts where board.arrow(at: q) != nil { hits += 1 }
        let us = (CACurrentMediaTime() - t0) / Double(pts.count) * 1e6
        results["hittest"] = ["cellPoints": total, "wrong": wrong, "random100k_us_per_query": us, "randomHits": hits]
        ready("hittest")
    }

    /// Plays the greedy solution (every tap must exit, the board must clear, no heart lost) while recording.
    private func autoplay() {
        let order = BoardState.greedy(board.level).order
        let gap = UserDefaults.standard.string(forKey: "pc.tapGap").flatMap(Double.init) ?? 0.12
        if tun.initialZoom != 1 { board.setZoom(tun.initialZoom, centredOn: boardCentre) }
        after(1.0) {
            self.startRecording()
            var bumps = 0, peak = 0, k = 0
            let t0 = CACurrentMediaTime()
            @MainActor func step() {
                guard k < order.count else {
                    self.after(2.0) {
                        self.results["autoplay"] = [
                            "taps": order.count, "bumps": bumps, "cleared": self.board.state.aliveCount == 0,
                            "hearts": self.board.hearts, "peakMovers": peak, "seconds": CACurrentMediaTime() - t0,
                            "moversLeft": self.board.movers.count,
                        ]
                        self.results["frames"] = self.stopRecording()
                        self.ready("autoplay")
                    }
                    return
                }
                let out = self.board.tapArrow(order[k])
                if case .blocked = out { bumps += 1 }
                if case .exitsGroup = out, let f = UserDefaults.standard.string(forKey: "pc.freezeOnGroup").flatMap(Double.init) {
                    self.after(f) {
                        self.board.freeze()
                        self.after(0.3) { self.ready("autoplay", info: ["frozenAfterGroupTap": k]) }
                    }
                    return
                }
                peak = max(peak, self.board.movers.count)
                k += 1
                self.after(gap, step)
            }
            step()
        }
    }
}
