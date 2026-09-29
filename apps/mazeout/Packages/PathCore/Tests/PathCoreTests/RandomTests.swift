import XCTest
@testable import PathCore     // the published xoshiro vector needs the raw-state init (internal)

/// C1 (SPEC-architecture §4.13, D12): PathRandom equals the independent references — tools/rng_ref.py (MF's, read-only)
/// and Tests/tools/c1_rng_ref_extra.py (levelSeed, below) — pinned here AND checked live against the scripts' output.
final class RandomTests: XCTestCase {

    // Values printed by `python3 tools/rng_ref.py` (never edit them to match the Swift).
    static let first8: [UInt64: [UInt64]] = [
        0: [0x99EC5F36CB75F2B4, 0xBF6E1F784956452A, 0x1A5F849D4933E6E0, 0x6AA594F1262D2D2C,
            0xBBA5AD4A1F842E59, 0xFFEF8375D9EBCACA, 0x6C160DEED2F54C98, 0x8920AD648FC30A3F],
        1: [0xB3F2AF6D0FC710C5, 0x853B559647364CEA, 0x92F89756082A4514, 0x642E1C7BC266A3A7,
            0xB27A48E29A233673, 0x24C123126FFDA722, 0x123004EF8DF510E6, 0x61954DCC47B1E89D],
        42: [0x15780B2E0C2EC716, 0x6104D9866D113A7E, 0xAE17533239E499A1, 0xECB8AD4703B360A1,
             0xFDE6DC7FE2EC5E64, 0xC50DA53101795238, 0xB82154855A65DDB2, 0xD99A2743EBE60087],
    ]

    func testFirstEightOutputsMatchRngRef() {
        for (seed, expected) in RandomTests.first8 {
            var r = PathRandom(seed: seed)
            XCTAssertEqual((0..<8).map { _ in r.next() }, expected, "seed \(seed)")
        }
        // The published xoshiro256** vector from state (1, 2, 3, 4) and SplitMix64's first outputs from 0.
        var x = PathRandom(state: (1, 2, 3, 4))
        XCTAssertEqual((0..<4).map { _ in x.next() }, [11520, 0, 1509978240, 1215971899390074240])
        var sm: UInt64 = 0
        XCTAssertEqual((0..<4).map { _ in PathRandom.splitMixStep(&sm) },
                       [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4, 0x06C45D188009454F, 0xF88BB8A8724C81EC])
        XCTAssertEqual(PathRandom.fnv1a64("spawn"), 0x4328F78AB20E1F98)
        XCTAssertEqual(PathRandom.fnv1a64(""), 0xCBF29CE484222325)
    }

    func testForksAttemptSeedsAndUnit() {
        var spawn = PathRandom(seed: 42).fork("spawn")
        XCTAssertEqual((0..<4).map { _ in spawn.next() }, [0xB9BB3721FD8636E6, 0x24460CC4D2E5E468, 0xC66E61955C211495, 0x66DB7CE32EFD173E])
        var hint = PathRandom(seed: 42).fork("hint")
        XCTAssertEqual((0..<4).map { _ in hint.next() }, [0x7E2CD01BAB3605D1, 0xE572465D3E420439, 0x132171D6A148A154, 0xAA9BB41BFDC800C3])
        XCTAssertEqual(PathRandom.attemptSeed(install: 42, level: 1, attempt: 1), 0x2AA7E46C18DBC455)
        XCTAssertEqual(PathRandom.attemptSeed(install: 42, level: 1, attempt: 2), 0x09F06948AB91F485)
        XCTAssertEqual(PathRandom.attemptSeed(install: 42, level: 2, attempt: 1), 0xB9BA5C379319B214)
        var u = PathRandom(seed: 42)
        XCTAssertEqual((0..<4).map { _ in u.unit() }, [0.08386297105988216, 0.3789802506626686, 0.6800434110281394, 0.9246929453253876])
    }

    func testForkIndependence() {
        // A fork does not advance its parent, and a new consumer never shifts another's numbers (§4.13).
        var parent = PathRandom(seed: 9)
        let before = parent
        _ = parent.fork("generator")
        _ = parent.fork("fx")
        var p2 = before
        XCTAssertEqual(parent.next(), p2.next(), "forking does not advance the parent")
        let base = PathRandom(seed: 9)
        var g1 = base.fork("generator")
        let g1v = (0..<16).map { _ in g1.next() }
        let withNewConsumer = base
        var combo = withNewConsumer.fork("combo")
        _ = (0..<100).map { _ in combo.next() }
        var g2 = withNewConsumer.fork("generator")
        XCTAssertEqual((0..<16).map { _ in g2.next() }, g1v)
        // Streams differ from each other and from the parent.
        let labels = ["generator", "hint", "autoplay", "fx", "combo"]
        var firsts = Set<UInt64>()
        for l in labels { var f = base.fork(l); firsts.insert(f.next()) }
        var b = base
        firsts.insert(b.next())
        XCTAssertEqual(firsts.count, labels.count + 1)
        // Fork of a fork is deterministic.
        var ff1 = base.fork("a").fork("b"), ff2 = base.fork("a").fork("b")
        XCTAssertEqual(ff1.next(), ff2.next())
    }

