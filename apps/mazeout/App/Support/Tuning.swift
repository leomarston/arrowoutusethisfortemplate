import Foundation
import PathCore

// ◆ CONTRACT (SPEC-architecture §3.3, §3.4 rule 4, §3.5, §14). Written by the LEAD in WP0 and FROZEN: any change goes
// through the orchestrator (build/wp0/frozen-contracts.sha256).
// One JSON file per owner, `bundle/Tuning/<name>.json`: board (BOARD), game (GAME), ui (SHELL), audio (AUDIO),
// rules (CORE C2: decoded into PathCore's RulesTuning), social (SOCIAL: decoded into PathCore's SocialConfig).
// The values the content specs have not written yet (PENDING-<spec>, §14) are DATA here: each JSON file carries the
// §-cited default and the compiled defaults below are only the fallback, so a missing key or file never crashes.
// `-pc.tune file.key=v,…` overrides any key (`-pc.tune board.zoom.min=0.8,ui.dim.popup=0.85`); list values in an
// override are separated by ';'.
// Owners add knobs WITHOUT touching this file: the key goes in their JSON and is read from an extension in their own
// file, e.g. `extension BoardTuning { var starCount: Int { file.int("stars.count", 6) } }`.

/// One parsed tuning JSON with dotted-path lookup ("zoom.min") and string overrides.
struct TuningFile: @unchecked Sendable {          // immutable after init; JSON values are plist types
    let name: String
    let json: [String: Any]
    let data: Data?                               // the raw file, for Codable decoding (rules, social)
    let overrides: [String: String]               // keys without the file prefix
    /// FIX-2 A: a process-unique number per loaded file — the key of the read memos (`Tokens.text`, colours): a file never
    /// changes after init, so a memo keyed by it can never serve another file's (a test's `-pc.tune`) values.
    let identity: Int

    private static let idLock = NSLock()
    nonisolated(unsafe) private static var nextIdentity = 1

    init(name: String, json: [String: Any], data: Data? = nil, overrides: [String: String] = [:]) {
        self.name = name; self.json = json; self.data = data; self.overrides = overrides
        Self.idLock.lock()
        identity = Self.nextIdentity
        Self.nextIdentity += 1
        Self.idLock.unlock()
    }

