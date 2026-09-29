import UIKit
import PathCore

// B2 (SPEC-architecture §5.5 painters, §5.6 obstacles, §5.7 transitions; SPEC-motion-audio §3, §10, §13.1). The B2 knobs,
// read ONCE per engine from Tuning/board.json (+ `-pc.tune board.*`). Every default below is the SPEC-motion-audio §13.1 value
// (the file carries the same numbers; a missing key never crashes). B1's `BoardConfig` keeps the B1 keys.

struct ShardSpec {
    var count: Int
    var g: Double              // pt/s², screen space (MA6)
    var life: Double
    var fadeFrom: Double
    var vyMin: Double          // pt/s (negative = up)
    var vyMax: Double
    var vxMin: Double
    var vxMax: Double
    var spinDeg: Double
}

struct EffectsConfig {
    // painters (MA §3.2.2)
    var violetPalette: [CGColor]
    var violetPeriod: Double
    var rainbowPalette: [CGColor]
    var rainbowPeriod: Double
    // trail stars (MA §3.2.3)
    var starsPerCell: Double
    var starSize: Double
    var starSizeRange: Double
    var starJitter: Double
    var starLife: Double
    var starEndScale: Double
    var starSpinDeg: Double
    var starSolidColors: [CGColor]
    var starsOn: Bool
    // intro (MA §3.6) and stage transitions (§3.7)
    var introAckAt: Double
    var ftueAckAt: Double
    var drawStartA: Double
    var drawStartB: Double
    var dotsFadeFrom: Double
    var dotsFade: Double
    // clear wave (§3.8)
    var waveFront: Double
    var waveTotal: Double
    var waveEnvelope: [Double]      // t0, w0, t1, w1, … (seconds after the front passes, weight)
    // key flight + door burst (§3.5.2)
    var keyDetachAt: Double
    var keySagPitch: Double
    var keySagDur: Double
    var keyWobbleDeg: Double
    var keyFloatPitch: Double
    var keyFloatDur: Double
    var keyDiveGap: Double          // apex hold before the dive (R + 0.53 → R + 0.55)
    var keyDiveG: Double            // pitch/s²
    var keyDiveMin: Double
    var keyDiveMax: Double
    var keyInsertDur: Double
    var keyInsertScale: Double
    var keyTurnGap: Double
    var keyTurnDur: Double
    var keyTurnDeg: Double
    var keyBurstAfterTurn: Double
    var lockFlashDur: Double
    var lockFlashPitch: Double
    // pipe (§3.5.3), box counters (§3.5.4), elevator (§3.5.5), corner (§3.5.6)
    var pipeBreakAfterLeave: Double
    var elevatorDoorsAt: Double
    var elevatorDoorsDur: Double
    var elevatorTintFrom: Double
    var elevatorFrameFadeAt: Double
    var elevatorFrameFadeDur: Double
    /// FIX-2 A (L02): the MEASURED corner hit (art/lanes/corner.md; replaces the 1.0 → 1.15 → 1.0 pop).
    var cornerHit: CornerHitSpec
    // shards (§10)
    var doorShards: ShardSpec
    var pipeShards: ShardSpec
    var boxShards: ShardSpec
    // bump on an obstacle (§3.4.2)
    var obstacleTintAlpha: Double
    // hint (§3.10.1)
    var hintColor: CGColor
    var hintCameraDelay: Double
    var hintCameraDur: Double
    var hintCurve: [Double]
    var hintBlink: [Double]
    var hintReturnDur: Double
    // pan (§3.9)
    var panCentreInGrid: Bool
    var zoomBounces: Bool
    // F1: board (re)loads split across frames
    var attachPerFrame: Int
    var teardownPerFrame: Int
    /// FEEL item 4: main-thread ms per idle frame for preparing exits ahead (`board.json load.prepBudgetMs`).
    var prepBudgetMs: Double

