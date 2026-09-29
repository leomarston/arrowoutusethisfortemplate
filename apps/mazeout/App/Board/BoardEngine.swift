import UIKit
import SwiftUI
import PathCore

// B1 + B2 (SPEC-architecture §5.1–§5.12, §8.2, §9.4, §10.3). The one app-lifetime Core Animation board (D2): created at
// boot, warmed up behind Loading (`prepare`, §5.9), re-loaded per stage. It implements the ◆ BoardControlling contract:
//  - commands that arrive before the container's first layout are QUEUED and replayed after it (never awaits the layout
//    of a view that is not in a window, GP §13);
//  - input fires on RELEASE (ReleaseTapRecognizer, grid-maths hit test) and the ripple + the delegate's session call +
//    the movers all land in the release handler's run-loop turn (D8, §8.2);
//  - every motion is a CAAnimation on the render server; beats come back from animation delegates, never timers;
//  - it owns the app's single CADisplayLink (the master clock: `boardFrame`, PerfMonitor, LatencyProbe, the probe,
//    the debug overlay, and B2's split loads: the batched attach / teardown of F1).
// B2: the stage layer holds TWO root sets (StageTransition.swift: double-buffered loads and render-exact stage
// transitions) and the shared fx overlay (the shard pool); the combo painters, trail stars, every obstacle layer and its
// beats (ObstacleSet), the clear wave, the hint highlight.

@MainActor final class BoardEngine: NSObject, BoardControlling, UIScrollViewDelegate {
    // MARK: contract state
    weak var delegate: BoardDelegate?
    var view: UIView { container }
    var inputEnabled = false
    var allowedArrows: Set<ArrowID>?
    var zoomScale: CGFloat { container.scroll.zoomScale }
    var pitchOnScreen: CGFloat { CGFloat(stage?.layout.pitch ?? 0) * zoomScale }
    /// FIX-2 lane B (review): settled also means the PAN is at rest — no finger dragging, no deceleration and no bounce-back
    /// (a swipe past the pan limit springs back after the finger lifts: the "hit" board's 52 pt swipe ends 2.33 pt beyond it,
    /// 180.19 → 182.53, over ~0.3 s). Before, the probe read settled in the frames between the lift and the bounce, so
    /// BoardInputTests.testSwipePansWithoutFiring took its "after" position mid-bounce whenever a 4 Hz probe fell there
    /// (the same 182.525 vs 180.1917 every time: the release point and the rest point, both deterministic).
    var isSettled: Bool {
        let pan = container.scroll
        return stage != nil && movers.isEmpty && !introRunning && !transitionRunning && !warmingUp && pendingAttach.isEmpty
            && pendingNext == nil && activeBursts == 0
            && !pan.isDragging && !pan.isDecelerating && !pan.isZooming && !pan.isZoomBouncing
    }

    // MARK: services
    let args: LaunchArgs
    let config: BoardConfig
    let fx: EffectsConfig
    let clock: MotionClock
    let perf: PerfMonitor
    let latency: LatencyProbe
    let bundle: Bundle
    let container = BoardContainerView()
    let sprites: SpriteCache
    let boardArt: BoardArt
    let shards: ShardPool
    let kinematics: ExitKinematics
    /// Exit painters by ladder name (B1: solid; B2 registers violet / rainbow).
    var painters: [String: ExitPainter] = ["solid": SolidPainter()]
    var missingPainters: Set<String> = []
    var trailOverride: LaunchArgs.Trail?
    /// Forces one painter by name (warm-up); wins over `-pc.trail` and the ladder.
    var forcedPainter: String?
    /// The effects stream (painter phases, star seeds); re-seeded per stage from `StageSetup.seed`.
    var fxRng = FXRandom(seed: 1, label: "fx")

    /// The stage layer (speed / timeOffset: freeze and slow motion, §5.12), shared by both root sets.
    let stageLayer = CALayer()
    /// Board-space overlay above both sets: the shard pool (arch §5.1 fxRoot, shared across a stage swap).
    let sharedFX = CALayer()
    /// An empty layer carrying engine-level beats on the stage clock.
    let beatCarrier = CALayer()
    let setA: StageRoots
    let setB: StageRoots
    /// The ACTIVE root set (B1's `roots`).
    var roots: StageRoots
    var dots: DotsPainter { roots.dotsPainter }

    // MARK: stage state
    struct StageState {
        let setup: StageSetup
        let geo: BoardGeometry
        var hit: HitTester
        var level: LevelSpec { setup.level }
        var layout: BoardLayout { setup.layout }
        var stage: Int { setup.stage }
        var stages: Int { setup.stages }
    }
    var stage: StageState?
    var nodes: [ArrowID: ArrowNode] = [:]
    var movers: [ArrowID: Mover] = [:]
    var tapes: [ObstacleID: CALayer] = [:]
    var tapeOf: [ArrowID: ObstacleID] = [:]
    var obstacles = ObstacleSet()
    var exited: Set<ArrowID> = []
    /// Revealed-to-be arrows attached under their (still closed) door: drawn, not live.
    var preAttached: Set<ArrowID> = []
    var hint: [ArrowID] = []
    var introRunning = false
    var transitionRunning = false
    var introStartLocal: CFTimeInterval = 0
    var lastExitReported = false
    /// The running build-in / draw-in (late-attached arrows join it in phase).
    var drawIn: (begin: CFTimeInterval, noZoom: Bool)?
    var introShown = false

