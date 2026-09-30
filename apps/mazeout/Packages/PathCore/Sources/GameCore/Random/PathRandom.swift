import Foundation

// SPEC-architecture §4.13 (D12). COPIED in WP0 from apps/matchfactory Packages/MFCore/Sources/MFCore/Random/MFRandom.swift
// (05424db, identical in the working tree), renamed MFRandom -> PathRandom; added `levelSeed(level:salt:)` and the
// §4.13 `below(_: Int) -> Int`. C1 OWNS the file from now on.
//
// Xoshiro256** (Blackman & Vigna), seeded through SplitMix64. Named sub-streams (§4.13): "generator", "hint",
// "autoplay", "fx", "combo". A new consumer never shifts another consumer's numbers, because `fork` reads the parent's
// state without advancing it.
//
// Every helper below is implemented here (not with the standard library's `random(in:using:)`), so the numbers a seed
// produces can never change with a Swift version: golden replays, `-pc.seed` captures and the bot stay reproducible.
// RandomTests pins the first 8 outputs for seeds 0, 1 and 42 against the independent reference tools/rng_ref.py.

public struct PathRandom: RandomNumberGenerator, Sendable {
    var s: (UInt64, UInt64, UInt64, UInt64) = (0, 0, 0, 0)

    /// The four state words are consecutive SplitMix64 outputs from `seed` (never all zero).
    public init(seed: UInt64) {
        var sm = seed
        s.0 = PathRandom.splitMixStep(&sm)
        s.1 = PathRandom.splitMixStep(&sm)
        s.2 = PathRandom.splitMixStep(&sm)
        s.3 = PathRandom.splitMixStep(&sm)
    }

    /// Raw state (tests: the published xoshiro256** vector starts from state (1, 2, 3, 4)).
    init(state: (UInt64, UInt64, UInt64, UInt64)) { s = state }

    public mutating func next() -> UInt64 {
        let result = PathRandom.rotl(s.1 &* 5, 7) &* 9
        let t = s.1 << 17
        s.2 ^= s.0
        s.3 ^= s.1
        s.1 ^= s.2
        s.0 ^= s.3
        s.2 ^= t
        s.3 = PathRandom.rotl(s.3, 45)
        return result
    }

    /// seed' = splitmix(state ^ fnv1a64(label)); does not advance self. The 256-bit state is folded to 64 bits with
    /// rotations (so no two state words can cancel each other out).
    public func fork(_ label: String) -> PathRandom {
        let folded = s.0 ^ PathRandom.rotl(s.1, 16) ^ PathRandom.rotl(s.2, 32) ^ PathRandom.rotl(s.3, 48)
        return PathRandom(seed: PathRandom.splitMix(folded ^ PathRandom.fnv1a64(label)))
    }

    /// Seed of one attempt of one level. Each step is a SplitMix64 bijection, so for a fixed install and level every
    /// attempt gets a different seed: a retry gets a new seed. `-pc.seed N` replaces `install`.
    public static func attemptSeed(install: UInt64, level: Int, attempt: Int) -> UInt64 {
        var h = splitMix(install ^ fnv1a64("attempt"))
        h = splitMix(h ^ UInt64(bitPattern: Int64(level)))
        h = splitMix(h ^ UInt64(bitPattern: Int64(attempt)))
        return h
    }

    /// Seed of a GENERATED level (§4.14 LevelProvider): the same board for every player, like authored content.
    /// Built like `attemptSeed`, so a Python mirror is two lines (add it to tools/rng_ref.py before pinning it).
    public static func levelSeed(level: Int, salt: UInt64) -> UInt64 {
        var h = splitMix(salt ^ fnv1a64("level"))
        h = splitMix(h ^ UInt64(bitPattern: Int64(level)))
        return h
    }

    // MARK: Version-stable draws

    /// Uniform in [0, 1), 53 random bits.
    public mutating func unit() -> Double { Double(next() >> 11) * 0x1.0p-53 }

