// Debug harness: compiled into Debug and Measure only (`#if DEBUG || PC_MEASURE`), never into the Release (store) build.
// tools/harness_gate.py (CI) fails when a harness type is used outside that gate.
#if DEBUG || PC_MEASURE
import SwiftUI
import UIKit
import PathCore

// B1 (SPEC-architecture §5.12, §9.5, §10.4). BoardLab: `-pc.go boardlab -pc.lab <scenario> [-pc.labBoard <id>] [-pc.zoom Z]`
// drives the REAL app-lifetime engine (the one AppModel built and warmed up behind Loading) with scripted taps through
// `handleRelease` — the same release handler a finger reaches — or waits for real XCUITest touches. The lab is the board
// delegate (LabRules stand in for the session until C2 lands) and supplies the probe's session half. Each scenario
// writes Documents/lab-ready.json (+ its result) and Documents/lab-perf.json and prints `[PC][lab] <scenario> done`.
// B1 scenarios: idle, input, latency, exit, exit5, exitWaves, bump, hittest, zoomramp, intro, autoplay, kinematics,
// firstuse, soak. B2 adds the obstacle ones (BoardLab+Obstacles).

struct BoardLab: View {
    let app: AppModel
    @State private var controller: BoardLabController?

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            if let engine = app.board {
                BoardHost(board: engine)
                    .ignoresSafeArea()
            }
            if let c = controller, !app.args.capture {
                Text(verbatim: c.status)
                    .font(.system(size: 11, weight: .semibold, design: .monospaced))
                    .foregroundStyle(.black.opacity(0.55))
                    .padding(.horizontal, 8)
                    .padding(.bottom, 6)
                    .allowsHitTesting(false)
                    .accessibilityIdentifier("boardlab.status")
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("boardlab")
        .onAppear {
            guard controller == nil else { return }
            let c = BoardLabController(app: app)
            controller = c
            c.start()
        }
    }
}

@MainActor @Observable final class BoardLabController: BoardDelegate, BoardProbeSupplying {
    var status = "boardlab: starting"

    @ObservationIgnored let app: AppModel
    @ObservationIgnored let engine: BoardEngine?
    @ObservationIgnored let scenario: String
    @ObservationIgnored var boardName: String
    @ObservationIgnored var rules: LabRules?
    /// B2: the real rules (C2's LevelSession) for the obstacle scenarios and the soak.
    @ObservationIgnored var driver: LabDriver?
    @ObservationIgnored var wantWave = false
    @ObservationIgnored var waveStart: CFTimeInterval = 0
    @ObservationIgnored var clearWaveAt: Double?
    @ObservationIgnored var wantTransition = false
    @ObservationIgnored var transitionW: CFTimeInterval = 0
    @ObservationIgnored var transitionWWall: CFTimeInterval = 0
    @ObservationIgnored var transitionDoneAt: CFTimeInterval?
    @ObservationIgnored var timerStart: CFTimeInterval?
    @ObservationIgnored var releases = 0
    @ObservationIgnored var exitsFinished = 0
    @ObservationIgnored var contacts: [(ArrowID, CFTimeInterval)] = []
    @ObservationIgnored var bumpsFinished = 0
    @ObservationIgnored var introDone = false
    @ObservationIgnored var lastExitAt: CFTimeInterval?
    @ObservationIgnored var peakMovers = 0
    @ObservationIgnored var peakLayers = 0
    @ObservationIgnored private var started = false
    @ObservationIgnored var onFrame: ((CADisplayLink) -> Void)?
    /// The process footprint with no board loaded (the board's own share = footprint − this).
    @ObservationIgnored var baselineFootprintMB = 0.0

    init(app: AppModel) {
        self.app = app
        engine = app.board as? BoardEngine
        scenario = app.args.lab ?? "idle"
        boardName = app.args.labBoard ?? Self.defaultBoard(for: app.args.lab ?? "idle")
    }

    static func defaultBoard(for scenario: String) -> String {
        switch scenario {
        case "exit5", "exitWaves", "zoomramp", "kinematics", "soak": return "synth40"
        case "input": return "hit"
        default: return "L032"
        }
    }

    func start() {
        guard !started else { return }
        started = true
        guard let e = engine else {
            status = "boardlab: the board is not BOARD's engine (placeholder)"
            Log.error("boardlab", status)
            return
        }
        e.delegate = self
        e.frameHook = { [weak self] l in self?.frame(l) }
        Task { @MainActor [weak self] in
            guard let self else { return }
            await e.prepare()                                    // no-op after boot's warm-up
            await self.run(e)
        }
    }

