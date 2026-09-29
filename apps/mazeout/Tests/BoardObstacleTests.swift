import XCTest
import UIKit
import PathCore
@testable import ArrowOut

/// B2 (SPEC-architecture §5.5 painters, §5.6 obstacles, §5.7 transitions, §5.9 F1 split loads; SPEC-motion-audio §3):
/// the obstacle layers, their beats on the REAL rules (C2's LevelSession through BoardLab's LabDriver), the combo
/// painters, the stage transition, the clear wave and the split loads — on a private engine in its own window.
@MainActor final class BoardObstacleTests: XCTestCase, BoardDelegate {
    var beats: [(BoardBeat, CFTimeInterval)] = []
    var driver: LabDriver?
    weak var engine: BoardEngine?
    var window: UIWindow?

    func boardFrame(timestamp: CFTimeInterval, targetTimestamp: CFTimeInterval) {}
    func boardReleased(arrow: ArrowID?, contentPoint: CGPoint, touchTimestamp: TimeInterval) {
        guard let d = driver, let e = engine else { return }
        e.present(d.tap(arrow, at: CACurrentMediaTime()))
    }
    func boardBeat(_ beat: BoardBeat) {
        beats.append((beat, CACurrentMediaTime()))
        guard let d = driver, let e = engine else { return }
        switch beat {
        case .bumpContact(let a): e.present(d.ack(.bumpContact(a)))
        case .bumpFinished(let a): e.present(d.ack(.bumpFinished(a)))
        case .doorBurst(let x): e.present(d.ack(.doorBurst(x)))
        default: break
        }
    }
    func boardZoomChanged(scale: CGFloat) {}

    private func makeEngine() -> BoardEngine {
        let a = LaunchArgs(arguments: [])
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("board-obstacle-tests-\(UUID().uuidString)")
        let ctx = AppContext(args: a, tuning: Tuning.load(bundle: .main), clock: MotionClock(args: a),
                             store: PlayerStore(args: a, now: Date(), bundle: .main, directory: dir), hud: HUDModel(),
                             anchors: AnchorRegistry(), perf: PerfMonitor(), latency: LatencyProbe(), bundle: .main)
        let e = BoardEngine(ctx)
        e.delegate = self
        engine = e
        let scene = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first
        let w = scene.map { UIWindow(windowScene: $0) } ?? UIWindow(frame: CGRect(x: 0, y: 0, width: 393, height: 852))
        w.frame = CGRect(x: 0, y: 0, width: 393, height: 852)
        w.addSubview(e.view)
        e.view.frame = w.bounds
        w.isHidden = false
        e.view.layoutIfNeeded()
        window = w
        // the art the obstacle layers draw (the warm-up's step 1 without its board run)
        e.sprites.preload(BoardArt.names)
        let end = Date().addingTimeInterval(2)
        while e.sprites.image("lockHex") == nil && Date() < end { wait(0.02) }
        e.boardArt.build()
        for n in ["doorShards", "pipeShards", "pipeCounter", "pipeMouth"] { e.shards.setImage(n, e.sprites.image(n)) }
        return e
    }

    override func tearDown() {
        window?.isHidden = true
        window = nil
        driver = nil
        beats = []
        super.tearDown()
    }

    private func wait(_ s: Double) { RunLoop.main.run(until: Date().addingTimeInterval(s)) }

    private func waitFor(_ timeout: Double, _ cond: () -> Bool) {
        let end = Date().addingTimeInterval(timeout)
        while !cond() && Date() < end { wait(0.01) }
    }

    private func load(_ e: BoardEngine, _ level: LevelSpec, more: [LevelSpec] = []) {
        driver = LabDriver(stages: [level] + more, bundle: .main)
        e.inputEnabled = true
        e.load(StageSetup(level: level, stage: 0, stages: 1 + more.count, seed: 1,
                          screen: CGSize(width: 393, height: 852), config: e.config))
        e.playIntro(.none)
        waitFor(2) { e.pendingAttach.isEmpty }
        if let d = driver { e.present(d.ack(.introFinished)) }
    }

    private func tap(_ e: BoardEngine, _ id: Int) {
        guard let st = e.stage, let a = st.level.arrows.first(where: { $0.id == ArrowID(id) }) else { return XCTFail("a\(id)") }
        let p = e.tapPoint(of: ArrowID(id)) ?? e.contentToScreen(st.geo.centre(a.cells[a.cells.count / 2]))
        e.handleRelease(screenPoint: p, touchTimestamp: CACurrentMediaTime())
    }

    // MARK: the door: a code-drawn 9-slice shutter at ANY size (CONSISTENCY O-23 / §21.11)

