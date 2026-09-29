import UIKit
import PathCore

// B1 (SPEC-architecture §5.5, D5, §5.11). The exit mover: everything in ONE CATransaction with actions disabled
// (addSublayer included, P1); keyframes at every display frame (1/60 s) with exact linear interpolation; the explicit
// beginTime of every animation is the stage-local time of the tap, so beats, freezes and slow motion share one clock.
// Beats the core needs back are reported from animation delegates, never timers.

/// The exit law (D5; motion §3.3) is C1's `ExitKinematics` (PathCore §4.16): s(τ) = vmax·τ − (vmax − v0)·T·(1 − e^(−τ/T))
/// cells. The board builds it from board.json `exit.v0/vmax/tau` (the same pass-2 numbers as `ExitKinematics.measured`)
/// so SPEC-motion-audio can retune it as data.
extension BoardConfig {
    var kinematics: ExitKinematics { ExitKinematics(v0: exitV0, vmax: exitVmax, tau: exitTau) }
}

/// One arrow in motion (an exit or a bump). Built at tap time, removed by its own "end" animation delegate.
@MainActor final class Mover {
    enum Kind { case exit, bump }
    let id: ArrowID
    let kind: Kind
    let root = CALayer()
    /// Layers outside `root` that belong to this motion (the ✖ badge in fxRoot, a carried tape).
    var extras: [CALayer] = []
    /// Stage-local begin time of every animation of this motion.
    let begin: CFTimeInterval
    var duration: Double = 0
    /// Travel (pt) at which the tail left its last cell / the grid (exitLeftBoard).
    var leftBoardAt: Double = 0
    var hasLeftBoard = false
    var finished = false
    // kinematics sampling (BoardLab `kinematics`): the moving head and where it started
    weak var headLayer: CALayer?
    var headStartLocal: CGPoint = .zero
    var dirVec = CGVector(dx: 1, dy: 0)
    var pitch: CGFloat = 1
    var straight = true
    /// Built by the rigid-translation fast path (StraightExit).
    var fastPath = false
    /// The travel samples (seconds, pt) every layer of this exit follows (tape carry, B2 decorations).
    var times: [Double] = []
    var travel: [CGFloat] = []
    /// Bump: seconds from the release to the contact frame.
    var contactAt: Double = 0

    init(id: ArrowID, kind: Kind, begin: CFTimeInterval) {
        self.id = id; self.kind = kind; self.begin = begin
    }
}

/// `-pc.profileExit 1`: the exit build's main-thread cost by section (samples · keyframes · painter · stars · beats).
@MainActor enum ExitProfile {
    static var on = false
    static var sums = [Double](repeating: 0, count: 10)
    static var taps = 0
    static var count = 0
    static func add(_ k: Int, _ dt: Double) { sums[k] += dt * 1000 }
    static func report() -> String {
        let names = ["samples", "keyframes", "painter", "stars", "beats"]
        let n = max(1, count)
        let per = zip(names, sums).map { String(format: "%@ %.3f", $0, $1 / Double(n)) }.joined(separator: " · ")
        let t = Double(max(1, taps))
        let tapNames = ["hit", "ripple", "session", "present", "presentExitOther"]
        let perTap = zip(tapNames, sums[5...]).map { String(format: "%@ %.3f", $0, $1 / t) }.joined(separator: " · ")
        return per + " ms/exit (n \(count)) | per tap: " + perTap + " (taps \(taps))"
    }
}

/// Keyframe / beat helpers (exact linear between samples: timingFunctions nil, calculationMode linear).
enum Anim {
    static func keyframes(_ keyPath: String, _ values: [Any], times: [Double], duration: Double,
                          begin: CFTimeInterval, functions: [CAMediaTimingFunction]? = nil) -> CAKeyframeAnimation {
        let a = CAKeyframeAnimation(keyPath: keyPath)
        a.values = values
        a.keyTimes = times.map { NSNumber(value: duration > 0 ? min(1, max(0, $0 / duration)) : 0) }
        a.timingFunctions = functions
        a.calculationMode = .linear
        a.duration = duration
        a.beginTime = begin
        a.fillMode = .both
        return a.hi()
    }