    /// Loads a lab board into the engine at the current screen size, input enabled, no intro (unless asked).
    func loadBoard(_ name: String, intro: IntroStyle = .none) async -> Bool {
        guard let e = engine, let level = LabBoards.level(name, bundle: app.bundle) else {
            status = "boardlab: no board \(name)"
            Log.error("boardlab", status)
            return false
        }
        boardName = name
        if e.stage == nil || baselineFootprintMB == 0 {
            e.doClear()
            baselineFootprintMB = PerfMonitor.footprintMB()
        }
        rules = LabRules(level: level)
        driver = nil
        timerStart = nil
        let screen = BoardEngine.keyWindow()?.bounds.size ?? CGSize(width: 393, height: 852)
        e.inputEnabled = true
        e.load(StageSetup(level: level, screen: screen, config: e.config))
        e.playIntro(intro)
        // the lab measures only once the board is really on screen (a router may still be cross-fading to it) and every
        // arrow is attached (F1: big boards attach over a few frames)
        let end = CACurrentMediaTime() + 8
        while (e.container.window == nil || e.stage == nil || !e.pendingAttach.isEmpty) && CACurrentMediaTime() < end {
            await wait(1.0 / 60)
        }
        await e.frames(2)
        status = "boardlab \(scenario) · \(name) · \(level.arrows.count) arrows · pitch \(String(format: "%.2f", e.pitchOnScreen))"
        return true
    }

    // MARK: taps through the real release path

    /// A scripted release on an arrow (its safe tap point, else its middle cell even off screen).
    func tap(_ id: ArrowID) {
        guard let e = engine, let st = e.stage, let a = st.level.arrows.first(where: { $0.id == id }) else { return }
        let p = e.tapPoint(of: id) ?? e.contentToScreen(st.geo.centre(a.cells[a.cells.count / 2]))
        e.handleRelease(screenPoint: p, touchTimestamp: CACurrentMediaTime())
    }

    func frame(_ l: CADisplayLink) {
        guard let e = engine else { return }
        peakMovers = max(peakMovers, e.movers.count)
        onFrame?(l)
    }

    // MARK: BoardDelegate

    func boardFrame(timestamp: CFTimeInterval, targetTimestamp: CFTimeInterval) {}

    func boardReleased(arrow: ArrowID?, contentPoint: CGPoint, touchTimestamp: TimeInterval) {
        if let d = driver, let e = engine {
            releases += 1
            if arrow != nil, timerStart == nil { timerStart = CACurrentMediaTime() }
            let events = d.tap(arrow, at: CACurrentMediaTime())
            e.present(events)                                      // 1. the board (same run-loop turn, §8.1)
            if events.contains(where: { if case .exited = $0 { return true }; if case .bumped = $0 { return true }; return false }) {
                app.haptics.play(.tap)                             // 2. the haptic
            }
            return
        }
        guard let rules, let e = engine else { return }
        releases += 1
        if arrow != nil, timerStart == nil { timerStart = CACurrentMediaTime() }
        let events = rules.tap(arrow, at: CACurrentMediaTime())
        e.present(events)                                          // 1. the board (same run-loop turn, §8.1)
        if events.contains(where: { if case .exited = $0 { return true }; if case .bumped = $0 { return true }; return false }) {
            app.haptics.play(.tap)                                 // 2. the haptic
        }
    }

