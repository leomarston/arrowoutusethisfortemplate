import UIKit
import PathCore

// B2 (SPEC-architecture §5.6, §5.1 layer order, D4). One stage's obstacle layers and how the board PLAYS the core's plan:
// the logical change happened at the tap (C2's BoardState.commit); the look follows the plan's beats, each converted from
// the leading head's arc position s (cells) to time with the exit kinematics (arch D4/D5):
//   .keyReleased → the key flight to its door (burst at the computed time, `.doorBurst` from that beat);
//   .pipeCount   → the counter swap when the head comes out of the far mouth (`pipe.countAt leave`; the final pass shows no
//                  "0": the tube shatters 0.05 s later);
//   .pipeBreak   → the shatter at leave + `pipe.breakAfterLeave`, `.pipeBroken` from that beat;
//   .counterTick → every box's count on its beat (the tap: `box.countAt tap`); .counterBreak → the break + `.counterBroken`;
//   .elevatorEmptied → the platform opens at O (the last platform tail clears the platform) + 0.02;
//   .corner      → the plate is pushed in when the head reaches it and springs out after the tail passes (FIX-2 A, L02:
//                  the measured hit, CornerLayer.swift).
// The session's events do the rest: `.doorOpened` / `.counterBroken` / `.elevatorActivated` reveal their arrows (live for the
// hit test from that event; the door's arrows were attached, covered, at the key's dispatch so they show on the burst
// frame; the elevator's layer-2 arrows show from O + 0.02 under the tint).
// Placement (roots): doors, boxes, corners → obstacleRoot; keys → tapeRoot; pipes → tubeRoot (over the movers);
// elevator platforms → platformRoot (between the hidden layer and the resting arrows).

@MainActor final class ObstacleSet {
    var doors: [ObstacleID: DoorNode] = [:]
    var keys: [ObstacleID: KeyNode] = [:]
    var pipes: [ObstacleID: PipeNode] = [:]
    var boxes: [ObstacleID: BoxNode] = [:]
    var elevators: [ObstacleID: ElevatorNode] = [:]
    var corners: [ObstacleID: CornerNode] = [:]
    /// Elevator id → (stage-local tap time, O) of its activation (the `.elevatorActivated` event reads it).
    var elevatorOpen: [ObstacleID: (begin: CFTimeInterval, o: Double)] = [:]
    /// Boxes / pipes whose break was scheduled by a plan beat (an event without a beat breaks at once).
    var breakScheduled: Set<ObstacleID> = []
    var kinds: [ObstacleID: ObstacleKind] = [:]
    /// F3-B (SPEC-gameplay §3.5, VERIFIED v552 L69 / L89): the layers of the obstacles lying wholly inside a door (L59's
    /// pipes, L99's corner), by door. Hidden from the build; shown on that door's `.doorOpened` (the burst frame).
    var underDoor: [ObstacleID: [CALayer]] = [:]

    init() {}

    var isEmpty: Bool { doors.isEmpty && keys.isEmpty && pipes.isEmpty && boxes.isEmpty && elevators.isEmpty && corners.isEmpty }

