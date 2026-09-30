// Debug harness: compiled into Debug and Measure only (`#if DEBUG || PC_MEASURE`), never into the Release (store) build.
// tools/harness_gate.py (CI) fails when a harness type is used outside that gate.
#if DEBUG || PC_MEASURE
import UIKit
import PathCore

// B2 (SPEC-architecture §5.12 BoardLab obstacle scenarios, §9.5, §10.4; §12.2 B2 acceptance). The obstacle scenarios run
// on the REAL rules: a `LabDriver` wraps C2's LevelSession (the bundle's Tuning/rules.json) exactly as GAME's controller
// will (tap → events → board.present in the same turn; the board's beats → session.ack → board.present), minus the
// clock (the lab never times out) and the fail chain (a hearts-out offer is accepted at once so a soak keeps playing).
// Scenarios: door, pipe, box, tape, elevator, corner, clearwave, stageGap, firstfx (+ the soak, which now runs on the
// driver with the rainbow painter). Each writes lab-ready.json / lab-perf.json and prints its §9.3 marks; the timing
// facts the acceptance asks for are logged by the engine (`doorBurst … planned … measured`, `pipeBroken … (leave + 0.05)`,
// `stage transition … swap at W+0.70`, `stageTransitionDone …`).
// `-pc.freezeAt <sequence>@<t>` freezes t seconds after the scenario's anchor: keyFlight / doorBurst (the key tap),
// pipeBreak (the breaking pass's tap), boxBreak (the breaking tap), tape / exit (the bundle tap), elevator (the last
// platform tap), corner (the corner exit's tap), clearWave / stageGap (W: the last exit left the board).

@MainActor final class LabDriver {
    let session: LevelSession
    var level: LevelSpec { session.level }
    private(set) var offersAccepted = 0

    init(stages: [LevelSpec], bundle: Bundle) {
        let levels = stages.map(\.level)
        let plan = SessionPlan(id: "lab", levels: levels, reward: 0, stageGap: 0.7)
        session = LevelSession(plan: plan, stages: stages, setup: AttemptSetup(levels: levels, attemptIndex: 1, seed: 1),
                               rules: BoardEngine.bundleRules(bundle))
        _ = session.start()
    }

    /// A session call's events, with a hearts-out offer accepted at once (the lab keeps playing).
    func settle(_ ev: [SessionEvent]) -> [SessionEvent] {
        var out = ev
        for e in ev {
            if case .offer = e { offersAccepted += 1; out += session.acceptContinue() }
        }
        return out
    }

    func tap(_ id: ArrowID?, at t: TimeInterval) -> [SessionEvent] { settle(session.tap(id, at: t)) }
    func ack(_ a: SessionAck) -> [SessionEvent] { settle(session.ack(a)) }

    /// Units that would exit now (first member = the tap target).
    func freeUnits() -> [[ArrowID]] { session.board.freeUnits() }

    /// Live arrows that would bump now.
    func blocked() -> [ArrowID] {
        let free = Set(freeUnits().flatMap { $0 })
        return session.board.live.filter { !free.contains($0) && !session.board.isBumping($0) }
    }

    /// The exit plan a tap on `id` would produce (nil when it would not exit).
    func plan(_ id: ArrowID) -> ExitPlan? {
        if case .exit(let p) = session.board.resolve(tap: id) { return p }
        return nil
    }
}

extension BoardLabController {
    // MARK: loading on the real rules

    /// Loads `name` (or the stages) with a LabDriver as the rules; intro none; input on.
    func loadDriven(_ name: String, stages extra: [String] = []) async -> Bool {
        guard let e = engine, let level = LabBoards.level(name, bundle: app.bundle) else {
            status = "boardlab: no board \(name)"
            Log.error("boardlab", status)
            return false
        }
        let more = extra.compactMap { LabBoards.level($0, bundle: app.bundle) }
        boardName = name
        if baselineFootprintMB == 0 { baselineFootprintMB = PerfMonitor.footprintMB() }
        rules = nil
        driver = LabDriver(stages: [level] + more, bundle: app.bundle)
        timerStart = nil
        let screen = BoardEngine.keyWindow()?.bounds.size ?? CGSize(width: 393, height: 852)
        e.inputEnabled = true
        e.load(StageSetup(level: level, stage: 0, stages: 1 + more.count, seed: 1, screen: screen, config: e.config))
        e.playIntro(.none)
        let end = CACurrentMediaTime() + 8
        while (e.container.window == nil || e.stage == nil || !e.pendingAttach.isEmpty) && CACurrentMediaTime() < end {
            await wait(1.0 / 60)
        }
        await e.frames(2)
        if let d = driver { e.present(d.ack(.introFinished)) }
        status = "boardlab \(scenario) · \(name) · \(level.arrows.count) arrows · pitch \(String(format: "%.2f", e.pitchOnScreen))"
        return true
    }

