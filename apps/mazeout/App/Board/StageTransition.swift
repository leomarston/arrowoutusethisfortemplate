import UIKit
import PathCore

// B2 (SPEC-architecture §5.7 "Stage transition", §5.9, §10.2 "Level start"; SPEC-motion-audio §3.7; D1a finding F1).
//
// DOUBLE-BUFFERED STAGE ROOTS. The stage layer (freeze / slow motion, §5.12) holds two complete root sets (each: the
// intro container → dots, under, platform, rest, obstacle, tape, mover, tube, fx) and the shared fx overlay (shards).
// One set is active; the other is either empty or being torn down. That gives:
//  - F1 (a board (re)load dropped 1–2 frames on the iPhone 15, 33–50 ms): a load never removes the old board's ~600
//    layers in its own frame — the old set is hidden (one property) and emptied `load.teardownPerFrame` layers per
//    frame; the new board's rest arrows attach at most `load.attachPerFrame` arrows per frame (arrows attached late join
//    the build-in at its common begin time, so they draw in phase); nodes, paths, the hit test and the dots are built at
//    once (cheap, measured in the lab);
//  - the stage transition (Levels 1-4, §3.7) is RENDER-EXACT: at W the clear wave runs on the old set and its dots fade
//    (W + 0.12, 0.56 s); the next stage is built into the other set at once, hidden; both sets swap by discrete opacity
//    keyframes at exactly W + 0.70 (board.json `stageGap`); the new arrows draw tail → head from W + 0.70 (no zoom, no
//    HUD intro); the engine's state swaps to the new stage from a beat at W + 0.70 (main thread, never a timer) and
//    `.stageTransitionDone` comes at the end of the longest draw.

@MainActor final class StageRoots {
    unowned let stage: CALayer
    let name: String
    let intro = CALayer()
    let dots = CALayer()
    let under = CALayer()          // the elevator's hidden layer-2 arrows
    let platform = CALayer()       // elevator platforms
    let rest = CALayer()
    let obstacle = CALayer()
    let tape = CALayer()
    let mover = CALayer()
    let tube = CALayer()
    let fx = CALayer()
    let dotsPainter = DotsPainter()
    var retiring = false

    var children: [CALayer] { [dots, under, platform, rest, obstacle, tape, mover, tube, fx] }

    init(stage: CALayer, name: String) {
        self.stage = stage
        self.name = name
        for l in children { intro.addSublayer(l) }
        dots.addSublayer(dotsPainter.layer)
    }

    func setFrame(_ b: CGRect) {
        intro.frame = b
        for l in children { l.frame = b }
    }

    /// Every layer this set holds except the dots painter's (the teardown list).
    func removable() -> [CALayer] {
        var out: [CALayer] = []
        for root in children {
            for l in root.sublayers ?? [] where l !== dotsPainter.layer { out.append(l) }
        }
        return out
    }
}

/// A stage built into a root set (installed at once by `load`, or at the swap beat of a stage transition).
@MainActor struct StageBuild {
    let setup: StageSetup
    let geo: BoardGeometry
    var hit: HitTester
    var nodes: [ArrowID: ArrowNode]
    var tapes: [ObstacleID: CALayer]
    var tapeOf: [ArrowID: ObstacleID]
    var obstacles: ObstacleSet
    /// Visible arrows still to attach (in order), and the set they go to.
    var pending: [ArrowNode]
    let set: StageRoots
    var buildMs: Double
    /// F3-B: door-hidden arrows that poke out of their door (L58's key-arrow humps), attached with the visible ones but not
    /// live: they start as the engine's `preAttached` (drawn, covered by their door where they lie inside it).
    var stubs: Set<ArrowID> = []
}

extension BoardEngine {
    // MARK: sets

    var spareSet: StageRoots { roots === setA ? setB : setA }

    /// Hides a set at once and queues its layers for removal (`load.teardownPerFrame` per display-link frame).
    func retire(_ set: StageRoots) {
        guard !set.retiring else { return }
        set.intro.isHidden = true
        set.intro.removeAllAnimations()
        for c in set.children { c.removeAllAnimations() }
        let list = set.removable()
        guard !list.isEmpty else { return }
        set.retiring = true
        teardown.append(contentsOf: list)
        teardownSets.append(set)
    }

