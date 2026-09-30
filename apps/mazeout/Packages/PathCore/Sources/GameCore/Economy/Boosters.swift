import Foundation

// C3 (SPEC-architecture §4.9; SPEC-gameplay §6). The booster table: what each booster does, its start stock, its price at
// 0 stock. The session hook (`LevelSession.useBooster`) is C2's and never touches stock; GAME checks and decrements
// `PlayerState.boosters` through `Economy.useBooster` / `Economy.buyBooster` (MF rule).
// v552 has two (VERIFIED research/boosters.md, ORCH 10): left hourglass `freeze` (timer frozen 1.5 s flight + 10 s), right
// bulb `hint` (one free unit highlighted). Both start at 3, no unlock level, never sold alone in the shop (VERIFIED); at 0
// stock a "Buy ×3 for 900" popup (DECISION SPEC-gameplay §6.4). The videos' two extra boosters are admitted as `custom`.

public enum BoosterEffect: Codable, Sendable, Equatable {
    case freezeTimer(seconds: Double)
    case hint(units: Int)
    case custom(String)
}

public struct BoosterRule: Codable, Sendable, Equatable {
    public var id: BoosterID
    public var effect: BoosterEffect
    /// Stock at install (`rules.json:economy.startBoosters`).
    public var startStock: Int
    /// Coins for one pack at 0 stock (`economy.boosterPack.price`); nil = not for sale.
    public var price: Int?
    /// Boosters per pack (`economy.boosterPack.count`).
    public var packCount: Int
    /// The level the booster appears at; nil = from the first board (VERIFIED: no booster unlock anywhere).
    public var unlockLevel: Int?

    public init(id: BoosterID, effect: BoosterEffect, startStock: Int, price: Int?, packCount: Int = 3, unlockLevel: Int? = nil) {
        self.id = id; self.effect = effect; self.startStock = startStock; self.price = price; self.packCount = packCount
        self.unlockLevel = unlockLevel
    }
}

extension Economy {
    /// The booster's stock (0 when never granted).
    public static func stock(_ s: PlayerState, _ b: BoosterID) -> Int { max(0, s.boosters[b.rawValue] ?? 0) }
}
