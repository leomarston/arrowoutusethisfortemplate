import UIKit
import PathCore

// B1 (SPEC-architecture §5.12, §9.5, §10.4, §11 R1–R6, §12.2 B1 acceptance). The B1 BoardLab scenarios. Each loads a lab
// board into the real engine, drives it through the real release handler (or waits for real touches), measures with
// PerfMonitor / LatencyProbe and the engine's own counters, and ends with `finish` (lab-ready.json + lab-perf.json).
// Launch arguments read from `raw` (lab-private): pc.waves, pc.perWave, pc.waveGap, pc.minGap, pc.exits, pc.soakSeconds,
// pc.soakBoards, pc.r1 (fallback recogniser, R1).

extension BoardLabController {
    func run(_ e: BoardEngine) async {
        switch scenario {
        case "idle": await runIdle(e)
        case "input": await runInteractive(e, latency: false)
        case "latency": await runInteractive(e, latency: true)
        case "exit": await runExit(e)
        case "exit5", "exitWaves": await runWaves(e)
        case "bump": await runBump(e)
        case "hittest": await runHitTest(e)
        case "zoomramp": await runZoomRamp(e)
        case "intro": await runIntroScenario(e)
        case "autoplay": await runAutoplay(e)
        case "kinematics": await runKinematics(e)
        case "firstuse": await runFirstUse(e)
        case "soak": await runSoak(e)
        default:
            if await runObstacleScenario(e) { return }
            status = "boardlab: unknown scenario \(scenario)"
            Log.error("boardlab", status)
            finish(["error": "unknown scenario \(scenario)"])
        }
    }

    // MARK: helpers

    func rawDouble(_ k: String) -> Double? { app.args.raw["pc." + k].flatMap(Double.init) }
    func rawInt(_ k: String) -> Int? { app.args.raw["pc." + k].flatMap { Int($0) } }

    func boardCentre(_ e: BoardEngine) -> CGPoint { CGPoint(x: e.contentBounds.midX, y: e.contentBounds.midY) }

    func headPoint(_ e: BoardEngine, _ id: ArrowID) -> CGPoint? {
        guard let st = e.stage, let a = st.level.arrows.first(where: { $0.id == id }) else { return nil }
        return st.geo.centre(headCell(a))
    }

    /// Free arrows nearest `p` (content space), the ones with an on-screen tap point first.
    func freeNear(_ e: BoardEngine, _ p: CGPoint, count: Int) -> [ArrowID] {
        guard let rules else { return [] }
        let free = rules.freeArrows().filter { e.movers[$0] == nil }
        func d(_ id: ArrowID) -> CGFloat {
            guard let h = headPoint(e, id) else { return .greatestFiniteMagnitude }
            return hypot(h.x - p.x, h.y - p.y)
        }
        let onScreen = free.filter { e.tapPoint(of: $0) != nil }.sorted { d($0) < d($1) }
        let off = free.filter { e.tapPoint(of: $0) == nil }.sorted { d($0) < d($1) }
        var out: [ArrowID] = []
        var taken = Set<ArrowID>()
        for id in onScreen + off where out.count < count && !taken.contains(id) {
            rules.unit(id).forEach { taken.insert($0) }
            out.append(id)
        }
        return out
    }

    func blockedNear(_ e: BoardEngine, _ p: CGPoint, minGap: Int) -> (ArrowID, Int)? {
        guard let rules else { return nil }
        let all = rules.blockedArrows().filter { e.movers[$0.0] == nil && e.tapPoint(of: $0.0) != nil }
        func d(_ id: ArrowID) -> CGFloat {
            guard let h = headPoint(e, id) else { return .greatestFiniteMagnitude }
            return hypot(h.x - p.x, h.y - p.y)
        }
        let pool = all.filter { $0.1 >= minGap }
        return (pool.isEmpty ? all : pool).min { d($0.0) < d($1.0) }
    }

    func waitUntil(_ timeout: Double, _ cond: () -> Bool) async {
        let end = CACurrentMediaTime() + timeout
        while !cond() && CACurrentMediaTime() < end { await wait(1.0 / 60) }
    }