    /// Removes the next batch of retired layers (display link). Returns the number removed.
    @discardableResult
    func teardownStep(_ maxCount: Int) -> Int {
        guard !teardown.isEmpty else { finishTeardowns(); return 0 }
        let n = min(maxCount, teardown.count)
        CATransaction.begin(); CATransaction.setDisableActions(true)
        for l in teardown[0..<n] { l.removeFromSuperlayer() }
        CATransaction.commit()
        teardown.removeFirst(n)
        if teardown.isEmpty { finishTeardowns() }
        return n
    }

    private func finishTeardowns() {
        for s in teardownSets {
            s.retiring = false
            s.dotsPainter.reset(frame: s.dots.bounds, color: config.dotColor, scale: screenScale)
            s.dots.opacity = 1
            s.dots.removeAllAnimations()
        }
        teardownSets = []
    }

    /// The set a new build goes to: the spare, emptied synchronously if its teardown is still running (rare).
    func takeSpare() -> StageRoots {
        let s = spareSet
        if s.retiring {
            CATransaction.begin(); CATransaction.setDisableActions(true)
            let mine = Set(s.removable().map { ObjectIdentifier($0) })
            for l in s.removable() { l.removeFromSuperlayer() }
            teardown.removeAll { mine.contains(ObjectIdentifier($0)) }
            CATransaction.commit()
            s.retiring = false
            teardownSets.removeAll { $0 === s }
        }
        CATransaction.begin(); CATransaction.setDisableActions(true)
        s.dotsPainter.reset(frame: s.dots.bounds, color: config.dotColor, scale: screenScale)
        s.dots.opacity = 1
        s.dots.removeAllAnimations()
        s.intro.removeAllAnimations()
        s.intro.opacity = 1
        s.intro.transform = CATransform3DIdentity
        CATransaction.commit()
        return s
    }

    // MARK: build

    /// Builds a stage into `set` (layers created; the first `attachPerFrame` visible arrows attached, hidden until an
    /// intro / draw shows them). Call inside a no-actions transaction.
    func buildStage(_ setup: StageSetup, into set: StageRoots) -> StageBuild {
        let t0 = CACurrentMediaTime()
        let level = setup.level
        let scale = screenScale
        let geo = BoardGeometry(layout: setup.layout, config: config, screenScale: scale)
        var hit = HitTester(level: level, layout: setup.layout, metrics: config.arrowMetrics)
        let bounds = CGRect(origin: .zero, size: setup.layout.contentSize)
        set.setFrame(bounds)
        set.dotsPainter.reset(frame: bounds, color: config.dotColor, scale: scale)
        var nodes: [ArrowID: ArrowNode] = [:]
        nodes.reserveCapacity(level.arrows.count)
        var visible: [ArrowNode] = []
        var dotCells: [Cell] = []
        dotCells.reserveCapacity(level.arrows.reduce(0) { $0 + $1.cells.count })
        // F3-B (SPEC-gameplay §3.5, VERIFIED v552 L62): a door-hidden arrow may poke out of its door, and its humps show above
        // the door frame from the start. Such an arrow is drawn from the load (the door covers the rest of it) but stays inert
        // (no hit-test entry, `preAttached`) until the burst reveals it. Before, hidden arrows attached only at the key
        // dispatch, so L58's humps were missing at the start and popped in ~1.2 s before the burst.
        var doorCells: [ObstacleID: Set<Cell>] = [:]
        for o in level.obstacles where o.kind == .door { doorCells[o.id] = Set(o.cells) }
        var stubs: Set<ArrowID> = []
        for a in level.arrows {
            let n = ArrowNode(spec: a, geo: geo, ink: config.ink, red: config.markedColor, scale: scale)
            nodes[a.id] = n
            dotCells.append(contentsOf: a.cells)                  // MA §3.2.4: every arrow cell at load, hidden ones too
            if a.layer <= 1, let d = a.hiddenBy, let dc = doorCells[d], a.cells.contains(where: { !dc.contains($0) }) {
                stubs.insert(a.id)
                visible.append(n)
                continue
            }
            guard a.hiddenBy == nil && a.layer <= 1 else { continue }
            hit.insert(a.id, cells: a.cells)
            visible.append(n)
        }
        let tNodes = CACurrentMediaTime()
        set.dotsPainter.add(cells: dotCells, geo: geo)
        let tDots = CACurrentMediaTime()
        let tapes = TapeLayer.build(level, geo: geo, cache: sprites, scale: scale)
        for l in tapes.values { set.tape.addSublayer(l) }
        var tapeOf: [ArrowID: ObstacleID] = [:]
        for o in level.obstacles where o.kind == .tape { for a in o.arrows { tapeOf[a] = o.id } }
        let obs = ObstacleSet.build(level, geo: geo, art: boardArt, roots: set, scale: scale, cornerHit: fx.cornerHit)   // FIX-2 A (L02)
        let tObs = CACurrentMediaTime()
        // the first batch now; the rest over the next frames (F1)
        let first = min(visible.count, fx.attachPerFrame)
        for n in visible[0..<first] {
            n.attach(to: set.rest)
            n.setVisible(false)
        }
        let rest = Array(visible[first...])
        let t1 = CACurrentMediaTime()
        let ms = (t1 - t0) * 1000
        lastBuildParts = String(format: "nodes %.2f dots %.2f tapes+obstacles %.2f attach %.2f", (tNodes - t0) * 1000,
                                (tDots - tNodes) * 1000, (tObs - tDots) * 1000, (t1 - tObs) * 1000)
        return StageBuild(setup: setup, geo: geo, hit: hit, nodes: nodes, tapes: tapes, tapeOf: tapeOf, obstacles: obs,
                          pending: rest, set: set, buildMs: ms, stubs: stubs)
    }