    /// Builds every non-tape obstacle of `level` into `roots`. Call inside a no-actions transaction.
    static func build(_ level: LevelSpec, geo: BoardGeometry, art: BoardArt, roots: StageRoots, scale: CGFloat,
                      cornerHit: CornerHitSpec = CornerHitSpec()) -> ObstacleSet {
        let s = ObstacleSet()
        let arrows = Dictionary(level.arrows.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
        // F3-B: an obstacle whose cells all lie inside a door is UNDER it: it acts AND is drawn only from the door's burst on
        // (SPEC-gameplay §3.5). Before, the tube root (over the doors) drew L59's pipes across its shut doors from the start.
        let doorCells = level.obstacles.filter { $0.kind == .door }.map { ($0.id, Set($0.cells)) }
        func hostDoor(_ o: ObstacleSpec) -> ObstacleID? {
            guard [.pipe, .corner, .box, .curtain].contains(o.kind), !o.cells.isEmpty else { return nil }
            let cs = Set(o.cells)
            return doorCells.first { cs.isSubset(of: $0.1) }?.0
        }
        func under(_ o: ObstacleSpec, _ layer: CALayer) {
            guard let d = hostDoor(o) else { return }
            layer.isHidden = true
            s.underDoor[d, default: []].append(layer)
        }
        for o in level.obstacles {
            s.kinds[o.id] = o.kind
            switch o.kind {
            case .door:
                let d = DoorNode(spec: o, geo: geo, art: art, scale: scale)
                roots.obstacle.addSublayer(d.root)
                s.doors[o.id] = d
            case .key:
                let rider = o.arrows.first.flatMap { arrows[$0] }
                let k = KeyNode(spec: o, arrow: rider, geo: geo, art: art)
                // a key on a hidden arrow (under a door / box / the elevator) shows with its arrow (tapeRoot is above them)
                if let r = rider, r.hiddenBy != nil || r.layer > 1 { k.rest.opacity = 0 }
                roots.tape.addSublayer(k.rest)
                s.keys[o.id] = k
            case .pipe:
                let p = PipeNode(spec: o, geo: geo, art: art, scale: scale)
                roots.tube.addSublayer(p.root)
                s.pipes[o.id] = p
                under(o, p.root)
            case .box, .curtain:
                let b = BoxNode(spec: o, geo: geo, art: art, scale: scale)
                roots.obstacle.addSublayer(b.root)
                s.boxes[o.id] = b
                under(o, b.root)
            case .elevator:
                let e = ElevatorNode(spec: o, geo: geo, scale: scale)
                roots.platform.addSublayer(e.root)
                s.elevators[o.id] = e
            case .corner:
                let c = CornerNode(spec: o, geo: geo, art: art, scale: scale, hit: cornerHit)
                roots.obstacle.addSublayer(c.layer)
                s.corners[o.id] = c
                under(o, c.layer)
            case .tape:
                break
            }
        }
        return s
    }

    /// The board's half of the probe's obstacle rows (§9.4): tapes are added by the caller.
    func probeRows() -> [BoardProbeData.Obstacle] {
        var out: [BoardProbeData.Obstacle] = []
        for (id, d) in doors { out.append(BoardProbeData.Obstacle(id: id.raw, k: "door", state: d.state)) }
        for (id, k) in keys { out.append(BoardProbeData.Obstacle(id: id.raw, k: "key", state: k.used ? "used" : "on")) }
        for (id, p) in pipes {
            out.append(BoardProbeData.Obstacle(id: id.raw, k: "pipe", n: p.broken ? 0 : p.remaining, state: p.broken ? "broken" : "on"))
        }
        for (id, b) in boxes {
            out.append(BoardProbeData.Obstacle(id: id.raw, k: kinds[id]?.rawValue ?? "box", n: b.broken ? 0 : b.remaining,
                                               state: b.broken ? "broken" : "on"))
        }
        for (id, e) in elevators { out.append(BoardProbeData.Obstacle(id: id.raw, k: "elevator", state: e.active ? "active" : "idle")) }
        for (id, _) in corners { out.append(BoardProbeData.Obstacle(id: id.raw, k: "corner", state: "on")) }
        return out.sorted { $0.id < $1.id }
    }

    /// The sprite ids a level needs (preload).
    static func spriteIDs(_ level: LevelSpec) -> [String] {
        var out: Set<String> = []
        for o in level.obstacles {
            switch o.kind {
            case .door: out.formUnion(["doorW4H8", "lockHex", "doorShards"])
            case .key: out.insert("keyOnArrow")
            case .pipe: out.formUnion(["pipeMouth", "pipeCounter", "pipeShards"])
            case .box, .curtain: out.insert("boxRing")
            case .corner:
                // FIX-2 A (L02): the facing's own spring + plate (+ the rotated `cornerWedge` fallback, the validator's id)
                let ids = CornerNode.layerIDs(o.turn ?? .upRight)
                out.formUnion([ids.spring, ids.plate, "cornerWedge"])
            default: break
            }
        }
        return Array(out)
    }
}

extension BoardEngine {
    /// Plays the plan's obstacle beats of one exit that started at stage-local `t0` (the tap's transaction).
    func playBeats(_ plan: ExitPlan, begin t0: CFTimeInterval, tapWall: CFTimeInterval) {
        guard !plan.beats.isEmpty, let st = stage else { return }
        let p = st.geo.pitch
        let token = stageToken
        func t(_ s: Double) -> Double { kinematics.time(toTravel: max(0, s)) }
        for b in plan.beats {
            switch b {
            case let .keyReleased(k, d, _):
                guard let key = obstacles.keys[k], let door = obstacles.doors[d] else { continue }
                let tb = playKeyFlight(key, to: door, begin: t0, tapWall: tapWall)
                let ids = door.spec.reveals + st.level.arrows.filter { $0.hiddenBy == d }.map(\.id)
                // the door's arrows go in under it in a later frame (F4: off the tap's handler; covered until the burst)
                let token = stageToken
                deferred.append { [weak self] in
                    guard let self, self.stageToken == token else { return }
                    self.preAttach(ids)
                    self.showKeys(riding: ids, begin: t0, at: tb)
                }
            case let .pipeCount(pid, n, s):
                guard let pipe = obstacles.pipes[pid] else { continue }
                pipe.remaining = n
                if n > 0 { pipe.digits?.schedule(n, at: t0 + t(s), now: Anim.now(roots.tube)) }
            case let .pipeBreak(pid, s):
                guard let pipe = obstacles.pipes[pid], !pipe.broken else { continue }
                obstacles.breakScheduled.insert(pid)
                let at = t(s) + fx.pipeBreakAfterLeave
                pipe.shatter(engine: self, begin: t0, at: at, pitch: p)
                let carrier = roots.tube
                Anim.beat(on: carrier, key: "pipeBreak:\(pid.raw)", begin: t0, delay: at) { [weak self] finished in
                    guard finished, let self, self.stageToken == token else { return }
                    Log.mark("board", String(format: "pipeBroken %@ %.3f s after the tap (leave %.3f s + %.3f)", pid.raw,
                                             CACurrentMediaTime() - tapWall, t(s), self.fx.pipeBreakAfterLeave))
                    self.lastPipeBreaks.append((pid, t(s), at, CACurrentMediaTime() - tapWall))
                    self.noteFirst("pipeBreak")
                    self.delegate?.boardBeat(.pipeBroken(pid))
                }
            case let .corner(cid, aid, s):
                // FIX-2 A (L02): pushed in at the head's arrival, out when the TAIL passes the cell centre (that arrow's own cells;
                // a tape member uses its own)
                guard let corner = obstacles.corners[cid] else { continue }
                let cells = st.level.arrows.first(where: { $0.id == aid })?.cells.count ?? 1
                let hold = t(s + Double(max(0, cells - 1))) - t(s)
                corner.hit(beat: t0 + t(s), hold: hold, spec: fx.cornerHit, now: Anim.now(roots.obstacle))
            case let .counterTick(bid, n, s):
                obstacles.boxes[bid]?.schedule(n, at: t0 + t(s), now: Anim.now(roots.obstacle))
            case let .counterBreak(bid, s):
                guard let box = obstacles.boxes[bid], !box.broken else { continue }
                obstacles.breakScheduled.insert(bid)
                let at = t(s)
                box.shatter(engine: self, begin: t0, at: at, pitch: p)
                let carrier = roots.obstacle
                Anim.beat(on: carrier, key: "boxBreak:\(bid.raw)", begin: t0, delay: max(at, 0.0001)) { [weak self] finished in
                    guard finished, let self, self.stageToken == token else { return }
                    self.noteFirst("boxBreak")
                    self.delegate?.boardBeat(.counterBroken(bid))
                }
            case let .elevatorEmptied(eid, _):
                guard let e = obstacles.elevators[eid] else { continue }
                let o = elevatorClearTime(plan, platform: e.block)
                obstacles.elevatorOpen[eid] = (t0, o)
                e.activate(begin: t0, o: o, fx: fx)
                Log.mark("board", String(format: "elevator %@ opens at O = %.3f s after the tap (+%.2f)", eid.raw, o, fx.elevatorDoorsAt))
                noteFirst("elevator")
            case .enterTube, .leaveTube:
                break
            }
        }
    }