    init(_ t: BoardTuning) {
        let f = t.file
        func colors(_ k: String, _ d: [String]) -> [CGColor] { f.strings(k, d).map(BoardConfig.color) }
        violetPalette = colors("violet.palette", ["#01ACFD", "#3972FF", "#7B3CFC", "#B908FE", "#7B3CFC", "#3972FF"])
        violetPeriod = max(0.1, f.double("violet.periodCells", 3.75))
        rainbowPalette = colors("rainbow.palette", ["#FF6500", "#FFCE01", "#9DE600", "#37E500", "#00E100", "#00D3AF",
                                                    "#00C1FF", "#4079FF", "#8D5FFF", "#BC4BF3", "#FF2FC6", "#FF5A85"])
        rainbowPeriod = max(0.1, f.double("rainbow.periodCells", 4.2))
        starsPerCell = f.double("stars.perCell", 2.4)
        starSize = f.double("stars.sizePitch", 0.30)
        starSizeRange = f.double("stars.sizeRangePitch", 0.08)
        starJitter = f.double("stars.jitterPitch", 0.25)
        starLife = max(0.05, f.double("stars.life", 0.40))
        starEndScale = f.double("stars.endScale", 0.4)
        starSpinDeg = f.double("stars.spinDegPerS", 90)
        starSolidColors = colors("stars.solidColors", ["#1E88F5", "#7FD8FF"])
        starsOn = f.bool("stars.enabled", true)
        introAckAt = f.double("intro.ackAt", 1.015)
        ftueAckAt = f.double("intro.ftueAckAt", 0.36)
        let fr = f.doubles("intro.drawStartFraction", [0.10, 0.30])
        drawStartA = fr.first ?? 0.10
        drawStartB = fr.count > 1 ? fr[1] : 0.30
        dotsFadeFrom = f.double("stage.dotsFadeFrom", 0.12)
        dotsFade = f.double("stage.dotsFade", 0.56)
        waveFront = max(0.05, f.double("clearWave.frontDuration", 0.45))
        waveTotal = f.double("clearWave.total", 0.50)
        waveEnvelope = f.doubles("clearWave.envelope", [0, 0, 0.05, 1, 0.15, 1, 0.40, 0])
        keyDetachAt = f.double("key.detachAt", 0.23)
        keySagPitch = f.double("key.sagPitch", 0.48)
        keySagDur = f.double("key.sagDur", 0.08)
        keyWobbleDeg = f.double("key.wobbleDeg", 15)
        keyFloatPitch = f.double("key.floatPitch", 2.3)
        keyFloatDur = f.double("key.floatDur", 0.22)
        keyDiveGap = f.double("key.diveGap", 0.02)
        keyDiveG = max(1, f.double("key.diveGPitch", 357))   // reconciled with the measured 0.224 s dive (board.json _sources)
        keyDiveMin = f.double("key.diveMin", 0.16)
        keyDiveMax = f.double("key.diveMax", 0.40)
        keyInsertDur = f.double("key.insertDur", 0.15)
        keyInsertScale = f.double("key.insertScale", 0.7)
        keyTurnGap = f.double("key.turnGap", 0.08)
        keyTurnDur = f.double("key.turnDur", 0.10)
        keyTurnDeg = f.double("key.turnDeg", 90)
        keyBurstAfterTurn = f.double("key.burstAfterTurn", 0.03)
        lockFlashDur = f.double("key.flashDur", 0.216)
        lockFlashPitch = f.double("key.flashPitch", 0.9)
        pipeBreakAfterLeave = f.double("pipe.breakAfterLeave", 0.05)
        elevatorDoorsAt = f.double("elevator.doorsAt", 0.02)
        elevatorDoorsDur = f.double("elevator.doorsDur", 0.30)
        elevatorTintFrom = f.double("elevator.tintFrom", 0.55)
        elevatorFrameFadeAt = f.double("elevator.frameFadeAt", 0.30)
        elevatorFrameFadeDur = f.double("elevator.frameFadeDur", 0.15)
        var ch = CornerHitSpec()
        ch.pressLead = f.double("corner.pressLead", ch.pressLead)
        ch.pressDur = f.double("corner.pressDur", ch.pressDur)
        ch.push = f.double("corner.push", ch.push)
        ch.holdEnd = f.double("corner.holdEnd", ch.holdEnd)
        ch.releaseAfterTail = f.double("corner.releaseAfterTail", ch.releaseAfterTail)
        let pk = f.doubles("corner.peak", [ch.peak.t, ch.peak.x]), tr = f.doubles("corner.trough", [ch.trough.t, ch.trough.x])
        if pk.count == 2 { ch.peak = (pk[0], pk[1]) }
        if tr.count == 2 { ch.trough = (tr[0], tr[1]) }
        ch.restAt = f.double("corner.restAt", ch.restAt)
        ch.pivot = f.double("corner.pivot", ch.pivot)
        ch.springLen = f.double("corner.springLen", ch.springLen)
        cornerHit = ch
        func shard(_ k: String, _ d: ShardSpec) -> ShardSpec {
            ShardSpec(count: f.int("shards.\(k).count", d.count), g: f.double("shards.\(k).g", d.g),
                      life: f.double("shards.\(k).life", d.life), fadeFrom: f.double("shards.\(k).fadeFrom", d.fadeFrom),
                      vyMin: f.double("shards.\(k).vyMin", d.vyMin), vyMax: f.double("shards.\(k).vyMax", d.vyMax),
                      vxMin: f.double("shards.\(k).vxMin", d.vxMin), vxMax: f.double("shards.\(k).vxMax", d.vxMax),
                      spinDeg: f.double("shards.\(k).spin", d.spinDeg))
        }
        doorShards = shard("door", ShardSpec(count: 60, g: 1000, life: 0.90, fadeFrom: 0.65, vyMin: -260, vyMax: -120,
                                             vxMin: 40, vxMax: 160, spinDeg: 360))
        pipeShards = shard("pipe", ShardSpec(count: 40, g: 1000, life: 1.40, fadeFrom: 1.0, vyMin: -220, vyMax: -80,
                                             vxMin: 30, vxMax: 140, spinDeg: 300))
        boxShards = shard("box", ShardSpec(count: 140, g: 1275, life: 0.67, fadeFrom: 0.35, vyMin: 0, vyMax: 0,
                                           vxMin: 60, vxMax: 180, spinDeg: 240))
        obstacleTintAlpha = f.double("bump.obstacleTintAlpha", 0.6)
        hintColor = BoardConfig.color(f.string("color.hint", "#00DE00"))
        hintCameraDelay = f.double("hint.cameraDelay", 0.05)
        hintCameraDur = f.double("hint.cameraDur", 0.80)
        hintCurve = f.doubles("hint.cameraCurve", [0.25, 0.1, 0.25, 1.0])
        hintBlink = f.doubles("hint.blink", [1.03, 0.20, 0.13, 0.17, 0.38, 0.19])
        hintReturnDur = f.double("hint.returnDur", 0.50)
        panCentreInGrid = f.string("pan.limit", "centreInGrid") == "centreInGrid"
        zoomBounces = f.bool("zoom.bounces", true)
        attachPerFrame = max(20, f.int("load.attachPerFrame", 110))
        teardownPerFrame = max(20, f.int("load.teardownPerFrame", 120))
        prepBudgetMs = max(0, f.double("load.prepBudgetMs", 1.0))
    }
}

