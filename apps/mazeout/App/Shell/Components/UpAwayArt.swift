import SwiftUI

// Up & Away's art slots and their image view (kit decoupling step, docs/ROADMAP.md). Moved as they were: `UpAwayArt` from
// Game/EventRotationPolicy.swift, `UpAwayArtImage` from Social/BalloonViews.swift. Core (the skin runtime's slot table): the
// rotation policy (core), the social model's preload list, the event announcements, the Profile's "Up & Away Best Streak" stat
// and the balloon-rise component all name these slots, so they cannot live in any one of them.
// (FixTwoATests scans the App sources for `UpAwayArt.<name>` draws: this file only declares them.)

/// Up & Away's art (events.md §7.1; the art lane's R8 requests, `build/p/B1/art-requests.md` is not written: the ids are in
/// B1's report). Referenced by raw value = the art SLOT id (skin/art.json; `tools/skin/art.py --check` fails on one the skin
/// lacks): the Release gate stays shut for a skin that does not map them.
/// A4 ART-INTEG (R8 EVENT-ART, art/lanes/events-d1.handoff.json "upaway"): R8 shipped the tall page as PIECES instead of one
/// backdrop (≈ 21 MB decoded against 53 MB for a 393 × 3 794 pt bitmap) — the tower's top, a shaft tile that repeats every
/// 340 pt, its foot with the launch pad, and a ledge per platform — so `backdrop` is gone and the gate waits for the pieces.
enum UpAwayArt {
    /// The home bar's token (a hot-air balloon on the badge frame; the bar's left end; its rig is `badge_upaway_rig`).
    static let badge = "event.balloonRise.badge"
    /// The page's balloon with its basket and a crew member (the rising / falling hero; also the win-panel strip's rider).
    static let hero = "event.balloonRise.hero"
    /// The page's tower: the observatory top (393 × 470 at y 0), the masonry shaft tile (112 × 340, every 340 pt), the foot
    /// with the launch pad and the town (393 × 700 at the bottom), a ledge per platform (240 × 150).
    static let towerTop = "event.balloonRise.towerTop"
    static let towerShaft = "event.balloonRise.towerShaft"
    static let towerFoot = "event.balloonRise.towerFoot"
    static let ledge = "event.balloonRise.ledge"
    static let ids = [badge, hero, towerTop, towerShaft, towerFoot, ledge]

    /// Every requested slot exists in the generated table.
    static var ready: Bool { ids.allSatisfy { UIArt(rawValue: $0) != nil } }
    static func art(_ id: String) -> UIArt? { UIArt(rawValue: id) }
}

/// A requested art id: the file when it exists, else (DEBUG only) the hatched placeholder; Release draws nothing.
struct UpAwayArtImage: View {
    let id: String
    var contentMode: ContentMode = .fit
    var body: some View {
        if let a = UpAwayArt.art(id) {
            ArtImage(art: a, contentMode: contentMode)
        } else {
            #if DEBUG
            DebugPlaceholder(name: id)
            #else
            Color.clear
            #endif
        }
    }
}
