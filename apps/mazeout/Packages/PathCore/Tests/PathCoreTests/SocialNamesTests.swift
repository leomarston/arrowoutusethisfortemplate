import XCTest
@testable import GameCore
@testable import ArrowEscape

// SOC1 (§12.2 acceptance: "100 k generated names pass the blocklists; Resources/Social byte-identical to
// design/social/data"; SPEC-architecture §4.11 invariant 6) + the shipped social.json.

final class SocialNamesTests: XCTestCase {
    typealias F = SocFix

    /// 100,000 nicknames of the SHIPPED world (spread over three years of joins): none is blocked, each has 3-16
    /// characters. SOC1c: names are DRAWN with replacement like the original's (two "Bobby" in its World top 15), so they
    /// repeat — at the phone's rate: the chance that two board-like rows (non-tourist players) share a name sits inside
    /// the 95 % interval of the phone's boards (1 repeated pair in 1,721 row pairs: 1.5e-5 … 3.2e-3). Every row is still
    /// one player: identity is the gid, never the name. (SOC1/SOC1b asserted 0 repeats; the reference world still does,
    /// SocialPropertyTests #9.)
    func testHundredThousandShippedNamesPassTheBlocklists() {
        let W = F.world("v552")
        W.extend(to: 1_883_000_000)
        let pEnd = SocialCalendar.eventWeek(1_883_000_000)
        let cs = W.cohorts.filter { $0.n > 0 && $0.p <= pEnd }          // independent of what other tests built
        var seen = Set<String>(), gids = Set<Int>()
        var byName: [String: Int] = [:], boardLike: [String: Int] = [:]
        var n = 0, blocked = 0, dup = 0, badLen = 0, fallbacks = 0, custom = 0, badAvatar = 0, maze = 0
        var k = 0
        while n < 100_000 {
            let c = cs[(k * 7919) % cs.count]
            let j = (k * 104_729) % c.n
            k += 1
            guard seen.insert("\(c.idx)|\(j)").inserted else { continue }
            let (nm, st) = W.name(c, j)
            if SocialNames.isBlocked(nm, bank: F.bank) { blocked += 1 }
            if !(3...16).contains(nm.count) { badLen += 1 }
            let key = SocialNames.key(nm)
            if byName[key, default: 0] > 0 { dup += 1 }
            byName[key, default: 0] += 1
            if c.arch.key != "tourist" { boardLike[key, default: 0] += 1 }   // tourists never reach a board
            gids.insert(W.gid(c, j))
            if st == "fallback" { fallbacks += 1 } else if st != "default" { custom += 1 }
            if !(0...8).contains(W.avatar(c, j, style: st)) { badAvatar += 1 }
            if key.contains("maze") { maze += 1 }
            n += 1
        }
        let nb = Double(boardLike.values.reduce(0, +))
        let rate = Double(boardLike.values.reduce(0) { $0 + $1 * ($1 - 1) }) / (nb * (nb - 1))
        let common = byName.sorted { $0.value > $1.value }.prefix(8).map { "\($0.key) ×\($0.value)" }
        print("[SOC1c] 100k shipped names: blocked \(blocked), bad length \(badLen), repeats \(dup) (\(byName.count) distinct; "
              + "board-like pair rate \(rate) over \(Int(nb)) rows; most common \(common)), fallbacks \(fallbacks), custom \(custom)")
        XCTAssertEqual(blocked, 0)
        XCTAssertEqual(badLen, 0)
        XCTAssertEqual(gids.count, n, "identity = the gid: every sampled player is a different id")
        XCTAssertGreaterThan(dup, 0, "names are drawn with replacement: they repeat (the original's two Bobby)")
        XCTAssertTrue((1.5e-5...3.2e-3).contains(rate), "board-like pair rate \(rate) (phone 1/1721, 95 % CI 1.5e-5 … 3.2e-3)")
        XCTAssertEqual(badAvatar, 0, "shipped avatars are 0 (default) or one of the 8 portraits (CONSISTENCY V-24)")
        XCTAssertEqual(maze, 0, "the original's title word never appears in a shipped nickname")
        XCTAssertGreaterThan(custom, 20_000, "a third of the players picked a name")
    }