    // MARK: F1 split loads
    var pendingAttach: [ArrowNode] = []
    var teardown: [CALayer] = []
    var teardownSets: [StageRoots] = []
    var pendingNext: StageBuild?
    var pendingNextDraw: CFTimeInterval = 0
    var stageSwapPlanned: (w: CFTimeInterval, gap: Double)?
    var lastStageGap: (gap: Double, done: Double)?
    /// Frames since the last load began (a hitch within 3 frames of it counts as a load hitch).
    private(set) var loadFrames = 1_000
    private(set) var hitchesLoad = 0
    private(set) var hitchesPlay = 0
    private(set) var lastLoadMs = 0.0
    var loadCommits: [(main: Double, total: Double)] = []
    var lastBuildParts = ""
    private var beatCounter = 0
    var activeBursts = 0
    var lastDoorBursts: [(ObstacleID, Double, Double)] = []
    var lastPipeBreaks: [(ObstacleID, Double, Double, Double)] = []
    var hintState: HintState?
    /// Shared exit tracks (StraightExit), by (direction, travel, pitch): kept for the stage (FEEL item 4: a later tap with
    /// the same travel reuses them; cleared at every stage install).
    var exitShares: [String: ExitShare] = [:]
    /// FEEL item 4: the release point whose ripple the tap's present adds after its movers; when it was added.
    var pendingRipple: CGPoint?
    private(set) var lastRippleAt: CFTimeInterval = 0
    /// FEEL F3: while a tap's exit / bump is built, the seconds its motion starts before now (stars use it too).
    var motionLead: CFTimeInterval = 0
    /// FEEL item 4: bent exits prepared in idle frames (ExitMover.swift `ExitPrep`), the pass's queue and keys.
    var exitPreps: [ArrowID: ExitPrep] = [:]
    var prepQueue: [ArrowID] = []
    var prepFarKey = ""
    var prepToken = -1
    var lastExitPrepHit = false
    /// Replaced stages' preps / shares, released a few per idle frame (FEEL: never in a load's frame).
    var prepGraveyard: [ExitPrep] = []
    var shareGraveyard: [ExitShare] = []
    /// FEEL item 4 (the same-frame proof's detail): the last present's main-thread ms and what it built ("S" straight / "B"
    /// bent exit, "P" bump; + painter initial; "+" = the shared track was reused).
    private(set) var lastPresentMs = 0.0
    var presentNotes: [String] = []
    /// Work moved off the tap's handler to the next display-link frames (one item per frame).
    var deferred: [() -> Void] = []
    /// `-pc.noFastExit 1`: every exit through B1's trimmed-stroke mover (comparison runs).
    lazy var fastExits: Bool = args.raw["pc.noFastExit"] == nil
    /// Bumped at every stage install: late beats of a replaced stage compare it and stay silent.
    var stageToken = 0
    /// A running stage transition's id (a clear / reload in its gap makes its late beats silent).
    var transitionID = 0

    // MARK: queue, clock, perf
    private(set) var laidOutOnce = false
    private var pending: [() -> Void] = []
    private var link: CADisplayLink?
    private var lastTimestamp: CFTimeInterval = 0
    private var skipFrames = 2
    private var lastProbeTime: CFTimeInterval = 0
    private var lastOverlayTime: CFTimeInterval = 0
    var lastProbeJSON = ""
    private var overlay: DebugOverlayView?
    var frozen = false
    var warmingUp = false
    var warmedUp = false
    var warmTask: Task<Void, Never>?
    /// FIX-B: the boot's cap passed while the warm-up ran (`hurryWarmUp`): its frame waits return at once.
    var warmHurry = false
    /// Frame waiters (warm-up, labs): resumed after N display-link frames.
    private var frameWaiters: [(Int, CheckedContinuation<Void, Never>)] = []
    /// Called every display-link frame (BoardLab).
    var frameHook: ((CADisplayLink) -> Void)?
    /// What the board was doing: the context of a `hitch` mark.
    var context = "idle"
    private var firstSeen: Set<String> = []
    private var firstWindows: [String: (frames: Int, maxMs: Double)] = [:]
    private(set) var firstResults: [String: Double] = [:]
    /// Main-thread cost of each release handler (touch handling + the delegate's session call + the board's present).
    private(set) var handlerMs: [Double] = []
    private(set) var lastTapArrow: ArrowID?
    /// Real touches only: touchesEnded → the release action (the recogniser's own delay, R1), and the touch-up's
    /// timestamp → touchesEnded (the system's / the harness's delivery).
    private(set) var recogniserMs: [Double] = []
    private(set) var deliveryMs: [Double] = []
    private(set) var taps = 0
    private let tap: ReleaseTapRecognizer

    // MARK: init

