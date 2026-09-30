import Foundation

// SOC1 (SPEC-social §2.2-§2.8, §3.2). Port of design/social/tools/socialsim/population.py, bit for bit.
//
// The world is identical on every device: derived from the model's seed only (the install seed never touches it), so two
// friends comparing phones see the same World / Country boards at the same moment (SPEC-social §0 rule 1).
// Players join in COHORTS = (join period p [a week from the epoch], timezone bucket, archetype[, join day]). Members
// j = 0…n−1 sit at quantiles u_j = (j + v_c)/n; every member parameter is monotone in u (higher u: joins earlier, plays
// more, stays longer), so level(u, t) is non-decreasing in u at every t and each query below is a binary search per
// cohort (O(C log n), never O(players)). Nothing about other players is stored: a player is (cohort, index).

/// One cohort (immutable after creation).
final class SocialCohort: @unchecked Sendable {
    let idx: Int, ck: Int, p: Int, b: Int, a: Int, day: Int
    let n: Int
    let gid0: Int
    /// The cohort's one country and culture (v1; a LOCAL cohort's in v2); nil when its members are split into country
    /// blocks (v2, M1: SocialPopulation.isoOf / cultureOf per member).
    let iso: String?, culture: String?
    let off: Int
    let local: Bool
    /// v2 (M4): XOR-ed into a LOCAL member's name / avatar id (the 16-bit ISO << 44); 0 otherwise.
    let salt: Int
    /// v2 (M1): the cohort's country blocks are SocialPopulation.blk[blockLo ..< blockHi] (empty range: no blocks).
    let blockLo: Int, blockHi: Int
    let v: Double, pace: Double, lamMax: Double
    /// The daily-volume pattern and the lapsed pattern in ONE array (B2, memory: one allocation per cohort instead of
    /// four, and the prefix sums are re-added when needed, in the same order, so they are the same doubles): m =
    /// pat[0 ..< 28], ml = pat[28 ..< 56]; T and Tl are the totals.
    let pat: [Double]
    let T: Double, Tl: Double
    let join0: Double, span: Double
    let R: Double?                                     // returners' comeback time
    /// Per nickname style (SocialPopulation.styleNames order): the member range [lo, hi) of the style and its first slot.
    let styleTab: [Int32]
    let arch: SocialArchInfo
    /// Honeymoon (shipped model): members play (1 + hb) × their volume until hE (capped by each member's T1); session
    /// windows of local days <= hDL are sized for that bigger share. hE = nil for the prototype's archetypes.
    let hb: Double, hE: Double?, hDL: Int

    // ---- exact memo layer (mutated only by the population's single user, see SocialPopulation) ----
    /// For t > frozenAfter every member's progress is a constant: the top member's activity (T1, the lapsed phase, a
    /// returner's second life) has ended, and every lower member's ends earlier (containment). The same arithmetic then
    /// yields the same doubles at every such t, so the memos below are exact.
    // B2 (perf): the memo fields are `@exclusivity(unchecked)` — one caller at a time holds the population (the engine's
    // lock), so the runtime's per-access exclusivity bookkeeping (~12 % of a World query) guards nothing here.
    @exclusivity(unchecked) var frozenAfter: Double = .infinity
    @exclusivity(unchecked) var frozenP: [Int: Double] = [:]              // j → P, for t > frozenAfter
    @exclusivity(unchecked) var frozenBoundary: [Int: Int] = [:]          // x → first j with level >= x, for t > frozenAfter
    @exclusivity(unchecked) var ckW = Int.min                             // 6-hour window of the bounds below
    @exclusivity(unchecked) var ckTopHi = -Double.infinity  // P of member n−1 at the window END (≥ its P anywhere in the window)
    @exclusivity(unchecked) var ckBotLo = -Double.infinity  // P of member 0 at the window START (≤ its P anywhere in the window)
    @exclusivity(unchecked) var ckBracket: [Int: (lo: Int, hi: Int)] = [:] // x → [boundary at the span end, at the span start]
    /// B2: the brackets' SPAN = the part of the 6-hour window inside one local day of the cohort ((window << 1) | the half
    /// after a local midnight), its first and last instant, and whether members' P is exactly monotone over it (no member
    /// lag). Inside one local day P(j, t) is non-decreasing in t EXACTLY (see bracketedBoundary).
    @exclusivity(unchecked) var ckSub = Int.min
    @exclusivity(unchecked) var ckSpanLo = 0.0, ckSpanHi = 0.0
    @exclusivity(unchecked) var ckMono = false
    /// B2: the neighbour bounds of ONE level boundary xb for the window (World neighbours): the fixed boundary b (−1: the
    /// bracket moves in this window) and P of members b and b − 1 at the window's start and end (−∞: not joined).
    @exclusivity(unchecked) var ckNbX = Int.min
    @exclusivity(unchecked) var ckNb: (b: Int, aLo: Double, aHi: Double, bLo: Double, bHi: Double) = (-1, 0, 0, 0, 0)

    static let P = SocialWorldModel.pattern
    /// The daily-volume pattern (tests; the hot paths read `pat`).
    var m: [Double] { Array(pat[0..<Self.P]) }
    /// The lapsed pattern (tests).
    var ml: [Double] { Array(pat[Self.P..<(2 * Self.P)]) }

    init(idx: Int, ck: Int, p: Int, b: Int, a: Int, day: Int, n: Int, gid0: Int, iso: String?, culture: String?, off: Int,
         local: Bool, salt: Int, blockLo: Int, blockHi: Int, v: Double, pace: Double, lamMax: Double, pat: [Double],
         T: Double, Tl: Double, join0: Double, span: Double, R: Double?, styleTab: [Int32], arch: SocialArchInfo,
         hb: Double, hE: Double?, hDL: Int) {
        self.idx = idx; self.ck = ck; self.p = p; self.b = b; self.a = a; self.day = day; self.n = n; self.gid0 = gid0
        self.iso = iso; self.culture = culture; self.off = off; self.local = local; self.salt = salt
        self.blockLo = blockLo; self.blockHi = blockHi; self.v = v; self.pace = pace
        self.lamMax = lamMax; self.pat = pat; self.T = T; self.Tl = Tl
        self.join0 = join0; self.span = span; self.R = R; self.styleTab = styleTab; self.arch = arch
        self.hb = hb; self.hE = hE; self.hDL = hDL
    }
}

/// An archetype's parameters shared by reference (B2, memory: a cohort holds 8 bytes instead of a copy of the struct).
final class SocialArchInfo: @unchecked Sendable {
    let key: String
    let share: Double
    let daily: Bool
    let lamX: [Double], lamY: [Double], lifeX: [Double], lifeY: [Double]
    let rho: Double
    let sessMin: Int, sessMax: Int
    let firstLo: Double, firstHi: Double
    let lapse: (lo: Double, hi: Double)?
    let life2X: [Double]?, life2Y: [Double]?
    let gap: (lo: Double, hi: Double)?
    let custom: Double, avatarDefault: Double, avatarCustom: Double
    let honey: (beta: Double, days: Double)?
    init(_ a: SocialArchetype) {
        key = a.key; share = a.share; daily = a.daily; lamX = a.lamX; lamY = a.lamY; lifeX = a.lifeX; lifeY = a.lifeY; rho = a.rho
        sessMin = a.sessMin; sessMax = a.sessMax; firstLo = a.firstLo; firstHi = a.firstHi; lapse = a.lapse; life2X = a.life2X
        life2Y = a.life2Y; gap = a.gap; custom = a.custom; avatarDefault = a.avatarDefault; avatarCustom = a.avatarCustom
        honey = a.honey
    }
}

/// A member's parameters (member() of the reference).
struct SocialMember {
    let u: Double, lam: Double, J: Double, T1: Double, F: Double, T2: Double?
}

/// A cohort-day's play windows (sessions() of the reference).
struct SocialSessions {
    let starts: [Double], f: [Double], pace: Double, m: Double
}

/// The home country's device-only partition (a country missing from the table).
public struct SocialLocalPartition: Sendable, Equatable {
    public var iso: String, offsetMinutes: Int, culture: String
    public init(iso: String, offsetMinutes: Int, culture: String) {
        self.iso = iso; self.offsetMinutes = offsetMinutes; self.culture = culture
    }
}

/// The simulated world (World of population.py). NOT thread-safe by itself: one caller at a time (SocialEngine holds a
/// lock around every query). The cohort table grows lazily (append-only); the per-cohort memos are exact caches of pure
/// functions (see SocialCohort.frozenAfter), so results never depend on what was asked before.
final class SocialPopulation: @unchecked Sendable {
    let model: SocialWorldModel
    let seed: UInt64
    let local: SocialLocalPartition?
    let names: NameBank