    /// Makes a build the engine's current stage.
    func install(_ b: StageBuild) {
        stageToken += 1
        // the previous stage's prepared exits are released over the next idle frames, not in the load's frame (hundreds of
        // tracks and paths)
        prepGraveyard.append(contentsOf: exitPreps.values)
        exitPreps = [:]
        shareGraveyard.append(contentsOf: exitShares.values)
        exitShares = [:]
        roots = b.set
        stage = StageState(setup: b.setup, geo: b.geo, hit: b.hit)
        nodes = b.nodes
        tapes = b.tapes
        tapeOf = b.tapeOf
        obstacles = b.obstacles
        pendingAttach = b.pending
        exited = []
        preAttached = b.stubs                                   // F3-B: door stubs are drawn, not live
        movers = [:]
        lastExitReported = false
    }

    /// Attaches the next batch of pending arrows (display link); late arrows join a running draw-in in phase.
    func attachStep() {
        guard !pendingAttach.isEmpty, let st = stage else { return }
        let n = min(fx.attachPerFrame, pendingAttach.count)
        let batch = pendingAttach[0..<n]
        pendingAttach.removeFirst(n)
        CATransaction.begin(); CATransaction.setDisableActions(true)
        for node in batch where !exited.contains(node.id) {
            node.attach(to: roots.rest)
            if let d = drawIn {
                node.setVisible(true)
                addDraw(node, begin: d.begin)
            } else {
                node.setVisible(introShown)
            }
        }
        CATransaction.commit()
        if pendingAttach.isEmpty {
            Log.debug("board", "L\(st.level.level): every arrow attached (\(loadFrames) frames)")
        }
    }

    /// During a transition gap: the incoming stage's remaining arrows go to ITS (hidden) set, drawing from the swap time.
    func attachStepNext() {
        guard var b = pendingNext, !b.pending.isEmpty else { return }
        let n = min(fx.attachPerFrame, b.pending.count)
        let batch = b.pending[0..<n]
        b.pending.removeFirst(n)
        CATransaction.begin(); CATransaction.setDisableActions(true)
        for node in batch {
            node.attach(to: b.set.rest)
            node.setVisible(true)
            addDraw(node, begin: pendingNextDraw)
        }
        CATransaction.commit()
        pendingNext = b
    }

    // MARK: draw-in (intro and stage transitions)

    /// strokeEnd f0 = a + b/n → 1 over D(n) = drawBase + drawPerCell·n (linear); the head appears when reached.
    func drawDuration(_ cells: Int) -> Double { config.introDrawBase + config.introDrawPerCell * Double(cells) }

