import Foundation

// SOC1 (SPEC-social §2.8; SPEC-architecture §4.11 invariant 6). Port of design/social/tools/socialsim/names.py + the
// fold/key helpers of data.py. The REFERENCE nickname is decode(style, slot, culture): `slot` is a dense per-(style,
// culture) counter handed out in cohort order (early joiners get the plain names, later ones the decorated variants).
// decode is injective per (style, culture) and the token sets are disjoint across styles and cultures
// (design/social/tools/build_name_data.py), so no two reference players share a nickname. The SHIPPED world (SOC1c)
// draws custom nicknames with replacement instead (`drawn`, SocialNameStyle.draw): names repeat like the original's (two
// "Bobby" in its World top 15); a player's identity is its gid, never its name.
// `NameBank` = the ONE shipped name resource, bundle/Social/social_names.json (copied byte for byte from
// design/social/data by SOC1; the blocklists inside it equal the *.txt lists).

/// The name data the world draws nicknames from (immutable; cheap to copy).
public struct NameBank: Sendable {
    final class Store: @unchecked Sendable {     // immutable after init
        let cultures: [String: [(native: String, folded: String)]]
        let words: [String], adjectives: [String], nouns: [String], invented: [String], caps: [String]
        let underscoreSuffixes: [String], mixedSuffixes: [String]
        let mixedTokens: [String: [String]]
        let initials: [String]
        let blockSubstring: [String]
        let blockSet: Set<String>                // blockToken ∪ blockNames
        let blockToken: [String], blockNames: [String]
        /// PUBLISH B2 (G4(c): the original's brand stems never ship as text): whole-name / token entries stored as the
        /// FNV-1a-64 of their key (lowercase hex in the JSON's "blockHashed"); matched exactly like blockToken ∪ blockNames.
        let blockHashed: Set<UInt64>
        let subByFirstByte: [[[UInt8]]]          // blockSubstring as UTF-8, bucketed by first byte (256 buckets)

        init(json: [String: Any]) throws {
            func strings(_ k: String) throws -> [String] {
                guard let a = json[k] as? [String] else { throw NameBankError.missingKey(k) }
                return a
            }
            guard let cul = json["cultures"] as? [String: [[String]]] else { throw NameBankError.missingKey("cultures") }
            var c: [String: [(native: String, folded: String)]] = [:]
            for (k, v) in cul { c[k] = v.map { (native: $0[0], folded: $0[1]) } }
            cultures = c
            words = try strings("words"); adjectives = try strings("adjectives"); nouns = try strings("nouns")
            invented = try strings("invented"); caps = try strings("caps")
            underscoreSuffixes = try strings("underscoreSuffixes"); mixedSuffixes = try strings("mixedSuffixes")
            guard let mt = json["mixedTokens"] as? [String: [String]] else { throw NameBankError.missingKey("mixedTokens") }
            mixedTokens = mt
            guard let letters = json["initialsLetters"] as? String else { throw NameBankError.missingKey("initialsLetters") }
            let ls = letters.unicodeScalars.map { String($0) }
            var ini: [String] = []
            for a in ls { for b in ls { ini.append(a + b) } }
            for a in ls { for b in ls { for e in ls { ini.append(a + b + e) } } }
            initials = ini
            blockSubstring = try strings("blockSubstring")
            blockToken = try strings("blockToken"); blockNames = try strings("blockNames")
            blockSet = Set(blockToken).union(blockNames)
            let hashed = (json["blockHashed"] as? [String]) ?? []
            var hs = Set<UInt64>()
            for h in hashed {
                guard let v = UInt64(h, radix: 16) else { throw NameBankError.missingKey("blockHashed") }
                hs.insert(v)
            }
            blockHashed = hs
            var buckets = [[[UInt8]]](repeating: [], count: 256)
            for b in blockSubstring where !b.isEmpty { let u = Array(b.utf8); buckets[Int(u[0])].append(u) }
            subByFirstByte = buckets
        }
    }

    let store: Store?

    /// An EMPTY bank (tests, previews): every simulated player then keeps a `player_` name. The app always loads the
    /// bundled data (`load(folder:)`).
    public init() { store = nil }

    init(store: Store) { self.store = store }

    public var isEmpty: Bool { store == nil }

    /// Loads `folder/social_names.json` (the app passes `bundle/Social`).
    public static func load(folder: URL) throws -> NameBank {
        try load(data: Data(contentsOf: folder.appendingPathComponent("social_names.json")))
    }