    private(set) var cohorts: [SocialCohort] = []
    /// v2 (M1): every cohort's country blocks, flat: (row index in the cohort's band << 16) | first member; a block ends
    /// where the next one of its cohort starts (or at n). The row 0xFFFF = the LOCAL partition's one block.
    private(set) var blk: [UInt32] = []
    /// v2: the per-country unit index of the country queries, built lazily for the countries asked about.
    private var isoIndex: [String: IsoIndex] = [:]
    private var periods = 0                               // complete join periods materialised
    private var styleCount: [String: Int] = [:]           // "style|culture" -> next free slot (shared world)
    private var localStyleCount: [String: Int] = [:]
    private var nextGid = 0
    private var nextLocalGid = 1 << 40
    private var periodEndGid: [Int] = []                  // shared-world gid count after each period
    private var nameCache: [Int: (name: String, style: String)] = [:]
    private var topOrder: [String: (window: Int, count: Int, order: [SocialCohort], ub: [Double])] = [:]
    // frozen cohorts sorted by the moment they freeze, and exact running counts of their players at level >= x
    private var frozenOrder: [SocialCohort] = []
    private var frozenAfterSorted: [Double] = []
    private var frozenOrderCount = -1
    private var frozenPrefix: [String: [Int]] = [:]
    /// Per (x, filter): the K best first candidates (above: smallest (P, gid); below: largest (P, −gid)) of the cohorts
    /// frozen so far along the freeze order, and how many of them were scanned.
    private var frozenNeighbourTop: [String: (m: Int, above: [Ref], below: [Ref])] = [:]
    static let neighbourK = 64
    static let window = 21_600                             // 6 h checkpoints of the exact pruning bounds
    static let pad = 1e-6                                  // float-rounding pad on the bounds (P's error is ~1e-10)

    // derived constants
    let weeklyArch: [Int], dailyArch: [Int], idxReturner: Int
    let buckets: [String]
    let bucketRows: [[SocialCountryRow]]
    let bucketShare: [Double]
    /// The world's epoch (join period 0; M8) and the v2 mechanisms (nil = a v1 model).
    let epoch: Int
    let intl: SocialIntl?
    let blocksOn: Bool, jitterOn: Bool, lagMin: Double
    /// v2 (M11): per band, per archetype, the rows' apportionment weights (weight × tilt) and their sum.
    private var tiltedWeights: [[[Double]]] = []
    private var tiltedTotal: [[Double]] = []
    /// The archetypes by reference and the nickname styles in a cohort's styleTab order ("default", then the mix's).
    let archInfos: [SocialArchInfo]
    let styleNames: [String]
    /// B2 (memory): the cohort-day session windows live in ONE direct-mapped cache instead of 16 slots in every cohort
    /// (~2 KB each, most of it dead once a cohort froze): 2 rows per cohort rounded up to a power of two, 4 096 … 65 536
    /// rows (0.5 … 8 MB), re-sized as the world grows. A row is 16 doubles (one 128-byte block): the key's bits (cohort idx
    /// << 32 | the local day), the session count (−1 = a rest day), pace, m, starts[6], f[6]. A miss recomputes the same
    /// windows (computeSessions is a pure function), so hits and misses give the same bits.
    static let sessStride = 16, sessMax = 6
    private var sessRows: UnsafeMutablePointer<Double>?
    private var sessN = 0, sessShift: UInt64 = 64, sessWanted = 4096

    init(model: SocialWorldModel, local: SocialLocalPartition? = nil, names: NameBank) {
        self.model = model
        self.seed = model.seed
        self.local = local
        self.names = names
        epoch = model.epoch
        intl = model.intl
        blocksOn = model.intl?.countryBlocks ?? false
        jitterOn = model.intl?.jitter ?? false
        lagMin = model.intl?.lagMinutes ?? 0.0
        archInfos = model.archetypes.map(SocialArchInfo.init)
        styleNames = ["default"] + model.nameStyle.weights.map(\.style)
        weeklyArch = model.archetypes.indices.filter { !model.archetypes[$0].daily }
        dailyArch = model.archetypes.indices.filter { model.archetypes[$0].daily }
        idxReturner = model.archetypes.firstIndex(where: { $0.key == "returner" }) ?? -1
        buckets = model.bucketNames
        var rows: [[SocialCountryRow]] = buckets.map { _ in [] }
        for r in model.countries {
            if let b = buckets.firstIndex(of: r.bucket) { rows[b].append(r) }
        }
        bucketRows = rows
        var total = 0.0
        for r in model.countries { total += r.weight }
        bucketShare = rows.map { rs in
            var s = 0.0
            for r in rs { s += r.weight }
            return s / total
        }
        if let intl {
            precondition(intl.bucketOffsets.count == buckets.count, "one schedule offset per band")
            // population._blocks: wts = [r.weight * ROW_TILT[r.iso].get(akey, 1.0) if r.iso in ROW_TILT else r.weight]
            tiltedWeights = rows.map { rs in
                model.archetypes.map { a in rs.map { r in intl.rowTilt[r.iso].map { r.weight * ($0[a.key] ?? 1.0) } ?? r.weight } }
            }
            tiltedTotal = tiltedWeights.map { perArch in perArch.map { ws in var t = 0.0; for w in ws { t += w }; return t } }
        }
    }

    deinit { sessRows?.deallocate() }

    /// The cache's size for the current table: 2 rows per cohort, a power of two in 4 096 … 65 536 (set by extend).
    private func resizeSessionCache() {
        var n = 4096
        while n < 2 * cohorts.count && n < 65_536 { n <<= 1 }
        sessWanted = n
    }

    // ------------------------------------------------------------- building

    /// Every cohort whose join period started by t exists afterwards.
    func extend(to t: Double) {
        let pmax = SocialHash.floorDiv(Int(t) - epoch, SocialCalendar.week)
        while periods <= pmax {
            addPeriod(periods)
            periods += 1
            periodEndGid.append(nextGid)
        }
        resizeSessionCache()
    }

    var periodCount: Int { periods }
    var sharedPlayerCount: Int { nextGid }

    private func addPeriod(_ p: Int) {
        let j = SocialWorldModel.weeklyJoins(p)
        var parts = Array(buckets.indices)
        if local != nil { parts.append(buckets.count) }     // LOCAL partition, after the shared buckets
        for b in parts {
            // the LOCAL partition adds 0.3 % ON TOP of the shared world, so the shared buckets stay byte-identical
            let share = b < buckets.count ? bucketShare[b] : SocialWorldModel.localShare
            for a in weeklyArch {
                let E = j * share * model.archetypes[a].share
                if let targets = intl?.shardTarget {
                    // M9: a weekly cohort of E expected players = ns independent shards (key ck + (k << 24))
                    let key = model.archetypes[a].key
                    var ns = 1
                    if let T = targets[key], T != 0 { ns = max(1, SocialHash.floorInt(E / T + 0.5)) }
                    if let mins = intl?.minShards { ns = max(ns, mins[key] ?? 1) }
                    for k in 0..<ns { addCohort(p, b, a, -1, E / Double(ns), shard: k) }
                } else {
                    addCohort(p, b, a, -1, E)
                }
            }
            for day in 0..<7 {
                for a in dailyArch { addCohort(p, b, a, day, j * share * model.archetypes[a].share / 7.0) }
            }
        }
    }

    /// population.iso16: a 2-letter region code as a 16-bit integer (the LOCAL salt, M4).
    static func iso16(_ iso: String) -> Int {
        let u = Array(iso.unicodeScalars)
        return (Int(u[0].value) << 8) | Int(u[1].value)
    }

    static func cohortKey(_ p: Int, _ b: Int, _ a: Int, _ day: Int) -> Int { ((p * 16 + b) * 16 + a) * 8 + (day + 1) }