    func testDoorNineSliceRendersEverySize() throws {
        let e = makeEngine()
        for (w, h) in [(4, 4), (4, 8), (5, 17), (22, 10), (26, 13), (10, 4)] {
            var cells: [Cell] = []
            for r in 0..<h { for c in 0..<w { cells.append(Cell(c + 1, r + 1)) } }
            let level = LevelSpec(level: 9200, source: .designed, cols: w + 2, rows: h + 2, timerSeconds: 180,
                                  arrows: [ArrowSpec(id: ArrowID(0), cells: [Cell(0, 0), Cell(1, 0)], dir: .right)],
                                  obstacles: [ObstacleSpec(id: "d0", kind: .door, cells: cells, order: 0)])
            let layout = e.config.layout(for: level, screen: CGSize(width: 393, height: 852))
            let geo = BoardGeometry(layout: layout, config: e.config, screenScale: 3)
            let d = DoorNode(spec: level.obstacles[0], geo: geo, art: e.boardArt, scale: 3)
            let p = CGFloat(layout.pitch)
            XCTAssertEqual(d.block.width, CGFloat(w) * p, accuracy: 0.01)
            XCTAssertEqual(d.block.height, CGFloat(h) * p, accuracy: 0.01)
            // top slice (rows 0–1) + one replicated slat per middle row + the foot row + the lock
            let rep = d.root.sublayers?.compactMap { $0 as? CAReplicatorLayer }.first
            XCTAssertEqual(rep?.instanceCount, h - 3, "one slat per cell row (\(w)×\(h))")
            XCTAssertEqual(Double(rep?.instanceTransform.m42 ?? 0), Double(p), accuracy: 0.001)
            XCTAssertNotNil(d.lock.contents, "lockHex drawn")
            XCTAssertEqual(d.lockCentre.x, d.block.midX, accuracy: 0.01)
            XCTAssertEqual(d.lockCentre.y, d.block.midY + 0.18 * p, accuracy: 0.01, "0.18 p below the block centre (STYLE §A.2)")
            XCTAssertGreaterThanOrEqual(d.root.frame.width, d.block.width)
        }
    }

    // MARK: the key flight (MA §3.5.2): the measured geometry bursts at tap + 1.14 s

    func testKeyTimelineReproducesTheMeasuredBurst() {
        let e = makeEngine()
        let measured = KeyTimeline.make(e.fx, distanceCells: 160 / 17.86)      // the clip's dive: 160 pt at pitch 17.86
        XCTAssertEqual(measured.dive, 0.224, accuracy: 0.003, "row 4: the dive took 0.224 s")
        XCTAssertEqual(measured.insertStart, 0.78, accuracy: 0.01, "row 5: dive end R + 0.78")
        XCTAssertEqual(measured.turnStart, 1.01, accuracy: 0.01, "row 6: the turn at R + 1.01")
        XCTAssertEqual(measured.burst, 1.14, accuracy: 1.0 / 60, "row 7: the burst at R + 1.14 ± 1 frame")
        XCTAssertEqual(KeyTimeline.make(e.fx, distanceCells: 0.1).dive, e.fx.keyDiveMin, "clamped short")
        XCTAssertEqual(KeyTimeline.make(e.fx, distanceCells: 400).dive, e.fx.keyDiveMax, "clamped long")
    }

    func testKeyFlightBurstsTheDoorOnItsBeatAndRevealsItsArrow() throws {
        let e = makeEngine()
        load(e, LabBoards.warmEffectsBoard())
        XCTAssertEqual(e.obstacles.doors[ObstacleID("d0")]?.state, "locked")
        let t0 = CACurrentMediaTime()
        tap(e, 5)                                           // the key arrow: k0 flies to d0
        XCTAssertTrue(e.obstacles.keys[ObstacleID("k0")]?.used ?? false)
        waitFor(0.5) { e.preAttached.contains(ArrowID(6)) }
        XCTAssertTrue(e.preAttached.contains(ArrowID(6)), "the door's arrow waits under the door (attached in a later frame), not live")
        XCTAssertNil(e.tapPoint(of: ArrowID(6)))
        waitFor(3) { self.beats.contains { $0.0 == .doorBurst(ObstacleID("d0")) } }
        let at = try XCTUnwrap(beats.first { $0.0 == .doorBurst(ObstacleID("d0")) }?.1) - t0
        let planned = try XCTUnwrap(e.lastDoorBursts.last?.1)
        XCTAssertEqual(at, planned, accuracy: 0.05, "the beat comes from the burst animation (render clock)")
        waitFor(1) { e.obstacles.doors[ObstacleID("d0")]?.state == "open" }
        XCTAssertEqual(e.obstacles.doors[ObstacleID("d0")]?.state, "open")
        XCTAssertFalse(e.preAttached.contains(ArrowID(6)))
        XCTAssertNotNil(e.tapPoint(of: ArrowID(6)), "revealed: live and tappable")
    }

    // MARK: the pipe (MA §3.5.3): the shatter 0.05 s after the head leaves the far mouth