    public static func load(data: Data) throws -> NameBank {
        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw NameBankError.missingKey("<root>")
        }
        return NameBank(store: try Store(json: json))
    }
}

public enum NameBankError: Error, Equatable { case missingKey(String) }

/// A world's nickname style mix and the shipped variants (names.py CUSTOM_WEIGHTS / VARIANTS; socialsim/shipped.py).
public struct SocialNameStyle: Sendable, Equatable {
    /// Style mix among players who set a custom name (the rest keep the default "player_xxxxxxx"), in table order (the
    /// reference: the last style takes the remainder of a cohort's custom names; see `systematic`).
    public var weights: [(style: String, weight: Double)]
    /// Shipped-only variants, in percent (nil = the prototype): case variants never collide (uniqueness is case-insensitive)
    /// and the compound digit variant swaps round 0 with one 2-digit round per token (still a bijection).
    public struct Variants: Sendable, Equatable {
        public var inventedLower: UInt64, inventedUpper: UInt64, givenUpper: UInt64, compoundDigits: UInt64, mixedLower: UInt64
    }
    public var variants: Variants?
    /// Shipped only (SOC1c; nil = the reference's unique first-come slots): custom nicknames are DRAWN with replacement
    /// by the player's gid (names.py DRAW / drawn). Percentages; `headN` = how many of the most common first names form
    /// the head of the popularity draw.
    public struct Draw: Sendable, Equatable {
        public var numberP: [String: Int]
        public var twoDigitP: Int
        public var headP: Int
        public var headN: Int
        /// v2 (M7, names.DRAW 'headScaled' / 'tailUniformP'): the head is min(headN, n / 6) names drawn on
        /// headP × min(n, 300) / 300 % of the draws, and tailUniformP % of the rest uniform over the list (else ⌊n·u²⌋):
        /// the most common name of a list is ~1.5-2.5 % of the draws, not ~4-11 %.
        public var headScaled = false
        public var tailUniformP = 0
    }
    public var draw: Draw? = nil
    /// v2 (M6, names.NATIVE_T / KANA_P): per culture, the share of first names shown in their NATIVE form as a threshold t
    /// of 256 (the spelling byte v < t → native); nil = the reference's 180/256 for every culture. kanaP = % of Japanese
    /// native forms shown in katakana instead of hiragana.
    public var nativeT: [String: Int]? = nil
    public var kanaP = 0
    /// Per-cohort style counts (population.py STYLE_SYSTEMATIC). false (the reference): each style's count is rounded on
    /// its own and clipped, the LAST style takes the remainder — several times its weight in a small cohort (with 'leet'
    /// last: ~10 % in cohorts under 10 players, ~12 % of the World top 100). true (shipped, SOC1c): systematic
    /// apportionment — one offset u per cohort, count_i = ⌊C·W_i + u⌋ − ⌊C·W_(i−1) + u⌋ over the cumulative weights, so
    /// every style's expected count is C·w_i at any cohort size and nothing is clipped.
    public var systematic: Bool = false

    public static func == (a: SocialNameStyle, b: SocialNameStyle) -> Bool {
        a.weights.map(\.style) == b.weights.map(\.style) && a.weights.map(\.weight) == b.weights.map(\.weight) && a.variants == b.variants
            && a.draw == b.draw && a.systematic == b.systematic && a.nativeT == b.nativeT && a.kanaP == b.kanaP
    }

    /// names.py as written (the prototype).
    public static let reference = SocialNameStyle(
        weights: [("given", 0.34), ("word", 0.07), ("compound", 0.19), ("invented", 0.14), ("caps", 0.04), ("underscore", 0.10),
                  ("initials", 0.05), ("mixed", 0.07)],
        variants: nil)

    /// Shipped (SOC1b + SOC1c; socialsim/shipped.py). The phone's boards (§H, classified like calib_s2.py): player_ 14 %,
    /// plain first names 14 %, other capitalised names/handles 34 %, lowercase 15 %, CamelCase 12 % (a third with 2
    /// digits), ALL CAPS 4 %, digits/leet 7 %; two different "Bobby" in its World top 15. SOC1c draws the names with
    /// replacement (`draw`), so the mix leans on first names again; SOC1b's unique slots left 0.5 % plain first names
    /// and 24 % digits.
    public static let calibrated = SocialNameStyle(
        weights: [("given", 0.24), ("word", 0.01), ("compound", 0.14), ("invented", 0.36), ("caps", 0.02), ("underscore", 0.005),
                  ("initials", 0.005), ("mixed", 0.19), ("leet", 0.03)],
        variants: Variants(inventedLower: 25, inventedUpper: 8, givenUpper: 8, compoundDigits: 35, mixedLower: 17),
        draw: Draw(numberP: ["given": 5, "word": 5, "invented": 5, "caps": 5, "underscore": 5, "initials": 5, "mixed": 5],
                   twoDigitP: 75, headP: 40, headN: 50),
        systematic: true)