    private func addCohort(_ p: Int, _ b: Int, _ a: Int, _ day: Int, _ expected: Double, shard: Int = 0) {
        typealias H = SocialHash
        typealias L = SocialLabels
        let S = seed
        let idx = cohorts.count
        var ck = Self.cohortKey(p, b, a, day) + (shard << 24)
        let isLocal = b >= buckets.count
        var salt = 0
        if isLocal, intl?.localByISO == true, let lp = local {
            let h = Self.iso16(lp.iso)
            ck ^= h << 32                     // M4: every LOCAL hash (size, pace, pattern, sessions, styles) keyed by the ISO
            salt = h << 44                    // ... and the member name / avatar ids (never the gid: fallbacks stay disjoint)
        }
        let n = H.floorInt(expected + H.u01(S, L.cn, ck))
        var iso: String?, off: Int, culture: String?
        let blockLo = blk.count
        if isLocal, let lp = local {
            iso = lp.iso; off = lp.offsetMinutes; culture = lp.culture
            if blocksOn && n > 0 { blk.append(0xFFFF << 16) }            // M1: the LOCAL cohort is one block
        } else if blocksOn, let intl {
            // M1 + M3: the members are split over every row of the band; the cohort plays on the band's schedule offset
            iso = nil; culture = nil
            off = intl.bucketOffsets[b]
            appendBlocks(ck: ck, n: n, a: a, b: b)
        } else {
            let rows = bucketRows[b]
            var tot = 0.0
            for r in rows { tot += r.weight }
            let x = H.u01(S, L.ccountry, ck) * tot
            var acc = 0.0
            var pick = rows[rows.count - 1]
            for r in rows {
                acc += r.weight
                if x < acc { pick = r; break }
            }
            iso = pick.iso; off = pick.offsetMinutes; culture = pick.culture
        }
        let blockHi = blk.count
        let v = H.u01(S, L.cv, ck)
        let (plo, phi) = SocialWorldModel.paceRange
        let pace = plo + (phi - plo) * H.u01(S, L.pace, ck)
        let arch = model.archetypes[a]
        let lamMax = H.interp(1.0, arch.lamX, arch.lamY)
        // daily-volume pattern (28 days, weekday-aligned), mean over played days = 1
        let P = SocialWorldModel.pattern
        let (vlo, vhi) = SocialWorldModel.volumeRange
        var raw = [Double](repeating: 0, count: P)
        var played = [Bool](repeating: false, count: P)
        for i in 0..<P {
            let pl = H.u01(S, L.play, ck, i) < arch.rho
            let vv = vlo + (vhi - vlo) * H.u01(S, L.vol, ck, i)
            let w = SocialWorldModel.weekdayVolume[H.posMod(i + 3, 7)]
            raw[i] = pl ? vv * w : 0.0
            played[i] = pl
        }
        if !played.contains(true) {
            // max by (u01, −i): the largest draw, ties to the smallest i
            var best = 0
            var bestU = H.u01(S, L.play, ck, 0)
            for i in 1..<P {
                let u = H.u01(S, L.play, ck, i)
                if u > bestU { bestU = u; best = i }
            }
            raw[best] = (vlo + (vhi - vlo) * H.u01(S, L.vol, ck, best)) * SocialWorldModel.weekdayVolume[H.posMod(best + 3, 7)]
            played[best] = true
        }
        var s = 0.0
        var k = 0
        for i in 0..<P where played[i] { s += raw[i]; k += 1 }
        let mean = s / Double(k)
        let m = raw.map { $0 / mean }
        var pre = [0.0]
        for x in m { pre.append(pre[pre.count - 1] + x) }
        let T = pre[P]
        // lapsed pattern: after quitting, a member still opens the game on some play days, at half volume
        var ml = [Double](repeating: 0, count: P)
        for i in 0..<P {
            let on = m[i] > 0.0 && H.u01(S, L.lapse, ck, i) < SocialWorldModel.lapseDayP
            ml[i] = on ? SocialWorldModel.lapseVolume * m[i] : 0.0
        }
        var prel = [0.0]
        for x in ml { prel.append(prel[prel.count - 1] + x) }
        let Tl = prel[P]
        // join window
        let start = epoch + p * SocialCalendar.week + (day >= 0 ? day * SocialCalendar.day : 0)
        let span = Double(day >= 0 ? SocialCalendar.day : SocialCalendar.week)
        let join0 = Double(start) + span
        // honeymoon (population.py 'honey'): one end per cohort = the END of its join window + days
        var hb = 0.0, hE: Double? = nil, hDL = Int.min
        if let h = arch.honey {
            hb = h.beta
            let e = join0 + h.days * Double(SocialCalendar.day)
            hE = e
            hDL = SocialCalendar.localDayMinute(e, offsetMinutes: off).day - SocialWorldModel.baseDay
        }
        var R: Double? = nil
        if a == idxReturner, let g = arch.gap {
            let gap = g.lo + (g.hi - g.lo) * H.u01(S, L.gap, ck)
            R = Double(epoch + (p + 1) * SocialCalendar.week) + (33.0 + gap) * Double(SocialCalendar.day)
        }
        // nickname styles: exact per-cohort counts, dense slots per (style, culture)
        var custom = H.floorInt(Double(n) * arch.custom + H.u01(S, L.ncustom, ck))
        custom = min(custom, n)
        var counts: [Int] = []
        let weights = model.nameStyle.weights
        if model.nameStyle.systematic {
            // shipped (SOC1c): systematic apportionment over the cumulative weights (population.py STYLE_SYSTEMATIC)
            let us = H.u01(S, L.nsys, ck)
            var prev = 0, cw = 0.0
            for (si, sw) in weights.enumerated() {
                cw += sw.weight
                let cur = si == weights.count - 1 ? custom : min(custom, H.floorInt(Double(custom) * cw + us))
                counts.append(cur - prev)
                prev = cur
            }
        } else {
            var rem = custom
            for (si, sw) in weights.enumerated() {
                let k2: Int
                if si == weights.count - 1 {
                    k2 = rem
                } else {
                    k2 = min(rem, H.floorInt(Double(custom) * sw.weight + H.u01(S, L.nstyle, ck, si)))
                }
                counts.append(k2)
                rem -= k2
            }
        }
        var order: [(String, Int)] = [("default", n - custom)]
        for (si, sw) in weights.enumerated() { order.append((sw.style, counts[si])) }
        var styleTab: [Int32] = []
        styleTab.reserveCapacity(order.count * 3)
        var accN = 0
        for (st, k2) in order {
            // (style, culture) slot counters; a block cohort has no one culture: population.py keys it (st, None)
            let cul = SocialNames.cultureStyles.contains(st) ? (culture ?? "\u{0}none") : "*"
            let keyc = st + "|" + cul
            let base = (isLocal ? localStyleCount[keyc] : styleCount[keyc]) ?? 0
            precondition(base + k2 < Int(Int32.max), "a style's slots fit the compact table")
            styleTab += [Int32(accN), Int32(accN + k2), Int32(base)]
            if isLocal { localStyleCount[keyc] = base + k2 } else { styleCount[keyc] = base + k2 }
            accN += k2
        }
        let gid0: Int
        if isLocal { gid0 = nextLocalGid; nextLocalGid += n } else { gid0 = nextGid; nextGid += n }
        let c = SocialCohort(idx: idx, ck: ck, p: p, b: b, a: a, day: day, n: n, gid0: gid0, iso: iso, culture: culture,
                             off: off, local: isLocal, salt: salt, blockLo: blockLo, blockHi: blockHi, v: v, pace: pace,
                             lamMax: lamMax, pat: m + ml, T: T, Tl: Tl, join0: join0, span: span, R: R,
                             styleTab: styleTab, arch: archInfos[a], hb: hb, hE: hE, hDL: hDL)
        if n > 0 {
            let top = member(c, n - 1)
            var end = max(top.T1, lapseEnd(c, top.u, top.T1))
            if let T2 = top.T2 { end = max(end, T2) }
            // M10: a member's clock trails its cohort's by at most lagMin minutes, so its activity ends that much later
            c.frozenAfter = end + lagMin * 60.0
        }
        cohorts.append(c)
    }

    /// population._blocks (M1): contiguous member blocks, one per row of the band per stratum — systematic apportionment of
    /// the (M11-tilted) row weights with one offset u per stratum, the rows in a per-stratum hashed order — appended to `blk`
    /// for the non-empty blocks, in member order.
    private func appendBlocks(ck: Int, n: Int, a: Int, b: Int) {
        typealias H = SocialHash
        typealias L = SocialLabels
        guard n > 0, let intl else { return }
        precondition(n < 1 << 16, "a cohort's member index fits the block encoding")
        let S = seed
        let wts = tiltedWeights[b][a]
        let tot = tiltedTotal[b][a]
        let strata = intl.strata
        let R = wts.count
        var keyed = [(h: UInt64, i: Int)](repeating: (0, 0), count: R)
        for k in 0..<strata {
            let z0 = (k * n) / strata, z1 = ((k + 1) * n) / strata
            let m = z1 - z0
            if m <= 0 { continue }
            let u: Double
            if strata == 1 {
                for i in 0..<R { keyed[i] = (H.h64(S, L.cord, ck, i), i) }
                u = H.u01(S, L.cblk, ck)
            } else {
                for i in 0..<R { keyed[i] = (H.h64(S, L.cord, ck, k, i), i) }
                u = H.u01(S, L.cblk, ck, k)
            }
            keyed.sort { $0.h != $1.h ? $0.h < $1.h : $0.i < $1.i }       // sorted(key=(h64(...), i))
            var cw = 0.0
            var prev = 0
            for q in 0..<R {
                let i = keyed[q].i
                cw += wts[i]
                let cur = q == R - 1 ? m : min(m, H.floorInt(Double(m) * (cw / tot) + u))
                if cur > prev { blk.append(UInt32(i) << 16 | UInt32(z0 + prev)) }
                prev = cur
            }
        }
    }

    // ------------------------------------------------------------- member parameters (all monotone in u)

    /// population.u_of: (j + v) / n, or with the stratified jitter (M2) (j + u01('uj', ck, j)) / n.
    @inline(__always) func u(_ c: SocialCohort, _ j: Int) -> Double {
        jitterOn ? (Double(j) + SocialHash.u01(seed, SocialLabels.uj, c.ck, j)) / Double(c.n) : (Double(j) + c.v) / Double(c.n)
    }

    @inline(__always)
    func member(_ c: SocialCohort, _ j: Int) -> SocialMember {
        let a = c.arch
        let u = self.u(c, j)
        let lam = SocialHash.interp(u, a.lamX, a.lamY)
        let J = c.join0 - u * c.span
        let life = SocialHash.interp(u, a.lifeX, a.lifeY)
        let T1 = J + life * Double(SocialCalendar.day)
        let F = a.firstLo + (a.firstHi - a.firstLo) * u
        var T2: Double? = nil
        if let R = c.R, let x2 = a.life2X, let y2 = a.life2Y {
            T2 = R + SocialHash.interp(u, x2, y2) * Double(SocialCalendar.day)
        }
        return SocialMember(u: u, lam: lam, J: J, T1: T1, F: F, T2: T2)
    }

