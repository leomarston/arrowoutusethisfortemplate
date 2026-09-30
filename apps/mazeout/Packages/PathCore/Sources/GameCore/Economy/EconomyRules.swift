import Foundation

// C3 (SPEC-architecture §4.8–§4.10; SPEC-gameplay §6, §8, §9, §11, §15). Every economy / lives / booster-purchase / shop /
// Claw / streak / event value as DATA: compiled defaults here (= SPEC-gameplay §15 and SPEC-social §12), overridable by
//   - `bundle/Tuning/rules.json` sections `economy`, `lives`, `streak`, `claw`, `shop` (SPEC-gameplay §0.2, §15: "C3's
//     EconomyRules decodes them"; the other rules.json sections are C2's RulesTuning and are ignored here), and
//   - `bundle/Tuning/social.json` sections `unlocks` (SPEC-gameplay §15) and `events` (C3's layout of SPEC-social §4/§12 values,
//     proposed to SOC1 — see `EventRules`).
// Decoding is tolerant (a missing key keeps its default, an unknown key is ignored and listed by `unknownKeys`), so a tuning
// edit never crashes the app. Nothing in the C3 logic hard-codes a number: it reads these structs.
//
// Tags: VERIFIED (source) · INFERRED · DECISION · PENDING-<spec>.

public struct EconomyRules: Codable, Sendable, Equatable {

    // MARK: economy (rules.json "economy")