    static func basic(_ keyPath: String, from: Any, to: Any, duration: Double, begin: CFTimeInterval,
                      function: CAMediaTimingFunction? = nil) -> CABasicAnimation {
        let a = CABasicAnimation(keyPath: keyPath)
        a.fromValue = from
        a.toValue = to
        a.duration = duration
        a.beginTime = begin
        a.timingFunction = function
        a.fillMode = .backwards
        return a.hi()
    }

    /// A carrier animation whose delegate runs `body` on the main actor when it stops `delay` seconds after `begin`
    /// (layer-local time: freezes and slow motion delay it with the layer). Never a timer (§5.5 rule 8).
    static func beat(on layer: CALayer, key: String, begin: CFTimeInterval, delay: Double,
                     _ body: @escaping @MainActor (Bool) -> Void) {
        let a = CABasicAnimation(keyPath: "opacity")
        a.fromValue = 1
        a.toValue = 1
        a.duration = max(delay, 0.0001)
        a.beginTime = begin
        a.delegate = AnimationEnd { finished in MainActor.assumeIsolated { body(finished) } }
        layer.add(a, forKey: key)
    }

    static let easeOutQuad = CAMediaTimingFunction(controlPoints: 0.25, 0.46, 0.45, 0.94)
    static let easeOutCubic = CAMediaTimingFunction(controlPoints: 0.215, 0.61, 0.355, 1)
    static let easeInOut = CAMediaTimingFunction(name: .easeInEaseOut)
}

/// FEEL item 4: everything about one bent exit that depends only on the arrow, its path beyond the rest cells and the far
/// rect — the moving path, the samples, the keyframe tracks (begin 0: the tap sets its time on copies), the star spawn track.
/// Built in idle display-link frames after a load (`prepStep`, ≤ `prepBudgetMs` a frame) or at the tap when missing / stale;
/// the tap only adds the layers.
@MainActor final class ExitPrep {
    let key: String
    let path: ArrowPath
    let local: LocalPath
    let restLen: CGFloat
    let total: CGFloat
    let travelEnd: CGFloat
    let tEnd: Double
    let times: [Double]
    let travel: [CGFloat]
    let leftBoardAt: Double
    let straight: Bool
    let s0: CAKeyframeAnimation
    let s1: CAKeyframeAnimation
    let hp: CAKeyframeAnimation
    let rot: CAKeyframeAnimation?
    let finalStart: CGFloat
    let finalEnd: CGFloat
    let finalHead: CGPoint
    let finalAngle: CGFloat
    /// The stars' tail track (absolute content points at each sample) and the sample index where emission stops.
    let starPts: [NSValue]
    let starStop: Int

    init(key: String, path: ArrowPath, local: LocalPath, restLen: CGFloat, total: CGFloat, travelEnd: CGFloat, tEnd: Double,
         times: [Double], travel: [CGFloat], leftBoardAt: Double, straight: Bool, s0: CAKeyframeAnimation,
         s1: CAKeyframeAnimation, hp: CAKeyframeAnimation, rot: CAKeyframeAnimation?, finalStart: CGFloat, finalEnd: CGFloat,
         finalHead: CGPoint, finalAngle: CGFloat, starPts: [NSValue], starStop: Int) {
        self.key = key; self.path = path; self.local = local; self.restLen = restLen; self.total = total
        self.travelEnd = travelEnd; self.tEnd = tEnd; self.times = times; self.travel = travel; self.leftBoardAt = leftBoardAt
        self.straight = straight; self.s0 = s0; self.s1 = s1; self.hp = hp; self.rot = rot; self.finalStart = finalStart
        self.finalEnd = finalEnd; self.finalHead = finalHead; self.finalAngle = finalAngle; self.starPts = starPts
        self.starStop = starStop
    }

    /// A copy of a prepared track that starts at `begin`.
    static func at(_ a: CAKeyframeAnimation, _ begin: CFTimeInterval) -> CAKeyframeAnimation {
        let c = a.copy() as! CAKeyframeAnimation
        c.beginTime = begin
        return c
    }
}

