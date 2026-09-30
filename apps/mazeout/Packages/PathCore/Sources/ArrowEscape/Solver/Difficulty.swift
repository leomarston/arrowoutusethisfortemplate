import Foundation
import GameCore

// C4 (SPEC-architecture §4.14, §4.17 "in their curve bands"; SPEC-gameplay §14.3). Difficulty of a level against the
// generator curve: the level's measured units / waves / free-at-start / grid / timer against the curve target of its
// number, and the band a generated level must fall in.
//
// The bands are the envelope of the reference generator's own authored output (design/levels.json L84-L150 since the
// content recast of 2026-09-25, designed by gen_levels.py from the same curve) widened by a quarter of its width on each
// side: a runtime level is "in band" when it looks like the designed ones. Hard constraints on top: the cadence tag, the
// timer (the tag's, or the target template's when the curve says `timers.fromTemplate`), the grid inside the
// target (the crop never grows it) and the curve's size cap, the 0.6 s/tap driver keeping ≥ 20 % of the timer, and
// (C4c, SPEC.md §5.27) every Box counter inside what the counter ring's art can show.
// GeneratorTests pins the constants below to that envelope.
//
// C4c (SPEC.md §5.27, the ENDLESS QUALITY GATE): LevelProvider serves a generated level only when `assess` finds no
// violation; otherwise it re-rolls the seed and, after its bounded tries, serves the candidate `ranksBefore` the others
// (fewest hard violations, then the smallest `centreDistance`).

public struct DifficultyBands: Sendable, Equatable {
    /// measured units / target units
    public var unitsRatio: ClosedRange<Double>
    /// measured waves / target waves
    public var roundsRatio: ClosedRange<Double>
    /// measured free-at-start − target free
    public var freeDelta: ClosedRange<Int>
    /// the driver's time left / timer
    public var minTimeShare: Double
    /// The largest Box (and curtain) counter a level may carry: the counter ring's art limit (Difficulty.boxCounterArtMax).
    public var maxBoxCounter: Int

    /// Envelope of the designed L106-L150 (units 0.842…1.239, waves 0.467…1.500, free −6…+5), widened by 25 % of the
    /// width (C4FullTests.testBandsAreTheDesignedEnvelope recomputes it from the pinned levels.json).
    public static let designed = DifficultyBands(unitsRatio: 0.743...1.339, roundsRatio: 0.208...1.758, freeDelta: -9...8,
                                                 minTimeShare: 0.2, maxBoxCounter: Difficulty.boxCounterArtMax)

    public init(unitsRatio: ClosedRange<Double>, roundsRatio: ClosedRange<Double>, freeDelta: ClosedRange<Int>, minTimeShare: Double,
                maxBoxCounter: Int = Difficulty.boxCounterArtMax) {
        self.unitsRatio = unitsRatio; self.roundsRatio = roundsRatio; self.freeDelta = freeDelta; self.minTimeShare = minTimeShare
        self.maxBoxCounter = maxBoxCounter
    }

    /// How far a measurement lies from the centre of the three ratio bands: each of the units ratio, the waves ratio and
    /// the free-at-start delta as |x − centre| / half-width (0 = the centre, 1 = on that band's edge), combined as the
    /// Euclidean norm. Inside all three bands ⇒ every term ≤ 1.
    public func centreDistance(unitsRatio u: Double, roundsRatio r: Double, freeDelta f: Int) -> Double {
        func term(_ x: Double, _ lo: Double, _ hi: Double) -> Double {
            let half = (hi - lo) / 2
            return half > 0 ? abs(x - (lo + hi) / 2) / half : (x == lo ? 0 : .infinity)
        }
        let a = term(u, unitsRatio.lowerBound, unitsRatio.upperBound)
        let b = term(r, roundsRatio.lowerBound, roundsRatio.upperBound)
        let c = term(Double(f), Double(freeDelta.lowerBound), Double(freeDelta.upperBound))
        return (a * a + b * b + c * c).squareRoot()
    }
}

public enum Difficulty {

    /// The Box counter ring's art limit (SPEC.md §5.27). The counter is live text in the well of the fixed-size boxRing
    /// sprite (art/MANIFEST.json `boxRing`: "the counter is live text in the well"; its notes state no numeric limit), so
    /// the limit is the L2 measurement build/l2/box-digits-fit.txt: the well is 0.439 of the ring diameter, the 2-digit
    /// counters measured fit (8 … 99, widest "77": 0.424) and every 3-digit one overflows (≥ 0.616); App/Board/DigitGlyphs
    /// warms "0"..."99" only. Hence 99.
    public static let boxCounterArtMax = 99