    /// SOC1c: a nickname style's share does not depend on the cohort's size (systematic apportionment, population.py
    /// STYLE_SYSTEMATIC). The reference's rounding (each style rounded and clipped, the LAST style takes the remainder)
    /// gave 'leet' ~10 % of the custom names in cohorts under 10 players (weight 3 %) — and the World top is made of such
    /// cohorts (median size 3): S150 / F689 / Y775 in the top 10 of every install's World board, ~12 % of the top 100.
    func testStyleSharesDoNotDependOnCohortSize() {
        let W = F.world("v552")
        let t = 1_790_327_340.0                                          // Fri 25 Sep 2026 12:09 TRT (phone session 2)
        W.extend(to: t)
        let pEnd = SocialCalendar.eventWeek(t)
        let small = W.cohorts.filter { $0.n > 0 && $0.n < 10 && $0.p <= pEnd }
        var cnt: [String: Int] = [:]
        var custom = 0
        for c in small {
            for sc in W.styleCum(c) where sc.style != "default" { cnt[sc.style, default: 0] += sc.hi - sc.lo; custom += sc.hi - sc.lo }
        }
        XCTAssertGreaterThan(custom, 500, "enough small-cohort names to judge")
        XCTAssertTrue(W.model.nameStyle.systematic)
        for (st, w) in W.model.nameStyle.weights {
            let e = Double(custom) * w
            let got = cnt[st, default: 0]
            XCTAssertLessThanOrEqual(abs(Double(got) - e), 4 * (e * (1 - w)).squareRoot() + 1,
                                     "\(st): \(got) of \(custom) custom names in cohorts under 10 players (weight \(w) → \(e))")
        }
        let top = W.top(t, 100)
        let leet = top.filter { W.name($0.c, $0.j).style == "leet" }.count
        print("[SOC1c] style counts in cohorts under 10 players: \(cnt.sorted { $0.key < $1.key }) of \(custom); leet in the World top 100: \(leet)")
        XCTAssertLessThanOrEqual(leet, 8, "leet handles in the World top 100 (weight 3 %; the reference's rounding gave 12)")
    }

    /// The generator never emits a blocked name except as a replaced candidate: every style's raw decode that the
    /// blocklist catches is swapped for a fallback `player_` name (the 0.3 % of SPEC-social §2.8).
    func testBlockedCandidatesAreReplaced() {
        let bad = ["fuckface", "Sh1tHead", "NHLKitten", "kanye", "ass_x", "F4GGOT", "Nazi88", "hitler", "Peacock"]
        for s in bad { XCTAssertTrue(SocialNames.isBlocked(s, bank: F.bank), s) }
        for s in ["Kate23", "Cassandra", "SunnyOtter", "DSMShark", "GOLDEN", "Hsheh", "Gulyabani", "Gülşen_7"] {
            XCTAssertFalse(SocialNames.isBlocked(s, bank: F.bank), s)
        }
        XCTAssertEqual(SocialNames.tokens("NHLKitten"), ["nhl", "kitten"])
        XCTAssertEqual(SocialNames.tokens("SneakyFalconer51"), ["sneaky", "falconer", "51"])
        XCTAssertEqual(SocialNames.tokens("kate_m"), ["kate", "m"])
        XCTAssertEqual(SocialNames.key("Şükrü"), "sukru")
        XCTAssertEqual(SocialNames.key("Sławomir"), "slawomir")
    }

    func testUsernameValidation() {
        XCTAssertEqual(SocialNames.validateUsername("  Hsheh ", bank: F.bank), "Hsheh")
        XCTAssertEqual(SocialNames.validateUsername("Gülşen_7", bank: F.bank), "Gülşen_7")
        XCTAssertNil(SocialNames.validateUsername("ab", bank: F.bank))
        XCTAssertNil(SocialNames.validateUsername("abcdefghijklmnopq", bank: F.bank))
        XCTAssertNil(SocialNames.validateUsername("bad name", bank: F.bank))
        XCTAssertNil(SocialNames.validateUsername("player_abc1234", bank: F.bank))
        XCTAssertNil(SocialNames.validateUsername("Sh1tHead", bank: F.bank))
        // the player's own default name lives in its own slot range
        let me = SocialNames.userDefaultName(installSeed: 42)
        XCTAssertTrue(me.hasPrefix("player_") && me.count == 14)
        XCTAssertEqual(me, SocialNames.userDefaultName(installSeed: 42))
        XCTAssertNotEqual(me, SocialNames.userDefaultName(installSeed: 43))
    }