    func zoomTarget(_ e: BoardEngine, default def: String) -> CGFloat {
        if let z = app.args.zoom { return CGFloat(z) }
        return def == "max" ? e.container.scroll.maximumZoomScale : 1
    }

    // MARK: idle (captures: L32 vs shot 003, dots after autoplay, …)

    func runIdle(_ e: BoardEngine) async {
        guard await loadBoard(boardName) else { return finish(["error": "board"]) }
        await e.frames(45)
        beginMeasure()
        await e.frames(60)
        finish(["arrows": rules?.level.arrows.count ?? 0, "dots": e.dots.dotCount, "free": rules?.freeArrows().count ?? 0,
                "tapes": e.tapes.count])
    }

    // MARK: input / latency: real XCUITest touches (BoardInputTests, R1)

    func runInteractive(_ e: BoardEngine, latency: Bool) async {
        guard await loadBoard(boardName) else { return finish(["error": "board"]) }
        beginMeasure()
        finish(["arrows": rules?.level.arrows.count ?? 0, "interactive": true])
        guard latency else { return }
        var written = 0
        while true {
            await wait(1.0)
            let n = app.latency.samples.count
            if n != written {
                written = n
                Self.writeJSON(perfDict(), "lab-perf.json")
                if n % 10 == 0 { Log.mark("boardlab", "latency samples \(n) perf \(Self.compact(perfDict()))") }
            }
        }
    }

    // MARK: one exit (freeze captures: P1 full ink on the first frame, the trail look)

    func runExit(_ e: BoardEngine) async {
        guard await loadBoard(boardName) else { return finish(["error": "board"]) }
        if let z = app.args.zoom { e.setZoom(CGFloat(z), centredOn: nil) }
        await e.frames(30)
        guard let rules else { return }
        // the longest free snake with bends near the centre (the spike's trail pick)
        let c = boardCentre(e)
        let cand = rules.freeArrows().filter { e.tapPoint(of: $0) != nil && rules.unit($0).count == 1 }
        let pick = cand.max { a, b in score(e, a, c) < score(e, b, c) }
        guard let id = pick else { return finish(["error": "no free arrow"]) }
        let s0 = e.roots.stage.convertTime(CACurrentMediaTime(), from: nil)
        let f0 = e.container.screenFX.localNow
        tap(id)
        let cells = rules.level.arrows.first { $0.id == id }?.cells.count ?? 0
        if let f = app.args.freezeAt, f.sequence == "exit" {
            e.freezeSequence(stageStart: s0, fxStart: f0, at: f.t)
            await e.frames(4)
            finish(["arrow": id.raw, "cells": cells, "frozenAt": f.t])
        } else {
            await waitUntil(4) { e.movers.isEmpty }
            await wait(0.3)
            finish(["arrow": id.raw, "cells": cells])
        }
    }

    private func score(_ e: BoardEngine, _ id: ArrowID, _ c: CGPoint) -> Double {
        guard let st = e.stage, let a = st.level.arrows.first(where: { $0.id == id }) else { return -1e9 }
        let bends = zip(zip(a.cells, a.cells.dropFirst()), a.cells.dropFirst(2)).filter { pair, z in
            Dir(from: pair.0, to: pair.1) != Dir(from: pair.1, to: z)
        }.count
        let h = st.geo.centre(headCell(a))
        let dist = Double(hypot(h.x - c.x, h.y - c.y) / st.geo.pitch)
        return Double(a.cells.count * 3 + bends * 4) - dist
    }

    // MARK: exit waves (acceptance 6: 304 arrows at max zoom, 5 simultaneous exits × 4 waves)

