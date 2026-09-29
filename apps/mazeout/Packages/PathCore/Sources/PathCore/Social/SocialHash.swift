import Foundation

// SOC1 (SPEC-architecture §4.11 invariants 2-3, SPEC-social §7 "Exactness rules").
// The exact-arithmetic primitives of the offline world, a bit-for-bit port of design/social/tools/socialsim/core.py:
//   * UInt64 wrap-around (&* &+ ^ >>), the SplitMix64 finaliser + FNV-1a-64 of tools/rng_ref.py, used STATELESSLY:
//     every derived quantity is h64(seed, "label", a, b, …), so any player / day / event is computed in O(1);
//   * doubles: only correctly rounded + − × ÷ and comparisons; floor via `.rounded(.down)`; NO exp/log/pow/sqrt, NO FMA
//     (`addingProduct` is banned in PathCore/Social; Swift never contracts `a * b + c`);
//   * rounding is floor(x) or floor(x + 0.5) written out (never `.rounded()` = banker's/schoolbook ambiguity);
//   * integer division / modulo of possibly negative numbers go through floorDiv / posMod (Swift / and % truncate).
// Negative hash arguments are passed as their two's complement (Python: x & M).

enum SocialHash {
    static let golden: UInt64 = 0x9E37_79B9_7F4A_7C15

    @inline(__always)
    static func mix(_ z0: UInt64) -> UInt64 {
        var z = z0
        z = (z ^ (z >> 30)) &* 0xBF58_476D_1CE4_E5B9
        z = (z ^ (z >> 27)) &* 0x94D0_49BB_1331_11EB
        return z ^ (z >> 31)
    }

    @inline(__always)
    static func splitmix(_ x: UInt64) -> UInt64 { mix(x &+ golden) }

    /// FNV-1a 64 of the UTF-8 bytes of `label`.
    static func fnv1a64(_ label: String) -> UInt64 {
        var h: UInt64 = 0xcbf2_9ce4_8422_2325
        for b in label.utf8 {
            h ^= UInt64(b)
            h = h &* 0x0000_0100_0000_01b3
        }
        return h
    }

    @inline(__always) static func word(_ x: Int) -> UInt64 { UInt64(bitPattern: Int64(x)) }

    // Stateless keyed hash: splitmix chain over (seed ^ fnv(label)), then each integer argument (two's complement).
    // `Label` carries the precomputed FNV so the hot paths never re-hash a string.
    @inline(__always) static func h64(_ seed: UInt64, _ l: Label) -> UInt64 { splitmix(seed ^ l.fnv) }
    @inline(__always) static func h64(_ seed: UInt64, _ l: Label, _ a: Int) -> UInt64 {
        splitmix(splitmix(seed ^ l.fnv) ^ word(a))
    }
    @inline(__always) static func h64(_ seed: UInt64, _ l: Label, _ a: Int, _ b: Int) -> UInt64 {
        splitmix(splitmix(splitmix(seed ^ l.fnv) ^ word(a)) ^ word(b))
    }
    @inline(__always) static func h64(_ seed: UInt64, _ l: Label, _ a: Int, _ b: Int, _ c: Int) -> UInt64 {
        splitmix(splitmix(splitmix(splitmix(seed ^ l.fnv) ^ word(a)) ^ word(b)) ^ word(c))
    }
    @inline(__always) static func h64(_ seed: UInt64, _ l: Label, _ a: Int, _ b: Int, _ c: Int, _ d: Int) -> UInt64 {
        splitmix(splitmix(splitmix(splitmix(splitmix(seed ^ l.fnv) ^ word(a)) ^ word(b)) ^ word(c)) ^ word(d))
    }
    @inline(__always) static func h64(_ seed: UInt64, _ l: Label, _ a: Int, _ b: Int, _ c: Int, _ d: Int, _ e: Int) -> UInt64 {
        splitmix(splitmix(splitmix(splitmix(splitmix(splitmix(seed ^ l.fnv) ^ word(a)) ^ word(b)) ^ word(c)) ^ word(d)) ^ word(e))
    }
    /// Any arity (fixtures, tests; the hot paths use the fixed-arity forms above).
    static func h64(_ seed: UInt64, _ label: String, _ xs: [Int]) -> UInt64 {
        var h = splitmix(seed ^ fnv1a64(label))
        for x in xs { h = splitmix(h ^ word(x)) }
        return h
    }