    /// The session's obstacle events (after the plan's beats in the same batch).
    func presentObstacleEvent(_ e: SessionEvent, begin t0: CFTimeInterval) {
        switch e {
        case let .doorOpened(d, revealed):
            obstacles.doors[d]?.markOpen()
            for l in obstacles.underDoor.removeValue(forKey: d) ?? [] { l.isHidden = false }      // F3-B: §3.5
            reveal(revealed)
            showKeys(riding: revealed, begin: t0, at: 0)
        case let .counterBroken(b, revealed):
            if let box = obstacles.boxes[b], !box.broken, !obstacles.breakScheduled.contains(b) {
                box.shatter(engine: self, begin: t0, at: 0, pitch: stage?.geo.pitch ?? 20)
            }
            reveal(revealed)
            showKeys(riding: revealed, begin: t0, at: 0)
        case let .counterChanged(b, n):
            if let box = obstacles.boxes[b], box.remaining != n { box.schedule(n, at: t0, now: t0) }
        case let .pipeBroken(p):
            if let pipe = obstacles.pipes[p], !pipe.broken, !obstacles.breakScheduled.contains(p) {
                pipe.shatter(engine: self, begin: t0, at: 0, pitch: stage?.geo.pitch ?? 20)
            }
        case let .elevatorActivated(eid, revealed):
            let open = obstacles.elevatorOpen[eid]
            if open == nil, let node = obstacles.elevators[eid] { node.activate(begin: t0, o: 0.15, fx: fx) }
            let o = open ?? (t0, 0.15)
            reveal(revealed, into: roots.under, showAt: (o.begin, o.o + fx.elevatorDoorsAt))
            showKeys(riding: revealed, begin: o.begin, at: o.o + fx.elevatorDoorsAt)
        default:
            break
        }
    }