    func addDraw(_ n: ArrowNode, begin: CFTimeInterval) {
        let cells = n.spec.cells.count
        let d = drawDuration(cells)
        let f0 = min(1, fx.drawStartA + fx.drawStartB / Double(max(1, cells)))
        let draw = Anim.basic("strokeEnd", from: f0, to: 1, duration: d, begin: begin)
        draw.timingFunction = Ease2.linear
        n.body.add(draw, forKey: "intro")
        let appear = max(0, d - 1.0 / 60)
        n.head.add(Anim.keyframes("opacity", [0, 0, 1], times: [0, appear, d], duration: d, begin: begin), forKey: "intro")
    }

    // MARK: the stage transition (§3.7)

    func runStageTransition(to next: StageSetup) {
        guard stage != nil, laidOutOnce else {
            doLoad(next)
            runStageDrawIn(begin: Anim.now(roots.stage), report: true)
            return
        }
        transitionRunning = true
        transitionID += 1
        let tid = transitionID
        let old = roots
        let W = Anim.now(stageLayer)
        let gap = max(0.05, config.stageGap)
        runClearWave(begin: W, report: false)
        // the old dots fade (W + 0.12, 0.56 s), the whole old set goes at W + gap
        let f0 = fx.dotsFadeFrom, fd = max(0.01, fx.dotsFade)
        let fade = Anim.keyframes("opacity", [1, 1, 0, 0].map { NSNumber(value: $0) }, times: [0, f0, f0 + fd, max(f0 + fd, gap)],
                                  duration: max(f0 + fd, gap), begin: W)
        fade.fillMode = .forwards
        CATransaction.begin(); CATransaction.setDisableActions(true)
        old.dots.opacity = 0
        old.dots.add(fade, forKey: "stageFade")
        Anim.switchOpacity(old.intro, from: 1, to: 0, begin: W, at: gap, key: "stageOut")
        // the next stage, built now into the other set, shown from W + gap
        let set = takeSpare()
        set.intro.isHidden = false
        var b = buildStage(next, into: set)
        // FEEL (OWNER P0 19:40, G2 19:28): the next board sits where a direct load of it would put it — centred in the play
        // rect at zoom 1. Until the swap installs its own scroll geometry, the set is placed in the CURRENT content space
        // (the old stage's zoom and offset) by a transform that maps it onto that final screen position; the swap then sets
        // the geometry and drops the transform in one transaction, so nothing moves on screen.
        placeIncoming(set, layout: next.layout)
        Anim.switchOpacity(set.intro, from: 0, to: 1, begin: W, at: gap, key: "stageIn")
        var longest = 0.0
        for a in next.level.arrows {
            guard let n = b.nodes[a.id], n.attached else { continue }
            n.setVisible(true)
            addDraw(n, begin: W + gap)
            longest = max(longest, drawDuration(a.cells.count))
        }
        for a in next.level.arrows where a.hiddenBy == nil && a.layer <= 1 {
            longest = max(longest, drawDuration(a.cells.count))
        }
        CATransaction.commit()
        b.pending = b.pending.filter { !$0.attached }
        pendingNext = b
        pendingNextDraw = W + gap
        let buildMs = b.buildMs
        context = "stageGap L\(next.level.level)"
        noteFirst("stageGap")
        Log.mark("board", String(format: "stage transition → L%d: wave at W, dots fade W+%.2f, swap at W+%.2f (build %.2f ms)",
                                 next.level.level, f0, gap, buildMs))
        stageSwapPlanned = (W, gap)
        // the state swap at W + gap (a beat on the render clock, never a timer)
        Anim.beat(on: beatCarrier, key: "stageSwap\(beatSeq())", begin: W, delay: gap) { [weak self] _ in
            guard let self, self.transitionID == tid, let b = self.pendingNext else { return }
            self.pendingNext = nil
            let oldSet = self.roots
            // old movers are off the board by now: drop them with their layers (the set is hidden already)
            self.movers = [:]
            // FEEL: the incoming board must not move on screen at the swap (placeIncoming's transform → the real geometry)
            let probeP = CGPoint(x: b.set.intro.bounds.midX, y: b.set.intro.bounds.midY)
            let before = b.set.intro.convert(probeP, to: self.container.layer)
            self.installGeometry(b.setup.layout, set: b.set)
            let after = b.set.intro.convert(probeP, to: self.container.layer)
            Log.mark("board", String(format: "stage swap: the next board's centre on screen (%.1f, %.1f) → (%.1f, %.1f), moved %.2f pt",
                                     Double(before.x), Double(before.y), Double(after.x), Double(after.y),
                                     Double(hypot(after.x - before.x, after.y - before.y))))
            self.install(b)
            self.drawIn = (W + gap, true)
            self.introShown = true
            self.retire(oldSet)
            self.context = "stage L\(next.level.level)"
            Log.mark("board", "ready L\(next.level.level): \(next.level.arrows.count) arrows (stage \(next.stage + 1)/\(next.stages))")
            self.delegate?.boardZoomChanged(scale: self.zoomScale)
        }
        let doneAt = gap + longest
        Anim.beat(on: beatCarrier, key: "stageDone\(beatSeq())", begin: W, delay: doneAt) { [weak self] _ in
            guard let self, self.transitionID == tid else { return }
            self.transitionRunning = false
            self.drawIn = nil
            self.lastStageGap = (gap, doneAt)
            Log.mark("board", String(format: "stageTransitionDone %.3f s after W (swap at %.3f s)", doneAt, gap))
            self.delegate?.boardBeat(.stageTransitionDone)
        }
    }