    func runWaves(_ e: BoardEngine) async {
        guard await loadBoard(boardName) else { return finish(["error": "board"]) }
        let z = zoomTarget(e, default: "max")
        let centre = boardCentre(e)
        let anchor = freeNear(e, centre, count: 1).first.flatMap { headPoint(e, $0) } ?? centre
        e.setZoom(z, centredOn: anchor)
        await e.frames(60)
        beginMeasure()
        await e.frames(60)
        let idle = app.perf.snapshot()
        beginMeasure()
        let waves = rawInt("waves") ?? 4
        let perWave = rawInt("perWave") ?? 5
        let gap = rawDouble("waveGap") ?? 0.7
        var costs: [Double] = []
        var counts: [Int] = []
        for _ in 0..<waves {
            let picks = freeNear(e, anchor, count: perWave)
            let h0 = CACurrentMediaTime()
            for id in picks { tap(id) }                        // one run-loop turn: simultaneous exits
            costs.append(round2((CACurrentMediaTime() - h0) * 1000))
            counts.append(picks.count)
            await wait(0.25)
            peakLayers = max(peakLayers, e.layerCount())
            await wait(max(0, gap - 0.25))
        }
        await wait(2.5)
        finish(["waves": waves, "perWave": perWave, "waveGap": gap, "waveStartCost_ms": costs, "waveCounts": counts,
                "zoom": round2(Double(e.zoomScale)), "pitchOnScreen": round2(Double(e.pitchOnScreen)),
                "idle": ["frames": idle.frames, "over20": idle.over20, "max_ms": round2(idle.max_ms)],
                "arrows": rules?.level.arrows.count ?? 0])
    }

    // MARK: bump (acceptance 6: contact beat, vignette, red return; freeze captures)

    func runBump(_ e: BoardEngine) async {
        guard await loadBoard(boardName) else { return finish(["error": "board"]) }
        if let z = app.args.zoom { e.setZoom(CGFloat(z), centredOn: nil) }
        await e.frames(30)
        guard let rules, let (id, gap) = blockedNear(e, boardCentre(e), minGap: rawInt("minGap") ?? 1) else {
            return finish(["error": "no blocked arrow"])
        }
        var planned = 0.0
        var contactCells = 0.0
        if case .bump(let plan) = rules.resolve(id) {
            contactCells = plan.contactCells
            planned = e.config.bumpOutBase + e.config.bumpOutPerCell * max(0.05, plan.contactCells)
        }
        beginMeasure()
        let s0 = e.roots.stage.convertTime(CACurrentMediaTime(), from: nil)
        let f0 = e.container.screenFX.localNow
        let tTap = CACurrentMediaTime()
        tap(id)
        if let f = app.args.freezeAt, f.sequence == "bump" {
            e.freezeSequence(stageStart: s0, fxStart: f0, at: f.t)
            await e.frames(4)
            finish(["arrow": id.raw, "gap": gap, "contactCells": round2(contactCells), "plannedContact_s": round2(planned),
                    "frozenAt": f.t, "hearts": rules.hearts, "marked": e.nodes[id]?.marked ?? false])
            return
        }
        await waitUntil(3) { self.bumpsFinished >= 1 }
        await wait(0.5)
        let contactAt = contacts.first.map { $0.1 - tTap } ?? -1
        finish(["arrow": id.raw, "gap": gap, "contactCells": round2(contactCells), "plannedContact_s": round2(planned),
                "contactBeat_s": round2(contactAt), "hearts": rules.hearts, "marked": e.nodes[id]?.marked ?? false,
                "restVisible": !(e.nodes[id]?.body.isHidden ?? true)])
    }

    // MARK: hit test (the spike's 873 + 399 jittered in-cell points, 0 wrong; cost per query)