    @inline(__always)
    func lapseEnd(_ c: SocialCohort, _ u: Double, _ T1: Double) -> Double {
        guard let l = c.arch.lapse else { return T1 }
        var le = T1 + (l.lo + (l.hi - l.lo) * u) * Double(SocialCalendar.day)
        if let R = c.R, le > R { le = R }             // a returner's lapse phase ends when its comeback starts
        return le
    }

    // ------------------------------------------------------------- activity

    /// pre[k] (from = 0) or prel[k] (from = 28): the pattern's first k values added up from 0.0 in order — population.py
    /// builds its prefix list the same way (pre = [0.0]; pre.append(pre[-1] + x)), so these are the same doubles.
    @inline(__always)
    func prefix(_ c: SocialCohort, _ from: Int, _ k: Int) -> Double {
        c.pat.withUnsafeBufferPointer { p in
            var s = 0.0
            for i in from..<(from + k) { s = s + p[i] }
            return s
        }
    }

    /// Cumulative daily volume of the cohort before local day dl (days since BASE_DAY).
    @inline(__always)
    func C(_ c: SocialCohort, _ dl: Int) -> Double {
        Double(SocialHash.floorDiv(dl, SocialWorldModel.pattern)) * c.T + prefix(c, 0, SocialHash.posMod(dl, SocialWorldModel.pattern))
    }

    /// The cache row holding cohort c's session windows on local day dl (computed and stored on a miss); nil on a rest day.
    @inline(__always)
    func sessionRow(_ c: SocialCohort, _ dl: Int) -> UnsafeMutablePointer<Double>? {
        if sessN != sessWanted {
            sessRows?.deallocate()
            let N = sessWanted
            sessN = N
            sessShift = UInt64(64 - N.trailingZeroBitCount)
            sessRows = .allocate(capacity: N * Self.sessStride)
            sessRows!.initialize(repeating: 0, count: N * Self.sessStride)
            for k in 0..<N { sessRows![k * Self.sessStride] = Double(bitPattern: UInt64.max) }      // an impossible key
        }
        let key = UInt64(truncatingIfNeeded: c.idx) << 32 | UInt64(UInt32(truncatingIfNeeded: dl))
        let k = Int(truncatingIfNeeded: (key &* 0x9E37_79B9_7F4A_7C15) >> sessShift)          // multiplicative hashing
        let row = sessRows! + k * Self.sessStride
        if row[0].bitPattern == key { return row[1] < 0 ? nil : row }
        row[0] = Double(bitPattern: key)
        guard let s = computeSessions(c, dl) else { row[1] = -1; return nil }
        precondition(s.starts.count <= Self.sessMax, "at most 6 sessions a day (the archetypes' sess ranges)")
        row[1] = Double(s.starts.count)
        row[2] = s.pace
        row[3] = s.m
        for j in 0..<s.starts.count { row[4 + j] = s.starts[j]; row[10 + j] = s.f[j] }
        return row
    }

    func computeSessions(_ c: SocialCohort, _ dl: Int) -> SocialSessions? {
        typealias H = SocialHash
        typealias L = SocialLabels
        let S = seed
        let m = c.pat[H.posMod(dl, SocialWorldModel.pattern)]
        if m <= 0.0 { return nil }
        let a = c.arch
        let k = a.sessMin + H.below(S, L.sk, a.sessMax - a.sessMin + 1, c.ck, dl)
        let weekend = H.posMod(dl + SocialWorldModel.baseDay + 3, 7) >= 5
        let cdf = SocialWorldModel.diurnalCDF[weekend ? 1 : 0]
        var starts: [Double] = []
        starts.reserveCapacity(k)
        for j in 0..<k {
            let x = H.u01(S, L.ss, c.ck, dl, j)
            var h = 0
            while h < 23 && cdf[h + 1] <= x { h += 1 }
            let frac = (x - cdf[h]) / (cdf[h + 1] - cdf[h])
            starts.append((Double(h) + frac) * 60.0)
        }
        starts.sort()
        var ws: [Double] = []
        for j in 0..<k { ws.append(0.5 + H.u01(S, L.sf, c.ck, dl, j)) }
        var tot = 0.0
        for w in ws { tot += w }
        let f = ws.map { $0 / tot }
        var Q = c.lamMax * m
        if c.hE != nil && dl <= c.hDL { Q = c.lamMax * (1.0 + c.hb) * m }   // honeymoon days: windows for the bigger share
        var pace = c.pace
        let need = Q / pace
        if need > SocialWorldModel.dayBudget { pace = Q / SocialWorldModel.dayBudget }
        let Lw = f.map { $0 * Q / pace }
        if k > 1 {
            for j in 1..<k {
                let lo = starts[j - 1] + Lw[j - 1] + SocialWorldModel.sessionGap
                if starts[j] < lo { starts[j] = lo }
            }
        }
        var limit = SocialWorldModel.minutes - 1.0
        for j in stride(from: k - 1, through: 0, by: -1) {
            if starts[j] > limit - Lw[j] { starts[j] = limit - Lw[j] }
            limit = starts[j] - SocialWorldModel.sessionGap
        }
        return SocialSessions(starts: starts, f: f, pace: pace, m: m)
    }

    /// Levels a member with rate lam has accumulated by time t along the cohort clock (absolute, not since join).
    /// lapsed = the lapsed pattern (sparse days, half volume) with the same session windows.
    @inline(__always)
    func lcum(_ c: SocialCohort, _ lam: Double, _ t: Double, lapsed: Bool = false) -> Double {
        let (dlabs, minute) = SocialCalendar.localDayMinute(t, offsetMinutes: c.off)
        let dl = dlabs - SocialWorldModel.baseDay
        let k = SocialHash.posMod(dl, SocialWorldModel.pattern)
        var base: Double
        var ml = 0.0
        if lapsed {
            let P = SocialWorldModel.pattern
            base = lam * (Double(SocialHash.floorDiv(dl, P)) * c.Tl + prefix(c, P, k))
            ml = c.pat[P + k]
        } else {
            base = lam * C(c, dl)
        }
        if !lapsed || ml > 0.0 {
            if let row = sessionRow(c, dl) {
                // (the same arithmetic as over SocialSessions: q = λ·m, then Σ min(pace·d, f_j·q) in session order)
                let n = Int(row[1])
                let pace = row[2]
                let q = lam * (lapsed ? ml : row[3])
                var g = 0.0
                for j in 0..<n {
                    let d = minute - row[4 + j]
                    if d > 0.0 {
                        let a = pace * d
                        let b = row[10 + j] * q
                        g += a < b ? a : b
                    }
                }
                base += g
            }
        }
        return base
    }

    /// Continuous progress P (level = 1 + floor(P)); nil if the member has not joined yet at t.
    func progress(_ c: SocialCohort, _ j: Int, _ t: Double) -> Double? {
        if t > c.frozenAfter {
            if let P = c.frozenP[j] { return P }
            let P = rawProgress(c, j, t)
            if c.frozenP.count >= 512 { c.frozenP.removeAll(keepingCapacity: true) }
            c.frozenP[j] = P
            return P
        }
        return rawProgress(c, j, t)
    }

    /// progress() of the reference, evaluated.
    func rawProgress(_ c: SocialCohort, _ j: Int, _ t0: Double) -> Double? {
        let mb = member(c, j)
        var t = t0
        if lagMin != 0 { t = t - lagMin * 60.0 * (1.0 - mb.u) }      // M10: the member's own (delayed) clock
        if t < mb.J { return nil }
        let tA = t < mb.T1 ? t : mb.T1
        var first = SocialWorldModel.firstPace * ((tA - mb.J) / 60.0)
        if first > mb.F { first = mb.F }
        var P: Double
        if let hE = c.hE {
            // honeymoon: (1 + hb)·λ until E1 = min(hE, T1), then λ (population.py progress)
            let lh = mb.lam * (1.0 + c.hb)
            let E1 = hE < mb.T1 ? hE : mb.T1
            let tH = tA < E1 ? tA : E1
            P = first + (lcum(c, lh, tH) - lcum(c, lh, mb.J))
            if tA > E1 { P += lcum(c, mb.lam, tA) - lcum(c, mb.lam, E1) }
        } else {
            P = first + (lcum(c, mb.lam, tA) - lcum(c, mb.lam, mb.J))
        }
        if t > mb.T1 {
            let LE = lapseEnd(c, mb.u, mb.T1)
            if LE > mb.T1 {
                let tL = t < LE ? t : LE
                P += lcum(c, mb.lam, tL, lapsed: true) - lcum(c, mb.lam, mb.T1, lapsed: true)
            }
        }
        if let T2 = mb.T2, let R = c.R, t > R {
            let tB = t < T2 ? t : T2
            P += lcum(c, mb.lam, tB) - lcum(c, mb.lam, R)
        }
        return P
    }

    /// population.lag (M10): seconds member j trails its cohort's clock (0 when the switch is off).
    @inline(__always) func lag(_ c: SocialCohort, _ j: Int) -> Double {
        lagMin == 0 ? 0.0 : lagMin * 60.0 * (1.0 - u(c, j))
    }