    func testPipeShattersAfterTheHeadLeaves() throws {
        let e = makeEngine()
        load(e, LabBoards.warmEffectsBoard())
        let plan = try XCTUnwrap(driver?.plan(ArrowID(7)))
        var leave = -1.0
        for b in plan.beats { if case let .leaveTube(_, _, s) = b { leave = e.kinematics.time(toTravel: s) } }
        XCTAssertGreaterThan(leave, 0)
        XCTAssertTrue(plan.beats.contains { if case .pipeBreak = $0 { return true }; return false }, "counter 1: this pass breaks it")
        let t0 = CACurrentMediaTime()
        tap(e, 7)
        waitFor(3) { self.beats.contains { $0.0 == .pipeBroken(ObstacleID("p0")) } }
        let at = try XCTUnwrap(beats.first { $0.0 == .pipeBroken(ObstacleID("p0")) }?.1) - t0
        XCTAssertEqual(at, leave + e.fx.pipeBreakAfterLeave, accuracy: 0.05)
        XCTAssertEqual(e.lastPipeBreaks.last?.2 ?? -1, leave + 0.05, accuracy: 0.001, "planned at leave + 0.05 s")
        XCTAssertTrue(e.obstacles.pipes[ObstacleID("p0")]?.broken ?? false)
    }

    // MARK: boxes (MA §3.5.4): every box counts on the tap frame, together; the break reveals

    func testBoxesCountDownTogetherOnTheTapFrame() throws {
        let e = makeEngine()
        let level = try XCTUnwrap(LabBoards.level("L011", bundle: .main))
        load(e, level)
        let before = e.obstacles.boxes.values.map { $0.remaining ?? -1 }.sorted()
        XCTAssertEqual(before, [8, 13])
        let free = try XCTUnwrap(driver?.freeUnits().first(where: { $0.count == 1 })?.first)
        tap(e, free.raw)
        let after = e.obstacles.boxes.values.map { $0.remaining ?? -1 }.sorted()
        XCTAssertEqual(after, [7, 12], "both boxes lowered on the tap frame (no wait)")
        XCTAssertEqual(e.obstacles.boxes.values.compactMap { $0.digits?.shown }.sorted(), [7, 12], "the digits swapped at once")
    }

    func testBoxBreakRevealsItsArrowOnTheSameFrame() throws {
        let e = makeEngine()
        load(e, LabBoards.warmEffectsBoard())
        XCTAssertNil(e.tapPoint(of: ArrowID(9)), "under the box")
        tap(e, 0)                                           // the taped bundle: the box (counter 1) breaks on this exit
        XCTAssertTrue(e.obstacles.boxes[ObstacleID("b0")]?.broken ?? false)
        XCTAssertTrue(e.nodes[ArrowID(9)]?.attached ?? false, "revealed on the tap frame")
        waitFor(1) { self.beats.contains { $0.0 == .counterBroken(ObstacleID("b0")) } }
        XCTAssertTrue(beats.contains { $0.0 == .counterBroken(ObstacleID("b0")) })
    }

    // MARK: the elevator (MA §3.5.5): live at the tap, shown from O + 0.02 under the tint

    func testElevatorActivatesAndRevealsLayerTwoUnderThePlatform() throws {
        let e = makeEngine()
        load(e, LabBoards.warmEffectsBoard())
        tap(e, 8)                                           // the last platform arrow
        let node = try XCTUnwrap(e.obstacles.elevators[ObstacleID("e0")])
        XCTAssertTrue(node.active)
        let open = try XCTUnwrap(e.obstacles.elevatorOpen[ObstacleID("e0")])
        XCTAssertGreaterThanOrEqual(open.o, 0.15)
        let n11 = try XCTUnwrap(e.nodes[ArrowID(11)])
        XCTAssertTrue(n11.attached)
        XCTAssertTrue(n11.body.superlayer === e.roots.under, "layer 2 sits under the platform")
        XCTAssertNotNil(n11.body.animation(forKey: "reveal"), "shown from O + 0.02 (render clock)")
        XCTAssertNotNil(e.tapPoint(of: ArrowID(11)), "live from the tap (rules elevator.activateAt tap)")
    }

    // MARK: the painters (MA §3.2.2): a colour FIELD fixed on the path

    func testColourFieldIsCyclicAndFixedOnThePath() {
        let e = makeEngine()
        let f = ColourField(palette: e.fx.rainbowPalette, period: e.fx.rainbowPeriod, phase: 0)
        XCTAssertEqual(e.fx.rainbowPeriod, 4.2, "CONSISTENCY E-12")
        XCTAssertEqual(e.fx.violetPalette.count, 6)
        XCTAssertEqual(e.fx.violetPeriod, 3.75)
        for sigma in [0.0, 1.3, 2.9] {
            let a = f.colour(sigma).components ?? [], b = f.colour(sigma + 4.2).components ?? []
            XCTAssertEqual(a.count, b.count)
            for (x, y) in zip(a, b) { XCTAssertEqual(Double(x), Double(y), accuracy: 1e-6, "one period later the same colour") }
        }
        XCTAssertEqual(f.stop(0), e.fx.rainbowPalette[0])
        XCTAssertEqual(f.stop(4.2 / 12), e.fx.rainbowPalette[1], "12 stops evenly over one period")
        XCTAssertTrue(e.painters["violet"] is FieldPainter)
        XCTAssertTrue(e.painters["rainbow"] is FieldPainter)
    }