    /// Reads `<bundle>/Tuning/<name>.json`; missing or malformed → empty (the compiled defaults apply). Overrides come
    /// from the `-pc.tune` pairs whose key starts with "<name>.".
    static func load(_ name: String, bundle: Bundle, tune: [String: String]) -> TuningFile {
        var json: [String: Any] = [:]
        var raw: Data?
        if let url = bundle.url(forResource: name, withExtension: "json", subdirectory: "Tuning"),
           let d = try? Data(contentsOf: url) {
            raw = d
            if let obj = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any] {
                json = obj
            } else {
                Log.error("tuning", "\(name).json is not a JSON object: compiled defaults apply")
            }
        }
        var ov: [String: String] = [:]
        for (k, v) in tune where k.hasPrefix(name + ".") { ov[String(k.dropFirst(name.count + 1))] = v }
        return TuningFile(name: name, json: json, data: raw, overrides: ov)
    }

    func value(_ path: String) -> Any? {
        if let o = overrides[path] { return o }
        var node: Any? = json
        for part in path.split(separator: ".") { node = (node as? [String: Any])?[String(part)] }
        return node
    }

    func has(_ path: String) -> Bool { value(path) != nil }

    func double(_ path: String, _ fallback: Double) -> Double {
        switch value(path) {
        case let n as NSNumber: return n.doubleValue
        case let s as String: return Double(s) ?? fallback
        default: return fallback
        }
    }

    func int(_ path: String, _ fallback: Int) -> Int { Int(double(path, Double(fallback))) }

    func bool(_ path: String, _ fallback: Bool) -> Bool {
        switch value(path) {
        case let n as NSNumber: return n.boolValue
        case let s as String: return ["1", "true", "yes", "on"].contains(s.lowercased())
        default: return fallback
        }
    }

    func string(_ path: String, _ fallback: String) -> String {
        switch value(path) {
        case let s as String: return s
        case let n as NSNumber: return n.stringValue
        default: return fallback
        }
    }

    func doubles(_ path: String, _ fallback: [Double]) -> [Double] {
        switch value(path) {
        case let a as [Any]:
            let n = a.compactMap { ($0 as? NSNumber)?.doubleValue }
            return n.count == a.count ? n : fallback
        case let s as String:
            let n = s.split(separator: ";").compactMap { Double($0) }
            return n.isEmpty ? fallback : n
        default: return fallback
        }
    }

    func strings(_ path: String, _ fallback: [String]) -> [String] {
        switch value(path) {
        case let a as [Any]:
            let s = a.compactMap { $0 as? String }
            return s.count == a.count ? s : fallback
        case let s as String:
            let parts = s.split(separator: ";").map(String.init)
            return parts.isEmpty ? fallback : parts
        default: return fallback
        }
    }

    /// SKIN (docs/SKIN.md): `<bundle>/Tuning/<name>.json`'s "colors" object, {id: "#RRGGBB[AA]"}. tools/skin/build.py
    /// generates it (ui-colors.json) from skin/colors.json `ui`; missing or malformed -> empty, and the references stay
    /// unresolved, so every read falls back to its compiled default (a missing file never crashes).
    static func referenceTable(_ name: String, bundle: Bundle) -> [String: String] {
        guard let url = bundle.url(forResource: name, withExtension: "json", subdirectory: "Tuning"),
              let d = try? Data(contentsOf: url),
              let obj = (try? JSONSerialization.jsonObject(with: d)) as? [String: Any],
              let colors = obj["colors"] as? [String: String] else {
            Log.error("tuning", "\(name).json is missing or has no \"colors\" object: skin references stay unresolved")
            return [:]
        }
        return colors
    }

    /// SKIN (docs/SKIN.md): the same file with every string "@<id>" (in the JSON and in the `-pc.tune` overrides) replaced
    /// by `table[id]`, e.g. ui.json's colour slots by the skin's colours. An id the table lacks stays as written (the typed
    /// read then uses its compiled default). `data` stays the raw file.
    func resolvingReferences(_ table: [String: String]) -> TuningFile {
        guard !table.isEmpty else { return self }
        func resolve(_ node: Any) -> Any {
            if let s = node as? String {
                if s.hasPrefix("@"), let v = table[String(s.dropFirst())] { return v }
                return s
            }
            if let d = node as? [String: Any] { return d.mapValues(resolve) }
            if let a = node as? [Any] { return a.map(resolve) }
            return node
        }
        let resolved = (resolve(json) as? [String: Any]) ?? json
        let ov = overrides.mapValues { (resolve($0) as? String) ?? $0 }
        return TuningFile(name: name, json: resolved, data: data, overrides: ov)
    }

    /// The whole file decoded as `T` (PathCore's Codable tuning types); nil when the file is missing or does not decode.
    func decode<T: Decodable>(_ type: T.Type) -> T? {
        guard let data else { return nil }
        do { return try JSONDecoder().decode(T.self, from: data) } catch {
            Log.error("tuning", "\(name).json does not decode as \(T.self): \(error)")
            return nil
        }
    }
}

/// `Tuning/board.json` (BOARD). Defaults: SPEC-architecture §4.2, §5 (VERIFIED unless the JSON's `_pending` lists it).
struct BoardTuning: Sendable {
    let file: TuningFile