    /// A scripted release on an arrow through the real handler (its safe tap point, else its middle cell).
    func tapDriven(_ id: ArrowID) {
        guard let e = engine, let st = e.stage, let a = st.level.arrows.first(where: { $0.id == id }) else { return }
        let p = e.tapPoint(of: id) ?? e.contentToScreen(st.geo.centre(a.cells[a.cells.count / 2]))
        e.handleRelease(screenPoint: p, touchTimestamp: CACurrentMediaTime())
    }

    /// Free units whose plan contains a beat matching `want`, nearest-first to the view centre.
    func freeWithBeat(_ want: (PlanBeat) -> Bool) -> ArrowID? {
        guard let d = driver else { return nil }
        for u in d.freeUnits() {
            if let p = d.plan(u[0]), p.beats.contains(where: want) { return u[0] }
        }
        return nil
    }

    func anyFree() -> ArrowID? { driver?.freeUnits().first?.first }

    /// Plays the solver's order (one tap every `rate` s) until a free unit's plan has a beat matching `want`; returns it.
    func progress(until want: (PlanBeat) -> Bool, maxTaps: Int = 80, rate: Double = 0.18) async -> ArrowID? {
        for _ in 0..<maxTaps {
            if let id = freeWithBeat(want) { return id }
            guard let d = driver, let u = d.session.hint() else { return nil }
            tapDriven(u[0])
            await wait(rate)
        }
        return freeWithBeat(want)
    }

    /// Freezes if `-pc.freezeAt <seq>@t` names this sequence (anchor = now); returns true when frozen.
    func freezeIf(_ seqs: [String], _ e: BoardEngine, stageStart s0: CFTimeInterval, fxStart f0: CFTimeInterval) async -> Bool {
        guard let f = app.args.freezeAt, seqs.contains(f.sequence) else { return false }
        await waitStage(e, until: s0 + f.t)
        e.freezeSequence(stageStart: s0, fxStart: f0, at: f.t)
        await e.frames(6)
        return true
    }

    /// Waits (real time) until the stage clock passes `t` (so later beats of the sequence have been processed).
    func waitStage(_ e: BoardEngine, until t: CFTimeInterval) async {
        let end = CACurrentMediaTime() + 10
        while e.roots.stage.convertTime(CACurrentMediaTime(), from: nil) < t - 0.03 && CACurrentMediaTime() < end {
            await wait(1.0 / 120)
        }
    }

    func runObstacleScenario(_ e: BoardEngine) async -> Bool {
        switch scenario {
        case "door": await runDoor(e)
        case "pipe": await runPipe(e)
        case "box": await runBox(e)
        case "tape": await runTape(e)
        case "elevator": await runElevator(e)
        case "corner": await runCorner(e)
        case "clearwave": await runClearWaveScenario(e)
        case "stageGap": await runStageGap(e)
        case "firstfx": await runFirstFX(e)
        case "hint": await runHint(e)
        case "reloads": await runReloads(e)
        default: return false
        }
        return true
    }

    // MARK: door + key (MA §3.5.2: burst at tap + 1.14 s for the measured geometry)