/// The exact cubic timing functions of SPEC-motion-audio §0.2 (a cubic polynomial with f(0) = 0, f(1) = 1 is exactly
/// cb(1/3, f'(0)/3, 2/3, 1 − f'(1)/3)).
enum Ease2 {
    static let linear = CAMediaTimingFunction(controlPoints: 1.0 / 3, 1.0 / 3, 2.0 / 3, 2.0 / 3)
    static let outQuad = CAMediaTimingFunction(controlPoints: 1.0 / 3, 2.0 / 3, 2.0 / 3, 1)
    static let inQuad = CAMediaTimingFunction(controlPoints: 1.0 / 3, 0, 2.0 / 3, 1.0 / 3)
    static let outCubic = CAMediaTimingFunction(controlPoints: 1.0 / 3, 1, 2.0 / 3, 1)
    static let inCubic = CAMediaTimingFunction(controlPoints: 1.0 / 3, 0, 2.0 / 3, 0)
    static let inOut = CAMediaTimingFunction(controlPoints: 0.42, 0, 0.58, 1)
    static func outBack(_ s: Double) -> CAMediaTimingFunction {
        CAMediaTimingFunction(controlPoints: 1.0 / 3, Float((s + 3) / 3), 2.0 / 3, 1)
    }
}

/// A cyclic colour field along an exit path (MA5: fixed on the path's arc coordinate σ, in cells). `palette` stops are
/// spread evenly over one `period`; `phase` (0…1) is drawn per exit from the fx stream.
struct ColourField {
    let palette: [CGColor]
    let comps: [[CGFloat]]
    let period: Double
    let phase: Double