    /// Uniform integer in 0..<n, unbiased (Lemire's multiply-shift with rejection). n must be > 0.
    public mutating func below(_ n: UInt64) -> UInt64 {
        precondition(n > 0, "PathRandom.below(0)")
        var m = next().multipliedFullWidth(by: n)
        if m.low < n {
            let threshold = (0 &- n) % n
            while m.low < threshold { m = next().multipliedFullWidth(by: n) }
        }
        return m.high
    }

    /// Uniform integer in 0..<n (§4.13 API); n must be > 0.
    public mutating func below(_ n: Int) -> Int {
        precondition(n > 0, "PathRandom.below(\(n))")
        return Int(below(UInt64(n)))
    }

    /// Uniform integer in a closed range.
    public mutating func int(in range: ClosedRange<Int>) -> Int {
        let span = UInt64(bitPattern: Int64(range.upperBound &- range.lowerBound)) &+ 1
        if span == 0 { return Int(Int64(bitPattern: next())) }            // the full Int range
        return range.lowerBound &+ Int(Int64(bitPattern: below(span)))
    }

    /// Uniform integer in a half-open range (must not be empty).
    public mutating func int(in range: Range<Int>) -> Int {
        precondition(!range.isEmpty, "PathRandom.int(in:) with an empty range")
        return int(in: range.lowerBound...(range.upperBound - 1))
    }

    /// Uniform in [lower, upper] (the upper bound is reached only through rounding).
    public mutating func double(in range: ClosedRange<Double>) -> Double {
        range.lowerBound + (range.upperBound - range.lowerBound) * unit()
    }

    public mutating func float(in range: ClosedRange<Float>) -> Float {
        Float(double(in: Double(range.lowerBound)...Double(range.upperBound)))
    }

    /// true with probability p.
    public mutating func chance(_ p: Double) -> Bool { unit() < p }

    /// ±1 with equal probability.
    public mutating func sign() -> Double { next() >> 63 == 0 ? 1 : -1 }

    /// Fisher–Yates, back to front.
    public mutating func shuffle<T>(_ array: inout [T]) {
        guard array.count > 1 else { return }
        for i in stride(from: array.count - 1, to: 0, by: -1) {
            let j = Int(below(UInt64(i + 1)))
            if i != j { array.swapAt(i, j) }
        }
    }

    public mutating func shuffled<T>(_ array: [T]) -> [T] { var a = array; shuffle(&a); return a }

    /// A uniformly chosen element, or nil for an empty collection.
    public mutating func element<C: Collection>(of c: C) -> C.Element? {
        guard !c.isEmpty else { return nil }
        return c[c.index(c.startIndex, offsetBy: Int(below(UInt64(c.count))))]
    }

    // MARK: Primitives (internal; the tests check them against the published reference values)

    @inline(__always) static func rotl(_ x: UInt64, _ k: UInt64) -> UInt64 { (x << k) | (x >> (64 - k)) }

    /// The SplitMix64 output function.
    @inline(__always) static func mix(_ z0: UInt64) -> UInt64 {
        var z = z0
        z = (z ^ (z >> 30)) &* 0xBF58_476D_1CE4_E5B9
        z = (z ^ (z >> 27)) &* 0x94D0_49BB_1331_11EB
        return z ^ (z >> 31)
    }

    /// One SplitMix64 generator step: advances `state` by the golden gamma and returns the mixed value.
    @inline(__always) static func splitMixStep(_ state: inout UInt64) -> UInt64 {
        state = state &+ 0x9E37_79B9_7F4A_7C15
        return mix(state)
    }

    /// SplitMix64 as a pure function of its input (the first output of a generator whose state is x).
    @inline(__always) package static func splitMix(_ x: UInt64) -> UInt64 { mix(x &+ 0x9E37_79B9_7F4A_7C15) }

    /// FNV-1a, 64 bit, over the UTF-8 bytes.
    package static func fnv1a64(_ label: String) -> UInt64 {
        var h: UInt64 = 0xCBF2_9CE4_8422_2325
        for b in label.utf8 { h ^= UInt64(b); h = h &* 0x0000_0100_0000_01B3 }
        return h
    }
}
