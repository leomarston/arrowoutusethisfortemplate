import Foundation

// AUDIO A2 (SPEC-architecture §7.2, §7.3; SPEC-motion-audio §11.2, §12, §13.3). The moment → sound map and the haptic map
// are DATA (`Tuning/audio.json` keys `cues`, `gain`, `haptics`, `hapticPriority`). This file turns them into typed tables
// and holds the one-haptic-per-frame arbiter (§12.2). It is platform-neutral: tools/audio/engine_test.sh runs it on macOS
// against the real audio.json.

/// A moment that can carry a sound (`audio.json cues.<moment>`, SPEC-motion-audio §11.2). Every in-level event has no moment
/// and stays silent (MA1, VERIFIED v552). `arrowTap` is the owner's optional tap sound. It maps to "" (silent) by default
/// (MA3, SPEC.md §5 item 4), and one data change turns it on.
enum CueMoment: String, CaseIterable, Sendable {
    case uiButton, celebrationSkip, dismissTap, unlockOverlay, homePayout
    case clawToken, clawMerge, clawTick, clawComplete, streakPop
    case arrowTap
}

/// `audio.json haptics.<case>.style` (SPEC-motion-audio §12.2).
enum HapticStyle: String, CaseIterable, Sendable {
    case light, medium, heavy, rigid, soft          // UIImpactFeedbackGenerator styles (intensity 0…1)
    case success, warning, error                    // UINotificationFeedbackGenerator types (no intensity)
    case none                                       // the row is off: no code change needed to disable it

    var isImpact: Bool {
        switch self {
        case .light, .medium, .heavy, .rigid, .soft: return true
        case .success, .warning, .error, .none: return false
        }
    }

    var isNotification: Bool { self == .success || self == .warning || self == .error }
}

/// One haptic row: the generator and its intensity (impact styles only).
struct HapticRow: Equatable, Sendable, CustomStringConvertible {
    var style: HapticStyle
    var intensity: Double
    var description: String { style.isImpact ? "\(style.rawValue) \(String(format: "%.2f", intensity))" : style.rawValue }
}

/// The typed `audio.json` tables. Built once when the app starts (AudioEngine and Haptics), so the play paths never parse
/// JSON. A key that is missing or invalid falls back to the SPEC-motion-audio §13.3 value; the reason goes into
/// `problems`, which is logged at boot (SPEC-architecture §3.4 rule 4: a missing key never crashes).
struct AudioCueMap: Sendable {
    /// Moment → sound. A moment mapped to "" is absent (silent).
    let cues: [CueMoment: SoundID]
    /// Linear gain per sound (`gain.<id>`; the files are mastered at their target peaks, so 1.0 except tapTick 0.6).
    let gains: [SoundID: Float]
    let haptics: [Haptic: HapticRow]
    /// Highest priority first. Every `Haptic` case appears exactly once: the listed ones in the listed order, then any
    /// case the list forgot, in declaration order and at the lowest priority.
    let priority: [Haptic]
    let problems: [String]

    // MARK: SPEC-motion-audio §13.3 (the fallbacks; the shipped audio.json carries exactly these)