    func runHitTest(_ e: BoardEngine) async {
        guard await loadBoard(boardName), let st = e.stage else { return finish(["error": "board"]) }
        var rng = PathRandom(seed: 99)
        let p = st.geo.pitch
        var total = 0, wrong = 0, apexTotal = 0, apexWrong = 0
        func hit(_ q: CGPoint) -> ArrowID? {
            st.hit.arrow(at: q, zoom: 1, radiusPt: e.config.hitRadius, tieTolerancePt: e.config.tieTolerance, tieTolerancePitch: e.config.tieTolerancePitch,
                         rightThenDown: e.config.tieRightThenDown)
        }
        for a in st.level.arrows where a.hiddenBy == nil {
            for c in a.cells {
                let o = st.geo.centre(c)
                let jx = CGFloat(rng.unit() * 0.9 - 0.45) * p
                let jy = CGFloat(rng.unit() * 0.9 - 0.45) * p
                total += 1
                if hit(CGPoint(x: o.x + jx, y: o.y + jy)) != a.id { wrong += 1 }
            }
            // a tap on the head triangle's tip area
            let h = st.geo.centre(headCell(a))
            let apex = CGFloat(e.config.arrowMetrics.apexPast(a.dir)) * p * 0.9
            apexTotal += 1
            if hit(CGPoint(x: h.x + CGFloat(a.dir.dc) * apex, y: h.y + CGFloat(a.dir.dr) * apex)) != a.id { apexWrong += 1 }
        }
        let bx = st.geo.centre(Cell(0, 0)), ex = st.geo.centre(Cell(st.level.cols - 1, st.level.rows - 1))
        let n = 100_000
        var pts: [CGPoint] = []
        pts.reserveCapacity(n)
        for _ in 0..<n {
            let x = bx.x + CGFloat(rng.unit()) * (ex.x - bx.x)
            let y = bx.y + CGFloat(rng.unit()) * (ex.y - bx.y)
            pts.append(CGPoint(x: x, y: y))
        }
        let t0 = CACurrentMediaTime()
        var hits = 0
        for q in pts where hit(q) != nil { hits += 1 }
        let us = (CACurrentMediaTime() - t0) / Double(n) * 1e6
        finish(["cellPoints": total, "wrong": wrong, "apexPoints": apexTotal, "apexWrong": apexWrong,
                "random100k_us_per_query": round2(us * 100) / 100, "randomHits": hits])
    }

    // MARK: zoom ramp (R5 proxy: zoomScale set every frame 1 → max → min → 1 over 6 s)

    func runZoomRamp(_ e: BoardEngine) async {
        guard await loadBoard(boardName) else { return finish(["error": "board"]) }
        await e.frames(60)
        beginMeasure()
        let s = e.container.scroll
        let zmax = s.maximumZoomScale, zmin = s.minimumZoomScale
        var done = false
        let t0 = CACurrentMediaTime()
        onFrame = { [weak self] _ in
            let t = CACurrentMediaTime() - t0
            func ease(_ x: Double) -> CGFloat { CGFloat(0.5 - 0.5 * cos(Double.pi * min(max(x, 0), 1))) }
            let z: CGFloat
            if t < 2.5 { z = 1 + (zmax - 1) * ease(t / 2.5) }
            else if t < 5 { z = zmax + (zmin - zmax) * ease((t - 2.5) / 2.5) }
            else { z = zmin + (1 - zmin) * ease(t - 5) }
            e.setZoom(z, centredOn: nil)
            if t > 6.05 { self?.onFrame = nil; done = true }
        }
        await waitUntil(10) { done }
        finish(["zoomMax": round2(Double(zmax)), "zoomMin": round2(Double(zmin))])
    }

    // MARK: intro (freeze captures at intro@t; the build-in duration)

    func runIntroScenario(_ e: BoardEngine) async {
        guard await loadBoard(boardName, intro: .none) else { return finish(["error": "board"]) }
        await e.frames(20)
        guard let st = e.stage else { return }
        beginMeasure()
        introDone = false
        e.load(st.setup)                                        // rebuild hidden, then the build-in
        let tStart = CACurrentMediaTime()
        e.playIntro(.growFromTails)
        if let f = app.args.freezeAt, f.sequence == "intro" {
            e.freezeSequence(stageStart: e.introStartLocal, fxStart: e.container.screenFX.localNow, at: f.t)
            await e.frames(4)
            finish(["frozenAt": f.t])
            return
        }
        await waitUntil(4) { self.introDone }
        let dur = CACurrentMediaTime() - tStart
        await wait(0.3)
        finish(["introFinished_s": round2(dur), "planned_s": round2(max(e.config.introZoomDuration,
            e.config.introDrawBase + e.config.introDrawPerCell * Double(st.level.arrows.map(\.cells.count).max() ?? 0)))])
    }

    // MARK: autoplay (the greedy order through the real release handler; P3: every dot present after the clear)