    init(palette: [CGColor], period: Double, phase: Double) {
        self.palette = palette.isEmpty ? [UIColor.black.cgColor] : palette
        comps = self.palette.map { c in
            let k = c.components ?? [0, 0, 0, 1]
            return k.count >= 4 ? [k[0], k[1], k[2], k[3]] : [k[0], k[0], k[0], k.count > 1 ? k[1] : 1]
        }
        self.period = max(0.01, period)
        self.phase = phase - floor(phase)
    }

    /// Position in palette units (0…N) at σ cells.
    func position(_ sigma: Double) -> Double {
        let u = sigma / period + phase
        let n = Double(palette.count)
        let x = (u - floor(u)) * n
        return x >= n ? 0 : x
    }

    /// The interpolated colour at σ cells.
    func colour(_ sigma: Double) -> CGColor {
        let x = position(sigma)
        let i = Int(floor(x)) % palette.count
        let j = (i + 1) % palette.count
        let f = CGFloat(x - floor(x))
        if f < 0.001 { return palette[i] }
        let a = comps[i], b = comps[j]
        return UIColor(red: a[0] + (b[0] - a[0]) * f, green: a[1] + (b[1] - a[1]) * f, blue: a[2] + (b[2] - a[2]) * f,
                       alpha: 1).cgColor
    }

    /// The nearest palette entry at σ (star colours: "the palette colour at the spawn σ").
    func stop(_ sigma: Double) -> CGColor { palette[Int(position(sigma).rounded()) % palette.count] }
}

/// The deterministic effects stream (arch §4.13 `fx`): per stage from `StageSetup.seed`, forked per effect.
struct FXRandom {
    private var rng: PathRandom
    init(seed: UInt64, label: String) { rng = PathRandom(seed: seed).fork(label) }
    mutating func unit() -> Double { rng.unit() }
    mutating func range(_ a: Double, _ b: Double) -> Double { a + (b - a) * rng.unit() }
    mutating func sign() -> Double { rng.unit() < 0.5 ? -1 : 1 }
    mutating func u32() -> UInt32 { UInt32(truncatingIfNeeded: rng.next()) }
}

extension Anim {
    /// A discrete opacity switch at `at` seconds after `begin`: `from` before, `to` after (model = `to`).
    static func switchOpacity(_ layer: CALayer, from: Float, to: Float, begin: CFTimeInterval, at: Double, key: String) {
        let a = CAKeyframeAnimation(keyPath: "opacity")
        a.values = [from, to]
        a.keyTimes = [0, 1]
        a.calculationMode = .discrete
        a.duration = max(at, 0.0001)
        a.beginTime = begin
        a.fillMode = .backwards
        layer.opacity = to
        layer.add(a.hi(), forKey: key)
    }

    /// Layer-local "now" for a layer (the begin time of anything added this run-loop turn).
    static func now(_ l: CALayer) -> CFTimeInterval { l.convertTime(CACurrentMediaTime(), from: nil) }
}
