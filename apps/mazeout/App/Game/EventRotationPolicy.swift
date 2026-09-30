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