    func runAutoplay(_ e: BoardEngine) async {
        guard await loadBoard(boardName) else { return finish(["error": "board"]) }
        if let z = app.args.zoom { e.setZoom(CGFloat(z), centredOn: nil) }
        await e.frames(30)
        guard let rules else { return }
        let order = rules.greedyOrder()
        let rate = app.args.autoplayRate ?? 0.12
        beginMeasure()
        let t0 = CACurrentMediaTime()
        for id in order {
            if rules.isAlive(id) { tap(id) }
            await wait(rate)
        }
        await waitUntil(6) { e.movers.isEmpty }
        let secs = CACurrentMediaTime() - t0
        await wait(1.0)
        let cells = rules.level.arrows.reduce(0) { $0 + $1.cells.count }
        finish(["taps": order.count, "bumps": rules.bumps, "cleared": rules.liveCount == 0, "hearts": rules.hearts,
                "dots": e.dots.dotCount, "arrowCells": cells, "moversLeft": e.movers.count,
                "lastExitLeftBoard": lastExitAt != nil, "exitsFinished": exitsFinished, "seconds": round2(secs)])
    }

    // MARK: kinematics (acceptance 3: 20 exits' presented head travel vs the model within ±1 frame; P1 full ink)

    func runKinematics(_ e: BoardEngine) async {
        guard await loadBoard(boardName) else { return finish(["error": "board"]) }
        if let z = app.args.zoom { e.setZoom(CGFloat(z), centredOn: nil) }
        await e.frames(30)
        guard let rules else { return }
        struct Track { var cells = 0; var samples = 0; var maxDtMs = 0.0; var maxDsCells = 0.0; var lastD = 0.0; var firstOpacity = -1.0 }
        var tracks: [ArrowID: Track] = [:]
        let kin = e.kinematics
        onFrame = { _ in
            for (id, m) in e.movers where m.kind == .exit && m.straight {
                guard let head = m.headLayer, let pres = head.presentation() else { continue }
                var tr = tracks[id] ?? Track()
                if tr.firstOpacity < 0 {
                    // the first frame of the motion: every layer of the mover at full opacity (P1: no implicit fade-in)
                    // (B2: the field painters' colour-ramp overlay fades on purpose: its layers carry a "ramp" animation)
                    let ops = [m.root.presentation()?.opacity ?? 0]
                        + (m.root.sublayers ?? []).filter { $0.animation(forKey: "ramp") == nil }.map { $0.presentation()?.opacity ?? 0 }
                    tr.firstOpacity = Double(ops.min() ?? 0)
                }
                let tau = m.root.convertTime(CACurrentMediaTime(), from: nil) - m.begin
                let dx = pres.position.x - m.headStartLocal.x, dy = pres.position.y - m.headStartLocal.y
                let d = Double((dx * m.dirVec.dx + dy * m.dirVec.dy) / m.pitch)
                guard tau > 0.001, d > 0.02, tau < m.duration - 0.001 else { tracks[id] = tr; continue }
                let tModel = kin.time(toTravel: d)
                tr.samples += 1
                tr.maxDtMs = max(tr.maxDtMs, abs(tau - tModel) * 1000)
                tr.maxDsCells = max(tr.maxDsCells, abs(kin.s(tau) - d))
                tr.lastD = d
                tracks[id] = tr
            }
        }
        let n = rawInt("exits") ?? 20
        var tapped: [ArrowID] = []
        let centre = boardCentre(e)
        for k in 0..<n {
            // alternate long and short free arrows near the centre (varied lengths)
            let free = freeNear(e, centre, count: 12).filter { rules.unit($0).count == 1 }
            func length(_ id: ArrowID) -> Int { rules.level.arrows.first(where: { $0.id == id })?.cells.count ?? 0 }
            let sorted = free.sorted { length($0) > length($1) }
            guard let id = (k % 2 == 0 ? sorted.first : sorted.last) else { break }
            tracks[id] = Track(cells: rules.level.arrows.first { $0.id == id }?.cells.count ?? 0)
            tapped.append(id)
            tap(id)
            await wait(0.4)
        }
        await waitUntil(5) { e.movers.isEmpty }
        onFrame = nil
        let rows: [[String: Any]] = tapped.compactMap { id in
            guard let t = tracks[id] else { return nil }
            return ["id": id.raw, "cells": t.cells, "samples": t.samples, "maxDt_ms": round2(t.maxDtMs),
                    "maxDs_cells": round2(t.maxDsCells * 1000) / 1000, "travelSeen_cells": round2(t.lastD),
                    "firstFrameMinOpacity": t.firstOpacity]
        }
        let worst = tracks.values.map(\.maxDtMs).max() ?? -1
        let minOpacity = tracks.values.map(\.firstOpacity).filter { $0 >= 0 }.min() ?? -1
        finish(["exits": rows, "exitCount": rows.count, "worstDt_ms": round2(worst), "frame_ms": 16.67,
                "withinOneFrame": worst <= 16.67 && worst >= 0, "firstFrameMinOpacity": minOpacity,
                "model": ["v0": kin.v0, "vmax": kin.vmax, "tau": kin.tau]])
    }