    func boardBeat(_ beat: BoardBeat) {
        if let d = driver, let e = engine {
            switch beat {
            case .bumpContact(let a):
                contacts.append((a, CACurrentMediaTime()))
                e.present(d.ack(.bumpContact(a)))
                app.haptics.play(.bumpContact)
            case .bumpFinished(let a):
                bumpsFinished += 1
                e.present(d.ack(.bumpFinished(a)))
            case .doorBurst(let x):
                e.present(d.ack(.doorBurst(x)))
                app.haptics.play(.burst)
            case .pipeBroken, .counterBroken:
                app.haptics.play(.burst)
            case .exitFinished:
                exitsFinished += 1
            case .introFinished:
                introDone = true
            case .lastExitLeftBoard:
                lastExitAt = CACurrentMediaTime()
                let now = e.roots.stage.convertTime(CACurrentMediaTime(), from: nil)
                if wantTransition, case .stageClear(let k) = d.session.phase, k + 1 < d.session.stages.count {
                    wantTransition = false
                    transitionW = now
                    transitionWWall = CACurrentMediaTime()
                    let screen = BoardEngine.keyWindow()?.bounds.size ?? CGSize(width: 393, height: 852)
                    e.playStageTransition(to: StageSetup(level: d.session.stages[k + 1], stage: k + 1, stages: d.session.stages.count,
                                                         seed: 1, screen: screen, config: e.config))
                } else if wantWave {
                    wantWave = false
                    waveStart = now
                    clearWaveAt = nil
                    e.playClearWave()
                }
            case .clearWaveFinished:
                clearWaveAt = (e.roots.stage.convertTime(CACurrentMediaTime(), from: nil) - waveStart)
            case .stageTransitionDone:
                transitionDoneAt = CACurrentMediaTime()
            default:
                break
            }
            return
        }
        guard let rules, let e = engine else { return }
        switch beat {
        case .bumpContact(let a):
            contacts.append((a, CACurrentMediaTime()))
            e.present(rules.contact(a))
            app.haptics.play(.bumpContact)
        case .bumpFinished(let a):
            bumpsFinished += 1
            rules.bumpFinished(a)
        case .exitFinished:
            exitsFinished += 1
        case .introFinished:
            introDone = true
        case .lastExitLeftBoard:
            lastExitAt = CACurrentMediaTime()
        default:
            break
        }
    }

    func boardZoomChanged(scale: CGFloat) {}

    // MARK: BoardProbeSupplying (the session's half, from the lab rules)

    func supplementProbe(_ p: inout BoardProbeData) {
        if let d = driver {
            let s = d.session.snapshot()
            p.phase = s.phase
            p.timerStarted = s.timerStarted
            p.hearts = s.hearts
            p.t = s.remaining
            p.combo = s.combo
            let free = Set(s.free.flatMap { $0 })
            p.arrows = p.arrows.map { a in
                var b = a
                b.free = free.contains(ArrowID(a.id))
                b.unit = d.session.board.unit(of: ArrowID(a.id)).map(\.raw)
                return b
            }
            return
        }
        guard let rules else { return }
        p.phase = timerStart == nil ? "ready" : "playing"
        p.timerStarted = timerStart != nil
        p.hearts = rules.hearts
        let limit = Double(rules.level.timerSeconds)
        p.t = timerStart.map { max(0, limit - (CACurrentMediaTime() - $0)) } ?? limit
        p.combo = rules.combo
        let free = Set(rules.freeArrows())
        p.arrows = p.arrows.map { a in
            var b = a
            b.free = free.contains(ArrowID(a.id))
            b.unit = rules.unit(ArrowID(a.id)).map(\.raw)
            return b
        }
    }

    // MARK: results

    func perfDict() -> [String: Any] {
        guard let e = engine else { return [:] }
        let s = app.perf.snapshot()
        let lat = app.latency
        func pct(_ v: [Double], _ p: Double) -> Double {
            let s = v.sorted()
            guard !s.isEmpty else { return 0 }
            return s[min(s.count - 1, Int((Double(s.count - 1) * p).rounded()))]
        }
        return ["frames": s.frames, "fps": round2(s.fps), "over20": s.over20, "max_ms": round2(s.max_ms),
                "p50_ms": round2(s.p50_ms), "p95_ms": round2(s.p95_ms), "p99_ms": round2(s.p99_ms),
                "footprint_mb": round2(s.footprint_mb), "baseline_footprint_mb": round2(baselineFootprintMB),
                "board_footprint_mb": round2(s.footprint_mb - baselineFootprintMB),
                "layers": e.layerCount(), "movers_peak": peakMovers,
                "layers_peak": peakLayers,
                "tap_handler_ms_p99": round2(pct(e.handlerMs, 0.99)), "tap_handler_ms_p50": round2(pct(e.handlerMs, 0.5)),
                "touch_to_handler_ms_p99": round2(lat.percentile(0.99) { $0.touchToHandlerMs }),
                "touch_to_commit_ms_p99": round2(lat.percentile(0.99) { s in s.handlerToCommitMs.map { $0 + s.touchToHandlerMs } }),
                "handler_to_commit_ms_p99": round2(lat.percentile(0.99, \.handlerToCommitMs)),
                "commit_to_vsync_ms_p50": round2(lat.percentile(0.5, \.commitToVsyncMs)),
                "commit_to_vsync_ms_max": round2(lat.percentile(1.0, \.commitToVsyncMs)),
                "latency_samples": lat.samples.count,
                "recogniser_delay_ms_p50": round2(pct(e.recogniserMs, 0.5)), "recogniser_delay_ms_p99": round2(pct(e.recogniserMs, 0.99)),
                "recogniser_delay_ms_max": round2(pct(e.recogniserMs, 1.0)),
                "event_delivery_ms_p50": round2(pct(e.deliveryMs, 0.5)), "event_delivery_ms_p99": round2(pct(e.deliveryMs, 0.99)),
                "touch_to_handler_ms_p50": round2(lat.percentile(0.5) { $0.touchToHandlerMs }),
                "r1_mode": app.args.raw["pc.r1"] == "fallback" ? "fallback (no require(toFail:))" : "require(toFail:) pan + pinch",
                "sprite_cache_mb": round2(e.sprites.footprintMB),
                "footprint_peak_mb": round2(s.footprint_peak_mb), "thermal_state": s.thermal,
                "over20_load": e.hitchesLoad, "over20_play": e.hitchesPlay, "last_load_ms": round2(e.lastLoadMs),
                "load_commits": e.loadCommitsSummary.mapValues { round2($0) },
                "painters": e.painters.keys.sorted()]
    }