    init(_ ctx: AppContext) {
        args = ctx.args
        config = BoardConfig(ctx.tuning.board)
        fx = EffectsConfig(ctx.tuning.board)
        clock = ctx.clock
        perf = ctx.perf
        latency = ctx.latency
        bundle = ctx.bundle
        sprites = SpriteCache(capMB: config.spriteCacheCapMB, bundle: ctx.bundle)
        boardArt = BoardArt(cache: sprites)
        shards = ShardPool(fx: fx, size: 280)
        kinematics = config.kinematics
        trailOverride = ctx.args.trail
        tap = ReleaseTapRecognizer(target: nil, action: nil)
        setA = StageRoots(stage: stageLayer, name: "A")
        setB = StageRoots(stage: stageLayer, name: "B")
        roots = setA
        super.init()

        CATransaction.begin()
        CATransaction.setDisableActions(true)
        let content = container.scroll.content
        content.layer.addSublayer(stageLayer)
        stageLayer.addSublayer(setA.intro)
        stageLayer.addSublayer(setB.intro)
        stageLayer.addSublayer(sharedFX)
        stageLayer.addSublayer(beatCarrier)
        setB.intro.isHidden = true
        CATransaction.commit()

        let s = container.scroll
        s.delegate = self
        s.slack = config.panSlack
        s.centreInGrid = fx.panCentreInGrid
        s.bounces = config.panBounces
        s.bouncesZoom = fx.zoomBounces
        s.alwaysBounceVertical = config.panBounces
        s.alwaysBounceHorizontal = config.panBounces
        tap.addTarget(self, action: #selector(onRelease(_:)))
        tap.slop = config.slop
        if args.raw["pc.r1"] == "fallback" {
            tap.vetoScroll = s                      // R1 fallback: decide in touchesEnded
        } else {
            tap.require(toFail: s.panGestureRecognizer)
            if let pinch = s.pinchGestureRecognizer { tap.require(toFail: pinch) }
        }
        s.addGestureRecognizer(tap)
        container.probeElement.isHidden = !args.exposesProbe
        container.onLayout = { [weak self] size in self?.containerLaidOut(size) }
        container.onWindow = { [weak self] w in self?.windowChanged(w) }
        clock.observeTimeScale { [weak self] k in self?.applyClockScale(k) }
        latency.onSample = { [weak self] s in self?.logLatency(s) }
        installComboPainters()
        ExitProfile.on = args.raw["pc.profileExit"] != nil
        startLink()
        Log.mark("board", "engine up (B2): painters \(painters.keys.sorted().joined(separator: ",")), "
                 + "kinematics v0 \(config.exitV0) vmax \(config.exitVmax) tau \(config.exitTau)")
    }

    /// A unique beat key suffix.
    func beatSeq() -> Int { beatCounter += 1; return beatCounter }

    // MARK: geometry helpers

    var screenScale: CGFloat {
        let s = container.window?.screen.scale ?? container.traitCollection.displayScale
        return s > 0 ? s : 3
    }

    var contentBounds: CGRect { container.scroll.content.bounds }

    /// The visible screen in content coordinates.
    func visibleContentRect() -> CGRect {
        let s = container.scroll
        return s.convert(s.bounds, to: s.content)
    }

    /// The play rect in screen (container) coordinates.
    var playRectOnScreen: CGRect { config.playRect(in: container.bounds.size) }

    func contentToScreen(_ p: CGPoint) -> CGPoint { container.scroll.content.convert(p, to: container) }
    func screenToContent(_ p: CGPoint) -> CGPoint { container.convert(p, to: container.scroll.content) }

    // MARK: command queue

    /// Runs `body` now if the container has had its first layout, else queues it (the Arrows/MF rule).
    func enqueue(_ body: @escaping () -> Void) {
        if laidOutOnce { body() } else { pending.append(body) }
    }

    private func containerLaidOut(_ size: CGSize) {
        container.screenFX.configure(config, scale: screenScale)
        container.scroll.playRect = config.playRect(in: size)
        if !laidOutOnce {
            laidOutOnce = true
            let q = pending
            pending = []
            q.forEach { $0() }
        } else if stage != nil {
            container.scroll.updateInsets()
        }
    }

    private func windowChanged(_ w: UIWindow?) {
        link?.isPaused = w == nil
        lastTimestamp = 0
        skipFrames = 2
        if let w, args.showsDebugHUD {
            let o = overlay ?? DebugOverlayView()
            overlay = o
            o.install(in: w)
        } else if w == nil {
            overlay?.removeFromSuperview()
        }
    }

    // MARK: BoardControlling

    func prepare() async {
        if warmedUp { return }
        if let t = warmTask { await t.value; return }
        let t = Task { @MainActor [weak self] in
            guard let self else { return }
            await self.runWarmUp()
        }
        warmTask = t
        await t.value
    }

    func preload(_ levels: [LevelSpec]) {
        var ids: [String] = []
        for l in levels {
            ids.append(contentsOf: TapeLayer.spriteIDs(l))
            ids.append(contentsOf: ObstacleSet.spriteIDs(l))
        }
        if !ids.isEmpty { sprites.preload(ids) }
    }

    func load(_ setup: StageSetup) {
        enqueue { [weak self] in self?.doLoad(setup) }
    }

    func playIntro(_ style: IntroStyle) {
        enqueue { [weak self] in self?.runIntro(style) }
    }

    func present(_ events: [SessionEvent]) {
        enqueue { [weak self] in self?.doPresent(events) }
    }

    /// B2 (§5.7, MA §3.7): the clear wave, the dots fade, the next board swapped in at W + 0.70 s and drawn in (no zoom);
    /// `.stageTransitionDone` at the end of the longest draw.
    func playStageTransition(to next: StageSetup) {
        enqueue { [weak self] in self?.runStageTransition(to: next) }
    }

    /// B2 (§5.7, MA §3.8): the rainbow ring through the vacated dots; `.clearWaveFinished` at W + 0.50 s.
    func playClearWave() {
        enqueue { [weak self] in self?.runClearWave() }
    }

    func clear() {
        enqueue { [weak self] in self?.doClear() }
    }

    func setHint(_ arrows: [ArrowID]) {
        enqueue { [weak self] in self?.showHint(arrows) }
    }

    func screenPoint(of arrow: ArrowID) -> CGPoint? {
        guard let st = stage, let n = nodes[arrow], n.attached else { return nil }
        let c = n.spec.cells[n.spec.cells.count / 2]
        return contentToScreen(st.geo.centre(c))
    }

    func tapPoint(of arrow: ArrowID) -> CGPoint? {
        guard let st = stage, let n = nodes[arrow], n.attached, !preAttached.contains(arrow),
              movers[arrow]?.kind != .exit else { return nil }
        let safe = playRectOnScreen.insetBy(dx: 6, dy: 6).intersection(container.bounds.insetBy(dx: 6, dy: 6))
        let cells = n.spec.cells
        let mid = cells.count / 2
        // the middle cell first, then outward
        var order: [Int] = [mid]
        var k = 1
        while order.count < cells.count {
            if mid + k < cells.count { order.append(mid + k) }
            if mid - k >= 0 { order.append(mid - k) }
            k += 1
        }
        for i in order {
            let c = cells[i]
            guard st.hit.owner(c) == arrow else { continue }
            let sp = contentToScreen(st.geo.centre(c))
            if safe.contains(sp) { return sp }
        }
        return nil
    }

    func setFrozen(_ frozen: Bool) {
        if frozen { clock.freeze() } else { clock.resume() }
    }

    func setTimeScale(_ k: Double) { clock.setTimeScale(k) }

    func probe() -> BoardProbeData { boardProbe() }

    // MARK: load / clear

    func doLoad(_ setup: StageSetup) {
        let t0 = CACurrentMediaTime()
        resetStage()                                               // the active set retires (hidden now, emptied later)
        let s = container.scroll
        let limits = config.zoomLimits(setup.layout)
        let size = setup.layout.contentSize
        fxRng = FXRandom(seed: setup.seed == 0 ? 1 : setup.seed, label: "fx")

        CATransaction.begin()
        CATransaction.setDisableActions(true)
        s.minimumZoomScale = 1
        s.maximumZoomScale = 1
        s.zoomScale = 1
        s.content.frame = CGRect(origin: .zero, size: size)
        s.contentSize = size
        s.minimumZoomScale = limits.min
        s.maximumZoomScale = limits.max
        let bounds = CGRect(origin: .zero, size: size)
        stageLayer.frame = bounds
        sharedFX.frame = bounds
        let set = takeSpare()
        set.intro.isHidden = false
        let b = buildStage(setup, into: set)
        install(b)
        roots.intro.isHidden = false
        spareSet.intro.isHidden = true
        CATransaction.commit()

        s.gridMargin = CGFloat(setup.layout.pitch)
        s.updateInsets()
        s.contentOffset = s.centredOffset()
        if let z = args.zoom, z != 1 { setZoom(CGFloat(z), centredOn: nil) }
        let ms = (CACurrentMediaTime() - t0) * 1000
        lastLoadMs = ms
        loadFrames = 0
        measureCommit(since: t0, label: "L\(setup.level.level)")
        let level = setup.level
        context = "load L\(level.level)"
        if !warmingUp { Log.mark("board", "ready L\(level.level): \(level.arrows.count) arrows") }
        Log.debug("board", String(format: "load %.2f ms (build %.2f ms, %d arrows attached now, %d next frames), pitch %.3f, zoom %.3f…%.3f",
                                  ms, b.buildMs, level.arrows.count - b.pending.count, b.pending.count, setup.layout.pitch,
                                  Double(limits.min), Double(limits.max)))
        delegate?.boardZoomChanged(scale: s.zoomScale)
    }

    /// Clears the board: the active set is hidden at once and emptied over the next frames; state resets.
    func doClear() { resetStage() }

    /// Retires the active set (hidden at once, its layers removed `load.teardownPerFrame` per frame) and resets the
    /// stage state. The next load builds into the other set.
    func resetStage() {
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        pendingNext = nil
        transitionID += 1
        deferred = []
        retire(roots)
        shards.releaseAll()
        activeBursts = 0
        cancelHintCamera()
        CATransaction.commit()
        // a stage transition interrupted in its gap (placeIncoming stopped pan and zoom until its swap)
        container.scroll.isScrollEnabled = true
        container.scroll.pinchGestureRecognizer?.isEnabled = true
        movers = [:]
        nodes = [:]
        tapes = [:]
        tapeOf = [:]
        obstacles = ObstacleSet()
        pendingAttach = []
        exited = []
        preAttached = []
        hint = []
        hintState = nil
        stage = nil
        introRunning = false
        transitionRunning = false
        lastExitReported = false
        drawIn = nil
        introShown = false
    }

    // MARK: events

    func doPresent(_ events: [SessionEvent]) {
        guard stage != nil else { flushRipple(); return }
        let pp = ExitProfile.on ? CACurrentMediaTime() : 0
        defer { if ExitProfile.on { ExitProfile.add(8, CACurrentMediaTime() - pp) } }
        let t0 = roots.mover.convertTime(CACurrentMediaTime(), from: nil)
        let wall = CACurrentMediaTime()
        presentNotes.removeAll(keepingCapacity: true)
        // FEEL F3: a tap's motion starts `tapMotionLead` (one frame) before now, so its first presented frame already moves
        let tm = t0 - config.tapMotionLead
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        for e in events {
            switch e {
            case .exited(let plan):
                motionLead = config.tapMotionLead
                presentExit(plan, begin: tm)
                if !plan.beats.isEmpty {
                    let b0 = CACurrentMediaTime()
                    playBeats(plan, begin: tm, tapWall: wall)
                    presentNotes.append(String(format: "beats%d %.2f", plan.beats.count, (CACurrentMediaTime() - b0) * 1000))
                }
                motionLead = 0
            case .bumped(let plan):
                motionLead = config.tapMotionLead
                presentBump(plan, begin: tm)
                motionLead = 0
            case .arrowMarked(let id): nodes[id]?.mark()
            case .doorOpened, .counterBroken, .counterChanged, .pipeBroken, .elevatorActivated:
                let o0 = CACurrentMediaTime()
                presentObstacleEvent(e, begin: t0)
                presentNotes.append(String(format: "O %.2f", (CACurrentMediaTime() - o0) * 1000))
            case .hintShown(let ids): showHint(ids)
            default: break
            }
        }
        // FEEL item 4: the release's ripple goes in right after the movers (same transaction, same frame), so ripple, mover,
        // haptic and sound are issued within microseconds of each other at the end of the tap's work
        flushRipple()
        CATransaction.commit()
        lastPresentMs = (CACurrentMediaTime() - wall) * 1000
    }

    /// Adds the pending release ripple (FEEL item 4); a no-op when none is pending.
    func flushRipple() {
        guard let p = pendingRipple else { return }
        pendingRipple = nil
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        container.screenFX.ripple(at: p)
        CATransaction.commit()
        lastRippleAt = CACurrentMediaTime()
        noteFirst("ripple")
    }

    private func presentExit(_ plan: ExitPlan, begin t0: CFTimeInterval) {
        guard var st = stage else { return }
        var leader: Mover?
        let now = CACurrentMediaTime()
        for id in plan.unit {
            guard let n = nodes[id], n.attached, !exited.contains(id) else { continue }
            if let old = movers[id] { removeMover(old) }            // e.g. a bumping bundle member
            st.hit.remove(id, cells: n.spec.cells)
            // G-9: while its body is still over its own cells, a tap there is IGNORED (never re-targeted)
            st.hit.markMoving(id, until: now + kinematics.time(toTravel: Double(n.spec.cells.count) - 0.5))
            exited.insert(id)
            let e0 = CACurrentMediaTime()
            guard let m = startExit(n, path: plan.paths[id], combo: plan.combo, begin: t0) else { continue }
            presentNotes.append((m.fastPath ? "S" : "B") + String(painterFor(combo: plan.combo).name.prefix(1))
                                + (m.fastPath ? "" : (lastExitPrepHit ? "+" : "-"))
                                + String(format: " %.2f", (CACurrentMediaTime() - e0) * 1000))
            if ExitProfile.on { ExitProfile.count += 1 }
            movers[id] = m
            if leader == nil || m.duration > (leader?.duration ?? 0) { leader = m }
        }
        stage = st
        let tapeID = plan.tape ?? (plan.unit.count > 1 ? tapeOf[plan.tapped] : nil)
        if let tid = tapeID, let tape = tapes.removeValue(forKey: tid), let m = leader, let spec = nodes[m.id]?.spec {
            carryTape(tape, dir: spec.dir, times: m.times, travel: m.travel, duration: m.duration, begin: t0) {
                CATransaction.begin(); CATransaction.setDisableActions(true)
                tape.removeFromSuperlayer()
                CATransaction.commit()
            }
        }
        context = "exit a\(plan.tapped.raw)×\(plan.unit.count) movers \(movers.count)"
        lastUnitSize = plan.unit.count
        noteFirst("exit")
    }

    private func presentBump(_ plan: BumpPlan, begin t0: CFTimeInterval) {
        guard let n = nodes[plan.arrow], n.attached, movers[plan.arrow] == nil else { return }
        let e0 = CACurrentMediaTime()
        guard let m = startBump(n, plan: plan, begin: t0) else { return }
        presentNotes.append(String(format: "P %.2f", (CACurrentMediaTime() - e0) * 1000))
        movers[plan.arrow] = m
        // a taped bundle bumps rigidly with it (MA §3.4.6): every member's rest layers ride the same travel
        if let tid = tapeOf[plan.arrow], let tape = tapes[tid], let spec = stage?.level.obstacles.first(where: { $0.id == tid }) {
            bumpBundle(members: spec.arrows.filter { $0 != plan.arrow }, tape: tape, lead: m, dir: n.spec.dir, begin: t0)
        }
        if case .obstacle(let oid) = plan.blocker { flashObstacle(oid, begin: t0 + m.contactAt) }
        context = "bump a\(plan.arrow.raw)"
        noteFirst("bump")
    }

    /// The other members of a bumping tape bundle (and the tape) translate with the lead's travel, then turn red at the
    /// contact (the session marks every member at the contact ack).
    private func bumpBundle(members: [ArrowID], tape: CALayer, lead m: Mover, dir: Dir, begin t0: CFTimeInterval) {
        let d = dirVector(dir)
        let offsets = m.travel.map { NSValue(cgSize: CGSize(width: d.dx * $0, height: d.dy * $0)) }
        for id in members {
            guard let n = nodes[id], n.attached else { continue }
            for l in [n.body, n.head] as [CALayer] {
                let a = Anim.keyframes("transform.translation", offsets, times: m.times, duration: m.duration, begin: t0)
                l.add(a, forKey: "bundleBump")
            }
        }
        let a = Anim.keyframes("transform.translation", offsets, times: m.times, duration: m.duration, begin: t0)
        tape.add(a, forKey: "bundleBump")
    }

    /// Makes hidden arrows live and visible (door / box / curtain / elevator reveals). `into` = the root (the elevator's
    /// layer-2 arrows go under the platform); `showAt` = (begin, seconds) from which they are drawn (render-exact).
    func reveal(_ ids: [ArrowID], into root: CALayer? = nil, showAt: (CFTimeInterval, Double)? = nil) {
        guard var st = stage else { return }
        for id in ids {
            guard let n = nodes[id], !exited.contains(id) else { continue }
            if !n.attached {
                n.attach(to: root ?? roots.rest)
                n.setVisible(true)
                if let s = showAt, s.1 > 0.001 {
                    Anim.switchOpacity(n.body, from: 0, to: 1, begin: s.0, at: s.1, key: "reveal")
                    Anim.switchOpacity(n.head, from: 0, to: 1, begin: s.0, at: s.1, key: "reveal")
                }
            }
            preAttached.remove(id)
            st.hit.insert(id, cells: n.spec.cells)
        }
        stage = st
    }

    /// Attaches arrows that a burst will reveal, covered by their obstacle (drawn on the burst frame), not yet live.
    func preAttach(_ ids: [ArrowID]) {
        for id in ids {
            guard let n = nodes[id], !n.attached, !exited.contains(id) else { continue }
            n.attach(to: roots.rest)
            n.setVisible(true)
            preAttached.insert(id)
        }
    }

    // MARK: movers

    func moverLeftBoard(_ id: ArrowID) {
        guard let m = movers[id], m.kind == .exit, !m.hasLeftBoard else { return }
        m.hasLeftBoard = true
        delegate?.boardBeat(.exitLeftBoard(id))
        hintUnitLeft(id)
        guard !lastExitReported, let st = stage else { return }
        let remaining = st.level.arrows.contains { !exited.contains($0.id) }
        let inFlight = movers.values.contains { $0.kind == .exit && !$0.hasLeftBoard }
        if !remaining && !inFlight {
            lastExitReported = true
            delegate?.boardBeat(.lastExitLeftBoard)
        }
    }

    func finishMover(_ id: ArrowID) {
        guard let m = movers[id], !m.finished else { return }
        m.finished = true
        if m.kind == .exit && !m.hasLeftBoard { moverLeftBoard(id) }
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        m.root.removeFromSuperlayer()
        m.extras.forEach { $0.removeFromSuperlayer() }
        if m.kind == .exit {
            nodes[id]?.detach()
        } else if let n = nodes[id] {
            n.mark(n.marked)
            n.setVisible(true)
        }
        CATransaction.commit()
        movers[id] = nil
        delegate?.boardBeat(m.kind == .exit ? .exitFinished(id) : .bumpFinished(id))
    }

    /// Drops a mover at once, without its beats (a bump overtaken by an exit).
    func removeMover(_ m: Mover) {
        m.finished = true
        m.root.removeFromSuperlayer()
        m.extras.forEach { $0.removeFromSuperlayer() }
        movers[m.id] = nil
    }

    // MARK: input

    @objc private func onRelease(_ r: ReleaseTapRecognizer) {
        guard r.state == .ended else { return }
        let now = CACurrentMediaTime()
        recogniserMs.append((now - r.touchesEndedAt) * 1000)       // R1: touchesEnded → the action (same dispatch?)
        deliveryMs.append((r.touchesEndedAt - r.touchTimestamp) * 1000)   // the system: touch-up → touchesEnded
        if recogniserMs.count > 400 { recogniserMs.removeFirst(); deliveryMs.removeFirst() }
        handleRelease(screenPoint: r.location(in: container), touchTimestamp: r.touchTimestamp)
    }

    /// The release handler (also BoardLab's scripted taps): hit test, ripple, `boardReleased` — the delegate resolves
    /// the tap and presents the plan in this same run-loop turn, before the Core Animation commit (§8.2).
    func handleRelease(screenPoint sp: CGPoint, touchTimestamp ts: TimeInterval) {
        guard inputEnabled, let st = stage, !warmingUp else { return }
        let h0 = CACurrentMediaTime()
        latency.beginTap(touchTimestamp: ts)
        let cp = introAdjusted(screenToContent(sp))
        var hit = st.hit.arrow(at: cp, zoom: zoomScale, radiusPt: config.hitRadius, tieTolerancePt: config.tieTolerance,
                               tieTolerancePitch: config.tieTolerancePitch, rightThenDown: config.tieRightThenDown, now: h0)
        if let a = hit, let allowed = allowedArrows, !allowed.contains(a) { hit = nil }
        let h1 = CACurrentMediaTime()
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        // FEEL item 4: the ripple is added by the tap's present, right after its movers (or below, when nothing presents)
        pendingRipple = sp
        let h2 = CACurrentMediaTime()
        delegate?.boardReleased(arrow: hit, contentPoint: cp, touchTimestamp: ts)
        flushRipple()
        CATransaction.commit()
        if ExitProfile.on {
            let h3 = CACurrentMediaTime()
            ExitProfile.taps += 1
            ExitProfile.add(5, h1 - h0); ExitProfile.add(6, h2 - h1); ExitProfile.add(7, h3 - h2)
        }
        taps += 1
        lastTapArrow = hit
        handlerMs.append((CACurrentMediaTime() - h0) * 1000)
        if handlerMs.count > 400 { handlerMs.removeFirst(handlerMs.count - 400) }
    }

    /// During the intro zoom (MA §3.6: input opens at K + 1.015 while the board still scales to 1.0 until K + 1.35), a
    /// touch is converted through the set container's PRESENTATION transform (CONSISTENCY T-10).
    func introAdjusted(_ p: CGPoint) -> CGPoint {
        guard introRunning, let pres = roots.intro.presentation() else { return p }
        let s = pres.transform.m11
        guard abs(s - 1) > 0.0005, s > 0.01 else { return p }
        let c = CGPoint(x: roots.intro.bounds.midX, y: roots.intro.bounds.midY)
        return CGPoint(x: c.x + (p.x - c.x) / s, y: c.y + (p.y - c.y) / s)
    }

    private func logLatency(_ s: LatencyProbe.Sample) {
        guard args.showsDebugHUD || args.bench || args.lab == "latency" || args.raw["pc.logTaps"] != nil else { return }
        let lvl = stage?.level.level ?? 0
        let a = lastTapArrow.map { String($0.raw) } ?? "-"
        let handler = handlerMs.last ?? -1
        Log.mark("perf", String(format: "tap L%d a%@ touch→handler %.2f handler→commit %.2f commit→vsync %.2f "
                                + "(handler %.2f delivery %.2f recogniser %.2f unit %d)", lvl, a, s.touchToHandlerMs,
                                s.handlerToCommitMs ?? -1, s.commitToVsyncMs ?? -1, handler, deliveryMs.last ?? -1,
                                recogniserMs.last ?? -1, lastUnitSize))
    }
    var lastUnitSize = 0

    // MARK: zoom

    func viewForZooming(in scrollView: UIScrollView) -> UIView? { container.scroll.content }

    func scrollViewDidZoom(_ scrollView: UIScrollView) {
        container.scroll.updateInsets()
        delegate?.boardZoomChanged(scale: scrollView.zoomScale)
    }

    func scrollViewWillBeginDragging(_ scrollView: UIScrollView) { cancelHintCamera() }
    func scrollViewWillBeginZooming(_ scrollView: UIScrollView, with view: UIView?) { cancelHintCamera() }

    /// Zooms to `z` (clamped) with content point `p` (default: the board centre) at the centre of the play rect.
    func setZoom(_ z: CGFloat, centredOn p: CGPoint?) {
        let s = container.scroll
        let zc = min(max(z, s.minimumZoomScale), s.maximumZoomScale)
        s.setZoomScale(zc, animated: false)
        s.updateInsets()
        s.contentOffset = offset(zoom: zc, centredOn: p)
        delegate?.boardZoomChanged(scale: zc)
    }

    /// The content offset that puts content point `p` (default the board centre) at the play-rect centre at zoom `zc`,
    /// clamped to the pan limits.
    func offset(zoom zc: CGFloat, centredOn p: CGPoint?) -> CGPoint {
        let s = container.scroll
        let target = p ?? CGPoint(x: contentBounds.midX, y: contentBounds.midY)
        let play = s.playRect
        var off = CGPoint(x: target.x * zc - play.midX, y: target.y * zc - play.midY)
        let inset = s.insets(forZoom: zc)
        let cw = contentBounds.width * zc, ch = contentBounds.height * zc
        let maxX = cw + inset.right - s.bounds.width
        let maxY = ch + inset.bottom - s.bounds.height
        off.x = min(max(off.x, -inset.left), max(maxX, -inset.left))
        off.y = min(max(off.y, -inset.top), max(maxY, -inset.top))
        return off
    }

    // MARK: freeze and slow motion (§5.12)

    /// Mirrors MotionClock: 0 freezes the stage and the screen FX at their current time; k > 0 runs them at speed k.
    func applyClockScale(_ k: Double) {
        if k <= 0 {
            guard !frozen else { return }
            frozen = true
            CATransaction.begin(); CATransaction.setDisableActions(true)
            Self.setLayerTiming(roots.stage, speed: 0, freezeAt: roots.stage.convertTime(CACurrentMediaTime(), from: nil))
            container.screenFX.applyTiming(speed: 0, freezeAt: container.screenFX.localNow)
            CATransaction.commit()
        } else {
            frozen = false
            CATransaction.begin(); CATransaction.setDisableActions(true)
            Self.setLayerTiming(roots.stage, speed: Float(k), freezeAt: nil)
            container.screenFX.applyTiming(speed: Float(k), freezeAt: nil)
            CATransaction.commit()
        }
    }

    /// Shows the frame exactly `t` seconds into a sequence that began at stage-local `start` (`-pc.freezeAt`), then
    /// freezes MotionClock too (it mirrors, §5.12).
    func freezeSequence(stageStart: CFTimeInterval, fxStart: CFTimeInterval, at t: Double) {
        frozen = true
        CATransaction.begin(); CATransaction.setDisableActions(true)
        Self.setLayerTiming(roots.stage, speed: 0, freezeAt: stageStart + t)
        container.screenFX.applyTiming(speed: 0, freezeAt: fxStart + t)
        CATransaction.commit()
        clock.freeze()
    }

    /// Layer timing: `freezeAt` holds the layer's local time there; otherwise the layer runs at `speed` from its current
    /// local time (no jump).
    static func setLayerTiming(_ l: CALayer, speed: Float, freezeAt: CFTimeInterval?) {
        if let f = freezeAt {
            l.speed = 0
            l.timeOffset = f
            return
        }
        let localNow = l.convertTime(CACurrentMediaTime(), from: nil)
        let parentNow = l.superlayer?.convertTime(CACurrentMediaTime(), from: nil) ?? CACurrentMediaTime()
        l.speed = speed
        l.timeOffset = localNow
        l.beginTime = parentNow
    }

    // MARK: the display link (the master clock)

    private func startLink() {
        guard link == nil else { return }
        let l = CADisplayLink(target: self, selector: #selector(tick(_:)))
        l.preferredFrameRateRange = CAFrameRateRange(minimum: 60, maximum: 120, preferred: 120)
        l.add(to: .main, forMode: .common)
        l.isPaused = container.window == nil
        link = l
    }

    @objc private func tick(_ l: CADisplayLink) {
        let ts = l.timestamp
        if lastTimestamp > 0, skipFrames == 0 {
            let dt = ts - lastTimestamp
            let over = perf.record(frameDT: dt)
            let ms = dt * 1000
            for (k, w) in firstWindows {
                let nw = (frames: w.frames - 1, maxMs: max(w.maxMs, ms))
                if nw.frames <= 0 {
                    firstWindows[k] = nil
                    firstResults[k] = nw.maxMs
                    Log.mark("board", String(format: "first:%@ max %.1f ms over 45 frames", k, nw.maxMs))
                } else {
                    firstWindows[k] = nw
                }
            }
            if over, stage != nil, !warmingUp {
                let isLoad = loadFrames <= 3
                if isLoad { hitchesLoad += 1 } else { hitchesPlay += 1 }
                let tags = firstWindows.keys.sorted().map { "first:" + $0 }.joined(separator: " ")
                Log.mark("board", String(format: "hitch %.1f ms %@%@%@", ms, context, isLoad ? " (load+\(loadFrames))" : "",
                                         tags.isEmpty ? "" : " " + tags))
            }
        } else if skipFrames > 0 {
            skipFrames -= 1
        }
        lastTimestamp = ts
        if loadFrames < 1_000 { loadFrames += 1 }
        // F1: the split load's next batches (one kind per frame: attach first, then teardown)
        if !pendingAttach.isEmpty {
            attachStep()
        } else if pendingNext?.pending.isEmpty == false {
            attachStepNext()
        } else if !teardown.isEmpty {
            teardownStep(fx.teardownPerFrame)
        }
        if !deferred.isEmpty {
            let job = deferred.removeFirst()
            CATransaction.begin(); CATransaction.setDisableActions(true)
            job()
            CATransaction.commit()
        } else if !prepGraveyard.isEmpty || !shareGraveyard.isEmpty {
            prepGraveyard.removeLast(min(40, prepGraveyard.count))
            shareGraveyard.removeLast(min(40, shareGraveyard.count))
        } else if pendingAttach.isEmpty, teardown.isEmpty, pendingNext == nil, !transitionRunning, laidOutOnce {
            prepStep(budget: fx.prepBudgetMs / 1000)                  // FEEL item 4: exits prepared ahead, idle frames only
        }
        latency.frame(targetTimestamp: l.targetTimestamp)
        delegate?.boardFrame(timestamp: ts, targetTimestamp: l.targetTimestamp)
        frameHook?(l)
        if !frameWaiters.isEmpty {
            var keep: [(Int, CheckedContinuation<Void, Never>)] = []
            for (n, c) in frameWaiters { if n <= 1 { c.resume() } else { keep.append((n - 1, c)) } }
            frameWaiters = keep
        }
        let probeGap = 1 / max(0.5, config.probeHz)
        if args.exposesProbe, ts - lastProbeTime >= probeGap {
            lastProbeTime = ts
            publishProbe()
        }
        if let o = overlay, ts - lastOverlayTime >= 0.25 {
            lastOverlayTime = ts
            o.update(overlayLines())
        }
    }

    var linkPaused: Bool? { link?.isPaused }

    /// F1 evidence: the load's main-thread work + its Core Animation commit (a one-shot run-loop observer ordered after
    /// CA's own commit observer, like LatencyProbe). Kept in `loadCommits` (the lab reports p50 / max).
    func measureCommit(since t0: CFTimeInterval, label: String) {
        let main = lastLoadMs
        let obs = CFRunLoopObserverCreateWithHandler(kCFAllocatorDefault, CFRunLoopActivity.beforeWaiting.rawValue, false,
                                                     2_000_001) { [weak self] _, _ in
            MainActor.assumeIsolated {
                let total = (CACurrentMediaTime() - t0) * 1000
                self?.loadCommits.append((main, total))
                if self?.loadCommits.count ?? 0 > 400 { self?.loadCommits.removeFirst() }
                if self?.warmingUp == false {
                    Log.mark("board", String(format: "load %@ main %.2f ms, to the end of the commit %.2f ms (%@)", label, main, total,
                                             self?.lastBuildParts ?? ""))
                }
            }
        }
        CFRunLoopAddObserver(CFRunLoopGetMain(), obs, .commonModes)
    }
    var loadCommitsSummary: [String: Double] {
        guard !loadCommits.isEmpty else { return [:] }
        let m = loadCommits.map(\.main).sorted(), t = loadCommits.map(\.total).sorted()
        return ["loads": Double(loadCommits.count), "main_ms_p50": m[m.count / 2], "main_ms_max": m[m.count - 1],
                "commit_end_ms_p50": t[t.count / 2], "commit_end_ms_max": t[t.count - 1]]
    }

    /// Resets the load / play hitch counters (a lab measurement window).
    func resetHitchCounters() { hitchesLoad = 0; hitchesPlay = 0 }

    /// Suspends until `n` display-link frames have been presented (the link must be running).
    /// If the board is not in a window yet (the display link is paused), it first waits up to `timeout` s for one.
    func frames(_ n: Int, timeout: Double = 5) async {
        let end = CACurrentMediaTime() + timeout
        while link?.isPaused != false, CACurrentMediaTime() < end, !hurried {
            try? await Task.sleep(nanoseconds: 16_000_000)
        }
        guard link?.isPaused == false, !hurried else { return }
        await withCheckedContinuation { (c: CheckedContinuation<Void, Never>) in frameWaiters.append((max(1, n), c)) }
    }

    /// A hurried warm-up waits for no frame.
    private var hurried: Bool { warmHurry && warmingUp }

    /// FIX-B (AppModel.boot's cap, §6.1): the warm-up is still running at the boot cap. Its frame-paced part stops waiting
    /// for frames (the pending waits resume now) and runs its remaining steps and its clear at once; a warm-up still decoding
    /// its sprites skips its board part after the decode. Returns when the warm-up is over, so the first screen never
    /// shares the engine with the warm-up board (the sprite decode and the door/key art, which every level needs, finish
    /// first). Under load the frame-paced part took 2-3 s and the whole warm-up up to 29 s (V3 r2, V1 run 4).
    func hurryWarmUp() async {
        guard !warmedUp else { return }
        warmHurry = true
        let waiting = frameWaiters
        frameWaiters = []
        for (_, c) in waiting { c.resume() }
        await prepare()          // joins the running warm-up, or starts it when the boot's own call has not run yet
    }

    /// Tags the next 45 frames after the first occurrence of an effect in this process (`first:<effect>`, §10.3 item 6).
    func noteFirst(_ effect: String) {
        guard !warmingUp, !firstSeen.contains(effect) else { return }
        firstSeen.insert(effect)
        firstWindows[effect] = (45, 0)
    }

    func layerCount() -> Int {
        func count(_ l: CALayer) -> Int { 1 + (l.sublayers ?? []).reduce(0) { $0 + count($1) } }
        return count(roots.intro) + count(sharedFX) + count(container.screenFX.fxLayer)
    }

    private func overlayLines() -> [String] {
        let s = perf.snapshot()
        let l = latency.last
        return [String(format: "%.0f fps p95 %.1f p99 %.1f ms", s.fps, s.p95_ms, s.p99_ms),
                String(format: "%.0f MB %d layers %d movers", s.footprint_mb, layerCount(), movers.count),
                String(format: "tap %.1f/%.1f vsync %.1f", l?.touchToHandlerMs ?? 0, l?.handlerToCommitMs ?? 0,
                       l?.commitToVsyncMs ?? 0)]
    }
}