    /// The SHIPPED v2 style (PUBLISH B2; socialsim/v2.py): the calibrated mix and variants, with
    ///   M6 native-script shares (ruling 38 = social-intl §7-2: ja 45 %, ko 50 %, zh 60 %, ar 30 %, ru/uk/bg 35 %, el 30 %,
    ///      th 30 %, he 25 %; fa like ar, kk like ru; hy / ka 0 — no stems for those scripts), as thresholds ⌊(p·256 + 50) / 100⌋
    ///      of the spelling byte; 35 % of Japanese native names in katakana;
    ///   M7 the popularity head scaled to the list (headP 20 over min(50, n / 6) names; half of the rest uniform).
    public static let shipped: SocialNameStyle = {
        var s = calibrated
        s.draw = Draw(numberP: ["given": 5, "word": 5, "invented": 5, "caps": 5, "underscore": 5, "initials": 5, "mixed": 5],
                      twoDigitP: 75, headP: 20, headN: 50, headScaled: true, tailUniformP: 50)
        let share = ["jp": 45, "kr": 50, "zh": 60, "ar": 30, "ru": 35, "uk": 35, "bg": 35, "el": 30, "th": 30, "he": 25, "fa": 30,
                     "hy": 0, "ka": 0, "kk": 35]
        s.nativeT = share.mapValues { ($0 * 256 + 50) / 100 }
        s.kanaP = 35
        return s
    }()
}

/// The nickname generator and the blocklist (names.py).
public enum SocialNames {
    /// names.py STYLES_V2: the prototype's nine styles, then the shipped 'leet' (a style's index keys its hashes).
    public static let styles = ["default", "given", "word", "compound", "invented", "caps", "underscore", "initials", "mixed", "leet"]
    static let cultureStyles: Set<String> = ["given", "underscore", "mixed"]

    // 'leet' (shipped): procedural short handles with digits inside — X d Y (L8M), X ddd (K710), 0x X Y (0xBK). Every form
    // has a digit before a letter or is one letter + exactly 3 digits, which no other style can produce.
    static let leetLetters = Array("ABCDEFGHJKLMNPRSTVWXYZ").map(String.init)
    static let leetA = 22 * 9 * 22, leetB = 22 * 900, leetC = 22 * 22
    static let leetSize = leetA + leetB + leetC
    static func leetToken(_ i0: Int) -> String {
        let L = leetLetters, n = L.count
        var i = i0
        if i < leetA { return L[i / (9 * n)] + String(1 + (i / n) % 9) + L[i % n] }
        i -= leetA
        if i < leetB { return L[i / 900] + String(100 + i % 900) }
        i -= leetB
        return "0x" + L[i / n] + L[i % n]
    }
    static let b36 = Array("0123456789abcdefghijklmnopqrstuvwxyz")
    public static let d36_7 = 78_364_164_096              // 36^7
    public static let localDefaultBase = d36_7 / 2         // LOCAL partition default-name slots
    public static let userDefaultBase = d36_7 / 4          // the user's own default name
    public static let localCustomBase = 1_000_000_000      // LOCAL partition custom-style slots
    static let nameSeed: UInt64 = 0x6E61_6D65              // "name"
    static let defaultSeed: UInt64 = 0x706C_6179           // "play"

    static func styleIndex(_ s: String) -> Int { styles.firstIndex(of: s) ?? 0 }
    /// names._tokkey: the culture's index in data.CULTURES (v2 appends its cultures after the reference's 16, so the
    /// reference / calibrated indices are unchanged), 99 when unknown.
    static func cultureIndex(_ c: String) -> Int { cultureIndexMap[c] ?? 99 }
    static let cultureIndexMap: [String: Int] = {
        var m: [String: Int] = [:]
        for (i, c) in SocialWorldModel.intlCultures.enumerated() where m[c] == nil { m[c] = i }
        return m
    }()