    public struct Assessment: Sendable {
        public var target: Generator.Target
        public var measured: ContentRules.Measured
        /// Empty = inside the bands.
        public var violations: [String]
        /// The violations outside the three ratio bands (tag, timer, grid, time share, Box counter).
        public var hardViolations: Int
        /// `DifficultyBands.centreDistance` of the level (units, waves, free-at-start).
        public var centreDistance: Double
        public var unitsRatio: Double { Double(measured.units) / Double(max(1, target.units)) }
        public var roundsRatio: Double { Double(measured.rounds) / Double(max(1, target.rounds)) }
        public var inBand: Bool { violations.isEmpty }

        /// The re-roll order (SPEC.md §5.27 "the closest-to-profile candidate"): fewer hard violations first, then the
        /// smaller distance from the band centre. Strict, so the earlier candidate wins a tie.
        public func ranksBefore(_ other: Assessment) -> Bool {
            hardViolations != other.hardViolations ? hardViolations < other.hardViolations : centreDistance < other.centreDistance
        }
    }

    /// The cadence tag of level n (SPEC-gameplay §10.5: every level ending in 4 is Hard, in 9 Super Hard).
    public static func cadenceTag(_ n: Int, curve: CurveSpec = .default) -> LevelTag {
        let p = Silhouettes.floorMod(n, curve.cycle)
        switch curve.tagByPosition[p] {
        case "hard"?: return .hard
        case "superHard"?: return .superHard
        default: return .normal
        }
    }

    /// The timers a level of `tag` may carry. With `timers.fromTemplate` (the recast curve) a level carries its target
    /// template's recorded timer whatever its tag (gen_levels.timer_for), so that timer is the only one allowed when
    /// `templateTimer` is given.
    public static func allowedTimers(_ tag: LevelTag, curve: CurveSpec = .default, templateTimer: Int? = nil) -> Set<Int> {
        if curve.timers.fromTemplate, let tt = templateTimer { return [tt] }
        switch tag {
        case .hard: return [curve.timers.hard]
        case .superHard: return [curve.timers.superHard]
        case .normal: return [curve.timers.normal, curve.timers.short]
        }
    }

    /// A level (normally a generated one) against the curve target of its number.
    public static func assess(_ level: LevelSpec, curve: CurveSpec = .default, bands: DifficultyBands = .designed) throws -> Assessment {
        let t = try Generator.target(curve, level.level)
        let m = ContentRules.metrics(level)
        var v: [String] = []
        var hard = 0
        func H(_ s: String) { v.append(s); hard += 1 }
        if level.tag != cadenceTag(level.level, curve: curve) { H("tag \(level.tag.rawValue) off the cadence") }
        if !allowedTimers(level.tag, curve: curve, templateTimer: t.templateTimer).contains(level.timerSeconds) { H("timer \(level.timerSeconds) for \(level.tag.rawValue)") }
        if level.cols > t.cols || level.rows > t.rows { H("grid \(level.cols)x\(level.rows) beyond the target \(t.cols)x\(t.rows)") }
        if level.cols > curve.maxCols || level.rows > curve.maxRows { H("grid \(level.cols)x\(level.rows) beyond the cap") }
        let ur = Double(m.units) / Double(max(1, t.units)), rr = Double(m.rounds) / Double(max(1, t.rounds))
        if !bands.unitsRatio.contains(ur) { v.append(String(format: "units %d vs target %d (×%.2f)", m.units, t.units, ur)) }
        if !bands.roundsRatio.contains(rr) { v.append(String(format: "waves %d vs target %d (×%.2f)", m.rounds, t.rounds, rr)) }
        if !bands.freeDelta.contains(m.freeAtStart - t.free) { v.append("free at start \(m.freeAtStart) vs target \(t.free)") }
        if m.botTimeLeft < bands.minTimeShare * Double(level.timerSeconds) { H("time left \(m.botTimeLeft) of \(level.timerSeconds)") }
        for o in level.obstacles where o.kind == .box || o.kind == .curtain {
            if let c = o.counter, c > bands.maxBoxCounter { H("box \(o.id.raw) counter \(c) above the ring art's max \(bands.maxBoxCounter)") }
        }
        return Assessment(target: t, measured: m, violations: v, hardViolations: hard,
                          centreDistance: bands.centreDistance(unitsRatio: ur, roundsRatio: rr, freeDelta: m.freeAtStart - t.free))
    }
}