    func round2(_ v: Double) -> Double { (v * 100).rounded() / 100 }

    /// Starts a measurement window (frames, latency, handler costs, peaks).
    func beginMeasure() {
        app.perf.reset()
        app.latency.resetSamples()
        engine?.resetHitchCounters()
        peakMovers = 0
        peakLayers = 0
    }

    /// Writes lab-perf.json and lab-ready.json (the ready file last) and prints the §9.3 mark.
    func finish(_ result: [String: Any]) {
        guard let e = engine else { return }
        let perf = perfDict()
        let uptime = ProcessInfo.processInfo.systemUptime
        var ready: [String: Any] = ["screen": "boardlab", "scenario": scenario, "board": boardName, "t": uptime,
                                    "uptime": uptime, "lang": "en", "frozen": e.frozen, "zoom": round2(Double(e.zoomScale)),
                                    "pitch": round2(Double(e.pitchOnScreen)), "perf": perf]
        for (k, v) in result { ready[k] = v }
        Self.writeJSON(perf, "lab-perf.json")
        Self.writeJSON(ready, "lab-ready.json")
        let over = perf["over20"] as? Int ?? -1
        let mx = perf["max_ms"] as? Double ?? -1
        status = "boardlab \(scenario) done · over20 \(over) · max \(mx) ms"
        if ExitProfile.on { Log.mark("boardlab", "exit profile: " + ExitProfile.report()) }
        Log.mark("lab", "\(scenario) done")
        Log.mark("boardlab", "\(scenario) \(boardName) over20 \(over) max_ms \(mx) result \(Self.compact(result))")
    }

    /// Serialises on the main actor (the dictionary is not Sendable) and writes OFF the main thread (D1a anomaly 3: the
    /// lab's own file writes made a 33 ms frame). The ready file is written last by `finish` (a serial queue keeps order).
    static func writeJSON(_ obj: [String: Any], _ name: String) {
        let url = BoardEngine.documents.appendingPathComponent(name)
        guard JSONSerialization.isValidJSONObject(obj),
              let d = try? JSONSerialization.data(withJSONObject: obj, options: [.prettyPrinted, .sortedKeys]) else {
            Log.error("boardlab", "\(name): not JSON-serialisable")
            return
        }
        writeQueue.async { try? d.write(to: url, options: .atomic) }
    }
    static let writeQueue = DispatchQueue(label: "boardlab.write", qos: .utility)

    static func compact(_ obj: [String: Any]) -> String {
        guard JSONSerialization.isValidJSONObject(obj),
              let d = try? JSONSerialization.data(withJSONObject: obj, options: [.sortedKeys]) else { return "{}" }
        let s = String(decoding: d, as: UTF8.self)
        return s.count > 900 ? String(s.prefix(900)) + "…" : s
    }

    func wait(_ seconds: Double) async {
        try? await Task.sleep(nanoseconds: UInt64(max(0, seconds) * 1_000_000_000))
    }
}
#endif