    /// r >= 1 → a decimal string, injective in r: 1..9 → 1 digit, 10..99 → 2 digits, … each length class permuted by the
    /// token key (so 'Kate' and 'Mia' don't get the same number sequence).
    public static func number(_ r: Int, _ tokkey: UInt64) -> String {
        var lo = 1, hi = 10
        while r >= hi { lo = hi; hi *= 10 }
        return String(lo + SocialHash.perm(r - lo, hi - lo, tokkey))
    }

    static func tokkey(_ style: String, _ culture: String, _ idx: Int) -> UInt64 {
        SocialHash.h64(nameSeed, SocialLabels.tok, styleIndex(style), cultureIndex(culture), idx)
    }

    /// slot → (index in [0, size), round), the round-0 order shuffled per (style, culture) and per round.
    static func grid(_ slot: Int, _ size: Int, _ style: String, _ culture: String) -> (Int, Int) {
        let r = slot / size, i = slot % size          // slot >= 0
        let key = SocialHash.h64(nameSeed, SocialLabels.grid, styleIndex(style), cultureIndex(culture), r)
        return (SocialHash.perm(i, size, key), r)
    }

    /// "player_" + 7 base-36 chars: a keyed bijection of the slot into 36^7 (always salt 0 in the product).
    public static func defaultName(_ slot: Int, salt: Int = 0) -> String {
        var x = SocialHash.perm(SocialHash.posMod(slot, d36_7), d36_7, SocialHash.h64(defaultSeed, SocialLabels.dflt, salt))
        var s = [Character](repeating: "0", count: 7)
        for k in stride(from: 6, through: 0, by: -1) { s[k] = b36[x % 36]; x /= 36 }
        return "player_" + String(s)
    }

    /// The user's own default name until they pick one.
    public static func userDefaultName(installSeed: UInt64) -> String {
        defaultName(userDefaultBase + Int(SocialHash.h64(installSeed, SocialLabels.username) & ((1 << 30) - 1)))
    }

    static func capFirst(_ s: String) -> String {
        guard let f = s.unicodeScalars.first else { return s }
        return String(f).uppercased() + String(s.unicodeScalars.dropFirst())
    }

    /// names.py grid_size: the size of a style's round-0 token grid for a culture (nil: no data — an empty bank, or a
    /// culture the bank does not hold).
    static func gridSize(_ style: String, _ culture: String, bank: NameBank) -> Int? {
        if style == "leet" { return bank.store == nil ? nil : leetSize }
        guard let d = bank.store else { return nil }
        switch style {
        case "given": return d.cultures[culture].flatMap { $0.isEmpty ? nil : $0.count }
        case "word": return d.words.count
        case "compound": return d.adjectives.count * d.nouns.count
        case "invented": return d.invented.count
        case "caps": return d.caps.count
        case "underscore": return d.cultures[culture].flatMap { $0.isEmpty ? nil : $0.count * d.underscoreSuffixes.count }
        case "initials": return d.initials.count * d.nouns.count
        case "mixed": return d.mixedTokens[culture].flatMap { $0.isEmpty ? nil : $0.count * d.mixedSuffixes.count }
        default: return nil
        }
    }

    /// decode(style, slot, culture) of names.py — the reference's first-come nickname: slot → (grid index, round) →
    /// `build`. Nil when the bank is empty (degraded mode). `variants` = the world's shipped variants (nil = the prototype).
    public static func decode(_ style: String, _ slot: Int, _ culture: String, bank: NameBank,
                              variants V: SocialNameStyle.Variants? = nil, nativeT: [String: Int]? = nil,
                              kanaP: Int = 0) -> String? {
        if style == "default" { return defaultName(slot) }
        guard let size = gridSize(style, culture, bank: bank) else { return nil }
        let cul = cultureStyles.contains(style) ? culture : "*"
        let (i, r) = grid(slot, size, style, cul)
        return build(style, i, r, culture, bank: bank, variants: V, vr: r, nativeT: nativeT, kanaP: kanaP)
    }