    // MARK: first use after a fresh install (acceptance 7; R3 on the simulator)

    func runFirstUse(_ e: BoardEngine) async {
        guard await loadBoard(boardName) else { return finish(["error": "board"]) }
        await e.frames(60)
        beginMeasure()
        let c = boardCentre(e)
        guard let free = freeNear(e, c, count: 1).first else { return finish(["error": "no free arrow"]) }
        tap(free)
        await wait(1.2)
        let blocked = blockedNear(e, c, minGap: 0)
        if let b = blocked?.0 { tap(b) }
        await wait(1.6)
        var first: [String: Double] = [:]
        for (k, v) in e.firstResults { first[k] = round2(v) }
        finish(["first_ms": first, "exitArrow": free.raw, "bumpArrow": blocked?.0.raw ?? -1,
                "warmedUp": e.warmedUp])
    }

    // MARK: soak (§10.4, the board part; V3 / D1a run it in full: 90 s per board and zoom)
    // B2: on the REAL rules (LabDriver, the bundle's rules.json) with the painter `-pc.trail` names (rainbow for §10.4) +
    // trail stars; the boards carry their obstacles (labb_ fixtures: keys fly, doors burst, pipes and boxes break as the
    // waves reach them); frames within 3 frames of a board (re)load are counted apart (`over20_load` vs `over20_play`,
    // D1a F1: the lab tags its own reloads).

    func freeUnitsNear(_ e: BoardEngine, _ p: CGPoint, count: Int) -> [ArrowID] {
        guard let d = driver else { return [] }
        func dist(_ id: ArrowID) -> CGFloat {
            guard let h = headPoint(e, id) else { return .greatestFiniteMagnitude }
            return hypot(h.x - p.x, h.y - p.y)
        }
        let units = d.freeUnits().filter { u in u.allSatisfy { e.movers[$0] == nil } }
        let on = units.filter { e.tapPoint(of: $0[0]) != nil }.sorted { dist($0[0]) < dist($1[0]) }
        let off = units.filter { e.tapPoint(of: $0[0]) == nil }.sorted { dist($0[0]) < dist($1[0]) }
        return (on + off).prefix(count).map { $0[0] }
    }

