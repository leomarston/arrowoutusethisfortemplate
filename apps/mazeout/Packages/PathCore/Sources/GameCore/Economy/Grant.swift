import Foundation

// C3 (SPEC-architecture §4.8; SPEC-gameplay §9, §11.2, §15). WP0 wrote the shape so ◆ EventTypes (EventOutcome) compiles;
// C3 owns the file from here. MF's Grant.swift is the model. Codable + Sendable + Equatable + Hashable: ◆ EventOutcome
// carries it. JSON shape = SPEC-gameplay §15: {"coins": 100} · {"boosters": {"hint": 1}} · {"unlimitedLives": 1800}.

/// What a purchase, a claim or an event reward gives: coins, boosters, unlimited lives (stacking, §4.8).
public struct Grant: Codable, Sendable, Equatable, Hashable {
    public var coins: Int
    public var boosters: [String: Int]               // BoosterID.rawValue → count
    public var unlimitedLives: TimeInterval          // seconds (0 = none); stacks: until = max(until, now) + duration

    public init(coins: Int = 0, boosters: [String: Int] = [:], unlimitedLives: TimeInterval = 0) {
        self.coins = coins; self.boosters = boosters; self.unlimitedLives = unlimitedLives
    }

    enum CodingKeys: String, CodingKey { case coins, boosters, unlimitedLives }

    /// Tolerant: every key is optional.
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        coins = try c.decodeIfPresent(Int.self, forKey: .coins) ?? 0
        boosters = try c.decodeIfPresent([String: Int].self, forKey: .boosters) ?? [:]
        unlimitedLives = try c.decodeIfPresent(TimeInterval.self, forKey: .unlimitedLives) ?? 0
    }

    /// Writes only the non-empty parts, so a Grant round-trips to the §15 shape ({"coins": 100}, not three keys).
    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        if coins != 0 { try c.encode(coins, forKey: .coins) }
        let b = boosters.filter { $0.value != 0 }
        if !b.isEmpty { try c.encode(b, forKey: .boosters) }
        if unlimitedLives != 0 { try c.encode(unlimitedLives, forKey: .unlimitedLives) }
    }

    // MARK: helpers

    public static let none = Grant()
    public static func coins(_ n: Int) -> Grant { Grant(coins: n) }
    public static func booster(_ b: BoosterID, _ n: Int) -> Grant { Grant(boosters: [b.rawValue: n]) }
    public static func unlimited(_ seconds: TimeInterval) -> Grant { Grant(unlimitedLives: seconds) }

    /// Nothing to give (no coins, no booster count, no unlimited time).
    public var isEmpty: Bool { coins == 0 && unlimitedLives == 0 && boosters.values.allSatisfy { $0 == 0 } }

    /// Both grants together (claims that pay coins AND unlimited lives, e.g. the Rocket Race stage prizes).
    public static func + (a: Grant, b: Grant) -> Grant {
        Grant(coins: a.coins + b.coins, boosters: a.boosters.merging(b.boosters, uniquingKeysWith: +),
              unlimitedLives: a.unlimitedLives + b.unlimitedLives)
    }
}