    /// build(style, i, r, culture, vr) of names.py: the nickname at grid index `i` (round-0 order) and round `r` (r >= 1
    /// appends number(r, token key)); `vr` keys the case / spelling variants (the reference: the round; the shipped drawn
    /// names: a per-player value).
    static func build(_ style: String, _ i: Int, _ r0: Int, _ culture: String, bank: NameBank,
                      variants V: SocialNameStyle.Variants?, vr: Int, nativeT: [String: Int]? = nil, kanaP: Int = 0) -> String? {
        if style == "leet" {
            guard bank.store != nil else { return nil }        // degraded mode: an empty bank shows only player_ names
            let s = leetToken(i)
            return r0 == 0 ? s : s + number(r0, tokkey(style, "*", i))
        }
        guard let d = bank.store else { return nil }
        let cul = cultureStyles.contains(style) ? culture : "*"
        var r = r0
        switch style {
        case "given":
            guard let toks = d.cultures[culture], !toks.isEmpty else { return nil }
            let k = tokkey(style, cul, i)
            let v = SocialHash.h64(k, SocialLabels.spell, vr) & 0xFF
            let useNative = v < UInt64(nativeT?[culture] ?? 180)       // reference: ~70 % native spelling, ~30 % ASCII-folded
            var base = useNative ? toks[i].native : toks[i].folded
            if kanaP > 0 && useNative && culture == "jp" && SocialHash.h64(k, SocialLabels.kana, vr) % 100 < UInt64(kanaP) {
                base = toKatakana(toks[i].native)                     // v2 (M6): a per-player katakana form
            }
            if v % 5 == 0 {
                base = base.lowercased()                               // ~20 % typed in lowercase
            } else if let V = V, SocialHash.h64(k, SocialLabels.upper, vr) % 100 < V.givenUpper {
                base = toks[i].folded.uppercased()                     // shipped: ASLAN, KAREN (ASCII: exact)
            }
            return r == 0 ? base : base + number(r, k)
        case "word":
            let toks = d.words
            let k = tokkey(style, cul, i)
            var w = toks[i]
            if SocialHash.h64(k, SocialLabels.caseL, vr) & 3 == 0 { w = capFirst(w) }   // 'Nope' vs 'nope'
            return r == 0 ? w : w + number(r, k)
        case "compound":
            let a = d.adjectives, n = d.nouns
            let s = capFirst(a[i / n.count]) + capFirst(n[i % n.count])
            let k = tokkey(style, cul, i)
            if let V = V, SocialHash.h64(k, SocialLabels.d2) % 100 < V.compoundDigits {
                let rs = 10 + Int(SocialHash.h64(k, SocialLabels.r2) % 90)   // a 2-digit round: number(rs) has 2 digits
                r = r == 0 ? rs : (r == rs ? 0 : r)
            }
            return r == 0 ? s : s + number(r, k)
        case "invented":
            var s = d.invented[i]
            if let V = V {
                let x = SocialHash.h64(tokkey(style, cul, i), SocialLabels.lower, vr) % 100
                if x < V.inventedLower { s = s.lowercased() }                                  // rng, ecr, turko
                else if x < V.inventedLower + V.inventedUpper { s = s.uppercased() }          // DER (ASCII tokens)
            }
            return r == 0 ? s : s + number(r, tokkey(style, cul, i))
        case "caps":
            return r == 0 ? d.caps[i] : d.caps[i] + number(r, tokkey(style, cul, i))
        case "underscore":
            guard let toks = d.cultures[culture], !toks.isEmpty else { return nil }
            let suf = d.underscoreSuffixes
            let t = toks[i / suf.count].folded.lowercased().replacingOccurrences(of: " ", with: "")
            let s = t + "_" + suf[i % suf.count]
            return r == 0 ? s : s + number(r, tokkey(style, cul, i))
        case "initials":
            let ini = d.initials, n = d.nouns
            let s = ini[i / n.count].uppercased() + capFirst(n[i % n.count])
            return r == 0 ? s : s + number(r, tokkey(style, cul, i))
        case "mixed":
            guard let toks = d.mixedTokens[culture], !toks.isEmpty else { return nil }
            let suf = d.mixedSuffixes
            var s = toks[i / suf.count] + suf[i % suf.count]
            if let V = V, SocialHash.h64(tokkey(style, cul, i), SocialLabels.lower, vr) % 100 < V.mixedLower {
                s = s.lowercased()                                     // shipped: 'limminator'-style, typed in lowercase
            }
            return r == 0 ? s : s + number(r, tokkey(style, cul, i))
        default:
            return nil
        }
    }

    /// names.py POPULAR_STYLES: the first-name styles, drawn by popularity (the per-culture lists are most common first).
    static let popularStyles: Set<String> = ["given", "mixed", "underscore"]