    func runSoak(_ e: BoardEngine) async {
        // B0 (level re-order): the same 4 soak boards as before — v552 L39 / L44 / L49 / L54 ship at L49 / L54 / L39 / L34
        let boards = (app.args.raw["pc.soakBoards"] ?? "synth40,L049,L054,L039,L034").split(separator: ",").map(String.init)
        let secs = rawDouble("soakSeconds") ?? 90
        var segments: [[String: Any]] = []
        var totalOver = 0, totalLoad = 0, totalPlay = 0
        var worst = 0.0
        var worstFoot = 0.0
        var peakFoot = 0.0
        for b in boards {
            for mode in ["max", "fit"] {
                guard await loadDriven(b) else { segments.append(["board": b, "error": "missing"]); continue }
                let z: CGFloat = mode == "max" ? e.container.scroll.maximumZoomScale : 1
                e.setZoom(z, centredOn: nil)
                await e.frames(30)
                beginMeasure()
                let t0 = CACurrentMediaTime()
                var bumpsDone = 0
                var ramp = false
                var reloads = 0
                var effects: [String: Int] = [:]
                while CACurrentMediaTime() - t0 < secs {
                    let el = CACurrentMediaTime() - t0
                    guard let d = driver else { break }
                    // on the real rules a board with obstacles often has fewer than 5 free units: tap what is free,
                    // reload only when nothing is (so keys, pipes and boxes are reached: §10.4)
                    if d.freeUnits().isEmpty || d.session.isFinished || d.session.board.isCleared {
                        reloads += 1
                        guard await loadDriven(b) else { break }
                        e.setZoom(z, centredOn: nil)
                        continue
                    }
                    let vis = e.visibleContentRect()
                    for id in freeUnitsNear(e, CGPoint(x: vis.midX, y: vis.midY), count: 5) {
                        if let plan = d.plan(id) {
                            for beat in plan.beats {
                                switch beat {
                                case .keyReleased: effects["keyFlight", default: 0] += 1
                                case .pipeBreak: effects["pipeBreak", default: 0] += 1
                                case .counterBreak: effects["boxBreak", default: 0] += 1
                                case .elevatorEmptied: effects["elevator", default: 0] += 1
                                default: break
                                }
                            }
                        }
                        tapDriven(id)
                    }
                    if (bumpsDone == 0 && el > secs / 3) || (bumpsDone == 1 && el > 2 * secs / 3) {
                        if let bl = d.blocked().first(where: { e.tapPoint(of: $0) != nil }) { tapDriven(bl) }
                        bumpsDone += 1
                    }
                    if !ramp && el > secs / 2 - 3 {
                        ramp = true
                        let s = e.container.scroll
                        let zmax = s.maximumZoomScale, zmin = s.minimumZoomScale
                        let r0 = CACurrentMediaTime()
                        onFrame = { [weak self] _ in
                            let t = CACurrentMediaTime() - r0
                            func ease(_ x: Double) -> CGFloat { CGFloat(0.5 - 0.5 * cos(Double.pi * min(max(x, 0), 1))) }
                            let zz: CGFloat
                            if t < 2.5 { zz = 1 + (zmax - 1) * ease(t / 2.5) }
                            else if t < 5 { zz = zmax + (zmin - zmax) * ease((t - 2.5) / 2.5) }
                            else { zz = zmin + (1 - zmin) * ease(t - 5) }
                            e.setZoom(zz, centredOn: nil)
                            if t > 6.05 { self?.onFrame = nil; e.setZoom(z, centredOn: nil) }
                        }
                    }
                    peakLayers = max(peakLayers, e.layerCount())
                    await wait(0.7)
                }
                onFrame = nil
                await wait(1.0)
                let s = app.perf.snapshot()
                totalOver += s.over20
                totalLoad += e.hitchesLoad
                totalPlay += e.hitchesPlay
                worst = max(worst, s.max_ms)
                worstFoot = max(worstFoot, s.footprint_mb)
                peakFoot = max(peakFoot, s.footprint_peak_mb)
                segments.append(["board": b, "zoom": mode, "frames": s.frames, "over20": s.over20, "over20_load": e.hitchesLoad,
                                 "over20_play": e.hitchesPlay, "max_ms": round2(s.max_ms), "p99_ms": round2(s.p99_ms),
                                 "footprint_mb": round2(s.footprint_mb), "movers_peak": peakMovers, "layers_peak": peakLayers,
                                 "bumps": bumpsDone, "reloads": reloads, "effects": effects, "thermal": s.thermal])
                Log.mark("boardlab", "soak \(b) \(mode) over20 \(s.over20) (load \(e.hitchesLoad), play \(e.hitchesPlay)) max \(round2(s.max_ms)) ms effects \(effects)")
            }
        }
        let painter = app.args.trail?.rawValue ?? "ladder"
        finish(["segments": segments, "total_over20": totalOver, "total_over20_load": totalLoad, "total_over20_play": totalPlay,
                "worst_ms": round2(worst), "worst_footprint_mb": round2(worstFoot), "footprint_peak_mb": round2(peakFoot),
                "secondsPerSegment": secs, "painter": painter, "rules": "LevelSession (bundle rules.json)"])
    }
}