    func runDoor(_ e: BoardEngine) async {
        guard await loadDriven(app.args.labBoard ?? "L033") else { return finish(["error": "board"]) }
        await e.frames(20)
        beginMeasure()
        e.lastDoorBursts = []
        var flights: [[String: Any]] = []
        for k in 0..<(rawInt("keys") ?? 2) {
            guard let id = await progress(until: { if case .keyReleased = $0 { return true }; return false }) else { break }
            await waitUntil(2) { e.movers.isEmpty }
            let s0 = e.roots.stage.convertTime(CACurrentMediaTime(), from: nil)
            let f0 = e.container.screenFX.localNow
            let before = e.lastDoorBursts.count
            tapDriven(id)
            if k == 0, await freezeIf(["keyFlight", "doorBurst"], e, stageStart: s0, fxStart: f0) {
                return finish(["arrow": id.raw, "frozenAt": app.args.freezeAt?.t ?? 0])
            }
            await waitUntil(3) { e.lastDoorBursts.count > before }
            await wait(0.5)
            if let b = e.lastDoorBursts.last {
                flights.append(["arrow": id.raw, "door": b.0.raw, "planned_s": round3(b.1), "measured_s": round3(b.2),
                                "error_frames": round2((b.2 - b.1) * 60)])
            }
        }
        let doors = e.obstacles.doors.values.map { ["id": $0.id.raw, "state": $0.state] }
        finish(["flights": flights, "doors": doors, "hidden": e.probe().hidden.count])
    }

    // MARK: pipe (MA §3.5.3: the count swaps at leave, the shatter at leave + 0.05 s)

    func runPipe(_ e: BoardEngine) async {
        guard await loadDriven(app.args.labBoard ?? "L021") else { return finish(["error": "board"]) }
        await e.frames(20)
        beginMeasure()
        e.lastPipeBreaks = []
        var passes: [[String: Any]] = []
        for _ in 0..<12 {
            guard let id = await progress(until: { if case .enterTube = $0 { return true }; return false }),
                  let plan = driver?.plan(id) else { break }
            await waitUntil(2) { e.movers.isEmpty }
            var leave = -1.0, count = -1, breaks = false
            for b in plan.beats {
                if case let .leaveTube(_, _, s) = b { leave = e.kinematics.time(toTravel: s) }
                if case let .pipeCount(_, n, _) = b { count = n }
                if case .pipeBreak = b { breaks = true }
            }
            let s0 = e.roots.stage.convertTime(CACurrentMediaTime(), from: nil)
            let f0 = e.container.screenFX.localNow
            tapDriven(id)
            if breaks, await freezeIf(["pipeBreak"], e, stageStart: s0, fxStart: f0) {
                return finish(["arrow": id.raw, "frozenAt": app.args.freezeAt?.t ?? 0, "leave_s": round3(leave)])
            }
            passes.append(["arrow": id.raw, "leave_s": round3(leave), "remaining": count, "breaks": breaks])
            await wait(breaks ? 1.8 : 0.9)
            if breaks { break }
        }
        let breaks = e.lastPipeBreaks.map { ["pipe": $0.0.raw, "leave_s": round3($0.1), "planned_s": round3($0.2),
                                             "measured_s": round3($0.3), "after_leave_s": round3($0.3 - $0.1)] }
        finish(["passes": passes, "breaks": breaks, "probe": e.probe().obstacles.map { ["id": $0.id, "n": $0.n ?? -1, "state": $0.state ?? ""] }])
    }

    // MARK: box (MA §3.5.4: every box counts down together on the tap frame; the break shows the dots underneath)

    func runBox(_ e: BoardEngine) async {
        guard await loadDriven(app.args.labBoard ?? "L011") else { return finish(["error": "board"]) }
        await e.frames(20)
        beginMeasure()
        var steps: [[String: Any]] = []
        for _ in 0..<60 {
            guard let d = driver, let id = anyFree() else { break }
            let breaking = d.plan(id)?.beats.contains { if case .counterBreak = $0 { return true }; return false } ?? false
            let s0 = e.roots.stage.convertTime(CACurrentMediaTime(), from: nil)
            let f0 = e.container.screenFX.localNow
            tapDriven(id)
            if breaking, await freezeIf(["boxBreak"], e, stageStart: s0, fxStart: f0) {
                return finish(["arrow": id.raw, "frozenAt": app.args.freezeAt?.t ?? 0])
            }
            let counters = e.obstacles.boxes.values.sorted { $0.id < $1.id }.map { "\($0.id.raw)=\($0.broken ? 0 : ($0.remaining ?? -1))" }
            steps.append(["arrow": id.raw, "counters": counters.joined(separator: " "), "breaks": breaking])
            await wait(breaking ? 1.0 : 0.25)
            if e.obstacles.boxes.values.allSatisfy(\.broken) { break }
        }
        await wait(0.8)
        finish(["steps": steps, "revealedLive": e.probe().arrows.count, "dots": e.dots.dotCount])
    }

