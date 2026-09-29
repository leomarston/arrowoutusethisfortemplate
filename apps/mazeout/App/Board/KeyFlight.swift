import UIKit
import PathCore

// B2 (SPEC-architecture §5.4 "key", §5.6 "door + lock"; SPEC-motion-audio §3.5.2; STYLE §A.2 "Key"; MANIFEST keyOnArrow:
// anchor = the arrow's line and the centre of the key's first cell on the tail side, drawn pointing DOWN; up = rotate 180,
// right = transpose, left = right rotated 180). The key hangs on its arrow (tapeRoot). When the arrow exits (the plan's
// `.keyReleased(key, door, s: 0)`, anchor R = the release):
//   #1 R: the ribbon (the hanger) vanishes; the gold key stays where it hung while the arrow exits through it;
//   #2 R + 0.23, 0.08 s: sag +0.48 p (easeOutQuad) with a wobble −15° → +15° → 0;
//   #3 R + 0.31, 0.22 s: float up 2.3 p (easeInOut) — apex; a 0.02 s hold;
//   #4 R + 0.55, T_dive = clamp(√(2·D/428), 0.16, 0.40) (D = apex → keyhole in cells, g = 428 p/s²): x linear, y from rest
//      under gravity (u²), plus a lift 0.25·D·sin(πu) toward screen-up when the lock is above the apex;
//   #5 dive end, 0.15 s: scale 1 → 0.7 and a turn to point into the keyhole (+45°) (easeOutQuad);
//   #6 + 0.08, 0.10 s: the turn in the lock (+45° → +90°) (easeInOut);
//   #7 turn end + 0.03 = the BURST (R + 1.14 for the measured geometry): the key, the door and its lock vanish (render-exact
//      opacity switches), the lock flash and the door shards start, and the board reports `.doorBurst(door)` from that
//      beat (the session opens the door on it; its hidden arrows were attached under the door at the dispatch).

@MainActor final class KeyNode {
    let id: ObstacleID
    let rider: ArrowID?
    /// The hanging sprite (ribbon + key) in tapeRoot.
    let rest = CALayer()
    /// The registration point (content): the key's first cell on the tail side.
    let anchor: CGPoint
    let orient: CGAffineTransform
    /// Extra rotation that makes the shaft point down (screen) from this orientation.
    let toDown: CGFloat
    let size: CGSize
    let anchorFrac = CGPoint(x: 19.84 / 43.0, y: 27.52 / 78.0)
    var used = false

    init(spec: ObstacleSpec, arrow: ArrowSpec?, geo: BoardGeometry, art: BoardArt) {
        id = spec.id
        rider = spec.arrows.first ?? arrow?.id
        let p = geo.pitch
        var cells = spec.cells
        if cells.count >= 2, let a = arrow {
            let i0 = a.cells.firstIndex(of: cells[0]) ?? 0, i1 = a.cells.firstIndex(of: cells[1]) ?? 1
            if i1 < i0 { cells = [cells[1], cells[0]] }
        }
        let first = cells.first ?? (arrow.map { $0.cells[0] } ?? Cell(0, 0))
        let second = cells.count > 1 ? cells[1] : (arrow.flatMap { $0.cells.count > 1 ? $0.cells[1] : nil } ?? first + .down)
        let d = Dir(from: first, to: second) ?? .down
        anchor = geo.centre(first)
        switch d {
        case .down: orient = .identity; toDown = 0
        case .up: orient = CGAffineTransform(rotationAngle: .pi); toDown = .pi
        case .right: orient = CGAffineTransform(a: 0, b: 1, c: 1, d: 0, tx: 0, ty: 0); toDown = .pi / 2
        case .left: orient = CGAffineTransform(a: 0, b: -1, c: -1, d: 0, tx: 0, ty: 0); toDown = -.pi / 2
        }
        let img = art.image("keyOnArrow")
        let wPx = CGFloat(img?.width ?? 129), hPx = CGFloat(img?.height ?? 234)
        size = CGSize(width: wPx * p / 96, height: hPx * p / 96)
        rest.contents = img
        rest.contentsGravity = .resize
        rest.bounds = CGRect(origin: .zero, size: size)
        rest.anchorPoint = anchorFrac
        rest.position = anchor
        rest.setAffineTransform(orient)
    }
}