    @inline(__always)
    func level(_ c: SocialCohort, _ j: Int, _ t: Double) -> Int {
        guard let P = progress(c, j, t) else { return 0 }
        return 1 + SocialHash.floorInt(P)
    }

    // ------------------------------------------------------------- identity

    @inline(__always) func gid(_ c: SocialCohort, _ j: Int) -> Int { c.gid0 + j }

    /// population.ident: the id that keys a member's drawn nickname and avatar (a v2 LOCAL member's is salted, M4).
    @inline(__always) func ident(_ c: SocialCohort, _ j: Int) -> Int { (c.gid0 + j) ^ c.salt }

    /// population.block_of (M1): (row index in the band, first member, end) of member j — the last block starting at or
    /// before j (the blocks tile [0, n) in order).
    func blockOf(_ c: SocialCohort, _ j: Int) -> (row: Int, s: Int, e: Int) {
        var lo = c.blockLo, hi = c.blockHi - 1
        while lo < hi {
            let mid = (lo + hi + 1) / 2
            if Int(blk[mid] & 0xFFFF) <= j { lo = mid } else { hi = mid - 1 }
        }
        let s = Int(blk[lo] & 0xFFFF)
        let e = lo + 1 < c.blockHi ? Int(blk[lo + 1] & 0xFFFF) : c.n
        return (Int(blk[lo] >> 16), s, e)
    }

    /// The member's country (population.iso_of): its block's row (v2), else the cohort's.
    func isoOf(_ c: SocialCohort, _ j: Int) -> String {
        if let iso = c.iso { return iso }
        return bucketRows[c.b][blockOf(c, j).row].iso
    }

    /// The member's name culture (population.culture_of): the cohort's (v1, LOCAL), its block row's first culture, or a
    /// draw from the row's culture mix by the member's id (M5, label 'mcul').
    func cultureOf(_ c: SocialCohort, _ j: Int) -> String {
        if let cu = c.culture { return cu }
        let row = bucketRows[c.b][blockOf(c, j).row]
        guard intl?.memberCulture == true, let mix = row.mix, mix.count > 1 else { return row.culture }
        var tot = 0.0
        for x in mix { tot += x.weight }
        let x = SocialHash.u01(seed, SocialLabels.mcul, gid(c, j)) * tot
        var acc = 0.0
        for m in mix {
            acc += m.weight
            if x < acc { return m.culture }
        }
        return mix[mix.count - 1].culture
    }

    func styleOf(_ c: SocialCohort, _ j: Int) -> (style: String, slot: Int) {
        let q = SocialHash.perm(j, c.n, SocialHash.h64(seed, SocialLabels.style, c.ck))
        let tab = c.styleTab
        for si in 0..<(tab.count / 3) where Int(tab[3 * si]) <= q && q < Int(tab[3 * si + 1]) {
            return (styleNames[si], Int(tab[3 * si + 2]) + (q - Int(tab[3 * si])))
        }
        return ("default", q)      // unreachable: the ranges cover [0, n)
    }

    /// The cohort's style ranges and first slots in the reference's shape (tests: population.py style_cum / style_base).
    func styleCum(_ c: SocialCohort) -> [(style: String, lo: Int, hi: Int)] {
        (0..<(c.styleTab.count / 3)).map { (styleNames[$0], Int(c.styleTab[3 * $0]), Int(c.styleTab[3 * $0 + 1])) }
    }
    func styleBase(_ c: SocialCohort) -> [Int] { (0..<(c.styleTab.count / 3)).map { Int(c.styleTab[3 * $0 + 2]) } }

    /// Nickname of member j and its style ("fallback" when the blocklist or the length cap replaced it). The reference
    /// hands out unique first-come slots; the shipped world draws custom names by the gid (duplicates allowed, SOC1c).
    /// All 'player_xxxxxxx' names come
    /// from ONE bijection of [0, 36^7) with disjoint slot ranges: shared default slots count up from 0, LOCAL ones from
    /// 36^7/2, the user's own from 36^7/4, blocklist fallbacks DOWN from 36^7 − 1 (8 re-salts per player).
    func name(_ c: SocialCohort, _ j: Int) -> (name: String, style: String) {
        let g = gid(c, j)
        if let hit = nameCache[g] { return hit }
        let r = rawName(c, j)
        if nameCache.count >= 50_000 { nameCache.removeAll(keepingCapacity: true) }
        nameCache[g] = r
        return r
    }

    func rawName(_ c: SocialCohort, _ j: Int) -> (name: String, style: String) {
        var (st, slot) = styleOf(c, j)
        var nm: String
        if st == "default" {
            nm = SocialNames.defaultName(slot + (c.local ? SocialNames.localDefaultBase : 0))
        } else if let draw = model.nameStyle.draw {
            // shipped (SOC1c): drawn with replacement by the gid — names may repeat; identity is the gid, never the name
            guard let d = SocialNames.drawn(st, cultureOf(c, j), key: SocialHash.h64(seed, SocialLabels.nick, ident(c, j)), bank: names,
                                            variants: model.nameStyle.variants, draw: draw, nativeT: model.nameStyle.nativeT,
                                            kanaP: model.nameStyle.kanaP) else {
                return (SocialNames.defaultName(SocialNames.d36_7 - 1 - fallbackIndex(c, j, 7)), "fallback")
            }
            nm = d
        } else if let d = SocialNames.decode(st, slot + (c.local ? SocialNames.localCustomBase : 0), cultureOf(c, j), bank: names,
                                             variants: model.nameStyle.variants, nativeT: model.nameStyle.nativeT,
                                             kanaP: model.nameStyle.kanaP) {
            nm = d
        } else {
            // empty name bank (tests/previews only): a unique fallback-range default name
            return (SocialNames.defaultName(SocialNames.d36_7 - 1 - fallbackIndex(c, j, 7)), "fallback")
        }
        var k = 0
        let cap = model.maxNameLength ?? Int.max
        while nm.unicodeScalars.count > cap || SocialNames.isBlocked(nm, bank: names) || hasExtraStem(nm) {
            nm = SocialNames.defaultName(SocialNames.d36_7 - 1 - fallbackIndex(c, j, k))
            st = "fallback"
            k += 1
        }
        return (nm, st)
    }

    func hasExtraStem(_ nm: String) -> Bool {
        if model.extraBlockedStems.isEmpty { return false }
        let k = SocialNames.key(nm)
        return model.extraBlockedStems.contains { $0.matches(k) }     // FIX-3 B: hashed stems (was k.contains(stem))
    }

    @inline(__always)
    func fallbackIndex(_ c: SocialCohort, _ j: Int, _ k: Int) -> Int {
        let g = gid(c, j)
        return c.local ? (g - (1 << 40)) * 8 + k + (1 << 31) : g * 8 + k
    }

    func avatar(_ c: SocialCohort, _ j: Int, style: String) -> Int {
        let p = (style == "default" || style == "fallback") ? c.arch.avatarDefault : c.arch.avatarCustom
        let g = ident(c, j)
        if SocialHash.u01(seed, SocialLabels.avatarQ, g) >= p { return 0 }
        return 1 + SocialHash.below(seed, SocialLabels.avatar, model.avatarCount, g)
    }

    // ------------------------------------------------------------- queries (O(C log n))

    func candidates(_ iso: String?) -> [SocialCohort] {
        cohorts.filter { $0.n > 0 && (iso == nil || $0.iso == iso) }
    }

    /// The window bounds of an ACTIVE cohort at t: progress is non-decreasing in t, so inside the 6-hour window
    /// [tLo, tHi) member n−1's P is at most P(tHi) and member 0's at least P(tLo) (up to float noise: `pad`).
    @inline(__always)
    func windowBounds(_ c: SocialCohort, _ t: Double) {
        let w = SocialHash.floorDiv(Int(t.rounded(.down)), Self.window)
        let tLo = w * Self.window, tHi = tLo + Self.window
        if c.ckW != w {
            c.ckW = w
            c.ckTopHi = rawProgress(c, c.n - 1, Double(tHi)) ?? -Double.infinity
            c.ckBotLo = rawProgress(c, 0, Double(tLo)) ?? -Double.infinity
        }
        // B2: the span of the brackets = the window's part inside t's local day (a 6-hour window holds at most one local
        // midnight: m, the first local day start after tLo). Before m the span ends one second before it (queries are at
        // whole seconds; a later t falls back to the full search), from m on it runs to the window's end.
        let m = (SocialHash.floorDiv(tLo + c.off * 60, SocialCalendar.day) + 1) * SocialCalendar.day - c.off * 60
        let after = m <= tHi && t >= Double(m)
        let sub = w << 1 | (after ? 1 : 0)
        if c.ckSub == sub { return }
        c.ckSub = sub
        c.ckBracket.removeAll(keepingCapacity: true)
        c.ckNbX = Int.min
        if m > tHi { c.ckSpanLo = Double(tLo); c.ckSpanHi = Double(tHi) }
        else if after { c.ckSpanLo = Double(m); c.ckSpanHi = Double(tHi) }
        else { c.ckSpanLo = Double(tLo); c.ckSpanHi = Double(m - 1) }
        c.ckMono = lagMin == 0
    }