    /// The incoming stage's set in the current content space: content point p of the next board shows at screen
    /// p − o_new (zoom 1, centred offset o_new); in the current space (zoom z, offset o) that is q = (p − o_new + o) / z.
    /// Pan and zoom stop until the swap (a pan in the gap would move the old space under the placed board).
    func placeIncoming(_ set: StageRoots, layout: BoardLayout) {
        let s = container.scroll
        s.setContentOffset(s.contentOffset, animated: false)          // stop a deceleration / bounce now
        s.isScrollEnabled = false
        s.pinchGestureRecognizer?.isEnabled = false
        let z = max(s.zoomScale, 0.0001)
        let o = s.contentOffset
        let size = layout.contentSize
        let oNew = s.centredOffset(contentSize: size)
        let c = CGPoint(x: size.width / 2, y: size.height / 2)
        set.intro.transform = CATransform3DMakeScale(1 / z, 1 / z, 1)
        set.intro.position = CGPoint(x: (c.x - oNew.x + o.x) / z, y: (c.y - oNew.y + o.y) / z)
        Log.debug("board", String(format: "stage placed: current zoom %.3f offset (%.1f, %.1f) → next centred offset (%.1f, %.1f)",
                                  Double(z), Double(o.x), Double(o.y), Double(oNew.x), Double(oNew.y)))
    }

    /// The scroll geometry of a stage (doLoad's): zoom 1 and its limits, the content size, the stage layers' frames, the
    /// grid margin, the insets, the centred offset; the incoming set's placement transform goes in the same transaction.
    func installGeometry(_ layout: BoardLayout, set: StageRoots) {
        let s = container.scroll
        let limits = config.zoomLimits(layout)
        let size = layout.contentSize
        let bounds = CGRect(origin: .zero, size: size)
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        s.minimumZoomScale = 1
        s.maximumZoomScale = 1
        s.zoomScale = 1
        s.content.frame = bounds
        s.contentSize = size
        s.minimumZoomScale = limits.min
        s.maximumZoomScale = limits.max
        stageLayer.frame = bounds
        sharedFX.frame = bounds
        set.intro.transform = CATransform3DIdentity
        set.intro.frame = bounds
        s.gridMargin = CGFloat(layout.pitch)
        s.updateInsets()
        s.contentOffset = s.centredOffset()
        s.isScrollEnabled = true
        s.pinchGestureRecognizer?.isEnabled = true
        CATransaction.commit()
    }

    /// A draw-in without zoom from `begin` (a transition with no previous stage).
    func runStageDrawIn(begin: CFTimeInterval, report: Bool) {
        guard let st = stage else { return }
        var longest = 0.0
        CATransaction.begin(); CATransaction.setDisableActions(true)
        for a in st.level.arrows {
            guard let n = nodes[a.id], n.attached else { continue }
            n.setVisible(true)
            addDraw(n, begin: begin)
            longest = max(longest, drawDuration(a.cells.count))
        }
        CATransaction.commit()
        drawIn = (begin, true)
        introShown = true
        transitionRunning = true
        Anim.beat(on: beatCarrier, key: "stageDone\(beatSeq())", begin: begin, delay: longest) { [weak self] _ in
            guard let self else { return }
            self.transitionRunning = false
            self.drawIn = nil
            if report { self.delegate?.boardBeat(.stageTransitionDone) }
        }
    }
}