    static let specCues: [CueMoment: String] = [
        .uiButton: "uiClick", .celebrationSkip: "uiClick", .dismissTap: "uiClick", .unlockOverlay: "unlockChime",
        .homePayout: "coinCollect", .clawToken: "clawToken", .clawMerge: "clawMerge", .clawTick: "clawTick",
        .clawComplete: "clawComplete", .streakPop: "streakPop", .arrowTap: "",
    ]
    static let specGains: [SoundID: Float] = [.tapTick: 0.6]            // every other gain.<id> is 1.0
    static let specHaptics: [Haptic: HapticRow] = [
        .tap: HapticRow(style: .rigid, intensity: 0.70), .heartLost: HapticRow(style: .error, intensity: 1.0),
        .bumpContact: HapticRow(style: .heavy, intensity: 0.85), .fail: HapticRow(style: .warning, intensity: 1.0),
        .clear: HapticRow(style: .medium, intensity: 0.80), .win: HapticRow(style: .heavy, intensity: 1.0),
        .burst: HapticRow(style: .medium, intensity: 0.65), .button: HapticRow(style: .rigid, intensity: 0.60),
        .booster: HapticRow(style: .medium, intensity: 0.60), .coinLand: HapticRow(style: .soft, intensity: 0.45),
        // A0, contract amend 4 (SPEC.md §5 item 42 = ruling 39 OD4 + design/publish/motion-catalog.md §5.1): button rigid 0.60
        // (was light 0.50), win = the OUT! slam heavy 1.0 (was success; set above), and the seven new rows
        .logoLetter: HapticRow(style: .rigid, intensity: 0.70), .logoBounce: HapticRow(style: .rigid, intensity: 0.40),
        .firework: HapticRow(style: .soft, intensity: 0.35), .rewardPop: HapticRow(style: .light, intensity: 0.40),
        .logoSwell: HapticRow(style: .light, intensity: 0.45), .keyTurn: HapticRow(style: .rigid, intensity: 0.45),
        .play: HapticRow(style: .rigid, intensity: 0.75),
    ]
    /// motion-catalog §5.2's order; logoSwell and keyTurn (not placed there) sit with the other event beats above `tap`, and
    /// `play` just above `button` (A0, contract amend 4).
    static let specPriority: [Haptic] = [.heartLost, .fail, .win, .burst, .bumpContact, .clear, .logoLetter, .logoSwell, .keyTurn,
                                         .booster, .rewardPop, .coinLand, .firework, .logoBounce, .tap, .play, .button]

    /// `lookup` reads a dotted key ("cues.uiButton") from audio.json. In the app this is `TuningFile.value`, which also
    /// applies `-pc.tune audio.<key>=<value>` overrides, so a value may arrive as a String.
    init(lookup: (String) -> Any?) {
        var problems: [String] = []

        var cues: [CueMoment: SoundID] = [:]
        for m in CueMoment.allCases {
            let fallback = Self.specCues[m] ?? ""
            let raw: String
            switch lookup("cues." + m.rawValue) {
            case let s as String: raw = s
            case nil: raw = fallback; problems.append("cues.\(m.rawValue) missing: using \"\(fallback)\"")
            case let other?: raw = fallback; problems.append("cues.\(m.rawValue) is not a string (\(other)): using \"\(fallback)\"")
            }
            if raw.isEmpty { continue }
            if let s = SoundID(rawValue: raw) {
                cues[m] = s
            } else {
                problems.append("cues.\(m.rawValue) = \"\(raw)\" is not a SoundID: silent")
            }
        }

        var gains: [SoundID: Float] = [:]
        for s in SoundID.allCases {
            let fallback = Self.specGains[s] ?? 1
            let raw = lookup("gain." + s.rawValue)
            if let g = Self.number(raw), g >= 0, g <= 4 {
                gains[s] = Float(g)
            } else {
                problems.append("gain.\(s.rawValue) \(raw == nil ? "missing" : "invalid"): using \(fallback)")
                gains[s] = fallback
            }
        }

        var haptics: [Haptic: HapticRow] = [:]
        for h in Haptic.allCases {
            let fallback = Self.specHaptics[h] ?? HapticRow(style: .none, intensity: 0)
            var row = fallback
            if let s = lookup("haptics.\(h.rawValue).style") as? String {
                if let style = HapticStyle(rawValue: s) { row.style = style } else {
                    problems.append("haptics.\(h.rawValue).style \"\(s)\" unknown: using \(fallback.style.rawValue)")
                }
            } else {
                problems.append("haptics.\(h.rawValue).style missing: using \(fallback.style.rawValue)")
            }
            if let i = Self.number(lookup("haptics.\(h.rawValue).intensity")) {
                row.intensity = min(max(i, 0), 1)
            }
            haptics[h] = row
        }

        var priority: [Haptic] = []
        let listed: [Any]? = {
            switch lookup("hapticPriority") {
            case let a as [Any]: return a
            case let s as String: return s.split(separator: ";").map(String.init)
            default: return nil
            }
        }()
        if let listed {
            for item in listed {
                guard let name = item as? String, let h = Haptic(rawValue: name) else {
                    problems.append("hapticPriority: \(item) is not a Haptic case (ignored)")
                    continue
                }
                if priority.contains(h) { problems.append("hapticPriority: \(name) listed twice (first kept)") } else { priority.append(h) }
            }
        } else {
            problems.append("hapticPriority missing: using SPEC-motion-audio §12.2")
            priority = Self.specPriority
        }
        for h in Haptic.allCases where !priority.contains(h) {
            problems.append("hapticPriority: \(h.rawValue) not listed (lowest priority)")
            priority.append(h)
        }

        self.cues = cues
        self.gains = gains
        self.haptics = haptics
        self.priority = priority
        self.problems = problems
    }

