import Foundation
import GameCore

// C4 (SPEC-architecture §4.14 LevelProvider, D9; SPEC-gameplay §14.2-§14.3; CONSISTENCY L-7..L-9, §21.10).
// The game's level source: level n = the authored level when n ≤ the bundle's authored end, else the GENERATED level n
// (Generator = design/tools/gen_levels.py, seeded by PathRandom.levelSeed(n, curve.salt): the same board for every
// player). A generated level is served only after the full Validator passes it (content rules + the game's own rules:
// C2's greedy and a HeadlessDriver win at 0.6 s per tap): the Validator GATES the generator's attempt loop, so a
// candidate it refuses is rejected and the next attempt fork is tried (SPEC-gameplay §14.3 runtime) — the served level
// is the reference's own board whenever that board is valid and in band, and the next valid attempt otherwise (in
// L151-L650 the reference's L240, L254, L519, L580 and L617 are dead ends).
//
// C4c, the ENDLESS QUALITY GATE (SPEC.md §5.27): the validated winner is served only when `Difficulty.assess` finds it
// inside the bands (units, waves, free-at-start, the template's timer, grid, time share) with every Box counter inside the
// ring art's max (Difficulty.boxCounterArtMax = 99). Otherwise the level is RE-ROLLED: roll k (1 …) generates the same
// level number from `rollSeed(levelSeed, k)` (the seed salted with the roll number), up to `maxRolls` rolls in all; the
// first roll in band is served, and when none is, the roll whose assessment `ranksBefore` the others (fewest hard
// violations, then nearest the band centre; the earlier roll wins a tie). A roll the generator cannot finish is skipped.
// Every step is integer seeds + the deterministic generator, so a level number yields the same board on every device.
// In L151-L650 the reference's L430, L545, L572, L590 and L622 are out of band and re-rolled. If no roll yields a
// candidate at all, the nearest authored level of the same tag stands in (logged, never a crash, never an unvalidated
// board).
//
// Threading (CONSISTENCY §21.10, binding): generation runs OFF the main thread, ONE LEVEL AHEAD — call `prefetch(n)` at
// boot for the level the player is on and `levelStarted(n)` when a level starts (it prefetches the next one). `level(n)`
// returns at once for authored and prefetched levels; on a cache miss it waits for the job in flight (or generates on
// the calling thread), so the tap path never generates when the game follows that protocol. Results are cached (LRU).

public final class LevelProvider: @unchecked Sendable {

    /// How one level was produced (timings for the log and the evidence).
    public struct Record: Sendable, Equatable {
        /// generated: the level's own seed, in band · retried: a re-rolled seed, in band (SPEC.md §5.27) · nearest: no
        /// roll in band, the one nearest the band centre · fallback: no candidate at all, an authored stand-in.
        public enum Route: String, Sendable { case generated, retried, nearest, fallback }
        public var level: Int
        public var route: Route
        /// Candidate seeds tried (1 = the level's own seed passed).
        public var seedsTried: Int
        /// Wall milliseconds: the generator, the validator (+ the band check), the whole production (every roll).
        public var generateMs: Double
        public var validateMs: Double
        public var totalMs: Double
        /// Why earlier candidates were refused (validator findings, generator failures, band violations), "roll k …".
        public var refused: [String]
        /// The roll served (0 = the level's own seed; `rollSeed(levelSeed, roll)` otherwise; -1 = the fallback).
        public var roll: Int = 0
        /// The served level's band violations (empty unless the route is nearest or fallback).
        public var bandViolations: [String] = []
    }

    /// Rolls per generated level (SPEC.md §5.27 "bounded tries"): the level's own seed + 15 re-rolls.
    public static let maxRolls = 16

    public let library: LevelLibrary
    public let curve: CurveSpec
    public let options: Validator.Options
    /// The bands a served level must sit in (SPEC.md §5.27).
    public let bands: DifficultyBands
    public let maxRolls: Int
    public let cacheLimit: Int
    /// Called on the provider's queue after every production (the app logs it: "[PC][level] …").
    public var onProduced: (@Sendable (Record) -> Void)?

    private let queue: DispatchQueue
    private let lock = NSLock()
    private var cache: [Int: LevelSpec] = [:]
    private var recent: [Int] = []
    private var inFlight: [Int: DispatchGroup] = [:]
    private var log: [Record] = []