    /// Smallest j with level >= x (c.n if none).
    func boundary(_ c: SocialCohort, _ x: Int, _ t: Double) -> Int {
        if x <= 1 && t >= c.join0 { return 0 }          // everyone has joined (level >= 1)
        if t <= c.frozenAfter {
            windowBounds(c, t)
            if c.ckTopHi == -.infinity || 1 + SocialHash.floorInt(c.ckTopHi + Self.pad) < x { return c.n }
            if c.ckBotLo != -.infinity && 1 + SocialHash.floorInt(c.ckBotLo - Self.pad) >= x { return 0 }
            return bracketedBoundary(c, x, t)
        }
        if t > c.frozenAfter {
            if let b = c.frozenBoundary[x] { return b }
            let b = rawBoundary(c, x, t)
            if c.frozenBoundary.count >= 64 { c.frozenBoundary.removeAll(keepingCapacity: true) }
            c.frozenBoundary[x] = b
            return b
        }
        return rawBoundary(c, x, t)
    }

    /// boundary() of an active cohort inside its window: levels only rise with time, so the boundary at t lies between
    /// its values at the window's end and start (memoised per x); the narrow search is VERIFIED at its edges and falls
    /// back to the full search if float noise ever broke the bracket — the result is always rawBoundary's.
    /// The boundaries of level x at the end and the start of the cohort's current window (memoised per x).
    @inline(__always)
    func bracket(_ c: SocialCohort, _ x: Int) -> (lo: Int, hi: Int) {
        if let hit = c.ckBracket[x] { return hit }
        let br = (lo: rawBoundary(c, x, c.ckSpanHi), hi: rawBoundary(c, x, c.ckSpanLo))
        if c.ckBracket.count >= 16 { c.ckBracket.removeAll(keepingCapacity: true) }
        c.ckBracket[x] = br
        return br
    }

    /// B2 (World neighbours): for a cohort whose boundary of level xb is FIXED over a monotone window (the bracket did not
    /// move, see bracketedBoundary), that boundary b and exact bounds of its two candidates over the window: members' P
    /// only rise inside it, so P(b, t) ∈ [P(b, tLo), P(b, tHi)] and P(b − 1, t) ∈ [P(b − 1, tLo), P(b − 1, tHi)] for every
    /// t of the window. Nil when the bracket moves (the caller evaluates as before). Call after windowBounds(c, t).
    func fixedNeighbourBounds(_ c: SocialCohort, _ xb: Int, _ t: Double) -> (b: Int, aLo: Double, aHi: Double, bLo: Double, bHi: Double)? {
        guard t <= c.ckSpanHi else { return nil }                    // the last second before a local midnight
        if c.ckNbX == xb { return c.ckNb.b < 0 ? nil : c.ckNb }
        c.ckNbX = xb
        let br = bracket(c, xb)
        guard c.ckMono && br.lo == br.hi else { c.ckNb.b = -1; return nil }
        let b = br.lo
        let tLo = c.ckSpanLo, tHi = c.ckSpanHi
        let ninf = -Double.infinity
        c.ckNb = (b, b < c.n ? rawProgress(c, b, tLo) ?? ninf : ninf, b < c.n ? rawProgress(c, b, tHi) ?? ninf : ninf,
                  b > 0 ? rawProgress(c, b - 1, tLo) ?? ninf : ninf, b > 0 ? rawProgress(c, b - 1, tHi) ?? ninf : ninf)
        return c.ckNb
    }

    func bracketedBoundary(_ c: SocialCohort, _ x: Int, _ t: Double) -> Int {
        if t > c.ckSpanHi { return rawBoundary(c, x, t) }               // the last second before a local midnight
        let br = bracket(c, x)
        // B2 (perf, exact): an unchanged bracket (the same boundary b at the span's start and end) IS the boundary at every t
        // of the span. Inside one local day P(j, t) is non-decreasing in t exactly: every term (the install session, lcum's
        // base + Σ min(pace·d, f·q), the honeymoon / lapse / comeback parts) is a monotone composition of correctly rounded
        // + − × ÷ and min, which are monotone; only lcum's day switch can round DOWN by an ulp, and it happens at a local
        // midnight, which no span contains. rawBoundary returned b at the span's start and end, so level(b, start) >= x
        // and level(b − 1, end) < x, hence level(b, t) >= x > level(b − 1, t): the check below would pass — it is skipped.
        if br.lo == br.hi && c.ckMono { return br.lo }
        var lo = min(br.lo, br.hi), hi = max(br.lo, br.hi)          // the answer is in [lo, hi] (hi may be n)
        while lo < hi {
            let mid = (lo + hi) / 2
            if level(c, mid, t) >= x { hi = mid } else { lo = mid + 1 }
        }
        let b = lo
        if (b < c.n && level(c, b, t) < x) || (b > 0 && level(c, b - 1, t) >= x) { return rawBoundary(c, x, t) }
        return b
    }

    func rawBoundary(_ c: SocialCohort, _ x: Int, _ t: Double) -> Int {
        if level(c, c.n - 1, t) < x { return c.n }
        if level(c, 0, t) >= x { return 0 }
        var lo = 0, hi = c.n - 1          // level(hi) >= x, level(lo) < x
        while hi - lo > 1 {
            let mid = (lo + hi) / 2
            if level(c, mid, t) >= x { hi = mid } else { lo = mid }
        }
        return hi
    }

    /// Players at level >= x at time t (x >= 1), optionally only country iso. Frozen cohorts (whose levels no longer
    /// change) contribute a running count kept along their freeze order; the active ones are searched.
    /// Cohorts (n > 0) sorted by the moment they freeze; returns how many are frozen at t (frozenAfter < t).
    func frozenCount(_ t: Double) -> Int {
        if frozenOrderCount != cohorts.count {
            frozenOrder = cohorts.filter { $0.n > 0 }.sorted { $0.frozenAfter < $1.frozenAfter }
            frozenAfterSorted = frozenOrder.map(\.frozenAfter)
            frozenOrderCount = cohorts.count
            frozenPrefix.removeAll()
            frozenNeighbourTop.removeAll()
        }
        var lo = 0, hi = frozenAfterSorted.count
        while lo < hi { let mid = (lo + hi) / 2; if frozenAfterSorted[mid] < t { lo = mid + 1 } else { hi = mid } }
        return lo
    }

    func countAtLeast(_ x: Int, _ t: Double, iso: String? = nil) -> Int {
        if blocksOn, let iso { return countAtLeastUnits(x, t, iso) }
        let m = frozenCount(t)
        let key = "\(x)|\(iso ?? "*")"
        var pre = frozenPrefix[key] ?? [0]
        if pre.count <= m {
            pre.reserveCapacity(m + 1)
            for i in (pre.count - 1)..<m {
                let c = frozenOrder[i]
                let add = (iso == nil || c.iso == iso) ? c.n - boundary(c, x, max(t, c.frozenAfter + 1)) : 0
                pre.append(pre[pre.count - 1] + add)
            }
            if frozenPrefix.count >= 64 { frozenPrefix.removeAll() }
            frozenPrefix[key] = pre
        }
        var tot = pre[m]
        for i in m..<frozenOrder.count {
            let c = frozenOrder[i]
            if iso == nil || c.iso == iso { tot += c.n - boundary(c, x, t) }
        }
        return tot
    }

    func joined(_ t: Double, iso: String? = nil) -> Int { countAtLeast(1, t, iso: iso) }

    /// The rank the USER gets at level x: every player at a higher level is above; the user leads its own level group.
    func rankOfLevel(_ x: Int, _ t: Double, iso: String? = nil) -> Int { 1 + countAtLeast(x + 1, t, iso: iso) }

    struct Ref { let P: Double; let gid: Int; let c: SocialCohort; let j: Int }

    /// Top-k players by progress P (descending; ties → lower gid first): a k-way merge over the cohorts (the reference's
    /// heap), fed LAZILY in upper-bound order: a cohort enters the heap only while its bound could reach the heap's best,
    /// so the heap's best is always the global best (the reference's exact sequence, ties included).
    func top(_ t: Double, _ k: Int, iso: String? = nil) -> [Ref] {
        if blocksOn, let iso { return topUnits(t, k, iso) }
        var h = BinaryHeap<Ref> { a, b in (-a.P, a.gid) < (-b.P, b.gid) }
        let (order, ub) = boundOrder(t, iso: iso)
        var i = 0
        var out: [Ref] = []
        out.reserveCapacity(k)
        while out.count < k {
            while i < order.count && (h.first.map { ub[i] >= $0.P } ?? true) {
                let c = order[i]
                if let P = progress(c, c.n - 1, t) { h.push(Ref(P: P, gid: c.gid0 + c.n - 1, c: c, j: c.n - 1)) }
                i += 1
            }
            guard let r = h.pop() else { break }
            out.append(r)
            if r.j > 0, let P = progress(r.c, r.j - 1, t) {
                h.push(Ref(P: P, gid: r.c.gid0 + r.j - 1, c: r.c, j: r.j - 1))
            }
        }
        return out
    }