    /// drawn(style, culture, key) of names.py — the SHIPPED nickname of a custom-named player (SOC1c; names.DRAW):
    /// key = h64(world seed, "nick", gid). Drawn WITH replacement, so names repeat like the original's (two "Bobby" in its
    /// World top 15); the player's identity stays its gid. First-name styles: `headP` % one of the `headN` most common
    /// names uniformly, else index ⌊n·u²⌋ over the whole list; the suffix uniformly; other styles uniformly over their
    /// grid. A number on `numberP[style]` % (2 digits `twoDigitP` %, else 3); case / spelling variants per player.
    /// Nil when the bank is empty or lacks the culture (the caller falls back to a `player_` name).
    public static func drawn(_ style: String, _ culture: String, key: UInt64, bank: NameBank,
                             variants V: SocialNameStyle.Variants?, draw D: SocialNameStyle.Draw,
                             nativeT: [String: Int]? = nil, kanaP: Int = 0) -> String? {
        guard let (i, _) = drawIndex(style, culture, key: key, bank: bank, draw: D) else { return nil }
        typealias H = SocialHash
        typealias L = SocialLabels
        var r = 0
        if H.below(key, L.numQ, 100) < (D.numberP[style] ?? 0) {
            r = H.below(key, L.num2, 100) < D.twoDigitP ? 10 + H.below(key, L.num, 90) : 100 + H.below(key, L.num, 900)
        }
        return build(style, i, r, culture, bank: bank, variants: V, vr: Int(H.h64(key, L.variant) & 0x7FFF_FFFF),
                     nativeT: nativeT, kanaP: kanaP)
    }

    /// names.draw_index: the grid index a drawn nickname is built on and, for the first-name styles, the index of its first
    /// name in the culture's list (nil for the other styles). Nil when the bank is empty or lacks the culture.
    static func drawIndex(_ style: String, _ culture: String, key: UInt64, bank: NameBank,
                          draw D: SocialNameStyle.Draw) -> (index: Int, token: Int?)? {
        typealias H = SocialHash
        typealias L = SocialLabels
        guard let d = bank.store else { return nil }
        if popularStyles.contains(style) {
            let toks = style == "mixed" ? d.mixedTokens[culture]?.count : d.cultures[culture]?.count
            guard let ntok = toks, ntok > 0 else { return nil }
            let nsuf = style == "given" ? 1 : (style == "mixed" ? d.mixedSuffixes.count : d.underscoreSuffixes.count)
            let t: Int
            if D.headScaled {
                // v2 (M7): the head scaled to the list, part of the rest uniform
                let headN = max(1, min(D.headN, ntok / 6))
                if H.below(key, L.headQ, 100) < D.headP * min(ntok, 300) / 300 {
                    t = H.below(key, L.head, headN)
                } else {
                    let u = H.u01(key, L.pop)
                    if H.below(key, L.tailU, 100) < D.tailUniformP {
                        t = H.floorInt(Double(ntok) * u)
                    } else {
                        t = H.floorInt(Double(ntok) * u * u)
                    }
                }
            } else if H.below(key, L.headQ, 100) < D.headP {
                t = H.below(key, L.head, min(D.headN, ntok))       // the most common names: real first names are concentrated
            } else {
                let u = H.u01(key, L.pop)
                t = H.floorInt(Double(ntok) * u * u)               // the rest by rank: P(index < k) = sqrt(k / n)
            }
            return (t * nsuf + H.below(key, L.suf, nsuf), t)
        }
        guard let n = gridSize(style, culture, bank: bank) else { return nil }
        return (H.below(key, L.pick, n), nil)
    }

    /// names.to_katakana: hiragana U+3041…U+3096 shifted by 0x60; every other character unchanged.
    static func toKatakana(_ s: String) -> String {
        var out = String.UnicodeScalarView()
        for sc in s.unicodeScalars {
            if (0x3041...0x3096).contains(sc.value), let k = Unicode.Scalar(sc.value + 0x60) { out.append(k) } else { out.append(sc) }
        }
        return String(out)
    }

    // ------------------------------------------------------------------ fold / key (data.py) and the blocklist

    static let foldMap: [Character: String] = ["ı": "i", "İ": "I", "ß": "ss", "ł": "l", "Ł": "L", "ø": "o", "Ø": "O",
                                                "æ": "ae", "Æ": "Ae", "ð": "d", "þ": "th"]

    @inline(__always) static func isASCII(_ s: String) -> Bool { s.utf8.allSatisfy { $0 < 0x80 } }