    /// PUBLISH B2 (requirement change: the app ships the v2 world, SPEC.md rulings 37(b) + 38; PLAN-P G4(c) "blocklist stems
    /// stored hashed"). Was: App/Resources/Social = a byte-for-byte copy of design/social/data (the v1 files). Now the app
    /// ships ONE file, social_names.json = Tests/tools/soc_ship_names.py's build of T6's design/social/data_v2 bank, which
    /// must generate EXACTLY the design bank's names (the goldens pin the design bank) while carrying no text of the
    /// original: the same lists token for token except the unshowable tokens (key holds an extra blocked stem) marked
    /// U+0001 in place, the brand blocklist entries moved to FNV-1a-64 hashes, and 20 000+ players' names identical.
    func testBundledNameDataIsTheShippedBuildOfTheV2Data() throws {
        let dst = F.appRoot.appendingPathComponent("App/Resources/Social")
        let files = try FileManager.default.contentsOfDirectory(atPath: dst.path).filter { !$0.hasPrefix(".") }.sorted()
        XCTAssertEqual(files, ["social_names.json"], "the app ships the v2 name bank only")
        let raw = try String(contentsOf: dst.appendingPathComponent("social_names.json"), encoding: .utf8)
        for word in ["maze", "grandgames", "grand games", "arrowjam", "arrow jam", "v552", "research/", "simulat"] {
            XCTAssertNil(raw.range(of: word, options: .caseInsensitive), "the shipped name data carries no '\(word)'")
        }
        let shipped = try NameBank.load(folder: dst)
        let d = try XCTUnwrap(F.bankV2.store), b = try XCTUnwrap(shipped.store)
        // FIX-3 B (SPEC.md ruling 55(c), V1A-G8-1): the model stores its extra stem HASHED (SocialBlockedStem). This test
        // keeps the plain word as its own independent oracle (tests never ship) and pins, as strongly as the old
        // `XCTAssertEqual(stems, ["maze"])`, that the model's stems are exactly that word's hash.
        let stems = ["maze"]
        XCTAssertEqual(SocialWorldModel.shipped.extraBlockedStems, stems.map { SocialBlockedStem(hashing: $0) })
        var marked = 0
        func same(_ design: [String], _ ship: [String], _ what: String) {
            XCTAssertEqual(design.count, ship.count, what)
            for (x, y) in zip(design, ship) where x != y {
                let unshowable = stems.contains { SocialNames.key(x).contains($0) }
                XCTAssertTrue(y == "\u{1}" && unshowable, "\(what): a token differs without being unshowable")
                marked += 1
            }
            for (x, y) in zip(design, ship) where stems.contains(where: { SocialNames.key(x).contains($0) }) {
                XCTAssertEqual(y, "\u{1}", "\(what): an unshowable token is not marked")
            }
        }
        same(d.words, b.words, "words"); same(d.adjectives, b.adjectives, "adjectives"); same(d.nouns, b.nouns, "nouns")
        same(d.invented, b.invented, "invented"); same(d.caps, b.caps, "caps")
        XCTAssertEqual(Set(d.mixedTokens.keys), Set(b.mixedTokens.keys))
        for (cu, toks) in d.mixedTokens { same(toks, b.mixedTokens[cu] ?? [], "mixed \(cu)") }
        XCTAssertEqual(Set(d.cultures.keys), Set(b.cultures.keys))
        for (cu, toks) in d.cultures {
            let bt = b.cultures[cu] ?? []
            same(toks.map(\.native), bt.map(\.native), "given \(cu) native")
            same(toks.map(\.folded), bt.map(\.folded), "given \(cu) Latin")
        }
        XCTAssertEqual(d.underscoreSuffixes, b.underscoreSuffixes); XCTAssertEqual(d.mixedSuffixes, b.mixedSuffixes)
        XCTAssertEqual(d.initials, b.initials)
        XCTAssertEqual(d.blockSubstring, b.blockSubstring, "the substring stems ship as they are")
        let removed = Set(d.blockToken + d.blockNames).subtracting(b.blockToken + b.blockNames)
        XCTAssertTrue(Set(b.blockToken + b.blockNames).isSubset(of: Set(d.blockToken + d.blockNames)))
        XCTAssertEqual(Set(removed.map { SocialHash.fnv1a64($0) }), b.blockHashed, "hashed = exactly the removed entries")
        XCTAssertFalse(removed.isEmpty)
        XCTAssertTrue(removed.allSatisfy { SocialNames.isBlocked($0, bank: shipped) }, "a hashed entry is still blocked")
        XCTAssertGreaterThan(marked, 0)
        // behaviour: the shipped bank yields the design bank's nickname, style and avatar for every sampled player
        let A = SocialPopulation(model: .shipped, names: F.bankV2), B = SocialPopulation(model: .shipped, names: shipped)
        let t = 1_830_000_000.0                                        // 2027-12-27: a 68-week world
        A.extend(to: t); B.extend(to: t)
        var n = 0, diff = 0, fallbacks = 0
        for (ci, c) in A.cohorts.enumerated() where ci % 7 == 0 {
            let c2 = B.cohorts[ci]
            for j in stride(from: 0, to: c.n, by: max(1, c.n / 12)) {
                let x = A.name(c, j), y = B.name(c2, j)
                n += 1
                if x != y || A.avatar(c, j, style: x.style) != B.avatar(c2, j, style: y.style) { diff += 1 }
                if x.style == "fallback" { fallbacks += 1 }
            }
        }
        XCTAssertGreaterThan(n, 20_000)
        XCTAssertEqual(diff, 0, "names that differ between the shipped and the design bank (of \(n))")
        // every culture's drawn names under the 24 player keys of the goldens, plus the blocklist verdict of each
        let draw = try XCTUnwrap(SocialWorldModel.shipped.nameStyle.draw)
        let ns = SocialWorldModel.shipped.nameStyle
        var dn = 0
        for cu in SocialWorldModel.intlCultures where d.cultures[cu] != nil {
            for st in ["given", "mixed", "underscore", "word", "compound", "invented", "caps", "initials", "leet"] {
                for g in 0..<24 {
                    let key = SocialHash.h64(SocialWorldModel.worldSeed, SocialLabels.nick, g * 7919 + 13)
                    let x = SocialNames.drawn(st, cu, key: key, bank: F.bankV2, variants: ns.variants, draw: draw, nativeT: ns.nativeT, kanaP: ns.kanaP)
                    let y = SocialNames.drawn(st, cu, key: key, bank: shipped, variants: ns.variants, draw: draw, nativeT: ns.nativeT, kanaP: ns.kanaP)
                    func verdict(_ nm: String, _ bank: NameBank) -> Bool {
                        let k = SocialNames.key(nm)
                        return SocialNames.isBlocked(nm, bank: bank) || stems.contains { k.contains($0) }
                    }
                    let bx = x.map { verdict($0, F.bankV2) }, by = y.map { verdict($0, shipped) }
                    XCTAssertEqual(bx, by, "\(st) \(cu): the blocked verdict")
                    if bx == false { XCTAssertEqual(x, y, "\(st) \(cu): a shown name") }
                    dn += 1
                }
            }
        }
        XCTAssertGreaterThan(dn, 9000)
        print("[B2] shipped name bank: \(n) players identical (\(fallbacks) fallback names), \(marked) tokens marked, \(removed.count) entries hashed, \(dn) draws")
    }