    /// The SPEC-motion-audio §13.3 tables (tests, previews): an empty file falls back to every row.
    static let spec: AudioCueMap = {
        let json: [String: Any] = [
            "cues": Dictionary(uniqueKeysWithValues: specCues.map { ($0.key.rawValue, $0.value) }),
            "gain": Dictionary(uniqueKeysWithValues: SoundID.allCases.map { ($0.rawValue, Double(specGains[$0] ?? 1)) }),
            "haptics": Dictionary(uniqueKeysWithValues: specHaptics.map {
                ($0.key.rawValue, ["style": $0.value.style.rawValue, "intensity": $0.value.intensity] as [String: Any])
            }),
            "hapticPriority": specPriority.map(\.rawValue),
        ]
        return AudioCueMap(lookup: { AudioCueMap.dotted(json, $0) })
    }()

    /// The sound for a moment and its gain; nil = silent.
    func sound(for m: CueMoment) -> (id: SoundID, gain: Float)? {
        guard let s = cues[m] else { return nil }
        return (s, gains[s] ?? 1)
    }

    func row(_ h: Haptic) -> HapticRow { haptics[h] ?? HapticRow(style: .none, intensity: 0) }

    /// 0 = the highest priority.
    func rank(_ h: Haptic) -> Int { priority.firstIndex(of: h) ?? priority.count }

    /// Reads a dotted path from a parsed JSON object ("haptics.tap.style").
    static func dotted(_ json: [String: Any], _ path: String) -> Any? {
        var node: Any? = json
        for part in path.split(separator: ".") { node = (node as? [String: Any])?[String(part)] }
        return node
    }

    private static func number(_ v: Any?) -> Double? {
        switch v {
        case let n as NSNumber: return n.doubleValue
        case let s as String: return Double(s)
        default: return nil
        }
    }
}

/// SPEC-motion-audio §12.2: one haptic per display frame; when several are asked for, the highest priority wins.
///
/// Requests made during one main run-loop turn are collected, and the winner fires at the end of that turn, before Core
/// Animation commits it (`Haptics` flushes from a run-loop observer ordered just ahead of the commit). So the haptic still
/// leaves in the same turn as the visual (SPEC-architecture D8). This is how `burst` replaces `tap` on a box-break tap frame
/// and `heartLost` wins over `bumpContact`, whatever order the callers use.
/// A flush that comes less than one frame after the last fired haptic fires only when it outranks that haptic. A heart loss is
/// never swallowed by a button tick, and a lower row never doubles a frame.
struct HapticArbiter: Sendable {
    let map: AudioCueMap
    /// One display frame (the owner's iPhone 15 runs at 60 Hz).
    var frameWindow: Double = 1.0 / 60.0

    private(set) var pending: Haptic?
    private(set) var last: (haptic: Haptic, at: Double)?
    private(set) var dropped = 0
    private(set) var fired = 0

    init(map: AudioCueMap) { self.map = map }

    /// Records a request; a lower-priority request in the same turn is dropped.
    mutating func request(_ h: Haptic) {
        guard let p = pending else { pending = h; return }
        if map.rank(h) < map.rank(p) { pending = h }
        dropped += 1
    }

    /// The haptic to fire now (at the end of the turn), or nil.
    mutating func flush(now: Double) -> Haptic? {
        guard let p = pending else { return nil }
        pending = nil
        if let l = last, now - l.at < frameWindow, map.rank(p) >= map.rank(l.haptic) {
            dropped += 1
            return nil
        }
        last = (p, now)
        fired += 1
        return p
    }

    /// Drops a pending request (the Haptic toggle switched off mid-turn).
    mutating func clear() { pending = nil }
}