    /// Keys hanging on arrows an obstacle reveals appear with them (render-exact at `at` after `begin`, or now).
    func showKeys(riding ids: [ArrowID], begin: CFTimeInterval, at: Double) {
        let set = Set(ids)
        for k in obstacles.keys.values where !k.used {
            guard let r = k.rider, set.contains(r), k.rest.opacity == 0 else { continue }
            if at > 0.001 {
                Anim.switchOpacity(k.rest, from: 0, to: 1, begin: begin, at: at, key: "show")
            } else {
                k.rest.opacity = 1
            }
        }
    }

    /// A red tint on an obstacle that blocked a bump (MA §3.4.2: same timing as the blocking-arrow flash, peak alpha 0.6;
    /// DECISION: never observed).
    func flashObstacle(_ id: ObstacleID, begin: CFTimeInterval) {
        guard let st = stage, let spec = st.level.obstacles.first(where: { $0.id == id }) else { return }
        let p = st.geo.pitch
        let l = CAShapeLayer()
        let path = CGMutablePath()
        if spec.kind == .pipe, let pipe = obstacles.pipes[id] {
            path.addLines(between: pipe.tube.map(st.geo.centre))
            l.fillColor = nil
            l.strokeColor = config.markedColor
            l.lineWidth = p
            l.lineJoin = .round
        } else {
            let cs = spec.cells
            guard let minC = cs.map(\.c).min(), let maxC = cs.map(\.c).max(), let minR = cs.map(\.r).min(),
                  let maxR = cs.map(\.r).max() else { return }
            let tl = st.geo.centre(Cell(minC, minR))
            let rect = CGRect(x: tl.x - p / 2, y: tl.y - p / 2, width: CGFloat(maxC - minC + 1) * p, height: CGFloat(maxR - minR + 1) * p)
            path.addPath(CGPath(roundedRect: rect, cornerWidth: 0.3 * p, cornerHeight: 0.3 * p, transform: nil))
            l.fillColor = config.markedColor
        }
        l.path = path
        l.opacity = 0
        let c = config
        let a = Anim.keyframes("opacity", [0, 0, fx.obstacleTintAlpha, fx.obstacleTintAlpha, 0].map { NSNumber(value: $0) },
                               times: [0, c.blockerRedFrom, c.blockerRedTo, c.blockerRedTo + 0.01, c.blockerBlackAt],
                               duration: c.blockerBlackAt, begin: begin)
        a.fillMode = .forwards
        l.add(a, forKey: "flash")
        roots.fx.addSublayer(l)
        Anim.beat(on: l, key: "flashEnd", begin: begin, delay: c.blockerBlackAt + 0.02) { [weak l] _ in
            CATransaction.begin(); CATransaction.setDisableActions(true)
            l?.removeFromSuperlayer()
            CATransaction.commit()
        }
    }
}