extension BoardEngine {
    /// The far rect: the visible screen ∪ the content, outset by 25 % of the screen (a zoom-out mid-exit still ends
    /// off-screen; spike). Its rounded value keys the exit preps.
    func farRect() -> CGRect {
        let vis = visibleContentRect()
        let z = max(zoomScale, 0.01)
        let out = CGFloat(config.farOutsetOfScreen)
        return vis.union(contentBounds).insetBy(dx: -container.bounds.width / z * out, dy: -container.bounds.height / z * out)
    }

    static func farKey(_ r: CGRect) -> String {
        "\(Int(r.minX.rounded())),\(Int(r.minY.rounded())),\(Int(r.maxX.rounded())),\(Int(r.maxY.rounded()))"
    }

    /// The prep of one bent exit (see ExitPrep). `beyond` = the plan's cells past the arrow's own.
    func makeExitPrep(_ node: ArrowNode, beyond: [Cell], far: CGRect, key: String) -> ExitPrep? {
        guard let st = stage else { return nil }
        let geo = st.geo
        let p = geo.pitch
        let spec = node.spec
        let own = spec.cells.count
        let lastCell = beyond.last ?? headCell(spec)
        let prevCell = beyond.count >= 2 ? beyond[beyond.count - 2] : (beyond.count == 1 ? headCell(spec) : spec.cells[max(0, own - 2)])
        let lastPt = geo.centre(lastCell)
        let lastDir = beyond.isEmpty ? dirVector(spec.dir) : ArrowPath.unit(geo.centre(prevCell), lastPt)
        let dEdge = BoardGeometry.distanceToEdge(from: lastPt, dir: lastDir, in: far)
        let restLen = node.rest.length
        let extend = dEdge + restLen + geo.lineWidth + p
        let path = geo.movingPath(spec, beyond: beyond, extend: extend)
        let total = path.length
        let arcLast = total - extend
        // the exit ends when the TAIL (cap included) has left the far rect (VERIFIED motion §3.2: tail past the screen)
        let travelEnd = arcLast + dEdge + geo.lineWidth
        let kin = kinematics
        let tEnd = kin.time(toTravel: Double(travelEnd / p))
        // samples at every display frame + the end
        var times: [Double] = []
        var step = 0.0
        let dt = max(config.keyframeStep, 1.0 / 240)
        while step < tEnd { times.append(step); step += dt }
        times.append(tEnd)
        let travel: [CGFloat] = times.map { t in min(travelEnd, CGFloat(kin.s(t)) * p) }
        let local = LocalPath(path.cgPath, pad: max(p, geo.headExtent))
        let straight = beyond.isEmpty || beyond.allSatisfy { c in
            (c.c - headCell(spec).c) * spec.dir.dr == 0 && (c.r - headCell(spec).r) * spec.dir.dc == 0
        }
        let leftTravel: CGFloat
        if config.leftBoardAtLastCell {
            leftTravel = restLen + p * 0.5
        } else {
            let gridRect = CGRect(x: geo.centre(Cell(0, 0)).x - p / 2, y: geo.centre(Cell(0, 0)).y - p / 2,
                                  width: CGFloat(st.level.cols) * p, height: CGFloat(st.level.rows) * p)
            leftTravel = arcLast + BoardGeometry.distanceToEdge(from: lastPt, dir: lastDir, in: gridRect) + geo.lineWidth / 2
        }
        let leftBoardAt = kin.time(toTravel: Double(min(leftTravel, travelEnd) / p))
        let startFrac = travel.map { NSNumber(value: Double($0 / total)) }
        let endFrac = travel.map { NSNumber(value: Double(min(1, (restLen + $0) / total))) }
        let headPts = travel.map { s -> NSValue in NSValue(cgPoint: local.local(path.point(at: restLen + s))) }
        let angles = travel.map { s -> CGFloat in path.angle(at: restLen + s) }
        let s0 = Anim.keyframes("strokeStart", startFrac, times: times, duration: tEnd, begin: 0)
        let s1 = Anim.keyframes("strokeEnd", endFrac, times: times, duration: tEnd, begin: 0)
        let hp = Anim.keyframes("position", headPts, times: times, duration: tEnd, begin: 0)
        var rot: CAKeyframeAnimation?
        if let a0 = angles.first, angles.contains(where: { abs($0 - a0) > 0.01 }) {
            rot = Anim.keyframes("transform.rotation.z", angles.map { NSNumber(value: Double($0)) }, times: times,
                                 duration: tEnd, begin: 0)
        }
        // the stars' spawn track: the tail point at every sample until it leaves the content rect
        var starPts: [NSValue] = []
        var starStop = times.count - 1
        if fx.starsOn {
            let tailExt = CGFloat(config.tailExtend) * p
            let rect = CGRect(origin: .zero, size: contentBounds.size)
            starPts.reserveCapacity(travel.count)
            var stopped = false
            for (i, s) in travel.enumerated() {
                let q = path.point(at: s + tailExt)
                starPts.append(NSValue(cgPoint: q))
                if !stopped && !rect.contains(q) { starStop = max(0, i); stopped = true }
            }
        }
        return ExitPrep(key: key, path: path, local: local, restLen: restLen, total: total, travelEnd: travelEnd, tEnd: tEnd,
                        times: times, travel: travel, leftBoardAt: leftBoardAt, straight: straight, s0: s0, s1: s1, hp: hp, rot: rot,
                        finalStart: CGFloat(startFrac.last?.doubleValue ?? 1), finalEnd: CGFloat(endFrac.last?.doubleValue ?? 1),
                        finalHead: headPts.last?.cgPointValue ?? .zero, finalAngle: angles.last ?? CGFloat(spec.dir.angle),
                        starPts: starPts, starStop: starStop)
    }