    public init(library: LevelLibrary, curve: CurveSpec? = nil, options: Validator.Options = Validator.Options(),
                bands: DifficultyBands = .designed, maxRolls: Int = LevelProvider.maxRolls,
                cacheLimit: Int = 8, qos: DispatchQoS = .utility) {
        self.library = library
        self.curve = curve ?? library.curve
        self.options = options
        self.bands = bands
        self.maxRolls = maxRolls
        self.cacheLimit = max(2, cacheLimit)
        queue = DispatchQueue(label: "pc.levels.generator", qos: qos)
    }

    /// The last authored level (the bundle's contiguous level files).
    public var authoredEnd: Int { library.authoredCount }

    public func isGenerated(_ n: Int) -> Bool { n > authoredEnd }

    /// Ready without waiting (authored, or generated and cached).
    public func isReady(_ n: Int) -> Bool {
        if !isGenerated(n) { return true }
        lock.lock(); defer { lock.unlock() }
        return cache[n] != nil
    }

    /// Every production so far (oldest first).
    public var records: [Record] { lock.lock(); defer { lock.unlock() }; return log }

    /// Level n (n < 1 reads as 1). See the threading note above.
    public func level(_ n: Int) -> LevelSpec {
        let n = max(1, n)
        if !isGenerated(n), let l = library.authored(n) { return l }
        lock.lock()
        if let l = cache[n] { touch(n); lock.unlock(); return l }
        if let g = inFlight[n] {
            lock.unlock()
            g.wait()
            lock.lock()
            if let l = cache[n] { lock.unlock(); return l }
        }
        lock.unlock()
        return produceAndStore(n)
    }

    /// Level n delivered on the provider's queue (never blocks the caller).
    public func level(_ n: Int, completion: @escaping @Sendable (LevelSpec) -> Void) {
        prefetch(n)
        queue.async { [self] in completion(level(n)) }
    }

    public func level(_ n: Int) async -> LevelSpec {
        await withCheckedContinuation { c in level(n) { c.resume(returning: $0) } }
    }

    /// Starts generating level n in the background (no-op for authored, cached or in-flight levels).
    public func prefetch(_ n: Int) {
        let n = max(1, n)
        guard isGenerated(n) else { return }
        lock.lock()
        if cache[n] != nil || inFlight[n] != nil { lock.unlock(); return }
        let g = DispatchGroup()
        g.enter()
        inFlight[n] = g
        lock.unlock()
        queue.async { [self] in
            _ = produceAndStore(n)
            g.leave()
        }
    }

    /// A level started: generate the one after its session (one level ahead).
    public func levelStarted(_ n: Int) {
        prefetch(library.nextLevel(after: library.session(containing: max(1, n))))
    }

    // MARK: production

    private func produceAndStore(_ n: Int) -> LevelSpec {
        let (l, rec) = LevelProvider.produce(n, curve: curve, library: library, options: options, bands: bands, maxRolls: maxRolls)
        lock.lock()
        cache[n] = l
        touch(n)
        inFlight[n] = nil
        log.append(rec)
        lock.unlock()
        onProduced?(rec)
        return l
    }

    private func touch(_ n: Int) {
        recent.removeAll { $0 == n }
        recent.append(n)
        while recent.count > cacheLimit { cache[recent.removeFirst()] = nil }
    }

    static func ms(_ a: UInt64, _ b: UInt64) -> Double { Double(b &- a) / 1_000_000 }

    /// The seed of roll `roll` of a level whose own seed is `levelSeed` (SPEC.md §5.27 "seed salted with the attempt
    /// number"): roll 0 is `levelSeed` itself (the reference board); roll k ≥ 1 is two SplitMix64 steps over the seed
    /// salted with "reroll" and k (built like PathRandom.levelSeed): a different seed per roll, the same on every device.
    public static func rollSeed(_ levelSeed: UInt64, roll: Int) -> UInt64 {
        guard roll > 0 else { return levelSeed }
        let h = PathRandom.splitMix(levelSeed ^ PathRandom.fnv1a64("reroll"))
        return PathRandom.splitMix(h ^ UInt64(bitPattern: Int64(roll)))
    }