    func testRainbowExitMasksAFieldAndABundleSharesItsTracks() throws {
        let e = makeEngine()
        e.trailOverride = .rainbow
        load(e, LabBoards.warmEffectsBoard())
        tap(e, 0)                                           // the 2-arrow taped bundle
        let m0 = try XCTUnwrap(e.movers[ArrowID(0)]), m1 = try XCTUnwrap(e.movers[ArrowID(1)])
        XCTAssertTrue(m0.straight && m1.straight)
        XCTAssertEqual(e.exitShares.count, 1, "both members use ONE set of tracks (F4)")
        XCTAssertTrue(m0.times == m1.times)
        let content = try XCTUnwrap(m0.extras.first)
        XCTAssertNotNil(content.mask, "the field is masked by the moving shapes")
        XCTAssertTrue(content.sublayers?.first is CAGradientLayer)
        XCTAssertGreaterThan((content.sublayers?.first as? CAGradientLayer)?.colors?.count ?? 0, 12)
        XCTAssertTrue(e.roots.fx.sublayers?.contains { $0 is CAEmitterLayer } ?? false, "trail stars")
    }

    // MARK: A3 GLITCH (owner item 5): no end-of-exit frame can draw the resting arrow again

    /// A straight exit's moving layers keep their MODEL at the final place (off the far rect) and run an additive track from
    /// −travelEnd (= the rest) to 0. Before A3 the model was the rest and the track went 0 → travelEnd, so the frame(s)
    /// between the track's end on the render server and the main thread's "end" beat drew the whole arrow back on its rest
    /// cells in the exit colour / the rainbow field (blipscan found it after straight exits in every recorded board).
    func testStraightExitModelSitsOffTheBoardSoItsEndFrameCannotShowTheRestingArrow() throws {
        for trail in [LaunchArgs.Trail.solid, .rainbow] {
            let e = makeEngine()
            e.trailOverride = trail
            load(e, LabBoards.hitBoard())
            let rest = try XCTUnwrap(e.nodes[ArrowID(2)]).body.frame.union(try XCTUnwrap(e.nodes[ArrowID(2)]).head.frame)
            let far = e.farRect()
            tap(e, 2)                                       // the isolated horizontal arrow: a straight exit to the right
            let m = try XCTUnwrap(e.movers[ArrowID(2)], "\(trail)")
            XCTAssertTrue(m.fastPath && m.straight, "\(trail): the rigid-translation path")
            let move = try XCTUnwrap(m.root.animation(forKey: "move") as? CAKeyframeAnimation, "\(trail)")
            XCTAssertTrue(move.isAdditive)
            let first = try XCTUnwrap((move.values?.first as? NSValue)?.cgPointValue)
            let last = try XCTUnwrap((move.values?.last as? NSValue)?.cgPointValue)
            XCTAssertEqual(last, .zero, "\(trail): the track ends ON the model (nothing to snap back to)")
            XCTAssertEqual(m.root.position.x + first.x, rest.midX, accuracy: 0.01, "\(trail): the track starts at the rest")
            XCTAssertEqual(m.root.position.y + first.y, rest.midY, accuracy: 0.01)
            XCTAssertEqual(m.headStartLocal.x, rest.midX, accuracy: 0.01, "BoardLab's kinematics origin stays the rest")
            // the model = the rest moved by travelEnd, where the TAIL has left the far rect (the arrow points right)
            let tail = try XCTUnwrap(e.nodes[ArrowID(2)]).rest.vertices[0]
            XCTAssertLessThan(first.x, 0)
            XCTAssertEqual(first.y, 0, accuracy: 0.001)
            XCTAssertGreaterThanOrEqual(tail.x - first.x, far.maxX, "\(trail): at its model place the tail is past \(far)")
            if trail == .rainbow {
                // the field's mask: the moving shapes it reveals the gradient through sit at the final place too
                let content = try XCTUnwrap(m.extras.first)
                let mover = try XCTUnwrap(content.mask?.sublayers?.first)
                XCTAssertEqual(mover.frame.minX + content.frame.minX - rest.minX, -first.x, accuracy: 0.01,
                               "the masked field's model is the final place")
                XCTAssertEqual(mover.frame.minY + content.frame.minY, rest.minY, accuracy: 0.01)
                XCTAssertNotNil(mover.animation(forKey: "move"))
            }
            window?.isHidden = true
        }
    }

    // MARK: G-9: a tap on a moving arrow is ignored, never re-targeted

    func testTapOnAnArrowThatJustLeftIsReportedAsThatArrow() throws {
        let e = makeEngine()
        let level = LabBoards.hitBoard()
        load(e, level)
        driver = nil                                                        // report only (no session)
        e.present(LabRules(level: level).tap(ArrowID(2), at: 0))            // arrow 2 starts to exit
        let c = e.stage!.geo.centre(Cell(1, 7))                            // its tail cell, just vacated
        e.handleRelease(screenPoint: e.contentToScreen(c), touchTimestamp: CACurrentMediaTime())
        XCTAssertEqual(e.lastTapArrow, ArrowID(2), "the moving arrow is reported (the session ignores it: .moving)")
    }

    // MARK: F1: a big board attaches over frames; the old board goes over frames too

