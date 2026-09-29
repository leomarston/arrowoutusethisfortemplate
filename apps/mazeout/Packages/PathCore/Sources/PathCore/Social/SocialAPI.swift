import Foundation

// ◆ CONTRACT (SPEC-architecture §3.5, §4.11, D10). Written by the LEAD in WP0 and FROZEN: any change goes through the
// orchestrator (build/wp0/frozen-contracts.sha256 + APISurfaceTests).
//
// The public face of the offline world simulation. The MODEL is SPEC-social's and SOC1's: every body below delegates to
// SOC1's internal types (`SocialEngine` in Social/Leaderboards.swift, `SocialClockRules` in Social/SocialClock.swift),
// so SOC1 implements the world without touching this file. `SocialConfig`, `NameBank`, `LedgerEntry` and `SocialState`
// are SOC1's types too. Invariants (binding for SOC1): deterministic from (installSeed, SocialTime, the player's ledger),
// stateless O(1) evaluation, bit-exact with design/social/tools/socialsim, rewind-safe clock (§4.11 items 1-7).

/// Effective epoch seconds of the world clock (never earlier than any time already shown, §4.11 item 5).
public struct SocialTime: Hashable, Comparable, Codable, Sendable {
    public let seconds: Int64
    public init(seconds: Int64) { self.seconds = seconds }
    public static func < (a: SocialTime, b: SocialTime) -> Bool { a.seconds < b.seconds }
}

public enum LeaderboardKind: Hashable, Codable, Sendable {
    case weekly(week: Int)                   // week index since the calendar epoch
    case world
    case country(String)                     // ISO 3166 alpha-2
}

/// A simulated (or the real) player as the screens show them.
public struct SimPlayer: Hashable, Codable, Sendable {
    public var id: UInt64
    public var name: String
    public var country: String               // ISO 3166 alpha-2
    public var avatar: Int                   // 0 = default silhouette

    public init(id: UInt64, name: String, country: String, avatar: Int) {
        self.id = id; self.name = name; self.country = country; self.avatar = avatar
    }
}

public struct LeaderboardRow: Hashable, Codable, Sendable {
    public var rank: Int
    public var player: SimPlayer
    public var value: Int                    // level (World / Country) or score (Weekly)
    public var isMe: Bool

    public init(rank: Int, player: SimPlayer, value: Int, isMe: Bool) {
        self.rank = rank; self.player = player; self.value = value; self.isMe = isMe
    }
}

public struct LeaderboardPage: Codable, Sendable {
    public var rows: [LeaderboardRow]
    public var myRank: Int
    public var total: Int

    public init(rows: [LeaderboardRow], myRank: Int, total: Int) {
        self.rows = rows; self.myRank = myRank; self.total = total
    }
}

/// The real player, as the world needs them.
public struct PlayerStanding: Codable, Sendable {
    public var name: String
    public var avatar: Int
    public var country: String
    public var level: Int
    public var ledger: [LedgerEntry]

    public init(name: String, avatar: Int, country: String, level: Int, ledger: [LedgerEntry]) {
        self.name = name; self.avatar = avatar; self.country = country; self.level = level; self.ledger = ledger
    }
}

/// The world. Immutable after init; safe to query from any thread (pages > 50 rows are computed off the main thread).
public final class SocialWorld: RivalProvider, @unchecked Sendable {
    let engine: SocialEngine

    public init(installSeed: UInt64, config: SocialConfig, names: NameBank) {
        engine = SocialEngine(installSeed: installSeed, config: config, names: names)
    }

    /// Rows `ranks` (1-based, inclusive) of a board, with the player merged in at their rank.
    public func page(_ kind: LeaderboardKind, me: PlayerStanding, at: SocialTime, ranks: ClosedRange<Int>) -> LeaderboardPage {
        engine.page(kind, me: me, at: at, ranks: ranks)
    }

    /// `radius` rows either side of rank `around` (Country opens scrolled to the player's row).
    public func page(_ kind: LeaderboardKind, me: PlayerStanding, at: SocialTime, around: Int, radius: Int) -> LeaderboardPage {
        engine.page(kind, me: me, at: at, around: around, radius: radius)
    }

    /// The Weekly Contest podium of `week`: 3 rows (prizes 2000 / 1000 / 500, VERIFIED flows).
    public func weeklyPodium(week: Int, at: SocialTime) -> [LeaderboardRow] {
        engine.weeklyPodium(week: week, at: at)
    }

    public func player(_ id: UInt64) -> SimPlayer { engine.player(id) }

    // MARK: RivalProvider (§4.10)

    public func streakRace(_ instance: EventInstance, player: PlayerStanding, at: SocialTime) -> [RaceStanding] {
        engine.streakRace(instance, player: player, at: at)
    }

    public func rocketRace(_ instance: EventInstance, joinedAt: SocialTime, at: SocialTime) -> [RaceStanding] {
        engine.rocketRace(instance, joinedAt: joinedAt, at: at)
    }

    public func skyJump(_ run: SkyJumpRun, at: SocialTime) -> SkyJumpField {
        engine.skyJump(run, at: at)
    }
}

/// The rewind-safe world clock: `max(wall, highWater)`, and it raises `highWater` (PlayerState.social.highWater).
/// Setting the device clock back freezes the world until wall time catches up (§4.11 item 5).
public enum SocialClock {
    public static func now(wall: Date, highWater: inout Int64) -> SocialTime {
        SocialClockRules.now(wall: wall, highWater: &highWater)
    }
}