    /// ASCII fold for uniqueness keys and the 'folded' spelling (ı→i, ß→ss, ł→l, …, then NFKD with the marks stripped).
    public static func fold(_ s: String) -> String {
        if isASCII(s) { return s }                        // NFKD of ASCII is itself; nothing to strip
        var pre = ""
        pre.reserveCapacity(s.utf8.count)
        for sc in s.unicodeScalars {
            if let r = foldMap[Character(sc)] { pre += r } else { pre.unicodeScalars.append(sc) }
        }
        var out = String.UnicodeScalarView()
        for sc in pre.decomposedStringWithCompatibilityMapping.unicodeScalars
        where sc.properties.canonicalCombiningClass == .notReordered {
            out.append(sc)
        }
        return String(out)
    }

    /// Case- and accent-insensitive key (data.key).
    public static func key(_ s: String) -> String {
        if isASCII(s) {
            return String(decoding: s.utf8.map { ($0 >= 65 && $0 <= 90) ? $0 + 32 : $0 }, as: UTF8.self)
        }
        return fold(s).lowercased()
    }

    static let leet: [Unicode.Scalar: Unicode.Scalar] = ["0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b",
                                                         "@": "a", "$": "s", "!": "i"]
    static func leetFold(_ s: String) -> String {
        if isASCII(s) {
            return String(decoding: s.utf8.map { b -> UInt8 in
                switch b {
                case 48: return 111   // 0 → o
                case 49, 33: return 105   // 1 ! → i
                case 51: return 101   // 3 → e
                case 52, 64: return 97    // 4 @ → a
                case 53, 36: return 115   // 5 $ → s
                case 55: return 116   // 7 → t
                case 56: return 98    // 8 → b
                default: return b
                }
            }, as: UTF8.self)
        }
        var out = String.UnicodeScalarView()
        for sc in s.unicodeScalars { out.append(leet[sc] ?? sc) }
        return String(out)
    }

    static func isDigit(_ s: Unicode.Scalar) -> Bool {
        switch s.properties.numericType { case .decimal?, .digit?: return true; default: return false }
    }

    /// Lowercase tokens split at '_', letter/digit changes and CamelCase humps, including an acronym run followed by a
    /// capitalised word ("NHLKitten" → nhl, kitten).
    public static func tokens(_ name: String) -> [String] {
        let chars = Array(name.unicodeScalars)
        var toks: [String] = []
        var cur = String.UnicodeScalarView()
        for (i, ch) in chars.enumerated() {
            if ch == "_" {
                if !cur.isEmpty { toks.append(String(cur)) }
                cur = String.UnicodeScalarView()
                continue
            }
            var brk = false
            if let prev = cur.last {
                let nxtLower = i + 1 < chars.count ? chars[i + 1].properties.isLowercase : false
                if isDigit(ch) != isDigit(prev) {
                    brk = true
                } else if ch.properties.isUppercase && prev.properties.isLowercase {
                    brk = true
                } else if ch.properties.isUppercase && prev.properties.isUppercase && nxtLower {
                    brk = true
                }
            }
            if brk { toks.append(String(cur)); cur = String.UnicodeScalarView() }
            cur.append(ch)
        }
        if !cur.isEmpty { toks.append(String(cur)) }
        return toks.map(key)
    }

    /// The allowed length (characters) of a username: 2-16 when it contains Han, Hangul or kana, else 3-16.
    public static func usernameLengths(_ s: String) -> ClosedRange<Int> { (hasCJK(s) ? 2 : 3)...16 }

    /// True when a character of `s` is Han, Hangul or kana (tests_v2.username_ok: the Unicode name starts with CJK UNIFIED,
    /// HANGUL, HIRAGANA or KATAKANA).
    static func hasCJK(_ s: String) -> Bool {
        for sc in s.unicodeScalars where sc.value >= 0x1100 {
            guard let nm = sc.properties.name else { continue }
            if nm.hasPrefix("CJK UNIFIED") || nm.hasPrefix("HANGUL") || nm.hasPrefix("HIRAGANA") || nm.hasPrefix("KATAKANA") { return true }
        }
        return false
    }