    // MARK: tape carry, elevator, corner

    func runTape(_ e: BoardEngine) async {
        guard await loadDriven(app.args.labBoard ?? "L007") else { return finish(["error": "board"]) }
        await e.frames(20)
        guard let d = driver, let u = d.freeUnits().first(where: { $0.count > 1 }) else { return finish(["error": "no free bundle"]) }
        let s0 = e.roots.stage.convertTime(CACurrentMediaTime(), from: nil)
        let f0 = e.container.screenFX.localNow
        beginMeasure()
        tapDriven(u[0])
        if await freezeIf(["tape", "exit"], e, stageStart: s0, fxStart: f0) {
            return finish(["unit": u.map(\.raw), "frozenAt": app.args.freezeAt?.t ?? 0])
        }
        await waitUntil(4) { e.movers.isEmpty }
        finish(["unit": u.map(\.raw), "tapesLeft": e.tapes.count])
    }

    func runElevator(_ e: BoardEngine) async {
        guard await loadDriven(app.args.labBoard ?? "L031") else { return finish(["error": "board"]) }
        await e.frames(20)
        beginMeasure()
        var taps: [Int] = []
        for _ in 0..<60 {
            guard let d = driver else { break }
            let free = d.freeUnits()
            // prefer the platform's own arrows, then anything that frees them
            let platform = Set(e.stage?.level.obstacles.filter { $0.kind == .elevator }.flatMap(\.arrows) ?? [])
            guard let pick = free.first(where: { platform.contains($0[0]) })?.first ?? free.first?.first else { break }
            let empties = d.plan(pick)?.beats.contains { if case .elevatorEmptied = $0 { return true }; return false } ?? false
            let s0 = e.roots.stage.convertTime(CACurrentMediaTime(), from: nil)
            let f0 = e.container.screenFX.localNow
            tapDriven(pick)
            taps.append(pick.raw)
            if empties {
                if await freezeIf(["elevator"], e, stageStart: s0, fxStart: f0) {
                    return finish(["taps": taps, "frozenAt": app.args.freezeAt?.t ?? 0])
                }
                await wait(1.2)
                break
            }
            await wait(0.3)
        }
        let active = e.obstacles.elevators.values.map { ["id": $0.id.raw, "active": $0.active] }
        finish(["taps": taps, "elevators": active, "live": e.probe().arrows.count])
    }

    func runCorner(_ e: BoardEngine) async {
        guard await loadDriven("corner") else { return finish(["error": "board"]) }
        await e.frames(20)
        beginMeasure()
        let s0 = e.roots.stage.convertTime(CACurrentMediaTime(), from: nil)
        let f0 = e.container.screenFX.localNow
        let plan = driver?.plan(ArrowID(0))
        tapDriven(ArrowID(0))
        if await freezeIf(["corner", "exit"], e, stageStart: s0, fxStart: f0) {
            return finish(["frozenAt": app.args.freezeAt?.t ?? 0])
        }
        await waitUntil(4) { e.movers.isEmpty }
        let beats = plan?.beats.map { "\($0)" } ?? []
        finish(["beats": beats, "cells": plan?.paths[ArrowID(0)]?.cells.map { [$0.c, $0.r] } ?? []])
    }

    // MARK: the clear wave and the Levels 1-4 stage gap (W-anchored)