    public struct BoosterPack: Codable, Sendable, Equatable {
        /// Boosters per purchase at 0 stock. DECISION SPEC-gameplay §6.4 ("Buy ×3").
        public var count: Int = 3
        /// Coins per pack. DECISION SPEC-gameplay §6.4 (900 = the original's single coin sink).
        public var price: Int = 900
        public init() {}
        public init(count: Int, price: Int) { self.count = count; self.price = price }
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = BoosterPack()
            count = try c.v(.count, d.count); price = try c.v(.price, d.price)
        }
    }

    public struct EconomySection: Codable, Sendable, Equatable {
        /// Coins at install. VERIFIED vflows §8 (1000 + 80 + 6 × 20 = 1200 at L11 in both videos; the first home 1000 → 1120).
        public var startCoins: Int = 1000
        /// Booster stock at install. VERIFIED badges "3" from L1-4 in both videos and the phone kickoff (SPEC-gameplay §6).
        public var startBoosters: [String: Int] = ["freeze": 3, "hint": 3]
        public var boosterPack = BoosterPack()
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = EconomySection()
            startCoins = try c.v(.startCoins, d.startCoins)
            startBoosters = try c.v(.startBoosters, d.startBoosters)
            boosterPack = try c.v(.boosterPack, d.boosterPack)
        }
    }

    // MARK: lives (rules.json "lives")

    /// When a level costs its life. VERIFIED `atStart` (research/fail.md §6, economy.md §2: taken at the level start, given
    /// back on a win); `atLoss` is the architecture's first placeholder (§4.8 table), kept as a switch.
    public enum LifeCost: String, Codable, Sendable, CaseIterable { case atStart, atLoss }

    public struct Lives: Codable, Sendable, Equatable {
        /// VERIFIED (economy.md §2, meta §6).
        public var max: Int = 5
        /// One life per 30:00 on one continuous clock. VERIFIED economy.md §2b (the tick landed on the predicted second).
        public var refillSeconds: Double = 1800
        /// "Refill [coin] 900" on More Lives (lives to max). VERIFIED meta §6.
        public var refillPrice: Int = 900
        /// An attempt killed mid-level is a failed attempt at the next launch. DECISION SPEC-gameplay §8.5.
        public var killIsLoss: Bool = true
        /// C3 knob (not in §15): when a level costs its life. VERIFIED `atStart`.
        public var cost: LifeCost = .atStart
        /// Floating slack when counting whole refill periods (a life due at exactly +1800 s is never missed).
        public var refillEpsilon: Double = 1e-6
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Lives()
            max = try c.v(.max, d.max)
            refillSeconds = try c.v(.refillSeconds, d.refillSeconds)
            refillPrice = try c.v(.refillPrice, d.refillPrice)
            killIsLoss = try c.v(.killIsLoss, d.killIsLoss)
            cost = try c.v(.cost, d.cost)
            refillEpsilon = try c.v(.refillEpsilon, d.refillEpsilon)
        }
    }

    // MARK: streak (rules.json "streak")

    public struct Streak: Codable, Sendable, Equatable {
        /// The x1 x5 x10 x25 x100 chips; the last one stays. VERIFIED flows, economy §5, levels L32–L61.
        public var steps: [Int] = [1, 5, 10, 25, 100]
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Streak()
            steps = try c.v(.steps, d.steps)
            if steps.isEmpty { steps = d.steps }
        }
    }

    // MARK: claw (rules.json "claw")

    public struct ClawStep: Codable, Sendable, Equatable {
        public var threshold: Int
        public var grant: Grant
        public init(_ threshold: Int, _ grant: Grant) { self.threshold = threshold; self.grant = grant }
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self)
            threshold = try c.v(.threshold, 1)
            grant = try c.v(.grant, Grant())
        }
    }

    public struct Claw: Codable, Sendable, Equatable {
        /// "week" (ends Monday 07:00 UTC, SPEC-social D2) or "day".
        public var period: String = "week"
        /// SPEC-gameplay §11.2: steps 1–7 VERIFIED (thresholds 1/200/300/400/300/500/500, rewards from the phone), rewards
        /// 8–20 VERIFIED from the ladder art, thresholds 8–20 DECISION.
        public var ladder: [ClawStep] = Claw.defaultLadder
        public init() {}
        public init(from decoder: Decoder) throws {
            let c = try decoder.container(keyedBy: CodingKeys.self); let d = Claw()
            period = try c.v(.period, d.period)
            ladder = try c.v(.ladder, d.ladder)
        }

        public static let defaultLadder: [ClawStep] = {
            let inf = { (h: Double) in Grant(unlimitedLives: h * 3600) }
            return [
                ClawStep(1, inf(0.5)), ClawStep(200, .coins(100)), ClawStep(300, inf(0.5)), ClawStep(400, .coins(200)),
                ClawStep(300, inf(1)), ClawStep(500, .booster(.hint, 1)), ClawStep(500, .coins(300)), ClawStep(600, inf(2)),
                ClawStep(600, .coins(400)), ClawStep(700, inf(3)), ClawStep(700, .booster(.freeze, 2)), ClawStep(800, inf(4)),
                ClawStep(800, .booster(.hint, 2)), ClawStep(1000, .coins(2000)), ClawStep(900, inf(5)), ClawStep(1000, .coins(500)),
                ClawStep(1000, .booster(.hint, 1)), ClawStep(1100, .coins(600)), ClawStep(1200, inf(6)), ClawStep(1500, .coins(10000)),
            ]
        }()
    }

    // MARK: the table

    public var economy = EconomySection()
    public var lives = Lives()
    public var streak = Streak()
    public var claw = Claw()
    public var shop = ShopCatalog()
    /// The events' own values (unlock levels, calendar, prizes, stages): social.json (`EventRules.load`).
    public var events = EventRules()

    public init() {}
    public static let `default` = EconomyRules()

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self); let d = EconomyRules()
        economy = try c.v(.economy, d.economy)
        lives = try c.v(.lives, d.lives)
        streak = try c.v(.streak, d.streak)
        claw = try c.v(.claw, d.claw)
        shop = try c.v(.shop, d.shop)
        events = try c.v(.events, d.events)
    }

    // MARK: derived

    /// The booster table of SPEC-architecture §4.9 from this table (stock, pack price) and C2's session actions
    /// (`MetaRules.boosters` = rules.json `boosters`, read by the puzzle's `RulesTuning.boosters` too: the freeze seconds and
    /// hint units are C2's knobs; one source of truth).
    public func boosterRules(_ session: MetaRules.Boosters = MetaRules.default.boosters) -> [BoosterRule] {
        let ids = Set(economy.startBoosters.keys).union(session.actions.keys).sorted()
        return ids.map { id in
            let effect: BoosterEffect
            switch session.action(BoosterID(id)) {
            case .freezeTimer: effect = .freezeTimer(seconds: session.freezeSeconds)
            case .hint: effect = .hint(units: session.hintUnits)
            case .none: effect = .custom(id)
            }
            return BoosterRule(id: BoosterID(id), effect: effect, startStock: economy.startBoosters[id] ?? 0,
                               price: economy.boosterPack.price, packCount: economy.boosterPack.count, unlockLevel: nil)
        }
    }

    // MARK: loading

    /// The rules.json sections this table decodes (SPEC-gameplay §15).
    public static let rulesSections = ["economy", "lives", "streak", "claw", "shop"]

    /// Decodes the C3 sections of `rules` (rules.json) and the event sections of `social` (social.json; see
    /// `EventRules.load`), then applies dotted overrides (`"lives.refillSeconds": "60"` — the `-pc.tune rules.<key>=v` pairs
    /// without the "rules." prefix; `"events.unlocks.skyJump": "5"` reaches the event table). Never throws: a broken file or
    /// value falls back to the defaults and is reported in `problems`.
    public static func load(rules: Data?, social: Data? = nil, overrides: [String: String] = [:])
        -> (rules: EconomyRules, problems: [String]) {
        var problems: [String] = []
        var obj: [String: Any] = [:]
        if let rules, !rules.isEmpty {
            if let o = (try? JSONSerialization.jsonObject(with: rules)) as? [String: Any] {
                for k in rulesSections { if let v = o[k] { obj[k] = v } }
            } else {
                problems.append("rules.json is not a JSON object: economy defaults apply")
            }
        }
        let (ev, evProblems) = EventRules.load(social: social)
        problems += evProblems
        do { obj["events"] = try JSONSerialization.jsonObject(with: JSONEncoder().encode(ev)) } catch {
            problems.append("event rules do not encode: \(error)")
        }
        for (key, raw) in overrides.sorted(by: { $0.key < $1.key }) {
            let parts = key.split(separator: ".").map(String.init)
            guard let head = parts.first, rulesSections.contains(head) || head == "events" else { continue }
            obj = TuningJSON.setPath(obj, parts[...], TuningJSON.overrideValue(raw))
        }
        do {
            let data = try JSONSerialization.data(withJSONObject: obj)
            return (try JSONDecoder().decode(EconomyRules.self, from: data), problems)
        } catch {
            problems.append("economy rules do not decode: \(error)")
            return (EconomyRules(), problems)
        }
    }

    /// Keys inside the C3 sections of `rules` (rules.json) that this table does not know (reported, never applied).
    public static func unknownKeys(in rules: Data) -> [String] {
        guard let over = (try? JSONSerialization.jsonObject(with: rules)) as? [String: Any],
              let base = (try? JSONSerialization.jsonObject(with: JSONEncoder().encode(EconomyRules()))) as? [String: Any]
        else { return [] }
        var out: [String] = []
        func walk(_ o: [String: Any], _ b: [String: Any], _ path: String) {
            for (k, v) in o where !k.hasPrefix("_") {
                guard let bv = b[k] else { out.append(path + k); continue }
                // open maps keyed by data (booster ids) and lists: do not descend
                if k == "startBoosters" || k == "ladder" || k == "products" { continue }
                if let ov = v as? [String: Any], let bo = bv as? [String: Any] { walk(ov, bo, path + k + ".") }
            }
        }
        for k in rulesSections {
            guard let o = over[k] else { continue }
            guard let ob = o as? [String: Any], let bb = base[k] as? [String: Any] else { continue }
            walk(ob, bb, k + ".")
        }
        return out.sorted()
    }
}