    /// FIX-3 B (SPEC.md ruling 55(c), V1A-G8-1): the extra stem ships HASHED (SocialBlockedStem: its length + FNV-1a-64),
    /// and its verdict must be exactly the old plain `key.contains(stem)`'s. Checked on (1) adversarial keys: the stem at
    /// every position, split, doubled, cut short, next to CR LF / combining marks / variation selectors / ZWJ / emoji
    /// modifiers / CJK / fullwidth letters (where a Character is more than its first scalar); (2) every token of both
    /// name banks (the design banks carry the plain tokens the shipped bank marks), alone and joined to its neighbour;
    /// (3) the nickname keys of a shipped-world population built WITHOUT the stem, so names that carry it are generated.
    /// Each set must hold keys that carry the stem, or it proves nothing; a hash collision would show as a mismatch.
    func testHashedStemIsThePlainContains() throws {
        let plain = "maze"
        let s = SocialBlockedStem(hashing: plain)
        XCTAssertEqual(s, SocialBlockedStem(length: 4, fnv: 0x1f20_5da2_ce68_3602))
        XCTAssertEqual(SocialWorldModel.shipped.extraBlockedStems, [s])
        XCTAssertEqual(SocialWorldModel.calibrated.extraBlockedStems, [s])
        XCTAssertEqual(SocialWorldModel.reference.extraBlockedStems, [])
        var n = 0, hits = 0, mismatches: [String] = []
        func check(_ k: String) {
            let want = k.contains(plain)
            n += 1
            if want { hits += 1 }
            if s.matches(k) != want { mismatches.append(k.unicodeScalars.map { String($0.value, radix: 16) }.joined(separator: " ")) }
        }
        let edge = ["maze", "amazes", "xmaze", "mazex", "mazemaze", "mmaze", "maz", "aze", "", "m", "MAZE", "ma ze", "ma_ze",
                    "maze\u{FE0F}", "maze\u{200D}", "maze\u{0301}", "\u{0301}maze", "ma\u{200D}ze", "\u{200D}maze", "maze\u{1F3FB}",
                    "maze\u{E0100}", "ｍaze", "maz\u{00E9}", "maze\u{00E9}", "a\r\nmaze", "maze\r\n", "\r\nmaze", "m\r\naze", "maze\r",
                    "\rmaze", "日本maze", "maze日本", "ma日ze", "🙂maze", "maze🙂", "mazé", "ma\u{0301}ze", "\u{0915}\u{093F}maze",
                    "maze\u{093F}", "player_maze1", "1maze1"]
        for k in edge { check(k) }
        let edgeHits = hits
        XCTAssertGreaterThan(edgeHits, 10)
        for bank in [F.bank, F.bankV2] {
            let d = try XCTUnwrap(bank.store)
            var toks = d.words + d.adjectives + d.nouns + d.invented + d.caps + d.mixedTokens.values.flatMap { $0 }
            for v in d.cultures.values { toks += v.map(\.native) + v.map(\.folded) }
            for (i, t) in toks.enumerated() {
                check(SocialNames.key(t))
                check(SocialNames.key(t + toks[(i + 1) % toks.count]))
            }
        }
        let tokenHits = hits - edgeHits
        XCTAssertGreaterThan(tokenHits, 0, "the design banks hold tokens that carry the stem")
        var m = SocialWorldModel.shipped
        m.extraBlockedStems = []
        let W = SocialPopulation(model: m, names: F.bankV2)
        W.extend(to: 1_830_000_000)
        var names = 0
        for c in W.cohorts where c.n > 0 {
            for j in stride(from: 0, to: c.n, by: max(1, c.n / 8)) {
                check(SocialNames.key(W.name(c, j).name))
                names += 1
            }
        }
        let nameHits = hits - edgeHits - tokenHits
        print("[FIX-3 B] hashed stem vs plain contains: \(n) keys (\(names) generated names), \(hits) carry the stem "
              + "(edge \(edgeHits), tokens \(tokenHits), names \(nameHits)), \(mismatches.count) mismatches")
        XCTAssertGreaterThan(names, 20_000)
        XCTAssertGreaterThan(nameHits, 0, "a world without the stem generates names that carry it (the sample is not blind)")
        XCTAssertEqual(mismatches, [], "hashed verdict != plain contains")
    }