    // Values printed by `python3 Packages/PathCore/Tests/tools/c1_rng_ref_extra.py`.
    func testLevelSeedsMatchTheReference() {
        XCTAssertEqual(PathRandom.levelSeed(level: 1, salt: 0), 0xE72936680555D141)
        XCTAssertEqual(PathRandom.levelSeed(level: 62, salt: 0), 0x14E96231EEEC001B)
        XCTAssertEqual(PathRandom.levelSeed(level: 100, salt: 1), 0x3AF5087F45DF1E94)
        XCTAssertEqual(PathRandom.levelSeed(level: 101, salt: 1), 0x29BE6CF55BA6FE6C)
        XCTAssertEqual(PathRandom.levelSeed(level: 5000, salt: 0xC0FFEE), 0x5F367ED57EFA169C)
        XCTAssertEqual(PathRandom.levelSeed(level: -1, salt: 42), 0x2D4DD90AF32BBD8E)
        // Stable and distinct over the generated range (the same board for every player).
        var seen = Set<UInt64>()
        for n in 62...20_000 { XCTAssertTrue(seen.insert(PathRandom.levelSeed(level: n, salt: 7)).inserted) }
        XCTAssertNotEqual(PathRandom.levelSeed(level: 100, salt: 1), PathRandom.levelSeed(level: 100, salt: 2))
    }

    func testBelowMatchesTheReferenceAndIsUnbiased() {
        func draws(_ seed: UInt64, _ n: Int) -> [Int] { var r = PathRandom(seed: seed); return (0..<8).map { _ in r.below(n) } }
        XCTAssertEqual(draws(42, 6), [0, 2, 4, 5, 5, 4, 4, 5])
        XCTAssertEqual(draws(7, 1000), [700, 278, 839, 981, 990, 872, 60, 104])
        XCTAssertEqual(draws(1, 3), [2, 1, 1, 1, 2, 0, 0, 1])
        var big = PathRandom(seed: 0)
        XCTAssertEqual((0..<8).map { _ in big.below(UInt64(1) << 63) },
                       [5545672335626533210, 6896998655084667541, 950191689423254384, 3842356051313071766,
                        6760701995058861868, 9221051770647995749, 3894213962488260172, 4940544114935563551])
        // Range and a loose uniformity check (χ² over 6 bins, 60 000 draws).
        var r = PathRandom(seed: 11)
        var bins = [Int](repeating: 0, count: 6)
        for _ in 0..<60_000 { let v = r.below(6); XCTAssertTrue((0..<6).contains(v)); bins[v] += 1 }
        let chi2 = bins.map { pow(Double($0) - 10_000, 2) / 10_000 }.reduce(0, +)
        XCTAssertLessThan(chi2, 20.5, "χ²(5) at p = 0.001")
        var one = PathRandom(seed: 3)
        XCTAssertEqual(one.below(1), 0)
        var ranged = PathRandom(seed: 4)
        for _ in 0..<1000 { XCTAssertTrue((-3...3).contains(ranged.int(in: -3...3))) }
    }

    func testLiveAgainstThePythonReferences() throws {
        guard let ref = C1Fixtures.python("tools/rng_ref.py") else { throw XCTSkip("python3 not available") }
        for (seed, expected) in RandomTests.first8 {
            let line = ref.split(separator: "\n").first { $0.hasPrefix("seed \(seed):") }
            XCTAssertNotNil(line, "rng_ref.py prints seed \(seed)")
            let hex = line.map { String($0).components(separatedBy: ": ")[1].components(separatedBy: ", ") } ?? []
            XCTAssertEqual(hex.compactMap { UInt64($0.dropFirst(2), radix: 16) }, expected, "seed \(seed)")
        }
        XCTAssertTrue(ref.contains(String(format: "attemptSeed(42,1,1) = 0x%016llX", PathRandom.attemptSeed(install: 42, level: 1, attempt: 1))))
        guard let extra = C1Fixtures.python("Packages/PathCore/Tests/tools/c1_rng_ref_extra.py") else {
            XCTFail("c1_rng_ref_extra.py did not run"); return
        }
        for (level, salt) in [(1, 0), (62, 0), (100, 1), (101, 1), (5000, 0xC0FFEE), (-1, 42)] as [(Int, UInt64)] {
            let expect = String(format: "levelSeed(level %d, salt %llu) = 0x%016llX", level, salt, PathRandom.levelSeed(level: level, salt: salt))
            XCTAssertTrue(extra.contains(expect), expect)
        }
        var r = PathRandom(seed: 7)
        let seven = (0..<8).map { _ in String(r.below(1000)) }.joined(separator: ", ")
        XCTAssertTrue(extra.contains("below seed 7 n 1000: \(seven)"))
    }
}