/// The key flight's beats after the release (s) for a dive of D cells (apex → keyhole), MA §3.5.2 rows 2–7.
struct KeyTimeline: Equatable {
    var detach: Double, sagEnd: Double, apex: Double, diveStart: Double, dive: Double, insertStart: Double
    var insertEnd: Double, turnStart: Double, turnEnd: Double, burst: Double

    static func make(_ f: EffectsConfig, distanceCells D: Double) -> KeyTimeline {
        let detach = f.keyDetachAt
        let sagEnd = detach + f.keySagDur
        let apex = sagEnd + f.keyFloatDur
        let diveStart = apex + f.keyDiveGap
        let dive = min(max(sqrt(2 * max(0, D) / f.keyDiveG), f.keyDiveMin), f.keyDiveMax)
        let insertStart = diveStart + dive
        let insertEnd = insertStart + f.keyInsertDur
        let turnStart = insertEnd + f.keyTurnGap
        let turnEnd = turnStart + f.keyTurnDur
        return KeyTimeline(detach: detach, sagEnd: sagEnd, apex: apex, diveStart: diveStart, dive: dive,
                           insertStart: insertStart, insertEnd: insertEnd, turnStart: turnStart, turnEnd: turnEnd,
                           burst: turnEnd + f.keyBurstAfterTurn)
    }
}