    /// The candidate cohorts sorted by an upper bound of their top member's P at t (exact for frozen cohorts, the window
    /// end for active ones, + pad); cached per 6-hour window and filter.
    func boundOrder(_ t: Double, iso: String?) -> (order: [SocialCohort], ub: [Double]) {
        let w = SocialHash.floorDiv(Int(t.rounded(.down)), Self.window)
        let key = iso ?? "*"
        if let hit = topOrder[key], hit.window == w, hit.count == cohorts.count { return (hit.order, hit.ub) }
        var items: [(SocialCohort, Double)] = []
        for c in candidates(iso) {
            let u: Double
            if t > c.frozenAfter {
                u = progress(c, c.n - 1, t) ?? -Double.infinity
            } else {
                windowBounds(c, t)
                u = c.ckTopHi + Self.pad
            }
            if u > -Double.infinity { items.append((c, u)) }
        }
        items.sort { $0.1 > $1.1 }
        let order = items.map(\.0), ub = items.map(\.1)
        if topOrder.count > 16 { topOrder.removeAll() }
        topOrder[key] = (w, cohorts.count, order, ub)
        return (order, ub)
    }

    /// Players just above (level >= x+1, smallest P first) and just below (level <= x, largest P first) a user at
    /// level x, each ordered AWAY from the user (the heap orders of the reference, ties included).
    func neighbours(_ x: Int, _ t: Double, above kA: Int, below kB: Int, iso: String? = nil) -> (above: [Ref], below: [Ref]) {
        if blocksOn, let iso { return neighboursUnits(x, t, above: kA, below: kB, iso) }
        var ha = BinaryHeap<Ref> { a, b in (a.P, a.gid) < (b.P, b.gid) }
        var hb = BinaryHeap<Ref> { a, b in (-a.P, -a.gid) < (-b.P, -b.gid) }
        func firstCandidates(_ c: SocialCohort, _ ha: inout BinaryHeap<Ref>, _ hb: inout BinaryHeap<Ref>) {
            let b = boundary(c, x + 1, t)
            if b < c.n, let P = progress(c, b, t) { ha.push(Ref(P: P, gid: c.gid0 + b, c: c, j: b)) }
            if b > 0, let P = progress(c, b - 1, t) { hb.push(Ref(P: P, gid: c.gid0 + b - 1, c: c, j: b - 1)) }
        }
        if kA <= Self.neighbourK && kB <= Self.neighbourK {
            // frozen cohorts: only the K best first candidates can yield any of the first K pops (each pop removes at
            // most one first candidate, so a better-ranked first candidate is always still waiting); kept exactly along
            // the freeze order. Active cohorts are scanned.
            let m = frozenCount(t)
            let key = "\(x)|\(iso ?? "*")"
            var entry = frozenNeighbourTop[key] ?? (0, [], [])
            // B2 (a SOC1 bug the new pruned-vs-full-scan property found): the memo holds the K best of the first entry.m
            // frozen cohorts; a query at an EARLIER moment (fewer cohorts frozen) cannot use it — those extra cohorts are
            // still active then (the active scan below takes them) — so it rebuilds from the first frozen cohort
            if entry.m > m { entry = (0, [], []) }
            if entry.m < m {
                var fa = BinaryHeap<Ref> { a, b in (a.P, a.gid) < (b.P, b.gid) }
                var fb = BinaryHeap<Ref> { a, b in (-a.P, -a.gid) < (-b.P, -b.gid) }
                for r in entry.above { fa.push(r) }
                for r in entry.below { fb.push(r) }
                for i in entry.m..<m {
                    let c = frozenOrder[i]
                    if iso == nil || c.iso == iso { firstCandidates(c, &fa, &fb) }
                }
                var na: [Ref] = [], nb: [Ref] = []
                while na.count < Self.neighbourK, let r = fa.pop() { na.append(r) }
                while nb.count < Self.neighbourK, let r = fb.pop() { nb.append(r) }
                entry = (m, na, nb)
                if frozenNeighbourTop.count >= 32 { frozenNeighbourTop.removeAll() }
                frozenNeighbourTop[key] = entry
            }
            for r in entry.above { ha.push(r) }
            for r in entry.below { hb.push(r) }
            // active cohorts: the window bounds classify most of them as wholly above or wholly below the player; those
            // only matter if their bound can beat the k-th best candidate already in hand (exact, as above)
            var wholeBelow: [(SocialCohort, Double)] = [], wholeAbove: [(SocialCohort, Double)] = []
            var belowPs = entry.below.map(\.P), abovePs = entry.above.map(\.P)
            var deferA: [(c: SocialCohort, j: Int, lo: Double, hi: Double)] = []
            var deferB: [(c: SocialCohort, j: Int, lo: Double, hi: Double)] = []
            for i in m..<frozenOrder.count {
                let c = frozenOrder[i]
                guard iso == nil || c.iso == iso else { continue }
                windowBounds(c, t)
                if c.ckTopHi == -.infinity { continue }                                    // nobody joined yet
                if 1 + SocialHash.floorInt(c.ckTopHi + Self.pad) < x + 1 { wholeBelow.append((c, c.ckTopHi + Self.pad)); continue }
                if c.ckBotLo != -.infinity && 1 + SocialHash.floorInt(c.ckBotLo - Self.pad) >= x + 1 {
                    wholeAbove.append((c, c.ckBotLo - Self.pad)); continue
                }
                // B2 (perf, exact): a straddler whose boundary is fixed for the window is known by exact bounds first; it is
                // evaluated below only if its bound can still beat the k-th candidate (the same argument as for the frozen
                // cohorts' K best: a first candidate that k others beat never yields any of the first k pops)
                if let nb = fixedNeighbourBounds(c, x + 1, t) {
                    if nb.b < c.n { deferA.append((c, nb.b, nb.aLo, nb.aHi)) }
                    if nb.b > 0 && nb.bHi > -Double.infinity { deferB.append((c, nb.b - 1, nb.bLo, nb.bHi)) }
                    continue
                }
                let b = boundary(c, x + 1, t)
                if b < c.n, let P = progress(c, b, t) { ha.push(Ref(P: P, gid: c.gid0 + b, c: c, j: b)); abovePs.append(P) }
                if b > 0, let P = progress(c, b - 1, t) { hb.push(Ref(P: P, gid: c.gid0 + b - 1, c: c, j: b - 1)); belowPs.append(P) }
            }
            // the deferred straddlers: above = the kA smallest (P, gid); a candidate whose LOWER bound exceeds the kA-th
            // smallest of {exact P in hand} ∪ {deferred upper bounds} is beaten by kA others → skipped. Below mirrors it.
            if kA > 0 && !deferA.isEmpty {
                let ub = (abovePs + deferA.map(\.hi)).sorted()
                let ta = ub.count >= kA ? ub[kA - 1] : Double.infinity
                for d in deferA where d.lo <= ta {
                    if let P = progress(d.c, d.j, t) { ha.push(Ref(P: P, gid: d.c.gid0 + d.j, c: d.c, j: d.j)); abovePs.append(P) }
                }
            }
            if kB > 0 && !deferB.isEmpty {
                let lb = (belowPs + deferB.map(\.lo)).sorted(by: >)
                let tbd = lb.count >= kB ? lb[kB - 1] : -Double.infinity
                for d in deferB where d.hi >= tbd {
                    if let P = progress(d.c, d.j, t) { hb.push(Ref(P: P, gid: d.c.gid0 + d.j, c: d.c, j: d.j)); belowPs.append(P) }
                }
            }
            // below: the kB-th largest P in hand; a wholly-below cohort with a smaller upper bound cannot enter
            belowPs.sort(by: >)
            let tb = belowPs.count >= kB && kB > 0 ? belowPs[kB - 1] : -Double.infinity
            for (c, ub) in wholeBelow where kB > 0 && ub >= tb {
                if let P = progress(c, c.n - 1, t) { hb.push(Ref(P: P, gid: c.gid0 + c.n - 1, c: c, j: c.n - 1)) }
            }
            // above: the kA-th smallest P in hand; a wholly-above cohort with a larger lower bound cannot enter
            abovePs.sort()
            let ta = abovePs.count >= kA && kA > 0 ? abovePs[kA - 1] : Double.infinity
            for (c, lb) in wholeAbove where kA > 0 && lb <= ta {
                if let P = progress(c, 0, t) { ha.push(Ref(P: P, gid: c.gid0, c: c, j: 0)) }
            }
        } else {
            for c in candidates(iso) { firstCandidates(c, &ha, &hb) }
        }
        var above: [Ref] = []
        while above.count < kA, let r = ha.pop() {
            above.append(r)
            if r.j + 1 < r.c.n, let P = progress(r.c, r.j + 1, t) {
                ha.push(Ref(P: P, gid: r.c.gid0 + r.j + 1, c: r.c, j: r.j + 1))
            }
        }
        var below: [Ref] = []
        while below.count < kB, let r = hb.pop() {
            below.append(r)
            if r.j > 0, let P = progress(r.c, r.j - 1, t) {
                hb.push(Ref(P: P, gid: r.c.gid0 + r.j - 1, c: r.c, j: r.j - 1))
            }
        }
        return (above, below)
    }