    // zoom and pan (§5.2)
    var zoomMin: Double { file.double("zoom.min", 0.786) }                    // × fit (VERIFIED levels L47)
    var zoomMaxPitch: Double { file.double("zoom.maxPitch", 28.07) }          // absolute pt per cell (VERIFIED L47/L50)
    var panSlackPt: Double { file.double("pan.slackPt", 120) }                // PENDING-motion-audio (DECISION default)
    var panBounces: Bool { file.bool("pan.bounces", true) }                   // PENDING-motion-audio
    // input (§5.3)
    var slopPt: Double { file.double("input.slopPt", 10) }                    // spike; the phone's value PENDING
    var hitRadiusPt: Double { file.double("input.hitRadiusPt", 15) }          // VERIFIED ≥ 15 pt (L47c)
    var tieBreak: String { file.string("input.tieBreak", "rightThenDown") }  // VERIFIED once (L52a)
    // exit colours and painters (§4.7, §5.5)
    var comboLadder: [String] { file.strings("combo.ladder", ["solid", "solid", "violet", "rainbow"]) }
    var inkColor: String { file.string("color.ink", "#000000") }
    var exitColor: String { file.string("color.exit", "#10A2EF") }            // VERIFIED motion §2.2
    var violetColor: String { file.string("color.violet", "#9A50F5") }        // INFERRED; PENDING-motion-audio
    var markedColor: String { file.string("color.marked", "#EE0A13") }        // VERIFIED items
    var dotColor: String { file.string("color.dot", "#C5E1FF") }              // VERIFIED spike + STYLE
    var rainbowPalette: [String] {
        file.strings("rainbow.palette", ["#FF6500", "#FFCE01", "#9DE600", "#37E500", "#00E100", "#00D3AF", "#00C1FF",
                                         "#4079FF", "#8D5FFF", "#BC4BF3", "#FF2FC6", "#FF5A85"])
    }
    var rainbowPeriodCells: Double { file.double("rainbow.periodCells", 5.6) } // PENDING-motion-audio (5.6 vs 3.8)
    var exitColourRamp: Double { file.double("exit.colourRamp", 0.08) }       // VERIFIED motion §2.2
    // screen-space feedback (§5.8)
    var rippleR0: Double { file.double("ripple.r0Pt", 11) }
    var rippleR1: Double { file.double("ripple.r1Pt", 22.5) }
    var rippleDuration: Double { file.double("ripple.duration", 0.25) }
    var rippleLum0: Double { file.double("ripple.lum0", 180) }
    var rippleLum1: Double { file.double("ripple.lum1", 250) }
    var ripplePool: Int { file.int("ripple.pool", 6) }
    var vignetteDepthPt: Double { file.double("vignette.depthPt", 50) }
    var vignetteFull: Double { file.double("vignette.full", 0.05) }
    var vignetteFade: Double { file.double("vignette.fade", 0.28) }
    // bump (§5.5; PENDING-motion-audio: the phone wins over YT-B)
    var bumpOutSpeedPtPerS: Double { file.double("bump.outSpeedPtPerS", 400) }
    var bumpHold: Double { file.double("bump.hold", 0.10) }
    var bumpBack: Double { file.double("bump.back", 0.13) }
    var bumpBadgeFade: Double { file.double("bump.badgeFade", 0.3) }
    // transitions, warm-up, memory, perf (§5.7, §5.9, §10)
    var stageGap: Double { file.double("stageGap", 0.7) }                     // VERIFIED tutorials §2
    var warmupSpeed: Double { file.double("warmup.speed", 20) }
    var spriteCacheCapMB: Double { file.double("spriteCache.capMB", 48) }
    var hitchMs: Double { file.double("perf.hitchMs", 20) }
}

/// `Tuning/game.json` (GAME). Defaults: SPEC-architecture §6.2, §6.10, §8.4.
struct GameTuning: Sendable {
    let file: TuningFile

    var ftueChainUntilLevel: Int { file.int("ftue.chainUntilLevel", 7) }     // VERIFIED tutorials §1/§4
    var autoplayRate: Double { file.double("autoplay.rate", 0.45) }
    var hudPublishHz: Double { file.double("hud.publishHz", 10) }             // GP §8.1
    var probeHz: Double { file.double("probe.hz", 4) }                        // §9.4 (P8)
    var ratingAfterLevel: Int { file.int("rating.afterLevel", 34) }           // VERIFIED phone + V2 (D24)
    var notificationsAskOnFirstLaunch: Bool { file.bool("notifications.askOnFirstLaunch", true) }   // VERIFIED F00, V2
}

/// `Tuning/ui.json` (SHELL). Defaults: SPEC-architecture §6 (uim for the dims; the rest PENDING-ui).
struct UITuning: Sendable {
    let file: TuningFile