    /// [0, 1) from the top 53 bits.
    @inline(__always) static func unit(_ h: UInt64) -> Double { Double(h >> 11) * (1.0 / 9007199254740992.0) }

    @inline(__always) static func u01(_ seed: UInt64, _ l: Label) -> Double { unit(h64(seed, l)) }
    @inline(__always) static func u01(_ seed: UInt64, _ l: Label, _ a: Int) -> Double { unit(h64(seed, l, a)) }
    @inline(__always) static func u01(_ seed: UInt64, _ l: Label, _ a: Int, _ b: Int) -> Double { unit(h64(seed, l, a, b)) }
    @inline(__always) static func u01(_ seed: UInt64, _ l: Label, _ a: Int, _ b: Int, _ c: Int) -> Double {
        unit(h64(seed, l, a, b, c))
    }

    /// Integer in [0, n): floor(unit * n) (exact for n < 2^53).
    @inline(__always) static func below(_ seed: UInt64, _ l: Label, _ n: Int) -> Int { floorInt(u01(seed, l) * Double(n)) }
    @inline(__always) static func below(_ seed: UInt64, _ l: Label, _ n: Int, _ a: Int) -> Int {
        floorInt(u01(seed, l, a) * Double(n))
    }
    @inline(__always) static func below(_ seed: UInt64, _ l: Label, _ n: Int, _ a: Int, _ b: Int) -> Int {
        floorInt(u01(seed, l, a, b) * Double(n))
    }

    // ------------------------------------------------------------------ integer / rounding helpers

    /// Python `a // b` (floors toward −∞).
    @inline(__always) static func floorDiv(_ a: Int, _ b: Int) -> Int {
        let q = a / b
        return (a % b != 0 && ((a < 0) != (b < 0))) ? q - 1 : q
    }
    /// Python `a % b` (sign of b).
    @inline(__always) static func posMod(_ a: Int, _ b: Int) -> Int {
        let r = a % b
        return (r != 0 && ((r < 0) != (b < 0))) ? r + b : r
    }
    /// math.floor as an Int.
    @inline(__always) static func floorInt(_ x: Double) -> Int { Int(x.rounded(.down)) }
    /// floor(x + 0.5) (never banker's rounding).
    @inline(__always) static func roundHalfUp(_ x: Double) -> Int { Int((x + 0.5).rounded(.down)) }

    // ------------------------------------------------------------------ keyed permutations (format-preserving)

    @inline(__always)
    static func permPow2(_ x: UInt64, _ half: Int, _ key: UInt64) -> UInt64 {
        let mask: UInt64 = (1 << UInt64(half)) &- 1
        var l = x >> UInt64(half)
        var r = x & mask
        for round in 0..<4 {
            let f = splitmix(key ^ (UInt64(round + 1) << 56) ^ r) & mask
            let nl = r
            r = l ^ f
            l = nl
        }
        return (l << UInt64(half)) | r
    }

    @inline(__always)
    static func permHalf(_ n: Int) -> Int {
        var bits = max(2, Int.bitWidth - (n - 1).leadingZeroBitCount)   // (n-1).bit_length(), n >= 2
        if bits & 1 == 1 { bits += 1 }
        return bits / 2
    }

    /// Bijection of [0, n) keyed by `key`: a 4-round balanced Feistel network on the smallest even bit width covering n,
    /// with cycle-walking back into [0, n). n >= 1.
    static func perm(_ x: Int, _ n: Int, _ key: UInt64) -> Int {
        if n <= 1 { return 0 }
        let half = permHalf(n)
        let nn = UInt64(n)
        // cycle walking only terminates from inside [0, n): an out-of-range x (a caller bug) is reduced first instead of
        // hanging (valid inputs are unchanged, so the reference's values stand)
        let x0 = x >= 0 && x < n ? x : posMod(x, n)
        var y = permPow2(UInt64(x0), half, key)
        while y >= nn { y = permPow2(y, half, key) }
        return Int(y)
    }

    /// Inverse of `perm` (tests).
    static func permInv(_ y: Int, _ n: Int, _ key: UInt64) -> Int {
        if n <= 1 { return 0 }
        let half = permHalf(n)
        let mask: UInt64 = (1 << UInt64(half)) &- 1
        func inv(_ z: UInt64) -> UInt64 {
            var l = z >> UInt64(half)
            var r = z & mask
            for round in stride(from: 3, through: 0, by: -1) {
                let f = splitmix(key ^ (UInt64(round + 1) << 56) ^ l) & mask
                let nl = r ^ f
                r = l
                l = nl
            }
            return (l << UInt64(half)) | r
        }
        var x = inv(UInt64(y))
        while x >= UInt64(n) { x = inv(x) }
        return Int(x)
    }

