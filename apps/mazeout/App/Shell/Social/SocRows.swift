import UIKit
import PathCore

// SOCIAL SOC2 (SPEC-ui §1.4 roles, §1.6.11 RankRow, §2.15.3-§2.15.5, §2.16; SPEC-social §3.3). The rows of the long social
// lists as the worker prepares them OFF the main thread: every label already shaped (`SocShaped`), every look decided, so the
// main thread only points layers at them. Geometry is in reference points of the 393-wide canvas (the list view scales it).

/// Which list a row belongs to (its content layout and text colours).
enum SocListKind: String, Sendable, CaseIterable {
    case world, country, weekly, streak
}

/// One prepared row.
struct SocRow: Sendable {
    let id: UInt64                      // the simulated player's id; the player's own row: UInt64.max (SocialEngine.meId)
    let rank: Int
    let isMe: Bool
    let look: SocRowLook
    let badge: UIArt?                   // the hexagon for ranks 1-3 (World / Country / Streak Race)
    let avatar: Int
    let name: String
    let value: Int                      // level (World / Country), score (Weekly), flags (Streak Race)
    let prize: Int                      // Streak Race coins for the rank (0 = no bowl)
    let rankText: SocShaped
    let nameText: SocShaped
    let captionText: SocShaped?
    let valueText: SocShaped
    let prizeText: SocShaped?

    /// The accessibility identifier (SPEC-ui §6 / arch §9.8).
    func identifier(_ kind: SocListKind) -> String {
        if kind == .streak { return "event.streakRace.row.\(rank)" }
        return isMe ? "leaderboard.me" : "leaderboard.row.\(rank)"
    }

    func sameContent(_ o: SocRow) -> Bool {
        id == o.id && rank == o.rank && value == o.value && look == o.look && avatar == o.avatar && name == o.name && prize == o.prize
    }
}

enum SocListItem: Sendable {
    case row(SocRow)
    case separator                      // "• • •" between the World top 100 and the player's window
}

/// What a list shows (one immutable snapshot).
struct SocListContent: Sendable {
    let kind: SocListKind
    let items: [SocListItem]
    let myRank: Int
    let total: Int
    let computedAt: SocialTime

    var meIndex: Int? {
        items.firstIndex { if case .row(let r) = $0 { return r.isMe }; return false }
    }
    var rows: [SocRow] { items.compactMap { if case .row(let r) = $0 { return r }; return nil } }

    static func empty(_ kind: SocListKind) -> SocListContent {
        SocListContent(kind: kind, items: [], myRank: 0, total: 0, computedAt: SocialTime(seconds: 0))
    }
}

/// The text roles of the rows (SPEC-ui §1.4, VERIFIED meta-013 / meta-018 / meta-045).
enum SocRowStyles {
    static func name(_ kind: SocListKind) -> SocStyle {
        switch kind {
        case .world, .country: return SocStyle(size: 23.6, tracking: -0.3, face: 0x05292B, maxWidth: 180)
        case .weekly: return SocStyle(size: 23.6, tracking: -0.3, face: 0x5A2801, maxWidth: 180)
        case .streak: return SocStyle(size: 23.6, tracking: -0.3, face: 0x5A2801, maxWidth: 130)
        }
    }
    static func rank(_ kind: SocListKind) -> SocStyle {
        switch kind {
        case .weekly, .streak: return SocStyle(size: 24.8, face: 0xF7E5C7, outline: 0x732517, width: 2.0, drop: 0.7, maxWidth: 44)
        case .world, .country: return SocStyle(size: 24.8, face: 0xFFFAEF, outline: 0x002226, width: 2.0, drop: 0.7, maxWidth: 44)
        }
    }
    /// The digit on a rank hexagon (≈ 20 pt white, outlined in the hexagon's dark shade; INFERRED).
    static func badgeDigit(_ rank: Int) -> SocStyle {
        let o: UInt32 = rank == 1 ? 0x985316 : rank == 2 ? 0x325653 : 0x8C2D18
        return SocStyle(size: 20, face: 0xFFFFFF, outline: o, width: 1.6, drop: 0.8)
    }
    static let caption = SocStyle(size: 15.3, tracking: -0.25, face: 0xA97630, maxWidth: 60)
    static let value = SocStyle(size: 26, tracking: -0.7, face: 0xF6E9D8, outline: 0x732517, width: 1.8, drop: 0.8, maxWidth: 52)
    /// The prize amount on the coin bowl's band (14.3 white outlined #660100).
    static let prize = SocStyle(size: 14.3, tracking: -0.2, face: 0xFFFFFF, outline: 0x620B00, width: 1.4, drop: 0.6, maxWidth: 46)
    /// The Streak Race score in its pill (16.4 cream-white outlined #622200, box 44).
    static let score = SocStyle(size: 16.4, tracking: -0.2, face: 0xFBF4E7, outline: 0x5A2801, width: 1.3, drop: 0.7, maxWidth: 44)
}

/// Builds rows (any thread).
enum SocRowBuilder {
    static func look(_ kind: SocListKind, rank: Int, isMe: Bool) -> SocRowLook {
        if isMe { return .me }
        if kind == .streak {
            switch rank { case 1: return .gold; case 2: return .silver; case 3: return .bronze; default: return .cream }
        }
        return .cream
    }

    static func badge(_ kind: SocListKind, rank: Int) -> UIArt? {
        guard kind != .weekly else { return nil }          // the Weekly list starts at rank 4 (the podium holds 1-3)
        switch rank { case 1: return .rankBadgeGold; case 2: return .rankBadgeSilver; case 3: return .rankBadgeBronze; default: return nil }
    }

    static func row(_ kind: SocListKind, rank: Int, player: SimPlayer, value: Int, isMe: Bool, prize: Int = 0,
                    caption: String?) -> SocRow {
        let badge = badge(kind, rank: rank)
        let rankText = badge != nil ? SocType.number(rank, SocRowStyles.badgeDigit(rank)) : SocType.number(rank, SocRowStyles.rank(kind))
        let name = player.name
        return SocRow(id: player.id, rank: rank, isMe: isMe, look: look(kind, rank: rank, isMe: isMe), badge: badge,
                      avatar: player.avatar, name: name, value: value, prize: prize,
                      rankText: rankText,
                      nameText: SocType.shape(name, SocRowStyles.name(kind)),
                      captionText: caption.map { SocType.shape($0, SocRowStyles.caption) },
                      valueText: kind == .streak ? SocType.number(value, SocRowStyles.score) : SocType.number(value, SocRowStyles.value),
                      prizeText: prize > 0 ? SocType.number(prize, SocRowStyles.prize) : nil)
    }
}