    func testLoadSplitsTheAttachAndRetiresTheOldSetOverFrames() throws {
        let e = makeEngine()
        load(e, LabBoards.warmEffectsBoard())
        let first = e.roots
        let synth = LabBoards.synthetic(cols: 40, rows: 40, seed: 7, meanLength: 3.0, id: 9040)
        e.load(StageSetup(level: synth, screen: CGSize(width: 393, height: 852), config: e.config))
        XCTAssertFalse(e.roots === first, "the new board goes to the other root set")
        XCTAssertTrue(first.intro.isHidden, "the old board is hidden at once")
        XCTAssertEqual(e.pendingAttach.count, synth.arrows.count - e.fx.attachPerFrame, "the rest attach in the next frames")
        XCTAssertLessThan(e.lastLoadMs, 50)
        waitFor(2) { e.pendingAttach.isEmpty && e.teardown.isEmpty }
        XCTAssertTrue(e.pendingAttach.isEmpty)
        XCTAssertEqual(e.roots.rest.sublayers?.count, 2 * synth.arrows.count)
        XCTAssertEqual(first.removable().count, 0, "the old set emptied")
    }

    // MARK: the stage transition (MA §3.7): swap at W + 0.70 s, done at the end of the draw-in

    func testStageTransitionSwapsAtTheGapAndDrawsTheNextBoard() throws {
        let e = makeEngine()
        let l1 = try XCTUnwrap(LabBoards.level("L001", bundle: .main))
        let l2 = try XCTUnwrap(LabBoards.level("L002", bundle: .main))
        load(e, l1, more: [l2])
        let old = e.roots
        let t0 = CACurrentMediaTime()
        e.playStageTransition(to: StageSetup(level: l2, stage: 1, stages: 2, seed: 1, screen: CGSize(width: 393, height: 852),
                                             config: e.config))
        XCTAssertEqual(e.stageSwapPlanned?.gap ?? 0, 0.7, accuracy: 1e-9)
        XCTAssertEqual(e.stage?.level.level, 1, "the state still belongs to stage 1 during the gap")
        waitFor(3) { self.beats.contains { $0.0 == .stageTransitionDone } }
        let done = try XCTUnwrap(beats.first { $0.0 == .stageTransitionDone }?.1) - t0
        XCTAssertEqual(e.stage?.level.level, 2)
        XCTAssertFalse(e.roots === old)
        let longest = l2.arrows.map { e.drawDuration($0.cells.count) }.max() ?? 0
        XCTAssertEqual(done, 0.7 + longest, accuracy: 0.06)
    }

    func testClearWaveReportsAtHalfASecond() throws {
        let e = makeEngine()
        load(e, LabBoards.hitBoard())
        let t0 = CACurrentMediaTime()
        e.playClearWave()
        XCTAssertTrue(e.roots.dots.sublayers?.contains { $0.mask != nil } ?? false, "the ring over the dots (masked)")
        waitFor(2) { self.beats.contains { $0.0 == .clearWaveFinished } }
        let at = try XCTUnwrap(beats.first { $0.0 == .clearWaveFinished }?.1) - t0
        XCTAssertEqual(at, 0.5, accuracy: 0.05)
    }

    // MARK: pan limit (MA §3.9): the play-rect centre reaches, never passes, the grid edge

    func testPanLimitKeepsThePlayCentreOverTheGrid() {
        let e = makeEngine()
        load(e, LabBoards.hitBoard())
        let s = e.container.scroll
        XCTAssertTrue(s.centreInGrid)
        let z: CGFloat = 1
        let inset = s.insets(forZoom: z)
        let m = s.gridMargin * z
        // the farthest left offset puts the grid's left edge (content x = m) at the play-rect centre
        let offMin = -inset.left
        XCTAssertEqual(m * z - offMin, s.playRect.midX, accuracy: 0.001)
        let offMaxY = e.contentBounds.height * z + inset.bottom - s.bounds.height
        XCTAssertEqual((e.contentBounds.height - m) * z - offMaxY, s.playRect.midY, accuracy: 0.001)
    }

    // MARK: the corner (FIX-2 A, L02; art/lanes/corner.md code requests 1-3, the measured hit of corner_anim.py)

    /// A 10 × 10 board with one corner of `turn` at (5, 5) and a far arrow (the corner layers need no rule traffic).
    private func cornerLevel(_ turn: CornerTurn) -> LevelSpec {
        LevelSpec(level: 9300, source: .designed, cols: 10, rows: 10, timerSeconds: 180,
                  arrows: [ArrowSpec(id: ArrowID(0), cells: [Cell(0, 0), Cell(1, 0)], dir: .right)],
                  obstacles: [ObstacleSpec(id: "c0", kind: .corner, cells: [Cell(5, 5)], turn: turn)])
    }

