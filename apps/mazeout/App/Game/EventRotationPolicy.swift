import Foundation
import PathCore

// GAME G2 — B1 EVENTS-P (events.md §4.6; PLAN-P §4.4 B1 "compiled default off; all-on under uitest/capture"). How the app runs
// C3's weekly rotation (PathCore EventRotation):
//  - the shipped social.json turns it ON (`events.rotation.enabled`);
//  - under `-pc.uitest` / `-pc.capture` it is the v552 plan (every unlocked event every week, Up & Away never) unless the
//    run asks for the calendar with `-pc.socialScenario rotation…` (SPEC.md ruling 33's pattern: existing UI tests keep their
//    meaning and never go red every other week; the calendar is scoped out, no assertion is weakened). An explicit
//    `-pc.tune rules.events.rotation.enabled=…` always wins;
//  - RELEASE ART GATE (never ship stand-in content): Up & Away's art ids are the art lane's R8 requests. While they are not in
//    the generated UIArt table, a Release build treats Up & Away as unavailable — its weeks run Treasure Climb (the calendar
//    itself is unchanged; `EventRules.Rotation.unavailable`). DEBUG builds show the hatched DebugPlaceholder instead.
// Both economy tables of the app (AppModel.economy and ShellEconomy.rules) go through `tune` + `apply`, so they agree.

enum EventRotationPolicy {
    /// The `-pc.tune` pairs the app loads its tuning with: the launch arguments' own + the uitest/capture rule.
    static func tune(_ args: LaunchArgs) -> [String: String] {
        var t = args.tune
        let key = "rules.events.rotation.enabled"
        let scenario = args.raw["pc.socialScenario"] ?? ""
        if args.quietUI, t[key] == nil, !scenario.hasPrefix("rotation") { t[key] = "false" }
        return t
    }

    /// The build-dependent part (the Release art gate), applied after every `EconomyRules.load`.
    static func apply(_ r: inout EconomyRules) {
        #if DEBUG
        let debug = true
        #else
        let debug = false
        #endif
        if gate(debug: debug, ready: UpAwayArt.ready) { r.events.rotation.unavailable.insert(EventID.balloonRise.rawValue) }
    }

    /// Up & Away is held back: a Release build without its art (pure, tested).
    static func gate(debug: Bool, ready: Bool) -> Bool { !debug && !ready }
}

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