    // ------------------------------------------------------------------ piecewise-linear tables

    /// Piecewise-linear interpolation, xs strictly increasing, clamped at both ends. Exact IEEE ops only (= core.interp).
    @inline(__always)
    static func interp(_ u: Double, _ xs: [Double], _ ys: [Double]) -> Double {
        if u <= xs[0] { return ys[0] }
        var i = 1
        while i < xs.count {
            if u <= xs[i] {
                let x0 = xs[i - 1], x1 = xs[i]
                let t = (u - x0) / (x1 - x0)
                return ys[i - 1] + (ys[i] - ys[i - 1]) * t
            }
            i += 1
        }
        return ys[ys.count - 1]
    }
}

/// A hash label with its FNV-1a-64 precomputed. Every label the model uses is listed once in `SocialLabels`.
struct Label: Sendable {
    let text: String
    let fnv: UInt64
    init(_ text: String) { self.text = text; fnv = SocialHash.fnv1a64(text) }
}

/// The hash labels of the reference (socialsim/*.py), spelled exactly as there. A typo here moves the whole world, and the
/// golden tests catch it (mutation m3 of SPEC-architecture §4.17).
enum SocialLabels {
    // population.py
    static let cn = Label("cn"), ccountry = Label("ccountry"), cv = Label("cv"), pace = Label("pace")
    static let play = Label("play"), vol = Label("vol"), lapse = Label("lapse"), gap = Label("gap")
    static let ncustom = Label("ncustom"), nstyle = Label("nstyle"), nsys = Label("nsys"), sk = Label("sk"), ss = Label("ss"), sf = Label("sf")
    static let style = Label("style"), avatarQ = Label("avatar?"), avatar = Label("avatar")
    // names.py
    static let tok = Label("tok"), grid = Label("grid"), dflt = Label("default"), spell = Label("spell"), caseL = Label("case")
    static let username = Label("username")
    // events.py
    static let order = Label("order"), early = Label("early"), arrE = Label("arrE"), arrL = Label("arrL")
    static let s0 = Label("s0"), q = Label("q"), fail = Label("fail"), hold = Label("hold"), delta = Label("delta")
    static let haz = Label("haz"), w1 = Label("w1"), w2 = Label("w2")
    static let weekly = Label("weekly"), streak = Label("streak"), rocket = Label("rocket"), sky = Label("sky")
    // shipped-model mechanisms of the reference (names.VARIANTS, events.SKY_DROPS; socialsim/shipped.py)
    static let upper = Label("upper"), lower = Label("lower"), d2 = Label("d2"), r2 = Label("r2")
    static let hazd = Label("hazd"), win = Label("win")
    // shipped drawn nicknames (names.DRAW / drawn, population 'nick'; SOC1c)
    static let nick = Label("nick"), headQ = Label("head?"), head = Label("head"), pop = Label("pop"), suf = Label("suf")
    static let pick = Label("pick"), numQ = Label("num?"), num2 = Label("num2"), num = Label("num"), variant = Label("var")
    // v2 (PUBLISH B2; socialsim/v2.py switches in population.py / names.py): country blocks, block order, quantile jitter,
    // member culture, the uniform tail of the scaled draw, katakana forms
    static let cblk = Label("cblk"), cord = Label("cord"), uj = Label("uj"), mcul = Label("mcul")
    static let tailU = Label("tailU"), kana = Label("kana")
    // Swift-side additions (not in the reference; used only by features the reference does not model)
    static let skyShown = Label("skyShown")

    /// "cand<slot>" / "any<slot>" labels of the matchmaking ('cand%d' % slot in events.py), precomputed for 128 slots.
    static let candTable: [Label] = (0..<128).map { Label("cand\($0)") }
    static let anyTable: [Label] = (0..<128).map { Label("any\($0)") }
    static func cand(_ slot: Int) -> Label { slot < candTable.count ? candTable[slot] : Label("cand\(slot)") }
    static func any(_ slot: Int) -> Label { slot < anyTable.count ? anyTable[slot] : Label("any\(slot)") }
}