    /// The blocklists inside social_names.json equal the *.txt lists (comments and blank lines dropped, lowercased).
    func testNameJSONBlocklistsEqualTheTextLists() throws {
        func lines(_ name: String) throws -> [String] {
            try String(contentsOf: F.designData.appendingPathComponent(name), encoding: .utf8)
                .split(separator: "\n", omittingEmptySubsequences: false).map(String.init)
                .filter { !$0.isEmpty && !$0.hasPrefix("#") }.map { $0.lowercased() }
        }
        let store = try XCTUnwrap(F.bank.store)
        XCTAssertEqual(Set(store.blockSubstring), Set(try lines("blocklist_substring.txt")))
        XCTAssertEqual(Set(store.blockToken), Set(try lines("blocklist_token.txt")))
        XCTAssertEqual(Set(store.blockNames), Set(try lines("block_names.txt")))
    }

    /// The compiled reference country table equals design/social/data/countries.tsv, row for row.
    func testReferenceCountriesEqualTheTSV() throws {
        let rows = try String(contentsOf: F.designData.appendingPathComponent("countries.tsv"), encoding: .utf8)
            .split(separator: "\n").map(String.init).filter { !$0.isEmpty && !$0.hasPrefix("#") }
            .map { $0.split(separator: "\t", omittingEmptySubsequences: false).map(String.init) }
        XCTAssertEqual(rows.count, SocialWorldModel.referenceCountries.count)
        for (r, c) in zip(rows, SocialWorldModel.referenceCountries) {
            XCTAssertEqual(r[0], c.iso); XCTAssertEqual(Double(r[1]), c.weight); XCTAssertEqual(Int(r[2]), c.offsetMinutes)
            XCTAssertEqual(r[3], c.culture); XCTAssertEqual(r[4], c.bucket)
        }
        XCTAssertTrue(SocialWorldModel.reference.containmentHolds())
        XCTAssertTrue(SocialWorldModel.calibrated.containmentHolds())
        XCTAssertEqual(SocialWorldModel.calibrated.archetypes.reduce(0) { $0 + $1.share }, 1.0, accuracy: 1e-12)
        // PUBLISH B2: the shipped v2 world keeps the calibrated archetypes (socialsim/v2.py applies shipped.py first)
        XCTAssertEqual(SocialWorldModel.shipped.archetypes, SocialWorldModel.calibrated.archetypes)
        XCTAssertTrue(SocialWorldModel.shipped.containmentHolds())
    }