extension BoardEngine {
    /// Plays one key flight from the release (stage-local `t0`) to `door`'s keyhole; schedules the burst (render-exact) and
    /// the `.doorBurst` beat. Returns the burst time after the release. Call inside the tap's no-actions transaction.
    @discardableResult
    func playKeyFlight(_ key: KeyNode, to door: DoorNode, begin t0: CFTimeInterval, tapWall: CFTimeInterval) -> Double {
        let f = fx
        let p = stage?.geo.pitch ?? 20
        let set = roots
        key.used = true
        key.rest.isHidden = true                                      // #1: the hanger goes (the key stays)
        // the flying key: a container (position / rotation / scale about the registration point) + the key image
        let flyer = CALayer()
        flyer.bounds = .zero
        flyer.position = key.anchor
        let img = CALayer()
        img.contents = boardArt.keyOnly ?? boardArt.image("keyOnArrow")
        img.contentsGravity = .resize
        img.bounds = CGRect(origin: .zero, size: key.size)
        img.anchorPoint = key.anchorFrac
        img.position = .zero
        img.setAffineTransform(key.orient)
        flyer.addSublayer(img)

        let P0 = key.anchor
        let sagP = CGPoint(x: P0.x, y: P0.y + CGFloat(f.keySagPitch) * p)
        let A = CGPoint(x: sagP.x, y: sagP.y - CGFloat(f.keyFloatPitch) * p)
        let K = door.keyhole
        let D = Double(hypot(K.x - A.x, K.y - A.y) / p)
        let tl = KeyTimeline.make(f, distanceCells: D)
        let tDetach = tl.detach, tSag = tl.sagEnd, tApex = tl.apex, tDive = tl.diveStart, T = tl.dive
        let tIn = tl.insertStart, tInEnd = tl.insertEnd, tTurn = tl.turnStart, tTurnEnd = tl.turnEnd, tBurst = tl.burst
        let total = tBurst + 0.001

        // position: hold, sag (easeOutQuad), float (easeInOut), hold, dive (60 Hz samples), hold
        var times: [Double] = [0, tDetach, tSag, tApex, tDive]
        var vals: [CGPoint] = [P0, P0, sagP, A, A]
        var fns: [CAMediaTimingFunction] = [Ease2.linear, Ease2.outQuad, Ease2.inOut, Ease2.linear]
        let lift = K.y < A.y ? 0.25 * D * Double(p) : 0
        var u = 1.0 / 60 / T
        while u < 1 {
            let x = A.x + (K.x - A.x) * CGFloat(u)
            let y = A.y + (K.y - A.y) * CGFloat(u * u) - CGFloat(lift * sin(.pi * u))
            times.append(tDive + u * T); vals.append(CGPoint(x: x, y: y)); fns.append(Ease2.linear)
            u += 1.0 / 60 / T
        }
        times.append(tIn); vals.append(K); fns.append(Ease2.linear)
        times.append(total); vals.append(K); fns.append(Ease2.linear)
        let pos = Anim.keyframes("position", vals.map { NSValue(cgPoint: $0) }, times: times, duration: total, begin: t0,
                                 functions: fns)
        flyer.position = K
        flyer.add(pos, forKey: "pos")
        // rotation: wobble in the sag, the insert turn, the turn in the lock
        let wob = CGFloat(f.keyWobbleDeg * .pi / 180)
        let turnIn = key.toDown + .pi / 4
        let turnOut = key.toDown + CGFloat(f.keyTurnDeg * .pi / 180)
        let rTimes = [0, tDetach, tDetach + f.keySagDur / 3, tDetach + 2 * f.keySagDur / 3, tSag, tIn, tInEnd, tTurn, tTurnEnd, total]
        let rVals: [CGFloat] = [0, 0, -wob, wob, 0, 0, turnIn, turnIn, turnOut, turnOut]
        let rFns = [Ease2.linear, Ease2.outQuad, Ease2.outQuad, Ease2.outQuad, Ease2.linear, Ease2.outQuad, Ease2.linear,
                    Ease2.inOut, Ease2.linear]
        flyer.setAffineTransform(CGAffineTransform(rotationAngle: turnOut))
        flyer.add(Anim.keyframes("transform.rotation.z", rVals.map { NSNumber(value: Double($0)) }, times: rTimes,
                                 duration: total, begin: t0, functions: rFns), forKey: "rot")
        let s = f.keyInsertScale
        let scale = Anim.keyframes("transform.scale.xy", [1, 1, s, s].map { NSNumber(value: $0) },
                                   times: [0, tIn, tInEnd, total], duration: total, begin: t0,
                                   functions: [Ease2.linear, Ease2.outQuad, Ease2.linear])
        flyer.add(scale, forKey: "scale")
        Anim.switchOpacity(flyer, from: 1, to: 0, begin: t0, at: tBurst, key: "gone")
        set.fx.addSublayer(flyer)

        // the burst: door + lock vanish, the flash, the shards (hidden until the burst), the beat
        door.burst(begin: t0, at: tBurst, fxRoot: sharedFX, fx: f, pitch: p)     // FIX-V2: the flash in the debris' layer, over it
        var rng = FXRandom(seed: stage?.setup.seed ?? 1, label: "door:\(door.id.raw)")
        let (pts, looks) = door.shardSpawn(count: f.doorShards.count, pitch: p, rng: &rng)
        burstShards(kind: .door, points: pts, looks: looks, begin: t0 + tBurst, life: f.doorShards.life, hiddenUntilBegin: true)
        // FIX-V2 F-05: the door's own frame / slat / lock pieces fly with the shards
        shards.setImage("doorW4H8", boardArt.doorWhole)
        shards.setImage("lockHex", boardArt.image("lockHex"))
        let (cpts, clooks) = door.chunkSpawn(art: boardArt, pitch: p)
        burstShards(kind: .door, points: cpts, looks: clooks, begin: t0 + tBurst, life: f.doorShards.life, hiddenUntilBegin: true)
        let doorID = door.id
        let token = stageToken
        Anim.beat(on: flyer, key: "burst", begin: t0, delay: tBurst) { [weak self, weak flyer] finished in
            guard let self, self.stageToken == token else { return }
            CATransaction.begin(); CATransaction.setDisableActions(true)
            flyer?.removeFromSuperlayer()
            CATransaction.commit()
            guard finished else { return }
            let measured = CACurrentMediaTime() - tapWall
            Log.mark("board", String(format: "doorBurst %@ key %@ planned %.3f s measured %.3f s after the tap (dive %.3f s, D %.2f cells)",
                                     doorID.raw, key.id.raw, tBurst, measured, T, D))
            self.lastDoorBursts.append((doorID, tBurst, measured))
            self.noteFirst("doorBurst")
            self.delegate?.boardBeat(.doorBurst(doorID))
        }
        Log.debug("board", String(format: "keyFlight %@ → %@ burst at %.3f s (dive %.3f s, D %.2f cells)",
                                  key.id.raw, door.id.raw, tBurst, T, D))
        return tBurst
    }
}