    /// Plays the stage out through the real handler (the solver's order) and returns the stage-local time of W.
    func clearStage(_ e: BoardEngine, rate: Double = 0.12) async -> CFTimeInterval? {
        lastExitAt = nil
        var wStage: CFTimeInterval?
        let hook: (CADisplayLink) -> Void = { [weak self] _ in
            if self?.lastExitAt != nil, wStage == nil { wStage = e.roots.stage.convertTime(CACurrentMediaTime(), from: nil) }
        }
        onFrame = hook
        for _ in 0..<400 {
            guard let d = driver, lastExitAt == nil else { break }
            guard let u = d.session.hint() else {
                if d.session.board.isCleared { break }
                await wait(0.1); continue
            }
            tapDriven(u[0])
            await wait(rate)
        }
        await waitUntil(5) { self.lastExitAt != nil }
        onFrame = nil
        return wStage ?? (lastExitAt != nil ? e.roots.stage.convertTime(CACurrentMediaTime(), from: nil) : nil)
    }

    func runClearWaveScenario(_ e: BoardEngine) async {
        guard await loadDriven(app.args.labBoard ?? "L001") else { return finish(["error": "board"]) }
        await e.frames(20)
        beginMeasure()
        wantWave = true
        guard let w = await clearStage(e) else { return finish(["error": "not cleared"]) }
        if let f = app.args.freezeAt, f.sequence == "clearWave" {
            await waitStage(e, until: waveStart + f.t)
            e.freezeSequence(stageStart: waveStart, fxStart: e.container.screenFX.localNow, at: f.t)
            await e.frames(6)
            return finish(["frozenAt": f.t, "dots": e.dots.dotCount])
        }
        await wait(1.2)
        finish(["W": round3(w), "waveStart": round3(waveStart), "clearWaveFinished": clearWaveAt.map { round3($0) } ?? -1,
                "dots": e.dots.dotCount])
    }

    func runStageGap(_ e: BoardEngine) async {
        guard await loadDriven("L001", stages: ["L002", "L003", "L004"]) else { return finish(["error": "board"]) }
        await e.frames(20)
        beginMeasure()
        var gaps: [[String: Any]] = []
        let upto = rawInt("stages") ?? 3
        for k in 0..<upto {
            wantTransition = true
            transitionDoneAt = nil
            guard let w = await clearStage(e) else { break }
            if k == 0, let f = app.args.freezeAt, f.sequence == "stageGap" {
                await waitStage(e, until: transitionW + f.t)
                e.freezeSequence(stageStart: transitionW, fxStart: e.container.screenFX.localNow, at: f.t)
                await e.frames(6)
                return finish(["frozenAt": f.t, "stage": e.stage?.stage ?? -1])
            }
            await waitUntil(4) { self.transitionDoneAt != nil }
            let planned = e.stageSwapPlanned.map { $0.gap } ?? -1
            gaps.append(["stage": k, "W": round3(w), "transitionAtW_s": round3(transitionW - w), "swapPlanned_s": round3(planned),
                         "done_s": e.lastStageGap.map { round3($0.done) } ?? -1,
                         "doneMeasured_s": transitionDoneAt.map { round3($0 - transitionWWall) } ?? -1])
            await wait(0.3)
            if let d = driver { e.present(d.ack(.stageTransitionDone)) }
            await wait(0.2)
        }
        finish(["gaps": gaps, "stageNow": e.stage?.stage ?? -1, "level": e.stage?.level.level ?? -1])
    }

    // MARK: first use of every B2 effect after a fresh install (R3, simulator)

    func runFirstFX(_ e: BoardEngine) async {
        guard await loadDriven("warmfx") else { return finish(["error": "board"]) }
        await e.frames(60)
        beginMeasure()
        let seq: [(Int, String)] = [(3, "bump"), (0, "tape+box"), (5, "key+door"), (7, "pipe"), (8, "elevator"), (4, "violet"), (11, "rainbow")]
        let saved = e.trailOverride
        for (id, what) in seq {
            e.trailOverride = what == "violet" || what == "rainbow" ? .ladder : saved
            if what == "violet" { e.forcedPainter = "violet" }
            if what == "rainbow" { e.forcedPainter = "rainbow" }
            tapDriven(ArrowID(id))
            e.forcedPainter = nil
            await wait(what == "key+door" ? 1.6 : 0.8)
        }
        e.trailOverride = saved
        wantWave = true
        e.playClearWave()
        await wait(1.5)
        var first: [String: Double] = [:]
        for (k, v) in e.firstResults { first[k] = round2(v) }
        finish(["first_ms": first, "warmedUp": e.warmedUp])
    }