    // ------------------------------------------------------------ Tuning/social.json

    func testShippedSocialJSONEqualsTheCompiledDefaults() throws {
        let url = F.appRoot.appendingPathComponent("App/Resources/Tuning/social.json")
        let data = try Data(contentsOf: url)
        let cfg = try JSONDecoder().decode(SocialConfig.self, from: data)
        XCTAssertEqual(cfg, SocialConfig.default)
        XCTAssertEqual(cfg.weekly.groupSize, 10)
        XCTAssertEqual(cfg.streak.groupSize, 50)
        // PUBLISH B0 (ruling 39 OD8, provenance strip; requirement change): the shipped file names its world "shipped" (was
        // "v552", the original's version tag); the name selects the model only (SocialWorldModel.named: anything but
        // "reference" is the shipped world) and feeds no seed, so the world is unchanged
        XCTAssertEqual(cfg.worldModel, "shipped")
        XCTAssertEqual(cfg.model.name, "shipped")
        XCTAssertEqual(SocialWorldModel.named("v552").name, "shipped", "a config written before the rename still gets the shipped world")
        // SOC1c: Sky Jump stage 3 = the phone's 10 levels / 10000, from ONE place in the file (events.skyJump) that C3's
        // EventRules (the player's runs) and the opponents' survivor curves both read — they switch together
        XCTAssertEqual(cfg.sky.levels, [5, 7, 10])
        XCTAssertEqual(cfg.sky.pools, [5000, 7000, 10000])
        let (ev, problems) = EventRules.load(social: data)
        XCTAssertEqual(problems, [])
        XCTAssertEqual(ev.skyJump.levels, cfg.sky.levels, "C3's runs and the opponents' curves use the same stage levels")
        XCTAssertEqual(ev.skyJump.pools, cfg.sky.pools)
        let (econ, econProblems) = EconomyRules.load(rules: nil, social: data)
        XCTAssertEqual(econProblems, [])
        XCTAssertEqual(econ.events.skyJump.levels, [5, 7, 10], "the app's EconomyRules.load (AppModel/ShopEconomy) sees 10 levels")
        XCTAssertEqual(SocialSkyJump(installSeed: 1, attemptId: 1, stage: 3, spec: cfg.sky).N, ev.skyJump.levels(stage: 3))
    }

    func testConfigDecodingIsTolerant() throws {
        XCTAssertEqual(try JSONDecoder().decode(SocialConfig.self, from: Data("{}".utf8)), SocialConfig.default)
        let partial = #"{"unlocks":{"weeklyContest":45},"events":{"weekly":{"prizes":[3000,1500,700]},"skyJump":{"levels":[4,6,8]}},"matchmaking":{"weekly":{"bands":[[2,1.0,1.5,1]]}},"worldModel":"reference","lists":"oops"}"#
        let c = try JSONDecoder().decode(SocialConfig.self, from: Data(partial.utf8))
        XCTAssertEqual(c.weekly.minLevel, 45)
        XCTAssertEqual(c.weekly.prizes, [3000, 1500, 700])
        XCTAssertEqual(c.sky.levels, [4, 6, 8])
        XCTAssertEqual(c.weekly.groupSize, 3)
        XCTAssertEqual(c.worldModel, "reference")
        XCTAssertEqual(c.lists, SocialListShape(), "a malformed key keeps its default")
        let round = try JSONDecoder().decode(SocialConfig.self, from: JSONEncoder().encode(SocialConfig.default))
        XCTAssertEqual(round, SocialConfig.default)
    }
}