    var loadingMinSeconds: Double { file.double("loading.minSeconds", 1.5) }   // PENDING-ui
    var loadingCapSeconds: Double { file.double("loading.capSeconds", 4.0) }   // §6.1 cap
    var loadingToBoardFade: Double { file.double("transition.loadingToBoard", 0.13) }   // VERIFIED 0.1–0.16 s
    var loadingToHomeFade: Double { file.double("transition.loadingToHome", 0.3) }      // PENDING-ui
    /// The popup dims (VERIFIED uim): popup 0.90, unlock 0.90, outOfTime 0.94, skyMatch 0.96; info 0.95, weeklyTutorial
    /// 0.92, overPage 0.63 (VERIFIED SPEC-ui §1.3; WP0b).
    func dim(_ token: DimToken) -> Double {
        switch token {
        case .popup: return file.double("dim.popup", 0.90)
        case .unlock: return file.double("dim.unlock", 0.90)
        case .outOfTime: return file.double("dim.outOfTime", 0.94)
        case .skyMatch: return file.double("dim.skyMatch", 0.96)
        case .none: return 0
        case .info: return file.double("dim.info", 0.95)
        case .weeklyTutorial: return file.double("dim.weeklyTutorial", 0.92)
        case .overPage: return file.double("dim.overPage", 0.63)
        }
    }
    var popupDimFadeIn: Double { file.double("popup.dimFadeIn", 0) }          // VERIFIED 0–0.1 s
    var unlockBeats: UnlockBeats {
        let d = UnlockBeats()
        return UnlockBeats(icon: file.double("unlock.icon", d.icon), iconSettle: file.double("unlock.iconSettle", d.iconSettle),
                           title: file.double("unlock.title", d.title), unlocked: file.double("unlock.unlocked", d.unlocked),
                           card: file.double("unlock.card", d.card), sparkles: file.double("unlock.sparkles", d.sparkles),
                           dismissFade: file.double("unlock.dismissFade", d.dismissFade),
                           dismissMode: UnlockDismissMode(rawValue: file.string("unlock.dismissMode", d.dismissMode.rawValue))
                               ?? d.dismissMode)
    }
    var winPanelAt: Double { file.double("win.panelAt", 3.36) }               // VERIFIED motion §5.6
    var toastHold: Double { file.double("toast.hold", 2.0) }                  // PENDING-ui
}

/// `Tuning/audio.json` (AUDIO). Defaults: SPEC-architecture §7 (the cue and haptic maps are DECISIONs, §7.2 / §7.3).
struct AudioTuning: Sendable {
    let file: TuningFile

    var ioBufferDuration: Double { file.double("engine.ioBuffer", 0.005) }
    var voices: Int { file.int("engine.voices", 8) }
    var musicCrossfade: Double { file.double("music.crossfade", 0.3) }
    var musicEnabled: Bool { file.bool("music.enabled", false) }              // PENDING-motion-audio (clips-needed #4)

    /// The sound mapped to a moment ("uiButton", "celebrationSkip", "homePayout", "unlockOverlay", "arrowTap");
    /// nil = silent (VERIFIED: v552 plays nothing on taps, exits, bumps, obstacles, the timer or the win).
    func cue(_ moment: String) -> SoundID? {
        let fallback: [String: String] = ["uiButton": "uiClick", "celebrationSkip": "uiClick", "homePayout": "coinCollect",
                                          "unlockOverlay": "unlockChime"]
        return SoundID(rawValue: file.string("cues." + moment, fallback[moment] ?? ""))
    }

    func gain(_ s: SoundID) -> Double { file.double("gain." + s.rawValue, 1.0) }