    // MARK: F1 stress: back-to-back (re)loads with taps right after each (load vs play hitches)

    func runReloads(_ e: BoardEngine) async {
        // B0 (level re-order): the same 4 soak boards as before — v552 L39 / L44 / L49 / L54 ship at L49 / L54 / L39 / L34
        let boards = (app.args.raw["pc.soakBoards"] ?? "synth40,L049,L054,L039,L034").split(separator: ",").map(String.init)
        let n = rawInt("loads") ?? 20
        var rows: [[String: Any]] = []
        if app.args.raw["pc.alternate"] != nil {
            // big ↔ small back to back: the retired set's teardown overlaps the next board's first frames
            guard await loadDriven(boards[0]) else { return finish(["error": "board"]) }
            await e.frames(20)
            beginMeasure()
            e.loadCommits = []
            for k in 0..<n {
                guard await loadDriven(boards[k % boards.count]) else { break }
                if let d = driver { for u in d.freeUnits().prefix(5) { tapDriven(u[0]) } }
                await wait(0.5)
            }
            let s = app.perf.snapshot()
            return finish(["alternate": boards, "loads": n, "frames": s.frames, "over20": s.over20, "over20_load": e.hitchesLoad,
                           "over20_play": e.hitchesPlay, "max_ms": round2(s.max_ms), "load_commits": e.loadCommitsSummary.mapValues { round2($0) },
                           "attachPerFrame": e.fx.attachPerFrame, "teardownPerFrame": e.fx.teardownPerFrame])
        }
        for b in boards {
            guard await loadDriven(b) else { continue }
            await e.frames(20)
            beginMeasure()
            e.loadCommits = []
            for _ in 0..<n {
                guard await loadDriven(b) else { break }
                if let d = driver { for u in d.freeUnits().prefix(5) { tapDriven(u[0]) } }
                await wait(0.5)
            }
            let s = app.perf.snapshot()
            rows.append(["board": b, "loads": n, "frames": s.frames, "over20": s.over20, "over20_load": e.hitchesLoad,
                         "over20_play": e.hitchesPlay, "max_ms": round2(s.max_ms), "load_commits": e.loadCommitsSummary.mapValues { round2($0) }])
            Log.mark("boardlab", "reloads \(b): over20 \(s.over20) (load \(e.hitchesLoad), play \(e.hitchesPlay)) max \(round2(s.max_ms)) ms")
        }
        finish(["boards": rows, "attachPerFrame": e.fx.attachPerFrame, "teardownPerFrame": e.fx.teardownPerFrame])
    }

    // MARK: the bulb's highlight (MA §3.10.1): camera to max zoom, blink, stay green, back to fit when the unit leaves

    func runHint(_ e: BoardEngine) async {
        guard await loadDriven(app.args.labBoard ?? "L049") else { return finish(["error": "board"]) }   // B0: v552 L39's board ships at L49
        await e.frames(20)
        guard let d = driver, let unit = d.session.hint() else { return finish(["error": "no hint"]) }
        beginMeasure()
        let s0 = e.roots.stage.convertTime(CACurrentMediaTime(), from: nil)
        let f0 = e.container.screenFX.localNow
        e.present([.hintShown(unit)])
        if let f = app.args.freezeAt, f.sequence == "hint" {
            await wait(f.t)
            e.freezeSequence(stageStart: s0, fxStart: f0, at: f.t)
            await e.frames(6)
            return finish(["unit": unit.map(\.raw), "frozenAt": f.t, "zoom": round2(Double(e.zoomScale))])
        }
        await wait(1.0)
        let zoomAtCamera = Double(e.zoomScale)
        await wait(1.5)
        tapDriven(unit[0])
        await waitUntil(3) { e.movers.isEmpty }
        await wait(0.8)
        finish(["unit": unit.map(\.raw), "zoomAfterCamera": round2(zoomAtCamera), "zoomMax": round2(Double(e.container.scroll.maximumZoomScale)),
                "zoomAfterExit": round2(Double(e.zoomScale))])
    }

    func round3(_ v: Double) -> Double { (v * 1000).rounded() / 1000 }
}
#endif