    func testCornerLayerIsTwoPitchesAndUsesTheFacingsSprites() throws {
        let e = makeEngine()
        e.sprites.preload(CornerNode.spriteIDs)
        waitFor(2) { CornerNode.spriteIDs.allSatisfy { e.sprites.image($0) != nil } }
        XCTAssertEqual(BoardArt.names.filter { $0.hasPrefix("corner") }.count, 9, "the 8 facing layers + cornerWedge are preloaded")
        for turn in CornerTurn.allCases {
            let level = cornerLevel(turn)
            let layout = e.config.layout(for: level, screen: CGSize(width: 393, height: 852))
            let geo = BoardGeometry(layout: layout, config: e.config, screenScale: 3)
            let p = CGFloat(layout.pitch)
            let c = CornerNode(spec: level.obstacles[0], geo: geo, art: e.boardArt, scale: 3)
            // request 1: the sprite's own frame (64 pt at the 32 pt design pitch = 2 × 2 pitch), centred on the cell centre
            XCTAssertEqual(c.layer.bounds.width, 2 * p, accuracy: 0.001, "\(turn): 2 pitches wide (was 1: half size)")
            XCTAssertEqual(c.layer.bounds.height, 2 * p, accuracy: 0.001)
            let centre = geo.centre(Cell(5, 5))
            XCTAssertEqual(c.layer.position.x, centre.x, accuracy: 0.001)
            XCTAssertEqual(c.layer.position.y, centre.y, accuracy: 0.001)
            XCTAssertTrue(CATransform3DIsIdentity(c.layer.transform), "\(turn): never rotated")
            // request 2: the facing's OWN spring + plate, spring under the plate, both the full frame
            let spring = try XCTUnwrap(c.spring, "\(turn): spring layer")
            let plate = try XCTUnwrap(c.plate, "\(turn): plate layer")
            let ids = CornerNode.layerIDs(turn)
            XCTAssertTrue((spring.contents as AnyObject?) === e.sprites.image(ids.spring), "\(turn): \(ids.spring)")
            XCTAssertTrue((plate.contents as AnyObject?) === e.sprites.image(ids.plate), "\(turn): \(ids.plate)")
            let subs = c.layer.sublayers ?? []
            let si = try XCTUnwrap(subs.firstIndex { $0 === spring }), pi = try XCTUnwrap(subs.firstIndex { $0 === plate })
            XCTAssertLessThan(si, pi, "\(turn): the plate draws over the spring")
            XCTAssertEqual(plate.frame.width, 2 * p, accuracy: 0.001)
            XCTAssertEqual(spring.frame.width, 2 * p, accuracy: 0.001)
            XCTAssertEqual(spring.frame.midX, p, accuracy: 0.001, "\(turn): the spring's frame stays centred")
            XCTAssertEqual(spring.frame.midY, p, accuracy: 0.001)
            // the spring scales about its FOOT: cell centre - 0.98 p along the facing (corner.md: upRight anchor 0.1535)
            let s = CornerNode.facing(turn)
            XCTAssertEqual(spring.position.x, p - 0.98 * p * s.dx, accuracy: 0.001, "\(turn): the foot pivot")
            XCTAssertEqual(spring.position.y, p - 0.98 * p * s.dy, accuracy: 0.001)
            let expected: [CornerTurn: CGPoint] = [.upRight: CGPoint(x: 0.1535, y: 0.1535), .upLeft: CGPoint(x: 0.8465, y: 0.1535),
                                                   .downLeft: CGPoint(x: 0.8465, y: 0.8465), .downRight: CGPoint(x: 0.1535, y: 0.8465)]
            XCTAssertEqual(spring.anchorPoint.x, expected[turn]!.x, accuracy: 0.0005, "\(turn): anchor per corner.md")
            XCTAssertEqual(spring.anchorPoint.y, expected[turn]!.y, accuracy: 0.0005)
        }
        // the level's preload list names the facing's pair (the validator's cornerWedge stays)
        XCTAssertEqual(Set(ObstacleSet.spriteIDs(cornerLevel(.upLeft))), ["cornerUpLeftSpring", "cornerUpLeftPlate", "cornerWedge"])
    }

    func testCornerHitCurveIsTheMeasuredTable() {
        let spec = CornerHitSpec()
        // corner.md's 60 Hz key table (hold 0.066 s, the clips' 3-cell arrows): t after the beat, plate offset (pitch)
        let table: [(Double, Double)] = [(-0.012, 0), (0.005, -0.093), (0.021, -0.096), (0.038, -0.099), (0.055, -0.101),
                                         (0.071, -0.104), (0.088, -0.089), (0.105, -0.026), (0.121, 0.046), (0.138, 0.079),
                                         (0.155, 0.062), (0.171, 0.019), (0.188, -0.020), (0.205, -0.030), (0.221, -0.027),
                                         (0.238, -0.021), (0.255, -0.014), (0.271, -0.007), (0.288, -0.002), (0.305, 0)]
        for (t, x) in table {
            XCTAssertEqual(spec.offset(t, hold: 0.066), x, accuracy: 0.005, "t \(t)")
        }
        // …and the clip's own measured frames (corner_anim.py MEASURED, clip 1): the fit's rms 0.0035 p, max 0.0093 p
        let measured: [(Double, Double)] = [(-0.015, -0.0023), (0.001, -0.0829), (0.018, -0.0946), (0.035, -0.0946), (0.051, -0.1024),
                                            (0.068, -0.1096), (0.084, -0.0885), (0.101, -0.0443), (0.118, 0.0371), (0.134, 0.0812),
                                            (0.151, 0.0649), (0.168, 0.0264), (0.184, -0.0126), (0.201, -0.0295), (0.218, -0.0283),
                                            (0.234, -0.0219), (0.251, -0.0151), (0.267, -0.0078), (0.284, -0.0034), (0.301, 0.0),
                                            (0.317, -0.0003)]
        var sq = 0.0, worst = 0.0
        for (t, x) in measured {
            let d = spec.offset(t, hold: 0.066) - x
            sq += d * d
            worst = max(worst, abs(d))
        }
        XCTAssertLessThanOrEqual((sq / Double(measured.count)).squareRoot(), 0.004, "rms vs the clip")
        XCTAssertLessThanOrEqual(worst, 0.035, "max vs the clip (its first pressed frame is half under the head)")
        // the spring: 0.849 fully pressed, 1.114 at the overshoot (k = 1 + x / 0.694)
        XCTAssertEqual(spec.springScale(-0.105), 0.849, accuracy: 0.001)
        XCTAssertEqual(spec.springScale(0.079), 1.114, accuracy: 0.001)
        // board.json carries the measured numbers (the retired pop keys are gone)
        let fx = EffectsConfig(Tuning.load(bundle: .main).board)
        XCTAssertEqual(fx.cornerHit, spec, "board.json corner.* = the measured spec")
    }