    /// The blocklist verdict (profanity/slur stems in 8 languages with leet folding, celebrities, brands, acronyms, the
    /// original's and publisher's names). An empty bank blocks nothing.
    public static func isBlocked(_ name: String, bank: NameBank) -> Bool {
        guard let d = bank.store else { return false }
        // PUBLISH B2: the shipped data marks a list token that can never be shown (its key holds an extra blocked stem)
        // with U+0001 in place (Tests/tools/soc_ship_names.py): every name built on it is blocked, as the stem would
        if name.utf8.contains(1) { return true }
        let k = leetFold(key(name))
        // substring stems: a UTF-8 byte search (UTF-8 is self-synchronising, so a byte match is a code-point match)
        let kb = Array(k.utf8)
        for i in kb.indices {
            for b in d.subByFirstByte[Int(kb[i])] where i + b.count <= kb.count {
                var ok = true
                for q in 1..<b.count where kb[i + q] != b[q] { ok = false; break }
                if ok { return true }
            }
        }
        if d.blockSet.contains(k) { return true }
        let hashed = !d.blockHashed.isEmpty
        if hashed && d.blockHashed.contains(SocialHash.fnv1a64(k)) { return true }
        for t in tokens(name) {
            if d.blockSet.contains(t) || d.blockSet.contains(leetFold(t)) { return true }
            if hashed && (d.blockHashed.contains(SocialHash.fnv1a64(t)) || d.blockHashed.contains(SocialHash.fnv1a64(leetFold(t)))) {
                return true
            }
        }
        return false
    }

    /// A username the player typed: 3-16 characters (2-16 when it contains Han, Hangul or kana: 민수, 小明, 太郎 —
    /// social-intl P2-4, PUBLISH B2), letters (any script), digits and '_', trimmed, not blocked, and not shaped like a
    /// default name (SPEC-social §2.8). Returns the trimmed name or nil.
    public static func validateUsername(_ raw: String, bank: NameBank) -> String? {
        let s = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard usernameLengths(s).contains(s.count) else { return nil }
        for ch in s where !(ch == "_" || ch.isLetter || ch.isNumber) { return nil }
        if s.lowercased().hasPrefix("player_") { return nil }
        return isBlocked(s, bank: bank) ? nil : s
    }
}

/// A blocked nickname stem stored HASHED (FIX-3 B, SPEC.md ruling 55(c), V1A-G8-1; PLAN-P G4(c) "blocklist stems stored
/// hashed"): its length in Characters and the FNV-1a-64 of its UTF-8 bytes, like the name bank's hashed brand entries
/// (`blockHashed`), so the binary never spells it. `matches(key)` is true when some run of `length` consecutive Characters
/// of `key` hashes to it. For an ASCII stem that is exactly `key.contains(stem)`, the check it replaces (String.contains
/// compares Characters, and an ASCII Character equals only its own one-byte spelling), up to a 64-bit hash collision;
/// SocialNamesTests.testHashedStemIsThePlainContains proves it on adversarial Unicode keys, every token of both name banks
/// and ~130 k nicknames of a world generated WITHOUT the stem (so names that carry it are in the sample).
public struct SocialBlockedStem: Sendable, Equatable {
    public let length: Int
    public let fnv: UInt64

    public init(length: Int, fnv: UInt64) {
        self.length = length
        self.fnv = fnv
    }

    /// Hashes a plain stem (tests and tools only: the shipped model is written with the hash, never the text).
    public init(hashing stem: String) { self.init(length: stem.count, fnv: SocialHash.fnv1a64(stem)) }

    public func matches(_ key: String) -> Bool {
        guard length > 0 else { return false }
        // ASCII without CR: one Character per byte (CR LF is ASCII's only two-byte Character), so the windows are byte runs,
        // hashed in place (SocialHash.fnv1a64's loop over the run's bytes) — the hot path: nearly every folded key is ASCII
        let fast: Bool?? = key.utf8.withContiguousStorageIfAvailable { u -> Bool? in
            for b in u where b >= 0x80 || b == 13 { return nil }
            guard u.count >= length else { return false }
            for i in 0...(u.count - length) {
                var h: UInt64 = 0xcbf2_9ce4_8422_2325
                for q in i..<(i + length) {
                    h ^= UInt64(u[q])
                    h = h &* 0x0000_0100_0000_01b3
                }
                if h == fnv { return true }
            }
            return false
        }
        if let f = fast, let r = f { return r }
        let cs = Array(key)
        guard cs.count >= length else { return false }
        for i in 0...(cs.count - length) where SocialHash.fnv1a64(String(cs[i..<(i + length)])) == fnv { return true }
        return false
    }
}
