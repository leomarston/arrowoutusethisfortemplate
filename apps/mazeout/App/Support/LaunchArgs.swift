import Foundation
import PathCore

// ◆ CONTRACT (SPEC-architecture §3.5, §9.1, §9.2, D21). Written by the LEAD in WP0 and FROZEN: any change goes through
// the orchestrator (build/wp0/frozen-contracts.sha256).
// Every test hook is a launch argument `-pc.<name> <value>`, read ONCE at launch (the same pairs the UserDefaults
// argument domain sees; never persisted). They exist in every build configuration; the Release build with no argument
// boots to the real first-run state. A flag with no value (last, or followed by another `-pc.` flag) reads as "1";
// a negative number is a value (`-pc.clockOffset -3600`). Always launch with --terminate-running-process (tools/run.sh):
// simctl drops the arguments of an app that is already running.
// Owners who need a private flag read it from `raw` (`args.raw["pc.myFlag"]`) instead of changing this file.

struct LaunchArgs: Equatable {
    enum GoTarget: Equatable {
        case home, level, shop, profile, settings
        case leaderboard(String?)            // leaderboard[:weekly|world|country]
        case event(String)                   // event:<claw|streakRace|rocketRace|skyJump>
        case lab(String)                     // boardlab | shelllab | soundboard | sociallab (any owner's debug screen)
    }
    /// `-pc.popup <id>[:variant]`, e.g. "continue:life" → (continue, life), "boosterBuy:hint" → (boosterBuy, hint).
    struct PopupArg: Equatable { var id: String; var variant: String? }
    enum SkipForce: String, Equatable { case skip, force }
    enum Trail: String, Equatable { case solid, rainbow, ladder }
    /// `-pc.freezeAt <sequence>@<t>`: board intro, exit, bump, keyFlight, doorBurst, pipeBreak, boxBreak, clearWave,
    /// stageGap; shell hudIntro, win, unlock, coinFly, caption (§5.12).
    struct FreezeAt: Equatable { var sequence: String; var t: Double }

    /// Every `-pc.*` pair as given, keyed without the dash ("pc.reset" → "1").
    var raw: [String: String] = [:]

    // state (§9.1)
    var reset = false                          // -pc.reset 1: fresh install (wipe PlayerState + backup before boot)
    var state: String?                         // -pc.state <path | base64 JSON>
    var level: Int?                            // -pc.level N (marks home seen when N ≥ 7)
    var stage: Int?                            // -pc.stage K: start a multi-board session at stage K
    var go: GoTarget?                          // -pc.go …
    var popup: PopupArg?                       // -pc.popup <id>[:variant]
    var seed: UInt64?                          // -pc.seed N: fixed install seed
    var coins: Int?                            // -pc.coins N
    var lives: Int?                            // -pc.lives N
    var livesNextIn: Double?                   // -pc.livesNextIn S: seconds until the next life
    var unlimitedLives: Double?                // -pc.unlimitedLives S
    var boosters: [String: Int] = [:]          // -pc.boosters freeze=3,hint=0
    var tutorials: SkipForce?                  // -pc.tutorials skip|force
    var unlocks: SkipForce?                    // -pc.unlocks skip|force
    // clock
    var now: Date?                             // -pc.now <ISO-8601>
    var clockOffset: Double?                   // -pc.clockOffset ±S
    var clockRate: Double?                     // -pc.clockRate K
    // level timer / hearts
    var timer: Double?                         // -pc.timer S: remaining seconds at the first tap
    var freezeTimer = false                    // -pc.freezeTimer 1: keep the timer frozen
    var timerRuns = false                      // -pc.timerRuns 1: let it run in capture mode
    var hearts: Int?                           // -pc.hearts N: hearts at stage start
    // outcomes
    var win: LevelTag?                         // -pc.win normal|hard|superHard
    var lose: LossReason?                      // -pc.lose timeUp|hearts|quit
    // bot
    var autoplay = false                       // -pc.autoplay 1
    var autoplayRate: Double?                  // -pc.autoplayRate S (default: game.json autoplay.rate)
    var autoplayStop: Int?                     // -pc.autoplayStop N
    var autoplayMistakes: Double?              // -pc.autoplayMistakes p
    // engine switches
    var trail: Trail?                          // -pc.trail solid|rainbow|ladder
    var zoom: Double?                          // -pc.zoom Z (start zoom for labs / captures)
    var tune: [String: String] = [:]           // -pc.tune file.key=v,… ("board.zoom.min=0.8")
    // labs, capture, tests
    var lab: String?                           // -pc.lab <scenario | page>
    var labBoard: String?                      // -pc.labBoard synth40|L032|…
    var slowmo: Double?                        // -pc.slowmo N: timeScale = 1/N
    var freezeAt: FreezeAt?                    // -pc.freezeAt <sequence>@<t>
    var capture = false                        // -pc.capture 1 (§9.2)
    var probeFile = false                      // -pc.probeFile 1: also write Documents/probe.json
    var uitest = false                         // -pc.uitest 1: exposes board.probe; hints, auto-popups, prompts off
    var hud: String?                           // -pc.hud debug
    var bench = false                          // -pc.bench 1: Documents/bench-L<n>-<ts>.json at each level end
    var fakeStore = false                      // -pc.fakeStore 1
    var rating = false                         // -pc.rating 1: allow the rating prompt under uitest / capture
    var notif = false                          // -pc.notif 1: allow the notification prompt under uitest / capture

    /// Capture mode's fixed clock (§9.2).
    static let captureDate: Date = ISO8601DateFormatter().date(from: "2026-09-25T12:00:00Z")!