    /// The validated, in-band generated level n (pure: no provider state; tests, `pclevels` and lvtool call it
    /// directly). See the header: validator-gated generation, then the band check with deterministic re-rolls.
    public static func produce(_ n: Int, curve: CurveSpec, library: LevelLibrary?, options: Validator.Options,
                               bands: DifficultyBands = .designed, maxRolls: Int = LevelProvider.maxRolls) -> (LevelSpec, Record) {
        let t0 = DispatchTime.now().uptimeNanoseconds
        var genMs = 0.0, valMs = 0.0
        var refused: [String] = []
        let base = PathRandom.levelSeed(level: n, salt: curve.salt)
        // the gate: the full Validator on every candidate that would win (content rules + the game's rules)
        var gateMs = 0.0
        let gate: Generator.Gate = { cand in
            var c = cand
            c.source = .generated
            let t = DispatchTime.now().uptimeNanoseconds
            let rep = Validator.checkLevel(c, raw: nil, sprites: nil, options: options)
            gateMs += ms(t, DispatchTime.now().uptimeNanoseconds)
            return rep.isValid ? nil : rep.errors.first.map(\.message) ?? "invalid"
        }
        let rolls = max(1, maxRolls)
        var nearest: (level: LevelSpec, a: Difficulty.Assessment, roll: Int)?
        for k in 0..<rolls {
            let ta = DispatchTime.now().uptimeNanoseconds
            let out: Generator.Output
            do { out = try Generator.generate(level: n, curve: curve, seed: rollSeed(base, roll: k), gate: gate) } catch {
                genMs += ms(ta, DispatchTime.now().uptimeNanoseconds) - gateMs
                valMs += gateMs
                gateMs = 0
                refused.append("roll \(k): \(error)")
                continue
            }
            genMs += ms(ta, DispatchTime.now().uptimeNanoseconds) - gateMs
            valMs += gateMs
            gateMs = 0
            var l = out.level
            l.source = .generated
            refused += out.info.rejected.filter { $0.hasPrefix("gate: ") }.map { "roll \(k) " + $0 }
            // the winner passed the gate (the same Validator); now the bands (SPEC.md §5.27)
            let tb = DispatchTime.now().uptimeNanoseconds
            let a = try? Difficulty.assess(l, curve: curve, bands: bands)
            valMs += ms(tb, DispatchTime.now().uptimeNanoseconds)
            guard let a, !a.inBand else {
                // in band (an unassessable level cannot occur: its target is the generator's own): served
                return (l, Record(level: n, route: k == 0 ? .generated : .retried, seedsTried: k + 1, generateMs: genMs,
                                  validateMs: valMs, totalMs: ms(t0, DispatchTime.now().uptimeNanoseconds), refused: refused,
                                  roll: k))
            }
            refused.append("roll \(k): out of band: " + a.violations.joined(separator: "; "))
            if nearest == nil || a.ranksBefore(nearest!.a) { nearest = (l, a, k) }
        }
        if let x = nearest {
            // no roll in band: the nearest to the band centre (fewest hard violations first)
            return (x.level, Record(level: n, route: .nearest, seedsTried: rolls, generateMs: genMs, validateMs: valMs,
                                    totalMs: ms(t0, DispatchTime.now().uptimeNanoseconds), refused: refused,
                                    roll: x.roll, bandViolations: x.a.violations))
        }
        // the never-crash net: the nearest authored level of the same tag, renumbered
        let tag = Difficulty.cadenceTag(n, curve: curve)
        var stand: LevelSpec?
        if let lib = library {
            var m = lib.authoredCount
            while m >= 1 && stand == nil {
                if let a = lib.authored(m), a.tag == tag, a.arrows.count > 1 { stand = a }
                m -= 1
            }
        }
        var l = stand ?? LevelProvider.minimalLevel(n, tag: tag, curve: curve)
        l.level = n
        l.source = .generated
        l.unlock = nil
        l.seed = nil
        let v = (try? Difficulty.assess(l, curve: curve, bands: bands))?.violations ?? []
        return (l, Record(level: n, route: .fallback, seedsTried: rolls, generateMs: genMs, validateMs: valMs,
                          totalMs: ms(t0, DispatchTime.now().uptimeNanoseconds), refused: refused, roll: -1, bandViolations: v))
    }

    /// Last resort when no library is available either: a tiny always-solvable board (tests only in practice).
    static func minimalLevel(_ n: Int, tag: LevelTag, curve: CurveSpec) -> LevelSpec {
        let arrows = (0..<4).map { i in ArrowSpec(id: ArrowID(i), cells: [Cell(i, 3), Cell(i, 2), Cell(i, 1)], dir: .up) }
        let tt = try? Generator.target(curve, n).templateTimer
        var l = LevelSpec(level: n, source: .generated, cols: 4, rows: 4,
                          timerSeconds: Difficulty.allowedTimers(tag, curve: curve, templateTimer: tt).max() ?? 180,
                          hearts: 3, tag: tag, arrows: arrows)
        l.metrics = ContentRules.metrics(l).bundle
        return l
    }
}