    /// The prep key: the far rect and the path beyond the arrow's own cells.
    func exitPrepKey(far: CGRect, beyond: [Cell]) -> String {
        Self.farKey(far) + "|" + beyond.map { "\($0.c):\($0.r)" }.joined(separator: ",")
    }

    /// The cells a plain exit takes past the head: the head ray to the grid edge (what C2's plan gives an arrow with no tube,
    /// corner or elevator on its ray; a plan that differs simply misses the prep).
    func defaultBeyond(_ spec: ArrowSpec) -> [Cell] {
        guard let st = stage else { return [] }
        var out: [Cell] = []
        var c = headCell(spec).moved(spec.dir, by: 1)
        while c.c >= 0, c.r >= 0, c.c < st.level.cols, c.r < st.level.rows { out.append(c); c = c.moved(spec.dir, by: 1) }
        return out
    }

    /// FEEL item 4: prepares the bent exits of the live arrows in idle frames (≤ `prepBudget` s of main thread per frame);
    /// restarts when the far rect changes (a pan / zoom) or a stage is installed.
    func prepStep(budget: CFTimeInterval) {
        guard !warmingUp, let st = stage, movers.count < 3 else { return }
        let sv = container.scroll
        guard !sv.isDragging, !sv.isDecelerating, !sv.isZooming, !sv.isZoomBouncing else { return }   // re-prep once it rests
        let t0 = CACurrentMediaTime()
        let far = farRect()
        let fk = Self.farKey(far)
        if fk != prepFarKey || prepToken != stageToken {
            prepFarKey = fk
            prepToken = stageToken
            prepQueue = st.level.arrows.map(\.id)
        }
        while let id = prepQueue.popLast() {
            guard let n = nodes[id], n.attached, !exited.contains(id) else { continue }
            let beyond = defaultBeyond(n.spec)
            if n.rest.vertices.count == 2 {
                // a straight exit: its shared track (StraightExit `exitShare`) for this travel
                _ = exitShare(dir: n.spec.dir, travelEnd: straightTravelEnd(n, beyondCount: beyond.count, far: far), pitch: st.geo.pitch)
                if CACurrentMediaTime() - t0 > budget { break }
                continue
            }
            let key = exitPrepKey(far: far, beyond: beyond)
            if exitPreps[id]?.key != key { exitPreps[id] = makeExitPrep(n, beyond: beyond, far: far, key: key) }
            if CACurrentMediaTime() - t0 > budget { break }
        }
    }