    // MARK: derived (§9.2)

    /// Install seed override: `-pc.seed`, or 1 in capture mode.
    var effectiveSeed: UInt64? { seed ?? (capture ? 1 : nil) }
    /// 1 normally, 1/N with `-pc.slowmo N`.
    var timeScale: Double { slowmo.map { 1 / max($0, 0.001) } ?? 1 }
    /// Where the wall clock starts: `-pc.now`, the capture date in capture mode, nil = the real clock.
    var clockStart: Date? { now ?? (capture ? Self.captureDate : nil) }
    /// How fast the wall clock runs from `clockStart`: `-pc.clockRate`, else 0 (fixed) in capture mode, else 1.
    var effectiveClockRate: Double { clockRate ?? (capture ? 0 : 1) }
    /// Tests and captures: no hints, auto-popups or system prompts unless forced.
    var quietUI: Bool { uitest || capture }
    var ratingPromptAllowed: Bool { !quietUI || rating }
    var notificationPromptAllowed: Bool { !quietUI || notif }
    /// Capture mode: audio muted, no random pitch, the debug overlay hidden, the level timer held unless -pc.timerRuns 1.
    var audioMuted: Bool { capture }
    var showsDebugHUD: Bool { hud == "debug" && !capture }
    var holdsTimerForCapture: Bool { capture && !timerRuns }
    var exposesProbe: Bool { uitest || probeFile }

    // MARK: parsing

    init() {}

    /// Parses `["-pc.reset", "1", "-pc.go", "home", …]`; anything that is not a `-pc.` pair is ignored.
    init(arguments: [String]) {
        var pairs: [String: String] = [:]
        var i = 0
        while i < arguments.count {
            let a = arguments[i]
            if a.hasPrefix("-pc.") {
                let key = String(a.dropFirst())
                if i + 1 < arguments.count, !arguments[i + 1].hasPrefix("-pc.") {
                    pairs[key] = arguments[i + 1]
                    i += 2
                    continue
                }
                pairs[key] = "1"
            }
            i += 1
        }
        self.init(pairs: pairs)
    }

    init(pairs: [String: String]) {
        raw = pairs
        func s(_ k: String) -> String? { pairs["pc." + k].flatMap { $0.isEmpty ? nil : $0 } }
        func b(_ k: String) -> Bool { s(k).map { ["1", "true", "yes", "on"].contains($0.lowercased()) } ?? false }
        func i(_ k: String) -> Int? { s(k).flatMap { Int($0) } }
        func d(_ k: String) -> Double? { s(k).flatMap { Double($0) } }
        func list(_ k: String) -> [String] {
            (s(k) ?? "").split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
        }

        reset = b("reset")
        state = s("state")
        level = i("level")
        stage = i("stage")
        if let g = s("go") {
            let parts = g.split(separator: ":", maxSplits: 1).map(String.init)
            let sub = parts.count > 1 ? parts[1] : nil
            switch parts[0] {
            case "home": go = .home
            case "level": go = .level
            case "shop": go = .shop
            case "profile": go = .profile
            case "settings": go = .settings
            case "leaderboard": go = .leaderboard(sub)
            case "event": go = .event(sub ?? "")
            default: go = .lab(g)
            }
        }
        if let p = s("popup") {
            let parts = p.split(separator: ":", maxSplits: 1).map(String.init)
            popup = PopupArg(id: parts[0], variant: parts.count > 1 ? parts[1] : nil)
        }
        seed = s("seed").flatMap { UInt64($0) }
        coins = i("coins")
        lives = i("lives")
        livesNextIn = d("livesNextIn")
        unlimitedLives = d("unlimitedLives")
        for item in list("boosters") {
            let kv = item.split(separator: "=").map(String.init)
            if kv.count == 2, let n = Int(kv[1]) { boosters[kv[0]] = n }
        }
        tutorials = s("tutorials").flatMap(SkipForce.init(rawValue:))
        unlocks = s("unlocks").flatMap(SkipForce.init(rawValue:))
        now = s("now").flatMap { ISO8601DateFormatter().date(from: $0) }
        clockOffset = d("clockOffset")
        clockRate = d("clockRate")
        timer = d("timer")
        freezeTimer = b("freezeTimer")
        timerRuns = b("timerRuns")
        hearts = i("hearts")
        win = s("win").flatMap { LevelTag(label: $0) }
        lose = s("lose").flatMap(LossReason.init(rawValue:))
        autoplay = b("autoplay")
        autoplayRate = d("autoplayRate")
        autoplayStop = i("autoplayStop")
        autoplayMistakes = d("autoplayMistakes")
        trail = s("trail").flatMap(Trail.init(rawValue:))
        zoom = d("zoom")
        for item in list("tune") {
            let kv = item.split(separator: "=", maxSplits: 1).map(String.init)
            if kv.count == 2 { tune[kv[0]] = kv[1] }
        }
        lab = s("lab")
        labBoard = s("labBoard")
        slowmo = d("slowmo")
        if let f = s("freezeAt") {
            let parts = f.split(separator: "@").map(String.init)
            if parts.count == 2, let t = Double(parts[1]) { freezeAt = FreezeAt(sequence: parts[0], t: t) }
        }
        capture = b("capture")
        probeFile = b("probeFile")
        uitest = b("uitest")
        hud = s("hud")
        bench = b("bench")
        fakeStore = b("fakeStore")
        rating = b("rating")
        notif = b("notif")
    }

    /// This process's arguments.
    static let current = LaunchArgs(arguments: CommandLine.arguments)
}