    func testCornerHitAnimationFollowsTheMeasuredTable() throws {
        let e = makeEngine()
        e.sprites.preload(CornerNode.spriteIDs)
        waitFor(2) { CornerNode.spriteIDs.allSatisfy { e.sprites.image($0) != nil } }
        load(e, LabBoards.cornerBoard())
        let corner = try XCTUnwrap(e.obstacles.corners[ObstacleID("c0")])
        let plate = try XCTUnwrap(corner.plate), spring = try XCTUnwrap(corner.spring)
        let plan = try XCTUnwrap(driver?.plan(ArrowID(0)))
        var beatS = -1.0
        for b in plan.beats { if case let .corner(_, _, s) = b { beatS = s } }
        XCTAssertGreaterThan(beatS, 0, "the lab arrow turns at the corner")
        let tapStage = Anim.now(e.roots.obstacle)
        tap(e, 0)
        let a = try XCTUnwrap(plate.animation(forKey: "cornerHit") as? CAKeyframeAnimation, "the plate's hit track")
        let sa = try XCTUnwrap(spring.animation(forKey: "cornerHit") as? CAKeyframeAnimation, "the spring's hit track")
        XCTAssertNil(corner.layer.animationKeys(), "the frame itself does not move (no 1.15 scale pop)")
        let spec = e.fx.cornerHit
        let p = Double(corner.pitch)
        let hold = e.kinematics.time(toTravel: beatS + 1) - e.kinematics.time(toTravel: beatS)   // a 2-cell arrow: tail = s + 1
        // the track starts one press lead before the beat (the head at the cell centre, T(s) after the tap's motion start;
        // ± the frame lead of the tap's transaction) and ends at rest
        let beat = a.beginTime + spec.pressLead
        XCTAssertEqual(beat, tapStage + e.kinematics.time(toTravel: beatS), accuracy: 0.03)
        XCTAssertEqual(a.duration, spec.pressLead + spec.end(hold: hold), accuracy: 0.0001)
        XCTAssertEqual(sa.beginTime, a.beginTime, accuracy: 0.0001, "plate and spring share one clock")
        let vals = try XCTUnwrap(a.values as? [NSValue]), times = try XCTUnwrap(a.keyTimes?.map(\.doubleValue))
        let svals = try XCTUnwrap(sa.values as? [NSValue])
        XCTAssertEqual(vals.count, times.count)
        XCTAssertGreaterThanOrEqual(vals.count, 15, "sampled at 60 Hz")
        let s = corner.facing
        let rest = CGPoint(x: corner.side / 2, y: corner.side / 2)
        var minX = 0.0, maxX = 0.0
        for (i, v) in vals.enumerated() {
            let t = a.beginTime + times[i] * a.duration - beat          // after the beat
            let pt = v.cgPointValue
            let x = Double((pt.x - rest.x) * s.dx + (pt.y - rest.y) * s.dy) / p
            XCTAssertEqual(x, spec.offset(t, hold: hold), accuracy: 0.005, "key \(i) at t \(t)")
            // the plate moves along the facing only
            XCTAssertEqual(Double((pt.x - rest.x) * s.dy - (pt.y - rest.y) * s.dx), 0, accuracy: 0.001)
            // the spring's scale along s follows the plate (k = 1 + x / 0.694)
            let m = svals[i].caTransform3DValue
            let k = Double(m.m11 + m.m12 * (s.dx * s.dy > 0 ? 1 : -1))
            XCTAssertEqual(k, spec.springScale(x), accuracy: 0.002, "spring key \(i)")
            minX = min(minX, x); maxX = max(maxX, x)
        }
        XCTAssertEqual(minX, spec.holdEnd, accuracy: 0.01, "pressed to -0.105 p")
        XCTAssertEqual(maxX, spec.peak.x, accuracy: 0.01, "overshoot +0.079 p")
        XCTAssertEqual(Double(vals.last!.cgPointValue.x), Double(rest.x), accuracy: 0.0001, "at rest at the end")
    }