    /// Starts one exit along the core's path (`nil`: the straight head ray). Returns the mover (nil if the arrow has no
    /// resting node). Call inside the caller's no-actions transaction.
    @discardableResult
    func startExit(_ node: ArrowNode, path plan: ExitPath?, combo: Int, begin t0: CFTimeInterval) -> Mover? {
        if fastExits, isStraightExit(node, plan: plan) {
            return startStraightExit(node, path: plan, combo: combo, begin: t0)
        }
        guard stage != nil else { return nil }
        let prof = ExitProfile.on
        var pt = prof ? CACurrentMediaTime() : 0
        func mark(_ k: Int) { if prof { let n = CACurrentMediaTime(); ExitProfile.add(k, n - pt); pt = n } }
        let spec = node.spec
        let own = spec.cells.count
        let beyond: [Cell] = plan.map { $0.cells.count > own ? Array($0.cells[own...]) : [] } ?? []
        let far = farRect()
        let key = exitPrepKey(far: far, beyond: beyond)
        let prepped = exitPreps[spec.id].flatMap { $0.key == key ? $0 : nil }
        guard let prep = prepped ?? makeExitPrep(node, beyond: beyond, far: far, key: key) else { return nil }
        exitPreps[spec.id] = nil
        lastExitPrepHit = prepped != nil
        mark(0)
        let geo = stage!.geo
        let p = geo.pitch
        let m = Mover(id: spec.id, kind: .exit, begin: t0)
        m.duration = prep.tEnd
        m.times = prep.times
        m.travel = prep.travel
        m.pitch = p
        m.dirVec = dirVector(spec.dir)
        m.straight = prep.straight
        m.leftBoardAt = prep.leftBoardAt
        let s0 = ExitPrep.at(prep.s0, t0), s1 = ExitPrep.at(prep.s1, t0), hp = ExitPrep.at(prep.hp, t0)
        let rot = prep.rot.map { ExitPrep.at($0, t0) }
        mark(1)
        let painter = painterFor(combo: combo)
        let ctx = ExitPaintContext(
            root: m.root, local: prep.local, path: prep.path, restLength: prep.restLen, lineWidth: geo.lineWidth,
            headPath: geo.headPath(spec.dir), headBounds: node.head.bounds,
            strokeStart: s0, strokeEnd: s1, headPosition: hp, headRotation: rot,
            finalStrokeStart: prep.finalStart, finalStrokeEnd: prep.finalEnd,
            finalHeadPosition: prep.finalHead, finalHeadAngle: prep.finalAngle,
            fromColor: node.color, config: config, begin: t0, duration: prep.tEnd,
            times: prep.times, travel: prep.travel, pitch: p, scale: screenScale, combo: combo, phase: fxRng.unit())

        m.root.frame = prep.local.frame
        roots.mover.addSublayer(m.root)
        node.setVisible(false)
        let headLayer = painter.paint(ctx)
        m.headLayer = headLayer
        m.headStartLocal = prep.local.local(node.headCentre)
        mark(2)
        addStars(ctx, painter: painter, moverRoot: roots.mover, fxRoot: roots.fx,
                 track: prep.starPts.isEmpty ? nil : (prep.starPts, prep.starStop))
        mark(3)

        let id = spec.id
        // beats are guarded by identity and `finished`: removing a layer stops its animations with finished = false
        Anim.beat(on: m.root, key: "leftBoard", begin: t0, delay: m.leftBoardAt) { [weak self, weak m] finished in
            guard finished, let self, let m, self.movers[id] === m else { return }
            self.moverLeftBoard(id)
        }
        Anim.beat(on: m.root, key: "end", begin: t0, delay: prep.tEnd) { [weak self, weak m] finished in
            guard finished, let self, let m, self.movers[id] === m else { return }
            self.finishMover(id)
        }
        mark(4)
        return m
    }

    /// The tape bundle's sprite rides with its arrows (parallel straight members: one common translation, §5.5 step 7).
    func carryTape(_ tape: CALayer, dir: Dir, times: [Double], travel: [CGFloat], duration: Double, begin t0: CFTimeInterval,
                   onEnd: @escaping @MainActor () -> Void) {
        let p0 = tape.position
        let d = dirVector(dir)
        let pts = travel.map { NSValue(cgPoint: CGPoint(x: p0.x + d.dx * $0, y: p0.y + d.dy * $0)) }
        tape.position = pts.last?.cgPointValue ?? p0
        tape.add(Anim.keyframes("position", pts, times: times, duration: duration, begin: t0), forKey: "carry")
        Anim.beat(on: tape, key: "carryEnd", begin: t0, delay: duration) { finished in if finished { onEnd() } }
    }
}