    /// The generator style ("light", "medium", "heavy", "rigid", "soft", "success", "warning", "error", "none") and the
    /// intensity for a haptic moment (§7.3 defaults; the rows heartLost … coinLand are SPEC-motion-audio §15.1, WP0b).
    /// Contract amend 4 (SPEC.md §5 item 42 = ruling 39 OD4 + motion-catalog §5.1): button rigid 0.60 (was light 0.5), win =
    /// the OUT! slam heavy 1.0 (was success), and the seven new rows logoLetter … play.
    func haptic(_ h: Haptic) -> (style: String, intensity: Double) {
        let d: (String, Double)
        switch h {
        case .tap: d = ("rigid", 0.7)
        case .bumpContact: d = ("heavy", 0.85)
        case .fail: d = ("warning", 1.0)
        case .clear: d = ("medium", 0.8)
        case .win: d = ("heavy", 1.0)
        case .burst: d = ("medium", 0.65)
        case .heartLost: d = ("error", 1.0)
        case .button: d = ("rigid", 0.6)
        case .booster: d = ("medium", 0.6)
        case .coinLand: d = ("soft", 0.45)
        case .logoLetter: d = ("rigid", 0.7)
        case .logoBounce: d = ("rigid", 0.4)
        case .firework: d = ("soft", 0.35)
        case .rewardPop: d = ("light", 0.4)
        case .logoSwell: d = ("light", 0.45)
        case .keyTurn: d = ("rigid", 0.45)
        case .play: d = ("rigid", 0.75)
        }
        return (file.string("haptics.\(h.rawValue).style", d.0), file.double("haptics.\(h.rawValue).intensity", d.1))
    }
}

/// `Tuning/social.json` (SOCIAL). The whole file decodes into PathCore's `SocialConfig` (SOC1 owns the keys).
struct SocialTuning: Sendable {
    let file: TuningFile
    /// FIX-2 A: decoded ONCE per file (it was a JSONDecoder pass over social.json on every read — the Leaderboard tab strip's
    /// body read it, so a home arrival decoded the whole file on the main thread: build/p/FIX2/A/tp/base-tp1).
    let config: SocialConfig

    init(file: TuningFile) {
        self.file = file
        config = file.decode(SocialConfig.self) ?? .default
    }
}

struct Tuning: Sendable {
    var board: BoardTuning
    var game: GameTuning
    var ui: UITuning
    var audio: AudioTuning
    var social: SocialTuning
    /// `Tuning/rules.json` (CORE C2): GAME decodes it into PathCore's RulesTuning (`rules.decode(RulesTuning.self)`).
    var rules: TuningFile

    static let fileNames = ["board", "game", "ui", "audio", "rules", "social"]

    static func load(bundle: Bundle = .main, tune: [String: String] = [:]) -> Tuning {
        Tuning(board: BoardTuning(file: .load("board", bundle: bundle, tune: tune)),
               game: GameTuning(file: .load("game", bundle: bundle, tune: tune)),
               ui: UITuning(file: TuningFile.load("ui", bundle: bundle, tune: tune)
                                .resolvingReferences(TuningFile.referenceTable(uiColorsFile, bundle: bundle))),
               audio: AudioTuning(file: .load("audio", bundle: bundle, tune: tune)),
               social: SocialTuning(file: .load("social", bundle: bundle, tune: tune)),
               rules: .load("rules", bundle: bundle, tune: tune))
    }

    /// SKIN: ui.json names no colour; its colour slots are "@<id>" references resolved at load from this generated file
    /// (`Tuning/ui-colors.json`, tools/skin/build.py from skin/colors.json `ui`).
    static let uiColorsFile = "ui-colors"

    /// Compiled defaults only (tests, previews).
    static let defaults = Tuning(board: BoardTuning(file: TuningFile(name: "board", json: [:])),
                                 game: GameTuning(file: TuningFile(name: "game", json: [:])),
                                 ui: UITuning(file: TuningFile(name: "ui", json: [:])),
                                 audio: AudioTuning(file: TuningFile(name: "audio", json: [:])),
                                 social: SocialTuning(file: TuningFile(name: "social", json: [:])),
                                 rules: TuningFile(name: "rules", json: [:]))

    /// Which tuning files the bundle actually carried (boot log / placeholder).
    var loadedFiles: [String] {
        [board.file, game.file, ui.file, audio.file, rules, social.file].filter { $0.data != nil }.map(\.name)
    }
}