    // MARK: F3-B (2026-09-29): the shipped door boards as SPEC-gameplay §3.5 draws them (VERIFIED v552 L62 / L69 / L89)

    private func shipped(_ n: Int) throws -> LevelSpec {
        let folder = try XCTUnwrap(Bundle.main.resourceURL?.appendingPathComponent("Levels"))
        return try LevelLibrary.load(folder: folder).loadAuthored(n)
    }

    /// An obstacle lying wholly inside a door is UNDER it: it acts and is drawn only from that door's burst on. L59's three
    /// pipes lie under three of its doors; before the fix the tube root (above the doors) drew them across the shut doors.
    /// The obstacles NOT under a door (L99's other corners) are drawn from the load, as before.
    func testObstaclesUnderADoorAreDrawnOnlyFromItsBurst() throws {
        let e = makeEngine()
        let l59 = try shipped(59)
        load(e, l59)
        let hosted: [(String, String)] = [("p0", "d0"), ("p1", "d1"), ("p2", "d2")]
        for (p, d) in hosted {
            let pipe = try XCTUnwrap(e.obstacles.pipes[ObstacleID(p)], p)
            XCTAssertTrue(pipe.root.isHidden, "L59 \(p) lies under \(d): not drawn while \(d) is shut")
            XCTAssertTrue(e.obstacles.underDoor[ObstacleID(d)]?.contains { $0 === pipe.root } ?? false)
        }
        // the burst of d1 shows p1 only
        e.present([.doorOpened(ObstacleID("d1"), revealed: [])])
        waitFor(1) { e.obstacles.pipes[ObstacleID("p1")]?.root.isHidden == false }
        XCTAssertFalse(e.obstacles.pipes[ObstacleID("p1")]!.root.isHidden, "d1's burst draws the pipe under it")
        XCTAssertTrue(e.obstacles.pipes[ObstacleID("p0")]!.root.isHidden, "d0 is still shut")
        XCTAssertTrue(e.obstacles.pipes[ObstacleID("p2")]!.root.isHidden, "d2 is still shut")

        let e2 = makeEngine()
        let l99 = try shipped(99)
        load(e2, l99)
        let x0 = try XCTUnwrap(e2.obstacles.corners[ObstacleID("x0")])
        XCTAssertTrue(x0.layer.isHidden, "L99's x0 lies under d0")
        let others = l99.obstacles.filter { $0.kind == .corner && $0.id != ObstacleID("x0") }
        XCTAssertFalse(others.isEmpty)
        for o in others { XCTAssertFalse(e2.obstacles.corners[o.id]!.layer.isHidden, "\(o.id.raw) is not under a door: drawn from the load") }
        e2.present([.doorOpened(ObstacleID("d0"), revealed: [])])
        waitFor(1) { !x0.layer.isHidden }
        XCTAssertFalse(x0.layer.isHidden, "d0's burst draws the corner under it")
    }

    /// A door-hidden arrow may poke out of its door, its humps drawn above the door frame from the start (L58's 53-cell key
    /// arrow 49 over the bottom door d0). It is drawn from the load but inert (no tap point, a hidden probe arrow) until the
    /// burst reveals it; the arrows wholly inside a door still attach only at the key's dispatch.
    func testADoorStubIsDrawnFromTheLoadButInertUntilTheBurst() throws {
        let e = makeEngine()
        let l58 = try shipped(58)
        load(e, l58)
        let stub = ArrowID(49)
        let spec = try XCTUnwrap(l58.arrows.first { $0.id == stub })
        let door = try XCTUnwrap(l58.obstacles.first { $0.id == spec.hiddenBy })
        XCTAssertFalse(Set(spec.cells).isSubset(of: Set(door.cells)), "the fixture: arrow 49 pokes out of its door")
        let n = try XCTUnwrap(e.nodes[stub])
        XCTAssertTrue(n.attached, "drawn from the load (its humps show above the door frame)")
        XCTAssertFalse(n.body.isHidden)
        XCTAssertTrue(e.preAttached.contains(stub), "not live while the door is shut")
        XCTAssertNil(e.tapPoint(of: stub))
        let inside = l58.arrows.filter { a in
            guard let d = a.hiddenBy, let o = l58.obstacles.first(where: { $0.id == d }) else { return false }
            return Set(a.cells).isSubset(of: Set(o.cells))
        }
        XCTAssertFalse(inside.isEmpty)
        for a in inside { XCTAssertFalse(e.nodes[a.id]?.attached ?? true, "arrow \(a.id.raw) lies wholly under its door: attached at the key's dispatch") }
        e.present([.doorOpened(door.id, revealed: l58.arrows.filter { $0.hiddenBy == door.id }.map(\.id))])
        waitFor(1) { !e.preAttached.contains(stub) }
        XCTAssertFalse(e.preAttached.contains(stub))
        XCTAssertNotNil(e.tapPoint(of: stub), "revealed: live and tappable")
    }
}