    // ------------------------------------------------------------- v2 country queries over (cohort, block) units (M1)
    // population.py count_ge / top / neighbours with an iso: a country is a set of member ranges ("units") of many
    // cohorts. Each cohort's boundary is one search; a unit's members are a contiguous range of it, so they stay sorted.

    /// The units of one country, grouped by cohort in cohort order (population.units[iso]), built lazily and extended as
    /// the cohort table grows.
    final class IsoIndex {
        var groups: [(c: SocialCohort, units: [(s: Int, e: Int)])] = []
        var scanned = 0
        var rowIsIso: [[Bool]] = []
        var bound: (window: Int, count: Int, order: [Int], ub: [Double])? = nil
    }

    func isoUnits(_ iso: String) -> IsoIndex {
        let ix: IsoIndex
        if let hit = isoIndex[iso] {
            ix = hit
        } else {
            ix = IsoIndex()
            ix.rowIsIso = bucketRows.map { rs in rs.map { $0.iso == iso } }
            isoIndex[iso] = ix
        }
        let localHere = local?.iso == iso
        while ix.scanned < cohorts.count {
            let c = cohorts[ix.scanned]
            ix.scanned += 1
            guard c.blockHi > c.blockLo else { continue }
            var us: [(s: Int, e: Int)] = []
            for bi in c.blockLo..<c.blockHi {
                let row = Int(blk[bi] >> 16)
                let mine = row == 0xFFFF ? localHere : ix.rowIsIso[c.b][row]
                guard mine else { continue }
                let s0 = Int(blk[bi] & 0xFFFF)
                let e0 = bi + 1 < c.blockHi ? Int(blk[bi + 1] & 0xFFFF) : c.n
                us.append((s0, e0))
            }
            if !us.isEmpty { ix.groups.append((c, us)) }
        }
        return ix
    }

    /// count_ge(x, t, iso) with blocks: per unit, e − max(boundary, s) players at level >= x; one search per cohort.
    func countAtLeastUnits(_ x: Int, _ t: Double, _ iso: String) -> Int {
        let ix = isoUnits(iso)
        var tot = 0
        for g in ix.groups {
            let b = boundary(g.c, x, t)
            for u in g.units where u.e > b { tot += u.e - max(b, u.s) }
        }
        return tot
    }

    /// A candidate of a unit's heap: member j of cohort c, inside the unit's range [lo, hi).
    struct URef { let P: Double; let gid: Int; let c: SocialCohort; let j: Int; let lo: Int; let hi: Int }

    /// top(t, k, iso) with blocks: the reference's k-way merge over the units, fed lazily per cohort in upper-bound order
    /// (a cohort's bound holds for every unit in it), so the heap's best is always the global best.
    func topUnits(_ t: Double, _ k: Int, _ iso: String) -> [Ref] {
        let ix = isoUnits(iso)
        let w = SocialHash.floorDiv(Int(t.rounded(.down)), Self.window)
        let order: [Int], ub: [Double]
        if let b = ix.bound, b.window == w, b.count == ix.groups.count {
            order = b.order; ub = b.ub
        } else {
            var items: [(Int, Double)] = []
            items.reserveCapacity(ix.groups.count)
            for (gi, g) in ix.groups.enumerated() {
                let c = g.c
                let u: Double
                if t > c.frozenAfter {
                    u = progress(c, c.n - 1, t) ?? -Double.infinity
                } else {
                    windowBounds(c, t)
                    u = c.ckTopHi + Self.pad
                }
                if u > -Double.infinity { items.append((gi, u)) }
            }
            items.sort { $0.1 > $1.1 }
            order = items.map(\.0); ub = items.map(\.1)
            ix.bound = (w, ix.groups.count, order, ub)
        }
        var h = BinaryHeap<URef> { a, b in (-a.P, a.gid) < (-b.P, b.gid) }
        var i = 0
        var out: [Ref] = []
        out.reserveCapacity(k)
        while out.count < k {
            while i < order.count && (h.first.map { ub[i] >= $0.P } ?? true) {
                let g = ix.groups[order[i]]
                for u in g.units {
                    if let P = progress(g.c, u.e - 1, t) { h.push(URef(P: P, gid: g.c.gid0 + u.e - 1, c: g.c, j: u.e - 1, lo: u.s, hi: u.e)) }
                }
                i += 1
            }
            guard let r = h.pop() else { break }
            out.append(Ref(P: r.P, gid: r.gid, c: r.c, j: r.j))
            if r.j > r.lo, let P = progress(r.c, r.j - 1, t) {
                h.push(URef(P: P, gid: r.c.gid0 + r.j - 1, c: r.c, j: r.j - 1, lo: r.lo, hi: r.hi))
            }
        }
        return out
    }

    /// neighbours(x, t, kA, kB, iso) with blocks: per unit, the first member at level >= x + 1 (above) and the last at
    /// level <= x (below), each walked AWAY from the user inside its unit (the reference's heaps, ties included).
    func neighboursUnits(_ x: Int, _ t: Double, above kA: Int, below kB: Int, _ iso: String) -> (above: [Ref], below: [Ref]) {
        let ix = isoUnits(iso)
        var ha = BinaryHeap<URef> { a, b in (a.P, a.gid) < (b.P, b.gid) }
        var hb = BinaryHeap<URef> { a, b in (-a.P, -a.gid) < (-b.P, -b.gid) }
        for g in ix.groups {
            let c = g.c
            let b = boundary(c, x + 1, t)
            for u in g.units {
                let ba = b > u.s ? b : u.s                     // first member of the unit at level >= x + 1
                if kA > 0, ba < u.e, let P = progress(c, ba, t) {
                    ha.push(URef(P: P, gid: c.gid0 + ba, c: c, j: ba, lo: u.s, hi: u.e))
                }
                let bb = (b < u.e ? b : u.e) - 1               // last member of the unit at level <= x
                if kB > 0, bb >= u.s, let P = progress(c, bb, t) {
                    hb.push(URef(P: P, gid: c.gid0 + bb, c: c, j: bb, lo: u.s, hi: u.e))
                }
            }
        }
        var above: [Ref] = []
        while above.count < kA, let r = ha.pop() {
            above.append(Ref(P: r.P, gid: r.gid, c: r.c, j: r.j))
            if r.j + 1 < r.hi, let P = progress(r.c, r.j + 1, t) {
                ha.push(URef(P: P, gid: r.c.gid0 + r.j + 1, c: r.c, j: r.j + 1, lo: r.lo, hi: r.hi))
            }
        }
        var below: [Ref] = []
        while below.count < kB, let r = hb.pop() {
            below.append(Ref(P: r.P, gid: r.gid, c: r.c, j: r.j))
            if r.j > r.lo, let P = progress(r.c, r.j - 1, t) {
                hb.push(URef(P: P, gid: r.c.gid0 + r.j - 1, c: r.c, j: r.j - 1, lo: r.lo, hi: r.hi))
            }
        }
        return (above, below)
    }

    /// Number of shared-world ids whose join period has started by t (independent of how far the table is built).
    func gidLimit(_ t: Double) -> Int {
        extend(to: t)
        let p = SocialHash.floorDiv(Int(t) - epoch, SocialCalendar.week)
        if p < 0 { return 0 }
        return periodEndGid[min(p, periodEndGid.count - 1)]
    }

    /// Cohort and index of a shared-world player id (binary search on gid0; LOCAL ids live at >= 2^40).
    func find(_ gid: Int) -> (SocialCohort, Int)? {
        let cs = cohorts
        if cs.isEmpty { return nil }
        if gid >= (1 << 40) {
            for c in cs where c.local && c.gid0 <= gid && gid < c.gid0 + c.n { return (c, gid - c.gid0) }
            return nil
        }
        var lo = 0, hi = cs.count - 1
        while lo < hi {
            let mid = (lo + hi + 1) / 2
            if cs[mid].local || cs[mid].gid0 > gid { hi = mid - 1 } else { lo = mid }
        }
        while lo < cs.count && (cs[lo].local || cs[lo].gid0 + cs[lo].n <= gid) { lo += 1 }
        return lo < cs.count ? (cs[lo], gid - cs[lo].gid0) : nil
    }
}

/// A binary min-heap under a strict "less" (keys are unique in every use, so the pop order is the reference's).
struct BinaryHeap<T> {
    private var a: [T] = []
    let less: (T, T) -> Bool
    init(less: @escaping (T, T) -> Bool) { self.less = less }
    var count: Int { a.count }
    var first: T? { a.first }
    mutating func push(_ x: T) {
        a.append(x)
        var i = a.count - 1
        while i > 0 {
            let p = (i - 1) / 2
            if less(a[i], a[p]) { a.swapAt(i, p); i = p } else { break }
        }
    }
    mutating func pop() -> T? {
        guard !a.isEmpty else { return nil }
        a.swapAt(0, a.count - 1)
        let top = a.removeLast()
        var i = 0
        while true {
            let l = 2 * i + 1, r = l + 1
            var m = i
            if l < a.count && less(a[l], a[m]) { m = l }
            if r < a.count && less(a[r], a[m]) { m = r }
            if m == i { break }
            a.swapAt(i, m); i = m
        }
        return top
    }
}
